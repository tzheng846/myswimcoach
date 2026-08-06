---
phase: 55-athlete-flow-fixes
plan: 01
subsystem: ui
tags: [react-native, react-navigation, expo, useFocusEffect, nested-navigation, ios]

requires:
  - phase: 51-api-correctness
    provides: working POST /athletes — athlete creation had to succeed before these defects were reachable
  - phase: 54-gate-removal
    provides: ratings.py threshold fallback (live in dedac17) + the isAnalyticsReady one-liner this plan shipped
provides:
  - record screen roster that refetches on focus instead of at app launch
  - working Root-stack → Tab navigation for the athlete Record button
  - route params applied (and cleared) after mount on a never-remounting tab screen
  - Phase 54-01's freestyle unlock, finally carried into an EAS build
affects: [mobile navigation, any future tab-screen data fetching, freestyle analytics work]

tech-stack:
  added: []
  patterns:
    - "Tab screens never remount: refetch with useFocusEffect, read params in an effect, never in a useState initializer"
    - "Root-stack → Tab navigation requires navigate('Tabs', { screen, params }); the bare name fails silently"

key-files:
  created: []
  modified:
    - swimnetics-mobile/src/screens/RecordingConfigScreen.js
    - swimnetics-mobile/src/screens/AthleteDetailScreen.js
    - swimnetics-mobile/src/navigation/RootTabs.js

key-decisions:
  - "Resolve head_waist_m from the roster row, not from a params payload — AthleteDetail's hw is a possibly-mid-edit TextInput string"
  - "Clear route params after consuming them — mandatory on a screen that never unmounts, or the next tab press inherits the previous athlete"
  - "Fix the RootTabs comment rather than restructure the navigators — moving AthleteDetail into the tab navigator would change presentation for every screen pushed over the tab bar"
  - "Verify, not re-edit, ReportCardScreen — 54-01 already wrote the one-liner"

patterns-established:
  - "Data-bearing tab screens use useFocusEffect + useCallback; all four now do"
  - "RootTabs.js documents the Root→Tab nested-navigate rule at the navigator definition, where the mistake gets made"

duration: ~50min
started: 2026-08-05
completed: 2026-08-05
---

# Phase 55 Plan 01: Athlete Flow Fixes Summary

**Adding or deleting an athlete now reflects on the record screen without an app restart, and the Record button on an athlete's page navigates for the first time since Phase 38-03 — both traced to one fact: `RecordingConfig` is a tab screen that never remounts.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~50 min (discuss → plan → apply → verify) |
| Tasks | 3 completed, 1 checkpoint approved |
| Files modified | 3 edited, 1 verify-only |
| Deviations | 0 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Roster reflects changes without restart | **Partial** | Add ✓. Delete ✓ in the dropdown, but the *selection bar* keeps the deleted athlete — see Deferred |
| AC-2: Record button reaches the record screen | **Pass** | Athlete pre-selected, stroke defaulted |
| AC-3: Tab press doesn't inherit previous athlete | **Pass** | The param-clear works; this path had never executed before today |
| AC-4: Freestyle analytics render on the build | **Pass** | Verified on device |

## Accomplishments

- **Diagnosed three symptoms down to one cause.** `RecordingConfig` is a tab screen (`RootTabs.js:29`), so it mounts once per app launch and never remounts. `useEffect(…,[])` runs once ever → frozen roster. `useState()` initializers run once ever → params ignored. It lives under `Tabs`, not Root → unreachable by bare name from `AthleteDetail`.
- **Caught a second half of B2 at plan time that the symptom hid.** Fixing only the `navigate()` call would have shipped a Record button that navigates to an *empty picker*, because params are read in `useState` initializers that never re-run. Both halves were needed; only one was visible from the bug report.
- **Turned the stale comment into the guardrail.** `RootTabs.js:21` had asserted that cross-screen navigation "keeps working" — the exact assumption that produced the bug. It now documents the Root→Tab rule, warns that getting it wrong fails *silently*, and states the never-remounts constraint.
- **Cleared a build backlog.** The EAS build carried six previously-deferred iOS checks (47-03, 41, 42, 44-03, 21-02, 34-01) alongside this work.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/src/screens/RecordingConfigScreen.js` | Modified | Roster `useEffect(…,[])` → `useFocusEffect` + `useCallback`; new effect applying and clearing route params |
| `swimnetics-mobile/src/screens/AthleteDetailScreen.js` | Modified | `:140` bare navigate → `navigate('Tabs', { screen, params })` |
| `swimnetics-mobile/src/navigation/RootTabs.js` | Modified | `:21` comment rewritten to state the Root→Tab rule and the never-remounts constraint |
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | Verified only | 54-01's `isAnalyticsReady = true` intact; all 6 usage sites + the `!isAnalyticsReady` branch retained |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Resolve `head_waist_m` from the roster row, not params | `AthleteDetail`'s `hw` is a TextInput string that may be mid-edit | Recording gets the DB value; one less param to keep in sync |
| Clear params after consuming them | On a never-unmounting screen params persist forever, so a later plain tab press would silently inherit the athlete | Became AC-3; a problem *created by* applying params post-mount, so in-scope cleanup |
| Fix the comment, not the navigator tree | Moving `AthleteDetail` into the tab navigator would also work but changes presentation for every screen pushed over the tab bar | Minimal blast radius |
| Verify rather than re-edit `ReportCardScreen` | 54-01 already wrote it; re-editing risks diverging from its documented one-line revert | Gate stays trivially reversible |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 1 | Recorded below, user-directed |

**Total impact:** none — plan executed exactly as written.

### Deferred Items

**1. Deleting the currently-selected athlete leaves them in the selection bar**
- **Found during:** the human-verify checkpoint (AC-1 delete)
- **Issue:** `athlete` (the selected one) is state independent of `athletes` (the list). The new `useFocusEffect` refetches the *list* only and never revalidates the selection against it, so a stale selected object survives. The dropdown is correct; only the selection display is wrong.
- **Why it matters beyond cosmetics:** recording while that stale selection shows would submit a deleted `athlete_id` — failing at `/process` or orphaning the session. Low likelihood (you must delete the athlete you are about to record) but it is a data path, not a display quirk.
- **Fix:** one line inside the effect that already exists — after `setAthletes(rows)`, `setAthlete(null)` when `athlete?.id` is absent from `rows`.
- **Status:** deliberately NOT applied. User: "just note this, no need to change right now."

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| EAS build scope — 13 modified + 7 untracked paths in the mobile repo, much of it the only copy | `.easignore` excludes only build artifacts, so EAS likely uploads the working directory rather than a git archive — but recommended committing regardless to remove doubt and protect the only copies. User committed before building. |

## Next Phase Readiness

**Ready:**
- All four data-bearing tab screens now refetch on focus — the pattern is uniform.
- `RootTabs.js` documents the navigation rule at the definition site, so the next Root-stack screen that needs a tab won't repeat this.
- Six deferred iOS checks cleared on the same build.

**Concerns:**
- The deferred selection-bar staleness above is the only known gap in this phase's surface.
- `useFocusEffect` refetches the roster on every tab focus. Fine at current roster sizes; revisit only if a team gets large enough for it to be felt.

**Blockers:** None.

---
*Phase: 55-athlete-flow-fixes, Plan: 01*
*Completed: 2026-08-05*
