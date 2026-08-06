---
phase: 51-api-correctness
plan: 02
subsystem: api
tags: [fastapi, supabase, postgrest, ast, schema-contract, multi-tenancy]

requires:
  - phase: 51-api-correctness
    provides: "51-01's API-AUDIT.md, supabase/live_schema.json, and tools/schema_contract.py — the audit that located all four sites and the AST extractor promoted here"
provides:
  - "POST /athletes works against the live schema (the 500 is gone)"
  - "team-scoped athlete queries at all four former coach_id sites"
  - "a permanent schema-contract test that fails when api.py names a column the live schema lacks"
affects: [any future athletes query, multi-coach teams, coach chat roster tools, billing status]

tech-stack:
  added: []
  patterns:
    - "athletes is scoped by team_id; sessions/devices/reports stay on coach_id"
    - "Static AST schema contract in the suite — mocks cannot guard this bug class"

key-files:
  created: []
  modified:
    - api.py
    - tests/test_api.py

key-decisions:
  - "Task 2 STRUCK before apply — superseded by 54-01's ENFORCE_TIER_LIMITS; two switches on one guard"
  - "Inverted the contradicted roster-scoping test rather than deleting it"
  - "Removed the orphaned coach_id variable our own change created"

patterns-established:
  - "Plan line numbers are re-resolved at apply time, never trusted — 52-01 and 54-01 had shifted api.py ~35-40 lines"

duration: ~35min
started: 2026-08-04
completed: 2026-08-04
---

# Phase 51 Plan 02: API Correctness Fixes Summary

**The phantom `athletes.coach_id` is gone — four sites scoped by `team_id`, `POST /athletes` works in production (`dedac17`), and an AST schema-contract test now fails the suite if any api.py column reference leaves the live schema.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min |
| Tasks | 3 of 4 (Task 2 struck as superseded) |
| Files modified | 2 |
| Suite | 172 → 176 passing |
| Schema violations | 4 → 0 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Athlete creation works against the live schema | **Pass** | Verified live by the user after `dedac17` deployed |
| AC-2: Limit count filters a column that exists | **Pass** | Enforcement itself stays off via 54-01's `ENFORCE_TIER_LIMITS` |
| AC-3: Team-wide coach chat works | **Unverified** | See Concerns — related defect found instead |
| AC-4: Billing status reports a real athlete count | **Unverified** | No client calls `/billing/status`; not exercised |
| AC-5: The bug class cannot silently return | **Pass** | Mutation-tested — see Verification |

## Accomplishments

- **Killed a production 500 that had been live since before 2026-07-30.** Coaches could not add athletes at all.
- **Fixed three silent failures alongside it** — the athlete-limit count (always threw into `except: count=0`), `/coach/chat`'s roster loader (broken since Phase 33-02), and `/billing/status` (`athlete_count` always 0).
- **Promoted 51-01's extractor into the suite.** `tests/test_api.py::TestSchemaContract` — 4 tests: api.py vs `supabase/live_schema.json`, plus three self-checks covering a bad `eq`, a bad insert payload key, and the regex-era false-positive case (response-dict keys and `select("*")`).

## Verification Results

```
python tools/schema_contract.py api.py supabase/live_schema.json
  → 4 violations  →  no violations

python -m pytest tests/ -q
  → 176 passed  (was 172; +4 schema-contract tests)

python -c "import api"
  → clean
```

**Mutation test (Task 3's required proof).** Reintroduced `coach_id` on the athletes count chain; the suite failed with `api.py:1310  athletes.coach_id  [eq]` — file, line, table, column, operation. Reverted, green again. Without this the extractor could have been silently broken and passed forever.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `api.py` | Modified | 6 edits: insert key removed (:1335), limit count → team_id (:1311), chat coach lookup widened to `id, team_id` (:1430), roster → team_id (:1551), billing `_get_coach_row` field list widened (:1807), billing count → team_id (:1818) |
| `tests/test_api.py` | Modified | New `TestSchemaContract` (4 tests); `_team_admin` fixture gained `team_id`; one contradicted assertion inverted |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Strike Task 2 before applying | 54-01 had already shipped `ENFORCE_TIER_LIMITS` covering all three limits; adding `ENFORCE_ATHLETE_LIMIT` would double-gate the same block | One switch, not two. Plan amended and re-approved before apply |
| Scope by `team_id`, not add a `coach_id` column | Athletes belong to a team; the portal, RLS, and `seed_demo_team.py` all already scope that way | On multi-coach teams, counts and the chat roster are now team-wide — intended, recorded below |
| Invert the contradicted test, don't delete it | It asserted the bug as expected behavior; deleting would lose the coverage | Now asserts team-scoping AND that no athletes query carries `coach_id` |
| Remove the orphaned `coach_id` variable | Both of its readers changed; our own edit made it unused | Matches the repo's "clean up only your own mess" rule |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Essential — a test encoded the bug |
| Scope additions | 0 | — |
| Struck before apply | 1 | Task 2, superseded |

### Auto-fixed

**1. [test] A test asserted the defect as correct behavior**
- **Found during:** Task 1 verification (suite went red on the first run)
- **Issue:** `tests/test_api.py:668` — *"Both roster queries filtered by coach_id"* — the exact behavior being fixed. The `_team_admin` fixture also returned a coaches row with no `team_id`, so the roster query would have filtered on `None` and passed vacuously.
- **Fix:** fixture gained `team_id="team-1"`; assertion now checks athletes→`team_id` **and** that no athletes query carries `coach_id`; the sessions→`coach_id` assertion kept.
- **Verification:** 176 passing.

### Deferred Items

Audit findings triaged in Task 0, dispositions recorded:
- **F2, F3** → closed by Phase 52 (`89205ca`).
- **F4** (limits fail open) — athlete half moot (54-01 turned enforcement off); session/device fail-open → own plan.
- **F5** (iOS displays `teams.swimmer_limit`, API enforces `coaches.athlete_limit`) → recommend `coaches` authoritative; `teams.coach_limit` has no equivalent so the merge is not mechanical. iOS out of scope. **User call, open.**
- **F6** (7/11 coach lookups mask DB errors as 403), **F8** (`_get_coach_row` inlined 11×) → own plan; F8 would fix F6 in the same pass.
- **F9** (`GET /export` has no caller) → kept; 52-01 had just updated it. **User call, open.**
- **F7, F10, F11** → accept-and-document.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Plan line numbers stale by ~35-40 lines (52-01 + 54-01 had both edited api.py) | Re-resolved every site by content before editing; plan amended to say line numbers are re-resolved, never trusted |
| `api.py` carried 54-01's uncommitted work, unsplittable by file | Disclosed before commit; `dedac17` deliberately ships both |

## Next Phase Readiness

**Ready:**
- Athlete creation works; the roster tools `/coach/chat` needs are functional for the first time since 33-02.
- The schema contract runs on every `pytest` invocation.

**Concerns:**
- **AC-3 and AC-4 were never verified.** Exercising the AC-3 path instead surfaced a *different* defect: `list_athlete_sessions` has no athlete parameter and is bound to the chat's anchor session, so naming another athlete returns the anchor athlete's data under that name. Cross-athlete attribution, not a phrasing bug. ROADMAP row 56, unscheduled.
- **The snapshot guards code-vs-snapshot, not snapshot-vs-reality.** A migration without `python tools/introspect_schema.py` silently re-opens the gap. Whether that belongs in CI is undecided.
- Multi-coach teams now see team-wide athlete counts and chat rosters. Correct per the schema; will look different if a second coach is ever added.

**Blockers:** None.

---
*Phase: 51-api-correctness, Plan: 02*
*Completed: 2026-08-04*
