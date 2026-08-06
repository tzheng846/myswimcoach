---
phase: 48-athlete-create-fix
plan: 01
subsystem: backend
tags: [bugfix, supabase, postgrest, dependency-pinning, regression-test]
requires: []
provides:
  - working POST /athletes (athlete creation restored)
  - pinned supabase/postgrest versions (reproducible Railway deploys)
  - regression guard against .single()-on-a-mutation-builder
affects:
  - 50-01 (demo seeder writes athletes directly via service role — unblocked either way)
  - any future endpoint chaining off .insert()/.update()/.delete()
tech-stack:
  added: []
  patterns: ["assert against the REAL postgrest builder class, not the conftest MagicMock"]
key-files:
  created: []
  modified: [api.py, requirements.txt, tests/test_api.py]
key-decisions:
  - "Keep .select(...) on the insert chain (valid); only .single() was invalid"
  - "Pin both supabase AND postgrest — pinning supabase alone leaves the transitive dep floating"
  - "Regression test imports SyncQueryRequestBuilder directly, because conftest's global
     create_client mock is precisely what let this bug reach production"
duration: ~25m (apply) + 10 days idle unpushed
completed: 2026-07-30
---

# Phase 48 Plan 01: Athlete-Create Fix Summary

**Restored athlete creation, which had been returning 500 in production. `.insert().select().single()`
is an invalid chain in postgrest 2.30.x — `.insert()` returns a `SyncQueryRequestBuilder` that has no
`.single()`, so the endpoint raised `AttributeError` before any network call.**

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| Coaches can add athletes again (live) | ⏳ **PENDING HUMAN-VERIFY** | Code deployed 2026-07-30; needs one live add in the coach portal |
| Regression guarded by a test on the real builder | ✅ PASS | `tests/test_api.py:1068` asserts `not hasattr(SyncQueryRequestBuilder, "single")` |
| Dependency versions reproducible across deploys | ✅ PASS | `supabase==2.30.1` + `postgrest==2.30.1` pinned in requirements.txt |

## Accomplishments
- **api.py:1306-1314** — dropped `.single()`; the chain now ends `.select(...).execute()` and the
  handler takes `(resp.data or [None])[0]`, raising a 500 if the insert returned no row.
- **requirements.txt:12-13** — pinned `supabase==2.30.1` and `postgrest==2.30.1`. The root cause was
  an unpinned `supabase`: a Railway redeploy (likely on Phase-47 `627419c`) pulled a postgrest where
  the chain became invalid, silently breaking a previously-working endpoint.
- **tests/test_api.py:1068** — regression test importing the real `SyncQueryRequestBuilder`.
- Full suite **149 passed** (was 148).
- Committed `40072e6` "Fix athlete creation endpoint" → pushed to origin/main → Railway auto-deploy.

## Verification
- `python -m pytest tests/ -q` → **149 passed** in 19.89s.
- Grep-confirmed blast radius: every other `.single()` in api.py is on a SELECT chain and is correct.

## ⚠ Important finding — systemic, not local to this bug

`tests/conftest.py` globally mocks `create_client` to return a `MagicMock`. A MagicMock answers
**every** attribute access, so any invalid supabase call chain passes the test suite silently. That
is exactly why 149 green tests did not catch an endpoint that 500s on every call.

**Consequence:** the test suite proves nothing about supabase call-chain validity anywhere in api.py.
The signal pipeline (metrics/ratings/annotations) is genuinely well covered; the database layer is
not covered at all. This bug class can recur in any endpoint on any dependency bump.

Mitigation options, cheapest first — none implemented, flagged for the Phase-51 decision:
1. Extend the builder-introspection pattern to other mutation chains (cheap, narrow).
2. A smoke test that exercises real chains against a throwaway Supabase project (real coverage, real setup cost).
3. Error monitoring, so the next one is caught in minutes rather than by hand (see below).

## Deviations from Plan
None material. Fix landed as specified.

## Process finding
The fix was applied, tested green, and then sat **uncommitted in the working tree for ~10 days**
while production kept returning 500 and STATE still read "awaiting approval." No CI ran the tests;
no error monitoring reported the live failures; the loop was never closed. This is the concrete
evidence behind the 2026-07-30 observability discussion (Phase-51 candidate: CI test gate + Sentry).

## Next Phase Readiness
Human-verify by adding an athlete in the coach portal. Then Phase 48's remaining batch items
(iOS video replay → BLE auto-reconnect → freestyle unlock) can be planned in turn.

---
*Phase: 48-athlete-create-fix, Plan: 01*
*Completed: 2026-07-30 (human-verify outstanding)*
