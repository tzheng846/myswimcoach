---
phase: 47-trial-annotation
plan: 01
subsystem: api
tags: [fastapi, supabase, annotations, rls, storage, signed-url, video]

requires:
  - phase: 36-metric-ratings
    provides: _owned_session-style ownership pattern (coach 403 / foreign 404, DB errors → 5xx)
  - phase: 39 (39-05)
    provides: cycle start_idx/end_idx ÷ 100 = seconds convention (seed reuses it)
  - phase: 44 (44-03)
    provides: video_origin_s end-anchor convention (deviceDuration − videoDuration)
provides:
  - Trial-annotation API contract (locked) — GET/PUT/DELETE /sessions/{id}/annotations,
    POST /sessions/{id}/video, GET /sessions/{id}/video-url
  - annotations.py pure module — PHASE_KEYS canonical order, build_seed, validate_annotation
  - session_annotations table + RLS; sessions.video_path/video_origin_s; private videos bucket (LIVE — user applied)
affects: [47-02 web annotation GUI, 47-03 iOS video upload, 47-04 recompute, 16-06 wavelet tuning]

tech-stack:
  added: []
  patterns:
    - "Annotation doc: {phases: {dive_start_s, underwater_start_s, breakout_start_s, stroke_start_s, finish_s}, stroke_marks_s: [sorted], source: manual|seeded}"
    - "Video bytes never proxy through the API — private bucket + 3600 s signed URL"
    - "_owned_session(sb_admin, user_id, session_id, fields) shared ownership helper"

key-files:
  created: [supabase/patch_07_annotations.sql, annotations.py, tests/test_annotations.py]
  modified: [api.py]

key-decisions:
  - "Seed ordering-consistency walks BACKWARDS through PHASE_KEYS — cycle-derived anchors beat speculative dive-based estimates"
  - "One annotation row per session, last write wins (no versioning)"
  - "Video stored as {session_id}.mp4 with x-upsert (re-upload replaces)"
  - "Light-touch validation: any phase subset OK; marks not required inside the stroke span"

patterns-established:
  - "underwater_start_s is the canonical key; clients display 'pulldown' for breaststroke"
  - "duration_s for clients = len(velocity_profile)/100 (FS_HZ in annotations.py)"

duration: ~25min
started: 2026-07-11
completed: 2026-07-11
---

# Phase 47 Plan 01: Annotation Backend Contract Summary

**Trial-annotation API shipped and live-schema'd: session_annotations table + private videos
bucket (user-applied patch_07), pure annotations.py seed/validate module, and 5 auth+ownership
endpoints — the locked contract for the web GUI (47-02), iOS video upload (47-03), and metric
recompute (47-04).**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~25 min |
| Tasks | 3 auto + 1 human-action checkpoint, all complete |
| Files modified | 4 (3 created, 1 modified) |
| Test suite | 131 passed (was 103; +28 new) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Annotation contract (GET seed + saved + video) | Pass | Seed from metrics_json verified: dive←baseline_end_s, underwater←dive peak, stroke_start←initial_phase_end_idx (fallback first cycle), finish←last cycle end, marks←cycle start_idx/100 |
| AC-2: Save + validation | Pass | Upsert on_conflict=session_id; 422 with errors list; partial docs accepted |
| AC-3: Ownership + auth | Pass | 401 no token, 403 no coach profile, 404 foreign session (ratings pattern; DB errors → 5xx) |
| AC-4: Video attach + retrieval, velocity-only OK | Pass | Private bucket, x-upsert, signed URL 3600 s; origin-only nudge update supported; video:null sessions fully annotatable |

## Accomplishments

- **Contract locked**: annotation doc shape + endpoint semantics documented in annotations.py and
  covered by tests — 47-02/03/04 build against it without renegotiation.
- **Video reaches the cloud for the first time** (resolves Phase 45's deferred "discuss first"):
  `videos` bucket + `sessions.video_path`/`video_origin_s` live in the real DB.
- **Schema applied to production** during the checkpoint (user ran patch_07; verified
  session_annotations + videos bucket exist).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `supabase/patch_07_annotations.sql` | Created | session_annotations + team-scoped RLS; sessions video cols; private videos bucket. Idempotent. **APPLIED LIVE 2026-07-11** |
| `annotations.py` | Created | Pure: FS_HZ=100, PHASE_KEYS, build_seed(metrics_json), validate_annotation(doc, duration_s) |
| `api.py` | Modified | `_owned_session` helper + 5 endpoints (annotations GET/PUT/DELETE, video POST, video-url GET) |
| `tests/test_annotations.py` | Created | 28 tests: pure seed/validate + endpoint auth/ownership/validation/video |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Backwards ordering-drop in build_seed | Cycle-derived anchors (stroke_start, finish) are trustworthy; dive+duration underwater estimate is speculative — when they disagree, keep the cycles | Seeds never violate the ordering contract and never sacrifice good anchors |
| Signed URL (no byte proxying) | Keeps large video traffic off Railway | 47-02 player consumes the URL directly |
| `{session_id}.mp4` fixed path + x-upsert | One video per session, re-upload replaces | Simple; multi-angle video would need a schema change (out of scope) |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Design fix inside planned scope |

**1. Seed ordering rule direction**
- **Found during:** Task 3 (test `test_misordered_detection_dropped` failed)
- **Issue:** Forward walk kept the speculative underwater estimate and dropped the reliable cycle-derived stroke_start
- **Fix:** Reversed iteration over PHASE_KEYS (later/cycle-derived anchors win)
- **Verification:** Full suite 131 green

## Issues Encountered

None beyond the deviation above.

## Next Phase Readiness

**Ready:**
- 47-02 (web GUI): GET returns everything the page needs in one call (annotation, seed, video, duration_s); portal VelocityChart already supports markers; session RLS lets supabase-js read too.
- 47-03 (iOS): POST /sessions/{id}/video accepts multipart + origin; origin = deviceDuration − videoDuration (44-03 values already computed in VideoOverlayScreen).
- 47-04 (recompute): stroke_marks_s are exactly cycle boundaries at 100 Hz — mapping back to start_idx/end_idx is ×100.

**Concerns:**
- Railway does not have the new endpoints until the user pushes api.py + annotations.py (47-02 can verify against a local backend, Phase-36 style).
- Seed quality inherits the wavelet segmenter's placeholder quality (`segmentation_reliable=False`) — that's the point of the tool, but expect editing work per session.

**Blockers:** None.

---
*Phase: 47-trial-annotation, Plan: 01*
*Completed: 2026-07-11*
