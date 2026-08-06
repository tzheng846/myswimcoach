# 36-01 SUMMARY — Backend Metric Ratings

**Loop:** PLAN → APPLY ✅ (autonomous, no checkpoint) — ready for UNIFY.
**Plan:** [36-01-PLAN.md](36-01-PLAN.md) · **Spec:** [RATINGS-SPEC.md](RATINGS-SPEC.md)

## Shipped
- **`ratings.py`** (pure, no I/O) — the shared source of truth:
  - 4 pillars: Speed, Stroke length, Consistency, Endurance. `PILLARS` table (primary metric +
    contributing metrics + explanation copy); kick metrics excluded.
  - `RATING_COLORS = {good:#2d9e5f, ok:#d4860a, needs_work:#c0392b}` (shipped Phase-2 trio).
  - `THRESHOLDS["breaststroke"]` with worst/ok/good/best anchors (DRAFT, seeded from app.py:56).
  - `rate_session(metrics, baseline=None, stroke="breaststroke")` → `{stroke, has_baseline,
    rating_colors, pillars:[{band, score(0–100), trend, provisional, explanation, primary,
    metrics}]}`. Band from primary vs thresholds; `score` piecewise-linear (higher always = better,
    inverted for lower-is-better); trend direction-aware ±5% deadband (`first_session` w/o baseline);
    provisional when `segmentation_reliable=False` or non-breaststroke; NaN/missing-safe.
  - `select_baseline(prior_sessions, mode="previous")` — pluggable; `"previous"`/`"first"`/
    `"recent_avg"` all implemented so the future coach-chosen comparison scope is a caller-only change.
- **`GET /sessions/{id}/ratings`** in api.py — auth + ownership (coach_id filter); loads the session
  (session metrics ⊕ data_quality flattened), picks the athlete's previous same-stroke session as
  baseline, returns the pillar payload. 401 unauth / 404 foreign-or-missing / 403 no coach profile.
- **`RATINGS-SPEC.md`** — the contract (pillars, thresholds+anchors, verdict rules, gating, payload,
  visual system) that 36-02 (web) and the later iOS phase implement from.

## Verification
- `tests/test_ratings.py` (24 cases) + `tests/test_api.py` TestSessionRatings (5 cases).
- Full suite: **92 passed** (was 64). No new dependency. `/process`, metrics.py compute, and clients untouched.

## Deviations from plan (intentional, APPLY-time)
- Consistency band is driven by **`cv_arm_peak_vel` alone** (the Phase-2 validated metric); `cv_isi`
  is shown as context with **no band** — ISI CV has no validated threshold (observed 0.2–0.5), so a
  shared "worst-of" band would have been an invented threshold. Honest over precise; revisit when ISI
  thresholds are validated.
- `select_baseline` "first"/"recent_avg" fully implemented (plan said stub) — cheap, makes the scope
  feature genuinely pluggable now.

## Open / owed
- **Thresholds are DRAFT, breaststroke only** — coach review owed before customer-facing (like drills.py).
- Non-breaststroke = trend-only + provisional until thresholds validated (ties to future 16-06).
- `segmentation_reliable` is always False today → every pillar reads "provisional"; flips automatically
  when 16-06 validates segmentation.

## Next
- **36-02 (web):** pillar cards (fixed red/amber/green band + marker at `score`, verdict word, trend
  chip, expand → contributing metrics + explanation, provisional chip) on the session report card,
  reading `GET /sessions/{id}/ratings`; raw grid demoted to advanced. Human-verify checkpoint.
- **iOS (later phase):** mirror RATINGS-SPEC.md against the same endpoint.
- Deploy: api.py change → Railway auto-deploys on push to main (user-owned).
