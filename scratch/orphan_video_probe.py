"""Read-only: cross-reference the videos bucket's actual file list against what
live rows (sessions.video_path, session_videos.storage_path) say should exist.
Anything in the bucket but not referenced by a live row is an orphan (deleted
session, video never cleaned up) or a video from a session with no video_path
(e.g. delete-then-something). No writes.
"""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def rest(path, params):
    r = httpx.get(f"{URL}/rest/v1/{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def list_all(bucket):
    objs, offset, limit = [], 0, 1000
    while True:
        r = httpx.post(f"{URL}/storage/v1/object/list/{bucket}", headers=HEADERS,
                        json={"prefix": "", "limit": limit, "offset": offset,
                              "sortBy": {"column": "name", "order": "asc"}}, timeout=30)
        r.raise_for_status()
        batch = r.json()
        objs.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return objs

bucket_files = list_all("videos")
bucket_names = {f["name"]: (f.get("metadata") or {}).get("size", 0) for f in bucket_files}

sessions = rest("sessions", {"select": "id,video_path"})
live_paths = {s["video_path"] for s in sessions if s.get("video_path")}

sv = rest("session_videos", {"select": "storage_path"})
live_paths |= {r["storage_path"] for r in sv if r.get("storage_path")}

orphans = {name: size for name, size in bucket_names.items() if name not in live_paths}
referenced_missing = live_paths - set(bucket_names.keys())

orphan_bytes = sum(orphans.values())
print(f"bucket files: {len(bucket_names)}")
print(f"live referenced paths (sessions.video_path + session_videos.storage_path): {len(live_paths)}")
print(f"orphan files (in bucket, no live row references them): {len(orphans)}")
print(f"orphan bytes: {orphan_bytes/1024/1024:.1f} MB ({orphan_bytes/1024/1024/1024:.3f} GB)")
print(f"rows referencing a path NOT found in bucket (broken link): {len(referenced_missing)}")
if orphans:
    print("\nsample orphan filenames (first 10):")
    for n in list(orphans.keys())[:10]:
        print(f"  {n}  ({orphans[n]/1024/1024:.1f} MB)")
