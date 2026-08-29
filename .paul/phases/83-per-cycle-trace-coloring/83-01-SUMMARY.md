---
phase: 83-per-cycle-trace-coloring
plan: 01
subsystem: ui
tags: [react, nextjs, tailwind-v4, svg, recharts, dataviz]

# Dependency graph
requires:
  - phase: 75-05
    provides: PhaseVelocity inset + the v3 report-card visual language
  - phase: 75-07
    provides: PhaseReportCard as the primary /app/sessions/[id] body, with CycleCharts under Swimming
  - phase: 75-06
    provides: the four completed phase sections (uncommitted tree this plan stacks on)
provides:
  - web/lib/cycleBands.js — pure, shape-agnostic band model (cycles today, kicks in 83-02)
  - PhaseVelocity optional bands/highlightN/onHoverBand props
  - Swimming inset per-cycle coloring, boundary ticks, outlier halo, provenance badge, hover readout
  - CycleCharts/TrendPanel optional highlightN/onHoverN cross-highlight props
affects: [83-02, 75-08, 75-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Grey base path overdrawn by coloured segments — gaps need no complement computation"
    - "@theme static for tokens consumed only via raw var()"
    - "Parent owns cross-surface hover state; both children take it as optional props"

key-files:
  created: [web/lib/cycleBands.js]
  modified:
    - web/components/portal/phases/PhaseVelocity.js
    - web/components/portal/phases/PhaseReportCard.js
    - web/components/portal/CycleCharts.js
    - web/app/globals.css
    - web/app/app/sessions/[id]/page.js

key-decisions:
  - "Band alternation keyed on the cycle's OWN number, not survivor position — a dropped band never flips parity downstream"
  - "Hover readout REPLACES the inset caption rather than adding a line, so the four charts don't shift mid-gesture"
  - "segmentationReliable threaded explicitly from the page; provenance is never inferred from an annotation row"
  - "@theme static is load-bearing, not cosmetic — a plain @theme block compiles the band colours away"

patterns-established:
  - "Any new theme token read only through var() must live in an @theme static block"
  - "Verify SVG colour work by reading computed styles, not by build+lint — both pass on invisible output"

# Metrics
duration: ~2h
started: 2026-08-28
completed: 2026-08-29T01:06:22Z
---

# Phase 83 Plan 01: Per-Cycle Trace Coloring (cycles half) Summary

**The Swimming inset now draws one alternating blue/purple band per `metrics_json.cycles` entry over a
neutral-grey base — with boundary ticks, an amber halo on the duration outlier, an annotated-vs-auto
count badge, a per-band hover readout, and bidirectional highlight with the four per-cycle charts — so
a coach can finally audit segmentation by eye. Frontend only; suite unchanged at 485.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2h |
| Completed | 2026-08-29T01:06:22Z |
| Tasks | 4 of 4 (3 auto + 1 blocking checkpoint) |
| Files modified | 5 modified, 1 created |
| Python diff | none — `pytest tests/` 485 passed |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Cycles render as alternating bands | **Pass** | 8-cycle fixture → 1 grey base path + 8 paths alternating `--color-cycle-a`/`-b` + 9 boundary ticks; every sample outside a band left grey |
| AC-2: Count badge states count + provenance | **Pass** | `8 cycles · annotated` with `segmentationReliable` true; `1 cycle · auto` when false; N equals band count |
| AC-3: Per-band hover readout | **Pass** | Hovering band 3 → `Cycle 3 · 0.95 s · 1.74 m/stroke · peak 2.04 m/s`, matching the stored cycle object exactly (not recomputed) |
| AC-4: Bidirectional cross-highlight | **Pass** | Inset hover → band to 3.8px/opacity 1, others dimmed, 4 `#f0f2f5` ReferenceLines in the panels. Chart hover at 72% → Cycle 6, band index 7 raised. Mouse-leave restores both |
| AC-5: Outlier carries an amber outline | **Pass** | 5-cycle fixture with one long cycle flags exactly one; halo strokes at 6.5px under the band's own 2.4px colour, so alternation is unaffected. `<3` bands flags nothing |
| AC-6: Degenerate inputs + Compare un-regressed | **Pass** | zero-cycle, one-cycle, and cycles-outside-window all fall back to the plain `--color-primary` trace with no badge and no console error. `CompareCycleCharts` passes neither new prop → handlers `undefined`, highlight line not rendered |
| AC-7: Visual approval | **Pass** | User approved on the live portal, 2026-08-28 |

## Verification Results

```
cd web && npx next build     → Compiled successfully, 19 pages (unchanged)
npx eslint <5 touched files> → 0 warnings
                               (4 pre-existing set-state-in-effect errors in untouched effects remain)
python -m pytest tests/ -q   → 485 passed, 1 warning
```

`buildBands` was additionally asserted against 13 cases in an ESM harness — empty/null input, missing
options, degenerate rows, clamping, drop-without-renumber, `<3`-band and non-finite-duration outlier
suppression, and a `{kick_num, interval_s}` fixture proving the `durationKey` path 83-02 will use.

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/cycleBands.js` | Created (72 lines) | Pure band model: filter degenerates, clamp to `[i0,i1]`, preserve the original 1-based `n`, flag one duration outlier. No React, no SVG geometry |
| `web/components/portal/phases/PhaseVelocity.js` | +108/−4 | Optional `bands`/`highlightN`/`onHoverBand`. Grey base path, overdrawn alternating segments, amber halo, boundary ticks, transparent hit rects |
| `web/components/portal/phases/PhaseReportCard.js` | Modified | `swimBands` memo, lifted `hoverCycle` state, count badge, `cycleReadout`; `toIdx` hoisted to module scope |
| `web/components/portal/CycleCharts.js` | +55/−12 | Optional `highlightN`/`onHoverN` on `TrendPanel` and `CycleCharts`; `data` memoized against hover churn (R4) |
| `web/app/globals.css` | +14 | New `@theme static` block: `--color-cycle-a/-b/-idle` |
| `web/app/app/sessions/[id]/page.js` | +5/−1 | Passes `segmentationReliable` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Alternate on the cycle's own `n`, not survivor index | A band dropped by clamping would otherwise flip the colour parity of every band after it, and desync the `CycleCharts` highlight key | Cross-highlight stays correct even when cycles overhang the swim window |
| Draw the full window grey first, overdraw bands | The inter-cycle gaps then require no complement computation | Cheapest possible satisfaction of D3 ("everything outside a band is neutral grey") |
| Hover readout replaces the caption | Adding a line would push the four charts down mid-gesture, exactly while the coach is reading them | Layout is stable during hover; caption returns on leave |
| Provenance passed explicitly, never inferred | `segmentation_reliable` flips true only on the recompute-from-annotation path; an annotation row existing is not the same fact | Badge cannot lie about whose cycles these are |
| `@theme static` for the three new tokens | Tailwind v4 tree-shakes theme variables no utility class references | Load-bearing — see auto-fix 2 |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 2 | Both were silent-failure bugs; the feature did not work without them |
| Scope additions | 1 | One extra file, plan-sanctioned |
| Deferred | 0 | — |

**Total impact:** Essential fixes only, no scope creep. All within the plan's boundaries — no Python,
no recharts velocity pair, no `TraceOverlay`, no Compare behaviour change.

### Auto-fixed Issues

**1. [correctness] `bands` prop shadowed inside `PhaseVelocity`'s `geom` memo — the prop was never read**
- **Found during:** Task 2 verification (ESLint flagged `bands` as an *unnecessary* memo dependency)
- **Issue:** `geom` already declares a local `const bands = []` for the hero variant's phase-tint rects.
  The new `for (const b of bands ?? [])` therefore iterated the local array, not the prop — so no cycle
  band would ever have rendered.
- **Fix:** Aliased the prop on destructure: `bands: cycleBands = null`.
- **Files:** `web/components/portal/phases/PhaseVelocity.js`
- **Verification:** ESLint warning cleared; 8 band paths present in the rendered DOM.

**2. [correctness] Tailwind v4 tree-shook the new colour tokens → every band rendered `stroke: none`**
- **Found during:** Task 2/3 visual check (the render showed only the amber halo — the one pre-existing
  token — with the rest of the trace invisible)
- **Issue:** Tailwind v4 only emits `@theme` variables that a utility class references. The three new
  colours are read **only** as raw `var()` inside an SVG `stroke` attribute, so they were compiled out.
  `getComputedStyle` returned `""` for all three and `stroke` resolved to `none`.
- **Fix:** Moved them into their own `@theme static` block, with the reason recorded in a comment.
- **Files:** `web/app/globals.css`
- **Verification:** tokens resolve to `#2196f3 / #a970ff / #55606b`; band stroke computes to
  `rgb(33, 150, 243)`; bands visible in the rendered screenshot.
- ⚠ **Neither bug is detectable by `next build` or `eslint`** — both pass cleanly on invisible output.
  Only a computed-style/render check catches them. This is the durable lesson for 83-02.

### Scope Additions

**`web/app/app/sessions/[id]/page.js` joined `files_modified`** — plan-sanctioned. The plan said to add
`segmentationReliable` "as an explicit prop from the page rather than inferring it" if it was not already
threaded; it was not. One prop plus a comment.

### Other deviations
- **`@theme static`** rather than the plain additive `@theme` block the plan specified (see auto-fix 2).
- **Hover readout replaces the caption** instead of sitting beneath it (reflow avoidance).
- **Badge pluralises** — the plan's literal template rendered `1 cycles`.
- **`toIdx` hoisted to module scope** in `PhaseReportCard` so the band memo has a stable reference
  instead of taking a new closure as a dependency each render.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Portal is Supabase-auth-gated, so the render could not be reached directly | Built a throwaway `/devpreview83` route with a synthetic 12 s / 89.5 Hz session + 8 cycles, verified all four AC cases plus both hover directions through it, then deleted the route (confirmed clean in `git status`) |
| Synthetic `mouseover`/`mouseenter` events do not reach React 19's delegated listeners | Drove real trusted events via the browser tool's `hover` action instead |
| Port 3000 held by another chat's dev server, then released | Verified against that server during development; started this session's own once the port freed |

## Next Phase Readiness

**Ready:**
- `web/lib/cycleBands.js` is pure and shape-agnostic — 83-02 passes `metrics_json.kicks` with
  `durationKey: "interval_s"` and needs **no modification** (asserted against a kick-shaped fixture).
- `PhaseVelocity` band rendering is generic; the Underwater inset needs only a `bands` prop.
- The three colour tokens are already defined and emitted, ready for kick bands.

**Concerns:**
- Phase 83 is **not complete** — 83-02 (kick band derivation, `metrics_json.kicks` persistence at three
  write sites, the Underwater inset, breaststroke gating, and the shared backfill) is still owed. No
  phase transition or phase commit was run for that reason.
- This diff sits on the **uncommitted 75-06 tree**, and `PhaseReportCard.js` now carries both plans'
  changes. `web/lib/phaseValence.js` is 75-06's alone. Hunk-level staging is unavailable here, so the
  next commit takes the whole tree — same constraint already recorded for `api.py` / 82-01.
- Palette values (amber halo blending toward olive over its band's colour; navy ticks reading dim on
  `--color-surface-2`) were approved as-is but are the natural adjustment points if kick bands make the
  Underwater inset busier.

**Blockers:** None.

---
*Phase: 83-per-cycle-trace-coloring, Plan: 01*
*Completed: 2026-08-29*
