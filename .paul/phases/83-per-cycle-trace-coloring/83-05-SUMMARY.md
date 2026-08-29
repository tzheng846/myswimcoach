---
phase: 83-per-cycle-trace-coloring
plan: 05
subsystem: ui
tags: [react, svg, nextjs, tailwind, signal-visualization]

requires:
  - phase: 83-01
    provides: "`web/lib/cycleBands.js` numbering rule (`cycle_num + 1` else array position + 1), the lifted hover state in PhaseReportCard, and the `--color-cycle-*` tokens"
  - phase: 83-02
    provides: "`phases.kick_bands` (schema 4) — the Underwater panel's item array"
  - phase: 83-03
    provides: "`web/lib/cycleShape.js` (`resample`, pointwise median, POINTS, MIN_ITEMS) and the measured evidence that killed the MAD classifier"
provides:
  - "`web/lib/cycleTraces.js` — pure trace/gutter model, shape-agnostic over cycles and kick bands"
  - "`CycleOverlay` — the per-cycle overlay panel under the Swimming and Underwater insets"
  - "Pinned highlight state (`active = hovered ?? pinned`) across inset, gutter and CycleCharts"
  - "`scratch/overlay_render_check.mjs` — a reusable headless RENDER harness for web components"
affects: [83-04, 81-02, "STATE item 17 (cross-session shape baseline)", "STATE item 18 (kick-band tiling)"]

tech-stack:
  added: []
  patterns:
    - "Headless render check: transpile JSX with the bundled `typescript` package, emit CJS into web/node_modules, server-render with react-dom/server, assert on markup"
    - "Gutter model separated from trace model so numbering is mode-invariant while drawability is not"

key-files:
  created:
    - web/lib/cycleTraces.js
    - web/components/portal/phases/CycleOverlay.js
    - scratch/overlay_checks.mjs
    - scratch/overlay_render_check.mjs
  modified:
    - web/components/portal/phases/PhaseReportCard.js
    - web/lib/cycleShape.js

key-decisions:
  - "AC-3 OVERRIDDEN by user mid-verify: the `0 · breakout` gutter row is now an interactive hover target, not inert"
  - "Gutter wraps into columns at 10 rows — found on a live 15-kick underwater, not anticipated by the plan"
  - "`niceMax` DUPLICATED from PhaseVelocity.js (DO-NOT-CHANGE), guarded by a byte-equality check"
  - "`cycleShape.js` gained two `export` keywords beyond the boundary's 'header comment only'"
  - "`excludeBreakout` derived from the actual gold band, not raw `segmentationReliable`"
  - "Axis modes left as planned (seconds + normalized) — user declined the peak-align proposal"

patterns-established:
  - "Every new web component gets a headless render check, not just build + lint — build and eslint are both blind to the 83-01 failure class"
  - "A component self-gates on degenerate input (returns null) rather than the parent gating it"

duration: ~75min
started: 2026-08-29T13:00:00Z
completed: 2026-08-29T14:15:00Z
---

# Phase 83 Plan 05: Cycle/Kick Overlay Panel Summary

**Every stroke cycle and downkick now draws on one shared axis beneath its phase inset, with a
wrapping number gutter that hover-previews and click-pins across three surfaces — the honest
replacement for 83-03's measured-and-cut shape classifier.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~75 min |
| Tasks | 4 of 4 completed (3 auto + 1 blocking checkpoint) |
| Files created | 4 |
| Files modified | 2 |
| Python touched | **none** |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Swimming overlay renders the pack | **Pass** | Render check: 5 items → 5 paths, gutter, seconds axis, y-scale from the inset window |
| AC-2: Hover previews, click pins, highlight reaches all three surfaces | **Pass** | `active = hovered ?? pinned` (`??` passes `0` through correctly); `highlightN` swapped at both call sites |
| AC-3: Breakout excluded from pack, present in gutter | **Pass, then DEVIATED** | Row present and trace-less as specified — but the "does nothing on hover/click" clause was **overridden by the user**; it now highlights `n: 0` in the inset |
| AC-4: Normalized toggle swaps axis + adds median, no renumbering | **Pass** | Gutter `n` sequence proven identical across modes (32/32 lib checks); median gated at `MIN_ITEMS` = 5, never computed in seconds mode |
| AC-5: Underwater renders from kick_bands, breaststroke renders nothing | **Pass** | Verified live on a 15-kick underwater; breaststroke self-gates on the backend's empty `kick_bands` via the <2-trace rule |
| AC-6: Degenerate cases render nothing rather than something wrong | **Pass** | 1 item / empty / no velocity / bad fsHz all render `""`; dropout draws a pen-up gap in seconds and is listed-but-absent normalized |
| AC-7: Provenance stated, nothing else regresses | **Pass** | Badge unchanged; `PhaseVelocity.js` + `cycleBands.js` byte-identical (absent from `git diff`); build clean; suite 497 |
| AC-8: Human verify on a live session | **Pass** | User reviewed a live 15-kick underwater, requested two changes (gutter wrap, breakout hover), both applied, then approved |

## Accomplishments

- **`web/lib/cycleTraces.js`** (118 lines) — pure trace + gutter model. Shape-agnostic over
  `metrics_json.cycles` and `phases.kick_bands`, reusing 83-01's numbering rule verbatim so the
  cross-highlight key cannot drift. Separates the **gutter model** (mode-invariant `n` sequence)
  from the **trace list** (mode-dependent drawability) — that split is what makes AC-4's
  no-renumbering promise and AC-6's dropout behaviour compatible.
- **`CycleOverlay.js`** (298 lines) — controlled component, owns only the mode toggle. Renders
  `null` below two drawable traces, so every caller's degenerate case is handled in one place.
- **Three-surface highlight with a pin.** `hoverCycle ?? pinnedCycle` resolved once in
  `PhaseReportCard`; `setHoverCycle` still writes only the hover half, so a mouseleave cannot
  clobber a pin.
- **Two new scratch harnesses, 72 checks total** — 32 data checks + 40 render checks.
- **`cycleShape.js` partially un-parked** with its header corrected to say so. `analyzeShapes` and
  `K` remain parked and, verified by grep, **unimported anywhere**.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/cycleTraces.js` | Created (118) | Pure trace + gutter model; seconds and normalized modes, pointwise median, breakout row |
| `web/components/portal/phases/CycleOverlay.js` | Created (298) | The overlay panel — SVG pack + HTML gutter + mode toggle |
| `scratch/overlay_checks.mjs` | Created (187) | 32 data checks over the pure lib |
| `scratch/overlay_render_check.mjs` | Created (217) | 40 headless render checks — the 83-01 failure class |
| `web/components/portal/phases/PhaseReportCard.js` | Modified (+55/−4) | Import, pin state, `active` resolution, `highlightN` swaps, both panels rendered |
| `web/lib/cycleShape.js` | Modified (+15/−5) | Header corrected; `resample` + `median` exported |

## Verification Results

| Check | Result |
|---|---|
| `node scratch/overlay_checks.mjs` | **32/32** |
| `node scratch/overlay_render_check.mjs` | **40/40** |
| `npm run build` | clean, 19 pages |
| `npx eslint` (4 changed files) | clean apart from the pre-existing `set-state-in-effect` at `PhaseReportCard.js:276` |
| `pytest tests/` | **497 passed** — unchanged, proving no Python drifted in |
| `git diff --stat` on protected paths | **empty** — `PhaseVelocity.js`, `cycleBands.js`, `CycleCharts.js`, `metrics.py`, `phase_metrics.py`, `api.py`, `tools/` all untouched |
| Production CSS grep | all 6 consumed tokens survive tree-shaking; **no new tokens added** |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Breakout gutter row is an **interactive hover target** | User direction at the verify checkpoint. The row has no trace in the pack, but it *does* have a gold band in the inset — so it must be able to point at it | Overrides AC-3's "does nothing" clause. Stays visually dim (nothing to accent below); nothing in CycleCharts reacts, since 0 is outside that keyspace |
| Gutter **wraps at 10 rows** into equal columns | A 15-dolphin-kick underwater made a single column stand taller than the chart it labels. `grid-auto-flow: column` over a fixed row count is deterministic, unlike flex-wrap which needs a guessed height | Breakout row moved OUTSIDE the grid as its own full-width row, so its long label cannot set every column's width |
| `niceMax` **duplicated** from `PhaseVelocity.js` | It is a non-exported local there, and that file is DO-NOT-CHANGE (damaged by edits in both 83-01 and 83-02) | The overlay's y-axis must match the inset stacked above it. A render check asserts the two function bodies are **byte-identical**, so the copies cannot silently diverge |
| `cycleShape.js` gained **two `export` keywords** | Task 1 mandates importing `resample` and reusing the `median` helper; neither was exported. Impossible to satisfy under a literal "header comment only" reading | Widens the boundary minimally. `analyzeShapes`' body and `K` untouched and still unimported |
| `excludeBreakout` derived from the **actual gold band** | The plan said "true when `segmentationReliable`", but `buildBands` only synthesises the band when there is a real gap. Raw `segmentationReliable` would show a `0 · breakout` row explaining a band that is not on screen | Strictly narrower and matches AC-3's own precondition ("whose inset shows a gold n:0 band") |
| Rows carry a **`duration`** field | The planned `{n, available, reason}` shape left `durationKey` a dead parameter | Feeds each gutter row's accessible label |
| Axis modes **left as planned** | User declined the peak-align proposal (see Deferred) | Seconds + normalized ship as specified |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| User-directed changes at checkpoint | 2 | One overrides an AC; both improve the shipped panel |
| Boundary widenings | 2 | Both minimal, both required by the plan's own tasks |
| Scope additions | 2 | One demanded by the plan's success criteria; one a dead-parameter fix |
| Deferred | 1 | Peak-align, declined for this plan |

**Total impact:** No scope creep. The two boundary widenings are forced by internal contradictions
in the plan itself (Task 1 vs the DO-NOT-CHANGE list), and both are guarded by checks.

### User-directed at the AC-8 checkpoint

**1. [UI] Gutter ran past the bottom of the chart**
- **Found during:** AC-8, on a live 15-dolphin-kick underwater
- **Issue:** 15 stacked rows stood visibly taller than the 200-unit plot beside them
- **Fix:** `MAX_GUTTER_ROWS = 10`; above that the gutter fills down then wraps to the next column
  (`grid-auto-flow: column`, `gridTemplateRows: repeat(perCol, …)`). Breakout row lifted out of the
  grid into its own full-width row above it
- **Verification:** render checks — 9 rows → 1 column, 15 → 2 columns of 8, 25 → 3 columns of 9

**2. [Interaction] Breakout row should highlight `n: 0` on hover — AC-3 override**
- **Found during:** AC-8
- **Issue:** the plan made the row inert; the user asked for it to point at the gold band
- **Fix:** row is now a `<button>` with hover/focus/click handlers. Dimmed until active
- **Verification:** render checks — `activeN: 0` lights the row, dims nothing in the pack, and
  accents no trace (there is no `n: 0` trace, by design)
- ⚠ **Numbered `dropout` / `too-short` rows are still inert.** The same argument applies to them —
  they have no trace but do have an inset band — but the user asked only about the breakout, so
  this was left alone rather than generalised.

### Boundary widenings

**3. `web/lib/cycleShape.js` — two `export` keywords beyond the header comment**
- **Cause:** Task 1 requires `import { resample, median, POINTS, MIN_ITEMS }`; the boundary says
  only the header comment may be edited. Directly contradictory
- **Resolution:** exported the two helpers. `analyzeShapes`' body and `K` untouched; grep confirms
  `analyzeShapes` is still imported nowhere

**4. `niceMax` duplicated into `CycleOverlay.js`**
- **Cause:** the plan sanctioned this explicitly and asked that it be called out here
- **Guard:** `overlay_render_check.mjs` extracts both function bodies from source and asserts they
  are byte-identical, so the duplicate cannot drift silently

### Scope additions

**5. `scratch/overlay_render_check.mjs` — not in `files_modified`**
- **Cause:** the plan's success criteria demand "a render check rather than build+lint alone",
  but no task produced one
- **What it is:** transpiles the component with the bundled `typescript` package, emits CJS into
  `web/node_modules/.render-check`, server-renders with `react-dom/server`, asserts on markup, then
  cleans up. Needs no auth, so it works despite the Supabase-gated portal
- **Why it matters:** it directly targets 83-01's two silent-failure classes — no path may render
  with `stroke="none"`/`undefined`, and every trace path must carry real `d="M…"` geometry

**6. `duration` added to the row shape** — keeps `durationKey` from being a dead parameter

### Deferred

**Peak-alignment as a third x-axis mode.** Raised at the checkpoint when the user asked why
normalized exists and how it compares to align-left / align-center. The analysis:

- Align-left anchors on the cycle **start** — a segmentation artifact. All error accumulates
  rightward, which is exactly the fan visible at the right of the underwater pack.
- Align-center anchors on the **midpoint**, which inherits jitter from *both* boundaries and
  corresponds to no physical event. Argued against.
- **Peak-align** anchors on each cycle's velocity peak — the arm-pull, read from the signal itself,
  independent of segmentation. Spread would become real stroke variation, durations stay honest (no
  rescaling), and **it would largely dissolve 83-05 D5's accepted caveat** that auto-session spread
  "may be segmentation, not stroke."

Cost ~30 lines, frontend only, no schema. **User declined for this plan** ("never mind no change").
Recorded as STATE owed item 19.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Bash heredoc could not carry the JS/regex quoting for the scratch files | Switched to the Write tool for those files |
| A `python -c` insert matched the *first* `fs.rmSync` in the render harness, landing new checks above their fixture definitions | Relocated the block to the tail programmatically |
| Three wrap checks failed on first run | False alarm — the behaviour was correct (8/9/9 rows); the regexes did not allow the spaces React emits in `repeat(8, minmax(0, auto))`. Regexes relaxed, not the code |

## Corrections to prior STATE claims

- **STATE item 18 overstates the kick-tiling artifact's visibility at high kick counts.** The item
  says "~2 of ~5 underwater traces" depart the pack. On the live 15-kick session used for AC-8 the
  two tiling bands are 2 of 15, and the pack read as tight. The defect is real and the fix is still
  owed — but its *visual* severity scales inversely with kick count, which the item does not say.

## Next Phase Readiness

**Ready:**
- `cycleTraces.js` is shape-agnostic and already proven against both a `cycle_num` and a `kick_num`
  array, so a third item source needs no lib change.
- The render-check harness is reusable for any future `web/components` work and is the concrete
  answer to 83-01's "build and lint are blind to this" lesson.
- Pin state exists in `PhaseReportCard` and can carry additional consumers.

**Concerns:**
- **`niceMax` is duplicated.** Guarded by a byte-equality check, but the real fix is exporting it
  from `PhaseVelocity.js` once that file is no longer under a DO-NOT-CHANGE boundary.
- **STATE item 18 shipped knowingly** (83-05 D8). Bands 1 and N of every underwater are the glide
  and the breakout transition, not kicks. Anyone reading the overlay must know this.
- **STATE item 17 remains open.** `resample` and the median are now wired; the MAD gate is not.
- **D5's auto-session posture survived the verify unchanged** — the user did not ask for caution
  copy, so auto sessions render the pack with only the existing `auto` badge to signal that spread
  may be segmentation rather than stroke.

**Blockers:** None.

⚠ **Phase 83 is NOT complete.** PLAN/SUMMARY counts are now 4/4 — the exact heuristic that has
falsely signalled "phase done" at 83-01, 83-02 and 83-03. **83-04 (inset window framing) is scoped
in STATE but has no PLAN.** No phase transition, no phase commit.

---
*Phase: 83-per-cycle-trace-coloring, Plan: 05*
*Completed: 2026-08-29*
