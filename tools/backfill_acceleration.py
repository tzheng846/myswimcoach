"""Backfill sessions.acceleration_profile from the stored velocity_profile (Phase 64-02).

Acceleration is a pure, deterministic function of velocity + sample rate
(``vel_acc_extraction.acceleration_from_velocity`` — decimate velocity to 5 Hz, np.gradient,
interpolate back), so every existing row can be filled EXACTLY from data already in the database.
No raw-CSV reprocessing, and the velocity_profile itself is never touched.

    python tools/backfill_acceleration.py            # dry run: process every candidate, no writes
    python tools/backfill_acceleration.py --apply     # perform the updates

Idempotent and narrow: only rows where acceleration_profile IS NULL and velocity_profile IS NOT
NULL are considered, so a re-run after a successful pass is a no-op and a row that already has an
acceleration_profile is never overwritten.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The service-role key BYPASSES RLS and
is used only as a request header, never printed. Acceleration values are derived signal (not
personal data); the script prints array lengths and min/max for sanity, never a name/note/email.
"""
import argparse
import math
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import vel_acc_extraction as vae  # noqa: E402
import annotations               # noqa: E402  (FS_HZ fallback for NULL-rate rows)


def _clean(values):
    """NaN/inf -> None, everything else -> plain float. Mirrors api.py's _clean intent so a
    backfilled row is byte-shaped like a freshly-processed one."""
    out = []
    for x in values:
        f = float(x)
        out.append(None if (math.isnan(f) or math.isinf(f)) else f)
    return out


class Rest:
    """Minimal PostgREST client: GET always, PATCH only from the --apply path."""

    def __init__(self, url, key):
        self.base = f"{url.rstrip('/')}/rest/v1"
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def select(self, table, select, **params):
        r = httpx.get(f"{self.base}/{table}", params={"select": select, **params},
                      headers=self.headers, timeout=120)
        r.raise_for_status()
        return r.json()

    def patch(self, table, row_id, payload):
        r = httpx.patch(f"{self.base}/{table}", params={"id": f"eq.{row_id}"},
                        headers={**self.headers, "Content-Type": "application/json",
                                 "Prefer": "return=minimal"},
                        json=payload, timeout=120)
        r.raise_for_status()
        return r


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="perform the updates (default is a dry run, no writes)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit no-write mode (the default); overrides --apply if both are given")
    args = ap.parse_args()
    write = args.apply and not args.dry_run

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")

    db = Rest(url, key)

    # Candidates: velocity present, acceleration absent. Light columns only for the sweep.
    rows = db.select("sessions", "id,sample_rate_hz",
                     acceleration_profile="is.null",
                     velocity_profile="not.is.null",
                     order="created_at.asc")
    print(f"{len(rows)} session(s) need backfill (acceleration NULL, velocity present).")
    if not rows:
        print("Nothing to do.")
        return

    updated = skipped = failed = 0
    for i, r in enumerate(rows, 1):
        sid = r["id"]
        fs = r.get("sample_rate_hz") or annotations.FS_HZ  # SAME fallback every reader uses
        tag = f"[{i}/{len(rows)}] {sid}"
        try:
            got = db.select("sessions", "velocity_profile", id=f"eq.{sid}")
            vel = (got[0].get("velocity_profile") if got else None) or []
            if not vel:
                skipped += 1
                print(f"  {tag} — empty velocity, skipped")
                continue
            accel = vae.acceleration_from_velocity(vel, fs)
            if len(accel) != len(vel):
                failed += 1
                print(f"  {tag} — LENGTH MISMATCH {len(accel)} != {len(vel)}, refused")
                continue
            cleaned = _clean(accel.tolist())
            finite = [x for x in cleaned if x is not None]
            lo, hi = (min(finite), max(finite)) if finite else (float("nan"), float("nan"))
            if write:
                db.patch("sessions", sid, {"acceleration_profile": cleaned})
                updated += 1
                verb = "written"
            else:
                verb = "would write"
            print(f"  {tag} — {verb}: n={len(cleaned)} fs={fs:.1f} accel[{lo:.2f}, {hi:.2f}]")
        except Exception as e:  # noqa: BLE001 — one bad row must not abort the batch
            failed += 1
            print(f"  {tag} — ERROR {type(e).__name__}: {e}")

    print()
    mode = "APPLIED" if write else "DRY RUN (no writes)"
    print(f"{mode}: {updated} updated, {skipped} skipped, {failed} failed of {len(rows)} candidates.")
    if not write:
        print("Re-run with --apply to perform the updates.")


if __name__ == "__main__":
    main()
