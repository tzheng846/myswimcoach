---
phase: 69-multi-camera-video
plan: 01
subsystem: api
tags: [fastapi, supabase, postgres, video, multi-camera, rls]

requires:
  - phase: 67-external-camera-sync
    provides: MAX_VIDEO_BYTES size guard + streamed upload pattern; the videos bucket
provides:
  - session_videos table (externals-only, additive) + patch_12
  - external-video API — GET/POST/PATCH/DELETE /sessions/{id}/videos[/{id}], unified list with signed URLs
affects: [69-02 videos page, 69-03 synced player]

tech-stack:
  added: []
  patterns:
    - "Additive multi-video: phone/primary stays in sessions.video_path; session_videos holds <=3 externals. No migration, no reader breaks, mobile untouched."
    - "New schema table must be declared in supabase/live_schema.json or the AST schema-contract test fails the suite."

key-files:
  created:
    - supabase/patch_12_session_videos.sql
  modified:
    - api.py
    - tests/test_api.py
    - supabase/live_schema.json

key-decisions:
  - "session_videos is externals-only and additive — legacy columns + all 5 web readers + mobile unchanged."
  - "Reused the 67-02 memory-safe size guard + streamed upload for external uploads; cap 3 externals (409)."

duration: ~45min
started: 2026-08-17T01:30:00Z
completed: 2026-08-17T02:15:00Z
---

# Phase 69 Plan 01: session_videos + External-Video API Summary

**Added the additive foundation for up to 3 external camera videos per session — a `session_videos`
table (RLS-on, API-only) plus GET/POST/PATCH/DELETE `/sessions/{id}/videos` returning a unified list
(phone/primary from the legacy columns + externals) with signed URLs — without touching the legacy
video path, any of the 5 web readers, or mobile. Suite 58→61. Shipped `ca73421`.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: session_videos exists, externals-only, secured | Pass (code) | patch_12: table + FK ON DELETE CASCADE + index + RLS enabled, no anon policies. ⚠ Live-apply pending (checkpoint). |
| AC-2: External CRUD, capped at 3 | Pass | POST stores `{session_id}/{id}.mp4`, inserts row; 4th → 409; PATCH label/origin_s; DELETE removes object+row. `test_external_cap_returns_409`. |
| AC-3: Unified list feeds the player | Pass | GET returns primary (role phone) + externals (role external), each with signed URL + origin_s + label. `test_list_unifies_primary_and_externals`. |
| AC-4: Guards + ownership + legacy untouched | Pass | 413 size guard (`test_oversized_external_returns_413`); `_owned_session` on all; legacy `/video`+`/video-url` byte-identical (git diff: 0 deletions). |

## Verification Results

- `python -c "import api"` clean; routes `/sessions/{id}/videos` and `/videos/{video_id}` registered.
- `pytest tests/test_api.py -q` → **61 passed** (was 58; +3 external-video tests).
- `git diff api.py` → **+217 lines, 0 deletions** — legacy video handlers unchanged.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `supabase/patch_12_session_videos.sql` | Created | session_videos table (externals, RLS-on, cascade). |
| `api.py` | Modified | `import uuid`; `_signed_video_url` helper; 4 external-video endpoints. |
| `tests/test_api.py` | Modified | `TestSessionVideos` (size guard, cap 409, unified list). |
| `supabase/live_schema.json` | Modified | Declared `session_videos` for the schema-contract test. |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | `supabase/live_schema.json` (not in files_modified) had to gain `session_videos` — the Phase 51-02 AST schema-contract test fails the suite if api.py names a table absent from the snapshot. Legitimate + necessary; the user re-runs `tools/introspect_schema.py` after applying patch_12 to confirm the snapshot matches live. |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `TestSchemaContract` failed — `session_videos.* [table missing]` | Added the table to `supabase/live_schema.json` (the contract snapshot). |

## Next Phase Readiness

**Ready:** the external-video API is code-complete and shipped; 69-02/03 build on `GET /videos`
(list) + POST/PATCH/DELETE.

**Concerns:**
- ⚠ **patch_12 is NOT applied live yet** — the new endpoints 500 until the user runs it. Deferred to
  the end-of-phase bundle (with UAT), per the auto-loop instruction. Nothing calls them until 69-02.
- ⚠ Live end-to-end + real-video UAT owed at phase end.

**Blockers:** None for building 69-02/03 (the web compiles against the API contract).

---
*Phase: 69-multi-camera-video, Plan: 01 · Completed: 2026-08-17*
