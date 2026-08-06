"""Snapshot the live Supabase schema (read-only).

Fetches ``{SUPABASE_URL}/rest/v1/`` — the OpenAPI document PostgREST generates from the
database — and writes ``{table: {column: type}}`` as JSON. Only catalog metadata crosses
the wire: no table rows are read and nothing is written.

Why this exists
---------------
``supabase/schema.sql`` and ``supabase/patch_04_backfill.sql`` have both been proven wrong
about the live database (the Phase-45 ``sessions.device_id`` migration and the
``athletes.coach_id`` column were each documented as applied but never run). The committed
snapshot is the only authority on what actually exists.

The snapshot is POINT-IN-TIME. Refresh it after any migration:

    python tools/introspect_schema.py

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The key is used only as a
request header and is never printed.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "supabase" / "live_schema.json"


def fetch_schema(url: str, key: str) -> dict:
    """Return {table: {column: type}} from PostgREST's OpenAPI document."""
    resp = httpx.get(
        f"{url.rstrip('/')}/rest/v1/",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=30,
    )
    resp.raise_for_status()
    spec = resp.json()

    # PostgREST emits Swagger 2.0 ("definitions"); tolerate OpenAPI 3 layout too.
    defs = spec.get("definitions") or spec.get("components", {}).get("schemas", {})
    if not defs:
        raise RuntimeError("OpenAPI document contained no table definitions")

    out = {}
    for table, meta in sorted(defs.items()):
        cols = {}
        for col, cmeta in (meta.get("properties") or {}).items():
            cols[col] = cmeta.get("format") or cmeta.get("type") or "unknown"
        out[table] = dict(sorted(cols.items()))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"output path (default: {DEFAULT_OUT})")
    parser.add_argument("--print", action="store_true", dest="to_stdout",
                        help="write to stdout instead of a file")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("error: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not found in .env", file=sys.stderr)
        return 1

    try:
        schema = fetch_schema(url, key)
    except Exception as e:  # network, auth, or malformed spec — one clear line, no traceback
        print(f"error: could not read the live schema ({type(e).__name__}: {e})", file=sys.stderr)
        return 1

    text = json.dumps(schema, indent=2) + "\n"
    if args.to_stdout:
        sys.stdout.write(text)
    else:
        Path(args.out).write_text(text, encoding="utf-8")
        total = sum(len(c) for c in schema.values())
        print(f"wrote {args.out} — {len(schema)} tables, {total} columns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
