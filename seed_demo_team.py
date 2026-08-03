"""
seed_demo_team.py — populate a demo coach account with a believable training history.

The demo can't show off long-term athlete tracking without long-term data. This script
replays REAL raw encoder recordings from raw/ through the REAL production pipeline
(vel_acc_extraction.run_pipeline → metrics.compute_session_metrics) and writes session
rows shaped exactly like POST /process writes them, with backdated created_at.

Because the rows are shape-identical to real ones, every downstream surface (pillar
ratings, /team/overview, compare, per-cycle analytics, AI chat, the annotate page) works
with no product code changes.

Two stages, split by a human gate:
    Stage 1 (this script, --stage1)  12 athletes, each with ONE real archetype session
    ── human annotates those 12 at /app/annotate/[id] ──
    Stage 2 (50-02)                  perturb into ~144 sessions, propagate the annotations

Usage
-----
    python seed_demo_team.py --validate
    python seed_demo_team.py --coach-email demo@swimnetics.com --stage1 [--dry-run]
    python seed_demo_team.py --coach-email demo@swimnetics.com --wipe   [--dry-run]

Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in .env (service role — RLS is bypassed,
so every write is explicitly scoped to the resolved demo team_id).
"""

import argparse
import contextlib
import csv as _csv
import datetime
import io
import math
import os
import sys
import time
from pathlib import Path

# The local supabase/ folder (SQL migrations) shadows the installed supabase-py package
# when running from the project directory. Remove bare-path entries before importing so
# Python finds the real package in site-packages. (Same shim as fetch_sessions.py:19.)
sys.path = [p for p in sys.path if p not in ('', '.')]

import numpy as np
from dotenv import load_dotenv
from supabase import create_client

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))  # re-add THIS dir so our own modules import

import metrics as m                  # noqa: E402
import vel_acc_extraction as vae     # noqa: E402

load_dotenv()

SUPABASE_URL              = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

RAW_DIR      = _HERE / "raw"
RAW_BUCKET   = "raw-csvs"
TARGET_FS_HZ = 100.0

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG — this is the re-tuning surface. Edit here, not in the logic below.
# ══════════════════════════════════════════════════════════════════════════════

DEMO_TEAM_LABEL     = "Swimnetics Demo Squad"
WINDOW_MONTHS       = 6     # history depth
SESSIONS_PER_ATHLETE = 12   # consumed by 50-02

# Minimum bar for a raw CSV to be usable as an archetype.
MIN_CYCLES          = 4
MAX_DROPOUT_PCT     = 15.0

# ── Roster ────────────────────────────────────────────────────────────────────
# Names are fictional and the team label is plainly a demo — this is SAMPLE data and
# must never be presented as a real club's track record.
#
# archetype_csv: chosen from `--validate` PASS files (>=4 cycles, <=15% dropout) in the
#   16–42 s range, which reads as a 25/50 test set. The 188 s and 232 s recordings pass
#   validation but were excluded — they'd render absurd lap times on a report card.
# warp: raw/ contains only TWO usable freestyle recordings, so two freestyle athletes
#   necessarily share a source. A mild time-warp keeps their traces from being identical.
# trajectory: consumed by 50-02. These are the story beats to point at during a pitch.

DEMO_ROSTER = [
    # ── breaststroke (8) ──
    {"name": "Ava Lindqvist",  "stroke_type": "breaststroke", "archetype_csv": "leo1.csv",
     "trajectory": "strong_improver",     "head_waist_m": 0.42, "warp": 1.0},
    {"name": "Noah Feldman",   "stroke_type": "breaststroke", "archetype_csv": "leo2.csv",
     "trajectory": "steady_improver",     "head_waist_m": 0.45, "warp": 1.0},
    {"name": "Priya Raman",    "stroke_type": "breaststroke", "archetype_csv": "leo3.csv",
     "trajectory": "steady_improver",     "head_waist_m": 0.39, "warp": 1.0},
    {"name": "Diego Ferreira", "stroke_type": "breaststroke", "archetype_csv": "leo4.csv",
     "trajectory": "regression_recovery", "head_waist_m": 0.44, "warp": 1.0},
    {"name": "Mei Watanabe",   "stroke_type": "breaststroke", "archetype_csv": "leo_br_1.csv",
     "trajectory": "needs_attention",     "head_waist_m": 0.38, "warp": 1.0},
    {"name": "Owen Brennan",   "stroke_type": "breaststroke", "archetype_csv": "leo_br_2.csv",
     "trajectory": "steady_improver",     "head_waist_m": 0.46, "warp": 1.0},
    {"name": "Sofia Marchetti", "stroke_type": "breaststroke", "archetype_csv": "lucas_br_2.csv",
     "trajectory": "plateau",             "head_waist_m": 0.40, "warp": 1.0},
    {"name": "Kai Andersen",   "stroke_type": "breaststroke",
     "archetype_csv": "swim_lucas_br_6_20260515_193303.csv",
     "trajectory": "steady_improver",     "head_waist_m": 0.43, "warp": 1.0},

    # ── freestyle (4, from 2 sources) ──
    {"name": "Elena Vargas",   "stroke_type": "freestyle", "archetype_csv": "carlos_fr_1.csv",
     "trajectory": "strong_improver",     "head_waist_m": 0.41, "warp": 1.0},
    {"name": "Jonah Okafor",   "stroke_type": "freestyle", "archetype_csv": "carlos_fr_1.csv",
     "trajectory": "needs_attention",     "head_waist_m": 0.44, "warp": 1.06},
    {"name": "Hana Kirchner",  "stroke_type": "freestyle",
     "archetype_csv": "swim_lucas_fr_1_20260515_192607.csv",
     "trajectory": "steady_improver",     "head_waist_m": 0.37, "warp": 1.0},
    {"name": "Marcus Delaney", "stroke_type": "freestyle",
     "archetype_csv": "swim_lucas_fr_1_20260515_192607.csv",
     "trajectory": "steady_improver",     "head_waist_m": 0.47, "warp": 0.95},
]

# ── Timeline ──────────────────────────────────────────────────────────────────
# Clustered, not evenly spaced: clubs test periodically, so sessions bunch into "test
# weeks" a few weeks apart. This is what makes the roster grid's "last tested" column
# read naturally instead of metronomic. Consumed by 50-02.
TIMELINE = {
    "window_months":        WINDOW_MONTHS,
    "test_weeks":           6,      # ~one test block every 3-4 weeks
    "sessions_per_week":    2,      # 6 x 2 = 12 sessions per athlete
    "week_spacing_days":    (21, 28),
    "within_week_gap_days": (2, 3),
    "athlete_jitter_days":  (-2, 2),
    "skip_probability":     0.12,   # an athlete occasionally misses a test block
}

# ══════════════════════════════════════════════════════════════════════════════


def _clean(obj):
    """Recursively sanitize nested dicts/lists for JSON serialization.

    Mirrors api.py:_clean — numpy types and NaN/inf become JSON-safe. Deliberately
    duplicated rather than imported: importing api.py drags in FastAPI and its env.
    """
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    return obj


@contextlib.contextmanager
def _quiet():
    """Suppress the pipeline's progress prints — this script prints its own tables."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield


def _get_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        sys.exit("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def resolve_demo_target(sb, coach_email):
    """Resolve the demo coach's (coach_id, team_id). Every write is scoped to this.

    Hard-fails on 0 or >1 matches — a mistyped email must never silently fall through
    to some other team's data.
    """
    if not coach_email:
        sys.exit("Error: --coach-email is required for any operation that touches the DB")
    try:
        resp = sb.table("coaches").select("id, team_id, email").eq("email", coach_email).execute()
    except Exception as e:
        sys.exit(f"Error: could not reach Supabase ({type(e).__name__}: {e}).\n"
                 "Check SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in .env and your connection.")
    rows = resp.data or []
    if not rows:
        sys.exit(
            f"Error: no coach found with email {coach_email!r}.\n"
            "Sign up that coach through the portal first (the seeder never creates accounts)."
        )
    if len(rows) > 1:
        sys.exit(f"Error: {len(rows)} coaches share the email {coach_email!r} — refusing to guess.")
    row = rows[0]
    if not row.get("team_id"):
        sys.exit(f"Error: coach {coach_email!r} has no team_id.")
    return row["id"], row["team_id"]


def _magnet_dropout_pct(raw_bytes):
    """Fraction of rows flagged magnet_ok=0, as api.py:123-134 computes it."""
    total = bad = 0
    try:
        reader = _csv.DictReader(io.StringIO(raw_bytes.decode("utf-8", errors="replace")))
        for row in reader:
            total += 1
            if row.get("magnet_ok", "1") == "0":
                bad += 1
    except Exception:
        return 0.0
    return round(100.0 * bad / total, 1) if total else 0.0


def time_warp_bytes(raw_bytes, factor):
    """Scale a raw CSV's timeline by `factor` (>1 = slower swim, lower stroke rate).

    Deliberately the simplest INVERTIBLE warp: t' = t0 + (t − t0) × factor, angle counts
    untouched. Annotation marks map exactly the same way, which is what lets 50-02
    propagate hand-annotations into derived sessions instead of re-clicking them.
    """
    if factor == 1.0:
        return raw_bytes
    text = raw_bytes.decode("utf-8", errors="replace")
    all_rows = list(_csv.DictReader(io.StringIO(text)))
    if not all_rows:
        return raw_bytes

    # Real logger output contains occasional rows with a blank timestamp (leo3.csv has 9
    # of 12,647). load_data drops them downstream via dropna, so drop them here too
    # rather than letting float('') blow up mid-warp.
    rows = []
    for row in all_rows:
        try:
            row["_t"] = float(row.get("timestamp_us") or "")
        except ValueError:
            continue
        rows.append(row)
    if not rows:
        return raw_bytes

    t0 = rows[0]["_t"]
    for row in rows:
        row["timestamp_us"] = int(round(t0 + (row.pop("_t") - t0) * factor))

    out = io.StringIO()
    writer = _csv.DictWriter(out, fieldnames=list(all_rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def process_csv(csv_path, head_waist_m=0.0, warp=1.0):
    """Run a raw CSV (optionally time-warped) through the production pipeline.

    Returns (result, vel, dist_dec, data_quality, dropout_pct, raw_bytes) where
    raw_bytes is the WARPED payload — so what gets stored matches what was processed,
    keeping annotate-recompute consistent.
    Raises on unusable input — callers decide whether that's fatal.
    """
    raw_bytes = time_warp_bytes(Path(csv_path).read_bytes(), warp)
    dropout_pct = _magnet_dropout_pct(raw_bytes)

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name
    try:
        with _quiet():
            df = vae.load_data(tmp_path)
            # actual_fs, not TARGET_FS_HZ — decimation is by an integer factor, so the
            # requested rate is never achieved (~89.5 Hz typical). Stored per session.
            t_dec, dist_dec, vel, _accel, actual_fs = vae.run_pipeline(df, TARGET_FS_HZ)
            result = m.compute_session_metrics(
                t_dec, vel, dist_dec, head_waist_m=head_waist_m or 0.0
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Same warning set api.py:148-175 attaches.
    warnings = [
        "Kick metrics (pct_cycles_with_kick, mean_arm_kick_ratio, mean_arm_kick_delay_s) "
        "are unreliable — LP filter at default cutoff merges arm-pull and kick peaks"
    ]
    if result["session"].get("implausible_cycle_count", 0) > 0:
        warnings.append(
            f"{result['session']['implausible_cycle_count']} cycle(s) have implausible duration "
            f"(< 0.5 s or > 4.0 s) — possible segmentation artifact"
        )
    if dropout_pct > 5.0:
        warnings.append(
            f"Magnet signal lost for {dropout_pct:.1f}% of samples — encoder reliability reduced"
        )
    if not result["session"].get("segmentation_reliable", False):
        warnings.append(
            "Cycle segmentation is experimental (wavelet ridge, all strokes) — metrics are provisional"
        )

    data_quality = {
        "magnet_dropout_pct":      dropout_pct,
        "outlier_cycle_count":     result["session"].get("outlier_cycle_count", 0),
        "implausible_cycle_count": result["session"].get("implausible_cycle_count", 0),
        "total_cycles_raw":        result["session"].get("total_cycles_raw", 0),
        "segmentation_reliable":   result["session"].get("segmentation_reliable", False),
        "warnings":                warnings,
    }
    return result, vel, dist_dec, data_quality, dropout_pct, raw_bytes, float(actual_fs)


def ingest_csv(sb, csv_path, athlete_id, coach_id, created_at, name, notes,
               stroke_type, head_waist_m=0.0, warp=1.0, dry_run=False):
    """Ingest one raw CSV as a session row, mirroring POST /process (api.py:120-298).

    created_at is an ISO-8601 string and MUST be supplied: api.py orders by created_at in
    six places and the entire web portal sorts and displays on it (recorded_at drives
    nothing in the UI). Omitting it collapses the whole timeline onto today.

    Returns (session_id, n_cycles); session_id is None on dry-run.
    """
    result, vel, dist_dec, data_quality, _dropout, raw_bytes, actual_fs = process_csv(
        csv_path, head_waist_m, warp
    )
    n_cycles = len(result["cycles"])

    storage_path = f"{athlete_id}/{int(time.time() * 1000)}.csv"
    if dry_run:
        print(f"    [dry-run] would upload {storage_path} ({len(raw_bytes)} bytes)")
    else:
        try:
            sb.storage.from_(RAW_BUCKET).upload(
                path=storage_path,
                file=raw_bytes,
                file_options={"content-type": "text/csv"},
            )
        except Exception as e:
            print(f"    warn: storage upload failed ({e}) — continuing with null raw_csv_path")
            storage_path = None

    session_row = {
        "athlete_id":       athlete_id,
        "coach_id":         coach_id,
        "metrics_json":     _clean({
            "session":       result["session"],
            "cycles":        result["cycles"],
            "initial_phase": result.get("initial_phase", {}),
            "data_quality":  data_quality,
        }),
        "velocity_profile": _clean(vel.tolist()),
        "distance_profile": _clean(dist_dec.tolist()),
        "sample_rate_hz":   actual_fs,
        "raw_csv_path":     storage_path,
        "upload_status":    "complete",
        "name":             name,
        "notes":            notes,
        "stroke_type":      stroke_type,
        # device_id deliberately omitted — demo sessions aren't tied to a physical
        # encoder, and the roster decision was "no fake device row". NOT a constraint:
        # sessions.device_id is TEXT as of patch_06 (verified live 2026-07-30), so a
        # chip-id string would be a legal value here if a later plan wants one.
        "created_at":       created_at,
        "recorded_at":      created_at,
    }

    if dry_run:
        print(f"    [dry-run] would insert session '{name}' at {created_at} "
              f"({n_cycles} cycles)")
        return None, n_cycles

    resp = sb.table("sessions").insert(session_row).execute()
    return (resp.data[0]["id"] if resp.data else None), n_cycles


def wipe(sb, team_id, dry_run=False):
    """Remove all demo athletes (sessions + annotations follow via ON DELETE CASCADE)
    and their raw-csvs storage objects. Leaves coaches + teams intact so re-seeding
    needs no new signup."""
    resp = sb.table("athletes").select("id, name").eq("team_id", team_id).execute()
    athletes = resp.data or []
    if not athletes:
        print("Nothing to wipe — team has no athletes.")
        return 0

    print(f"Wiping {len(athletes)} athlete(s) from team {team_id}:")
    for a in athletes:
        aid = a["id"]
        try:
            objs = sb.storage.from_(RAW_BUCKET).list(path=aid)
            paths = [f"{aid}/{o['name']}" for o in (objs or [])]
        except Exception as e:
            print(f"  warn: could not list storage for {aid} ({e})")
            paths = []
        if paths:
            if dry_run:
                print(f"  [dry-run] would remove {len(paths)} storage object(s) for {a['name']}")
            else:
                try:
                    sb.storage.from_(RAW_BUCKET).remove(paths)
                except Exception as e:
                    print(f"  warn: storage remove failed for {aid} ({e})")
        if dry_run:
            print(f"  [dry-run] would delete athlete {a['name']} ({aid})")
        else:
            sb.table("athletes").delete().eq("id", aid).eq("team_id", team_id).execute()
            print(f"  deleted {a['name']}")
    return len(athletes)


def validate_archetypes():
    """Run every raw/ CSV through the pipeline and report whether it can serve as an
    archetype. Local only — no DB, no account. Known-bad files (truncated, sub-2 s,
    wrong columns) must be reported, not crash the pass."""
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        print(f"No CSVs found in {RAW_DIR}")
        return 0

    print(f"\nValidating {len(files)} raw CSV(s) in {RAW_DIR}\n")
    print(f"  {'':<4} {'file':<42} {'dur':>7} {'cycles':>7} {'drop%':>6}  reason")
    print("  " + "-" * 90)

    n_pass = 0
    for f in files:
        try:
            result, vel, _dist, dq, dropout, _raw, fs = process_csv(f)
            cycles   = len(result["cycles"])
            duration = len(vel) / fs
            reasons  = []
            if cycles < MIN_CYCLES:
                reasons.append(f"only {cycles} cycles (need >= {MIN_CYCLES})")
            if dropout > MAX_DROPOUT_PCT:
                reasons.append(f"magnet dropout {dropout}% (max {MAX_DROPOUT_PCT}%)")
            ok = not reasons
            n_pass += ok
            print(f"  {'PASS' if ok else 'FAIL':<4} {f.name:<42} {duration:>6.1f}s "
                  f"{cycles:>7} {dropout:>6.1f}  {'; '.join(reasons)}")
        except Exception as e:
            print(f"  {'FAIL':<4} {f.name:<42} {'—':>7} {'—':>7} {'—':>6}  "
                  f"{type(e).__name__}: {e}")

    print(f"\n  {n_pass}/{len(files)} usable as archetypes "
          f"(>= {MIN_CYCLES} cycles, <= {MAX_DROPOUT_PCT}% dropout)\n")
    return n_pass


def window_start():
    """First day of the history window (sessions are backdated into it)."""
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=int(WINDOW_MONTHS * 30.44)
    )


def stage1(sb, coach_id, team_id, dry_run=False, seed=50):
    """Create the demo athletes and ingest each one's archetype session.

    These archetypes are REAL recordings and become each athlete's earliest session —
    the ones the coach hand-annotates, which 50-02 then propagates from.
    """
    import random
    rng = random.Random(seed)

    existing = sb.table("athletes").select("id").eq("team_id", team_id).execute().data or []
    if existing and not dry_run:
        sys.exit(
            f"Refusing to seed: team already has {len(existing)} athlete(s).\n"
            "Run with --wipe first if you mean to re-seed from scratch."
        )

    start = window_start()
    print(f"\nStage 1 — {len(DEMO_ROSTER)} athletes, archetypes backdated to ~{start.date()}\n")

    rows_out = []
    for i, spec in enumerate(DEMO_ROSTER):
        csv_path = RAW_DIR / spec["archetype_csv"]
        if not csv_path.exists():
            print(f"  SKIP {spec['name']}: missing {spec['archetype_csv']}")
            continue

        # Spread the baseline tests across the first few days of the window.
        created_at = (start + datetime.timedelta(
            days=rng.randint(0, 4), hours=rng.randint(6, 11), minutes=rng.randint(0, 59)
        )).isoformat()

        stroke_short = {"breaststroke": "br", "freestyle": "fr"}.get(spec["stroke_type"], "")
        name  = f"Season baseline — 25 {stroke_short}".strip()
        notes = "First test of the block. Baseline for the season."

        if dry_run:
            athlete_id = f"<dry-run-athlete-{i}>"
            print(f"  [dry-run] would create athlete {spec['name']} ({spec['stroke_type']})")
        else:
            resp = sb.table("athletes").insert({
                "team_id":      team_id,
                "name":         spec["name"],
                "stroke_type":  spec["stroke_type"],
                "head_waist_m": spec["head_waist_m"],
            }).execute()
            if not resp.data:
                print(f"  FAIL {spec['name']}: athlete insert returned no row")
                continue
            athlete_id = resp.data[0]["id"]

        try:
            session_id, n_cycles = ingest_csv(
                sb, csv_path, athlete_id, coach_id, created_at, name, notes,
                spec["stroke_type"], spec["head_waist_m"],
                warp=spec.get("warp", 1.0), dry_run=dry_run,
            )
        except Exception as e:
            print(f"  FAIL {spec['name']}: {type(e).__name__}: {e}")
            continue

        rows_out.append({
            "athlete":    spec["name"],
            "stroke":     spec["stroke_type"],
            "archetype":  spec["archetype_csv"],
            "session_id": session_id or "—",
            "date":       created_at[:10],
            "cycles":     n_cycles,
        })

    print(f"\n  {'athlete':<18} {'stroke':<13} {'archetype':<40} {'date':<11} {'cyc':>4}  session_id")
    print("  " + "-" * 108)
    for r in rows_out:
        print(f"  {r['athlete']:<18} {r['stroke']:<13} {r['archetype']:<40} "
              f"{r['date']:<11} {r['cycles']:>4}  {r['session_id']}")
    print(f"\n  {len(rows_out)}/{len(DEMO_ROSTER)} athletes seeded\n")
    return len(rows_out)


def main():
    parser = argparse.ArgumentParser(
        description="Seed a demo coach account with a replayed training history.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--coach-email", default="",
                        help="Demo coach's email — scopes every write to their team")
    parser.add_argument("--validate", action="store_true",
                        help="Run every raw/ CSV through the pipeline and report PASS/FAIL")
    parser.add_argument("--stage1", action="store_true",
                        help="Create the demo athletes and ingest their archetype sessions")
    parser.add_argument("--wipe", action="store_true",
                        help="Delete all demo athletes, sessions, annotations and stored CSVs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print intended writes without executing any of them")
    args = parser.parse_args()

    if not (args.validate or args.stage1 or args.wipe):
        parser.print_help()
        return

    # --validate is local-only: no DB, no account needed.
    if args.validate:
        validate_archetypes()
        if not (args.stage1 or args.wipe):
            return

    sb = _get_client()
    coach_id, team_id = resolve_demo_target(sb, args.coach_email)
    print(f"Demo target: coach {coach_id}  team {team_id}"
          + ("   [DRY RUN — no writes]" if args.dry_run else ""))

    if args.wipe:
        wipe(sb, team_id, dry_run=args.dry_run)
    if args.stage1:
        stage1(sb, coach_id, team_id, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
