---
phase: 64-video-velocity-overlay
plan: 03
subsystem: ui
tags: [react, svg, recharts, localStorage, hooks, nextjs]
requires:
  - phase: 64-video-velocity-overlay (plan 02)
    provides: sessions.acceleration_profile (the data this plan displays)
  - phase: 64-video-velocity-overlay (plan 01)
    provides: TraceOverlay, VideoTracePanel, PlaybackControls
provides:
  - Acceleration on the overlay (stacked band) AND the static chart (AccelerationChart)
  - Page-owned trace prefs (show/colour) via useTracePrefs, shared by both surfaces
affects: [66-acceleration-derivative]
tech-stack:
  added: []
  patterns: ["per-band DOM-ref map driving one shared rAF loop for N stacked traces",
             "page-level display prefs hook shared across two routes"]
key-files:
  created: [web/components/portal/AccelerationChart.js, web/lib/useTracePrefs.js]
  modified: [web/components/portal/TraceOverlay.js, web/components/portal/PlaybackControls.js, web/components/portal/VideoPane.js, web/components/portal/VideoTracePanel.js, web/app/app/sessions/[id]/page.js, web/app/app/sessions/[id]/video/page.js]
key-decisions:
  - "Visibility + colours owned at the PAGE so overlay and static chart stay in sync (AC-4)"
  - "Stacked bands, each own signed/scaled y-domain — NOT overlaid on one axis"
  - "AccelerationChart is a sibling of VelocityChart; VelocityChart.js untouched (boundary)"
patterns-established:
  - "Two stacked overlay bands share ONE window/scrub/playhead via a per-band DOM-ref map"
duration: ~1 session + live checkpoint
started: 2026-08-16
completed: 2026-08-16
---

# Phase 64 Plan 03: Acceleration Trace (both surfaces) Summary

**Put acceleration alongside velocity on both surfaces — a second stacked band on the video overlay
(own signed scale + zero line + cyan colour + m/s² readout, sharing one window/scrub/playhead) and a
new `AccelerationChart` stacked under `VelocityChart` — with independent, page-owned, persisted
velocity/acceleration toggles and an acceleration colour picker that keep both surfaces in sync.**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 auto + 1 checkpoint (approved) |
| Files | 8 (2 created, 6 modified) |
| Build | `npm run build` exit 0 (×2) |
| Lint | 18 problems = baseline (net zero) |
| Python | none touched |
| Commit | `fe3b53b` (pushed → Vercel) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Overlay stacked acceleration strip | Pass | Probe: 2 bands, accel band viewBox `0 0 2.99 9.77`, zero line present |
| AC-2: Independent toggles, persisted, default velocity-only | Pass | `useTracePrefs` persists; probe toggles bands 2→0; reload persistence approved at checkpoint |
| AC-3: Static acceleration chart stacked | Pass | Probe: recharts signed y-axis −4.9…+4.9, zero ReferenceLine, m/s² |
| AC-4: Both surfaces sync within a page | Pass | Single page-level state feeds panel + charts |
| AC-5: Absent acceleration degrades cleanly | Pass | Probe: empty accel → "No acceleration data" card, no error |
| AC-6: Velocity behaviour unchanged | Pass | Default velocity-only; velocity band structure identical; build/lint green |

## Verification

- Build exit 0 after Task 3 and again after the window-preset change.
- Lint held at **18** (baseline): removed VideoTracePanel's persisted-colour effect, added the same
  idiom in `useTracePrefs` — net zero, no new error category.
- Throwaway probe route (`/probe6403`, deleted): confirmed two stacked bands with the accel zero
  line, the signed AccelerationChart, the empty state, and toggle wiring — no console errors. The
  hidden Browser pane freezes rAF, so live playhead motion/scrub feel was verified by the user.
- User approved the front-end ("the new additions look good"); pushed `fe3b53b`.

## Deviations from Plan

| Type | Item | Rationale |
|------|------|-----------|
| Scope addition (file) | Edited `VideoPane.js` (not in `files_modified`) | Required pass-through — it renders `PlaybackControls`; not in DO-NOT-CHANGE |
| Scope addition (file) | Added `web/lib/useTracePrefs.js` | Prefs needed identically on both pages; a shared hook beats duplicating 4 state vars + persistence and keeps lint flat |
| Refinement | Static chart gated on `showAcceleration` alone (not `&& accel.length`) | So a NULL-accel session shows the explicit "No acceleration data" card (AC-5), mirroring VelocityChart's empty-state idiom |
| User request (at checkpoint) | Window presets `1/2/4/All` → `2/4/8/All` | 1 s too narrow to read a stroke |
| Carried in | Committed the previously-unpushed 64-01 drag-to-scrub | It lived in the same two files; approved by the same checkpoint |
| Naming | Kept `lineColor` as the velocity-colour prop; added `accelColor` | Surgical — avoids churn in VideoPane/PlaybackControls/TraceOverlay |

`VelocityChart.js` untouched (boundary held). Zero Python.

## Known Limitation

**No-video sessions can't toggle acceleration.** The Show toggles live in the overlay's
`PlaybackControls`, which renders only when a video is attached. A no-video report card follows the
persisted pref (default velocity-only, so it looks exactly as before). Surfaced to the user; a
page-level toggle for no-video sessions would be a small follow-up, out of this plan's scope.

## Next Phase Readiness

**Ready:** acceleration renders end-to-end; Phase 66 improves the *data* (SG derivative) behind it
with no web change.
**Concerns:** the displayed acceleration is choppy because the stored derivation is a ~5 Hz
reconstruction — Phase 66 addresses it (display-only; no metric moves).

---
*Phase: 64-video-velocity-overlay, Plan: 03 — Completed 2026-08-16*
