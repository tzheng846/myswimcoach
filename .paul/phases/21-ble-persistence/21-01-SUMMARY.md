---
phase: 21-ble-persistence
plan: 01
subsystem: ui
tags: [react-native, ble-plx, react-context, expo-secure-store, ios]

requires:
  - phase: 14-device-registration
    provides: chip_id convention; "SwimLogger-XXXXXX" BLE name (firmware)
provides:
  - BleContext (src/context/BleContext.js) — BleManager singleton, connectionStatus,
    knownDevices persisted to SecureStore, connectToDevice/forgetDevice/disconnect
  - BleProvider wrapping NavigationContainer (App.js)
  - DevicesScreen "Pair New Device" scan + PAIRED DEVICES section
affects: [21-02 RecordScreen refactor, 22-02 retrieval flow]

tech-stack:
  added: []
  patterns:
    - BLE state lifted above the navigation stack via React Context
    - SecureStore as the app-wide persistence layer (same adapter pattern as supabase.js)
    - chipId derived from BLE name prefix "SwimLogger-"

key-files:
  created: [swimnetics-mobile/src/context/BleContext.js]
  modified: [swimnetics-mobile/App.js, swimnetics-mobile/src/screens/DevicesScreen.js]

key-decisions:
  - "expo-secure-store instead of AsyncStorage — already installed, matches supabase.js pattern, no new native dep / no EAS rebuild required"
  - "manager exposed on context value so DevicesScreen can drive scans; not exported at module level"

patterns-established:
  - "useBle() hook for all BLE consumers; RecordScreen migrates in 21-02"

duration: ~30min (verification/reconciliation; implementation pre-existed from 2026-06-09 session)
started: 2026-06-10T00:00:00Z
completed: 2026-06-10T00:00:00Z
---

# Phase 21 Plan 01: BleContext + Pair Flow Summary

**Shared BleContext (BleManager singleton, SecureStore-persisted known devices, AppState foreground re-check) wired above the navigation stack, with a Pair New Device scan flow in DevicesScreen — implementation pre-existed from the 06-09 session; this session verified it against the plan and closed the loop.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min this session (reconciliation); implementation written 2026-06-09 |
| Completed | 2026-06-10 |
| Tasks | 2 of 2 verified |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Connection survives navigation | Pass (code-level) | State lives in BleProvider above the stack; on-device confirmation awaits next EAS build |
| AC-2: Connection survives background/foreground | Pass (code-level) | AppState listener re-checks isConnected() on 'active' |
| AC-3: Known devices persisted | Pass (code-level) | SecureStore key `swimnetics_known_devices`, loaded on mount |
| AC-4: DevicesScreen pair flow | Pass (code-level) | Scan (8 s, SwimLogger prefix, dedupe) → tap → connectToDevice → paired list with connected dot + Forget |

All four ACs are behavioral; code structure fully implements them, but live confirmation requires
an iPhone build — none exists past Phase 11 (tracked deferred item). Run /paul:verify after the next EAS build.

## Accomplishments

- BLE connection state decoupled from RecordScreen's component lifecycle — the prerequisite for both 21-02 (RecordScreen refactor) and 22-02 (dump retrieval)
- Pair-once UX: scan lives in DevicesScreen, devices persist across app restarts
- chipId extraction from the `SwimLogger-<chipID>` name — same convention firmware 1.1.0 (Phase 22-01) advertises

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/context/BleContext.js` | Created | BleManager singleton, connection state, knownDevices persistence, connect/forget/disconnect |
| `App.js` | Modified | BleProvider wraps NavigationContainer (inside AuthProvider) |
| `src/screens/DevicesScreen.js` | Modified | PAIRED DEVICES section, Pair New Device scan flow; Supabase device cards untouched |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| SecureStore instead of AsyncStorage | Already in package.json and the binary; same adapter pattern as supabase.js; AsyncStorage would add a native dep requiring a new build | No dependency change; knownDevices payload is tiny (well under keychain size limits) |
| `pairConnecting` state (beyond spec) | Spinner on the row being connected | Minor UX addition, no scope risk |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Substitution | 1 | SecureStore for AsyncStorage — improvement, not drift |
| Scope additions | 1 | pairConnecting spinner |
| Deferred | 0 | — |

**Total impact:** None negative. Plan executed faithfully with a storage-layer substitution that avoids a native rebuild.

### Process note

The implementation was written in the 2026-06-09 session but APPLY was never verified/closed —
STATE.md was left at "plan created, awaiting approval." This session's APPLY was reconciliation:
verified every plan check against the existing code (no changes needed) and closed the loop.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Stale STATE.md (said plan unapplied; code existed) | Reconciled — verified code against plan instead of re-implementing |

## Next Phase Readiness

**Ready:**
- `useBle()` provides everything 21-02 needs: connectedDevice, connectionStatus, knownDevices, connectToDevice
- 22-02 retrieval flow can read the connected device from context

**Concerns:**
- Two module-level BleManager instances exist (BleContext + RecordScreen legacy) until 21-02 removes RecordScreen's — functional but redundant
- On-device AC validation pending next EAS build (no build since Phase 11)
- RecordScreen still scan-filters on exact name 'SwimLogger' — fails against firmware 1.1.0's "SwimLogger-XXXXXX"; 21-02/22-02 must fix

**Blockers:** None

---
*Phase: 21-ble-persistence, Plan: 01*
*Completed: 2026-06-10*
