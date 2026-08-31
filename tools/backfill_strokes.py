"""Backfill sessions.metrics_json.strokes + the arm-asymmetry session keys (Phase 87-01).

A freestyle or backstroke CYCLE is two arm strokes, and until 87-01 the pipeline collapsed
them before anything could look at them. This tool adds the per-ARM-STROKE array beside the
existing per-cycle one on the sessions already in the library, plus the seven session-level
keys derived from it (3 signed asymmetry percentages, 4 per-side CVs).

ADDITIVE ONLY. Exactly two things are written — metrics_json.strokes, and the seven new keys
merged into metrics_json.session. cycles / phases / initial_phase / data_quality ride through
byte-identical, and compute_session_metrics is never called (it would re-segment and could
overwrite a coach's cycles with auto ones).

The swim window comes from the STORED metrics_json.phases.boundaries, not from re-running
the detectors: those are the RESOLVED boundaries (manual > detected > auto) and they are what
the report card actually draws, so the strokes and the chart cannot disagree.

⚠ THE AUTO-PATH A/B ASSIGNMENT IS NOT TRUSTWORTHY, MEASURED. Against the coach-mark truth on
23 annotated freestyle sessions (2026-08-31) the auto-derived asymmetry scored Pearson
r = -0.06 with a median error of 10.2 percentage points against a signal whose median is
6.1%. The cause is PARITY, not precision: one extra or missing boundary flips the A/B side of
every stroke after it. Coach marks are the only trustworthy source — the marks/auto split is
printed for exactly that reason. And a 1-D axial encoder CANNOT observe which arm is which:
the sides are A and B, never left and right.

    python tools/backfill_strokes.py                      # dry run (the default)
    python tools/backfill_strokes.py --apply              # write
    python tools/backfill_strokes.py --limit 10           # sample the first 10
    python tools/backfill_strokes.py --session <uuid>     # one session

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The service-role key BYPASSES
RLS and is used only as a request header, never printed. Stroke boundaries are derived
signal, not personal data; this prints a session id prefix and stroke type only.
"""
import argparse
import math
import os
import sys
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import annotations as annot     # noqa: E402  (FS_HZ fallback + annotation_to_overrides)
import metrics as m             # noqa: E402

ALTERNATING = ("freestyle", "backstroke")


def _clean(obj):
    """NaN/inf -> None throughout a nested structure. Mirrors api.py's _clean so a
    backfilled row is byte-shaped like one written by the endpoint."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    return obj


def _arr(values):
    """Stored profile -> float array, nulls as NaN."""
    return np.array([np.nan if v is None else float(v) for v in (values or [])], dtype=float)


class Rest:
    """Minimal PostgREST client: GET always, PATCH only from the --apply path."""

    def __init__(self, url, key):
        self.base = f"{url.rstrip('/')}/rest/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def select(self, table, select, **params):
        r = httpx.get(f"{self.base}/{table}", params={"select": select, **params},
                      headers=self.headers, timeout=180)
        r.raise_for_status()
        return r.json()

    def patch(self, table, row_id, payload):
        r = httpx.patch(f"{self.base}/{table}", params={"id": f"eq.{row_id}"},
                        headers={**self.headers, "Content-Type": "application/json",
                                 "Prefer": "return=minimal"},
                        json=payload, timeout=180)
        r.raise_for_status()
        return r


def _window(mj, fs, n):
    """(win_start_idx, swim_start_idx, swim_end_idx) from the STORED resolved boundaries.

    win_start is dive_start_s where the boundaries carry one — it is what
    compute_session_metrics windows v95 over (b_end), and v95 sets the dead-spot threshold,
    so using the stroke start instead would silently shift dead_spot_s. Falls back to the
    stroke start. Returns None when there is no usable [stroke_start, finish] window.
    """
    b = ((mj.get("phases") or {}).get("boundaries") or {})
    start, finish = b.get("stroke_start_s"), b.get("finish_s")
    if start is None or finish is None:
        return None
    a = min(max(int(round(float(start) * fs)), 0), n - 1)
    e = min(max(int(round(float(finish) * fs)) + 1, a + 1), n)
    if e - a < 2:
        return None
    dive = b.get("dive_start_s")
    w0 = min(max(int(round(float(dive) * fs)), 0), a) if dive is not None else a
    return w0, a, e


def _spans(bounds, vel, n):
    """(start, end) index pairs -> stroke dicts, with the degenerate drop the pipeline uses."""
    out = []
    for a, b in bounds:
        a = min(max(int(a), 0), n - 1)
        b = min(int(b), n)
        if b - a < 2:
            continue
        out.append({"stroke_num": len(out), "start_idx": a, "end_idx": b,
                    "peak_idx": a + int(np.argmax(vel[a:b]))})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="perform the updates (default is a dry run, no writes)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit no-write mode (the default); overrides --apply if both are given")
    ap.add_argument("--limit", type=int, default=None, help="only process the first N sessions")
    ap.add_argument("--session", default=None, help="only this session id")
    args = ap.parse_args()
    write = args.apply and not args.dry_run

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

    db = Rest(url, key)

    params = {"velocity_profile": "not.is.null", "order": "created_at.asc"}
    if args.session:
        params["id"] = f"eq.{args.session}"
    rows = db.select("sessions", "id,sample_rate_hz,stroke_type", **params)
    if args.limit:
        rows = rows[: args.limit]

    ann_rows = db.select("session_annotations", "session_id,phases,stroke_marks_s")
    ann_by_session = {a["session_id"]: a for a in ann_rows}

    print(f"{len(rows)} session(s) with a velocity_profile; "
          f"{len(ann_by_session)} annotation(s) on file.")
    if not rows:
        print("Nothing to do.")
        return

    written = failed = 0
    skipped_stroke = skipped_window = 0
    from_marks = from_auto = no_strokes = asym_none = 0

    for i, r in enumerate(rows, 1):
        sid = r["id"]
        tag = f"[{i}/{len(rows)}] {sid[:8]}"
        stroke = r.get("stroke_type")
        if stroke not in ALTERNATING:
            skipped_stroke += 1
            continue
        try:
            got = db.select("sessions", "velocity_profile,distance_profile,metrics_json",
                            id=f"eq.{sid}")
            row = got[0] if got else {}
            vel = _arr(row.get("velocity_profile"))
            dist = _arr(row.get("distance_profile"))
            if vel.size < 2 or dist.size != vel.size:
                skipped_window += 1
                print(f"  {tag} - unusable profiles (vel={vel.size} dist={dist.size}), skipped")
                continue

            fs = float(r.get("sample_rate_hz") or annot.FS_HZ)   # SAME fallback every reader uses
            mj = row.get("metrics_json") or {}
            win = _window(mj, fs, vel.size)
            if win is None:
                skipped_window += 1
                print(f"  {tag} {(stroke or '?'):12} - no resolvable swim window, skipped")
                continue
            w0, a, e = win
            t = np.arange(vel.size) / fs

            ann = ann_by_session.get(sid)
            source = "auto"
            strokes = []
            if ann and ann.get("stroke_marks_s"):
                bounds = annot.annotation_to_overrides(
                    ann, int(vel.size), fs, stroke
                ).get("stroke_bounds") or []
                if bounds:
                    strokes = _spans(bounds, vel, vel.size)
                    source = "marks"
            if not strokes:
                seg = m.segment_strokes(t[a:e], vel[a:e], stroke) or []
                strokes = _spans([(s["start_idx"] + a, s["end_idx"] + a) for s in seg],
                                 vel, vel.size)
                source = "auto"

            if strokes:
                m.extract_cycle_peaks(vel, strokes)
                m._derive_item_metrics(strokes, t, vel, dist, fs,
                                       m._window_v95(vel, w0, e))
                if source == "marks":
                    from_marks += 1
                else:
                    from_auto += 1
            else:
                no_strokes += 1

            asym = m._arm_asymmetry(strokes)
            if asym["arm_asym_tempo_pct"] is None:
                asym_none += 1

            new_mj = _clean({
                **mj,
                "strokes": strokes or None,
                "session": {**(mj.get("session") or {}), **asym},
            })
            if write:
                db.patch("sessions", sid, {"metrics_json": new_mj})
                written += 1
                verb = "written"
            else:
                verb = "would write"

            tempo = asym["arm_asym_tempo_pct"]
            tempo_txt = "-" if tempo is None else f"{tempo:+.1f}%"
            print(f"  {tag} {(stroke or '?'):12} {len(strokes):3} strokes "
                  f"({source:5}) tempo asym {tempo_txt:>7} {verb}")
        except Exception as ex:  # noqa: BLE001 — one bad row must not abort the batch
            failed += 1
            print(f"  {tag} - ERROR {type(ex).__name__}: {ex}")

    # ⚠ EVERY counter prints even when zero (83-02's lesson: an unprinted zero reads as a
    # success). A from_marks of 0 means the coach's ground truth never reached the strokes.
    print()
    mode = "APPLIED" if write else "DRY RUN (no writes)"
    print(f"{mode}: {written} written, {failed} failed of {len(rows)} session(s).")
    print(f"  skipped, stroke_type not free/back:  {skipped_stroke}")
    print(f"  skipped, no resolvable swim window:  {skipped_window}")
    print(f"  strokes from COACH MARKS (trusted):  {from_marks}")
    print(f"  strokes from the AUTO segmenter:     {from_auto}")
    print(f"  window resolved but no strokes found:{no_strokes}")
    print(f"  asymmetry left None (<3 per side):   {asym_none}")
    if not write:
        print("\nRe-run with --apply to perform the updates.")


if __name__ == "__main__":
    main()
