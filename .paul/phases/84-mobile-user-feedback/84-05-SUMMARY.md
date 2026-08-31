---
phase: 84-mobile-user-feedback
plan: 05
subsystem: mobile
tags: [expo-camera, video-upload, supabase-storage, retry, react-native, cross-repo]

requires:
  - phase: 26-in-app-video-overlay
    provides: the in-app camera + videoUploadQueue this plan repairs
  - phase: 84-mobile-user-feedback
    plan: 02
    provides: RecordScreen.js / RecordingConfigScreen.js in their post-GO-marker state
provides:
  - tools/probe_video_uploads.py — the read-only probe that MEASURED the cause
  - src/lib/uploadRetry.js — pure retry/refusal policy, size cap cross-checked against api.py
  - src/lib/cameraPrefs.js + live zoom + pre-recording lens choice
  - an upload chip that names the reason instead of retrying an unchangeable outcome
affects: [Phase 82 storage quota, any future video-upload consumer]

tech-stack:
  added: []
  patterns:
    - "Measure the cause before planning the fix — a read-only probe against live data beat
       six hypotheses down to one confirmed and one refuted"
    - "A headless harness cross-checks a client constant against the server's own source"

key-files:
  created:
    - tools/probe_video_uploads.py
    - scratch/upload_retry_check.mjs
    - ../swimnetics-mobile/src/lib/uploadRetry.js
    - ../swimnetics-mobile/src/lib/cameraPrefs.js
  modified:
    - ../swimnetics-mobile/src/lib/videoUploadQueue.js
    - ../swimnetics-mobile/src/components/UploadToast.js
    - ../swimnetics-mobile/src/screens/RecordScreen.js
    - ../swimnetics-mobile/src/screens/RecordingConfigScreen.js

key-decisions:
  - "Checkpoint answered option-a: videoQuality='720p'. One prop, no codec risk — option-b's
     videoBitrate route needs a getAvailableVideoCodecsAsync() guard whose failure mode is
     REJECTING recordAsync, on the critical path seconds before START, to buy 67 s vs 72 s"
  - "api.py's MAX_VIDEO_BYTES deliberately untouched — Phase 82 / Pro territory, and it is a
     RAM guard as well as a quota one"
  - "Queue persistence (H3) stays OUT of scope: saveVideoToLibrary copies every recording to
     Photos, so footage is never lost — only the attachment"

patterns-established:
  - "No zoom preset may claim a magnification factor: videoZoomFactor = maxZoomFactor ** zoom
     against a device max JS cannot read. Only zoom=0 is truthfully 1x"

duration: ~1 session
started: 2026-08-30
completed: 2026-08-31
---

# Phase 84 Plan 05: Upload Failures + Camera Options Summary

**The fifth and last Phase-84 plan.** Item 2's cause was **measured, not hypothesised** — a read-only
probe run against the live project during planning. Recordings now cap at 720p, an over-cap clip is
refused before the network with a reason the coach can read, and the camera gained a live zoom and a
pre-recording lens choice.

## The measurement that replaced six hypotheses

**H1 CONFIRMED and quantified.** 37 stored phone clips give a median encode rate of **1.38 MB/s**
(range 0.90–2.20) at iOS's default 1080p, so the 50 MB cap is reached at **≈36 s of video** — ≈23 s on
the fastest device — while `recordAsync` and auto-stop both allow 300 s. The bucket's own distribution
shows the ceiling: 97 phone clips, **max 48.3 MB, nothing ≥ 50 MB**.

**9 sessions carry the lost-clip fingerprint** (`video_origin_s` set, `video_path` NULL). Recovering
each clip's length from `deviceDuration − origin` prices **6 at 54–110 MB**, two more inside the device
spread — so **6–8 of 9 are H1**. One (25 MB) is unexplained and stays the residual.

**H2 REFUTED — Phase 82 is NOT a prerequisite.** A 1-byte probe object uploaded successfully with the
bucket at 2.63 GB and was deleted. The long-standing *"new uploads may already be blocked"* worry is
**retracted**; Phase 82 is a cost/hygiene phase, not an outage.

**The 413 was invisible three times over:** the queue wrapped it as `Server error (413)` and **retried
it twice over ~13 s** on an outcome that could not change; `UploadToast` rendered a constant string and
never showed `job.lastError`; and the chip died with the app.

## Acceptance Criteria Results

| AC | Result | Evidence |
|----|--------|----------|
| AC-1: The evidence is reproducible | **Pass** | `tools/probe_video_uploads.py` committed; reproduces G1/G2/G4 |
| AC-2: Normal recordings stop reaching the cap | **Pass (code)** | `videoQuality="720p"`; 720p at the measured rate puts a 300 s recording inside the cap |
| AC-3: An over-cap clip fails before the network | **Pass** | Pre-flight size refusal in `uploadRetry.js` |
| AC-4: Deterministic rejections are not retried | **Pass** | No-retry-on-4xx; harness asserts the policy table |
| AC-5: The failure is nameable in the UI | **Pass (code)** | `UploadToast` renders `job.lastError` |
| AC-6: Zoom adjustable while filming | **Deferred** | expo-camera's iOS source shows `zoom` touches only `device.lockForConfiguration()` — safe mid-record. **Needs a device.** |
| AC-7: Lens chosen before recording and persists | **Deferred** | `cameraPrefs.js`; `facing` reconfigures the session so it must be set before recording. **Needs a device.** |
| AC-8: Nothing outside scope moved | **Pass** | `api.py` untouched by this plan; suite **505**, no drift |

**Harness:** `node scratch/upload_retry_check.mjs` → **36/36, exit 0**, including
`mobile MAX_VIDEO_BYTES === api.py MAX_VIDEO_BYTES` (both 52428800). Re-run 2026-08-31 at close.

## Deviations

1. **G12 was already stale when written** — it listed 84-03 and 84-04 as planned; both were applied.
   Only the AC-8 pre-existing baseline is larger than G12 recorded.
2. **Two docs claims corrected:** iOS defaults to **1080p, not 4K** (`CameraViewModule.swift:184`), so
   H1's 4K framing was overstated — 1080p alone does it. And the TS docstring calling the 16:9
   `videoQuality` values Android-only is **wrong** (`CameraRecordingOptions.swift:17-30` maps them all).

## Deferred

**AC-6 + AC-7 — the device verify.** ⚠ Needs **encoder plus camera**, and `npx expo-doctor` first.
There is **no pre-recording camera preview** (`onCameraReady` writes START and calls `recordAsync` at
once), so the live overlay is the only place a coach can frame a shot — judge whether that reads right.

## Next Phase Readiness

⚠ **Shares `RecordScreen.js` and `RecordingConfigScreen.js` with 84-02** — there is no path-scoping
that separates them; they commit together. Phase 82 is unblocked but no longer urgent (H2 refuted).
