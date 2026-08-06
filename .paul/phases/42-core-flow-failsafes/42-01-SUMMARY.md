---
phase: 42-core-flow-failsafes
plan: 01
subsystem: ui
tags: [ios, react-native, ble, error-handling, failsafes, upload-retry, status-packet]

requires:
  - phase: 34-device-diagnostics
    provides: STATUS BLE packet + parseStatus/magnetVerdict (now extracted to a shared lib)
  - phase: 21-ble-persistence
    provides: BleContext (connect/forget/disconnect, known-device store)
  - phase: 26-in-app-video-overlay
    provides: RecordScreen video path (CameraView + onCameraReady)
provides:
  - Pairing failsafes (BLE-off/permission detection, connect timeout + auto-retry, specific reasons)
  - Recording failsafes (pre-record encoder STATUS check warn+override, plain-start connection guard)
  - Results failsafes (upload Retry on the saved CSV with specific reasons; report-card load-reason branching + Retry)
  - Shared src/lib/deviceStatus.js + src/lib/friendlyError.js
affects: [ios-record-flow, ios-pairing, future-eas-build-verification, offline-upload-queue]

tech-stack:
  added: []
  patterns:
    - "friendlyError.js: central BLE/upload error → coach-readable reason mapper"
    - "deviceStatus.js: single source of truth for STATUS-packet decode (shared Diagnostics + pre-record check)"
    - "auto-recover-first then specific-reason failure UX across all three core flows"

key-files:
  created:
    - swimnetics-mobile/src/lib/friendlyError.js
    - swimnetics-mobile/src/lib/deviceStatus.js
  modified:
    - swimnetics-mobile/src/context/BleContext.js
    - swimnetics-mobile/src/screens/DevicesScreen.js
    - swimnetics-mobile/src/screens/RecordingConfigScreen.js
    - swimnetics-mobile/src/screens/RecordScreen.js
    - swimnetics-mobile/src/screens/DiagnosticsScreen.js
    - swimnetics-mobile/src/screens/ReportCardScreen.js

key-decisions:
  - "Pre-record magnet check WARNS + allows override (Record-anyway/Cancel), never hard-blocks — STATUS can false-negative"
  - "If STATUS can't be read in 2s, proceed (don't block) — the START write still catches a real disconnect"
  - "Upload failsafe = saved CSV + Retry button + specific reason; NO background queue this pass (user decision)"
  - "Mid-record BLE drop handling already existed — built on it, did not duplicate; video path stays excluded by prior design"
  - "Connect timeout 10s + ONE auto-retry; connectToDevice throws an already-mapped friendly reason"

patterns-established:
  - "All BLE entry points pre-check ensureBleReady() before scan/connect"
  - "Error renders branch on whether a recoverable artifact (savedPath) exists → Retry vs Try-Again"

duration: ~40min
started: 2026-06-22T01:15:00Z
completed: 2026-06-22T01:55:00Z
---

# Phase 42 Plan 01: Core-Flow Failsafes (iOS) Summary

**Pairing, recording, and results-checking now each auto-recover or fail with a specific, actionable reason — connect can't hang (10s timeout + retry), Bluetooth-off/permission are named, a bad encoder warns before arming, and a failed upload offers Retry on the saved CSV so no session is ever lost.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~40 min |
| Started | 2026-06-22T01:15:00Z |
| Completed | 2026-06-22T01:55:00Z |
| Tasks | 3 auto completed |
| Files | 2 created, 6 modified |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Pairing fails specifically, never hangs | Pass (code) | `ensureBleReady` (off/permission) pre-checks scan+connect; `connectToDevice` 10s timeout + 1 auto-retry; empty scan → "No SwimLogger found"; scan errors surfaced via `bleReason`. |
| AC-2: Recording guards start + surfaces drops | Pass (code) | `checkEncoder` STATUS round-trip → warn + Record-anyway/Cancel on hard fault; plain-start connection guard added. Mid-record drop handler pre-existed (L141) — stops timer, "session retained on device, reconnect+Retrieve". |
| AC-3: Failed upload never strands a session | Pass (code) | `uploadAndProcess` classifies offline/server/parse via `uploadReason`; error state shows Retry-Upload re-sending `savedPath` (no re-record). |
| AC-4: Report-card load failures specific + retryable | Pass (code) | `fetchSession` branches not-found (PGRST116) / incomplete metrics_json / offline / generic; cancel-safe; `reloadKey` Retry button. |

**Note:** All ACs verified at code/bundle level (`expo export` exit 0 ×3). Actual failure-path behavior (BLE off, real timeout, magnet absent, network loss) is **deferred to the next EAS build** — no new native deps, but these are hardware/network conditions.

## Accomplishments

- The infinite connect spinner is eliminated (10s timeout + one auto-retry), and every pairing failure now names its cause instead of failing silently.
- A failed upload can no longer lose a session — the saved CSV is re-sendable via a Retry button with a clear offline/server reason.
- STATUS-packet decode is now a single shared source of truth (`deviceStatus.js`), consumed by both Diagnostics and the new pre-record encoder check.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/lib/friendlyError.js` | Created | `bleStateReason` / `bleReason` / `uploadReason` mappers |
| `src/lib/deviceStatus.js` | Created | Shared `parseStatus` / `magnetVerdict` (+`hardFault`) + STATUS consts |
| `src/context/BleContext.js` | Modified | `ensureBleReady` + connect timeout/retry + mapped-reason throw |
| `src/screens/DevicesScreen.js` | Modified | Pre-scan readiness, scan-error/empty-scan messaging (`pairMsg`) |
| `src/screens/RecordingConfigScreen.js` | Modified | Pre-connect readiness check |
| `src/screens/RecordScreen.js` | Modified | `checkEncoder` + connection guard + upload reason/Retry |
| `src/screens/DiagnosticsScreen.js` | Modified | Imports STATUS helpers from the lib (dupes deleted) |
| `src/screens/ReportCardScreen.js` | Modified | Load-reason branching + Retry, cancel-safe fetch |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Pre-record check warns + overrides (no hard block) | STATUS can false-negative; shouldn't stop a real session | Coach keeps control; prevents the "recorded nothing" surprise without blocking |
| STATUS-unreadable → proceed | A flaky 2s read shouldn't block; START still guards a true disconnect | No new failure mode introduced |
| No background upload queue | User decision — keep this pass focused; data already saved locally | Full PROJECT.md queue stays a future effort |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope reductions | 1 | Net-positive (less new code) |
| Deferred | 1 | Device verification → next EAS build |

- **Mid-record drop already implemented:** the plan scoped a new `linkDropped` banner, but `RecordScreen` already had a disconnect watcher (L141) that stops the timer and shows "session retained on the device — reconnect and tap Retrieve." It satisfies AC-2, so I built on it instead of duplicating. The deliberate `videoRecording` exclusion (camera keeps filming) was preserved.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Extracting STATUS helpers risked dangling refs in DiagnosticsScreen | Grep confirmed `STATUS_MARKER`/`*_BIT` were only used in the moved functions; kept `NUS_*`/`POLL_INTERVAL_MS`/`STALE_MS` local; export green |

## Next Phase Readiness

**Ready:**
- All three flows code-complete + export-green; two reusable helper libs in place.
- `friendlyError.uploadReason` already structured to slot a future offline upload queue on top.

**Concerns:**
- Device verification is the real proof — these are failure paths only triggerable on hardware/network (BLE off, timeout, magnet absent, network loss). Batch with the Phase 38/39/41 deferred device checks on the next EAS build.
- `checkEncoder` adds one BLE round-trip (~≤2s) before arming a recording — confirm it doesn't feel laggy on-device.

**Blockers:** None.

---
*Phase: 42-core-flow-failsafes, Plan: 01*
*Completed: 2026-06-22*
