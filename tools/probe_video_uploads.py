"""Measure why phone video clips go missing, and whether Phase 84-05's fix worked (read-only).

Phase 84 item 2 — "video fails to upload sometimes" — was diagnosed with a throwaway probe. This
is that probe made re-runnable, so the numbers can be re-taken instead of quoted from a plan:

    python tools/probe_video_uploads.py

Reports, in order:

1. **Bucket** — object count and total MB in `videos`, plus the size distribution of the
   *top-level* objects (the phone/primary clips; `session_videos` externals nest one level down)
   and the counts at >=30/40/45/48/50 MB. A distribution that stops just short of the server's
   50 MB cap and never crosses it is the cap truncating the tail.
2. **Encode rate** — MB/s recovered from every successfully-stored clip, as
   `object_bytes / (deviceDuration - video_origin_s)`, where
   `deviceDuration = len(velocity_profile) / sample_rate_hz`. Prints the median and range and the
   clip length at which 50 MB is reached, for the median and the fastest rate observed.
3. **Lost clips** — sessions with `video_origin_s` set and `video_path` NULL. That pairing is a
   direct fingerprint of a clip the phone had in hand that never landed: `VideoOverlayScreen`
   auto-posts the origin on mount whenever it is null, so the origin proves a local file existed.
   Each row is priced at the median rate and marked over/under the 50 MB cap.
4. **Write-ability** — a single 1-byte object `_quota_probe.bin` POSTed to the bucket and deleted
   again, printing both status codes. This is the standing check that Storage is not rejecting
   writes for quota reasons (an alternative explanation for a lost clip). It is the ONE write this
   script makes, and it cleans up after itself.

**This is the instrument that measures whether the 84-05 fix worked.** The fix stops the app
producing clips it cannot upload and refuses an over-cap clip before the network. So: the section-3
lost-clip count *for sessions created after the fixed build ships* must stop growing. Old rows stay
— they are history, not a regression.

Read-only apart from the 1-byte probe in section 4. No object CONTENTS are read anywhere — names
and byte sizes only — and no session field is printed beyond timings and sizes, so no personal data
leaves the database.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The service-role key BYPASSES RLS and
Storage ownership checks and is used only as a request header, never printed.
"""
import os
import statistics
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

BUCKET = "videos"
MB = 1024 * 1024
# Mirrors api.py's MAX_VIDEO_BYTES (50 MB, the Supabase free-tier global upload ceiling). The
# server's value is authoritative; this copy exists only to draw the line in the output.
MAX_VIDEO_BYTES = 50 * MB
# Project rule: sample_rate_hz NULL means "unknown", NOT "100". Fall back to 100 for arithmetic
# here (annotations.FS_HZ), and say so in the output rather than silently pretending.
FALLBACK_FS_HZ = 100.0
# A recovered clip shorter than this is a nonsense origin, not a real clip; it would divide a real
# byte count by ~0 and poison the median rate.
MIN_CLIP_S = 2.0

PROBE_NAME = "_quota_probe.bin"


def list_all_objects(base_url, headers, bucket, prefix=""):
    """Every object under `prefix` in `bucket`, recursing one level into any "folder" entry
    (an entry with no `id` — session_videos externals nest under {session_id}/{uuid}.mp4).
    Returns {name: size_bytes}. Same walk as tools/cleanup_orphan_videos.py.
    """
    objects = {}
    offset = 0
    limit = 1000
    while True:
        resp = httpx.post(
            f"{base_url}/storage/v1/object/list/{bucket}",
            headers=headers,
            json={"prefix": prefix, "limit": limit, "offset": offset,
                  "sortBy": {"column": "name", "order": "asc"}},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for entry in batch:
            full_name = f"{prefix}{entry['name']}" if prefix else entry["name"]
            if entry.get("id") is None:
                objects.update(list_all_objects(base_url, headers, bucket, prefix=f"{full_name}/"))
            else:
                objects[full_name] = (entry.get("metadata") or {}).get("size", 0)
        if len(batch) < limit:
            break
        offset += limit
    return objects


def percentile(sorted_vals, q):
    """Nearest-rank percentile over an already-sorted list."""
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


def device_duration_s(base_url, headers, session_id, fs_hz):
    """len(velocity_profile) / sample_rate_hz for one session.

    ⚠ Fetched PER SESSION, never in the bulk select: velocity_profile is thousands of floats and
    pulling it for every row would be several MB over the wire for one length each.
    There is no `duration_s` column on `sessions` — this is the only way to recover it.
    """
    resp = httpx.get(
        f"{base_url}/rest/v1/sessions",
        headers=headers,
        params={"select": "velocity_profile", "id": f"eq.{session_id}"},
        timeout=60,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        return None
    profile = rows[0].get("velocity_profile")
    if not isinstance(profile, list) or not profile:
        return None
    return len(profile) / fs_hz


def report_bucket(objects):
    total_bytes = sum(objects.values())
    print(f"\n=== 1. `{BUCKET}` bucket ===")
    print(f"{len(objects)} object(s), {total_bytes / MB:.0f} MB "
          f"({total_bytes / MB / 1024:.2f} GB)")

    # Top-level objects only: {session_id}.mp4 written by POST /sessions/{id}/video (the phone's
    # own clip). Externals live under {session_id}/{uuid}.mp4 and are a different producer.
    top = sorted(size for name, size in objects.items() if "/" not in name)
    if not top:
        print("No top-level (phone) clips.")
        return
    print(f"\nPhone clips ({len(top)} top-level objects), MB:")
    print(f"  min {top[0] / MB:.1f}   median {statistics.median(top) / MB:.1f}   "
          f"p90 {percentile(top, 0.90) / MB:.1f}   max {top[-1] / MB:.1f}")
    marks = [30, 40, 45, 48, 50]
    counts = "    ".join(f">={m} MB: {sum(1 for s in top if s >= m * MB)}" for m in marks)
    print(f"  {counts}")
    print(f"  (server cap is {MAX_VIDEO_BYTES // MB} MB - api.py MAX_VIDEO_BYTES)")


def report_encode_rate(base_url, headers, stored):
    """stored: rows with BOTH video_origin_s and video_path. Returns the median MB/s or None."""
    print("\n=== 2. Encode rate (from successfully-stored clips) ===")
    rates = []
    skipped_short = 0
    fallback_fs = 0
    missing_object = 0
    no_profile = 0
    for row in stored:
        size = row["_size"]
        if size is None:
            missing_object += 1
            continue
        fs = row.get("sample_rate_hz")
        if not fs:
            fs = FALLBACK_FS_HZ
            fallback_fs += 1
        dev_s = device_duration_s(base_url, headers, row["id"], fs)
        if dev_s is None:
            no_profile += 1
            continue
        clip_s = dev_s - float(row["video_origin_s"])
        if clip_s <= MIN_CLIP_S:
            skipped_short += 1
            continue
        rates.append((size / MB) / clip_s)

    print(f"{len(stored)} session(s) with both video_origin_s and video_path; "
          f"{len(rates)} usable for a rate.")
    notes = []
    if fallback_fs:
        notes.append(f"{fallback_fs} used the {FALLBACK_FS_HZ:.0f} Hz FALLBACK (sample_rate_hz NULL)")
    if skipped_short:
        notes.append(f"{skipped_short} skipped (recovered clip <= {MIN_CLIP_S:.0f} s)")
    if missing_object:
        notes.append(f"{missing_object} skipped (video_path has no object in the bucket)")
    if no_profile:
        notes.append(f"{no_profile} skipped (no velocity_profile)")
    for n in notes:
        print(f"  note: {n}")

    if not rates:
        print("  No usable rows — cannot derive an encode rate.")
        return None

    med = statistics.median(rates)
    lo, hi = min(rates), max(rates)
    print(f"\n  median {med:.2f} MB/s     range {lo:.2f} - {hi:.2f} MB/s")
    cap_mb = MAX_VIDEO_BYTES / MB
    print(f"  {cap_mb:.0f} MB is reached at {cap_mb / med:.0f} s of video at the median rate,")
    print(f"                        and at {cap_mb / hi:.0f} s at the fastest rate observed.")
    return med


def report_lost_clips(base_url, headers, lost, median_rate):
    """lost: rows with video_origin_s set and video_path NULL."""
    print("\n=== 3. Lost clips (video_origin_s set, video_path NULL) ===")
    print(f"{len(lost)} session(s) carry the fingerprint of a clip that never landed.")
    if not lost:
        return
    if median_rate is None:
        print("  (no median rate available — sizes not predicted)")
    print(f"\n  {'created_at':<20} {'device':>9} {'origin':>8} {'clip':>9} {'pred MB':>9}  vs cap")
    for row in sorted(lost, key=lambda r: r.get("created_at") or ""):
        fs = row.get("sample_rate_hz") or FALLBACK_FS_HZ
        dev_s = device_duration_s(base_url, headers, row["id"], fs)
        origin = float(row["video_origin_s"])
        created = (row.get("created_at") or "")[:19].replace("T", " ")
        if dev_s is None:
            print(f"  {created:<20} {'?':>9} {origin:>8.1f} {'?':>9} {'?':>9}")
            continue
        clip_s = dev_s - origin
        if median_rate is None:
            print(f"  {created:<20} {dev_s:>8.1f}s {origin:>8.1f} {clip_s:>8.1f}s {'-':>9}")
            continue
        pred_mb = clip_s * median_rate
        marker = "OVER" if pred_mb > MAX_VIDEO_BYTES / MB else "under"
        print(f"  {created:<20} {dev_s:>8.1f}s {origin:>8.1f} {clip_s:>8.1f}s "
              f"{pred_mb:>9.0f}  {marker}")
    print("\n  Predicted size = recovered clip duration x the median rate from section 2.")
    print("  After 84-05 ships, rows created AFTER that build must stop appearing here.")


def report_writeability(base_url, headers):
    """The one write: a 1-byte object, then its deletion. Standing quota/permission check."""
    print("\n=== 4. Storage write-ability (1-byte probe) ===")
    put = httpx.post(
        f"{base_url}/storage/v1/object/{BUCKET}/{PROBE_NAME}",
        headers={**headers, "Content-Type": "application/octet-stream", "x-upsert": "true"},
        content=b"\x00",
        timeout=30,
    )
    print(f"  POST {PROBE_NAME}  -> {put.status_code}")
    delete = httpx.request(
        "DELETE", f"{base_url}/storage/v1/object/{BUCKET}",
        headers={**headers, "Content-Type": "application/json"},
        json={"prefixes": [PROBE_NAME]},
        timeout=30,
    )
    print(f"  DELETE {PROBE_NAME} -> {delete.status_code}")
    if put.status_code < 300:
        print("  Storage accepts writes - a lost clip is NOT a quota rejection.")
    else:
        print("  !! Storage REFUSED the write - quota or permissions are implicated.")


def main():
    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    base_url = url.rstrip("/")
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    print(f"Listing objects in `{BUCKET}`...")
    objects = list_all_objects(base_url, headers, BUCKET)
    report_bucket(objects)

    print("\nReading sessions (video_origin_s / video_path / sample_rate_hz)...")
    rows = httpx.get(
        f"{base_url}/rest/v1/sessions",
        headers=headers,
        params={"select": "id,created_at,sample_rate_hz,video_origin_s,video_path",
                "video_origin_s": "not.is.null"},
        timeout=60,
    ).json()

    stored = [r for r in rows if r.get("video_path")]
    for r in stored:
        r["_size"] = objects.get(r["video_path"])
    lost = [r for r in rows if not r.get("video_path")]

    median_rate = report_encode_rate(base_url, headers, stored)
    report_lost_clips(base_url, headers, lost, median_rate)
    report_writeability(base_url, headers)


if __name__ == "__main__":
    main()
