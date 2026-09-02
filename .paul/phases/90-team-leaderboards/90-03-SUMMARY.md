---
phase: 90-team-leaderboards
plan: 03
subsystem: ui
tags: [leaderboard, react, ssr-harness, unit-conversion, ranking, portal, tailwind]

# Dependency graph
requires:
  - phase: 90-team-leaderboards
    provides: "90-01's rankBoard + LEADERBOARD_METRICS; 90-02's /app/leaderboard shell, fetchLeaderboard() and scratch/_lb_expect.py"
  - phase: 88-metric-units-and-splits
    provides: "displayUnit() (88-03 D2, display-only conversion) and useUnitPref() (the standing swimnetics.unit key)"
provides:
  - web/components/portal/LeaderboardBoard.js — one metric's ordering, top-5 with show-all, unranked rows
  - /app/leaderboard's eight boards per stroke + the metric/imperial toggle
  - scratch/leaderboard_check.mjs's render half — 63 -> 97 checks, still no auth/network/dev server
affects: [89-account-model-rework, 80-stroke-cycle-segmentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reset component state by REMOUNTING on a composite key, never by setState in an effect"
    - "Prove a display transform harmless by asserting the NAME and RANK sequences are identical between two renders"

key-files:
  created: [web/components/portal/LeaderboardBoard.js]
  modified: [web/app/app/leaderboard/page.js, scratch/leaderboard_check.mjs]

key-decisions:
  - "The board's key carries the stroke (`${stroke}:${metric}`), so a tab switch remounts it and the show-all collapses — no effect resets state, so react-hooks/set-state-in-effect stays satisfied structurally"
  - "'Show all N' counts RANKED athletes only — unranked rows are always visible, so counting them would promise rows already on screen"
  - "The seconds board is NOT special-cased: displayUnit('s', true) returns factor 1 and the same string, and the harness asserts the imperial render is byte-identical to the metric one"
  - "The unit toggle sits on the stroke-tab row rather than below the caveat block (approved at the human-verify checkpoint)"

patterns-established:
  - "A unit toggle is proved safe by comparing ORDERINGS across two renders, not by inspecting the conversion arithmetic"
  - "The 87-02 initializer-rewrite trick has a second user; the rewritten string is asserted first, so a moved line fails loudly instead of silently leaving a branch uncovered"

# Metrics
duration: ~35min
started: 2026-09-02T19:00:00Z
completed: 2026-09-02T19:35:00Z
---

# Phase 90 Plan 03: The Boards — Summary

**The phase's actual deliverable is on screen and human-verified: eight ranked boards per stroke,
top five with the full order one click away, missing values shown as unranked rather than last, and
a unit toggle that changes every number and no rank — the last of those proved structurally, by
asserting the name and rank sequences are identical between a metric render and an imperial one.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min |
| Started | 2026-09-02T19:00:00Z |
| Completed | 2026-09-02T19:35:00Z |
| Tasks | 4 of 4 (3 auto + 1 blocking human-verify, approved) |
| Files created | 1 (82 lines) |
| Files modified | 2 (+270 harness, +94/−50 page) |
| Harness | 63 → **97 checks**, 0 failed |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: A board reads as an ordering | **Pass** | Harness: title === catalog label; both direction phrasings render; row one parses as `1 \| Ana \| 1.88 \| m/s` with `n=5`; ranked best-first. Human-verified: Max leads freestyle Average speed at ~1.88 m/s, n=5 |
| AC-2: Top five, full order one click away | **Pass** | 7-athlete board → 5 rows, ranks `1,2,3,4,5`, control reads "Show all 7"; expanded → 7 rows, control reads "Show top 5", first five unchanged; 4-athlete board → 4 rows and **no `<button>` at all** |
| AC-3: A missing value is shown, not hidden, not ranked | **Pass** | Unranked entry sorts last, renders an em dash, carries no rank number, and is excluded from the count ("Show all 6", never 7); the note renders iff an unranked entry exists. Live case confirmed on screen: breaststroke Split 15–20 m is **4 of 5 ranked** |
| AC-4: The toggle converts every value and reorders nothing | **Pass** | **The load-bearing check.** Name sequence and rank sequence identical between the two renders; all five value strings changed (`1.88,1.80,1.72,1.64,1.56` → `2.06,1.97,1.88,1.79,1.71`); unit m/s → yd/s; top value equals `M_TO_YD` applied at format time |
| AC-5: Eight boards per stroke, switches cleanly | **Pass** | `LEADERBOARD_METRICS.map` in catalog order on a `sm:grid-cols-2` grid; `key={stroke:metric}` remounts every board on a tab switch. Human-verified: nothing stayed expanded across tabs |
| AC-6: Lap time is visibly the derived one | **Pass** | Fixture row carrying `lap_time_s: 39.0` alongside boundaries giving 15.1 renders **15.1**, and `"39.0"` appears nowhere in the markup. Human-verified: no 39.0 s row on any board |
| AC-7: The harness covers what a render can prove | **Pass** | `node scratch/leaderboard_check.mjs` → **97 passed, 0 failed**, exit 0, with no auth, no network and no dev server |
| AC-8: Verified on screen by a human | **Pass** | Approved at the blocking checkpoint against `scratch/_lb_expect.py`'s independent census |

## Verification Results

| Gate | Result |
|------|--------|
| `node scratch/leaderboard_check.mjs` | **97 passed, 0 failed**, exit 0 |
| `cd web && npm run build` | Clean, **21 routes**, exit 0 |
| `cd web && npx eslint .` | **26 problems / 23 errors — exactly the baseline**, zero new |
| Seven standing harnesses, **unedited** | `anchor_check` 17/17 · `stroke_toggle_check` 63/63 · `overlay_render_check` 40/40 · `marketing_render_check` 45/45 · `unit_check` 63/63 · `split_picker_check` 44/44 · `trend_toggle_check` 39/39 |
| `pytest tests/` | **566 passed**, 1 pre-existing warning |
| `scratch/_lb_expect.py` census | Freestyle 7/42 · Butterfly 4/28 · Breaststroke 5/12 · Backstroke 2/2 · no udk tab · 84 of 108 eligible |

## Accomplishments

- **The unit toggle's safety is structural, not hoped for.** `rankBoard` runs on SI and `factor` is
  applied at the point of formatting only — no rescale before sorting, no rank recomputed from a
  converted number, nothing converted fed back anywhere. The harness pins it by extracting the name
  and rank sequences from both renders and comparing them, which is a check that fails the moment
  someone "optimises" by scaling entries up front.
- **The seconds board proves 88-03 D1's design.** `displayUnit("s", true)` returns factor 1 and the
  same unit string by construction, so Lap time needed no special case — and the harness asserts
  the imperial render is **byte-identical** to the metric one rather than merely "looks the same".
- **The defect Phase 90's planning found stays fixed on screen.** `metrics_json.session.lap_time_s`
  is the recording duration (19 of 84 eligible sessions read exactly 39.0 s, the firmware's fixed
  record length). The board is asserted to render the derived `finish_s − dive_start_s` and to
  contain no `39.0` anywhere, in the harness and by eye.
- **A missing value is a visible absence.** The one live case — an athlete with no `splits_20m` on
  either of his eligible breaststroke swims — renders at the bottom with a dash, no rank, and a line
  saying it is not last place. He is excluded from the "Show all N" count, so the control never
  promises a row that is already on screen.
- **The show-all state cannot leak across tabs**, and not because an effect clears it: the call
  site's `key` carries the stroke, so a tab switch remounts every board. This repo treats
  `react-hooks/set-state-in-effect` as an error and 87-02 shipped a defect learning that lesson.

## Task Commits

Phase 90's convention is **one commit per plan, made at UNIFY** (`b7a0a6f` for 90-01, `eb3f596`
for 90-02) — not per-task commits. 90-03 follows it:

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Tasks 1–3 + plan close | see phase commit below | feat | Board component, eight boards + unit toggle, harness render half |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/LeaderboardBoard.js` | Created (82) | One metric's board: header + direction words, up to five ranked rows, unranked rows, the show-all control, the no-rank note |
| `web/app/app/leaderboard/page.js` | Modified (+94/−50) | 90-02's placeholder per-metric count replaced by a `sm:grid-cols-2` grid of eight boards; `useUnitPref()` + the report card's toggle control; `displayUnit` passed down so the page does no arithmetic |
| `scratch/leaderboard_check.mjs` | Modified (+270) | Section 7 — the render half; header rewritten because 90-01's "no typescript, no react-dom/server, no staging" claim stopped being true |
| `.paul/STATE.md` | Modified | Loop position, then closure |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `key={`${stroke}:${metric.key}`}` at the call site | Remounting is the only reset that does not need an effect; this repo errors on `set-state-in-effect` | AC-5's "no expanded state leaks" is structural. Any future per-board state gets the same reset for free |
| "Show all N" counts **ranked** entries only | Unranked rows are always rendered, so including them would name a count of rows the coach can already see | The control's number always equals the number of rows that appear |
| No special case for the seconds board | `displayUnit("s", true)` already returns `{factor: 1, unit: "s"}`; special-casing would duplicate a rule that already holds | One fewer branch, and the harness can assert byte-identity instead of approximate sameness |
| Unit toggle on the stroke-tab row | It is the row directly above the caveat block, and it matches how the report card puts the toggle in a header row | Cosmetic; raised at the checkpoint and approved |
| `metric.unit === "s" ? 1 : 2` decimals | Keyed off the **SI** unit, not the display unit — the two are the same for seconds, but keying off SI cannot drift if a future unit converts | Lap time prints `15.1`, speeds print `1.88` |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Header prose corrected in a file this plan owns |
| Scope additions | 0 | — |
| Cosmetic, approved at checkpoint | 1 | Toggle placement |
| Deferred | 0 | — |

**Total impact:** No scope creep. Every boundary held — `leaderboard.js`, `leaderboardData.js`,
`unitConvert.js`, `useUnitPref.js`, `components/portal/phases/*`, the Python pipeline and the other
six harnesses are byte-untouched.

### Auto-fixed Issues

**1. [Docs] `leaderboard_check.mjs`'s header asserted a property this plan removed**
- **Found during:** Task 3
- **Issue:** 90-01's header said the harness was "SIMPLER THAN THE RECENT HARNESSES ON PURPOSE …
  no `typescript`, no react-dom/server, no node_modules staging, no cleanup." Section 7 uses all
  four. Left alone, the file would open with a false claim about itself.
- **Fix:** Header rewritten to scope that claim to sections 1–6 and to state section 7's measured
  limitation (`renderToStaticMarkup` runs no effects and dispatches no clicks, so `expanded` is
  reached by the 87-02 initializer rewrite, and the button's actual click is human-verify step 4).
- **Files:** `scratch/leaderboard_check.mjs` — in this plan's `files_modified`, so no boundary crossed.
- **Verification:** 97/97 green; the rewrite target string is itself asserted before use.

### Approved Deviations

**1. Unit toggle placement.** Plan said "placed near the caveat block"; it sits right-aligned on the
stroke-tab row, which is the row immediately above that block. Presented at the checkpoint and
approved.

**2. The plan's verify text was stale about one number.** Step 7 said the caveat should read "15 of
99 today"; the library has since grown to **108 sessions, 84 eligible, 24 excluded**. No code
change — 90-02 made that count computed from loaded data precisely so growth does not falsify the
page. The per-stroke census the checkpoint actually turns on (7/42, 4/28, 5/12, 2/2, no udk) is
unchanged.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| The agent could not drive the browser itself — in-session navigation to `localhost:3000` was denied, and the page is behind a coach sign-in that must not be performed on the user's behalf | Confirmed what was confirmable without a browser: route returns **200**, dev-server logs show **no errors**, and `_lb_expect.py`'s independent census was printed for comparison. AC-8 rested entirely on the human's inspection — recorded here rather than implied to have been machine-checked |

## Next Phase Readiness

**Ready:**
- All five CONTEXT goals are delivered and seen: (1) squad ordered per metric per stroke in one
  glance; (2) every swimmer on every board for a stroke they have swum, including unranked;
  (3) nothing wrong for an invisible reason — 25 yd assumption, guard count and last-5 rule are all
  stated on the page; (4) no schema, no backfill, nothing stored; (5) the deferred work has a named
  seam.
- `fetchLeaderboard()` remains the single function Phase 89 D1 has to rewrite. 90-03 added no second
  reader — the boards receive rows as props and no board reaches back to the roster.
- Phase 80 (stroke-cycle segmentation) has a place to land: when cycle metrics become rankable, they
  are catalog entries in `LEADERBOARD_METRICS`, and the page renders however many the catalog holds.

**Concerns:**
- **`rankBoard` runs 8× per render with no `useMemo`** — on every tab switch and every unit flip.
  Instant at 84 rows (CONTEXT D6 measured this), but it is the first thing to memoise if the library
  grows an order of magnitude.
- **The 25 yd assumption (D2 / R1) is still unverifiable in the data and still load-bearing** for
  every lap-time and split comparison. Nothing in Phase 90 made it safer; the page states it.
- **`recorded_at` is upload time, not swim time** (STATE owed item 22), so "last 5 swims" is really
  "last 5 uploads". `session_start_utc_ms` (86-01) is the right field and does not yet cover the
  library.

**Blockers:** None.

---
*Phase: 90-team-leaderboards, Plan: 03*
*Completed: 2026-09-02*
