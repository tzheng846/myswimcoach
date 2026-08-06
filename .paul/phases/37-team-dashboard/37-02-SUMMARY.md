---
phase: 37-team-dashboard
plan: 02
subsystem: web
tags: [dashboard, portal, ratings, team, ui]
requires: [37-01]
provides:
  - team-health coach dashboard (4 sections) consuming GET /team/overview
  - TeamPulse / NeedsAttention / RecentActivity / RosterBandCard portal components
affects:
  - 50-01/50-02 (the demo seeder exists to fill exactly these four sections with history)
  - future iOS team-dashboard phase (already mirrored on iOS via Phase 38-02)
tech-stack:
  added: []
  patterns: ["one endpoint fetch powers the whole page", "band colors come from the payload
    (rating_colors), never hardcoded in the component"]
key-files:
  created: [web/components/portal/TeamPulse.js, web/components/portal/NeedsAttention.js,
    web/components/portal/RecentActivity.js, web/components/portal/RosterBandCard.js]
  modified: [web/app/app/page.js]
key-decisions:
  - "Single /team/overview call rather than N per-athlete rating calls"
  - "Bands stay Python-computed (Phase-36 source of truth); the UI only renders them"
  - "Dashboard kept on the portal's dark theme — the Phase-40 light redesign was marketing-only"
duration: unknown (retroactive summary)
completed: 2026-06-18 (recorded 2026-07-30)
---

# Phase 37 Plan 02: Team Dashboard Web UI Summary

**Rebuilt the coach dashboard from a raw-numbers athlete list into a team-health home: team pulse,
needs-attention, recent activity, and a color-banded roster grid — all from one `/team/overview`
fetch.**

> ⚠ **This is a retroactive summary.** The work shipped 2026-06-18 as commit `62a6f4f` and has been
> live on Vercel since, but no SUMMARY was written and both STATE and ROADMAP carried it as "plan
> awaiting approval" for ~6 weeks. Details below are reconstructed from the commit and the current
> source, not from a live apply session.

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| One /team/overview fetch powers the whole dashboard | ✅ PASS | `web/app/app/page.js` — single `apiFetch("/team/overview")` in one effect; all four sections read from that payload |
| Four sections render with payload-driven colors + empty states | ✅ PASS | All four components present; `data.rating_colors` passed down; `athlete_count === 0` renders the "add your roster" empty state |
| Build green; no backend/other-page changes; no new dependency | ✅ PASS | Commit touches 5 files, all under `web/`; package.json untouched |
| Coach confirms the dashboard visually | ❓ **UNKNOWN** | No checkpoint record exists. Worth a look next time you open the portal |

## Accomplishments
- **web/app/app/page.js** — rewritten (70 lines changed) to a loading/error/empty tri-state around
  the four sections.
- **TeamPulse.js** (61 lines) — athlete/tested counts + per-pillar band-distribution chips.
- **NeedsAttention.js** (50 lines) — athletes flagged needs-work / declined / stale / never-tested.
- **RecentActivity.js** (40 lines) — newest sessions team-wide.
- **RosterBandCard.js** (67 lines) — per-athlete 4-pillar band dots replacing raw numbers.

## Verification
- Committed as `62a6f4f` "Add team dashboard UI", on origin/main, auto-deployed to Vercel.
- Source inspection confirms the payload contract locked in 37-01 is what the page consumes.
- No retroactive build/preview run — the code has been live in production for six weeks, which is
  stronger evidence than a local build would be.

## ⚠ Important finding
This is the **third** instance found in one sweep of finished work that never closed its loop
(alongside 48-01 unpushed and 45-01 unrecorded). The dashboard being marked "awaiting approval"
directly distorted Phase-50 planning, which was scoped around an empty portal that had in fact
already been built.

## Deviations from Plan
Unknown — no apply-time record. Nothing in the source contradicts the plan.

## Next Phase Readiness
**Phase 37 is now complete (2/2 plans).** The dashboard is built and live but renders near-empty
for lack of history — which is precisely what Phase 50's seeder exists to fix. The iOS mirror
already shipped separately via Phase 38-02.

---
*Phase: 37-team-dashboard, Plan: 02*
*Shipped: 2026-06-18 · Summary written retroactively: 2026-07-30*
