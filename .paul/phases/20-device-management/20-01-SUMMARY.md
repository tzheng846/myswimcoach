---
phase: 20-device-management
plan: 01
subsystem: ui, api
tags: [react-native, fastapi, flatlist, supabase, device-management]

requires:
  - phase: 14-device-registration
    provides: GET/PATCH /devices endpoints + devices table + auto-registration on /process
  - phase: 6-auth
    provides: useAuth JWT pattern used in all API calls

provides:
  - DevicesScreen.js — iOS screen listing registered encoders with stats, inline rename, deregister
  - GET /devices enriched with session_count per device
  - DELETE /devices/{chip_id} endpoint

affects: [future device-related screens, any phase adding device analytics]

tech-stack:
  added: []
  patterns:
    - FlatList with extraData for reactive item re-render on editingChipId state change
    - Isolated try/except for non-critical enrichment queries (session_count fallback to 0)
    - onBlur-only rename (no onSubmitEditing) to prevent double-fire on iOS Return press

key-files:
  created:
    - swimnetics-mobile/src/screens/DevicesScreen.js
  modified:
    - api.py
    - swimnetics-mobile/src/screens/AthletesScreen.js
    - swimnetics-mobile/App.js

key-decisions:
  - "session_count query isolated: count query failure doesn't kill GET /devices"
  - "onBlur-only rename: removes onSubmitEditing to prevent double PATCH on iOS keyboard Done"
  - "extraData={editingChipId} on FlatList: required for item re-render when edit state changes"

patterns-established:
  - "Non-critical enrichment queries wrapped in separate try/except with safe default"
  - "FlatList items that depend on external state need extraData prop"

duration: ~1 session
started: 2026-06-09T00:00:00Z
completed: 2026-06-09T00:00:00Z
---

# Phase 20 Plan 01: Device Management Summary

**DevicesScreen added to iOS with inline rename + deregister; GET /devices enriched with session_count; DELETE /devices/{chip_id} added to api.py.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | 1 session |
| Tasks | 2 planned + 3 bug fixes |
| Files modified | 3 |
| Files created | 1 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: GET /devices returns session_count | Pass | count_map built from sessions table, keyed by device_id = chip_id |
| AC-2: DELETE /devices/{chip_id} deregisters device | Pass | require_auth + coach_row_id ownership check; returns {"ok": true} |
| AC-3: Devices screen accessible from Athletes | Pass | ⚙ gear icon in AthletesScreen header → navigation.navigate('Devices') |
| AC-4: DevicesScreen shows info, rename, deregister | Pass | Card shows name, …chip_id[-8:], firmware, last active, session_count; inline TextInput on name tap; Remove → Alert → DELETE |

## Accomplishments

- New `DevicesScreen.js` (174 lines) — dark-themed, consistent with app palette (#000 bg, #1a1a1a cards); FlatList with empty state; optimistic updates for both rename and remove
- `GET /devices` now returns `session_count` integer per device (sessions.device_id = chip_id string)
- `DELETE /devices/{chip_id}` follows same auth pattern as existing PATCH endpoint; sessions rows untouched (orphaned device_id reference is harmless)
- Three post-APPLY bugs caught and fixed before UNIFY (see Deviations)

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/src/screens/DevicesScreen.js` | Created | iOS device management screen |
| `api.py` | Modified | session_count enrichment on GET /devices; DELETE /devices/{chip_id}; count query isolation |
| `swimnetics-mobile/src/screens/AthletesScreen.js` | Modified | ⚙ gear icon in header → Devices navigation |
| `swimnetics-mobile/App.js` | Modified | DevicesScreen import + Stack.Screen name="Devices" |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| session_count via separate query, not JOIN | Simpler than a Postgres JOIN across two tables via supabase-py; count_map is O(n) and sessions-per-coach is small | GET /devices is two queries instead of one |
| Deregister deletes device row only | sessions.device_id is a string field with no FK — orphaned reference is harmless; avoids accidental session deletion | Historical sessions retain their device_id for future analytics |
| onBlur-only rename (no onSubmitEditing) | iOS fires both onSubmitEditing and onBlur on keyboard Done → two PATCH calls | Rename fires exactly once per keyboard dismiss or tap-away |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 3 | All essential; no scope creep |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** Three bugs caught in post-APPLY review; all fixed inline before UNIFY.

### Auto-fixed Issues

**1. iOS TextInput double-fire (onSubmitEditing + onBlur)**
- **Found during:** Post-APPLY bug audit
- **Issue:** TextInput had both `onBlur` and `onSubmitEditing` calling `handleRename`. On iOS, pressing Return fires `onSubmitEditing` then `onBlur` in sequence → two PATCH /devices/{chipId} calls
- **Fix:** Removed `onSubmitEditing` from TextInput; `onBlur` alone covers both keyboard Done and tap-away
- **Files:** `DevicesScreen.js`

**2. FlatList missing extraData**
- **Found during:** Post-APPLY bug audit
- **Issue:** Without `extraData`, FlatList's item-equality optimization suppresses re-renders when `editingChipId` changes — tapping a device name would silently fail to show the TextInput
- **Fix:** Added `extraData={editingChipId}` to FlatList
- **Files:** `DevicesScreen.js`

**3. Session count query failure kills GET /devices**
- **Found during:** Post-APPLY bug audit
- **Issue:** The sessions count query was inside the same `try` block as the devices fetch. Any failure (RLS, empty table, network) would 500 the entire endpoint
- **Fix:** Separated count query into its own `try/except` with `count_map = {}` fallback; devices always returned, session_count defaults to 0 on count failure
- **Files:** `api.py`

## Next Phase Readiness

**Ready:**
- DevicesScreen is complete and wired into navigation
- DELETE /devices/{chip_id} available for any future bulk-management flows
- session_count per device available in GET /devices response

**Concerns:**
- EAS build still pending — iOS changes from Phases 14/15/17/18/19/20 not yet shipped to TestFlight
- Phase 20 is the last confirmed plan for the v0.5 milestone; remaining v0.5 work is Phase 16 (Freestyle Support) which is a research spike

**Blockers:** None

---
*Phase: 20-device-management, Plan: 01*
*Completed: 2026-06-09*
