---
phase: 69-multi-camera-video
plan: 03
subsystem: ui
tags: [react, nextjs, video, multi-camera, synced-playback, requestanimationframe]
requires:
  - phase: 69-multi-camera-video
    provides: 69-01 GET /videos unified list; 69-02 Videos page + CameraTile
provides:
  - MultiCamPlayer — synced grid on one master timeline (focused-plays perf model) + trace strip
  - report-card declutter (VideoTracePanel removed → compact Videos link)
affects: [report card, videos page]
key-files:
  created:
    - web/components/portal/MultiCamPlayer.js
  modified:
    - web/app/app/sessions/[id]/videos/page.js
    - web/app/app/sessions/[id]/page.js
    - web/components/portal/CameraTile.js
key-decisions:
  - "One master timeline drives all cameras; focused camera sets sessionTime + carries audio; others drift-corrected >0.2 s (not per-frame seek)."
  - "Report card drops the inline VideoTracePanel for a compact Videos link — the declutter the user asked for."
patterns-established:
  - "rAF sync loop lives in a useEffect keyed on isPlaying, reading latest state via a ref — no stale closures, no setState in the effect body."
duration: ~50min
started: 2026-08-17T02:55:00Z
completed: 2026-08-17T03:45:00Z
---

# Phase 69 Plan 03: Synced Multi-Cam Player + Report Declutter Summary

**A `MultiCamPlayer` that plays up to 4 camera angles side-by-side on ONE shared timeline — each video
seeks to `sessionTime − its origin`, the focused camera drives the clock and carries audio, the
others are drift-corrected — with a velocity trace strip riding the same playhead. The report card
drops its inline video panel for a compact "Videos" link. Compile + lint clean; live UAT owed.
Shipped `f03c4fd`.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| Synced player, one timeline drives all | Pass (compile) | Master scrub + play/pause; each camera seeks to sessionTime − origin; focused sets the clock. |
| Trace shares the timeline | Pass | Inline SVG velocity polyline + a playhead at sessionTime, spanning the grid width. |
| Focused-plays perf model (D6) | Pass (compile) | Focused camera plays with audio; others muted + drift-corrected only when >0.2 s off (not per-frame). |
| Report-card declutter | Pass (build) | `VideoTracePanel` + its `video` state/select fields removed; a compact Videos link replaces it (−26 net lines). |

## Verification Results
- `npx eslint` on MultiCamPlayer + CameraTile + videos page → **exit 0** (4 first-pass errors — a `tick`
  self-reference stale-closure risk + refs-during-render — fixed by moving the rAF loop into an
  effect reading latest state via a ref, and stable `useMemo` ref-callbacks).
- `npm run build` → **exit 0**; report card, /video, and /videos all compile.
- Report card's remaining 2 lint errors (lines 74, 161) are **pre-existing** effects, not touched here.
- ⚠ **Live UAT owed** — 4-video synced playback, drift, and audio focus cannot be verified without
  patch_12 + real clips + auth. This is the phase's highest-UAT-risk piece.

## Files Created/Modified
| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/MultiCamPlayer.js` | Created | Synced grid + master control bar + trace strip. |
| `web/app/app/sessions/[id]/videos/page.js` | Modified | Mount the player above the "Manage cameras" tiles. |
| `web/app/app/sessions/[id]/page.js` | Modified | Report-card declutter: remove VideoTracePanel + orphans → Videos link. |
| `web/components/portal/CameraTile.js` | Modified | `preload="metadata"` (lighten the dual-mount). |

## Deviations from Plan
| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | The declutter also removed the Phase-64 velocity/accel **trace toggles** that lived in VideoTracePanel; the report card's static charts now follow the persisted pref (default velocity-only) with no on-card toggle. The /video route still has them. Minor, accepted. |
| Design note | 1 | The player and the manage tiles each mount their own `<video>` (dual-mount, `preload=metadata`). An integrated single-video-set sync-mode is a future elegance polish. |

## Next Phase Readiness
**Ready:** Phase 69 is code-complete end-to-end (schema + API + Videos page + synced player + declutter).
**Concerns:**
- ⚠ **patch_12 not applied live** — nothing works until it is.
- ⚠ **The synced player is UAT-critical** — most likely to need iteration against real 4-camera playback.
- Free-tier 50 MB per-clip cap still applies (externals compressed).
**Blockers:** None for closing the phase; UAT + patch_12 are the user's gates.

---
*Phase: 69-multi-camera-video, Plan: 03 · Completed: 2026-08-17*
