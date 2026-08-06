---
phase: 41-race-start-sequence
plan: 01
subsystem: ui
tags: [ios, react-native, expo-audio, expo-secure-store, recording, ble, race-start]

requires:
  - phase: 38-mobile-redesign
    provides: RecordingConfigScreen athlete picker + RecordScreen dark/immersive record flow + theme tokens
  - phase: 26-in-app-video-overlay
    provides: RecordScreen video path (CameraView + onCameraReady BLE START orchestration)
provides:
  - Optional race-start cue on the iOS recording flow (3-2-1 → "take your marks" → random 2–3 s hold → blare)
  - Recording (BLE START / camera) begins exactly on the blare
  - Persisted, default-ON toggle on RecordingConfigScreen
  - Reusable useStartSequence hook + StartSequenceOverlay component
affects: [ios-record-flow, future-eas-build-verification]

tech-stack:
  added: [expo-audio ~56.0.12]
  patterns: ["sequence hook returns {phase, run, cancel}; run() resolves at the blare so callers START on it", "secure-store preference helper with default-on"]

key-files:
  created:
    - swimnetics-mobile/src/hooks/useStartSequence.js
    - swimnetics-mobile/src/components/StartSequenceOverlay.js
    - swimnetics-mobile/src/lib/startSequencePrefs.js
    - swimnetics-mobile/assets/audio/(takeyourmarks.mp3, beep.mp3, README.md)
  modified:
    - swimnetics-mobile/src/screens/RecordScreen.js
    - swimnetics-mobile/src/screens/RecordingConfigScreen.js
    - swimnetics-mobile/package.json
    - swimnetics-mobile/app.json

key-decisions:
  - "Random 2–3 s hold (un-anticipatable, like a real meet) over a fixed hold"
  - "Two bundled real-starter clips via expo-audio (no TTS); user-supplied files"
  - "Toggle persisted via expo-secure-store (already installed), default ON"
  - "run() resolves AT the blare (not after) so START fires on the gun"
  - "Sequence gates WHEN the existing START is written — BLE/camera/sync logic untouched"

patterns-established:
  - "Cancelable async sequence via canceledRef + timerRef; guard() between steps; resolves {canceled}"
  - "Full-screen overlay reads a single phase value; renders null when idle"

duration: ~30min
started: 2026-06-22T00:30:00Z
completed: 2026-06-22T01:00:00Z
---

# Phase 41 Plan 01: Race-Start Sequence (iOS) Summary

**Optional meet-style race start on the iOS record flow — giant 3-2-1 countdown, spoken "take your marks", randomized 2–3 s hold, then a blare that begins recording on the gun; persisted default-ON toggle, works over plain and Record-with-Video.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Started | 2026-06-22T00:30:00Z |
| Completed | 2026-06-22T01:00:00Z |
| Tasks | 3 auto + 1 human-action checkpoint (pre-satisfied) |
| Files modified | 4 modified, 4 created (incl. 2 audio assets) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Persisted toggle, default ON, passed to Record | Pass (code) | Switch on RecordingConfigScreen; secure-store default TRUE; `startSequence` nav param. Persistence-across-reopen confirmed by code path; device confirm deferred. |
| AC-2: Plain record runs sequence, START on blare | Pass (code) | `beginPlain` runs `seq.run()` then `startRecording()` (writes BLE START) only on the blare; canceled → no START. |
| AC-3: Video path same sequence over live preview | Pass (code) | `onCameraReady` runs `seq.run()` before the existing `writeCmd('START')`+`recordAsync`; canceled → `setVideoMode(false)`. |
| AC-4: Toggle OFF preserves prior behavior | Pass (code) | `if (!startSequence)` → immediate `startRecording()` / unchanged `onCameraReady`. |
| AC-5: Cancelable + builds clean, assets bundled | Pass | `npx expo export --platform ios` exit 0, 1071 modules; `beep.mp3` + `takeyourmarks.mp3` listed in Assets. Cancel wired to `seq.cancel`. |

**Note:** AC-2…AC-5 runtime behavior (audio, visuals, timing, silent-mode) is verified at code/bundle level only; on-device verification is deferred to the next EAS build (expo-audio is a new native module).

## Accomplishments

- Authentic, un-anticipatable race-start cue that begins data capture exactly on the blare, so the buffered session is the race effort.
- Encapsulated, reusable `useStartSequence` hook + `StartSequenceOverlay` — both record entry points share one gate; the BLE/camera/META/DUMP/sync pipeline is untouched (timing-only wrapper).
- Persisted default-ON setting using the already-installed secure-store (no new persistence dep).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `src/hooks/useStartSequence.js` | Created | Phase machine + audio playback; `run()` resolves at the blare; cancelable |
| `src/components/StartSequenceOverlay.js` | Created | Full-screen scrim overlay: 3-2-1 / "Take your marks" / blare flash / Cancel |
| `src/lib/startSequencePrefs.js` | Created | secure-store get/set, default TRUE |
| `assets/audio/takeyourmarks.mp3`, `beep.mp3`, `README.md` | Created | Bundled voice + blare clips (user-supplied) + docs |
| `src/screens/RecordingConfigScreen.js` | Modified | "Race start sequence" Switch (persisted) + `startSequence` nav param |
| `src/screens/RecordScreen.js` | Modified | seq hook; `beginPlain` + `onCameraReady` gate START behind the cue; overlay render |
| `package.json` / `app.json` | Modified | `expo-audio ~56.0.12` dep + config plugin |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Random 2–3 s hold | Mimics a real meet — swimmers can't time the gun | Race-start training validity |
| Bundled clips (no TTS) via expo-audio | Authentic "official start" voice + horn | One new native dep → EAS build; user supplies/approves the files |
| Persist via secure-store, default ON | "Setting" semantics; reuses installed dep | No AsyncStorage added |
| `run()` resolves at the blare | Recording must begin on the gun, not after the horn finishes | START fires on the blare beat |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 1 | On-device verification (next EAS build) |

- **Filenames:** plan placeholder names (`take-your-marks.m4a` / `start-horn.m4a`) → actual user-supplied files `takeyourmarks.mp3` / `beep.mp3`; `require()` paths + README match the real files. No behavior impact.
- **Checkpoint pre-satisfied:** the human-action checkpoint (supply audio files) was resolved up front — the user placed both files before APPLY; they were moved into `assets/audio/` and bundle cleanly.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| None | — |

## Next Phase Readiness

**Ready:**
- Code-complete and export-green; bundles the audio assets.
- `useStartSequence` is reusable if a Record-island cold-start path ever needs the cue.

**Concerns:**
- expo-audio is a new native module — the existing dev client cannot run it; a fresh EAS build is required to verify.
- Verify `beep.mp3` is loud/punchy enough as the "gun" on-device (swappable in place).
- Confirm playback in iOS silent mode (handled via `setAudioModeAsync({ playsInSilentMode: true })`).

**Blockers:** None.

---
*Phase: 41-race-start-sequence, Plan: 01*
*Completed: 2026-06-22*
