---
phase: 58-video-ground-truth
plan: 02
subsystem: ui
tags: [react, recharts, nextjs, html5-video, annotation, coach-portal, tailwind]

requires:
  - phase: 57-annotation-workflow (57-01)
    provides: PHASE_KEYS / annotation_to_overrides contract, marks_per_cycle, out-of-window rule
  - phase: 57-annotation-workflow (57-02)
    provides: the annotate page v2 — undo-in-a-ref, suppressClickRef, fit-by-slicing, drag/nudge
  - phase: 47-trial-annotation
    provides: VideoPane, seekRef contract, the annotate route
provides:
  - Breakout removed from the annotation contract, tolerated on read, stripped on write
  - frame-step + slow-motion playback on VideoPane, exposed to the page via frameStepRef
  - mark-at-playhead (M) sharing one swim-window guard with chart clicks
  - modal arrow keys (frame-step vs mark-nudge) with Escape as the exit
  - viewport-responsive sizing for video, chart and tools panel
affects: [58-03 report-card visibility, 57-03 annotation queue, 16-06 segmenter tuning]

tech-stack:
  added: []
  patterns:
    - "A `//` comment between `return (` and JSX breaks SWC and `next build` STILL EXITS 0 —
       browser load is the verification for web plans, not the build"
    - "Viewport-responsive sizing via clamp(min,vh,max) verified against the live CSSOM, because
       inline-style clamps never appear in the CSS bundle to grep for"
    - "Retire a contract key with a LEGACY_PHASE_KEYS tolerance list: permissive read, strict write"

key-files:
  created: []
  modified:
    - annotations.py
    - tests/test_annotations.py
    - web/components/portal/VideoPane.js
    - web/components/portal/AnnotationChart.js
    - web/components/portal/AnnotationEditor.js
    - web/app/app/annotate/[id]/page.js

key-decisions:
  - "Breakout removed from the contract, not hidden; legacy values ignored on read, dropped on write"
  - "stroke_start_s keeps its meaning, so nothing recomputes — the distinguishing property vs 57-01"
  - "The first cycle contains the breakout: documentation only, in the docstring AND the UI"
  - "Mark-at-playhead does not select the new mark, or the step→mark→step loop breaks"
  - "Arrow keys are modal on selection; preventDefault is required or Chrome seeks ±5 s"

patterns-established:
  - "Web verification = loads in a browser with a clean console. `npm run build` exit 0 is not proof."
  - "Responsive sizing is measured at two viewports, not eyeballed at one."

duration: ~1 session (single sitting, 2026-08-07)
started: 2026-08-07
completed: 2026-08-07
---

# Phase 58 Plan 02: Annotate Page Usable With Video + Breakout Removed

**The annotate page now fits video and trace on one screen at any viewport size, lets a coach step
the footage frame by frame and drop a mark at the playhead, and no longer carries a Breakout marker
— without moving a single number on a single session.**

## Performance

| Metric | Value |
|--------|-------|
| Date | 2026-08-07 |
| Tasks | 3 auto + 1 checkpoint, all completed |
| Files modified | 6 (2 backend, 4 web) |
| Backend suite | 236 → **237 passed** |
| Web build | `npm run build` exit 0, 18 routes |
| Console | zero errors on a clean tab |
| Checkpoint | Approved by user |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Video and chart fit one viewport | **Pass** | Measured, not estimated: budget ~671 px of 720, ~934 of 1000. Checkpoint approved. |
| AC-2: Breakout gone, nothing recomputes | **Pass** | `PHASE_KEYS` and `PHASE_META` entries deleted; `annotation_to_overrides` untouched and pinned by a new test asserting a breakout-only doc yields `{}`. Suite 237 green with zero re-baselined assertions. |
| AC-3: Legacy breakout annotation survives | **Pass (unit-level)** | `test_legacy_breakout_key_tolerated` + `test_valid_full_doc`. ⚠ Not exercised against a real stored row — see Concerns. |
| AC-4: Frame-accurate scrubbing | **Pass** | Buttons + `frameStepRef`; `playbackRate` applied in an effect *and* `onLoadedMetadata`. Checkpoint approved. |
| AC-5: Mark at the video's current time | **Pass** | `M` → `placeStrokeMark(playheadS)`, one shared guard, undoable, no auto-select. Checkpoint approved. |
| AC-6: Arrow-key collision resolved | **Pass** | Modal on `selected`, `preventDefault()` on both branches, `Escape` exits, help text in the panel. Checkpoint approved. |

**Attestation boundary, stated plainly:** AC-2 and AC-3 rest on evidence I collected (tests, code,
greps). AC-1, AC-4, AC-5 and AC-6 require an authenticated session with video attached, which I
cannot reach — they rest on the user's checkpoint approval. AC-1's *arithmetic* was independently
measured in a real browser; its *appearance* was not.

## Accomplishments

- **Removed a marker from a live contract without touching a number.** `annotation_to_overrides`
  only ever read dive/stroke/finish, so Breakout could not reach `compute_session_metrics`. That
  made this the rare contract change with no comparability cost — explicitly unlike 57-01's v95
  fix — and a new test pins it rather than asserting it in prose.
- **Made the video actually usable for annotation.** It was rendered `w-full` with no height
  constraint; portrait footage would have been ~1244 px tall above a 340 px chart. Now both fit at
  any viewport, and the footage can be stepped one frame at a time at quarter speed.
- **Kept one copy of the swim-window rule.** `placeStrokeMark` is shared by chart clicks and
  mark-at-playhead. A second copy is precisely how a client guard drifts from the 57-01 server rule
  and starts accepting marks the server rejects.
- **Found that `npm run build` exit 0 does not mean the page loads.** See Issues — this is the most
  transferable thing the plan produced.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `annotations.py` | Modified | `breakout_start_s` out of `PHASE_KEYS`; new `LEGACY_PHASE_KEYS` tolerated by `validate_annotation` but excluded from the ordering walk; docstring rewritten with the new phase model and the first-cycle convention. |
| `tests/test_annotations.py` | Modified | 3 assertions updated, `test_legacy_breakout_key_tolerated` added (236 → 237). |
| `web/components/portal/VideoPane.js` | Modified | `clamp()` height cap + `object-contain`; `step()` (pauses first, pushes `onPlayhead` explicitly); `playbackRate` in an effect + `onLoadedMetadata`; `frameStepRef`; frame/speed controls. |
| `web/components/portal/AnnotationChart.js` | Modified | Breakout dropped from `PHASE_META`; `height` default became a CSS clamp string; `initialDimension` pinned to a literal number. |
| `web/components/portal/AnnotationEditor.js` | Modified | UW-kick "runs through the breakout" caption; first-cycle convention; keyboard help. |
| `web/app/app/annotate/[id]/page.js` | Modified | `max-w-7xl`; responsive grid; sticky scrolling sidebar; `placeStrokeMark` extracted; modal arrows + `Escape` + `M`; `frameStepRef` wired. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Keep the word "breakout" in `validate_annotation`'s docstring | It is an accurate historical note on why the swim-window check exists — the breakout is a physical region whether or not a marker names it. | The plan's grep expectation was not met; deleting correct documentation to satisfy a grep would be the worse trade. |
| Split, not replace, the `test_round_trip_upsert` assertion | The breakout assertion was carrying the "absent keys normalized" coverage under that comment. A straight swap would have silently dropped it. | Two assertions now: `underwater_start_s is None` keeps the old coverage, `"breakout_start_s" not in phases` pins the new behavior. |
| `initialDimension` pinned to a literal `320` | `height` became a CSS string; recharts needs a number there and a string would have silently zeroed the chart. | Pre-measurement guess only; real height comes from the parent div. |
| Chart clamp verified via the live CSSOM | It is an inline style, so unlike the Tailwind clamps it never appears in the CSS bundle — there was nothing to grep. | Confirmed accepted verbatim and computing correctly, with the 220 px floor honored at 720 px tall. |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | A self-inflicted parse error; caught before the checkpoint |
| Documentation judgment | 2 | Neither changes behavior |
| Scope additions | 1 | User-authorized at the checkpoint |
| Scope removals | 1 | Honoring a declined option |

**Total impact:** No scope creep. One addition, explicitly requested; one removal, to honor a choice
the plan had contradicted.

### 1. Parse error introduced and fixed (auto-fixed)

- **Found during:** browser verification after Task 3.
- **Issue:** I placed `//` comments between `return (` and the JSX. SWC begins JSX parsing right
  after the paren and reported the failure at the **closing brace ~90 lines below** the real cause.
  The dev server returned 500.
- **Fix:** comment moved above the `return`, with a note explaining why.
- **Why it matters beyond itself:** `npm run build` **exited 0 with the file in this state.** The
  plan's Task 3 verify listed both the build and a browser load; only the second caught it.

### 2. "breakout" retained in one docstring (documentation judgment)

Covered under Decisions. The plan's grep check was written too strictly.

### 3. Keyboard help landed in `AnnotationEditor.js` (documentation judgment)

Task 3's `<files>` listed only `page.js`, but its own `<action>` pointed at "the existing *Pick a
tool…* copy", which lives in the editor panel. Both files were already in `files_modified`.

### 4. Responsive sizing (scope addition, user-authorized at the checkpoint)

The plan's fixed `max-h-[34vh]` was a magic number. Replaced with viewport-relative clamps, measured
at two viewports:

| Element | Value | @720 h | @1000 h |
|---|---|---|---|
| Video | `max-h-[clamp(140px,26vh,420px)]` | 187 px | 260 px |
| Chart | `height="clamp(220px,30vh,480px)"` | 220 px *(floor)* | 300 px |
| Sidebar width | `clamp(260px,20vw,360px)` (was fixed 300 px) | — | 288 px @1440 w |
| Sidebar | `lg:sticky` + `lg:max-h-[calc(100dvh-2rem)]` + own scroll | keeps Save/Undo reachable | |

Vertical budget fits at both ends: **~671 px of 720**, **~934 of 1000**.

### 5. `VideoPane` end-anchor removed from scope

The plan listed it; the option the user declined at D8 was precisely the one bundling it. Moved to a
future 58 plan. **Consequence still live:** a record-with-video session must be opened once in Video
Overlay on the phone or it arrives at `origin_s = 0`, silently unsynced.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `npm run build` exit 0 on a file the dev server could not parse | Browser load caught it. Recorded as a standing rule: for web plans, verification is a clean browser load, not a clean build. |
| Two greps for `max-h-[34vh]` in the CSS bundle both returned 0, suggesting the class had not been generated | False alarm of my own making — CSS escapes the brackets (`max-h-\[34vh\]`), so both patterns missed a rule that was present. Corrected by reading the raw rule directly. |
| Bash tool working directory silently persisted/reset between `cd web` calls | Switched to absolute paths. |
| `read_console_messages` returns a retained buffer, so post-fix reads still showed the old parse error | Opened a fresh tab for a clean console read. |

## Next Phase Readiness

**Ready:**
- The annotate page is usable with footage, which is Phase 58's goal 3.
- 58-03 is written and awaiting approval (report-card visibility: the web stroke gate + the
  annotation-staleness diagnosis).

**Concerns:**
- ⚠ **R1 IS STILL UNANSWERED — for the second consecutive plan.** 57-02's SUMMARY had to record it
  as unknown; 58-02's checkpoint was approved without a report on it either. Whether ~40 arm-entry
  marks are genuinely placeable from footage, and whether the ~4° tripod angle is legible, remain
  **open**. This is not a formality: it gates Phase 53's Track A4 and the whole 16-06 tuning effort,
  and both 58-03 and 57-03 are being designed without the answer. Annotating one freestyle session
  end to end is all it takes.
- **AC-3 was never exercised against a real stored annotation** carrying `breakout_start_s` — only
  against unit fixtures. If no such row exists, that is fine and should be confirmed; if one does,
  it is worth one open-and-save.
- The frame step assumes 30 fps. If the tripod footage is 60 fps, each press moves two frames.
  Harmless but worth knowing.
- **Deploy order — CORRECTED 2026-08-07: either order is safe.** This summary originally said
  "never backend first". That rule was derived *before* D7b's `LEGACY_PHASE_KEYS` tolerance was
  written and was not re-derived once it existed — the tolerance is precisely what removes the
  constraint. A new backend accepts `breakout_start_s` from a stale page (`validate_annotation`
  skips retired keys, `api.py:857` drops it on write), so no 422 is possible; the only backend-first
  effect is a Breakout mark on a stale tab silently failing to persist, on a marker being abandoned.
  Web-first is equally fine. Recorded because the wrong rule was stated to the user twice.

**Blockers:** None.

---
*Phase: 58-video-ground-truth, Plan: 02*
*Completed: 2026-08-07*
