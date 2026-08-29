"""One-time reclaim of orphaned files in the `videos` Storage bucket (Phase 82).

Two leak sources in `DELETE /sessions/{id}` left files behind with no live row pointing at
them: the primary `video_path` was never removed from storage, and `session_videos` externals
`ON DELETE CASCADE` at the DB level without their storage object ever being removed. Both are
fixed in api.py going forward; this script clears the historical debt.

An orphan is any file in the `videos` bucket whose name is NOT the current
`sessions.video_path` of some row, and NOT the current `session_videos.storage_path` of some
row. Both reference sets are read fresh every run — nothing here is cached from an earlier
discussion or a prior run of this script.

    python tools/cleanup_orphan_videos.py            # dry run (also the default) - lists only
    python tools/cleanup_orphan_videos.py --dry-run  # explicit no-delete mode
    python tools/cleanup_orphan_videos.py --apply    # actually deletes the orphans

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The service-role key BYPASSES RLS
and Storage ownership checks and is used only as a request header, never printed. No object
contents are read — only names and byte sizes, which carry no personal data.
"""
import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

BUCKET = "videos"
DELETE_BATCH_SIZE = 100  # keeps each bulk-delete request body small and predictable


def list_all_objects(base_url, headers, bucket, prefix=""):
    """Every object under `prefix` in `bucket`, recursing one level into any "folder" entry
    (an entry with no `id` — e.g. session_videos externals nest under {session_id}/{uuid}.mp4).
    Returns {name: size_bytes}.
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


def live_referenced_paths(base_url, headers):
    """Every storage path a live row currently points at, read fresh from Postgres."""
    rest_headers = {**headers}
    sessions = httpx.get(f"{base_url}/rest/v1/sessions", headers=rest_headers,
                          params={"select": "video_path"}, timeout=60).json()
    session_videos = httpx.get(f"{base_url}/rest/v1/session_videos", headers=rest_headers,
                                params={"select": "storage_path"}, timeout=60).json()
    paths = {row["video_path"] for row in sessions if row.get("video_path")}
    paths |= {row["storage_path"] for row in session_videos if row.get("storage_path")}
    return paths


def delete_objects(base_url, headers, bucket, names):
    """Bulk-delete via the Storage API, batched so no single request gets too large."""
    deleted = []
    for i in range(0, len(names), DELETE_BATCH_SIZE):
        batch = names[i : i + DELETE_BATCH_SIZE]
        resp = httpx.request(
            "DELETE", f"{base_url}/storage/v1/object/{bucket}",
            headers={**headers, "Content-Type": "application/json"},
            json={"prefixes": batch}, timeout=60,
        )
        resp.raise_for_status()
        deleted.extend(batch)
    return deleted


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="actually delete the orphan files (default is a dry run, no deletes)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit no-delete mode (the default); overrides --apply if both are given")
    args = ap.parse_args()
    apply_deletes = args.apply and not args.dry_run

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Need SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    base_url = url.rstrip("/")
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    print(f"Listing objects in `{BUCKET}`...")
    bucket_files = list_all_objects(base_url, headers, BUCKET)
    print(f"Reading live references (sessions.video_path + session_videos.storage_path)...")
    live_paths = live_referenced_paths(base_url, headers)

    orphans = {name: size for name, size in bucket_files.items() if name not in live_paths}
    orphan_bytes = sum(orphans.values())

    print(f"\n{len(bucket_files)} file(s) in `{BUCKET}`; {len(live_paths)} live-referenced path(s).")
    print(f"{len(orphans)} orphan(s), {orphan_bytes / 1024 / 1024:.1f} MB "
          f"({orphan_bytes / 1024 / 1024 / 1024:.3f} GB)\n")

    if not orphans:
        print("Nothing to reclaim.")
        return

    for name in sorted(orphans):
        print(f"  {name}  ({orphans[name] / 1024 / 1024:.1f} MB)")

    if not apply_deletes:
        print("\nDry run - nothing deleted. Re-run with --apply to delete the files listed above.")
        return

    print(f"\nDeleting {len(orphans)} file(s)...")
    deleted = delete_objects(base_url, headers, BUCKET, list(orphans.keys()))
    reclaimed = sum(orphans[name] for name in deleted)
    print(f"Deleted {len(deleted)} file(s), reclaimed {reclaimed / 1024 / 1024:.1f} MB "
          f"({reclaimed / 1024 / 1024 / 1024:.3f} GB).")


if __name__ == "__main__":
    main()
