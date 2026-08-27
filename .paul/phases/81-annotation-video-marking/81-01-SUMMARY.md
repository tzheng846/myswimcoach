---
phase: 81-annotation-video-marking
plan: 01
subsystem: ui
tags: [annotate, video, fullscreen, react, next, traceoverlay]

requires:
  - phase: 71-video-surface-rework
    provides: CameraTile multi-cam annotate hub (active-camera playhead/seek/frame-step wiring)
  - phase: 64-fullscreen-video-overlay
    provides: TraceOverlay rolling strip + stage-fullscreen pattern (mirrored, not reused)
provides:
  - In-video marker bar on the active annotate camera (Dive/UW/Stroke/Finish + stroke-mark, at the current frame)
  - Stage-fullscreen marking on the active camera (marker + playback controls survive fullscreen)
  - Strip rolling-window presets (4s / 8s / All)
  - Placed-mark ticks on the strip (in-fullscreen confirmation)
affects: [81-02, annotation-backlog, phase-78]

tech-stack:
  added: []
  patterns:
    - "Active camera = stage-fullscreen overlay (Fullscreen API on the stage div, not the <video>); custom control bar so it survives fullscreen"
    - "overlayMode = active && synced gate: native controls until synced (scrub to Set-sync landmark), custom marking stage once synced"
    - "One shared placeBoundary(): chart-tool click, number keys, and in-video buttons all round + snapshot identically"

key-files:
  created:
    - .paul/phases/81-annotation-video-marking/81-01-SUMMARY.md
  modified:
    - web/components/portal/CameraTile.js
    - web/app/app/annotate/[id]/page.js
    - web/components/portal/AnnotationEditor.js

key-decisions:
  - "Active camera → stage-fullscreen overlay; native <video> controls dropped ONLY on the active synced tile (their fullscreen strands custom buttons — the documented PlaybackControls reason)"
  - "Shared report-card components (VideoTracePanel/VideoPane/PlaybackControls/TraceOverlay) left UNTOUCHED — zero report regression"
  - "Finish got a button (the number-key scheme had skipped it, digit collision with kick=3)"
  - "Strip window presets = 4/8/All (dropped the report's tight 2s per user's explicit list); default 4s"
  - "Keys 1/2/4/5+M retained as a secondary alias; AnnotationEditor digit labels kept"

patterns-established:
  - "Marker confirmation without the chart: placed marks fed to TraceOverlay as pseudo-cycles (markCycles) → strip ticks"

duration: ~90min (across the session, 3 live redirections)
started: 2026-08-26
completed: 2026-08-26
---

# Phase 81 Plan 01: Annotation Video Marking Summary

**The active annotate camera became a stage-fullscreen video overlay whose control bar carries the marker buttons (Dive/UW/Stroke/Finish + stroke-mark) and 4/8/All window presets — so a coach marks at the on-screen frame in fullscreen without exiting. Shipped well beyond the plan's keyboard-only slice via three live redirections.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~90 min (interactive) |
| Started | 2026-08-26 |
| Completed | 2026-08-26 |
| Tasks | 2 planned auto-tasks + 3 user-directed expansions |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: number keys place/move single boundaries at playhead | Pass | Kept from the original apply; `placeBoundary` shared with the buttons |
| AC-2: key 5 / M append a stroke mark, guarded; key 3 no-op | Pass | Unchanged |
| AC-3: velocity context strip on the active tile | Pass (expanded) | Strip now lives inside the fullscreen stage with 4/8/All window presets |
| AC-4: number-key workflow discoverable in the editor | Pass | Editor "Keys" help + digit-prefixed palette retained |
| **Blocking human-verify checkpoint** | **NOT RUN** | Auth-gated annotate page; could not sign in. Shipped on user instruction + ESLint/compile verification + mockup design approval. ⚠ owed against a live synced-video session |

## Accomplishments

- **Fullscreen marking**: active camera fullscreens the *stage* (Fullscreen API), so the strip + a control bar (▶/❚❚ · −1/+1 · speed · **Window 4s/8s/All** · **Mark Dive/UW/Stroke/Finish · + mark** · ⛶) stay on screen — the coach marks the frame they see without exiting. This was the actual ask.
- **In-video marker bar** replaced the keyboard-only workflow as the primary path; each button places at the tile's exact `videoRef.currentTime + origin`.
- **Strip window presets** (4/8/All) wired to `TraceOverlay.windowS` (default 4s).
- **In-fullscreen confirmation**: placed marks render as ticks on the strip via `markCycles` (TraceOverlay used as-is).
- **Zero report-card regression**: no edits to any shared video component.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Code (all changes) | `a73db03` | feat | In-video fullscreen marker bar + window presets |
| Docs (close loop) | (this commit) | docs | SUMMARY + STATE + ROADMAP |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/CameraTile.js` | Modified (+260/−48) | Stage-fullscreen overlay + in-stage control bar (playback + Window 4/8/All + marker buttons + fullscreen); `overlayMode` gating; `markCycles` strip ticks |
| `web/app/app/annotate/[id]/page.js` | Modified (+79) | Shared `placeBoundary` helper (chart-tool/keys/buttons DRY); `phaseTools` + `markTimes` memos passed to the tile |
| `web/components/portal/AnnotationEditor.js` | Modified (+20/−3) | "Keys" help + digit-prefixed palette (the keyboard alias's docs) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Active camera → stage-fullscreen overlay | Native `<video>` fullscreen is browser-owned; custom marker buttons can't live in it | The marking camera drops native controls once synced; playback lives in the custom bar |
| `overlayMode = active && synced` | An unsynced external has no origin to map time or draw the strip, and needs free scrubbing to Set-sync | Unsynced/inactive tiles keep native controls; the tile becomes the marking stage only once synced |
| Leave shared components untouched | VideoTracePanel/PlaybackControls/TraceOverlay are shared with the read-only report card | Zero report regression — the whole reason CameraTile carries its own bar |
| Window presets 4/8/All, default 4s | User's explicit list; dropped the report's 2s | Reachable tight window is now 4s (was 2s default) — trivially reversible |
| Keep keys + editor digit labels | Keys still work as a fast alias; docs stay accurate | Secondary path retained |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Scope additions (user-directed) | 3 | Large — redefined the primary workflow |
| Auto-fixed | 1 | Alignment-scrub regression caught + fixed pre-ship |
| Deferred | 2 | Human-verify + 81-02 |

**Total impact:** The plan scoped a keyboard-only throughput slice with a read-only strip and explicitly *no* video-structure changes. The shipped result is a stage-fullscreen marking overlay — a materially larger, better-aligned outcome driven by the user in real time.

### Scope additions (user-directed, live)

1. **Keyboard → in-panel buttons.** User: *"not the workflow I wanted… options within the video panel… add markers at current time."* Added a marker button row to the tile.
2. **Marking in fullscreen.** User screenshot of the report overlay + *"upon fullscreen it should have options… right now you still need to exit."* AskUserQuestion → **"Annotate page's active camera."** Rebuilt the active tile as a stage-fullscreen overlay with the marker/playback bar inside it.
3. **Variable window sizing (4/8/All).** Added to the strip bar.

### Auto-fixed

**1. [regression] Active-tile alignment scrub lost when native controls dropped**
- **Found during:** the fullscreen-stage rewrite
- **Issue:** dropping native `controls` on the active tile removed the scrub bar; an *unsynced* tile also has no strip (needs an origin), leaving no way to scrub to the Set-sync landmark
- **Fix:** `overlayMode = active && effectiveOrigin != null` — native controls stay until synced; the marking stage engages only once synced
- **Verification:** ESLint + compile; logic-traced (unsynced active tile keeps the native player + the below frame/speed row)
- **Commit:** `a73db03`

### Deferred Items

- **Blocking human-verify** against a live synced-video session (auth-gated; user shipped without it). Owed before treating 81-01 as field-proven.
- **81-02**: key-3 underwater-kick marker + ALL backend (annotations / phase_metrics / api recompute).
- (Minor) Whether to keep the native scrub bar on the active synced tile (dropped; strip-drag + frame-step replace it) — revisit if it bites.

## Verification Results

- `npx eslint components/portal/CameraTile.js app/app/annotate/[id]/page.js` → **exit 0** (clean).
- Next.js/Turbopack route compile → **✓ Compiled**, `/app/annotate/[id]` served 200; `preview_logs level=error` → **no server errors** on a fresh server.
- Backend untouched (frontend-only) → pytest suite unaffected; not run.
- **Human-verify: not performed** (see AC table).

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Could not preview the real page (Supabase-auth-gated; credentials off-limits) | Verified via lint + compile + a faithful mockup; live human-verify deferred to the user |
| HMR "useEffect dep array changed size" warning | Hot-reload artifact of adding a dependency mid-session; gone on fresh load (ESLint react-hooks clean) |

## Next Phase Readiness

**Ready:**
- Fullscreen marking unblocks annotating the backlog fast (STATE item 9) — the throughput goal (D4) is served, pending the live human-verify.
- Shared report surfaces proven unaffected (no edits).

**Concerns:**
- Human-verify still owed; treat 81-01 as shipped-but-unverified in the field.
- Active synced tile has no native timeline scrub (by design); confirm the strip-drag + frame-step scrub is enough in practice.

**Blockers:** None for 81-02. Phase 81 stays 🚧 — 81-02 (key-3 kick marker + backend recompute) is still owed.

---
*Phase: 81-annotation-video-marking, Plan: 01*
*Completed: 2026-08-26*
