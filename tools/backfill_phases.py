"""Backfill sessions.metrics_json.phases from the stored profiles (Phase 75-02).

The same derivation POST /sessions/{id}/recompute performs, applied to the whole library
in one pass: read velocity/distance/acceleration_profile + metrics_json + sample_rate_hz +
stroke_type, read the coach's session_annotations.phases if there is one, build a
phase_metrics.PhaseContext, and write back {**metrics_json, "phases": compute_phases(ctx)}.

No raw-CSV reprocessing. ONLY metrics_json.phases is replaced — session / cycles /
initial_phase / data_quality ride through untouched, exactly as the endpoint promises.
Idempotent: every value derives fresh from the stored profiles, so a second run produces
a byte-identical phases object.

    python tools/backfill_phases.py --dry-run            # no writes (also the default)
    python tools/backfill_phases.py --apply              # write
    python tools/backfill_phases.py --dry-run --limit 10 # sample the first 10

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The service-role key BYPASSES
RLS and is used only as a request header, never printed. Phase boundaries and metrics are
derived signal, not personal data; this prints a session id prefix and stroke type only —
never a name, note, or email.
"""
import argparse
import math
import os
import sys
from collections import Counter
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import annotations as annot     # noqa: E402  (FS_HZ fallback + build_seed)
import phase_metrics as pm      # noqa: E402


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
    """Stored profile -> float array, nulls as NaN (detect_underwater_start tolerates them)."""
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="perform the updates (default is a dry run, no writes)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit no-write mode (the default); overrides --apply if both are given")
    ap.add_argument("--limit", type=int, default=None, help="only process the first N sessions")
    args = ap.parse_args()
    write = args.apply and not args.dry_run

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

    db = Rest(url, key)

    rows = db.select("sessions", "id,sample_rate_hz,stroke_type",
                     velocity_profile="not.is.null", order="created_at.asc")
    if args.limit:
        rows = rows[: args.limit]

    # One read for every annotation, rather than a per-session round trip.
    ann_rows = db.select("session_annotations", "session_id,phases")
    ann_by_session = {a["session_id"]: a.get("phases") for a in ann_rows}

    print(f"{len(rows)} session(s) with a velocity_profile; "
          f"{len(ann_by_session)} annotation(s) on file.")
    if not rows:
        print("Nothing to do.")
        return

    written = skipped = failed = 0
    with_uw = 0
    sources = Counter()
    for i, r in enumerate(rows, 1):
        sid = r["id"]
        tag = f"[{i}/{len(rows)}] {sid[:8]}"
        stroke = r.get("stroke_type")
        try:
            got = db.select(
                "sessions",
                "velocity_profile,distance_profile,acceleration_profile,metrics_json",
                id=f"eq.{sid}",
            )
            row = got[0] if got else {}
            vel = _arr(row.get("velocity_profile"))
            dist = _arr(row.get("distance_profile"))
            if vel.size < 2 or dist.size != vel.size:
                skipped += 1
                print(f"  {tag} - unusable profiles (vel={vel.size} dist={dist.size}), skipped")
                continue

            fs = float(r.get("sample_rate_hz") or annot.FS_HZ)   # SAME fallback every reader uses
            mj = row.get("metrics_json") or {}
            ctx = pm.PhaseContext(
                t=np.arange(vel.size) / fs,
                vel=vel,
                dist=dist,
                accel=_arr(row.get("acceleration_profile")),
                fs=fs,
                stroke_type=stroke,
                go_signal_s=None,
                annotation_phases=ann_by_session.get(sid),
                seed_phases=annot.build_seed(mj, fs)["phases"],
                initial_phase=mj.get("initial_phase"),
            )
            phases = _clean(pm.compute_phases(ctx))

            b = phases["boundaries"]
            for k, v in b["sources"].items():
                sources[f"{k}={v}"] += 1
            uw = phases["underwater"]["uw_duration"]["value"]
            if uw is not None:
                with_uw += 1

            if write:
                db.patch("sessions", sid, {"metrics_json": {**mj, "phases": phases}})
                written += 1
                verb = "written"
            else:
                verb = "would write"

            uw_txt = f"{uw:.2f}s" if uw is not None else "-"
            start_txt = ("-" if b["underwater_start_s"] is None
                         else f"{b['underwater_start_s']:.2f}s")
            print(f"  {tag} {(stroke or '?'):12} uw_start {start_txt:>7} "
                  f"({b['sources']['underwater_start_s']:8}) uw_duration {uw_txt:>7} {verb}")
        except Exception as e:  # noqa: BLE001 — one bad row must not abort the batch
            failed += 1
            print(f"  {tag} - ERROR {type(e).__name__}: {e}")

    print()
    mode = "APPLIED" if write else "DRY RUN (no writes)"
    print(f"{mode}: {written} written, {skipped} skipped, {failed} failed of {len(rows)}.")
    print(f"Sessions with a non-null uw_duration: {with_uw} of {len(rows)}")
    print("Boundary sources:")
    for key in ("dive_start_s", "underwater_start_s", "stroke_start_s", "finish_s"):
        parts = [f"{src.split('=')[1]} {n}" for src, n in sorted(sources.items())
                 if src.startswith(key + "=")]
        print(f"  {key:20} {', '.join(parts)}")
    if not write:
        print("\nRe-run with --apply to perform the updates.")


if __name__ == "__main__":
    main()
