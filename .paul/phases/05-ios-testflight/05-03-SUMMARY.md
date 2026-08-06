---
phase: 05-ios-testflight
plan: 03
subsystem: api
tags: [fastapi, railway, react-native-svg, expo-file-system, upload, chart, multipart]

requires:
  - phase: 04-01
    provides: POST /process endpoint returning session + cycles + time + velocity JSON
  - phase: 05-02
    provides: BLE recording, CSV saved to FileSystem.documentDirectory

provides:
  - "FastAPI deployed to Railway at https://swimnetics-api-production.up.railway.app"
  - "Auto-upload via FileSystem.uploadAsync after every session stop"
  - "Velocity chart (react-native-svg SVG polyline, downsampled to 400pts)"
  - "4 headline metric cards: stroke rate, avg speed, distance, fatigue index"
  - "Persistent BLE connection between sessions (device stays connected)"

affects: [06-auth-athlete-profiles]

tech-stack:
  added: [react-native-svg@15.15.5, @railway/cli (deploy)]
  patterns:
    - "FileSystem.uploadAsync for multipart — fetch+FormData rejected by RN 0.85/Hermes"
    - "Device stays connected between sessions; reset() checks isConnected() to determine next state"
    - "disconnectRef.current?.remove() before overwriting in startRecording — prevents leaked watcher"
    - "isStoppingRef.current = false safety reset in startRecording — not just in reset()"

key-files:
  created: [swimnetics-mobile/src/config.js]
  modified: [swimnetics-mobile/src/screens/RecordScreen.js, swimnetics-mobile/package.json, swimnetics-mobile/eas.json]

key-decisions:
  - "FileSystem.uploadAsync not fetch+FormData — RN 0.85 rejects {uri, name, type} FormData pattern"
  - "Device stays connected between sessions — reset() returns to connected state if isConnected()"
  - "onData errors no longer auto-stop — only disconnect watcher triggers stopRecording(true)"
  - "Railway deployed directly via CLI (railway up) — no manual web UI needed"
  - "cancelConnection() removed from reset() — explicitly disconnects only on app close or error"

patterns-established:
  - "FileSystem.uploadAsync(url, filePath, {uploadType: MULTIPART, fieldName: 'file'}) for iOS file upload"
  - "VelocityChart: downsample via index-based loop, filter nulls, SVG Polyline"
  - "disconnectRef must be explicitly removed before overwriting with new onDisconnected listener"
  - "isStoppingRef safety reset at START of startRecording, not just in reset()"

duration: ~5h (including 5 debug/fix iterations)
started: 2026-05-22T00:00:00Z
completed: 2026-05-22T00:00:00Z
---

# Phase 5 Plan 03: Upload + Chart Summary

**End-to-end loop complete: BLE record → FileSystem.uploadAsync to Railway FastAPI → velocity chart + 4 metrics displayed on iPhone without a laptop.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~5 hours |
| Completed | 2026-05-22 |
| Fix iterations | 5 |
| Tasks | 4 of 4 complete (2 human-action + 1 auto + 1 human-verify) |
| Commits | 7 (including post-approval fixes) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Upload triggers automatically after Stop | Pass | Fire-and-forget call in stopRecording after CSV save |
| AC-2: Velocity chart renders | Pass | SVG Polyline with 400-point downsampling, null filtering |
| AC-3: Headline metrics displayed | Pass | 4 cards: stroke rate, avg speed, distance, fatigue |
| AC-4: Upload failure handled gracefully | Pass | 30s timeout, error state with CSV preserved locally |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 5 | All essential, no scope creep |
| Scope changes | 1 | Device stays connected (better UX than plan assumed) |
| Deferred | 0 | — |

### Auto-fixed Issues

**1. FormData rejected by RN 0.85/Hermes**
- **Issue:** `fetch()` with `{uri, name, type}` FormData object throws "Unsupported FormData implementation"
- **Fix:** `FileSystem.uploadAsync()` with `FileSystemUploadType.MULTIPART` — bypasses JS FormData entirely
- **Commit:** `be03762`

**2. `disconnectRef` watcher leaked between `connectTo` and `startRecording`**
- **Issue:** `startRecording()` overwrote `disconnectRef.current` without removing the idle watcher registered in `connectTo()`. On device disconnect during second recording, both the leaked idle watcher AND the recording watcher fired, causing state corruption
- **Fix:** Added `disconnectRef.current?.remove()` before registering recording watcher in `startRecording()`
- **Commit:** `aba8151`

**3. Double-stop on second recording session**
- **Issue:** `isStoppingRef.current` was left `true` from a transient error during recording, causing Stop button to do nothing
- **Fix 1:** `isStoppingRef.current = false` safety reset at START of `startRecording()` (not just in `reset()`)
- **Fix 2:** Removed `stopRecording(true)` auto-call from `onData` error handler — only disconnect watcher triggers auto-stop
- **Commit:** `320381e`

**4. `VelocityChart` null values**
- **Issue:** `_clean()` in api.py converts NaN → null; `Math.min(null, ...)` coerces to 0, distorting chart y-axis
- **Fix:** Index-based downsampling with null/NaN filter
- **Commit:** `aba8151`

**5. `cancelConnection()` wrongly added to `reset()`**
- **Issue:** Disconnect on reset prevented reconnection in the same session; coach wanted device to stay connected between swims
- **Fix:** Removed `cancelConnection()`; `reset()` now checks `isConnected()` and returns to `connected` state if still live
- **Commit:** `0e2b3cb` (reverted `d332d89`)

### Scope Change

**Device stays connected between sessions** — original plan assumed `reset()` always returns to idle (scan required). Tony specified device should stay connected; `reset()` was changed to check `isConnected()` and return to appropriate state.

## Railway Deployment

```
URL:     https://swimnetics-api-production.up.railway.app
Health:  GET /health → {"status":"ok"}
Process: POST /process → {session, cycles, time, velocity}
Deploy:  railway up --service swimnetics-api (from myswimcoach/)
```

## Next Phase Readiness

**Ready:**
- Full demo loop works: record → upload → metrics + chart on iPhone
- Railway URL stable in `src/config.js` — update if URL changes
- BLE connection persists between sessions — coach workflow is natural
- All critical bugs fixed; code reviewed to 95% confidence

**Concerns:**
- No auth — all coaches share same backend, no data isolation (Phase 6)
- Raw CSVs accumulate on device with no cleanup — add purge in Phase 6
- Railway free tier may sleep on inactivity — recommend $5/mo Starter plan before demos
- Debug log visible on results screen — consider hiding in production build

**Blockers:** None

---
*Phase: 05-ios-testflight, Plan: 03*
*Completed: 2026-05-22*
