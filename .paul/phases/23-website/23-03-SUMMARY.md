---
phase: 23-website
plan: 03
subsystem: ui
tags: [nextjs, recharts, supabase, vercel, compare, per-cycle]

requires:
  - phase: 23-website plan 02
    provides: portal data access (supabase.js/api.js), VelocityChart conventions, report card page
provides:
  - /app/compare — two-session overlay + direction-colored metric delta table
  - Simple/Advanced report-card toggle with per-cycle table + trend charts
  - Vercel deploy runbook (web/README.md)
affects: [website deploy, future stroke-analytics phases]

tech-stack:
  added: []
  patterns: ["baseline = older session; delta = % change from baseline (app.py convention)", "per-cycle data read straight from metrics_json.cycles — never recomputed client-side"]

key-files:
  created: [web/app/app/compare/page.js, web/components/portal/CompareChart.js, web/components/portal/MetricDeltaTable.js, web/components/portal/CycleTable.js, web/components/portal/CycleCharts.js]
  modified: [web/app/app/sessions/[id]/page.js, web/app/app/layout.js, web/README.md]

key-decisions:
  - "Delta directions ported from app.py: speed/DPS normal, CV+fatigue inverse, rate/coast neutral"
  - "Kick columns omitted from CycleTable (kick_metrics_reliable always False)"
  - "vercel.json omitted — standard Next.js needs none"

duration: ~45min active (split across session break + classifier outage)
completed: 2026-06-11
---

# Phase 23 Plan 03: Compare + Advanced Analytics + Deploy Prep — Summary

**Streamlit-demo analysis depth landed in the portal: /app/compare (overlaid velocity curves + metric deltas) and a per-cycle Advanced view; site is Vercel-deploy-ready with a written runbook.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Compare mode | Pass | Overlay aligned at t=0, blue/amber, legend, shared tooltip; delta table colored by direction. User-verified at checkpoint. |
| AC-2: Advanced analytics | Pass | Toggle defaults Simple (unchanged); Advanced adds CycleCharts + CycleTable with outlier tinting. User-verified. |
| AC-3: Deploy-ready build | Pass | `npm run build` exit 0 (8 routes incl. /app/compare); README covers env vars, root dir, CORS, DNS swap. |
| checkpoint:human-verify | **Approved** | User verified marketing + portal + compare + advanced end-to-end (2026-06-11). |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/compare/page.js` | Created | Athlete→session pickers ×2, baseline-by-date logic |
| `web/components/portal/CompareChart.js` | Created | Two 100 Hz profiles overlaid at t=0, Brush zoom |
| `web/components/portal/MetricDeltaTable.js` | Created | 8 metrics, % delta from baseline, direction coloring |
| `web/components/portal/CycleTable.js` | Created | Per-cycle rows from metrics_json.cycles; outlier tint (<0.8×median duration) |
| `web/components/portal/CycleCharts.js` | Created | Arm-peak + DPS per cycle w/ session-mean reference lines |
| `web/app/app/sessions/[id]/page.js` | Modified | Simple/Advanced toggle; advanced section after DataQualityCard |
| `web/app/app/layout.js` | Modified | "Compare" nav link |
| `web/README.md` | Replaced | Deploy runbook (Vercel root=web, env vars, DNS, CORS) |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope adjust | 2 | Minor, documented |
| Deferred | 0 | — |

1. **CycleTable outlier median** computed over all displayed cycles; metrics.py uses
   steady-state cycles only. Close approximation, display-only.
2. **vercel.json not created** (plan allowed omission — standard Next.js app).

Per-cycle key confirmed before building (plan instruction): per-cycle DPS key is
**`dist_m`** (set in metrics.py compute_session_metrics, line ~339).

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Permission-classifier outage blocked shell mid-verification | Presented checkpoint with code complete; ran final build + pytest after recovery (both green) |

## Verification Results

- `npm run build` exit 0 — routes: /, /login, /app, /app/athletes, /app/compare, /app/sessions, /app/sessions/[id]
- `pytest tests/` 26 passed (backend untouched this plan)
- Skill audit: no SPECIAL-FLOWS.md — N/A

## Next Phase Readiness

**Ready:** Website feature-complete per phase goal (iOS parity minus recording/devices,
plus Streamlit compare + per-cycle). Deploy is a user action away (runbook written).

**Concerns:** None blocking. Live-data rendering verified by user once; broader
cross-browser/perf checks not done. CORS is wide-open `*` (pre-existing) — tighten
post-deploy.

**Blockers:** None.

---
*Phase: 23-website, Plan: 03 — Completed: 2026-06-11*
