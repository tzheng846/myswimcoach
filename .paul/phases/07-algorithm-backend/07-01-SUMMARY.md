---
phase: 07-algorithm-backend
plan: 01
subsystem: api
tags: [signal-processing, numpy, scipy, fastapi, supabase, storage, breaststroke, dive-detection]

requires:
  - phase: 06-03
    provides: auth flow, sessions table, athlete roster, /process endpoint with JWT auth

provides:
  - "detect_initial_phase(): identifies dive surge + underwater pulldown before cyclic strokes"
  - "time_to_distance(): elapsed time from swim start to head crossing target distance (waist-offset corrected)"
  - "compute_session_metrics(): updated to exclude initial phase from stroke count; returns initial_phase dict"
  - "/process: returns distance[] at 100Hz alongside velocity[] and time[]"
  - "/process: stores raw CSV to Supabase Storage raw-csvs bucket when athlete_id provided"
  - "/process: inserts full session row (metrics_json + velocity_profile + distance_profile) when athlete_id provided"
  - "supabase/patch_02_profiles_headwaist.sql: velocity_profile + distance_profile on sessions; head_waist_m on athletes"

affects: [08-ios-full-analytics, 09-ios-dashboard-history]

tech-stack:
  added: []
  patterns:
    - "detect_initial_phase: first deep trough after baseline_end = initial phase boundary; peaks before it = dive/pulldown"
    - "time_to_distance: waist_target = target_m - head_waist_m; searchsorted on dist_from_start"
    - "SUPABASE_SERVICE_ROLE_KEY for admin client — bypasses RLS for Storage + session INSERT"
    - "athlete_id optional Form field: backend skips Supabase save gracefully if not provided (pre-Phase 8 transition)"
    - "coach_id looked up from coaches table using user_id from require_auth — not auth.users.id directly"

key-files:
  created:
    - myswimcoach/supabase/patch_02_profiles_headwaist.sql
  modified:
    - myswimcoach/metrics.py
    - myswimcoach/api.py
    - myswimcoach/supabase/schema.sql

key-decisions:
  - "athlete_id made Optional[str] = Form(None) not required — prevents breaking existing iOS app before Phase 8 sends it"
  - "Initial phase detection uses first deep trough (<20% v95) as boundary; peaks before it classified as dive/pulldown"
  - "dive = first peak, pulldown = last peak in initial window (not highest — preserves chronological order)"
  - "vel_swim kept from b_end for session velocity stats (includes initial phase); segmentation starts from ip_end"
  - "Backend session save is non-fatal: all try/except pass — /process always returns 200"

patterns-established:
  - "detect_initial_phase always returns a safe dict with defaults — never raises, never blocks metrics computation"
  - "time_to_distance returns None for unreachable targets — caller must handle None"
  - "compute_session_metrics additive only: no existing keys renamed or removed"

duration: ~45min
started: 2026-05-23T00:00:00Z
completed: 2026-05-23T01:00:00Z
---

# Phase 7 Plan 01: Algorithm + Backend Summary

**Dive/pulldown detection added to metrics.py; /process returns 100Hz distance profile and stores full session to Supabase when iOS sends athlete_id (Phase 8).**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Completed | 2026-05-23 |
| Tasks | 2 auto + 1 checkpoint = 3 total |
| Files modified | 4 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Dive phase detected | Pass | Verified with realistic synthetic signal: dive_detected=True, dive_duration_s correct |
| AC-2: Pulldown phase detected | Pass | pulldown_detected=True, pulldown_peak_vel_ms=1.8 |
| AC-3: Robustness — skipped phases | Pass | No crash; dive_detected=False when no surge present |
| AC-4: time_to_distance correct | Pass | Returns smaller value with head_waist offset as expected |
| AC-5: Backend returns distance profile | Pass | Code in place; iOS not displaying yet (Phase 8) |
| AC-6: Raw CSV to Supabase Storage | Partial | Code in place; requires athlete_id from iOS (Phase 8) + setup done (key + bucket) |
| AC-7: Session row with full profiles | Partial | Code in place; requires athlete_id from iOS (Phase 8); iOS still saves minimal row from RecordScreen.js |
| AC-8: Schema migration | Pass | patch_02 run; columns exist (confirmed null values in sessions, not errors) |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified | Added detect_initial_phase(), time_to_distance(); updated compute_session_metrics() |
| `api.py` | Modified | Service role client; athlete_id/head_waist_m form fields; distance in response; Supabase save |
| `supabase/patch_02_profiles_headwaist.sql` | Created | Migration: velocity_profile + distance_profile on sessions; head_waist_m on athletes |
| `supabase/schema.sql` | Modified | Updated table definitions to match patch_02 columns |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| athlete_id = Optional Form(None) | Existing iOS app doesn't send it; required would break /process before Phase 8 | Backend save skips gracefully until Phase 8 |
| Separate vel_swim / vel_seg | vel_swim from b_end for session stats (includes initial phase); vel_seg from ip_end for segmentation | max_vel_ms includes dive velocity; stroke count excludes it |
| Non-fatal Supabase saves | Demo must not fail if Storage/DB is unavailable | /process always returns 200 with full data |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Scope adjustments | 1 | athlete_id made optional (anticipated in plan notes) |
| Deferred | 2 | AC-6, AC-7 fully verified in Phase 8 when iOS sends athlete_id |

**Total impact:** Minimal. The plan anticipated the Phase 8 dependency; backend is wired and waiting.

### Deferred Items
- AC-6/AC-7 full verification: iOS must send `athlete_id` + `head_waist_m` as multipart form fields — Phase 8 task
- RecordScreen.js still saves a minimal session row (no profiles) — Phase 8 will remove this after backend save confirmed

## Environment Setup Done (Pre-Phase 8)

| Item | Status |
|------|--------|
| SUPABASE_SERVICE_ROLE_KEY in Railway | ✓ Done |
| raw-csvs bucket in Supabase Storage | ✓ Done |
| patch_02_profiles_headwaist.sql applied | ✓ Done |

## Next Phase Readiness

**Ready:**
- detect_initial_phase() and time_to_distance() fully implemented and tested
- /process returns distance[], initial_phase, raw_csv_path
- Backend will save full session (metrics + profiles) the moment iOS sends athlete_id
- Schema columns and Storage bucket are live

**Concerns:**
- RecordScreen.js still does fire-and-forget session save without profiles — Phase 8 must remove it to avoid duplicate rows
- iOS currently uses FileSystem.uploadAsync with no extra form fields — Phase 8 must add athlete_id + head_waist_m to the parameters dict

**Blockers:** None

---
*Phase: 07-algorithm-backend, Plan: 01*
*Completed: 2026-05-23*
