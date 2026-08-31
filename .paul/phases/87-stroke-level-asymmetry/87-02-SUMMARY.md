---
phase: 87-stroke-level-asymmetry
plan: 02
subsystem: ui
tags: [react, nextjs, svg, recharts, localstorage, accessibility, render-check]

requires:
  - phase: 87-stroke-level-asymmetry
    provides: metrics_json.strokes + the seven session asymmetry keys (87-01), backfilled to 47/101 sessions
  - phase: 83-per-cycle-trace-coloring
    provides: buildBands / buildTraces / CycleOverlay, the s.n % 2 band parity colouring, and the headless render-check harness
  - phase: 75-report-card
    provides: PhaseReportCard, its four phase sections and the Swimming cycleCharts slot
provides:
  - a cycles / strokes toggle in the Swimming section header, persisted globally
  - web/lib/strokeStats.js — deriveMeans + armBalance (pure)
  - numberKey seam on cycleBands + cycleTraces; parity tagging and per-side medians on cycleTraces
  - colorByParity on CycleOverlay, itemLabel on CycleCharts / TrendPanel / PhaseVelocity
  - the Arm balance readout — 3 signed asymmetry percentages + 4 per-side CVs
  - scratch/stroke_toggle_check.mjs — 63-check headless render gate over the whole PhaseReportCard
affects: [ratings, compare-page, mobile-report-card, any-future-per-side-baseline]

tech-stack:
  added: []
  patterns:
    - "numberKey/itemLabel seams keep one component shape-agnostic across two keyspaces rather than forking it"
    - "Headless render checks assert on captions, not on recharts geometry, which does not render server-side"

key-files:
  created: [web/lib/strokeStats.js, scratch/stroke_toggle_check.mjs]
  modified:
    - web/lib/cycleBands.js
    - web/lib/cycleTraces.js
    - web/components/portal/phases/CycleOverlay.js
    - web/components/portal/CycleCharts.js
    - web/components/portal/phases/PhaseVelocity.js
    - web/components/portal/phases/PhaseReportCard.js
    - web/app/app/sessions/[id]/page.js

key-decisions:
  - "D1 confirmed in code: side A is blue and side B purple for free — PhaseVelocity's s.n % 2 band colouring already agrees with 87-01's even-array-position side A"
  - "D4: stroke-level means re-derived client-side with population std; the stored session.mean_* keys are cycle-level and are never shown under stroke dots"
  - "D9: the Arm balance readout states magnitude and direction and passes no verdict — no threshold, no good/bad colour, unit-invariant"
  - "DEV-1: AC-7's hover/pin clearing lives in the toggle's click handler, not an effect on mode — the repo's eslint errors on react-hooks/set-state-in-effect"

patterns-established:
  - "Two keyspaces in one section are switched by a single derived `mode`, and hover/pin are cleared at the switch so numbers from one can never highlight the other"
  - "A render check may rewrite a state initializer in its own transpiled copy to reach an effect-gated mode, provided it asserts the exact initializer exists"

duration: ~95min
started: 2026-08-31T14:40:00Z
completed: 2026-08-31T16:17:00Z
---

# Phase 87 Plan 02: Stroke-level view — frontend toggle + visuals

**The Swimming section of the coach report card now switches between cycles and strokes on one
click — inset bands, count badge, overlay pack and all four trend panels rebuild from
`metrics_json.strokes` — and a new Arm balance block renders 87-01's three signed asymmetry
percentages and four per-side CVs, with side A blue and side B purple in all three places at once.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~95 min |
| Started | 2026-08-31T14:40Z |
| Completed | 2026-08-31T16:17Z |
| Tasks | 4 auto + 1 blocking human-verify, all complete |
| Files modified | 9 (7 modified, 2 created) |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: toggle appears only where it means something; cycle mode unchanged | Pass | `stroke_toggle_check.mjs` §1–2 — six legacy strings present with `strokes: null`, `>strokes<` / `Arm balance` / `arm-by-arm` / `% apart` / `Stroke Duration` all absent; with strokes present the toggle renders with `cycles` pressed and the card is still the cycle card |
| AC-2: one click switches four surfaces together and nothing else | Pass | §3 — badge `14 strokes · annotated`, `every stroke on one axis`, both panel titles, footer noun, and band count 7 → 14; §9 — Underwater badge still `3 kicks · auto` and its overlay still `every kick on one axis` |
| AC-3: stroke-mode means are stroke-level, never the stored cycle-level ones | Pass | §4 — fixture with cycle duration 1.10 s and stroke 0.55 s prints `mean 0.55 s` and never `mean 1.10 s`; distance `mean 1.15 m` never `2.30 m`; CV recomputed (`0%`) not the stored `8%` |
| AC-4: A and B are identifiable, and the naming colour is the drawing colour | Pass | §5 — inset band colours in document order are `idle, breakout, a, b, a, b …` with strict alternation; the Arm balance A chip carries `background-color:var(--color-cycle-a)`; no path strokes `none`/`undefined`; no left/right wording |
| AC-5: signed, unit-invariant, verdict-free, degrades honestly | Pass | §6 — `6.2% apart` / `A slower`, a negative tempo names B, the imperial render's Arm balance block is byte-identical to the metric one, and a single null key collapses to the not-enough-strokes line while bands and charts keep rendering |
| AC-6: overlay shows the two sides, gated on having enough of each | Pass | §7 — two medians at 5 traces a side, neither at 4, cycle mode still returns exactly one combined median and `side: null` |
| AC-7: the two keyspaces never mix | Pass | Hover and pin are cleared inside `chooseGranularity` (see DEV-1) |
| AC-8: blast radius | Pass | `git status` lists exactly the nine planned files; `PhaseVelocity.js` is +5/−1 (one optional parameter, one aria interpolation, and the comment explaining why); `overlay_render_check.mjs` 40/40 and `marketing_render_check.mjs` 45/45 both pass **unedited**; §8 pins `buildBands` default numbering and PhaseVelocity's default `coloured one band per cycle` |
| AC-9: verified on a live session | Pass | Human-verify approved on the running dev server |

## Verification Results

| Command | Result |
|---------|--------|
| `node scratch/stroke_toggle_check.mjs` | 63 passed, 0 failed, exit 0 |
| `node scratch/overlay_render_check.mjs` | 40/40, file unedited |
| `node scratch/marketing_render_check.mjs` | 45 passed, 0 failed, file unedited |
| `npm run build` (web/) | clean |
| `npx eslint .` (web/) | 26 problems / 23 errors vs a **25 / 22 pre-existing baseline** — see DEV-2 |
| `pytest tests/` | 563 passed — unchanged from the post-87-01 baseline, no Python in this diff |

Skill audit: no `.paul/SPECIAL-FLOWS.md` in this project — not applicable.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/strokeStats.js` | Created | `deriveMeans` (stroke-level means/CVs, population std) + `armBalance` (display model for the seven 87-01 keys). Carries 87-01's r = −0.06 caveat verbatim |
| `scratch/stroke_toggle_check.mjs` | Created | 63-check headless render gate over the whole `PhaseReportCard` in both modes |
| `web/lib/cycleBands.js` | Modified | `numberKey` option, defaulting to `cycle_num` |
| `web/lib/cycleTraces.js` | Modified | `numberKey` + `parity`; `side` on every row and trace; `medianA` / `medianB` gated per side |
| `web/components/portal/phases/CycleOverlay.js` | Modified | `numberKey`, `colorByParity`; per-side tint and the two per-side medians replacing the combined one |
| `web/components/portal/CycleCharts.js` | Modified | `itemLabel` on both the default export and `TrendPanel`; drives four strings plus the two mode-dependent panel titles |
| `web/components/portal/phases/PhaseVelocity.js` | Modified | D6's single exception — one optional `itemLabel`, used only in the banded aria-label |
| `web/components/portal/phases/PhaseReportCard.js` | Modified | `strokes` prop, granularity state + effect hydrate, the toggle, all mode-dependent wiring, and the `ArmBalance` block |
| `web/app/app/sessions/[id]/page.js` | Modified | One line — `strokes={metrics.strokes}` |

## Decisions Made

All ten plan decisions (D1–D10) were carried out as written. Two were confirmed against live code
rather than taken on faith:

| Decision | Confirmed how | Impact |
|----------|---------------|--------|
| D1 — the existing alternating band colours already ARE the A/B sides | `PhaseVelocity.js:238-240` still reads `s.n % 2 ? cycle-a : cycle-b`; `stroke_num` 0 → `n = 1` → odd → `cycle-a` | Zero change to the band renderer; the alignment is now pinned by a render assertion on the actual colour sequence, not by a comment |
| D6 — one optional `itemLabel` on `PhaseVelocity`, nothing else | Diff is +5/−1, geometry and `geom` untouched; the harness pins the default string | The standing DO-NOT-CHANGE on that file survives intact |

One decision was taken during execution:

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Clear hover/pin in the toggle's click handler rather than an effect on `mode` | The repo's eslint config errors on `react-hooks/set-state-in-effect`, and a click is the only way `mode` ever changes under a coach's hand | AC-7 satisfied with one fewer lint error and one fewer render pass; see DEV-1 |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Approach changed | 1 | DEV-1 — same behaviour, simpler mechanism |
| Verification criterion unmeetable as written | 1 | DEV-2 — pre-existing, not introduced here |
| Harness limitation worked around | 1 | DEV-3 — stated in the file, covered by the human-verify |
| Scope additions | 0 | — |
| Deferred | 2 | Both are 87-01's, carried forward rather than closed with the phase |

**Total impact:** no scope creep; the nine planned files and nothing else.

### DEV-1 — AC-7's clearing is in the click handler, not an effect

- **Found during:** Task 3 (the toggle and wiring)
- **Plan said:** *"Clear `hoverCycle` and `pinnedCycle` whenever `mode` changes (AC-7)"*, which reads
  as an effect on `mode`.
- **What was built:** both are cleared inside `chooseGranularity`, next to the `setGranularity` call.
- **Why:** the repo's eslint errors on `react-hooks/set-state-in-effect`; an effect here would have
  added a second new error and a cascading render, for a state change that only ever originates from
  this one click.
- **Residual gap, stated rather than hidden:** if `mode` ever flipped for a reason other than the
  click — `strokes` arriving asynchronously after a hover — the clear would not fire. In practice
  `strokes` arrives with `cycles` in the same `metrics` object, so there is no such path today.
- **Verification:** covered by the human-verify; not machine-checked (hover is a DOM event and the
  harness renders statically).

### DEV-2 — `npx eslint .` could not be met literally

- **Found during:** Task 3 verification
- **Issue:** the plan's checklist asks for `npx eslint .` clean. It is **not** clean at baseline:
  25 problems / 22 errors before this plan, including `lib/useTracePrefs.js` and
  `PhaseReportCard`'s own pre-existing `dismissed` localStorage hydrate.
- **What this diff adds:** exactly **one** new error — the granularity hydrate, the same
  `react-hooks/set-state-in-effect` rule, the same pattern, two lines below the `dismissed` one.
  It is **required by D2**: reading `localStorage` in a lazy initializer desyncs hydration, and that
  rule is written at the top of `useTracePrefs.js` and obeyed throughout this file.
- **Verified by:** `git stash` → eslint → `git stash pop` → eslint, 25 → 26 problems.

### DEV-3 — the render check cannot reach stroke mode from outside

- **Found during:** Task 4
- **Issue:** `renderToStaticMarkup` never runs effects, and the granularity preference is hydrated
  in an effect on purpose (D2). Stroke mode is therefore unreachable through props. No DOM library
  (jsdom, happy-dom) is installed in `web/`, and adding one is outside this plan's files.
- **Workaround:** the harness rewrites the one `useState("cycle")` initializer to
  `useState(globalThis.__TEST_GRANULARITY__ || "cycle")` **in its own transpiled copy**. Production
  source is untouched, and the harness asserts the exact initializer string exists before rewriting
  it, so the trick fails loudly if that line ever moves.
- **What stays uncovered:** the hydrate itself. That is step 6 of the human-verify ("reload — still
  on strokes"), which passed.

### Deferred Items

Neither is a defect in this plan; both are 87-01 realities that the plan's own `<output>`
deliberately leaves open, and both must survive the phase transition as owed items:

- **Backstroke is still unverifiable** — 0 annotated backstroke sessions in the library. It shares
  freestyle's code path exactly, so the toggle and the readout will render for it, but nothing about
  it has been checked against a human mark. (STATE item 10.)
- **The auto-path asymmetry is still uncorrelated with coach-mark truth** — Pearson r = −0.06,
  median error 10.2 percentage points against a 6.1% median signal. Shipped on the user's explicit
  call (87-01 D2 / this plan's D8), marked only by the existing `auto` chip. The number is now
  *visible to a coach*, which raises the stakes on that decision without changing it.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| First run of the render check found 3 bands where 14 were expected, and the wrong colour sequence | The colour extractor was reading the **Underwater** inset — it comes first in the section order and is banded too. Switched to `lastIndexOf("one band per")`, which is always the Swimming inset since Whole race carries no bands. Harness-only fix; no product code involved |
| `pytest` and the Python diff look like this plan's work | They are 87-01's, still uncommitted at APPLY time. Confirmed by file list: this plan's diff is the nine planned files and no `.py` |

## Next Phase Readiness

**Ready:**

- The individual arm stroke is now visible end to end — segmented (87-01), stored, backfilled, and
  rendered. Everything downstream that wants per-side numbers has both the data and a display
  vocabulary (`side`, `A`/`B`, the two colour tokens) to reuse.
- `numberKey` / `itemLabel` are general seams. A second consumer of `metrics_json.strokes` — the
  Compare page, mobile, a per-side baseline — can reuse `buildBands`, `buildTraces`, `CycleOverlay`
  and `CycleCharts` without forking any of them.
- `scratch/stroke_toggle_check.mjs` joins `overlay_render_check.mjs` and `marketing_render_check.mjs`
  as a standing regression gate over the report card.

**Concerns:**

- **The strips still compare per cycle** (87-01 D4). Stroke mode says so in one line, but a coach
  reading a 6% tempo split has no usual-range band for it. A per-side baseline is the natural next
  ask and needs backend work — `phase_metrics.py` was deliberately untouched.
- **The A/B colour alignment is an alignment, not a mechanism.** It holds only while `stroke_num`
  is dense and 0-based. AC-4's colour-sequence assertion is what catches a backend change that
  breaks it; do not weaken that check.
- **47 of 101 sessions carry `strokes`.** On the other 54 the toggle is simply absent — the designed
  degradation, but it means the feature is invisible on just over half the library until those
  sessions are reprocessed.
- **Neither 87-01's backend nor this frontend is deployed.** The whole phase sits uncommitted-then-
  committed locally; the backfill has already been applied to the live DB, so deploy ordering is a
  live question rather than a hypothetical.

**Blockers:** None.

---
*Phase: 87-stroke-level-asymmetry, Plan: 02*
*Completed: 2026-08-31*
