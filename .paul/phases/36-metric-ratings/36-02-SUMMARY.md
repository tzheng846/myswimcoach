---
phase: 36-metric-ratings
plan: 02
subsystem: ui
tags: [next, react, ratings, accessibility, recharts-free]
requires:
  - phase: 36-01
    provides: GET /sessions/{id}/ratings + RATINGS-SPEC.md payload contract
provides:
  - Web pillar cards on the session report card (band meter + marker + verdict + trend + expand)
  - Raw MetricGrid demoted to Advanced view
affects: [iOS ratings UI (future, mirrors RATINGS-SPEC.md)]
tech-stack:
  added: []
  patterns: ["client component fetches shared ratings endpoint; colors from payload, not hard-coded"]
key-files:
  created: [web/components/portal/PillarCards.js]
  modified: ["web/app/app/sessions/[id]/page.js"]
key-decisions:
  - "Simple view = pillars; Advanced view = raw MetricGrid + per-cycle"
  - "Verified web component against real local backend (endpoint not on Railway yet)"
duration: ~1.5h (incl. review-hardening pass)
completed: 2026-06-17
---

# Phase 36 Plan 02: Web Pillar Cards Summary

**Glanceable good/ok/needs-work pillar cards (fixed red/amber/green band + score marker + trend chip + tap-to-expand metrics) on the web session report card, reading the shared `/sessions/{id}/ratings` endpoint.**

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Pillar cards render from endpoint | Pass | 4 cards, consistent bands, marker at real `score` (Speed 69/Length 80/Consistency 71/Endurance 47), verdict color-matched, trend chips, expand → metrics + explanation, provisional chip |
| AC-2: Raw grid demoted; states handled | Pass | Simple = pillars, Advanced = MetricGrid + per-cycle; `unknown` → "Not enough data"; load failure → graceful inline message |

## Accomplishments
- `PillarCards.js`: fetches the endpoint, renders the approved mockup (linear traffic band, score marker, semantic trend chip, accordion expand). Colors come from the payload `rating_colors` (never hard-coded per component).
- Mounted on the report card: Simple → pillars, Advanced → existing raw grid (numbers on demand).
- Verified end-to-end against a **local backend** (ran uvicorn on :8000, repointed `web/.env.local`) since the endpoint isn't on Railway yet — real payload, real data, no console errors.

## Files Created/Modified
| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/PillarCards.js` | Created | Pillar card UI + endpoint fetch + a11y |
| `web/app/app/sessions/[id]/page.js` | Modified | Mount pillars (Simple) / raw grid (Advanced) |

## Review-hardening pass (post-apply, applies to 36-01 + 36-02 code)
A code review surfaced 4 findings; all valid against the new code, all fixed:
- `api.py` `/sessions/{id}/ratings`: replaced `.single()` + bare-`except` with `.limit(1)` + data check (coaches + session), and removed the prior-sessions `try/except` — real DB failures now surface as 5xx instead of being masked as 403/404 or silently degrading the trend. (Older endpoints share the broad-except pattern; left unchanged — out of scope.)
- `tests/test_api.py`: added `test_backend_failure_surfaces_5xx`; updated `_ratings_admin` mock to the new query shape.
- `PillarCards.js`: `aria-expanded` + `aria-controls` on the toggle, `id` on the collapsible.

## Verification
- `pytest tests/` → **93 passed** (24 ratings + 6 api ratings cases incl. the failure test).
- Preview (local backend): cards render, `aria-expanded` toggles, controlled element appears, no console errors.

## Deviations from Plan
| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 1 | Review-hardening pass (4 findings) — quality, no scope creep |
| Verification method | 1 | Verified vs local backend instead of Railway (endpoint not deployed yet) — equivalent coverage |

## Next Phase Readiness
**Ready:** Web ratings UI complete + verified. iOS can mirror `RATINGS-SPEC.md` against the same endpoint in its own phase.
**Concerns:** Breaststroke band thresholds are DRAFT — coach review owed before customer-facing. All pillars read "provisional" until segmentation is validated (future 16-06).
**Blockers (for go-live, user-owned):** Deploy `api.py` to Railway (push to main → auto-deploy), then revert `web/.env.local` `NEXT_PUBLIC_API_URL` back to the Railway URL. Until then the cards only render against the local backend.

---
*Phase: 36-metric-ratings, Plan: 02*
*Completed: 2026-06-17*
