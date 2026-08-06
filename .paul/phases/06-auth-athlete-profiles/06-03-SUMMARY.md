---
phase: 06-auth-athlete-profiles
plan: 03
subsystem: ui
tags: [supabase, rls, react-navigation, fastapi, athletes, sessions, keyboard-avoiding, ios]

requires:
  - phase: 06-02
    provides: AuthContext with session/coachId/teamId; Supabase client on iOS; authenticated /process

provides:
  - "AthletesScreen: list team athletes from Supabase, add athlete inline"
  - "Athlete-keyed RecordScreen: receives athleteId/athleteName/strokeType via route params"
  - "Session row inserted to Supabase after each successful upload"
  - "Back navigation: ‹ Athletes button returns to roster without signing out"
  - "Results-state disconnect watcher: device drop handled gracefully after session ends"
  - "FastAPI /process: required auth (401 without Bearer token)"
  - "RLS patch: WITH CHECK added to athletes + sessions policies (INSERT now enforced)"

affects: [06-device-qr, 07-billing]

tech-stack:
  added: []
  patterns:
    - "await fetchCoachProfile before setLoading(false) — ensures teamId populated at first render"
    - "KeyboardAvoidingView with behavior='padding' on iOS for bottom-of-screen forms"
    - "Results-state disconnect watcher: re-register onDisconnected after upload succeeds"
    - "supabase.from().insert().then() fire-and-forget — non-blocking session save after results shown"
    - "RLS FOR ALL needs both USING (read) and WITH CHECK (write) — USING alone ignored for INSERT"

key-files:
  created:
    - swimnetics-mobile/src/screens/AthletesScreen.js
    - myswimcoach/supabase/patch_01_rls_with_check.sql
  modified:
    - swimnetics-mobile/src/context/AuthContext.js
    - swimnetics-mobile/src/screens/RecordScreen.js
    - swimnetics-mobile/App.js
    - myswimcoach/api.py
    - myswimcoach/supabase/schema.sql

key-decisions:
  - "await fetchCoachProfile before loading=false: guarantees teamId non-null when AthletesScreen mounts"
  - "RLS WITH CHECK required for INSERT: USING alone silently ignored by PostgreSQL for INSERT operations"
  - "Results-state disconnect watcher: re-register after stopRecording() clears it, so device drop is handled"
  - "Back button instead of native header: headerShown=false requires manual navigation.goBack()"

patterns-established:
  - "All Supabase INSERT policies need WITH CHECK (not just USING) to enforce team isolation on writes"
  - "fetchCoachProfile must complete before loading gate lifts — always await it in getSession().then()"
  - "After stopRecording() clears disconnectRef, re-register a light watcher in results state"

duration: ~2h (including 4 post-verification bug fixes)
started: 2026-05-22T14:00:00Z
completed: 2026-05-22T16:00:00Z
---

# Phase 6 Plan 03: Athlete Roster + Session Save Summary

**Athlete roster screen with inline add, athlete-keyed recordings saved to Supabase sessions table, and FastAPI /process locked to authenticated coaches.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2 hours |
| Completed | 2026-05-22 |
| Tasks | 3 of 3 complete (2 auto + 1 human-verify) |
| Post-verify bug fixes | 4 |
| Files created/modified | 7 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Athletes list loads from Supabase | Pass | Verified on iPhone |
| AC-2: Add athlete persists to Supabase | Pass | Row confirmed in Table Editor |
| AC-3: Athlete tap → RecordScreen with name | Pass | Blue athlete name shows below title |
| AC-4: Session saved to Supabase after upload | Pass | Row with athlete_id + metrics_json confirmed |
| AC-5: /process returns 401 without auth | Pass | Confirmed via curl before EAS build |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/src/screens/AthletesScreen.js` | Created | Roster list + inline add form |
| `swimnetics-mobile/src/context/AuthContext.js` | Modified | await fetchCoachProfile; clear on sign out |
| `swimnetics-mobile/src/screens/RecordScreen.js` | Modified | route params, session save, back button, disconnect watcher |
| `swimnetics-mobile/App.js` | Modified | Athletes as initial AppStack screen |
| `myswimcoach/api.py` | Modified | optional_auth → require_auth |
| `myswimcoach/supabase/schema.sql` | Modified | WITH CHECK added to athletes + sessions policies |
| `myswimcoach/supabase/patch_01_rls_with_check.sql` | Created | Live patch SQL for Supabase dashboard |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| await fetchCoachProfile before loading=false | teamId was null at first render, silently blocking Save | teamId guaranteed populated when AthletesScreen mounts |
| RLS WITH CHECK on athletes + sessions | USING alone is silently ignored by PostgreSQL for INSERT — any authenticated user could insert into other teams | Schema patched; future RLS policies must always include WITH CHECK for INSERT |
| Results-state disconnect watcher | stopRecording() clears disconnectRef; without a new watcher the device drop is silent until user taps something | Device drop now handled immediately in results state |
| navigation.goBack() back button | headerShown=false hides native back; no way to return to roster | ‹ Athletes button added to RecordScreen header |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 4 | All essential; no scope creep |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** All fixes were direct consequences of code-review findings and device testing. No scope creep.

### Auto-fixed Issues

**1. Save button did nothing (teamId null at render)**
- **Found during:** Task 3 checkpoint (user testing)
- **Issue:** `handleAdd` silently returns when `teamId` is null. `fetchCoachProfile` was async but not awaited in `getSession().then()`, so `loading` went false before `teamId` was set.
- **Fix:** Changed `getSession().then(async ...)` and `await fetchCoachProfile(session)` before `setLoading(false)`
- **Files:** `AuthContext.js`

**2. Keyboard covered add form**
- **Found during:** Task 3 checkpoint (user testing)
- **Issue:** Add form sits at bottom of screen with no keyboard avoidance on iOS
- **Fix:** Wrapped AthletesScreen content in `KeyboardAvoidingView behavior="padding"`
- **Files:** `AthletesScreen.js`

**3. RLS INSERT not enforced (WITH CHECK missing)**
- **Found during:** Code audit between tasks
- **Issue:** `FOR ALL USING (...)` on athletes and sessions policies — USING is silently ignored for INSERT in PostgreSQL. Any authenticated user could insert rows for other teams.
- **Fix:** Added `WITH CHECK` clause matching the USING condition; schema.sql updated; patch_01 SQL file created and run in Supabase dashboard
- **Files:** `supabase/schema.sql`, `supabase/patch_01_rls_with_check.sql`

**4. No back navigation; disconnect not handled in results state**
- **Found during:** Task 3 checkpoint (user testing)
- **Issue 1:** headerShown=false hides native back — no way to return to AthletesScreen
- **Issue 2:** stopRecording() clears disconnectRef; device drop in results state was silent
- **Fix 1:** Added `navigation` prop + `‹ Athletes` TouchableOpacity calling `navigation.goBack()`
- **Fix 2:** Re-register `onDisconnected` watcher after setting results state in `uploadAndProcess`
- **Files:** `RecordScreen.js`

## Next Phase Readiness

**Ready:**
- Full coach flow works: login → select athlete → record → session in Supabase
- /process enforces auth — no anonymous uploads possible
- RLS correctly enforces team isolation on all INSERT operations
- Back navigation and disconnect UX are clean

**Concerns:**
- `device_id` is NULL on all sessions — device QR claim (06-04) will populate this
- No session history view in the app — athletes only show name/stroke, not past sessions
- Raw CSVs still accumulate on device — purge after upload deferred

**Blockers:** None

---
*Phase: 06-auth-athlete-profiles, Plan: 03*
*Completed: 2026-05-22*
