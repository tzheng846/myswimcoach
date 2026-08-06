---
phase: 05-ios-testflight
plan: 02
subsystem: ui
tags: [react-native, ble, react-native-ble-plx, nordic-uart, expo-file-system, buffer]

requires:
  - phase: 05-01
    provides: EAS Build pipeline, dev client installed on iPhone

provides:
  - "RecordScreen.js — full BLE state machine with debug log panel"
  - "Raw encoder CSV saved to device DocumentDirectory on session stop"
  - "Expo dev client + tunnel for fast JS iteration without rebuilding"

affects: [05-03-upload-chart]

tech-stack:
  added: [react-native-ble-plx@3.5.1, buffer@6.0.3, expo-dev-client@56.0.14, @expo/ngrok]
  patterns:
    - "BLE state machine: idle→scanning→connecting→connected→recording→saving→done/error"
    - "isStoppingRef guard prevents double-stop on concurrent callbacks"
    - "Subscribe to notifications BEFORE sending START command"
    - "writeCharacteristicWithResponseForService for [write-resp] characteristics"
    - "expo-file-system/legacy import for SDK 56 compatibility"

key-files:
  created: [swimnetics-mobile/src/screens/RecordScreen.js]
  modified: [swimnetics-mobile/App.js, swimnetics-mobile/package.json, swimnetics-mobile/eas.json, swimnetics-mobile/app.json]

key-decisions:
  - "Use writeCharacteristicWithResponseForService for RX char (not without-response — device requires ACK)"
  - "Subscribe before sending START — device may begin streaming immediately on subscription"
  - "expo-file-system/legacy not expo-file-system — writeAsStringAsync deprecated in SDK 56"
  - "isStoppingRef ref (not state) to guard double-stop without re-render"
  - "Error code 2 (OperationCancelled) is expected on Stop — suppress, don't call stopRecording"
  - "dev client profile: distribution:internal skips TestFlight for fast install"

patterns-established:
  - "BLE callbacks are outside React lifecycle — use refs for mutable state, setSampleCount with functional updater"
  - "parsePacket returns {samples, error} — never throws — all error paths logged"
  - "Debug log panel: setDebugLog(prev => [...prev, entry]) — append-only, always visible"

duration: ~4h (including 3 debugging iterations)
started: 2026-05-22T00:00:00Z
completed: 2026-05-22T00:00:00Z
---

# Phase 5 Plan 02: BLE Recording Summary

**React Native BLE recording screen connecting to SwimLogger via Nordic UART, streaming encoder packets at ~270 Hz, and saving raw CSV to on-device storage — verified on hardware.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~4 hours |
| Completed | 2026-05-22 |
| Debug iterations | 3 |
| Tasks | 2 of 2 complete (1 auto + 1 human-verify) |
| Files modified | 5 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: BLE scan discovers SwimLogger | Pass | Found via name filter within 8s scan window |
| AC-2: Recording streams live sample count | Pass | Counter increments on screen in real time |
| AC-3: Stop saves valid CSV | Pass | session_<timestamp>.csv in DocumentDirectory, count > 0 |
| AC-4: Errors surface, not crash | Pass | Debug log panel shows all errors; partial CSV saved on disconnect |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 5 | All essential, no scope creep |
| Scope additions | 1 | Debug log panel (diagnostic tool, minimal overhead) |
| Deferred | 1 | CSV read-back verification in log |

### Auto-fixed Issues

**1. Wrong write method for RX characteristic**
- **Issue:** RX char is `[write-resp]` but plan used `writeCharacteristicWithoutResponseForService` — device silently dropped START command, no data streamed
- **Fix:** `writeCharacteristicWithResponseForService` for both START and STOP
- **Discovered via:** debug log showing "START sent" but zero samples

**2. Double `stopRecording` call**
- **Issue:** Removing subscription fires `onData(error, null)` with code 2 (OperationCancelled), which called `stopRecording(true)` on top of the tap calling `stopRecording(false)` → two CSVs written
- **Fix:** `isStoppingRef` ref guard at top of `stopRecording`; code 2 errors suppressed in callback

**3. `expo-file-system` deprecated API**
- **Issue:** `writeAsStringAsync` removed from `expo-file-system` in SDK 56
- **Fix:** `import * as FileSystem from 'expo-file-system/legacy'`

**4. Stale `disconnectRef` after `reset()`**
- **Issue:** `reset()` didn't remove disconnect subscription — stale callback could fire and push UI to error state after reset
- **Fix:** Added `disconnectRef.current?.remove()` to `reset()`

**5. `autoIncrement` build number collision**
- **Issue:** Remote version counter initialized to 1, colliding with prior build number 1
- **Fix:** Rebuilt — autoIncrement correctly incremented to 2 on next build

### Scope Addition

**Debug log panel** — persistent on-screen log with colour-coded levels (ok/warn/error). Not in original plan. Added during debugging iteration 1; retained in final build as it has zero performance impact and is essential for field diagnostics.

### Deferred Items

- CSV read-back in debug log (show first row after save to confirm on-disk validity). Deferred to Plan 05-03 where the file is uploaded anyway.

## Key Protocol Facts (for Plan 05-03)

```
NUS Service:  6E400001-B5A3-F393-E0A9-E50E24DCCA9E
TX (notify):  6E400003-B5A3-F393-E0A9-E50E24DCCA9E  device → phone
RX (write):   6E400002-B5A3-F393-E0A9-E50E24DCCA9E  phone → device [write-resp]
Packet:       14 bytes = 2 samples × 7 bytes (<IHB at offsets 0, 7)
Commands:     START\n and STOP\n via writeWithResponse
CSV columns:  timestamp_us, angle_counts, magnet_ok
Save path:    FileSystem.documentDirectory + 'session_<timestamp>.csv'
```

## Next Phase Readiness

**Ready:**
- CSV file exists at `FileSystem.documentDirectory + 'session_<timestamp>.csv'` after every session
- Plan 05-03 reads this path (from `savedPath` state) and POSTs it to FastAPI `/process`
- FastAPI backend (`api.py`) is already running and tested (Phase 4)
- Response schema (`session`, `cycles`, `time`, `velocity`) is known

**Concerns:**
- CSV is only accessible within the app sandbox — Plan 05-03 must read it with `FileSystem.readAsStringAsync` and POST as multipart or JSON body (not a file path URL)
- Large sessions (~5 min × 270 Hz = ~81,000 samples × 20 bytes = ~1.6MB) may be slow to stringify for upload — consider chunked upload if needed

**Blockers:** None

---
*Phase: 05-ios-testflight, Plan: 02*
*Completed: 2026-05-22*
