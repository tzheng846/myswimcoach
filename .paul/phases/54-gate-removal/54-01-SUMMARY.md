---
phase: 54-gate-removal
plan: 01
subsystem: api
tags: [feature-flags, billing, tier-limits, ratings, thresholds, ios]

requires:
  - phase: 15-billing
    provides: "the tier-limit enforcement sites this plan gates"
  - phase: 36-metric-ratings
    provides: "ratings.py THRESHOLDS + the provisional/seg_reliable gating this plan unlocks"
provides:
  - "ENFORCE_TIER_LIMITS — one env kill switch, default OFF, covering all three tier limits"
  - "stroke unlock: breaststroke threshold fallback for every stroke + provisional no longer keyed to seg_reliable"
  - "mobile isAnalyticsReady = true"
affects: [51-02 athlete limit, Phase 53 pool day, team dashboard needs-attention, freestyle analytics]

tech-stack:
  added: []
  patterns:
    - "One module-level env kill switch, default off, skipping the guarded queries entirely rather than making them pass"
    - "Borrowed thresholds via `THRESHOLDS.get(stroke) or THRESHOLDS['breaststroke']` — fallback keeps 'borrowed' visible rather than copying keys"

key-files:
  created: []
  modified:
    - api.py
    - ratings.py
    - tests/test_api.py
    - tests/test_ratings.py
    - swimnetics-mobile/src/screens/ReportCardScreen.js

key-decisions:
  - "ONE switch (ENFORCE_TIER_LIMITS) superseding 51-02's planned ENFORCE_ATHLETE_LIMIT — not two switches on overlapping guards"
  - "Kill switch, not deletion and not DB-NULL — the Stripe webhook would repopulate NULLed columns"
  - "segmentation_reliable NOT flipped to default-True and NOT renamed — it is a provenance fact, not a reliability assessment"

patterns-established:
  - "Billing infrastructure stays intact behind the switch: _TIER_LIMITS, webhook writes, /billing/status all still work"

duration: "~1 session (2026-08-03) + device verification 2026-08-05"
started: 2026-08-03
completed: 2026-08-05
---

# Phase 54 Plan 01: Gate Removal Summary

**Every account-level restriction and the breaststroke-only analytics gate are off behind one reversible env switch — and the freestyle unlock finally reached a device build on 2026-08-05 via Phase 55-01.**

> **Reconciliation note.** Tasks were applied 2026-08-03 in a prior session; this SUMMARY was written 2026-08-05 from the APPLY record in STATE.md plus first-hand verification of the shipped state. The device half of the checkpoint was satisfied during Phase 55-01's EAS build.

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 + 1 human-verify checkpoint |
| Suite | 172 passed |
| Mobile | `npx expo export --platform ios` exit 0 (1075 modules, 3.2MB) |
| Shipped | backend half in `dedac17`; mobile half in Phase 55-01's build |

## Why this existed

The free-tier `device_limit`=1 blocked a live test on 2026-08-03. The user believed the limit had already been removed — what had actually been decided on 2026-07-30 was the *athlete* limit, a different limit, which had not landed either.

**The urgent second finding drove the scope:** free-tier `monthly_session_limit`=20 would have returned 402 **partway through the Phase-53 pool day** (10+ baseline trials plus warm-ups plus perturbation pairs ≈ 14-16 uploads). That would have wasted a collection session costing hardware, pool time and a swimmer.

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| Tier limits off by default, one switch | **Pass** | Default False; `ENFORCE_TIER_LIMITS=1` → True; `_TIER_LIMITS` byte-identical |
| Count queries skipped when off | **Pass** | Not merely made to pass — they do not run |
| Stroke unlock in ratings | **Pass** | Freestyle returns speed band=ok score=50 provisional=False; stroke_length band=good score=71 |
| Freestyle analytics on device | **Pass** | Verified 2026-08-05 on the Phase 55-01 EAS build |
| Billing infrastructure preserved | **Pass** | `_TIER_LIMITS`, Stripe webhook writes, `/billing/status`, schema columns all intact |

## Accomplishments

- **One switch, not two.** `ENFORCE_TIER_LIMITS` at `api.py:34` gates all three limit sites; when off the count queries never run. This deliberately **superseded** 51-02's planned `ENFORCE_ATHLETE_LIMIT` — 51-02's Task 2 was struck at apply time rather than double-gating the same block.
- **Made the stroke unlock actually visible.** The "thresholds only" option would have been a **no-op**: `provisional` stays True via the `seg_reliable` condition, which is False for every auto-segmented session. Dropping that condition is what makes the unlock real.
- **Kept every gate one line from restoration.** `seg_reliable` param and read retained in `ratings.py`; the mobile `!isAnalyticsReady` "Coming Soon" branch and all 6 usage sites retained.

## Deviations from Plan

**1. A third contradicted assertion existed beyond the two the plan named.** `tests/test_api.py:878` asserted `speed["provisional"] is True  # segmentation unreliable`. Inverted to False, not deleted. Missed at plan time because the grep for `segmentation_reliable` surfaced only that file's fixture setup lines, not the assertion.

**2. `depends_on` relaxed to `[]`.** 51-02 had not landed at apply time (`grep ENFORCE_ api.py` = 0 hits), so the dependency was dropped. The action this created — "drop 51-02's athlete-limit task before applying it" — was correctly executed when 51-02 ran on 2026-08-05.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Env kill switch, not deletion, not DB-NULL | The Stripe webhook would repopulate NULLed columns | Reversible with one Railway env var, no code change |
| `segmentation_reliable` NOT flipped or renamed | It is a **provenance fact** (`metrics.py:617` = `bool(manual_bounds)`, "did a human draw these?"), not a reliability assessment. Flipping it would record something false and destroy the marker distinguishing Phase 53's hand-annotated sessions from auto ones | Now inert metadata — nothing reads it after T2. Rename to `segmentation_source: "auto"｜"human"` deferred to Phase 53, the consumer that will define the vocabulary |

## ⚠ Accepted Consequence (user informed, chose it anyway)

Dropping `(not seg_reliable)` from `provisional` also **un-gates `summarize_team`**. The team dashboard needs-attention list — **inert since Phase 37** — now populates, driven by **breaststroke-derived bands applied to all strokes over segmentation flagged unreliable** (16-04: 3/8 breaststroke sessions within ±5 SPM).

This plan only makes those bands visible. **Phase 53 decides whether they should exist at all** — its within-athlete-contrast reframe needs no absolute thresholds.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Backend half could not be committed separately from 51-02 | `ratings.py` + `tests/test_ratings.py` rode along in `dedac17`; disclosed to the user before they committed |
| Mobile half sat uncommitted and unbuilt for two days, so freestyle still appeared blocked on the phone even after the backend shipped | Diagnosed during Phase 55 discussion; folded into 55-01 and verified on that build |

## Next Phase Readiness

**Ready:**
- The Phase-53 pool day can no longer 402 partway through — the original trigger for this phase.
- Freestyle analytics render end-to-end.

**Concerns:**
- The needs-attention list now shows verdicts built on borrowed, unvalidated thresholds. This is known and accepted, but it means the team dashboard is now *confidently wrong* in a way it previously was not — it was silent before. Phase 53 is the resolution.
- Turning enforcement back on is a real behavior change, not a no-op: after 51-02 the athlete count query actually works, so that guard is armed for the first time.

**Blockers:** None.

---
*Phase: 54-gate-removal, Plan: 01*
*Applied: 2026-08-03 · Device-verified: 2026-08-05 · Summary written: 2026-08-05*
