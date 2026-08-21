---
phase: 73-group-comparison
plan: 04
subsystem: ui
tags: [compare, groups, scope, metrics-window, next.js, web]
requires:
  - phase: 73-group-comparison
    provides: Groups mode + DiffBars headline + metricComparison
provides:
  - Scope selector (Full / Stroking / Underwater / Distance range) that recomputes the 6 REPORT_METRICS over the chosen window, client-side
  - web/lib/windowMetrics.js — pure window→metrics recompute (node-verified)
affects: []
tech-stack:
  added: []
  patterns:
    - "Client-side metric recompute from stored velocity_profile/distance_profile/cycles over a chosen index window; 'full' uses stored scalars verbatim"
key-files:
  created: [web/lib/windowMetrics.js]
  modified: [web/components/portal/GroupCompare.js]
key-decisions:
  - "Fixes the whole-swim-vs-stroking inconsistency: coach can scope every metric (incl. speed) to a phase or distance window"
  - "'Full swim' (default) uses STORED session scalars — never recomputed, so the default view can't drift from the unstored swim_end boundary"
  - "Distance/Stroking stroke metrics use WHOLE cycles only (no mid-stroke split); Underwater → stroke metrics blank (no strokes there)"
duration: ~loop
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 73 Plan 04: Phase + distance-range metric scoping Summary

**A "Scope" selector on the Groups view — Full swim / Stroking / Underwater / a distance range — recomputes the 6 metrics over that window entirely client-side from the stored velocity/distance profiles + per-cycle data, so an A/B comparison can exclude the (identical, diluting) dive. Default "Full swim" is byte-identical to before.**

## Why
The metric-window audit: `mean_vel_ms`/`max_vel_ms` are over the whole swim (dive included; top speed is usually the dive) while stroke metrics are over the stroking cycles only. For a breathing A/B the dive dilutes the speed contrast. Scoping lets the coach compare like-for-like.

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Full (default) unchanged | **Pass** | `scopedMetrics({mode:"full"})` returns stored `metrics_json.session` scalars verbatim (node-checked). |
| AC-2: Phase recompute (Stroking / Underwater) | **Pass (logic) / UAT-pending** | Windows from cycles+baseline_end; underwater → stroke metrics null (no cycles). node-checked. |
| AC-3: Distance range | **Pass (logic) / UAT-pending** | `[from,to] m` from push-off via distance_profile; whole-cycle selection for stroke metrics; empty→null (dropped, not zero). |
| AC-4: no backend/schema; rest untouched | **Pass** | Only the per-session values feeding `metricComparison` change; DiffBars/drill-down/pickers/two-swim mode unchanged; no api/schema/mobile. |

## Verification
- **`node` check of `windowMetrics.js`: 17/17** (full=stored; stroking mean-vel + 60/mean(dur) + cv; underwater null stroke metrics; distance window null stroke metrics + real mean speed).
- `npm --prefix web run build` exit 0; `/app/compare` prerenders; eslint clean on both files.
- Shipped `2f17a1a` → Vercel.

## Files
| File | Change |
|------|--------|
| `web/lib/windowMetrics.js` | Created — `phaseBounds` / `windowFor` / `scopedMetrics` (pure) |
| `web/components/portal/GroupCompare.js` | Scope selector + distance inputs; query now selects velocity/distance profile + cycles + sample_rate; `rows` recompute via `scopedMetrics` keyed on `scope` |

## Next Phase Readiness
**Ready:** scoping shipped. **Human step:** interactive UAT (auth-gated) — athlete with ≥2 same-stroke sessions → toggle Full/Stroking/Underwater/Distance → confirm the bars/deltas change and Full matches the pre-scope numbers. **Caveats surfaced in-UI:** whole-cycle selection for Distance/Stroking; Underwater shows blank stroke metrics. **V2s (unchanged):** group-average traces, >2 groups, saved experiments, LLM summary.

---
*Phase: 73-group-comparison, Plan: 04 — window scoping. Shipped `2f17a1a`. `.paul` docs local.*
*Completed: 2026-08-19*
