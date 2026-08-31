---
phase: 84-mobile-user-feedback
plan: 03
subsystem: mobile
tags: [react-native, design-tokens, ratings, indicators, accessibility]

requires:
  - phase: 36-metric-ratings
    provides: ratings.py's four pillars, the band vocabulary, and the rating_colors the
      server already ships and three of four surfaces were ignoring
provides:
  - src/lib/indicators.js — the single owner of band -> color/label/shape for the whole app
  - src/components/ui/BandDot.js — the one shared indicator component
  - a server-first color path (rating_colors) with a local fallback, on all four surfaces
affects: [any future surface that renders a pillar band]

tech-stack:
  added: []
  patterns:
    - "Server-first, total resolution: rc[band] || BAND_FALLBACK[band] — never a hardcoded map"
    - "Where a repo has no test runner, guard with a headless node harness over the source"

key-files:
  created:
    - ../swimnetics-mobile/src/lib/indicators.js
    - ../swimnetics-mobile/src/components/ui/BandDot.js
    - scratch/indicator_check.mjs
  modified:
    - ../swimnetics-mobile/src/components/PillarCards.js
    - ../swimnetics-mobile/src/screens/AthleteDetailScreen.js
    - ../swimnetics-mobile/src/screens/AthletesScreen.js
    - ../swimnetics-mobile/src/screens/DashboardScreen.js

key-decisions:
  - "G20: `provisional` is STRUCTURALLY UNREACHABLE — CONTEXT's reported symptom cannot occur.
     The plan handles it correctly by construction and deliberately does NOT decide its fate."
  - "G22: the real, observable defect is FOUR indicator FORMS for one band, not wrong colors"
  - "Athlete-page labels go title case and `—` becomes 'No data' — the one visible copy change"

patterns-established:
  - "AthletesScreen's existing `rc[band] || BAND_FALLBACK[band]` was already correct and became
     the pattern the other three were standardized onto — the fix was to spread what worked"

duration: unrecorded (APPLY ran 02:29-02:35 2026-08-30, straddling a STATE sweep)
started: 2026-08-30
completed: 2026-08-31
---

# Phase 84 Plan 03: Indicator Formalization Summary

**One shared vocabulary replaces four accidental ones.** `src/lib/indicators.js` + `BandDot.js` now
own band → color / label / shape, and all four surfaces read the server's `rating_colors` first with
a local fallback. Verified headlessly at **30/30**; the device trace (AC-7) is owed.

## ⚠ The plan's central premise was demoted during planning

CONTEXT reported that *"a provisional pillar is invisible, trusted, and warned-about depending on the
screen."* **That cannot happen.** `ratings.py:206` computes
`provisional = (thr_table is None) or (thr is None)`, and both halves are dead — `thr_table` falls
back to the breaststroke table (`:251`) and all four pillar primary keys have threshold rows.
`tests/test_ratings.py:142` confirms it from the other side: the test named
`test_provisional_driven_by_missing_threshold` could not construct a provisional pillar and asserts
`is False`.

So `PillarCards`' provisional banner has **never rendered** and the dashboard's provisional exclusion
has **never excluded anything**. The plan proves the handling on synthetic input rather than pretending
a device test exists. The band hexes were also found identical between `ratings.py:33` and
`tokens.js:40-42`, making `AthleteDetailScreen`'s hardcode *latent drift*, not a visible bug.

**What was actually broken (G22/G23):** one band rendered as four different FORMS — a dot, a lowercase
word, a 0–100 number, and a title-case word over a meter — and `unknown`, which IS reachable, got four
different accidental answers.

## Acceptance Criteria Results

| AC | Result | Evidence |
|----|--------|----------|
| AC-1: One module owns the vocabulary | **Pass** | `BAND_COLOR` / `BAND_FALLBACK` / `VERDICT` / `verdictColor` no longer appear anywhere in `src/` outside `indicators.js` |
| AC-2: Color resolution is server-first and total | **Pass** | Every surface resolves `rc[band] || BAND_FALLBACK[band]`; harness asserts totality over all bands |
| AC-3: `unknown` and dormant `provisional` handled once | **Pass** | Proven on synthetic input — no device path can reach `provisional` (see above) |
| AC-4: The athlete page reads the server's colors | **Pass** | `ratingColors` threaded as a navigation param — `AthleteDetailScreen` had no fetch of its own |
| AC-5: Dashboard leads with the band; score secondary | **Pass** | Decision checkpoint answered during APPLY |
| AC-6: The change set is item 5 only | **Pass** | Harness check: `RecordScreen` / `BleContext` / `CycleCharts` untouched by this vocabulary. Mobile diff = exactly 4 modified + 2 new under `src/`; no `.py`, no `web/` |
| AC-7: It reads correctly on a device | **Deferred** | Owed — see below |

**Harness:** `node scratch/indicator_check.mjs` → **30/30, exit 0** (re-run 2026-08-31 at close).

## Deviations

1. **The plan expected two static checks to be red until Task 3.** They were already green when the
   verifying run happened — the APPLY had landed at 02:29–02:35, straddling a STATE sweep that
   recorded the lane as NOT APPLIED. The later `/paul:apply` run therefore **verified rather than
   re-applied**; it wrote no mobile code. STATE's marker was overtaken by events, not wrong when written.
2. **`AthleteDetailScreen` needed navigation-param plumbing, not a lookup swap.** Pillars arrive via
   `route.params.athlete`, not a fetch, so there was no `rating_colors` in scope to read.

## Deferred

**AC-7 — the device trace.** One athlete across roster → detail → dashboard → report card, plus the
judgement on the title-case + "No data" copy change. This lane needs **no EAS build** (Metro is
enough); it was folded into the phase-wide build batch by user decision so the whole phase is judged
in one sitting.

## Next Phase Readiness

No blockers. Zero file overlap with 84-01, 84-02, 84-04 or 84-05. New STATE item 21 asks whether the
dead `provisional` flag should be re-armed, retired, or left dormant — a ratings decision, deliberately
not made here.
