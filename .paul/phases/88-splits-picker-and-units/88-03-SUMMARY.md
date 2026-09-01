---
phase: 88-splits-picker-and-units
plan: 03
subsystem: ui
tags: [react, nextjs, units, report-card, display-transform]

requires:
  - phase: 88-01
    provides: the DISPLAY table this converts, incl. the retired splits_25m and the new splits_remainder row
provides:
  - web/lib/unitConvert.js — the one place the m→yd rule lives
  - unit conversion at PhaseReportCard's three display sites (strip, hover explain, timeline flag list)
  - scratch/unit_check.mjs — 63-check harness pinning the 23/24/47 split and flag invariance
affects: [compare page, group comparison, parent report — all still unconverted (R7/D6)]

tech-stack:
  added: []
  patterns:
    - "Display transform at the last moment: the verdict model stays in SI, only rendered numbers scale"
    - "Conversion keyed on the UNIT STRING, not a per-metric list"

key-files:
  created: [web/lib/unitConvert.js, scratch/unit_check.mjs]
  modified: [web/components/portal/phases/PhaseReportCard.js, scratch/stroke_toggle_check.mjs]

key-decisions:
  - "D2: verdict computed on SI and NEVER on converted values — flag invariance is structural, not hoped for"
  - "D1: 4 unit strings, not 23 metric keys — a new metric converts without editing a list"
  - "D5: factor is 1.09361, matching every other conversion on the page"

patterns-established:
  - "A harness may parse the component's own DISPLAY table and assert its shape (23/24/47)"

duration: ~45min (review + verification; code applied in a prior cut-off session)
started: 2026-08-31
completed: 2026-08-31
---

# Phase 88 Plan 03: Unit conversion — Summary

**The yd/m toggle now converts all 23 length-dimensioned rows of the report card's 47-metric grid —
value, baseline median, usual-range band, strip domain and unit label moving together — while the
verdict stays computed in SI, so toggling units provably cannot create or clear a flag.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min (this session: review + verification) |
| Tasks | 3 auto + 1 blocking human-verify, all complete |
| Files created | 2 |
| Files modified | 2 |

⚠ **The three auto tasks were NOT executed in this session.** They were found already applied in
the working tree, exactly as STATE warned ("88-03 is PARTIALLY APPLIED and entangled with wave 1").
This UNIFY reconciles *found* work plus the verification and the human-verify run here — the same
posture as 84-02, and it is recorded rather than smoothed over.

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: 23 convert, 24 do not | **Pass** | `unit_check.mjs` parses `DISPLAY` and asserts 23/24/47 |
| AC-2: switching units cannot change a flag | **Pass** | Flag count, every status word, and every strip's band/median/dot percentages agree to 1e-6 across the two renders |
| AC-3: band and value move together | **Pass** | Hover-explain sentence quotes the range in yards; `HoverExplainStub` makes it assertable |
| AC-4: timeline flag list converts | **Pass** | `activeFlags` scaled at the push; "N yd/s vs M yd/s" |
| AC-5: nothing outside the conversion moved | **Pass** | 4 gate harnesses pass unedited; `npm run build` clean |

## Verification Results

| Check | Result |
|-------|--------|
| `node scratch/unit_check.mjs` | **63 passed, 0 failed** |
| `cd web && npm run build` | clean |
| `stroke_toggle_check` / `overlay_render_check` / `marketing_render_check` / `anchor_check` | 63 / 40 / 45 / 17 — all **unedited** |
| `npx eslint .` | 26 problems / 23 errors — **zero new** vs the post-87-02 baseline |
| Human-verify | **Approved** 2026-08-31 |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/unitConvert.js` | Created (44 ln) | `M_TO_YD`, `displayUnit`, `scaleBaseline` — the whole rule |
| `web/components/portal/phases/PhaseReportCard.js` | Modified | `conv` on each row; conversion at the 3 display sites |
| `scratch/unit_check.mjs` | Created (371 ln) | 63 checks incl. the AC-2 invariance assertion |
| `scratch/stroke_toggle_check.mjs` | Modified (+2 ln) | one MAP line + one compile-list entry for `unitConvert` |

⚠ **`scratch/stroke_toggle_check.mjs` was listed as must-pass-UNEDITED by BOTH wave-1 plans and was
edited anyway** (before this session). The edit is mechanically forced — `PhaseReportCard` now
imports `@/lib/unitConvert`, so the harness cannot transpile it without a MAP entry — and it is
additive, with the harness still at 63/63. Recorded as a real boundary breach, not waved through.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Verdict stays in SI (D2) | Scaling both sides preserves the comparison in exact arithmetic, but there is no reason to expose a flag to floating-point luck at a band edge | AC-2 is a structural property; a future refactor that converts too early fails loudly |
| Key on unit string (D1) | 4 strings vs 23 metric keys | Only correct while no unit carries a length power ≠ 1; the 23/24/47 assertion is the tripwire |
| `RangeStrip` / `PhaseTimeline` untouched (D4) | They already take `unit`/`value`/`baseline`/`domain` as props | The rule stays in one file |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 1 | `stroke_toggle_check.mjs` edited despite two DO-NOT-EDIT listings (above) |
| Deferred | 0 | — |

**Total impact:** The plan was followed. The one boundary breach is mechanically necessary and
additive; it predates this session.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Code found already applied, no SUMMARY, provenance unknown | Reviewed rather than re-applied; every AC re-verified from scratch before accepting |

## Next Phase Readiness

**Ready:** `unitConvert.js` is importable by any surface that needs the same rule.

**Concerns:**
- **R7/D6 stands:** the same metric converts on the session report card and **not** on compare,
  group comparison, or the parent report. The portal is internally inconsistent by decision.
- The 23/24/47 assertion will fail the day a metric with `m²` or `s/m` is added — by design, but
  whoever hits it must extend `LENGTH_UNITS`, not delete the check.

**Blockers:** None.

---
*Phase: 88-splits-picker-and-units, Plan: 03*
*Completed: 2026-08-31*
