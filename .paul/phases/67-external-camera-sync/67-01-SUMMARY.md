---
phase: 67-external-camera-sync
plan: 01
subsystem: ui
tags: [react, nextjs, video, sync, annotate, gopro, external-camera]

requires:
  - phase: 47-trial-annotation
    provides: the annotate page + VideoPane (upload, nudge, save-sync, signed-URL playback)
  - phase: 58-video-ground-truth
    provides: the end-anchor origin convention VideoPane computes (58-04)
  - phase: 61-web-portal-rework
    provides: VideoPane as the web writer of video_origin_s
provides:
  - one-tap "Sync to push-off" on the annotate video card (external-camera sync mechanic)
  - VideoPane `pushoffSessionS` prop + `alignToPushoff()` (origin = pushoffSessionS − videoTime)
affects: [67-02 production-size robustness, external-camera workflow]

tech-stack:
  added: []
  patterns:
    - "External-clip origin is set by coach visual push-off align; phone keeps the end-anchor. Same column, same reader."
    - "Align is a live preview (sets originS like nudge); the existing Save-sync is the ONLY persist path — VideoPane stays the single writer of video_origin_s."

key-files:
  created: []
  modified:
    - web/components/portal/VideoPane.js
    - web/app/app/annotate/[id]/page.js

key-decisions:
  - "Align snaps to the dive/push-off session-time (build_seed dive_start_s = baseline_end_s), coach-placed marker preferred over auto seed — no CV."
  - "Windowed card (annotate page) only; panel mode / fullscreen review left byte-identical (fast-follow)."

patterns-established:
  - "The align target is read from the auto seed read-only, so one-tap sync works with ZERO marks placed yet follows a placed Dive mark — Phase 57 D6 blank-start untouched."

duration: ~30min
started: 2026-08-16T23:40:00Z
completed: 2026-08-17T00:15:00Z
---

# Phase 67 Plan 01: External-Camera Push-off Video Sync Summary

**Shipped a one-tap "Sync to push-off" on the annotate video card: the coach scrubs an external
clip to the push-off frame and one click sets `video_origin_s = diveSessionTime − videoTime`,
replacing the dozens of ±0.1 s nudges an external clip needs because the 44-03 end-anchor is wrong
for a camera that never stops with the encoder. No computer vision. Web-only, additive, `2aa58ca` → Vercel.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Completed | 2026-08-17 |
| Tasks | 2 completed |
| Files modified | 2 |
| Lines | +52, −0 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Push-off align sets the correct origin | Pass (build + logic) | `alignToPushoff` sets `originS = round(pushoffSessionS − v.currentTime, 2)`, pushes the playhead; existing Save-sync persists. ⚠ Real-clip "feel" UAT is the user's. |
| AC-2: Zero-mark friction + follows a placed Dive mark | Pass | `pushoffSessionS` memo = `phases.dive_start_s ?? phases.underwater_start_s ?? ann.seed.phases.dive_start_s ?? … ?? null` — non-null on any auto-dive session with no marks; updates when the coach moves the Dive/Underwater marker. |
| AC-3: Graceful when no push-off time | Pass | Button disabled when `pushoffSessionS == null \|\| !url`, with an inline hint to place the Dive mark; nudge + Save-sync unchanged. |
| AC-4: Phone path + panel mode unchanged | Pass | `git diff` shows no additions to the panel-mode branch or the end-anchor logic; change is +52 additive lines only. |

## Verification Results

- `npm run build` → **exit 0** (Next 16 Turbopack; `/app/annotate/[id]` compiles; 18/18 static pages).
- `npx eslint` on the two files → annotate page **clean**; VideoPane's single `set-state-in-effect`
  is **pre-existing** at `:105` (`setUrl(null)` in the signed-URL effect), one of the repo's 18 —
  **no NEW lint errors introduced**.
- `git diff --stat` → only the two intended web files; panel-mode branch byte-identical.

## Accomplishments

- The external-camera sync mechanic exists: one gesture (scrub) + one tap, keyed on the encoder's
  own dive detection — the reliable half stays on the reliable sensor, the coach only marks the video frame.
- Reused the existing `VideoPane` upload/nudge/save entirely; the only new surface is the align
  button and one wired prop. Phone workflow and the fullscreen review page are provably untouched.

## Task Commits

Committed as one plan-level commit (not per-task — two tightly-coupled files, one feature):

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Task 1: VideoPane push-off align | `2aa58ca` | feat | `pushoffSessionS` prop + `alignToPushoff()` + windowed-card button |
| Task 2: annotate wiring | `2aa58ca` | feat | `pushoffSessionS` memo + prop pass-through |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/VideoPane.js` | Modified | New `pushoffSessionS` prop, `alignToPushoff()` action, "Sync to push-off" button in the windowed sync row (+ disabled hint). |
| `web/app/app/annotate/[id]/page.js` | Modified | `pushoffSessionS` `useMemo` (placed Dive → auto seed → null) passed to `VideoPane`. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Align snaps to `dive_start_s`/`underwater_start_s` | The dive/push-off is the sharpest shared event in both the velocity trace (auto-detected spike) and the video; no CV needed | The coach's only required action is scrubbing the video |
| Align is a live preview; Save-sync is the sole persist path | Keep VideoPane the single writer of `video_origin_s` (the 58-04/61-03 invariant) | No new write path introduced |
| Windowed card only | The annotate page already holds frame-step + the phase marks; the review page shares VideoPane and can inherit align later | Panel mode untouched this plan |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** Plan executed exactly as written.

### Deferred Items

None in this plan. (Phase-level: production-size robustness is the separately-scoped Plan 67-02.)

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `npm run lint` exits 1 | Pre-existing: 18 repo-wide `react-hooks/set-state-in-effect` errors; my files add none (annotate clean, VideoPane's is at `:105`, pre-existing). Build is the real gate and passes. |
| STATE.md modified by a concurrent session mid-edit | Surgical anchored edits applied cleanly; will read-before-edit STATE going forward. |

## Next Phase Readiness

**Ready:**
- The sync mechanic is live. 67-02 can layer production-size robustness on top without touching it.

**Concerns:**
- ⚠ The feature is only usable with **small (<50 MB) clips** until 67-02: `POST /sessions/{id}/video`
  does `await file.read()` (OOM risk) and the `videos` bucket inherits Supabase's ~50 MB default,
  so real GoPro footage is rejected/OOM today.
- ⚠ **Real-GoPro upload/playback + "does it feel aligned" is unverified** — needs the user with a clip.

**Blockers:**
- None for 67-02's code. Phase-level completion needs a Supabase dashboard cap raise (human) — 67-02.

---
*Phase: 67-external-camera-sync, Plan: 01*
*Completed: 2026-08-17*
