---
phase: 64-video-velocity-overlay
plan: 01
subsystem: ui
tags: [react, svg, requestAnimationFrame, fullscreen, video, recharts, nextjs]
requires:
  - phase: 61-web-portal-rework
    provides: /app/sessions/[id]/video route, VideoPane, VelocityChart, end-anchored video_origin_s
provides:
  - TraceOverlay (hand-rolled SVG velocity strip, viewBox-panned by rAF)
  - VideoTracePanel (inline+fullscreen container), PlaybackControls (custom bar)
  - VideoPane panel/fullscreen mode; drag-to-scrub on the overlay
affects: [64-02, 64-03, 65-underwater-phase-detection]
tech-stack:
  added: []
  patterns: ["zero-React-state rAF animation loop", "window-level pointer scrub with pointercancel teardown"]
key-files:
  created: [web/components/portal/TraceOverlay.js, web/components/portal/PlaybackControls.js, web/components/portal/VideoTracePanel.js]
  modified: [web/components/portal/VideoPane.js, web/app/app/sessions/[id]/video/page.js, web/app/app/sessions/[id]/page.js]
key-decisions:
  - "Fullscreen a CONTAINER, never the <video> (D1) — element must not move in the DOM"
  - "Hand-rolled SVG + rAF, not recharts (D6/D7) — recharts stutters at 60 Hz"
  - "Trace is PERMANENT; only the control bar auto-hides (post-checkpoint item 1)"
patterns-established:
  - "Overlay passed to VideoPane as an `overlay` node so VideoPane stays the single writer of video_origin_s"
duration: ~multi-session (2026-08-13 → 2026-08-14, iterated live)
started: 2026-08-13
completed: 2026-08-14
---

# Phase 64 Plan 01: Fullscreen Video + Velocity Overlay Summary

**Shipped a hand-rolled SVG velocity strip over the video — inline on the report card and fullscreen — panned by one `requestAnimationFrame` loop with zero React state, then iterated live into a reusable `VideoTracePanel` with a colour picker, stroke-mark triangles and drag-to-scrub.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Fullscreen shows video + trace | Pass | Stage container fullscreens both; `object-contain` |
| AC-2: Native fullscreen trap gone | Pass | Custom `PlaybackControls` bar; no native `controls` in panel mode |
| AC-3: Window follows playhead smoothly | Pass | rAF `viewBox` pan; user-verified against real playback |
| AC-4: Boundaries + readout + seek | Pass | `start_idx/fsHz` triangles, live m/s readout, click-to-seek |
| AC-5: Sync repair via single writer | Pass | Bar calls VideoPane `nudge`/`saveSync`; 58-04 invariant held |
| AC-6: Windowed layout unchanged | Pass | Superseded by the item-3 refinement (panel now inline on the report card) |
| AC-7: Annotate page unaffected | Pass | `VideoPane` new props default to prior behaviour |
| AC-8: Graceful degradation (iOS Safari) | Pass | Fullscreen button hidden when `requestFullscreen` absent |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/TraceOverlay.js` | Created | SVG trace, rAF viewBox pan, triangles, drag-scrub |
| `web/components/portal/PlaybackControls.js` | Created | Custom bar (renamed from `FullscreenControls`) |
| `web/components/portal/VideoTracePanel.js` | Created | Inline+fullscreen container (post-checkpoint restructure) |
| `web/components/portal/VideoPane.js` | Modified | `panel`/`fullscreen` mode; overlay as a node prop |
| `web/app/app/sessions/[id]/video/page.js` | Modified | Uses the panel; `metrics_json` in select |
| `web/app/app/sessions/[id]/page.js` | Modified | Inline panel above the velocity chart (item 3) |

## Deviations from Plan

All user-driven, live at the checkpoint (documented in STATE 2026-08-14):
- **Restructured into a reusable `VideoTracePanel`** — the plan named only `TraceOverlay` +
  `FullscreenControls`; the bar became inline too, so `FullscreenControls`→`PlaybackControls` and a
  new container component appeared.
- **Item 3 (inline panel on the report card)** replaced the redirect link — broadened scope to
  `sessions/[id]/page.js`.
- **Adjustable rolling window** (reversed the plan's fixed-2 s D5) + **colour picker** (persisted) +
  **downward-triangle stroke marks** + **blur removed / compact strip**.
- **Drag-to-scrub** added after the 0f63a15 push and left uncommitted pending a live feel-test;
  committed with 64-03 (`fe3b53b`, 2026-08-16) after the user approved the feel.

## Commits

Base shipped `0f63a15` (→ Vercel, 2026-08-14). Post-checkpoint drag-to-scrub committed in `fe3b53b`
(64-03). Zero Python; suite untouched.

## Next Phase Readiness

**Ready:** `VideoTracePanel` + `TraceOverlay` are the surfaces 64-03 extended with acceleration.
**Concerns:** playback *smoothness* verified by the user watching real footage, not by the hidden
Browser pane (rAF is shim-driven there).

---
*Phase: 64-video-velocity-overlay, Plan: 01 — Completed 2026-08-14*
