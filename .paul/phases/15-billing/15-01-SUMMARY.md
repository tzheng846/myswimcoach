---
phase: 15-billing
plan: 01
subsystem: payments
tags: [stripe, fastapi, supabase, subscriptions, billing]

requires: []
provides:
  - coaches table subscription columns (tier, status, athlete_limit, device_limit, monthly_session_limit, stripe_customer_id)
  - _TIER_LIMITS dict (free/starter/enterprise limits)
  - _get_coach_row() helper (reusable coach lookup)
  - POST /billing/checkout-session (Stripe checkout URL)
  - POST /billing/portal-session (Stripe customer portal URL)
  - GET /billing/complete (post-payment redirect page)
  - POST /billing/webhook (subscription event handler)
  - GET /billing/status (usage vs limits for iOS)
affects: [15-02 enforcement, iOS upgrade/manage flow]

tech-stack:
  added: [stripe]
  patterns:
    - "_get_coach_row() helper centralises the coaches lookup pattern — reuse in 15-02 enforcement"
    - "Tier limits in _TIER_LIMITS dict at module level — single source of truth for enforcement in 15-02"
    - "_stripe.api_key set inside each endpoint (not at import time) — safe with lazy env var loading"

key-files:
  modified:
    - requirements.txt
    - api.py

key-decisions:
  - "Enterprise tier (not Pro): product named 'Enterprise' in Stripe — tier identifier and env var updated throughout"
  - "STRIPE_ENTERPRISE_PRICE_ID env var (not STRIPE_PRO_PRICE_ID) — must match Railway setting"
  - "monthly_session_limit=None for paid tiers — iOS interprets null as unlimited"

patterns-established:
  - "_get_coach_row(sb_admin, user_id, fields) — use this instead of inline coach lookup in 15-02"
  - "_TIER_LIMITS['free'/'starter'/'enterprise'] — reference this dict in enforcement, not hardcoded values"

duration: ~25min
started: 2026-06-08T00:00:00Z
completed: 2026-06-08T00:00:00Z
---

# Phase 15 Plan 01: Billing Foundation Summary

**Stripe subscription billing foundation: coaches schema extended with tier/limits, checkout + portal + webhook + status endpoints live, Stripe MCP used to verify Starter ($200/mo) and Enterprise ($1,000/mo) products.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~25 min |
| Tasks | 3 completed (1 checkpoint, 2 auto) |
| Files modified | 2 |
| Tests | 26/26 pass |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Supabase coaches subscription columns | Pass | Human confirmed via checkpoint — SELECT verified defaults |
| AC-2: /billing/checkout-session returns Stripe URL | Pass | Implemented; Stripe MCP confirmed products/prices exist |
| AC-3: /billing/portal-session returns Stripe URL | Pass | Implemented; requires stripe_customer_id (set on first checkout) |
| AC-4: /billing/webhook updates coach subscription state | Pass | Handles created/updated/deleted; maps price_id → tier → limits |
| AC-5: GET /billing/status returns usage + limits | Pass | Returns tier, limits, athlete_count, device_count, session_count_this_month |
| AC-6: Import check + tests pass | Pass | `import api` ok; 26/26 pytest pass |

## Accomplishments

- Stripe billing infrastructure wired end-to-end: checkout → webhook → Supabase coaches row update → status query
- `_TIER_LIMITS` dict and `_get_coach_row()` helper extracted — Plan 15-02 enforcement reads from these directly
- Stripe MCP verified products and prices exist before writing any code (bonus: no manual lookup needed)

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `requirements.txt` | Modified | Added `stripe` |
| `api.py` | Modified | 4 env vars, `import stripe`, `_TIER_LIMITS`, `_get_coach_row()`, 5 billing endpoints |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| "Enterprise" tier (not "Pro") | Stripe product created as "Enterprise" by user | env var is STRIPE_ENTERPRISE_PRICE_ID; tier string is "enterprise" everywhere |
| `monthly_session_limit=None` for paid tiers | None serialises to JSON null; iOS reads null as "unlimited" | Plan 15-02 enforcement skips session limit check when value is None |
| `_stripe.api_key` set per-endpoint (not at import) | Env var may not be populated at import time on Railway cold start | Safe pattern; negligible overhead |
| `_get_coach_row()` extracted as helper | Four billing endpoints all need the same coaches lookup | Plan 15-02 can reuse without duplication |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Naming deviation | 1 | env var renamed; no functional impact |
| Scope addition | 1 | Stripe MCP verification step (bonus, no code change) |
| Auto-fixed | 1 | stripe not installed locally — pip install ran |

**Total impact:** Minimal. One naming change cascaded cleanly through all references.

### Naming Deviation

**Enterprise instead of Pro**
- **Found during:** Task 1 checkpoint verification via Stripe MCP
- **Issue:** Plan used "pro" / `STRIPE_PRO_PRICE_ID`; actual product in Stripe is "Enterprise"
- **Fix:** Updated all references — tier string `"enterprise"`, env var `STRIPE_ENTERPRISE_PRICE_ID`, `_TIER_LIMITS` key — before writing any code
- **Impact:** Railway env var must be `STRIPE_ENTERPRISE_PRICE_ID` (not `STRIPE_PRO_PRICE_ID`)

### Local Install

**stripe not installed in local venv**
- `pip install stripe -q` run locally; `requirements.txt` handles Railway deployment automatically

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| stripe not in local venv | `pip install stripe -q` — one-time local setup |
| Product name "Enterprise" ≠ plan's "Pro" | Caught via Stripe MCP before any code written; renamed throughout |

## Next Phase Readiness

**Ready:**
- `_TIER_LIMITS` dict ready for 15-02 enforcement — just read `_TIER_LIMITS[tier]` and compare counts
- `_get_coach_row()` helper ready — pass additional fields like `athlete_limit, device_limit, monthly_session_limit, subscription_status`
- `/billing/status` gives iOS current usage; Plan 15-02 adds server-side enforcement
- Supabase `coaches` rows default to `free` tier — no existing coach is accidentally locked out

**Concerns:**
- STRIPE_ENTERPRISE_PRICE_ID must be set in Railway (not STRIPE_PRO_PRICE_ID) — double-check before first real checkout
- Webhook signature verification requires Railway to have the correct `STRIPE_WEBHOOK_SECRET`; test with Stripe CLI (`stripe listen --forward-to ...`) before going live

**Blockers:** None

---
*Phase: 15-billing, Plan: 01*
*Completed: 2026-06-08*
