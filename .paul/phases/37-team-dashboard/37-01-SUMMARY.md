---
phase: 37-team-dashboard
plan: 01
subsystem: backend
tags: [dashboard, ratings, api, team, pure-aggregation]
requires: []
provides:
  - ratings.summarize_team (pure band-distribution + needs-attention rollup)
  - GET /team/overview endpoint (auth, coach-scoped) + locked payload contract
affects:
  - 37-02 (web dashboard UI consumes /team/overview)
  - future iOS team-dashboard phase (mirrors the same payload)
tech-stack:
  added: []
  patterns: ["team rollup reuses rate_session/select_baseline — zero duplicated band logic", "pure helper takes `today` as a param (clock-free, testable)"]
key-files:
  created: []
  modified: [ratings.py, api.py, tests/test_ratings.py, tests/test_api.py]
key-decisions:
  - "summarize_team lives in ratings.py (rating-domain) and consumes band strings, never re-derives them"
  - "recent[] carries no per-session verdict — keeps the endpoint O(athletes), not O(sessions)"
  - "STALE_DAYS=14, recent cap=10 fixed (not coach-configurable yet)"
duration: ~40m
completed: 2026-06-18
---

# Phase 37 Plan 01: Team Dashboard Backend Summary

**Shipped the backend that powers the team coach dashboard: one pure rollup helper and one
authenticated, coach-scoped endpoint that turns the whole roster's latest sessions into a
team-health payload — all by reusing the Phase-36 rating logic, no new metric code, no new dep.**

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| AC-1 distribution + counts | ✅ PASS | `summarize_team` counts bands per pillar (PILLARS order), ignores athletes with no sessions. `test_distribution_counts_only_athletes_with_pillars` |
| AC-2 needs_attention reasons | ✅ PASS | needs_work/declined only from non-provisional pillars; stale via injected `today`; never_tested for empty pillars; clean athletes omitted; sorted reason-count desc/name. 5 unit tests |
| AC-3 endpoint shape + auth + scope | ✅ PASS | 401 no-token, 403 no-coach, 200 full shape; foreign athlete/session dropped from `athletes[]` + `recent[]`. `test_shape_scope_and_rollup` |
| AC-4 no-session + DB-failure | ✅ PASS | no-session athlete → `pillars:[]`, `last_tested:null`; sessions-query failure → 5xx (`test_backend_failure_surfaces_5xx`) |

## Accomplishments
- **ratings.summarize_team(athletes, today, stale_days=14)** — pure team rollup → `{pillars:[band
  distribution], needs_attention:[...]}`. Clock-free (caller passes `today`). Added `STALE_DAYS`
  constant + `_days_since` helper. Consumes pillar band/trend strings; never re-derives a band.
- **GET /team/overview** — auth + coach lookup identical to `/sessions/{id}/ratings`; one athletes
  query + one sessions query (coach-scoped, newest-first); rates each athlete's latest session via
  the SAME path (stroke fallback → flatten session+data_quality → prior same-stroke →
  `select_baseline("previous")` → `rate_session`), projected to compact pillars. Builds `recent[]`
  (cap 10, no verdict), `tested_this_week` (within 7d), `rating_colors` from source. Defense-in-depth
  drop of any session whose athlete_id isn't in the roster.
- **Tests:** test_ratings +6 (TestSummarizeTeam), test_api +4 (TestTeamOverview). Full suite **103
  passed** (was 93). Renamed the new fake to `_team_overview_admin` to avoid colliding with the
  existing chat-team `_team_admin`.

## Verification
- `pytest tests/ -q` → 103 passed.
- `git status` → only api.py, ratings.py, tests/test_api.py, tests/test_ratings.py modified. No
  `web/**` diff, no `requirements.txt` change.

## Deviations from Plan
None material. The endpoint reads `today` from the real clock (`datetime.date.today()`) — correct
for production; stale/never-tested logic is exercised deterministically in the pure
`summarize_team` unit tests where `today` is injected, so endpoint tests assert structure/scope
rather than date-dependent values.

## Locked payload contract
Documented in 37-01-PLAN DESIGN SPEC and proven by the tests. 37-02 (web) + the future iOS phase
build against it. Shape: `{athlete_count, tested_this_week, pillars[], athletes[], recent[],
needs_attention[], rating_colors}`.

## Next Phase Readiness
37-02 (web): rebuild [web/app/app/page.js](web/app/app/page.js) into the four sections (team
pulse strip, needs-attention list, recent-activity feed, color-banded roster grid) consuming
`GET /team/overview`. The endpoint must be deployed to Railway (push to main) before the web
verifies against prod — or verify against a local uvicorn first, the Phase-36 pattern.

---
*Phase: 37-team-dashboard, Plan: 01*
*Completed: 2026-06-18*
