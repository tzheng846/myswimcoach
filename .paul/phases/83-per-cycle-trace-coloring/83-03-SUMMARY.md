---
phase: 83-per-cycle-trace-coloring
plan: 03
subsystem: ui
tags: [react, svg, tailwind, anomaly-detection, mad, annotations]

requires:
  - phase: 83-01
    provides: buildBands + PhaseVelocity band rendering + the @theme static token lesson
  - phase: 83-02
    provides: phases.kick_bands, the Underwater inset's band consumer
provides:
  - Breakout band (synthetic n:0) gilded gold on annotated Swimming insets
  - Measured verdict that per-lap shape-anomaly detection is not viable
  - web/lib/cycleShape.js, parked and unwired, carrying its own falsifying numbers
affects: [83-04, 81-02, cross-session-shape-baseline]

tech-stack:
  added: []
  patterns:
    - "Measure a gate's fire rate against the stored library BEFORE shipping the threshold"
    - "Synthetic bands may carry n:0 — outside the CycleCharts cross-highlight keyspace"

key-files:
  created:
    - web/lib/cycleShape.js
    - scratch/shape_checks.mjs
    - scratch/shape_viability_probe.py
    - scratch/shape_sweep_probe.py
  modified:
    - web/lib/cycleBands.js
    - web/components/portal/phases/PhaseVelocity.js
    - web/components/portal/phases/PhaseReportCard.js
    - web/app/globals.css

key-decisions:
  - "D1: CUT the shape-anomaly flag on measured evidence, do not tune k"
  - "D2: Breakout = its own synthetic band, streamline break -> first stroke mark (ONE stroke)"
  - "D3: Gold gated on segmentationReliable — auto cycle 1 is not the breakout"
  - "D4: Park cycleShape.js unwired rather than delete it"

patterns-established:
  - "A threshold is not shippable until its fire rate is measured on real data"
  - "No gap means no breakout band — never invent a zero-width segment"

duration: ~3h (incl. one retracted verify + a full re-cut)
started: 2026-08-29
completed: 2026-08-29
---

# Phase 83 Plan 03: Breakout band + shape-anomaly investigation

**The plan's headline feature was measured, falsified, and cut; what shipped is a gold breakout band
resting on the coach's own annotation convention — plus a recorded finding that per-lap shape-anomaly
detection cannot work at seven cycles a lap.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~3h across one APPLY + one retracted verify + one re-cut |
| Tasks | 4 auto + 1 blocking checkpoint (failed once, re-run) |
| Files | 4 modified, 4 created |
| Python touched | **none** — suite untouched at 497 |

## Acceptance Criteria Results

⚠ **The PLAN's ACs were written for a feature that no longer exists.** Reconciled honestly rather
than ticked off.

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Shape distance duration-invariant, amplitude-sensitive | **Pass (now moot)** | Proven in `shape_checks.mjs`: equal to 1e-9 across durations, weak-pull scores further. The lib is correct — it is simply unwired. |
| AC-2: Flag gated and can be absent | **FAILED ON REAL DATA** | Passed on synthetic fixtures, then fired on **75% of sessions** live at k=3.0. This is the finding, not a bug. |
| AC-3: Breakout gold, Swimming only | **Pass, redefined** | Gold ships as a synthetic `n:0` band covering the breakout PULL, not cycle 1 — and only on annotated sessions. |
| AC-4: Anomalous band red, precedence explicit | **CUT** | No red anywhere. `--color-cycle-anomaly` removed. |
| AC-5: Hover explains which flag fired | **CUT** | `flagClause` deleted. Breakout hover names what it spans instead. |
| AC-6: Kicks flagged by the same rule | **CUT** | Underwater keeps 83-02 behaviour exactly. |
| AC-7: Nothing else regresses | **Pass** | No Python; suite 497; build clean 19 pages; CycleCharts / hero / Start / Whole untouched. |
| AC-8: Visual approval | **Pass on the second attempt** | First verify **retracted** by the user; re-verified after the re-cut ("gold is one stroke now"). |

## Verification Results

| Check | Result |
|---|---|
| `node scratch/shape_checks.mjs` | **15/15** |
| `cd web && npx next build` | clean, **19 pages** |
| `npx eslint` on the 4 touched files | clean except the pre-existing `react-hooks/set-state-in-effect` |
| `python -m pytest tests/ -q` | **497 passed** (untouched) |
| Production CSS grep | `--color-cycle-breakout` present, `--color-cycle-anomaly` absent |
| No Python edited | `find -newermt` returned nothing |

## The measurement that changed the plan

Read-only probes over the stored library — **90 usable sessions, 618 cycles**.

**Cycle counts and the breakout gap:**

| | Annotated (43) | Auto (47) |
|---|---|---|
| Cycles/session | median **7** (1–11) | median 7 (1–17) |
| `stroke_start_s` → cycle 1 | median **+1.04 s**, 0.08–1.63, **negative 0/43** | median **−1.00 s**, **negative 28/47**, worst **−12.9 s** |

**Gate fire rate — the falsification:**

| k | sessions with ≥1 flag | bands flagged |
|---|---|---|
| 3.0 (shipped) | **75%** | 15.5% |
| 4.0 | 67% | 12.8% |
| 5.0 | 57% | 10.7% |
| 6.0 | 50% | 9.1% |
| 8.0 | **39%** | 6.6% |

Excluding cycle 1 helps marginally (67% → 55% at k=4.0) and costs 10 sessions their eligibility.
**No k separates clean from ragged.** Both halves of the test — the median profile and the spread of
distances — are estimated from ~7 samples, and the spread is the divisor, so the threshold moves with
sampling luck rather than with the swimming. `k = 3.0` had been justified in the PLAN by Gaussian
reasoning (MAD·1.4826 ≈ σ, "≈ 1-in-20") that needs dozens of samples; **the cycle count was never
checked before the gate was written.** That is the process failure worth carrying forward.

## Decisions Made

| Decision | Rationale | Impact |
|---|---|---|
| **D1: Cut the flag, don't tune k** | No threshold works; the failure is the reference population, not the constant | The plan's primary deliverable does not ship; owed item 17 opened |
| **D2: Breakout is its own synthetic band** | Coach's convention: `stroke_start_s` = streamline break, `stroke_marks_s[0]` = first hand overhead, so the pull between them is ONE stroke. An intermediate re-cut merged it into cycle 1 and the user correctly called it "two strokes" | `buildBands` inserts `n: 0`; cycle 1 keeps its own alternation colour |
| **D3: Gold only when `segmentationReliable`** | On auto sessions 28/47 have cycle 1 starting before the breakout (worst −12.9 s) | Auto sessions keep the grey lead-in; gives annotating a visible payoff (item 9) |
| **D4: Park `cycleShape.js`, don't delete** | Correct and covered; only its reference population was wrong, and the follow-up is a concrete owed item | Unwired code in the tree, deliberately, with the numbers in its header |
| **D5: No gap ⇒ no breakout band** | A zero-width gold band would invent a stroke that is not there | Sessions whose marks start at the breakout show no gold |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Feature cut on evidence | 1 | **Major** — AC-2/4/5/6 void |
| Scope additions | 2 | Two read-only probes; the annotation convention recorded to memory |
| Re-cuts after failed verify | 2 | Gold redefined twice (cycle 1 → pull + cycle 1 → pull only) |

**Auto-fixed:**

1. **`cycleBands.js:9` false comment** (owed from 83-02) — claimed 83-02 passes `metrics_json.kicks`;
   it passes `phases.kick_bands`. Fixed here as the plan required.
2. **Badge over-count** — the synthetic breakout band would have turned "5 cycles" into "6"; the
   badge now counts non-breakout bands only.

**Deferred:** owed **item 17** — cross-session shape baseline (needs prior sessions' velocity arrays
reachable in the browser; a backend/data question, not a frontend one).

## Issues Encountered

| Issue | Resolution |
|---|---|
| First human-verify **retracted** — grey lead-in unexplained, halo read pink, hover conflated shape and duration | Traced the grey to its source; the pink and the copy were **dissolved** by cutting the flag rather than fixed |
| `annotations.py:25` claims "THE FIRST STROKE CYCLE CONTAINS THE BREAKOUT" | **Contradicted** by the coach's actual marking convention — the pull sits ahead of cycle 1. Docstring left alone (Python boundary); flagged for a future pass |
| Two harness fixtures were degenerate (zero MAD; test cycles sitting *on* the median, scoring 0.0) | Rewritten to sit off-median with varied durations — not loosened |
| Bands were briefly modelled with `flag` + `isBreakout` only | AC-4 needed a both-flags band to draw gold line + red halo, so a third field was added — then made moot when the flag was cut |

## Next Phase Readiness

**Ready:** The breakout band is measured and correct. `buildBands` now models a band with no stored
row, which 83-04 can reuse. Both probes are re-runnable against the live library.

**Concerns:**

- `web/lib/cycleShape.js` is unwired code in the tree. Intentional, but it must not rot silently.
- `83-03-PLAN.md` now misdescribes the tree; anyone reading it cold will be misled.
- `annotations.py`'s breakout docstring disagrees with the coach's real convention.

**Blockers:** None. **Phase 83 stays 🚧 — 83-04 (inset window framing) has no PLAN yet, so the
plan-count heuristic must NOT be trusted here.**

---
*Phase: 83-per-cycle-trace-coloring, Plan: 03*
*Completed: 2026-08-29*
