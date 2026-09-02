---
phase: 90-team-leaderboards
plan: 02
subsystem: ui
tags: [leaderboard, supabase-read, rls, next-route, stroke-partition, phase-89-seam]

# Dependency graph
requires:
  - phase: 90-team-leaderboards
    provides: "90-01's SESSION_SELECT, isEligible, MIN_DIST_M, DEFAULT_N, LEADERBOARD_METRICS, rankBoard"
  - phase: 75-race-phase-report-card
    provides: the `metrics_json.phases` payload the deep-scalar select reads out of
provides:
  - fetchLeaderboard() — the ONE roster + sessions read, and the single seam Phase 89 D1 rewrites
  - /app/leaderboard — the route, stroke tabs with honest counts, the caveat block, 3 load states
  - scratch/_lb_expect.py — server-side expected counts, the independent check for 90-03's verify
affects: [90-03, 89-account-model-rework]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One fetch module per page-family, so a schema rewrite lands in one function and not N components"
    - "Derive the effective tab during render; never clamp a stale selection with setState in an effect"

key-files:
  created: [web/lib/leaderboardData.js, web/app/app/leaderboard/page.js, scratch/_lb_expect.py]
  modified: [web/app/app/layout.js]

key-decisions:
  - "Imported the EXPORTED STROKE_LABELS from SessionCard.js rather than lifting GroupCompare.js's module-local copy — web/lib/leaderboard.js stayed untouched and no third copy exists"
  - "Roster-scoping happens BEFORE the guard, so `excluded` counts only swims the guard removed, never swims that were never candidates"
  - "The caveat's counts are computed from the loaded data — which is why they now read 24 of 108, not the plan's measured 15 of 99"

patterns-established:
  - "The Phase-89 rewrite target is named in a comment ON the function that has to change"
  - "A client-side partition is checked against an independent server-side count, not against itself"

# Metrics
duration: ~25min
started: 2026-09-02T05:30:00Z
completed: 2026-09-02T05:55:00Z
---

# Phase 90 Plan 02: Leaderboard Data Layer + Route — Summary

**`/app/leaderboard` exists, is in the nav, and has the right swims in it: one function issues both
queries, the 15 m guard keeps 84 of 108, and the four stroke tabs match an independently-computed
server-side census exactly — including the absence of an Underwater Dolphin Kick tab.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~25 min |
| Started | 2026-09-02T05:30:00Z |
| Completed | 2026-09-02T05:55:00Z |
| Tasks | 3 of 3 completed |
| Files created | 3 (294 lines) |
| Files modified | 1 (1 line) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: One function owns the roster read | **Pass** | `fetchLeaderboard()` is the only export in `leaderboardData.js` and holds both queries — `grep -c "supabase.from"` → **2** there, **0** in `page.js`. Its docblock names Phase 89 D1 as the reason it is a single seam, on the function itself. |
| AC-2: Session read uses 90-01's constant, newest-first | **Pass** | `.select(SESSION_SELECT)` imported from `@/lib/leaderboard` — the string is not retyped anywhere in this plan. `.order("recorded_at", { ascending: false })`. Rows are dropped to `athletes.has(row.athlete_id)` before anything else. |
| AC-3: Stroke partition, only rankable strokes | **Pass** | `_lb_expect.py` against the live DB: **Freestyle 7 athletes / 42 swims · Butterfly 4 / 28 · Breaststroke 5 / 12 · Backstroke 2 / 2**, 4 blocks summing to 84. **No udk block** — all 5 udk sessions are Leo's at 9.87–13.48 m, every one under the guard. The page derives its tabs from the same rows through the same `isEligible`. ⚠ Counts verified server-side; the on-screen render is 90-03's blocking human-verify (see Concerns). |
| AC-4: Both assumptions stated once | **Pass** | One caveat block: (a) "compared as a 25 yd effort … nothing in the recorded data confirms the distance"; (b) `{data.excluded} of {data.total} swims are excluded for covering under {MIN_DIST_M} m` — both counts come from the fetch, nothing is hard-coded; (c) "the mean of an athlete's last {DEFAULT_N} swims of that stroke". A fourth line names `recorded_at` as **upload** time, which 90-01's SUMMARY listed as owed to the UI. |
| AC-5: Route reachable, portal untouched | **Pass** | `navLinks` gains one entry between Compare and Reports; `pathname.startsWith` already highlights it. `npm run build` exit 0, **21 routes** (was 20), `/app/leaderboard` listed as static. `git diff --stat -- web/` = **1 file, 1 insertion**. |
| AC-6: Loading / empty / error distinguishable | **Pass** | `undefined` → "Loading…", `null` → "Couldn't load the leaderboard.", zero eligible → "Nothing to rank yet — all N of your swims cover under 15 m, which is the likeliest reason a swim is missing here." (and a distinct wording when nothing has been uploaded at all). No branch renders a blank page or a board of zeros. |

## Verification Results

| Check | Result |
|-------|--------|
| `cd web && npm run build` | **exit 0**, clean, **21 routes**, `/app/leaderboard` present |
| `cd web && npx eslint .` | **26 problems / 23 errors / 3 warnings** — identical to the 88-05 baseline, **zero new** |
| `node scratch/leaderboard_check.mjs` | **63 passed, 0 failed** — 90-01 untouched |
| `node scratch/anchor_check.mjs` | **17/17** |
| `node scratch/stroke_toggle_check.mjs` | **63 passed, 0 failed** |
| `node scratch/overlay_render_check.mjs` | **40/40** |
| `node scratch/marketing_render_check.mjs` | **45 passed, 0 failed** |
| `node scratch/unit_check.mjs` | **63 passed, 0 failed** |
| `node scratch/split_picker_check.mjs` | **44 passed, 0 failed** |
| `node scratch/trend_toggle_check.mjs` | **39 passed, 0 failed** |
| `PYTHONIOENCODING=utf-8 python scratch/_lb_expect.py` | 4 stroke blocks, **84 swims across blocks = 84 eligible**, read-only |
| `git status --porcelain web/ scratch/_lb_expect.py` | 1 ` M`, 3 `??` — exactly the plan's `files_modified`, nothing else |

All eight standing harnesses ran **unedited**.

### UNIFY reconciliation (2026-09-02)

Every static claim above was re-derived from the files on disk rather than trusted from the APPLY
narrative, in the posture 86-03's UNIFY established:

| Claim | Re-derived |
|-------|------------|
| One export in `leaderboardData.js` | `grep "^export"` → a single `fetchLeaderboard` at line 33 |
| Two queries there, none in the page | **2** / **0** |
| `SESSION_SELECT` imported, not retyped | `grep "metrics_json->"` over both new files → **no matches** |
| Newest-first | `.order("recorded_at", { ascending: false })` |
| Roster-scoped before the guard | `mine = filter(athletes.has(...))` precedes `.filter(isEligible)` |
| Phase 89 named on the function | line 12, inside the JSDoc attached to line 33 |
| `web/lib/leaderboard.js` untouched | `git diff --stat` → empty |
| `layout.js` one line | `git diff --numstat` → `1 0` |
| 3 load states + derived tab | `useState(undefined)`, `=== null`, `tabs.find(...) ?? tabs[0] ?? null` |

The code gates were **not** re-run: the tree has not changed since they passed except for the
comment fix below, which is non-executable text.

**One drift found and fixed at UNIFY.** The explanatory comment above the sessions query still read
"Measured against the live DB: 99 rows" — the planning-time figure, stale for the same reason the
plan's census was. Reworded to cite 99 as the measurement's size and name 108 as the shipped-at
size, so the comment cannot be misread as a current row count. Comment-only; no gate re-run needed.

## Accomplishments

- **The Phase-89 blast radius is one function, and it says so.** `fetchLeaderboard()`'s docblock
  names D1's membership-table rewrite as the change that lands there, states why no `team_id`
  filter is written today (RLS already scopes the roster), and the page below contains no
  `supabase.from("athletes")` of its own — enforced by grep, not by convention.
- **The client-side partition is checked against an independent server-side count.** `_lb_expect.py`
  reimplements the guard, the derived lap time and the rankable-athlete rule from the database
  side, so a disagreement with the page is a signal rather than a coincidence. Both agree today,
  including the awkward cell.
- **CONTEXT F6's live counter-example is confirmed, not hypothesised.** Breaststroke reads *4 of 5
  athletes ranked* on Split 15–20 m and 5 of 5 on the other seven — the unranked-row branch
  90-03 AC-3 exists for is live on real data on day one.
- **`udk` really does disappear.** Not filtered by name, not special-cased: all five udk sessions
  measure 9.87–13.48 m, the guard removes every one, and a stroke with no eligible swims is not
  offered a tab.
- **The stale-tab rule from 88-04 was followed structurally.** The active tab is
  `tabs.find(...) ?? tabs[0] ?? null`, derived during render. Nothing resets state in an effect, so
  `react-hooks/set-state-in-effect` — an error in this repo — cannot fire.

## Task Commits

All three tasks land in **one** `feat(90-02): … close plan` commit at UNIFY, bundling code, this
SUMMARY, STATE.md and ROADMAP.md — the same shape as 90-01's `b7a0a6f`. Not committed atomically
per task: the three are a single vertical slice (a read, the page that calls it, the nav entry that
reaches the page) and no intermediate state builds a working route.

| Task | Type | Description |
|------|------|-------------|
| Task 1: the single roster + sessions read | feat | `web/lib/leaderboardData.js` |
| Task 2: route, stroke tabs, caveat | feat | `web/app/app/leaderboard/page.js` |
| Task 3: nav entry + expected-counts probe | feat | `web/app/app/layout.js`, `scratch/_lb_expect.py` |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/leaderboardData.js` | Created (59 lines) | `fetchLeaderboard()` → `{athletes, rows, excluded, total}`; the two queries; the Phase-89 seam comment |
| `web/app/app/leaderboard/page.js` | Created (136 lines) | The route: 3 load states, stroke tabs with `N athletes · M swims`, the caveat block, a plain per-metric rankable count (90-03 replaces the last of these) |
| `web/app/app/layout.js` | Modified (+1) | One `navLinks` entry between Compare and Reports |
| `scratch/_lb_expect.py` | Created (99 lines) | Read-only server-side census: per stroke, eligible athletes/swims and rankable athletes per metric |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Import `STROKE_LABELS` from `@/components/portal/SessionCard` instead of lifting `GroupCompare.js`'s copy into `web/lib/leaderboard.js` | The plan offered two routes and both were slightly off on the facts: `GroupCompare.js`'s map is module-local (not exported), **but an identical map is already exported from `SessionCard.js`** and imported by `PhaseReportCard.js` and `sessions/[id]/page.js`. Importing it takes the plan's preferred branch ("import it if it is exported") against the canonical copy. | `web/lib/leaderboard.js` stayed untouched — its DO NOT CHANGE default held and the sanctioned exception was not needed. No third copy of the map exists, and `leaderboard.js` stays JSX-free and bare-node importable. |
| Roster-scope **before** applying the guard | A session belonging to another coach's athlete is not "excluded for being short" — it was never a candidate. Counting it would inflate the caveat and misattribute the reason. | `total` = the roster's swims (108 today), `excluded` = only what the 15 m guard removed (24). |
| Keep the metric list a plain count row, unstyled | Task 2 says it exists to make AC-3 readable and is replaced wholesale by 90-03's boards. | No styling is written twice; the list is `LEADERBOARD_METRICS.map` over `rankBoard(...).filter(value != null).length`, so 90-03 deletes it rather than untangling it. |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 2 | Both self-inflicted, both caught by this plan's own gates |
| Plan facts corrected | 2 | One naming fact, one census fact — neither changes the deliverable |
| Deferred | 0 | — |

**Total impact:** All three tasks landed as written. No scope creep, no boundary touched, no
protected file edited.

### Plan Facts Corrected

**1. `STROKE_LABELS` is exported — from `SessionCard.js`, not `GroupCompare.js`**
- **Plan said:** "Reuse `GroupCompare.js`'s `STROKE_LABELS` map — import it if it is exported,
  otherwise lift it into `web/lib/leaderboard.js`."
- **Actual:** `GroupCompare.js:17` declares a module-local `const`. An identical map is exported at
  `SessionCard.js:7` and already imported by two other files.
- **Resolution:** Imported from `SessionCard.js`. The plan's fallback (editing `leaderboard.js`) was
  not exercised, so the boundary's sanctioned exception went unused. ⚠ `GroupCompare.js` still
  carries its private duplicate — **not** deduplicated here, because that is a change to a file
  AC-5 says must not change.

**2. The library has grown: 108 sessions, not 99 — and the caveat says so**
- **Plan said:** "99 sessions in, **84 eligible**, 15 excluded."
- **Actual:** **108 sessions in, 84 eligible, 24 excluded.** The 9 new rows are Phase 86-03's tap
  test bench runs (2026-09-01 22:04–22:15 local, `breaststroke`, 0.0008–0.095 m) — every one under
  the guard. (Timestamps normalised from the stored `recorded_at` UTC of 2026-09-02T05:0x–05:1x,
  following 86-03's UNIFY convention: writing 09-02 would date the run after the commits that
  produced it.)
- **Impact:** **The eligible set is unchanged at 84 and every AC-3 stroke count matches the plan
  exactly.** Only the *denominator* moved. Because AC-4 requires the caveat to be computed from the
  loaded data, the page now reads "24 of 108 swims are excluded" rather than the plan's measured
  15 of 99 — which is the AC working, not failing. Anyone re-reading the plan's Task 1 note should
  treat 99/15 as a 2026-09-01 snapshot.

### Auto-fixed Issues

**1. [self-inflicted] Task 1's verify returned 0 because the queries were chained across lines**
- **Found during:** Task 1 (`grep -c "supabase.from"` → **0**, expected 2)
- **Issue:** The first draft followed `compare/page.js`'s multi-line chaining style
  (`await supabase` / `.from("athletes")` / …), so the literal string `supabase.from` never
  appeared. The verify greps for that exact token.
- **Fix:** Both queries reflowed so `supabase.from("…")` sits on one line, with the awaited call
  split afterwards instead. No behaviour change.
- **Files:** `web/lib/leaderboardData.js`
- **Verification:** re-run → **2** in `leaderboardData.js`, **0** in `page.js`.

**2. [self-inflicted] The empty-state sentence wrapped inside a template literal**
- **Found during:** post-Task-2 read-back, before the final gates
- **Issue:** The zero-eligible message was a template literal broken across two source lines, so the
  rendered string carried a newline plus 15 spaces of source indentation mid-sentence. HTML collapses
  it, so no gate would ever have caught it.
- **Fix:** Rewrote as two complete single-line strings, one per branch (some swims but all short vs.
  nothing uploaded), which also made the two cases read better than the original concatenation.
- **Files:** `web/app/app/leaderboard/page.js`
- **Verification:** rebuild → exit 0, 21 routes; eslint → baseline unchanged.

### Deferred Items

None.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| A `python - <<'PY'` heredoc calling `load_dotenv()` with no argument raised `AssertionError` in `find_dotenv()` — it walks the caller's stack frame and there is no file frame when the script arrives on stdin | Only affected a throwaway inspection script, not `_lb_expect.py` (a real file, which works). Re-ran from a scratchpad file with an explicit path. Worth knowing: **stdin heredocs cannot use bare `load_dotenv()`** — every `scratch/_lb_*.py` probe must stay a file on disk. |
| A bash heredoc write of this SUMMARY failed on quoting before creating anything | Wrote it with the editor tool instead — the same trap, and the same resolution, as 90-01. |

## Next Phase Readiness

**Ready:**
- 90-03 replaces exactly one JSX block — the `LEADERBOARD_METRICS.map` count list — with the eight
  boards. Everything it needs is already in scope at that point: `active.rows` (one stroke,
  newest-first, guard-passing, `name` attached) and `data.athletes` for `nameFor`.
- `_lb_expect.py` is the counterpart for 90-03's blocking human-verify: the page and the probe must
  print the same numbers, and the probe already prints the per-metric rankable counts the boards
  will show.
- The unit toggle 90-03 reuses is still structurally safe: nothing in this plan imports
  `unitConvert.js`, and ranking still happens on SI inside `rankBoard`.

**Concerns:**
- **AC-3, AC-4 and AC-6 are verified by construction, the build and the server-side census — not by
  looking at a rendered page.** `/app/leaderboard` sits behind the portal's auth gate, so it cannot
  be loaded headlessly here, and this plan deliberately shipped no render harness (90-01's cheap
  direct-import pattern does not reach JSX). **90-03's human-verify is the first time a human sees
  these tabs**, and it should check the four counts against `_lb_expect.py` explicitly.
- **`recorded_at` is upload time** (owed item 22) — now stated on screen rather than only in a
  comment, but still the wrong key. The 9 tap-test rows are a live demonstration: they are the
  *newest* sessions in the library and would head any last-5 window they qualified for. They do not
  qualify only because the guard removes them.
- **The `lap_time_s` defect (owed item 30) is still wider than this phase.** Untouched here;
  `reportMetrics.js` still labels the recording duration "Lap Time" on the parent report card.
- **`GroupCompare.js` keeps a private duplicate of `STROKE_LABELS`.** Two copies of that map now
  exist repo-wide (`SessionCard.js` exported, `GroupCompare.js` local), alongside the separate
  abbreviation table in `sessionName.js`. Deduplicating is a one-line change to a file this plan's
  AC-5 forbids touching — worth a future cleanup, not worth a boundary violation.

**Blockers:** None. 90-03 is unblocked.

**Skill audit:** No `.paul/SPECIAL-FLOWS.md` in this repo — not applicable.

---
*Phase: 90-team-leaderboards, Plan: 02*
*Completed: 2026-09-01*
