---
phase: 06-auth-athlete-profiles
plan: 02
subsystem: auth
tags: [supabase, react-navigation, expo-secure-store, jwt, fastapi, hermes, metro, ios]

requires:
  - phase: 06-01
    provides: Supabase schema live, FastAPI optional JWT middleware, SUPABASE env vars in Railway

provides:
  - "iOS login screen (email/password) with Supabase Auth"
  - "React Navigation AuthStack/AppStack — gates RecordScreen behind login"
  - "Supabase session persisted to iOS Keychain via expo-secure-store"
  - "AppState-aware token auto-refresh (startAutoRefresh/stopAutoRefresh)"
  - "FileSystem.uploadAsync attaches Bearer token — FastAPI verifies via supabase-py auth.get_user()"
  - "Sign Out button on RecordScreen"

affects: [06-athlete-roster, 06-device-qr, 07-billing]

tech-stack:
  added:
    - "@supabase/supabase-js (iOS client)"
    - "expo-secure-store (Keychain session storage)"
    - "@react-navigation/native + native-stack"
    - "react-native-screens + react-native-safe-area-context"
    - "supabase (Python SDK, FastAPI token verification)"
  patterns:
    - "Metro CJS redirect: resolveRequest forces @supabase/supabase-js → dist/index.cjs to avoid Hermes dynamic import error"
    - "supabase-py auth.get_user(token) for server-side JWT verification — works with any Supabase signing scheme"
    - "sessionRef pattern in RecordScreen: useRef mirrors session state so uploadAndProcess useCallback reads latest token without adding session to deps"
    - "AppState listener in AuthProvider: startAutoRefresh on 'active', stopAutoRefresh otherwise"

key-files:
  created:
    - swimnetics-mobile/src/lib/supabase.js
    - swimnetics-mobile/src/context/AuthContext.js
    - swimnetics-mobile/src/screens/LoginScreen.js
  modified:
    - swimnetics-mobile/App.js
    - swimnetics-mobile/src/config.js
    - swimnetics-mobile/src/screens/RecordScreen.js
    - swimnetics-mobile/metro.config.js
    - swimnetics-mobile/package.json
    - myswimcoach/api.py
    - myswimcoach/requirements.txt

key-decisions:
  - "supabase-py auth.get_user() replaces python-jose: new Supabase uses asymmetric JWT signing, not HS256"
  - "Metro CJS redirect for @supabase/supabase-js: Hermes rejects dynamic import(variable) in .mjs build"
  - "sessionRef pattern in RecordScreen: avoids session in useCallback deps while always reading latest token"
  - "AppState token refresh: required by Supabase RN docs to prevent expired tokens after backgrounding"

patterns-established:
  - "For Supabase JWT verification in FastAPI: use supabase-py auth.get_user(token), not python-jose"
  - "For @supabase/* packages with OTEL: add Metro resolveRequest CJS redirect + @opentelemetry/api empty stub"
  - "New EAS builds after JS dependency changes always require a full eas build (not just env-var redeploy)"

duration: ~3h (including 2 EAS build failures + auth debugging)
started: 2026-05-22T12:00:00Z
completed: 2026-05-22T14:00:00Z
---

# Phase 6 Plan 02: iOS Login + Navigation Summary

**Supabase email/password login, React Navigation auth gating, and Bearer-token uploads verified end-to-end on iPhone — coaches must log in before recording.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~3 hours |
| Completed | 2026-05-22 |
| Tasks | 3 of 3 complete (1 auto + 2 checkpoints) |
| EAS builds | 3 (2 failed, 1 succeeded) |
| Files created/modified | 11 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Login screen on cold launch | Pass | Verified on device — LoginScreen shown before RecordScreen |
| AC-2: Valid credentials → RecordScreen + persists | Pass | Login works; force-quit and reopen goes straight to RecordScreen |
| AC-3: Wrong password → error on LoginScreen | Pass | Red error message shown, stays on LoginScreen |
| AC-4: Upload includes Bearer token, FastAPI accepts | Pass | Metrics + chart appear after recording; no 401 |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/src/lib/supabase.js` | Created | Supabase client with expo-secure-store session adapter |
| `swimnetics-mobile/src/context/AuthContext.js` | Created | Session state, AppState refresh, signOut |
| `swimnetics-mobile/src/screens/LoginScreen.js` | Created | Email/password login form with error display |
| `swimnetics-mobile/App.js` | Modified | NavigationContainer + AuthProvider + AuthStack/AppStack |
| `swimnetics-mobile/src/config.js` | Modified | SUPABASE_URL + SUPABASE_ANON_KEY added |
| `swimnetics-mobile/src/screens/RecordScreen.js` | Modified | sessionRef + Bearer header on upload + Sign Out button |
| `swimnetics-mobile/metro.config.js` | Modified | CJS redirect for supabase-js + OTEL empty stub |
| `swimnetics-mobile/package.json` | Modified | 6 new packages added |
| `myswimcoach/api.py` | Modified | supabase-py auth.get_user() replaces python-jose; null guard added |
| `myswimcoach/requirements.txt` | Modified | python-jose → supabase |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| supabase-py `auth.get_user()` for token verification | New Supabase projects use asymmetric JWT signing — python-jose HS256 always rejected valid tokens | Any Supabase signing scheme works; adds ~50ms latency per upload |
| Metro CJS redirect for `@supabase/supabase-js` | `.mjs` build uses `import(variable)` — Hermes compile error; `.cjs` uses `require(s)` which is fine | Required for any Expo/RN bare project using Supabase v2 |
| `sessionRef` in RecordScreen | Avoid adding `session` to `uploadAndProcess` useCallback deps (which would cascade to `stopRecording`) | Clean auth injection without disrupting existing BLE callback chain |
| AppState token refresh | Official Supabase RN docs: without this, JWT expires while app is backgrounded → next upload 401s | Auth stays valid across typical coaching session (app backgrounded between swims) |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 4 | All essential; no scope creep |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** Essential fixes only. Auth works correctly on device.

### Auto-fixed Issues

**1. Hermes dynamic import compile error (2 EAS build failures)**
- **Found during:** Task 3 (EAS build verification)
- **Issue:** `@supabase/supabase-js` `.mjs` build contains `import(OTEL_PKG)` with a variable. Hermes can't compile dynamic imports with non-literal arguments.
- **Fix:** `metro.config.js` `resolveRequest` redirects `@supabase/supabase-js` → `dist/index.cjs` (which uses `require(s)` instead); stubs `@opentelemetry/api` as empty module
- **Files:** `swimnetics-mobile/metro.config.js`
- **Verification:** Third EAS build succeeded; app installed and ran on device

**2. JWT verification rejected valid tokens (401 on all uploads)**
- **Found during:** Task 3 (AC-4 upload verification)
- **Issue:** `python-jose` HS256 verification with legacy JWT secret failed because the new Supabase project uses asymmetric signing keys, not HS256
- **Fix:** Replaced `python-jose` with `supabase-py` `auth.get_user(token)` — delegates verification to Supabase Auth API, works with any signing scheme
- **Files:** `myswimcoach/api.py`, `myswimcoach/requirements.txt`
- **Verification:** Uploads return 200 with metrics; `curl` with invalid token returns 401

**3. Missing AppState token refresh (audit finding)**
- **Found during:** Pre-build code audit
- **Issue:** Without `AppState` listener, Supabase stops auto-refreshing the JWT when the app is backgrounded. After ~1 hour, the token expires and the next upload 401s.
- **Fix:** Added `AppState.addEventListener` in `AuthProvider` calling `startAutoRefresh`/`stopAutoRefresh`
- **Files:** `swimnetics-mobile/src/context/AuthContext.js`

**4. Missing `response.user` null guard (audit finding)**
- **Found during:** Pre-build code audit
- **Issue:** `response.user.id` would throw `AttributeError` (500) instead of 401 if `get_user()` returned a response with `user=None`
- **Fix:** Added `if not response.user: raise HTTPException(401)` before `.id` access
- **Files:** `myswimcoach/api.py`

## Next Phase Readiness

**Ready:**
- Coach login works end-to-end on iPhone — session persists, uploads authenticated
- FastAPI verifies Supabase JWTs correctly for any signing scheme
- AppState-aware token refresh prevents expiry during coaching sessions
- Architecture patterns established for 06-03 (AuthContext + sessionRef reusable)

**Concerns:**
- `/process` endpoint still accepts unauthenticated requests (optional auth). Should flip to required once 06-03 ships and all athletes are selected pre-record.
- No athlete selection before recording yet — sessions saved to Railway without athlete association (06-03 fixes this)
- `SUPABASE_JWT_SECRET` env var in Railway is now unused (python-jose removed) — can be cleaned up

**Blockers:** None

---
*Phase: 06-auth-athlete-profiles, Plan: 02*
*Completed: 2026-05-22*
