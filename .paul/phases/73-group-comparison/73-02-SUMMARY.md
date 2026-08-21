---
phase: 73-group-comparison
plan: 02
subsystem: ui
tags: [compare, groups, chart, svg, next.js, web]
requires:
  - phase: 73-group-comparison
    provides: 73-01 Groups mode (strip plots) + groupStats + REPORT_METRICS
provides:
  - Mean-profile headline chart (Option C) — per-metric parallel axes, two mean lines + ±1 SD ribbons, "up=better", cue-tinted axis labels
  - Per-metric small-multiple line charts (Option A) as a collapsible drill-down
affects: []
tech-stack:
  added: []
  patterns:
    - "Hand-rolled inline SVG parallel-axis profile; per-axis normalization with direction-aware up=better"
key-files:
  created: []
  modified: [web/components/portal/GroupCompare.js]
key-decisions:
  - "Replaced the 73-01 per-metric strip plots (user: hard to read, scale-less) with a mean±SD profile headline + line-chart drill-down (design chosen from a published artifact of 3 options)"
duration: ~loop
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 73 Plan 02: Mean-profile headline chart Summary

**Swapped the cramped strip plots for a legible line-chart layout: a headline "mean profile" — one vertical axis per metric, two group-mean lines each with a ±1 SD ribbon, oriented so up = better, with axis labels tinted when the groups clearly separate — plus per-metric small-multiple line charts (real Y-axis) as a collapsible drill-down.**

## Why
UAT screenshot of 73-01: the per-metric dot strips were "hard to read and not really helpful" — bare axes, no scale. Presented 3 line-chart options as a published artifact; user chose **C as headline** (+ A drill-down).

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| Headline mean-profile with ±SD ribbons, up=better, cue-tinted axes | **Build-verified / UAT-pending** | `MeanProfile` SVG over `REPORT_METRICS`; ribbon = normalized mean±sd polygon (sd=0 for n<2 pinches to the line); clear-separation axis labels tinted accent. |
| Per-metric line-chart drill-down (labelled Y-axis) | **Build-verified** | `SmallMultiple` + `MetricDetail` behind a "Show per-metric detail" toggle; means/delta/cue kept. |
| No p-values; two-swim mode + assignment UI unchanged | **Pass** | Only the comparison render changed; pickers/assignment/labels intact. |

## Verification
- `npm --prefix web run build` exit 0; `/app/compare` prerenders (headline + drill-down import cleanly).
- `eslint components/portal/GroupCompare.js` → exit 0.
- Shipped `3964139` → Vercel.

## Files
| File | Change |
|------|--------|
| `web/components/portal/GroupCompare.js` | Strip plots → `MeanProfile` headline + `SmallMultiple`/`MetricDetail` drill-down; `normPos` helper, `SHORT_LABEL` map |

## Next Phase Readiness
**Ready:** headline chart shipped. **Human step:** interactive UAT (auth-gated) — athlete with ≥2 same-stroke sessions → assign A/B → confirm the ribbons separate on the differing metrics and the drill-down reads right. **V2s (unchanged):** group-average traces, >2 groups, saved experiments, LLM summary.

---
*Phase: 73-group-comparison, Plan: 02 — chart rework. Shipped `3964139`. Design chosen from artifact (3 options). `.paul` docs local.*
*Completed: 2026-08-19*
