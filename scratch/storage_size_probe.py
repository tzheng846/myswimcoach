"""Read-only probe: actual byte sizes in Supabase Storage buckets (raw-csvs, videos).

Uses the Storage API list endpoint (POST /storage/v1/object/list/{bucket}), which returns
each object's metadata including size in bytes. Recurses one level into raw-csvs (keyed
{athlete_id}/{timestamp}.csv); videos is flat ({session_id}.mp4).

No writes. No object contents are read or printed — only names and sizes.
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


def list_objects(bucket, prefix=""):
    objs = []
    offset = 0
    limit = 1000
    while True:
        resp = httpx.post(
            f"{URL}/storage/v1/object/list/{bucket}",
            headers=HEADERS,
            json={"prefix": prefix, "limit": limit, "offset": offset,
                  "sortBy": {"column": "name", "order": "asc"}},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        objs.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return objs


def bucket_total(bucket):
    top = list_objects(bucket)
    total_bytes = 0
    file_count = 0
    sizes = []
    for entry in top:
        if entry.get("id") is None:
            # it's a "folder" (no id) - recurse one level
            sub = list_objects(bucket, prefix=entry["name"])
            for f in sub:
                size = (f.get("metadata") or {}).get("size", 0)
                total_bytes += size
                file_count += 1
                sizes.append(size)
        else:
            size = (entry.get("metadata") or {}).get("size", 0)
            total_bytes += size
            file_count += 1
            sizes.append(size)
    return total_bytes, file_count, sizes


for bucket in ["raw-csvs", "videos"]:
    total, count, sizes = bucket_total(bucket)
    print(f"\n=== {bucket} ===")
    print(f"files: {count}")
    print(f"total: {total / 1024 / 1024:.1f} MB ({total / 1024 / 1024 / 1024:.3f} GB)")
    if sizes:
        sizes_sorted = sorted(sizes, reverse=True)
        print(f"avg: {sum(sizes)/len(sizes)/1024/1024:.2f} MB")
        print(f"largest 5 (MB): {[round(s/1024/1024,1) for s in sizes_sorted[:5]]}")
