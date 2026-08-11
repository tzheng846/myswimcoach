---
phase: 60-mobile-app-rework
plan: 01
subsystem: ui
tags: [react-native, ios, react-native-svg, sample-rate, per-cycle-charts, data-quality]

requires:
  - phase: 52-sample-rate-contract
    provides: sessions.sample_rate_hz — the authoritative per-session rate this finally reads on mobile
  - phase: 59-segmenter-evaluation
    provides: the per-stroke segmentation that populates metrics_json.cycles, which the charts draw
provides:
  - "Correct time base on the mobile report card (chart axis, cycle overlay, Time-to-Distance, CSV)"
  - "CycleCharts.js — four hand-rolled SVG per-cycle panels"
  - "dropoutWarning.js — pure >5% magnet-dropout predicate, node-verifiable"
  - "cv_isi gate demoted from blackout to banner on both mobile screens"
affects: [60-02, 60-03, 52-02, 53-attention-allocation]

tech-stack:
  added: []
  patterns:
    - "Pure lib module + node verification, because there is no jest in the mobile repo"
    - "Mirror the web's fsHz derivation exactly rather than inventing a second convention"

key-files:
  created: [src/components/CycleCharts.js, src/lib/dropoutWarning.js]
  modified: [src/screens/ReportCardScreen.js, src/screens/RecordScreen.js, CLAUDE.md]
  deleted: [src/components/DataQualityCard.js]

key-decisions:
  - "D1: full web parity on sample rate; NULL -> 100; never backfill"
  - "D2: chart the series, caption with the CV — cv_isi is not a per-cycle quantity"
  - "D8: plot ALL cycles, display-only; metrics.py untouched"
  - "D9: only the magnet-dropout stat survives the Data Quality card"
  - "D10: the cv_isi > 0.80 gate warns above the content instead of replacing it, on both screens"

patterns-established:
  - "Extract a pure predicate and run it in node — the only device-free verification available here"
  - "Mirror 58-05's verified web helper rather than re-deriving a threshold"

started: 2026-08-10
completed: 2026-08-11
---

# 60-01 SUMMARY — Report card correctness + per-cycle analytics

**Phase:** 60 — Mobile App Rework
**Plan:** 60-01 · `execute` · wave 1 · `depends_on []` · `autonomous:false`
**Applied:** 2026-08-10 · **Closed:** 2026-08-11 (checkpoint approved)
**Repo:** `swimnetics-mobile` (separate, user-owned) + one `CLAUDE.md` edit in `myswimcoach`

---

## Result

All 3 auto tasks complete, both checkpoints cleared, **all 5 ACs met**.

| Check | Result |
|---|---|
| Time axis vs `lap_time_s`, live DB, 4 sessions | **−10.0% → +0.0%** |
| NULL-rate sessions render identically | ✓ byte-identical |
| Dropout predicate, node, 10 cases | ✓ boundary-exact at `> 5` |
| `DataQualityCard` references remaining | ✓ **0** |
| `npx expo export --platform ios` | ✓ exit 0, **1091 → 1092 modules** (+1) |
| `pytest tests/` | ✓ **273 passed** (unchanged) |
| Python files changed | ✓ **none** |

---

## ⭐ AC-1 was measured against the live database, not simulated

The headline claim of this plan was that the mobile report card's time axis was ~11% wrong. That was
verified end-to-end by reproducing both the old and new axis against each session's own
`metrics_json.session.lap_time_s`:

```
session       rate      n    lap_s  OLD /100   NEW /fs   old err   new err
69f33669     89.99   2421    26.89     24.20     26.89    -10.0%     +0.0%
c0cdfc25     89.99   2035    22.60     20.34     22.60    -10.0%     +0.0%
e166b8fe     89.99   2283    25.36     22.82     25.36    -10.0%     +0.0%
d25c578f     89.99   1954    21.70     19.53     21.70    -10.0%     +0.0%
e20cd07d      NULL   1309    13.08     13.08     13.08     +0.0%     +0.0%
1ad0020f      NULL    273     3.02      2.72      2.72    -10.0%    -10.0%
ef49cb62      NULL   3510    38.99     35.09     35.09    -10.0%    -10.0%
```

Four for four on recorded-rate sessions: **exact** agreement where there was a −10.0% error.

### ⚠ FINDING THAT OUTLIVES THIS PLAN: most NULL-rate rows are ~90 Hz, not ~100

Two of the three sampled NULL rows are **still −10.0% off after the fix**, and correctly so — their
rate was never recorded, so the `NULL → 100` fallback reproduces their historical rendering exactly,
which is what AC-1 required. Backfilling is forbidden by D1 and by `CLAUDE.md` (writing 100 would
erase the distinction between "genuinely 100" and "unknown").

**This corrects a generalization in the Phase 59 record.** STATE.md notes that the two June NULL
sessions "genuinely ran at ~100 Hz (2033 samples ÷ 20.3 s lap = 100.1)". That check was accurate for
the sessions it examined — `e20cd07d` reproduces it — but it **does not generalize**: most NULL rows
sampled here are ~90 Hz. Phase **52-02** ("measure + backfill existing rows") is therefore worth more
than its backlog position suggests. Not actionable in Phase 60.

---

## What shipped

### Task 1 — real sample rate (D1, D1c)
`ReportCardScreen.js`: `sample_rate_hz` added to the `.select()`; one `fsHz` derived with the web's
exact `> 0` guard (which also rejects a stored 0); three `/100` division sites converted — the
`time` array, the cycle-boundary overlay, and the CSV export column. The three `* 100` percentage
formatters were left alone.

**Time-to-Distance was confirmed transitively fixed by reading, not assumed.** `computeTimeToX`
compares `baselineEndS` (true seconds, from `metrics_json`) against `timeArr`; both operands are now
on the same axis, which also resolves the *second, compounding* error where the baseline index
itself was wrong rather than merely scaled.

`CLAUDE.md`'s "Sample rate" section rewritten. It had scoped the iOS gap to "client-side CSV export",
which made a four-consumer defect look cosmetic; it now names all four and records that `89205ca` is
a `myswimcoach` commit that could never have reached the separately-owned mobile repo.

### Task 2 — per-cycle charts (D2, D8)
New `src/components/CycleCharts.js`: a hand-rolled `react-native-svg` line panel rendered four times
(no chart library exists on mobile). Distance per Stroke, Coast, Cycle Duration, Arm Peak Velocity —
each with a dashed mean reference and a caption carrying the mean or the CV.

The y-range deliberately spans the data **and** the reference line so the mean is never clipped
off-panel, and a flat series widens the range rather than dividing by zero.

**D8 honoured:** all cycles plotted, undifferentiated. The two resulting mismatches (more dots than
`stroke_count`, mean line off the visual average) are documented in the component header as
**expected**, with an explicit instruction not to "fix" them by filtering or renumbering.

### Task 3 — Data Quality retired, gate demoted (D3, D9, D10)
`DataQualityCard.js` deleted. ⚠ It was rendered on **two** screens, not one — a correction found at
plan time and recorded in CONTEXT before apply, so `RecordScreen.js` was in scope for three
decisions rather than the one D10 originally named.

New `src/lib/dropoutWarning.js` — a pure predicate firing only above 5%, mirroring 58-05's verified
web `qualityIssue` helper including its deliberate exclusion of the always-present kick warning.

`efficiencyUnreliable` now renders a banner **above** the content on both screens instead of
replacing it. On the report card the content below is the four charts, which is the point: they show
the very scatter that made `cv_isi` high, and the gate had been suppressing the one view that
explains itself.

---

## Deviations from the plan

1. **Sixth file added: `src/lib/dropoutWarning.js`.** The plan named five. Two screens needed the
   same threshold, and the plan's own `<verify>` required a node-runnable predicate — 58-01's
   `clampAutoStopS` precedent, which the plan cites. Inlining would have duplicated a threshold
   across two files.
2. **Fatigue kept as a scalar tile.** The plan said replace the six Efficiency scalars with charts.
   `fatigue_index_pct` has no per-cycle series — it is a first-quarter-vs-last-quarter comparison
   (`metrics.py:928-932`) — so it cannot be charted. Dropping it would have silently removed a
   metric the user never asked to lose. Kept; the other five became chart captions.
3. **The ROADMAP's 58-01 module baseline was stale.** It records 1075 → 1076; the measured baseline
   is **1091**. The gap is `expo-media-library`, added at 58-01's checkpoint *after* that number was
   written down. Baseline was re-measured by stashing the 60-01 work, exporting, and restoring —
   so the +1 delta is real and not inferred.

---

## ⚠ Verification honesty note

The checkpoint was approved with the message *"approved. also update 58 to say that everything
worked as intended."* That affirmatively answers **item 7** (58-01's auto-stop firing against real
hardware, outstanding since 2026-08-05 — see the Phase 58 close-out).

**Items 1–6 were approved without itemized on-device observations being reported.** The measured
evidence for AC-1, AC-3 and AC-5 is strong and independent of the device (live DB, node, pytest,
export). AC-2 and AC-4 are visual and rest on the approval plus a green export.

This is recorded because it is the same pattern the phase itself documents: 58-01 was
"approved on assumption, not device evidence", and that ambiguity is precisely why 60-01 opened with
a commit checkpoint. Noting it costs nothing and keeps the record honest.

---

## Files changed

| File | Change |
|---|---|
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | fsHz ×3 sites, CycleCharts wired in, DQ card out, dropout strip, banner |
| `swimnetics-mobile/src/screens/RecordScreen.js` | DQ card out, dropout strip, banner |
| `swimnetics-mobile/src/components/CycleCharts.js` | **NEW** |
| `swimnetics-mobile/src/lib/dropoutWarning.js` | **NEW** (deviation 1) |
| `swimnetics-mobile/src/components/DataQualityCard.js` | **DELETED** |
| `CLAUDE.md` | "Sample rate" section corrected (D1c) |

⚠ The mobile changes are **uncommitted** in the user-owned `swimnetics-mobile` repo. HEAD is
`4a03f2c` (Phase 58-01, committed at this plan's opening checkpoint).

---

## Carried forward

- **60-02** — windowed chart primitive + brush bar (D6, D7). Also owns three measured performance
  details: a 2 s window currently keeps only ~17 points, the y-axis would rescale 20×/s, and
  `VelocityChart` has no `useMemo` anywhere.
- **60-03** — video from any session + rolling window (D4, D5, D11). Depends on both prior plans.
- **Phase 52-02** — measure + backfill NULL sample rates. Newly better-motivated (see the finding
  above), still not urgent.
