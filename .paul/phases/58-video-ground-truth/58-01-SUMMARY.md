---
phase: 58-video-ground-truth
plan: 01
subsystem: mobile
tags: [react-native, expo, ble, securestore, expo-media-library, recording]

requires:
  - phase: 47-trial-annotation
    provides: one-tap Record-with-Video, videoUploadQueue, VideoOverlayScreen end-anchor
  - phase: 41-race-start-sequence
    provides: startSequencePrefs.js — the SecureStore get/set pattern autoStopPrefs mirrors
provides:
  - per-session auto-stop (default 20 s, editable, 0 = disabled) with a live countdown
  - one timer firing both camera-stop and BLE STOP — the guarantee the end-anchor premise needs
  - recorded video saved to the camera roll (expo-media-library), so footage survives leaving the screen
  - VideoOverlayScreen laid out for portrait footage
affects: [58-02 annotate page, 58-04 end-anchor, 53 attention-allocation data collection]

tech-stack:
  added: ["expo-media-library ~56.0.10"]
  patterns:
    - "Arm a recording deadline where the elapsed timer already starts, so countdown and deadline
       share one clock"
    - "Numeric text inputs hold raw text and commit on blur — clamping per keystroke corrupts typing"

key-files:
  created: ["../swimnetics-mobile/src/lib/autoStopPrefs.js"]
  modified:
    - "../swimnetics-mobile/src/screens/RecordingConfigScreen.js"
    - "../swimnetics-mobile/src/screens/RecordScreen.js"
    - "../swimnetics-mobile/src/screens/VideoOverlayScreen.js"
    - "../swimnetics-mobile/ios/mobile/Info.plist"
    - "../swimnetics-mobile/package.json"

key-decisions:
  - "Armed after writeCmd('START') resolves, not in beginPlain/startVideoRecording — the latter
     would fold in the race sequence's deliberately random hold"
  - "0 = disabled, so no second SecureStore key is needed"
  - "Info.plist edited directly — expo-doctor confirms app.json plugins are INERT in bare workflow"
  - "Did NOT run expo install --check before the build: device-proven skew beats a 4-package
     upgrade the night before a pool session"

patterns-established:
  - "Every place that stops the elapsed tick must also disarm the auto-stop deadline — asserted by
     grep count, not by reading"

duration: applied 2026-08-05; checkpoint approved 2026-08-07
started: 2026-08-05
completed: 2026-08-07
---

# Phase 58 Plan 01: iOS Auto-Stop (solo capture)

**The device and camera now stop themselves 20 s after the start blare, so a solo swimmer no longer
has to swim back to press Stop — and because one timer fires both stops, it repairs the end-anchor's
weakest premise as a side effect.**

## ⚠ Checkpoint status — approved on assumption, not on device evidence

The user approved this checkpoint on 2026-08-07 with *"assume 58-01 is working."* **No on-device
verification was reported.** Every AC below is therefore marked on static evidence (export, grep,
extracted-function testing) plus that approval — none on observed hardware behaviour.

Three specific things remain genuinely unverified:

1. **Auto-stop has never fired against real hardware.** The 20 s default was chosen from the user's
   own traces (18.93 s and 16.53 s end to end, velocity back to zero before each recording ended),
   but a too-early stop loses the end of a swim, which is the one failure mode here that destroys
   data rather than merely annoying.
2. **The checkpoint doubled as CONTEXT-R1's legibility test** — film one 25 from three tripod
   positions and try to mark arm entries off the footage. That was not reported. **R1 is now
   unanswered across three consecutive checkpoints** (57-02, 58-02, 58-01).
3. **`video_origin_s` still requires the Video Overlay tap.** Until 58-04 lands, any
   record-with-video session not opened there arrives on the web at `origin_s = 0`, silently
   unsynced.

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Auto-stop fires in plain record mode | **Assumed** | Code path verified statically; `stopPlainRef` mirrors the existing `stopVideoRef`. Not observed on device. |
| AC-2: Auto-stop fires in video mode | **Assumed** | Armed at the same site as the elapsed timer in both paths. Not observed on device. |
| AC-3: Editable + live countdown | **Assumed** | Countdown renders in both record states (`:702` video, `:746` plain). Not observed on device. |
| AC-4: 0 disables it | **Pass (unit)** | `clampAutoStopS` extracted and run in node — see below. |
| AC-5: Deadline never outlives its recording | **Pass (static)** | 5/5 cleanup-site parity asserted by grep count. See Deviation 1. |
| AC-6: Existing behaviour unchanged when disabled | **Pass (static)** | Route-param default is 0, so any caller omitting it — including a stale never-unmounted params object on that tab screen — behaves exactly as before. |

## Verification Results

**`clampAutoStopS` extracted and run through node:**
```
999 → 300      -5 → 0        0 → 0         20 → 20
2 → 5          "30" → 30     300.7 → 300   "abc"/null/undefined → 0
```

**Build:** `npx expo export --platform ios` exit 0, **1075 → 1076 modules** (the one new module is
`autoStopPrefs.js`), bundle 3.2 MB → 3.3 MB after `expo-media-library`.

**Boundaries:** `git status` in `myswimcoach` showed **no changes from this plan** — an explicit
plan boundary and a verification item, since 58-01 is mobile-only.

## Accomplishments

- **Made solo capture possible**, which is Phase 58's goal 1 and the precondition for the tripod test.
- **Repaired the end-anchor's premise structurally.** `deviceDuration − videoDuration` assumes camera
  and device stop together; a failed `writeCmd('STOP')` is caught non-fatal while the device keeps
  recording, silently inflating the auto-posted origin. One timer firing both stops is exactly that
  guarantee — the same silent-plausible-corruption class as Phases 51/52/57.
- **Made recorded video survive leaving the screen** (scope addition — see Deviation 2).

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Caught a real latent bug the plan's count had missed |
| Scope additions | 1 | User-authorized at the checkpoint; crossed a stated boundary by direction |
| Implementation notes beyond plan | 1 | Necessary; no scope change |

### 1. Five cleanup sites, not four (auto-fixed — and the worst one was the one missed)

The plan named 4 places that clear `elapsedTimerRef`. There are **5**: `reset()`
(`RecordScreen.js:626`) also clears it and was missed at plan time.

It is the worst one to miss. `reset()` sets `isStoppingRef.current = false`, so a surviving deadline
would **pass the double-stop guard and fire a real STOP + retrieval into an abandoned session.**
Parity is now 5/5, asserted by grep count. The plan's *rule* ("every place that stops the elapsed
tick must also disarm this") was right; only its *count* was wrong — which is the argument for
asserting the rule mechanically rather than enumerating sites by hand.

### 2. Video viewability (scope addition, user-authorized, crossed a stated boundary)

58-01 said "DO NOT CHANGE VideoOverlayScreen.js". The user reported *"I can't view video on mobile"*
at the checkpoint and explicitly authorized the fix. **Two root causes, the second worse:**

- **(a) Layout.** `video: { aspectRatio: 3/4 }` (`VideoOverlayScreen.js:207`) is a WIDTH-locked box.
  Portrait 9:16 footage in it is ~693 pt tall on a 390 pt screen, burying the 170 pt chart. Fixed to
  `flex: 1` with `contentFit="contain"`, so it takes what the fixed rows leave and pillarboxes
  inside — no hardcoded aspect, adapts to any screen or clip shape. User directed "assume portrait"
  and "keep video separate from trace + playhead", so stacked flex regions rather than a HUD overlay.
- **(b) Video was viewable in exactly one place, once.** VideoOverlay is reachable only from
  `RecordScreen.js:936` (the just-recorded results state) and hard-gates on a **local** `videoUri`;
  nothing on mobile calls `/sessions/{id}/video-url`; `expo-media-library` was not a dependency, so
  the clip never reached the camera roll. **Navigate away and that footage is unviewable on the
  phone forever.** It compounds with the sync gap, because that same screen is the only thing that
  POSTs `video_origin_s`. Fixed with `expo-media-library ~56.0.10` + `saveVideoToLibrary()` after
  `recordAsync` resolves, using a write-only grant (`requestPermissionsAsync(true)`) so only
  `NSPhotoLibraryAddUsageDescription` is needed. Every failure path is swallowed — a denied library
  permission must never cost a session.

**`Info.plist` was edited directly, and expo-doctor confirms that was the only working path:**
*"native project folders but also native configuration properties in app.json … EAS Build will not
sync: scheme, orientation, userInterfaceStyle, ios, **plugins**, android."* Adding the plugin to
`app.json` would have been inert. Matches the standing bare-workflow note in memory.

Result: **7 files changed in the mobile repo, not 3.**

### 3. Config field commits on blur, not per keystroke (implementation note)

The field holds raw text in `autoStopText` and commits on blur/submit. Without that, typing "20"
passes through "2" → clamped up to the 5 s floor mid-typing, and an empty field reads as 0 →
**silently switches auto-stop off**. The clamp itself is unchanged; this is only about when it runs.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| expo-doctor reports 4 packages out of date (expo 56.0.12 vs ~56.0.18, expo-audio, expo-dev-client, react-native-screens 4.25.2 vs ~4.26.0) | **Pre-existing, not introduced** — `expo-media-library` was installed at the SDK-matched version. This exact combination is what the Phase-55 build shipped and it was device-verified 2026-08-05. Recommended AGAINST `expo install --check` before the build: upgrading 4 packages the night before a pool session is a bigger risk than a device-proven skew, and SDK-56 version skew is precisely the failure that builds clean then dyld-crashes at launch. |

## Next Phase Readiness

**Ready:**
- Solo capture is code-complete. Video now reaches the camera roll and the overlay screen is
  portrait-usable.

**Concerns:**
- ⚠ **Nothing here has run on hardware.** The checkpoint was approved on assumption. Auto-stop
  firing, the countdown, and video-mode behaviour are all unobserved.
- ⚠ **R1 unanswered for the third consecutive checkpoint.**
- ⚠ **Not committed, and it is a separate repo** (`swimnetics-mobile`, user-owned git). Nothing in
  this summary is in the `myswimcoach` push.
- ⚠ 58-04 (end-anchor) still owed; until then the Video Overlay tap is mandatory per video session.

**Blockers:** None.

---
*Phase: 58-video-ground-truth, Plan: 01*
*Completed: 2026-08-07 (applied 2026-08-05; checkpoint approved on assumption)*
