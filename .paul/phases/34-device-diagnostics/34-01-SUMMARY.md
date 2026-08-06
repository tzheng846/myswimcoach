---
phase: 34-device-diagnostics
plan: 01
subsystem: firmware + ios
tags: [esp32, as5600, ble, diagnostics, react-native, i2c]

requires:
  - phase: 22-01
    provides: buffer-and-dump firmware + NUS TX/RX command pattern + length-based packet demux
  - phase: 21-01
    provides: BleContext singleton (useBle) + DevicesScreen
provides:
  - Firmware STATUS BLE command → 15-byte live-diagnostics packet (magnet/AGC/angle + state)
  - iOS DiagnosticsScreen (on-phone magnet/wiring + recording/buffer + link health)
  - PR-TICKETS.md (reviewer-ready, two repos)
affects: [device-bringup, field-support, any future on-phone hardware troubleshooting]

tech-stack:
  added: []
  patterns:
    - "STATUS packet length chosen to not collide with the existing length-based TX demux (8/1/×7)"
    - "STATUS marker byte 0xDD distinguishes status from the 0xEE end-of-dump marker"

key-files:
  created:
    - ../swimnetics-mobile/src/screens/DiagnosticsScreen.js
    - .paul/phases/34-device-diagnostics/PR-TICKETS.md
  modified:
    - ESP_32_V5/ESP_32_V5.ino
    - ../swimnetics-mobile/src/screens/DevicesScreen.js
    - ../swimnetics-mobile/App.js

key-decisions:
  - "In-app screen (not desktop tool) — matches the no-laptop-at-poolside thesis (user)"
  - "STATUS packet = 15 bytes, marker 0xDD — never collides with sample/META/end demux"
  - "PR creation skipped this plan; device checkpoint deferred to a later plan (user)"

patterns-established:
  - "Reuse the deferred-flag command pattern for any new BLE command (no I2C on the BLE task)"

duration: ~1 session
started: 2026-06-17T00:00:00Z
completed: 2026-06-17T00:00:00Z
---

# Phase 34 Plan 01: Device Diagnostics Summary

**On-phone Device Diagnostics — firmware `STATUS` BLE command (15-byte live AS5600/state packet) + an iOS Diagnostics screen that polls it and renders magnet/wiring, recording/buffer, and link health in plain English. Closes the "no recording found" black box.**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 of 4 done (Task 3 device checkpoint deferred) |
| Files modified | 3 modified, 2 created |
| Verification | iOS bundle exits 0 (1012 modules); firmware by structural review |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Firmware answers STATUS with the 15-byte packet | Pass (code) | Structural review — layout/marker/LE/disconnect-clear all present; no arduino-cli locally. On-device confirm deferred. |
| AC-2: Magnet/wiring legible on-phone | Pass (code) | `magnetVerdict()` maps MD/ML/MH → detected/not-detected/too-weak/too-strong; live angle + AGC. Bundles. |
| AC-3: Recording/buffer state shown | Pass (code) | recording/dataReady flags + `bufCount / maxSamples`; empty-buffer copy explains the failure. |
| AC-4: BLE link health shown | Pass (code) | device name + "last status Xs ago" freshness (stale > 3 s → red). |

All four pass at the code/bundle level; live on-device confirmation is the deferred Task 3.

## Accomplishments

- **Diagnosed the reported failure without new hardware:** the "quick flash → solid → no recording found" is the magnet-not-detected refusal in `startRecording()` (ESP_32_V5.ino) — firmware logged it only to USB serial. This plan surfaces it on the phone.
- Firmware `STATUS` command added via the existing deferred-flag pattern (no I2C on the BLE task), with a packet length (15) and marker (0xDD) that provably don't collide with the sample/META/end-of-dump demux.
- New iOS Diagnostics screen (polls ~2 Hz, parses only `len==15 && [0]==0xDD`, cleans up on unmount) reachable from Devices.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `ESP_32_V5/ESP_32_V5.ino` | Modified | `readAgc()`+`REG_AGC`; `STATUS_MARKER 0xDD`/`STATUS_PACKET_SIZE 15`; `pendingStatus` (set in RxCallbacks, cleared on disconnect, run in processPending); `sendStatus()`; header docs |
| `../swimnetics-mobile/src/screens/DiagnosticsScreen.js` | Created | Polls STATUS, parses the packet, renders magnet/buffer/connection cards |
| `../swimnetics-mobile/src/screens/DevicesScreen.js` | Modified | "🔧 Run Diagnostics" entry button |
| `../swimnetics-mobile/App.js` | Modified | `Diagnostics` nav route |
| `.paul/phases/34-device-diagnostics/PR-TICKETS.md` | Created | Two reviewer-ready PR tickets + byte contract + commands |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| In-app iOS screen, not a desktop BLE tool | No-laptop-at-poolside is the product thesis | Requires the firmware STATUS command + (for verify) a paid EAS build |
| STATUS = 15 bytes, marker 0xDD | Must not collide with META(8)/end(1)/samples(×7) length demux | Additive; existing parsers untouched |
| PR creation skipped this plan | User directive | PR-TICKETS.md kept as the ready-to-run artifact; nothing committed |
| Device checkpoint deferred to a later plan | User directive (EAS-credit gate) | ACs confirmed at code level only; on-device UAT is a separate future step |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 0 | — |
| Deferred | 2 | Task 3 device checkpoint → later plan; PR creation → skipped (artifact retained) |
| Auto-fixed | 1 | Replaced an inline `require()`-based back-button helper in DiagnosticsScreen with a top-level `TouchableOpacity` import (idiomatic, matches DevicesScreen) before the bundle check |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| No `arduino-cli` locally | Firmware verified by structural review (grep-confirmed all touchpoints + ordering); compile rides the reflash at the deferred checkpoint |

## Next Phase Readiness

**Ready:**
- Code shipped on both repos; iOS bundles clean. PR-TICKETS.md has copy-paste commands (firmware repo has a remote; iOS repo does not yet).

**Concerns:**
- iOS Diagnostics drill text/AGC interpretation is unverified against a real AS5600 reading until the device checkpoint runs.

**Blockers:**
- On-device verification gated on a paid EAS build + firmware reflash (the standing EAS-credit gate). Tracked as a deferred issue.
