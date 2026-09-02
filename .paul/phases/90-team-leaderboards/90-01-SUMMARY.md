---
phase: 90-team-leaderboards
plan: 01
subsystem: ui
tags: [leaderboard, ranking, metrics, pure-module, node-harness, postgrest]

# Dependency graph
requires:
  - phase: 88-splits-picker-and-units
    provides: the `direction` vocabulary + the SI-ranking / display-conversion split (88-03 D2), and `dive_start_s` as the hoisted start anchor (88-02)
  - phase: 75-race-phase-report-card
    provides: the `metrics_json.phases` payload the eight metrics are read out of
provides:
  - LEADERBOARD_METRICS — the 8-metric, cycle-independent catalog with labels + direction
  - SESSION_SELECT — the deep-scalar PostgREST select string, pinned to the catalog by test
  - isEligible / metricValue / lastNMean / rankBoard — the whole ranking core, pure
  - scratch/leaderboard_check.mjs — 63 checks, no auth, no network, no dev server
affects: [90-02, 90-03, 89-account-model-rework]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct-import node harness: a pure ESM lib with no JSX and no @/ aliases needs no typescript staging"
    - "Source-text assertions as a design lock: the harness greps the module it imports"

key-files:
  created: [web/lib/leaderboard.js, scratch/leaderboard_check.mjs]
  modified: []

key-decisions:
  - "Lap time is DERIVED from finish_s − dive_start_s; the stored scalar is unreachable from this module and absent from SESSION_SELECT"
  - "Reworded the module header so the harness's source-text bans can stay strict rather than be weakened"
  - "Added metricByKey so rankBoard accepts a key string as well as a catalog entry (matches reportMetrics.js)"

patterns-established:
  - "A metric with no sort order is not in the catalog — there is no `neutral` direction here by construction"
  - "Ranking runs on SI only; unitConvert.js is deliberately not imported, so a unit toggle structurally cannot reorder a board"
  - "Missing is null, never 0 and never NaN — lastNMean and rankBoard both key off null"

# Metrics
duration: ~15min
started: 2026-09-02T00:00:00Z
completed: 2026-09-02T00:16:00Z
---

# Phase 90 Plan 01: Leaderboard Ranking Core — Summary

**The whole leaderboard arithmetic as one pure, node-verifiable module — 8 cycle-independent
metrics, a 15 m eligibility guard, a last-5 mean, and a direction-aware stable ranking — with lap
time derived from boundaries because the stored `lap_time_s` is the recording duration, not a swim.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min |
| Started | 2026-09-02T00:00:00Z |
| Completed | 2026-09-02T00:16:00Z |
| Tasks | 2 of 2 completed |
| Files created | 2 (476 lines) |
| Files modified | 0 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Lap time is derived, never read | **Pass** | `metricValue({dive_start_s:4.0, finish_s:19.1, lap_time_s:39.0}, "elapsed_s")` → 15.1. Null on missing dive, missing finish, `finish <= dive`, and non-finite. Source-text check: the module contains neither `lap_time_s` nor `t[-1]`. |
| AC-2: Eligibility guard is a stated constant, one function | **Pass** | `MIN_DIST_M === 15`. 0 / 14.31 / 15.0 / 21.5 → false / false / true / true. null, undefined, missing, a null row and the string `"20"` are all ineligible — no `?? 0` coercion. |
| AC-3: Row value = mean of the last N, newest first | **Pass** | `[2,4,6,8,10,12]` at n=5 → **6**, not 7. `[2,null,4,null,6,8,10,12]` at n=5 → **6**, proving nulls drop before the slice. Empty / all-null / undefined → null. |
| AC-4: Ranking is direction-aware, stable, refuses to rank a missing value | **Pass** | 1.9 / 1.4 / 1.4 / null → Ana, Bo, Cy, Dane with ranks `[1,2,2,null]`; a fourth value gives `[1,2,2,4]`. Reversing the input is byte-identical. `elapsed_s` (lower) inverts and nothing else changes. `rows` is never mutated. |
| AC-5: The catalog carries exactly 8 metrics + the query that feeds them | **Pass** | 8 entries, exact key order, every entry `{key,label,unit,direction}`, every direction in {higher, lower}, `elapsed_s` the only `lower`. `SESSION_SELECT` names all 7 stored keys plus `dive_start_s`/`finish_s`/`total_dist_m`/`id`/`athlete_id`/`stroke_type`/`recorded_at`, does **not** name the stored lap-time scalar, and selects deep scalars (`->value`) rather than whole objects. |
| AC-6: The harness is green with no auth and no network | **Pass** | `node scratch/leaderboard_check.mjs` → **63 passed, 0 failed**, exit 0, in a bare checkout. No `typescript` staging, no `react-dom/server`, no `node_modules` write, no cleanup. |

## Verification Results

| Check | Result |
|-------|--------|
| `node scratch/leaderboard_check.mjs` | **63 passed, 0 failed** — exit 0 |
| `grep -n "lap_time_s\|supabase\|react" web/lib/leaderboard.js` | no output (exit 1) |
| `cd web && npx eslint lib/leaderboard.js` | exit 0, zero errors — baseline (26 problems / 23 errors, 88-05) unchanged |
| `cd web && npm run build` | exit 0, clean — no-regression only, nothing imports the module yet |
| `git status --porcelain web/ scratch/leaderboard_check.mjs` | two `??` lines and nothing else — the plan was purely additive as promised |

Exports, confirmed by importing the module under bare node:
`MIN_DIST_M · DEFAULT_N · LEADERBOARD_METRICS · metricByKey · SESSION_SELECT · isEligible ·
metricValue · lastNMean · rankBoard`

## Accomplishments

- **The lap-time defect is now structurally unreachable, not just documented.** `elapsed_s` is
  computed from `finish_s − dive_start_s`; the stored scalar is absent from `SESSION_SELECT`, and
  two source-text assertions fail loudly if a future edit reintroduces either the field name or its
  `t[-1]` derivation.
- **The catalog and the query cannot drift apart.** A per-metric loop asserts every catalog key
  appears in `SESSION_SELECT`, with `elapsed_s` handled by asserting its two boundary inputs
  instead — so adding a ninth metric without extending the select fails the harness.
- **The two branches most likely to be wrong in production are pinned on realistic data shapes.**
  Shared ranks (`1,2,2,4`) and the null-valued unranked entry both have checks, and the end-to-end
  section reproduces the live case where an athlete has the metric on none of his eligible swims.
- **Order-invariance is tested twice, two different ways** — a full reverse, and an athlete
  interleave that preserves each athlete's newest-first order while changing the input order
  completely. The second is the one that would catch a grouping-order dependency.
- **A cheaper harness pattern for pure libs.** 87-02 / 88-03 / 88-04 / 88-05 all transpile JSX and
  server-render because the subject was a component. This one imports the module directly: no
  `typescript`, no staging inside `node_modules`, no cleanup, ~40 fewer lines of scaffolding.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/leaderboard.js` | Created (162 lines) | The pure ranking core: `MIN_DIST_M`, `DEFAULT_N`, `LEADERBOARD_METRICS`, `metricByKey`, `SESSION_SELECT`, `isEligible`, `metricValue`, `lastNMean`, `rankBoard` |
| `scratch/leaderboard_check.mjs` | Created (314 lines) | 63 checks in 6 sections, one per AC plus an end-to-end board |
| `.paul/STATE.md` | Modified | Loop position + 90-01 outcome |
| `.paul/ROADMAP.md` | Modified | Phase 90 row: 1 of 3 plans applied |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Reword the module header so `lap_time_s`, `t[-1]`, `supabase` and `react` never appear in the file | Task 1 asked for a header explaining what is *not* used here; Task 2 and the verification gate ban those exact strings from the file. Both failed on the **documentation** on first run. Weakening the assertions to "not in code, only in comments" would need a parser and would be the softer guarantee. | The bans stay simple string checks. A comment in the header tells the next editor the file is asserted on by source text, so the workaround is not mistaken for coyness. |
| Export `metricByKey` and let `rankBoard` accept a key string | `reportMetrics.js` already exports exactly this helper, and 90-02/90-03 will iterate the catalog by key. Two lines. | `rankBoard(rows, "mean_vel_ms", …)` and `rankBoard(rows, spec, …)` both work; an unknown key returns an empty board rather than throwing. Beyond the plan's enumerated exports — AC-5's "exactly 8 entries" is untouched. |
| `n` on a board entry counts **values**, `swims` counts **eligible rows** | They differ exactly when a swim lacks the metric, which is the case 90-03 has to render honestly ("mean of 3 of his 5 swims"). | 90-03 can caption a row without recomputing anything. |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Self-inflicted, caught by the harness on its first run |
| Scope additions | 1 | Two lines, matches an existing repo convention |
| Deferred | 0 | — |

**Total impact:** No scope creep. Both tasks landed as written; the module's public surface is the
plan's list plus one convention-matching helper.

### Auto-fixed Issues

**1. [self-inflicted] The harness's source-text bans tripped on the module's own comments**
- **Found during:** Task 2 (first harness run — 61 passed, **2 failed**)
- **Issue:** Task 1 specified a header comment reading "No React, no Supabase" and quoting
  `float(t[-1])` as the defect being avoided. Task 2 specified assertions that the file contains
  neither `t[-1]` nor `lap_time_s`, and the plan's verification gate greps for
  `lap_time_s|supabase|react`. The two instructions are in direct tension: the documentation
  contained the banned strings.
- **Fix:** Reworded the header — "No JSX, no database client" and "the LAST TIMESTAMP of the trace
  … (metrics.py:1870)" — and added a line telling the next editor the file is asserted on by source
  text. The assertions were **not** relaxed.
- **Files:** `web/lib/leaderboard.js` (header comment only)
- **Verification:** re-run → 63 passed, 0 failed, exit 0; the gate grep returns nothing.

### Deferred Items

None. Nothing new was discovered that this plan chose not to handle.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| A bash heredoc write of the module failed on quoting before creating anything | Wrote the file with the editor tool instead; nothing partial was left on disk (`ls` confirmed no file existed). No effect on the deliverable. |

## Next Phase Readiness

**Ready:**
- 90-02 can import `SESSION_SELECT` and `isEligible` directly — the select string was measured
  working against the live DB during planning (99 rows, 47 KB, 0.76 s) and is now a single exported
  constant, so the query and the catalog cannot drift.
- 90-03 can call `rankBoard` and render `{athleteId, name, value, n, swims, rank}` without any
  further arithmetic, and its load-bearing "imperial render produces the same names and ranks"
  assertion is already structural: `unitConvert.js` is not imported here and cannot be, by test.

**Concerns:**
- **`recorded_at` is upload time, not swim time.** `api.py` never sets it, so it takes the schema
  default `NOW()`. "Last 5 swims" is really "last 5 uploads" — identical whenever upload follows
  the swim by minutes, wrong for a late queued upload. Stated in the module header, deliberately
  with no fallback chain; **90-02/90-03 owe this a visible caveat in the UI.**
- **The `lap_time_s` defect is wider than this phase.** `web/lib/reportMetrics.js` still labels the
  same field "Lap Time" on the parent report card, and it also feeds `GroupCompare`. Untouched here
  by boundary; still owed.
- Ranking assumes the caller passes rows already ordered newest-first. That contract lives in a
  comment and in 90-02's query, not in a type — the harness cannot catch a caller that forgets.

**Blockers:** None. 90-02 is unblocked.

**Skill audit:** No `.paul/SPECIAL-FLOWS.md` in this repo — not applicable.

---
*Phase: 90-team-leaderboards, Plan: 01*
*Completed: 2026-09-01*
