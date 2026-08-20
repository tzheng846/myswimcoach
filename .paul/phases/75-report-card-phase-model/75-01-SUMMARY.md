---
phase: 75-report-card-phase-model
plan: 01
subsystem: api
tags: [fastapi, jsonb, metrics-registry, backfill, phase-metrics]

requires:
  - phase: 64-video-velocity-overlay
    provides: sessions.acceleration_profile (PhaseContext.accel reads it; degrades to empty array on pre-64 sessions)

provides:
  - phase_metrics.py — MetricSpec registry (37 metrics, full taxonomy) + PhaseContext + compute_phases() engine
  - additive `phases` object in /process response + stored metrics_json
  - POST /sessions/{id}/recompute — backfill seam, rebuilds phases from stored profiles only

affects: [75-02-metric-implementation, 75-03-report-card-ui]

tech-stack:
  added: []
  patterns:
    - "MetricSpec registry with a reserved compute-fn slot (status: planned|implemented) — a metric is declared once with key/phase/unit/tier, then later 'turned on' by attaching a compute fn, no reshaping of callers"
    - "recompute-from-stored-profiles backfill endpoint (2nd instance of this pattern, after PUT /annotations' recompute block) — re-derive from velocity/distance/accel arrays already in Postgres, never re-touch the raw CSV"

key-files:
  created: [phase_metrics.py, tests/test_phase_metrics.py, tests/test_recompute.py]
  modified: [api.py, tests/test_api.py]

key-decisions:
  - "GO-signal reserved at metrics_json.phases.go_signal_s, not a new sessions column — the migration-free reading of D15"
  - "Tier (low/medium/high) assigned per-metric from CONTEXT's ✅/🟡/🔶 tags; re-rankable in Step 2 since nothing is implemented yet"
  - "One commit for the whole plan (not per-task), matching this repo's established per-plan commit convention (Phase 73's 4 plans each shipped as one commit)"

patterns-established:
  - "phase_metrics.REGISTRY is the single declarative source of truth for race-phase metrics — Step 2 flips one spec's status/compute per approved increment, never a batch edit"

duration: not instrumented (single continuous PLAN→APPLY→UNIFY session)
started: 2026-08-19
completed: 2026-08-19
---

# Phase 75 Plan 01: Report Card Phase Model — Skeleton/Integration Summary

**Built the metric registry + additive `phases` scaffold + a stored-profile recompute/backfill endpoint for the race-phase report-card revamp — zero metrics implemented, by design (CONTEXT D12).**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 of 3 completed |
| Files modified | 2 (`api.py`, `tests/test_api.py`) |
| Files created | 3 (`phase_metrics.py`, `tests/test_phase_metrics.py`, `tests/test_recompute.py`) |
| New tests | 29 (17 + 8 + 4) |
| Full suite | 317 passed, 0 failed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Registry is the single declarative source of truth, fully populated as planned | Pass | 37 `MetricSpec` entries across start(11)/underwater(13)/swim(9)/whole(4); all `status="planned"`, `compute=None`; `reaction_time` present under `start`; enforced by `test_all_specs_planned_with_no_compute_fn` |
| AC-2: `/process` writes an additive `phases` scaffold; existing metrics byte-identical | Pass | `phases` added to both stored `metrics_json` and response; `session`/`cycles`/`initial_phase`/`data_quality` untouched — proven by all pre-existing `test_api.py` assertions still passing plus a dedicated additive-only test |
| AC-3: `POST /sessions/{id}/recompute` re-derives phases from STORED profiles, auth-gated & idempotent | Pass | 401/403/404 covered; rebuilds from `velocity_profile`/`distance_profile`/`acceleration_profile` at the session's own rate, no raw-CSV read; two consecutive calls return identical `phases`; a row with `acceleration_profile=None` still succeeds; mismatched/empty profiles → 422 |

Skill audit: N/A — no `.paul/SPECIAL-FLOWS.md` configured for this project.

## Accomplishments

- A registry that gives every metric in the Phase-75 taxonomy (all 37, across all four
  race phases) a declared home — key, phase, label, unit, effort tier, and a reserved
  compute-fn slot — so Step 2 can implement metrics one at a time without ever touching
  the shape of the registry or its callers.
- Two API integration points wired without disturbing anything already shipping:
  `/process` gains the scaffold on every new session, and the new `/recompute` endpoint
  can backfill it onto every *existing* session later, from data already in Postgres.
- The GO-button reaction-time metric (CONTEXT D13) has a reserved slot
  (`start.reaction_time`) and a reserved input (`PhaseContext.go_signal_s`) without
  requiring any mobile or clock-sync work yet.

## Task Commits

Single commit for the plan (matches this repo's established one-commit-per-plan
convention, e.g. Phase 73's four plans):

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Tasks 1–3 (registry, /process wiring, /recompute) | `1ba589a` | feat | phase-metric registry + recompute skeleton |

Pushed: `2f17a1a..1ba589a` → `origin/main` (Railway auto-deploys `main`).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `phase_metrics.py` | Created | `MetricSpec`/`PhaseContext`/`REGISTRY`/`compute_phases()` — pure, no I/O |
| `api.py` | Modified | `import phase_metrics as pm`; additive `phases` in `/process`; new `POST /sessions/{id}/recompute` |
| `tests/test_phase_metrics.py` | Created | 17 tests — registry invariants + engine seam |
| `tests/test_recompute.py` | Created | 8 tests — endpoint auth/round-trip/idempotency |
| `tests/test_api.py` | Modified | `phases` added to `RESPONSE_TOP_KEYS`; new `TestPhaseMetricsScaffold` (4 tests) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| GO-signal lives at `metrics_json.phases.go_signal_s`, not a new column | D15 says "no migration"; a new `sessions` column would be one | Step 3's GO-button work writes into existing jsonb, no patch needed unless a future session wants it SQL-queryable |
| Effort tiers assigned per-metric from the CONTEXT's ✅/🟡/🔶 feasibility tags | Plan explicitly allows this to be approximate — "re-rankable in Step 2" | Zero cost today since nothing is implemented; Step 2 re-checks tier when it picks the first metric |
| One commit for the whole plan, not per-task | Matches the repo's observed convention (Phase 73's 4 plans, each one commit) rather than the PLAN.md template's generic per-task-commit suggestion | Keeps history consistent with how this project already ships PAUL plans |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** None — executed exactly as planned, all 3 tasks, no retries, no checkpoints.

### Deferred Items

None — the plan's own boundaries already deferred metric implementation and UI work to
future plans (75-02, 75-03); that is the plan working as designed, not something
discovered mid-execution.

## Issues Encountered

None.

## Phase Completion Check

**Phase 75 is NOT complete.** A mechanical PLAN-count-vs-SUMMARY-count check in this
directory would currently read 1-vs-1 and look like "last plan in phase," but that
would be wrong: `CONTEXT.md`'s "Build workflow" section explicitly resequenced this
phase into **3 ordered steps** (skeleton → metrics one-by-one → UI), of which this plan
was Step 1 only. Steps 2 (metric implementation, one at a time, gated on explicit user
approval per D12) and 3 (the phase-organized report-card UI) have no PLAN.md yet because
they have not been scoped — not because they don't exist. Per CONTEXT.md D14, this
sequencing is meant to survive exactly this kind of session boundary. **No phase
transition, ROADMAP "complete" marking, or PROJECT.md "shipped" language is triggered
by this SUMMARY.**

## Next Phase Readiness

**Ready:**
- The registry has a slot for every taxonomy metric — 75-02 just needs to pick one
  (candidates from the SUMMARY's "cheap, ship first" list: `uw_duration`, `uw_distance`,
  `uw_avg_speed`, `uw_surface_ratio`, `ivv`, `breakout_vel`, `phase_time_budget`,
  `phase_dist_budget`, `splits`, `pulldown_peak_vel`/`pulldown_duration`), implement its
  `compute` fn, and flip its `status` to `"implemented"`.
- `POST /sessions/{id}/recompute` already exists, so the moment 75-02 ships a metric,
  every existing session can be backfilled without touching raw CSVs.

**Concerns:**
- None specific to this plan. The general project-level caveats already tracked
  elsewhere (segmentation reliability, breaststroke-only validated thresholds, n=0 on
  backstroke underwater data) apply to whatever metric 75-02 picks, same as always.

**Blockers:**
- None. `/paul:plan 75` can run again once the user picks the first metric (D12 —
  requires their explicit approval before implementation, not a Claude judgment call).

---
*Phase: 75-report-card-phase-model, Plan: 01*
*Completed: 2026-08-19*
