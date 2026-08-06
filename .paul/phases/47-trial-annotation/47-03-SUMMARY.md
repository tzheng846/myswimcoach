---
phase: 47-trial-annotation
plan: 03
subsystem: mobile
tags: [expo, filesystem, background-upload, queue, react-native, ble, video]

requires:
  - phase: 47-trial-annotation (47-01)
    provides: POST /sessions/{id}/video contract (multipart file + video_origin_s, LIVE on Railway)
provides:
  - App-wide FIFO video upload queue (videoUploadQueue.js) that survives screen unmount + app backgrounding
  - In-app toast/chip UI for upload status (UploadToast.js)
  - RecordScreen enqueues video upload post-results (non-blocking)
  - VideoOverlayScreen persists end-anchored sync origin to the backend
affects: [phase-16-06 (wavelet tuning ground truth needs videos attached), future EAS-build device-verify batch]

tech-stack:
  added: []
  patterns:
    - "Module-singleton queue (no React/Redux) with subscribe/notify for cross-screen state, mirrors BleContext's non-React-state style"
    - "FileSystem.uploadAsync with sessionType BACKGROUND for uploads that survive navigation/backgrounding without a native dep"

key-files:
  created:
    - ../swimnetics-mobile/src/lib/videoUploadQueue.js
    - ../swimnetics-mobile/src/components/UploadToast.js
  modified:
    - ../swimnetics-mobile/App.js
    - ../swimnetics-mobile/src/screens/RecordScreen.js
    - ../swimnetics-mobile/src/screens/VideoOverlayScreen.js

key-decisions:
  - "In-app toast only, no expo-notifications (user decision, avoids new native dep)"
  - "FIFO one-at-a-time queue, not parallel (predictable poolside bandwidth)"
  - "Auto-retry x2 with backoff (~3s/~10s) then persistent dismissible chip, no infinite retry"
  - "No queue persistence across app restarts — file stays on disk, re-record-day risk accepted"

patterns-established:
  - "videoUriRef stale-closure guard: when a useCallback's deps can't include a value that changes via a different code path, mirror it into a ref set at the same point the state is set"

duration: ~45min
started: 2026-07-12T00:00:00Z
completed: 2026-07-12T03:00:00Z
---

# Phase 47 Plan 03: iOS Background Video Upload Summary

**Instagram-style FIFO video upload queue on iOS — enqueue-and-forget after Record-with-Video, in-app toast/chip status, survives navigation and backgrounding; VideoOverlayScreen now persists the end-anchored sync origin to the backend.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45min |
| Started / Completed | 2026-07-12 |
| Tasks | 3 of 3 completed |
| Files modified | 5 (2 new, 3 modified) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Non-blocking app-wide upload | Pass | Enqueue is fire-and-forget post-results in `uploadAndProcess`; no awaits added to record→results path; plain (no-video) path untouched |
| AC-2: FIFO queue + toast | Pass | Single-flight `working` flag + re-pump on `finally` guarantees one job at a time; toast fires on status transitions (prev-status diff) |
| AC-3: Retry ×2 + persistent chip | Pass | Backoff ~3s/~10s on attempts 1–2; 3rd failure → persistent chip (needsWorkBg/needsWork tokens) above TabBar with Retry/✕ |
| AC-4: Sync origin persisted from playback | Pass | `saveOrigin` fires once when `videoOriginS` first resolves, then debounced ~1s on nudge; no sessionId → no calls (verified by code path, not device) |
| AC-5: Export green | Pass | `npx expo export --platform ios` exit 0, 1075 modules, 3.2MB bundle (re-verified at UNIFY, matches APPLY-time result) |

## Accomplishments

- Videos no longer block the coach's flow between swimmers — upload happens entirely off the critical path, survives leaving the screen and iOS backgrounding via `FileSystem.FileSystemSessionType.BACKGROUND`
- One shared queue + toast host covers every screen (mounted once at App.js root next to the global AiBubble) instead of per-screen upload UI
- VideoOverlayScreen now closes the loop with the backend: the end-anchored sync origin computed on-device (44-03) is persisted, so the web annotate page's video playback is pre-aligned with no manual step
- Phase 47 is now feature-complete end-to-end: annotate contract (47-01) → web GUI (47-02) → iOS video capture+upload+sync (47-03) → recompute-on-save (47-04)

## Task Commits

Not committed — mobile repo is local-only per project convention; user runs git. No commits exist yet for this plan's changes (verified: `git status` in `../swimnetics-mobile` shows App.js, RecordScreen.js, VideoOverlayScreen.js modified and UploadToast.js/videoUploadQueue.js untracked, alongside other pending mobile-repo work from Phases 41/42/44).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `../swimnetics-mobile/src/lib/videoUploadQueue.js` | Created | Module-singleton FIFO upload queue — enqueue/subscribe/retry/dismiss, single-flight worker, retry with backoff, in-memory job tracking |
| `../swimnetics-mobile/src/components/UploadToast.js` | Created | Global toast ("Uploading video…" / "Video saved to cloud ✓") + persistent failed-job chip (Retry/✕), subscribed to the queue |
| `../swimnetics-mobile/App.js` | Modified | Mounts `<UploadToast />` once at root beside the global AiBubble |
| `../swimnetics-mobile/src/screens/RecordScreen.js` | Modified | Enqueues the video upload after `/process` success (non-awaited); added `videoUriRef` stale-closure guard; passes `sessionId` to VideoOverlay nav params |
| `../swimnetics-mobile/src/screens/VideoOverlayScreen.js` | Modified | `saveOrigin()` posts `video_origin_s` origin-only via string-FormData once resolved, then debounced (~1s) on nudge; appends save-status to the existing sync-debug line |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Toast styled as a dark pill (colors.text bg) rather than the plan's generic "light-theme tokens" | Matches the app's existing floating-element (AiBubble) visual language better than a light card would against varied screen backgrounds | Cosmetic only; no functional deviation from AC-2 |
| `FileSystem` imported from `'expo-file-system/legacy'` | Matches the import RecordScreen already uses elsewhere in the same file — consistency over the newer API surface | None — behavior-equivalent for this SDK version |
| Added `videoUriRef` mirroring `videoUri` state in RecordScreen | `uploadAndProcess`'s `useCallback` deps don't include `videoUri`, so the closure would've seen a stale value at enqueue time; a ref set at the same point `videoUri` is set (recordAsync resolve) and cleared on both reset paths sidesteps this without widening the callback's deps | Small addition not explicitly named in the plan, but required for AC-1 correctness (enqueue must use the video actually recorded, not a stale closure value) |
| Done-jobs pruned from the queue after 6s | Gives the toast time to render the transition before the job disappears from `subscribe()` snapshots | None — internal to Task 1's mechanics |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Necessary correctness fix (stale-closure guard), no scope creep |
| Scope additions | 0 | None |
| Deferred | 0 | Device verify was already explicitly deferred by the plan itself |

**Total impact:** Plan executed as specified; one implementation-level fix (videoUriRef) was required to satisfy AC-1 correctly and is documented above, not a scope change.

### Auto-fixed Issues

**1. [Correctness] Stale-closure risk on `videoUri` in RecordScreen's enqueue call**
- **Found during:** Task 2 (RecordScreen enqueue wiring)
- **Issue:** `uploadAndProcess`'s `useCallback` dependency array does not include `videoUri`, so reading `videoUri` directly inside it at enqueue time risked capturing a stale (pre-recording) value
- **Fix:** Added `videoUriRef`, set at the same point `videoUri` state is set (recordAsync resolve) and cleared on both reset paths; the enqueue call reads the ref instead of the closed-over state
- **Files:** `../swimnetics-mobile/src/screens/RecordScreen.js`
- **Verification:** Structural self-review (no arduino-cli/device available); `npx expo export --platform ios` exit 0
- **Commit:** Not committed (mobile repo local-only)

### Deferred Items

None new — the plan itself scoped device verification (AC-1 through AC-4 on real hardware/network) to the next EAS build, which remains outstanding along with the other Phase 41/42/44 device-verify deferrals already tracked in STATE.md.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Phase 47 (Trial Annotation) is now 4/4 plans complete: backend contract (47-01), web GUI (47-02), iOS video capture+upload+sync (47-03), recompute-on-save (47-04)
- The full pipeline is live end-to-end on the web side (endpoint deployed, GUI shipped, recompute verified with suite 148) and code-complete on iOS pending one device build
- Ground-truth annotation export (`GET /annotations/export` + `fetch_annotations.py`) is available today for 16-06 wavelet tuning, even before videos are flowing from real devices

**Concerns:**
- iOS side of this plan (and Phases 41/42/44) remains device-unverified — all riding the same next EAS build
- `../swimnetics-mobile` has substantial uncommitted work across several phases (41/42/44/47-03); when the user does commit, it will need careful staging to keep phase history legible (as was done for 47-01/02 in commit e7f72f4)
- `.mov` files are stored under a `.mp4` path with no transcode — playback risk flagged in the plan, not yet hit in practice since no real device upload has occurred

**Blockers:**
None.

---
*Phase: 47-trial-annotation, Plan: 03*
*Completed: 2026-07-12*
