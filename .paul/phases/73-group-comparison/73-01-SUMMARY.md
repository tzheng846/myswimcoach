---
phase: 73-group-comparison
plan: 01
subsystem: ui
tags: [compare, groups, experiments, stats, next.js, supabase, web]
requires:
  - phase: 61-web-portal-rework
    provides: Compare page (two-swim), REPORT_METRICS catalog, sessionName helpers
provides:
  - "Groups" mode on /app/compare — two labeled groups of one athlete's same-stroke swims, per-metric dots + means + delta + clear/overlapping cue
  - web/lib/groupStats.js — pure group stats (mean/sd/delta/betterSide/band-overlap separation), no p-values
affects: []
tech-stack:
  added: []
  patterns:
    - "Pure stats module (no React) so the math is node-verifiable without a JS test runner"
    - "Honest tiny-n comparison: distribution + ±SD band-overlap cue, never a significance test"
key-files:
  created: [web/lib/groupStats.js, web/components/portal/GroupCompare.js]
  modified: [web/app/app/compare/page.js]
key-decisions:
  - "Metrics only, no traces (D2/D9); one athlete, same stroke (D5/D6); 2 groups, array-ready for ≤5 (D7); ephemeral + labeled (D8)"
  - "No p-values (D4) — n=3 makes them fragile; separation = ±SD bands overlap, suppressed for n<2"
  - "Single assignment map {sessionId: A|B} makes dual-group membership structurally impossible"
duration: ~loop
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 73 Plan 01: Group Comparison (A/B experiments) Summary

**A "Groups" mode on Compare pits two labeled groups of one athlete's same-stroke swims against each other per metric — each swim a dot, group means, the delta, and an honest clear/overlapping cue (no p-values) — turning Compare into a "does breathing matter?" experiment tool.**

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: two labeled same-stroke groups, no dual membership | **Build-verified / UAT-pending** | Athlete+stroke selects; single `assignment` map ⇒ a swim is in at most one group by construction. Interactive assign needs a login + sessions. |
| AC-2: per-metric dots + delta + honest cue, no p-value | **Pass (logic + build)** | `groupStats` node-checked **17/17**; rows render mean/dots/delta/cue over `REPORT_METRICS`; grep confirms no significance test (only comments explaining their absence). |
| AC-3: tiny-n honesty + two-swim mode intact | **Pass** | Cue = "insufficient" (suppressed) for n<2; two-swim mode wrapped `mode==='swims'`, behavior unchanged; build green. |

## Verification
- **`node` sanity check of `groupStats.js`: 17/17** (mean, SD, delta, betterSide by direction, band-overlap separation, null handling).
- `npm --prefix web run build` → exit 0, `/app/compare` prerendered (both modes' modules import cleanly).
- `eslint` on the two new files → clean (exit 0). (Pre-existing `page.js:141` set-state-in-effect error is not mine.)
- Shipped `d66734a` → Vercel.

## Files
| File | Change | Purpose |
|------|--------|---------|
| `web/lib/groupStats.js` | Created | Pure group stats: `groupStats`, `bandsOverlap`, `metricComparison` |
| `web/components/portal/GroupCompare.js` | Created | Athlete+stroke pickers, A/B assignment, per-metric rows with SVG strip plots + cue |
| `web/app/app/compare/page.js` | Modified | "Two swims" / "Groups" mode toggle; two-swim UI unchanged |

## Decisions
| Decision | Rationale | Impact |
|----------|-----------|--------|
| No p-values, ±SD band-overlap cue | n=3 makes significance tests fragile/false | Honest read; separation suppressed for n<2 |
| Single assignment map | Prevents a swim in both groups | Simpler than two lists |
| Pure stats module | node-verifiable without adding a JS test runner | Real verification of the core math |

## Deviations
None — plan executed as written. Refactored the athlete-change reset out of the effect into the handler (lint `set-state-in-effect`).

## Next Phase Readiness
**Ready:** Phase 73 committed scope complete.
**Concerns / human steps:** interactive UAT owed (auth-gated) — pick an athlete with ≥2 same-stroke sessions, assign to A/B, confirm dots/means/delta/cue read correctly; group-average traces, >2 groups, saved experiments, and an LLM summary are the noted V2s.
**Blockers:** None.

---
*Phase: 73-group-comparison, Plan: 01 — only planned plan; phase complete. Shipped `d66734a`. `.paul` docs local; ROADMAP table untouched.*
*Completed: 2026-08-19*
