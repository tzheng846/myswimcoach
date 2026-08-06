---
phase: 21-ble-persistence
plan: 02
subsystem: ui
tags: [react-native, ble-plx, buffer-and-dump, meta-dump, clock-correlation, ios]

requires:
  - phase: 21-ble-persistence (plan 01)
    provides: useBle() — connectedDevice, connectionStatus, knownDevices, connectToDevice
  - phase: 22-video-overlay-validation (plan 01)
    provides: firmware 1.1.0 META/DUMP protocol (8B meta, 0xEE end marker, 7B samples)
provides:
  - RecordingConfigScreen device picker (paired devices, tap-to-connect, gated Continue)
  - RecordScreen rebuilt on BleContext + buffer-and-dump retrieval
  - sessionStartPhoneMs clock correlation (displayed on results + console-logged)
  - device_id (chipId) sent to /process — fills sessions.device_id via Phase 14 auto-registration
affects: [22-02 demo-video validation, future offline-queue work]

tech-stack:
  added: []
  patterns:
    - Retrieval state machine - subscribe → META → DUMP → 0xEE → save/upload
    - uint32 modular clock math - (deviceNowUs - sessionStartUs + 2**32) % 2**32
    - Context-level disconnect watcher replaces per-screen onDisconnected wiring

key-files:
  created: []
  modified: [swimnetics-mobile/src/screens/RecordingConfigScreen.js, swimnetics-mobile/src/screens/RecordScreen.js]

key-decisions:
  - "RecordScreen targets buffer-and-dump, not the dead live-stream protocol (scope decision from planning)"
  - "Live velocity graph (Phase 13-03) removed — no live data exists in dump mode"
  - "On-device checkpoint DEFERRED: EAS build credits exhausted; structural verification only"

patterns-established:
  - "All BLE consumers go through useBle(); only BleContext instantiates BleManager"

duration: ~45min (code); checkpoint deferred
started: 2026-06-10T00:00:00Z
completed: 2026-06-10T00:00:00Z
---

# Phase 21 Plan 02: Device Picker + Buffer-and-Dump RecordScreen Summary

**RecordingConfigScreen picks among paired devices via BleContext; RecordScreen rebuilt for firmware 1.1.0 — remote Start/Stop, META clock correlation (`sessionStartPhoneMs`), DUMP retrieval with stall guard, and `device_id` finally sent on upload. On-device verification DEFERRED (EAS build credits exhausted).**

## Performance

| Metric | Value |
|--------|-------|
| Completed | 2026-06-10 (code); device UAT pending |
| Tasks | 2 of 2 auto complete; checkpoint deferred by user |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Device picker in RecordingConfig | Pass (code) / **UAT deferred** | Rows from knownDevices, tap-to-connect, Continue gated |
| AC-2: RecordScreen has no BLE plumbing | Pass (code) | Grep: `new BleManager` only in BleContext.js; no scan UI; context disconnect watcher |
| AC-3: Remote record drives device | Pass (code) / **UAT deferred** | START/STOP writes with 3s timeout race; elapsed timer UI |
| AC-4: Retrieval with clock correlation | Pass (code) / **UAT deferred** | META→sessionStartPhoneMs (modular u32), DUMP→0xEE, 30s stall guard, no-session alert |
| AC-5: device_id reaches backend | Pass (code) / **UAT deferred** | `parameters.device_id = chipId` in uploadAndProcess |

**⚠ DEFERRED VERIFICATION:** the blocking checkpoint (EAS build + on-device end-to-end) was
not executed — **EAS build credits exhausted**. All ACs verified at code/structure level only.
Run the checkpoint procedure (in 21-02-PLAN.md Task 3) when credits renew, before the
22-02 demo-video session — the demo depends on this exact build.

## Accomplishments

- One pair, zero rescans: RecordScreen never scans; connection state lives in context
- The iOS half of the video-sync architecture is code-complete: `sessionStartPhoneMs` computed at retrieval and surfaced for the overlay workflow
- `sessions.device_id` will populate on the first upload from this build (Phase 14 auto-registration path, dormant since June 8)

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/screens/RecordingConfigScreen.js` | Modified | DEVICE section (picker/connect/gate); stroke/name/notes untouched |
| `src/screens/RecordScreen.js` | Rewritten | BleContext consumer; buffer-and-dump retrieval; live graph + own BleManager + scan UI removed |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Checkpoint deferred (user) | No EAS build credits | Phase closes with UAT debt; tracked in Deferred Issues |
| Live graph removed | Dump mode has no in-swim data | Phase 13-03 feature retired; revisit only if live streaming returns as a mode |
| STOP→META race accepted as safe | Firmware processes record-stop before META within one loop pass | No app-side delay needed between STOP and retrieval |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Checkpoint deferred | 1 | On-device ACs unverified until build credits renew |

No code deviations — tasks executed as written.

## Next Phase Readiness

**Ready:**
- 22-02 (demo-video validation) can be planned now; its procedure consumes this build's results screen output

**Concerns / blockers for 22-02 execution (not planning):**
- **EAS build credits exhausted** — the entire on-device chain (Phases 12–21 changes since the Phase 11 build) is untested on hardware
- ffmpeg/ffprobe not installed on the dev machine (needed for video creation_time)

---
*Phase: 21-ble-persistence, Plan: 02*
*Completed: 2026-06-10 (code complete; device UAT deferred)*
