---
phase: 32-coach-outreach-research
plan: 01
subsystem: marketing
tags: [go-to-market, coach-outreach, socal, research, swim-clubs, lead-list]

requires: []
provides:
  - marketing/socal-coach-outreach.md (target-club qualities rubric + scored SoCal club shortlist + social presence + media-presence coach list)
  - prioritized interest-only outreach targets (A/B/C tiers) across LA/OC/SD-Imperial/Inland Empire
affects: [future cold-email phase (reuse marketing/sales-pitch-email.md), business-model traction work]

tech-stack:
  added: []
  patterns: [web-research → evidence-backed marketing doc with verified-vs-unverified flagging]

key-files:
  created: [marketing/socal-coach-outreach.md]
  modified: []

key-decisions:
  - "Interest-only outreach, not selling (user 2026-06-16)"
  - "Geo: all greater SoCal weighted evenly, not San Diego-centric (user 2026-06-16)"
  - "Deliverable: research + qualities rubric only, no email copy this phase (user 2026-06-16)"
  - "Mid-sized clubs rank ABOVE mega-clubs for a first interest email (accessible decision-maker > prestige)"
  - "Mid-execution scope adds (user follow-ups): Part C social presence, Part D media-presence coaches"

patterns-established:
  - "Flag every unverified coach name / contact path explicitly; never fabricate emails"
  - "Active social account = double signal (tech-openness #3 + reachability #7)"

duration: ~1 session (single sitting)
started: 2026-06-16
completed: 2026-06-16
---

# Phase 32 Plan 01: SoCal Coach Outreach Research — Summary

**Shipped `marketing/socal-coach-outreach.md`: a weighted "ideal target club" qualities rubric + a
scored shortlist of 16 real greater-SoCal swim clubs, plus (added mid-execution) a club social-presence
table and a list of media-presence individual coaches (Dave Salo–type) for interest-only outreach.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 session |
| Started | 2026-06-16 |
| Completed | 2026-06-16 |
| Tasks | 2 planned, completed + 2 scope-add sections |
| Files modified | 1 created (marketing/socal-coach-outreach.md) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Qualities rubric explicit + weighted, includes 3 user seeds | Pass | Part A — 8 criteria, each with rationale + observable signal + weight; mid-sized/national-group/open-to-tech all present; A/B/C scoring method defined |
| AC-2: ≥12 real named clubs, scored + evidence-backed, region-balanced | Pass | Part B — 16 clubs: OC 4 / LA 4 / SD-Imperial 3 (+room) / Inland Empire 4; each tiered with coach, contact path, why-reach-out |
| AC-3: Honesty about gaps | Pass | Unverified coach names/contacts flagged throughout; "verify before sending" checklist + "how to prioritize" note included |

## Accomplishments

- **Qualities rubric (Part A)** — 8 weighted signals; key insight baked in: mega-clubs (400–600+)
  score *lower* on accessibility, so a mid-sized performance club beats a powerhouse for a first
  interest email.
- **Scored shortlist (Part B)** — 16 real clubs, region-balanced, A/B/C-tiered. Verified coaches:
  North Coast Aquatics = Jeff Pease (coach-owned), Rancho San Dieguito = Joe Benjamin (national-group
  lead), Seaport = Paul Folts. A-tier leads: OC Gold, South OC, Rose Bowl, North Coast, RSD.
- **Social presence (Part C, scope add)** — IG/FB handles for ~10 shortlist clubs with approximate
  reach; strongest: Rose Bowl (~2.9k), North Coast (~1.4k/868 posts), Circle City (~850/950 posts).
- **Media-presence coaches (Part D, scope add)** — the "Dave Salo–type" list the user actually wanted:
  **Dave Salo (returning to Irvine Novaquatics 2026)** and **Mark Schubert (The Swim Team, Lake Forest;
  video-analysis clinic)** as SoCal bullseyes; Gary Hall Sr. (The Race Club) as best out-of-region
  biomechanics sounding board; Brett Hawke flagged for reach BUT Enhanced Games reputational caution.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `marketing/socal-coach-outreach.md` | Created | Parts A–D: rubric, club shortlist, social presence, media-presence coaches + verify checklist + sources |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Interest-only, not selling | User intent 2026-06-16 | Targeting prioritizes accessible/receptive coaches over highest-budget buyers |
| All greater SoCal, even weighting | User 2026-06-16 | Shortlist balanced across 4 sub-regions, not SD-centric |
| Research + rubric only, no email copy | User 2026-06-16 | Email deferred; reuse marketing/sales-pitch-email.md when wanted |
| Mid-sized > mega-club for first touch | Accessible decision-maker predicts a reply | NOVA/MVN/Canyons → B tier despite prestige |
| Added Parts C + D mid-execution | User follow-ups ("social presence", "media-presence coaches") | Doc scope grew beyond the 2 planned tasks; both delivered |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 2 | Part C (social presence) + Part D (media-presence coaches), both user-requested mid-execution; net positive, on-theme |
| Deferred | 1 | Email copy intentionally out of scope (user decision), not a gap |

**Total impact:** Scope grew on-theme per user follow-ups; no scope creep against intent.

### Deferred Items

- Cold-email copy — explicitly out of scope this phase (user). Reuse `marketing/sales-pitch-email.md`.
- 1–2 additional San Diego/SI clubs to fully even SD coverage with OC/LA — noted as a "+room" gap in Part B.
- Not-surfaced social accounts (Swim South Bay, Redlands, Industry Hills, Seaport, Riverside Aquatics) — flagged to check directly.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| swimstandards.com SI club page returned HTTP 403 to WebFetch | Pivoted to WebSearch + gomotion/SwimCloud sources; still got NCA + RSD + Seaport with verified coaches |
| Most clubs expose only a web form / generic info@, not a personal coach email | Recorded contact *path* (coaching-staff page) and flagged "verify before sending"; did not fabricate addresses |

## Next Phase Readiness

**Ready:**
- Actionable target list — A-tier clubs + Salo/Schubert as media-presence leads — ready for an interest-email phase.
- `marketing/sales-pitch-email.md` exists as the base if a cold-email phase is opened next.

**Concerns:**
- Coach names/contacts are point-in-time; turnover is common — the verify-before-sending checklist must be run per club before any real send.
- "Open to new tech" signal is mostly unverified from the outside — the biggest A/B swing.

**Blockers:** None.

---
*Phase: 32-coach-outreach-research, Plan: 01*
*Completed: 2026-06-16*
