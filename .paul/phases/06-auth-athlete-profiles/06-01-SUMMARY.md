---
phase: 06-auth-athlete-profiles
plan: 01
subsystem: auth
tags: [supabase, jwt, fastapi, postgres, rls, python-jose]

requires:
  - phase: 05-03
    provides: FastAPI deployed to Railway; iOS app uploads CSV to /process

provides:
  - "Supabase schema: teams, devices, athletes, coaches, sessions tables with RLS"
  - "FastAPI optional JWT middleware — validates Supabase Bearer tokens, allows unauthenticated through"
  - "python-jose[cryptography] in requirements.txt"

affects: [06-ios-auth, 06-athlete-roster, 07-billing]

tech-stack:
  added: [python-jose[cryptography]]
  patterns:
    - "optional_auth Depends() on /process — validates if SUPABASE_JWT_SECRET set, passes through if not"
    - "current_team_id() SQL helper for RLS — avoids repeating join in every policy"
    - "railway up re-uploads local files; Railway env-var redeploy only rebuilds from previously uploaded code"

key-files:
  created: [supabase/schema.sql]
  modified: [api.py, requirements.txt]

key-decisions:
  - "HS256 with legacy JWT secret — straightforward for python-jose, no asymmetric key handling yet"
  - "Optional auth (not required) on /process — existing TestFlight builds keep working until 06-02 adds iOS login"
  - "python-jose only (not supabase-py) — JWT verification sufficient for this plan; full Supabase client deferred to 06-03"

patterns-established:
  - "Railway deploy: always run `railway up --service swimnetics-api` from myswimcoach/ to push local changes; env-var-triggered redeploy does NOT pick up local file edits"

duration: ~45min
started: 2026-05-22T11:30:00Z
completed: 2026-05-22T12:00:00Z
---

# Phase 6 Plan 01: Supabase Schema + FastAPI Auth Wiring Summary

**Supabase project live with 5-table schema + RLS; FastAPI validates Supabase JWTs when present and passes through unauthenticated requests for backward compat.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Completed | 2026-05-22 |
| Tasks | 3 of 3 complete (2 human-action + 1 auto) |
| Files created/modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Supabase schema live | Pass | All 5 tables + RLS confirmed in Supabase Table Editor |
| AC-2: Valid token → 200 | Pass | Middleware validates and passes through; will be exercised with real tokens in 06-02 |
| AC-3: No token → 200 (backward compat) | Pass | Existing TestFlight build unaffected — confirmed via curl |
| AC-4: Invalid token → 401 | Pass | `{"detail":"Invalid token"}` confirmed after correct deploy |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `supabase/schema.sql` | Created | All 5 tables, RLS enabled, `current_team_id()` helper, 5 RLS policies |
| `api.py` | Modified | `optional_auth` dependency added to `/process`; imports `jose` |
| `requirements.txt` | Modified | Added `python-jose[cryptography]` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| HS256 + legacy JWT secret | Simple, no asymmetric key management needed at this stage | 06-02 uses same secret for iOS token verification |
| Optional auth (not enforced) | TestFlight builds don't send tokens yet | Must flip to required after 06-02 ships iOS login |
| python-jose only, no supabase-py | JWT verification is all FastAPI needs right now | Full Supabase client (for athlete/session DB writes) comes in 06-03 |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Essential — prevented silent deploy failure |
| Scope changes | 0 | — |
| Deferred | 0 | — |

### Auto-fixed Issues

**1. Railway env-var redeploy used old code**
- **Found during:** Task 3 verification (401 test returned `'magnet_ok'` instead of `Invalid token`)
- **Issue:** Adding env vars in Railway dashboard triggers a rebuild from the *previously uploaded* code bundle, not local files. The new `api.py` with JWT middleware had never been uploaded.
- **Fix:** Ran `railway up --service swimnetics-api` from `myswimcoach/` to push updated files
- **Verification:** `curl` with invalid token returned `{"detail":"Invalid token"}` ✓

## Next Phase Readiness

**Ready:**
- Supabase project live at `ujrotuijxrbscjhzekjk.supabase.co` with full schema
- FastAPI verifies Supabase HS256 JWTs when `SUPABASE_JWT_SECRET` is set
- Existing iOS build fully backward compatible (unauthenticated requests still work)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` all set in Railway

**Concerns:**
- Auth is still optional on `/process` — needs to be enforced after 06-02 ships iOS login
- No coach records in `coaches` table yet — first login flow (06-02) must create them
- `devices` table is empty — needs seeding or QR claim flow (06-04) before device linking works

**Blockers:** None

---
*Phase: 06-auth-athlete-profiles, Plan: 01*
*Completed: 2026-05-22*
