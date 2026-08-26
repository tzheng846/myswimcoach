---
phase: 75-report-card-phase-model
plan: 07
subsystem: ui
tags: [nextjs, react, race-phase, report-card, coach-chat, redirect]

requires:
  - phase: 75-05
    provides: the phases/ component set (PhaseReportCard, RangeStrip, HoverExplain, PhaseTimeline, PhaseVelocity, AlertSummary) + phaseBaseline/phaseValence libs
provides:
  - "/app/sessions/[id] rebuilt around the race-phase spine (classic analytics removed)"
  - "PhaseReportCard accepts a middleSlot + renders Swimming per-cycle + a legacy empty-state"
  - "CoachChat as a floating bottom-right blob"
  - "/app/sessions/[id]/phases → server redirect to the primary page"
affects: [75-08, 75-09, 75-06, ios-report-card]

tech-stack:
  added: []
  patterns:
    - "middleSlot: page-owned cards (velocity/Time-to-Distance/video) threaded into PhaseReportCard between the timeline and the phase sections"
    - "Redundant route → server-component redirect() (307 semantics, RSC-delivered in the streaming context)"

key-files:
  created:
    - .paul/phases/75-report-card-phase-model/75-07-SUMMARY.md
  modified:
    - web/app/app/sessions/[id]/page.js
    - web/app/app/sessions/[id]/phases/page.js
    - web/components/portal/phases/PhaseReportCard.js
    - web/components/portal/CoachChat.js

key-decisions:
  - "Coach-chat simple flag: dropped (defaults false = full coach depth) since the Simple/Advanced toggle that fed it was removed; audience is coaches"
  - "⋯ overflow holds only Delete; Export CSV (needs auth+blob) and Manage-videos (no route) weren't trivial — the + Add video affordance stays in the Videos card"
  - "Velocity stays the interim classic VelocityChart+AccelerationChart (un-regressed); the unified phase-tinted trace is 75-09"

patterns-established:
  - "PhaseReportCard is now the session-report body; legacy (no metrics_json.phases) shows an empty state while universal cards still render"

duration: ~26min
started: 2026-08-26T08:32:00-07:00
completed: 2026-08-26T08:58:45-07:00
---

# Phase 75 Plan 07: Report-Card Consolidation Summary

**The race-phase view is now the primary session report at `/app/sessions/[id]`: classic analytics
(SessionSummaryCard / PillarCards / MetricGrid / Simple-Advanced) removed, the phase spine is the body
with velocity / Time-to-Distance / video threaded through it, per-cycle line charts fill the Swimming
section, delete moved to a header ⋯ overflow, coach chat is a floating blob, and `/phases` redirects here.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~26 min |
| Started | 2026-08-26T08:32:00-07:00 |
| Completed | 2026-08-26T08:58:45-07:00 |
| Tasks | 2 auto + 1 human-verify checkpoint |
| Files modified | 4 (code) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Phase spine is primary body; classic analytics removed | Pass | PhaseReportCard is the body; SessionSummaryCard/PillarCards/MetricGrid + Simple/Advanced no longer imported or rendered; provenance chip + dropout strip preserved |
| AC-2: Header ⋯ overflow with Delete | Pass | window.confirm → DELETE /sessions/{id} → router.push to `/app/sessions?athlete=<id>`; star/name/prev-next intact |
| AC-3: Essentials threaded; legend removed | Pass | meta = `<stroke> · <duration>s` (no distance, no "vs last N"); video/Time-to-Distance/notes present; Swimming = CycleCharts (existing recharts line charts); standalone legend card gone |
| AC-4: Coach chat is a floating blob | Pass | Fixed bottom-right FAB (z-[80], above the hover scrim z-40 / popover z-[70]); Enter send, Esc/✕ close, focus-on-open; POST /coach/chat unchanged |
| AC-5: Route consolidation + legacy degrade | Pass | `/phases` = server redirect (`NEXT_REDIRECT /app/sessions/{id};307`); legacy (no phases) renders velocity/TtoD/per-cycle/video/notes + phase empty state |
| AC-6: Human verification | Pass | Approved by user (2026-08-26) |

## Verification Results

- `npm --prefix web run build` — **clean**: compiled in ~9s, TypeScript passed, all 19 pages generated (no new warnings).
- `/app/sessions/[id]/phases` → body contains `NEXT_REDIRECT` → `/app/sessions/demo-id;307;` (307-semantics redirect delivered via the RSC/streaming mechanism, per the Next 16 redirect guide).
- `/app/sessions/[id]` and `/app/sessions` SSR **200**; dev log reports **no server errors**.
- Visual/interactive review (behind the client-side Supabase auth gate) approved at the AC-6 human-verify checkpoint.

## Accomplishments

- First single-page merge of the phase model into the primary session report — the phase timeline is now the coach's single-session spine.
- `PhaseReportCard` gained a `middleSlot` seam so the page threads its own velocity/Time-to-Distance/video cards into the phase order without forking the phases/ visual language; also renders the Swimming per-cycle charts and a legacy empty-state.
- Coach chat lifted from an inline card to a session-scoped floating blob with correct z-order vs the hover-explain overlay.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Task 1 (page rebuild) + Task 2 (chat blob) | `040ce0d` | feat | merge report card into phase view (4 files) |

Docs/loop-closure: this SUMMARY + STATE/ROADMAP committed separately (`docs(75-07): …`).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/sessions/[id]/page.js` | Modified | Rebuilt around the phase spine; removed pillars/grid/summary/Simple-Advanced; added ⋯-delete + baseline fetch + middleSlot; trimmed meta; mounts CoachChat once |
| `web/components/portal/phases/PhaseReportCard.js` | Modified | Added middleSlot/cycles/session/unit props; removed legend + velocity hero; Swimming = CycleCharts; legacy empty-state |
| `web/components/portal/CoachChat.js` | Modified | Inline card → fixed bottom-right FAB + panel (send logic unchanged) |
| `web/app/app/sessions/[id]/phases/page.js` | Modified | Client data page → server-component redirect to `/app/sessions/[id]` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Coach-chat `simple` dropped (defaults false) | The Simple/Advanced toggle that fed it was removed; the report is coach-facing and detailed | Coach chat now uses full (non-simple) depth; no backend change |
| ⋯ menu = Delete only | Export CSV needs auth+blob handling (not trivial); no Manage-videos route exists; `+ Add video` stays in the Videos card | Matches the plan's "Delete is the required item; others only if trivial" |
| Velocity/TtoD/video wrapped in matching cards | Visual coherence with the phase sections; chart internals + interactivity untouched | Interim look is coherent; unified trace is 75-09 |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 (all pre-scoped to 75-08/75-09) | — |

**Total impact:** Executed as planned. The `/phases` redirect delivers 307 semantics via the RSC/streaming mechanism (200 doc + embedded `NEXT_REDIRECT …;307`) rather than a raw 307 header — this is the documented Next 16 behavior in a streaming context, not a deviation from intent.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Merged-surface visual review needs the coach-portal login (client-side auth gate) | Handed to the AC-6 human-verify checkpoint; build + redirect + SSR verified automatically |

## Next Phase Readiness

**Ready:**
- 75-08 (compare-vs-last-X slider + alert "N Changes" rebuild + `phaseBaseline` as a persisted pref + timeline hover dot+range strips) — the merged page + AlertSummary/PhaseTimeline/phaseBaseline seams are in place.
- 75-09 (unified interactive phase-tinted velocity trace) — the interim VelocityChart+AccelerationChart slot is isolated in `middleSlot`, ready to swap; still gated on the "new functionality" decision.
- 75-06 (Swim/Whole metric batch) composes at the Swimming/Whole sections independently.

**Concerns:**
- Server-side dismiss persistence, LLM headline, and imperial units on the phase strips remain 75-05 deferrals (client localStorage / metric-only for now).

**Blockers:** None. Phase 75 stays 🚧 (Swim/Whole metrics + 75-08/75-09 still owed).

---
*Phase: 75-report-card-phase-model, Plan: 07*
*Completed: 2026-08-26*
