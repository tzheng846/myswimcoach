---
phase: 15-billing
plan: 02
subsystem: billing-enforcement
tags: [fastapi, billing, ios, stripe, enforcement]

requires: [15-01-SUMMARY.md]
provides:
  - monthly_session_limit enforced in /process (HTTP 402)
  - device_limit enforced in /process for new devices (HTTP 402)
  - POST /athletes proxy endpoint with athlete_limit enforcement (HTTP 402)
  - iOS RecordScreen.js: Alert.alert on 402 from /process
  - iOS AthletesScreen.js: POST /athletes API call + Alert.alert on 402
affects: [iOS app build needed for iOS changes]

tech-stack:
  patterns:
    - "_get_coach_row() reused from 15-01 for limit fields — no duplicate coach lookups"
    - "HTTPException pass-through fix: except HTTPException: raise before except Exception"
    - "Device limit check only on NEW devices (chip_id not yet in devices for this coach)"
    - "monthly_session_limit=None skips check — paid tiers are uncapped"

key-files:
  modified:
    - api.py
    - swimnetics-mobile/src/screens/RecordScreen.js
    - swimnetics-mobile/src/screens/AthletesScreen.js

key-decisions:
  - "athletes insert now via POST /athletes (server-enforced) not direct Supabase client"
  - "device limit check: is_new_device flag prevents blocking already-registered devices"
  - "402 detail message is user-readable and passed through to iOS Alert"

duration: ~15min
started: 2026-06-08T00:00:00Z
completed: 2026-06-08T00:00:00Z
---

# Phase 15 Plan 02: Tier Enforcement Summary

**Server-side billing limits wired end-to-end: /process enforces session + device limits, POST /athletes enforces athlete limit, iOS surfaces 402s as Alert dialogs.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min |
| Tasks | 6 completed |
| Files modified | 3 (api.py, RecordScreen.js, AthletesScreen.js) |
| Tests | 26/26 pass |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: /process returns 402 on session limit | Pass | Count vs monthly_session_limit; skipped when None |
| AC-2: /process returns 402 on new device over limit | Pass | is_new_device check + count vs device_limit |
| AC-3: POST /athletes returns 402 on athlete limit | Pass | count vs athlete_limit before insert |
| AC-4: iOS RecordScreen 402 → Alert | Pass | Alert.alert added; 402 handled before generic throw |
| AC-5: iOS AthletesScreen → POST /athletes + 402 Alert | Pass | Direct Supabase insert replaced with fetch |
| AC-6: 26/26 pytest pass | Pass | `pytest tests/ -q` |

## Accomplishments

- All three billing-controlled resources now enforced server-side — no client-side bypass possible
- HTTPException pass-through bug fixed (`except HTTPException: raise` added before `except Exception`)
- `_get_coach_row()` from 15-01 reused — no new Supabase query patterns
- iOS 402 alerts are user-readable (detail string from API passed straight through)

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `api.py` | Modified | `import datetime`; limit checks in /process; `except HTTPException: raise`; `POST /athletes` |
| `swimnetics-mobile/src/screens/RecordScreen.js` | Modified | `Alert` import; 402 handled before generic throw |
| `swimnetics-mobile/src/screens/AthletesScreen.js` | Modified | `Alert` + `API_BASE` imports; `session` from useAuth; `handleAdd` replaced with fetch |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Device limit: only check new devices | Returning coaches re-uploading from same device shouldn't be blocked | is_new_device flag queries devices table before limit check |
| `POST /athletes` sets both team_id and coach_id | coach_id enables count query; team_id satisfies schema constraint | Backend fetches both from coaches row |
| iOS removes `!teamId` guard from handleAdd | teamId no longer needed — backend resolves team from coach row | Slightly simpler iOS code |

## Deviations from Plan

None. Executed exactly as planned.

## Issues Encountered

None.

## Next Phase Readiness

**Phase 15 complete.** Both plans delivered:
- 15-01: Stripe checkout/portal/webhook/status endpoints
- 15-02: Server-side enforcement + iOS error handling

**iOS build needed** before enforcement is live on device (RecordScreen + AthletesScreen changes).

**Remaining v0.5 work:** Phase 16 (Freestyle Support — wavelet/CWT segmentation).

---
*Phase: 15-billing, Plan: 02*
*Completed: 2026-06-08*
