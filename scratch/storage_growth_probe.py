"""Read-only: video upload growth rate, from row timestamps (not object metadata,
which Supabase's list API doesn't expose creation time for reliably)."""
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
    resp = httpx.get(f"{URL}/rest/v1/{path}", headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


sessions = rest("sessions", {"select": "id,created_at,video_path", "order": "created_at.asc"})
with_video = [s for s in sessions if s.get("video_path")]
print(f"total sessions: {len(sessions)}")
print(f"sessions with video_path: {len(with_video)}")
if with_video:
    print(f"first video session: {with_video[0]['created_at']}")
    print(f"last video session:  {with_video[-1]['created_at']}")

try:
    sv = rest("session_videos", {"select": "id,created_at,storage_path"})
    print(f"\nsession_videos rows: {len(sv)}")
    if sv:
        sv_sorted = sorted(sv, key=lambda r: r["created_at"])
        print(f"first: {sv_sorted[0]['created_at']}")
        print(f"last:  {sv_sorted[-1]['created_at']}")
except httpx.HTTPStatusError as e:
    print(f"\nsession_videos: {e.response.status_code} {e.response.text[:200]}")
