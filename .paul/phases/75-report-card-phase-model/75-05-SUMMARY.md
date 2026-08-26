---
phase: 75-report-card-phase-model
plan: 05
subsystem: web
tags: [report-card, phases-ui, valence, baseline, nextjs, coach-portal, react]

requires:
  - phase: 75-01
    provides: metrics_json.phases object (schema_version 2) + boundaries
  - phase: 75-02
    provides: underwater window metrics + underwater_start_s boundary
  - phase: 75-03
    provides: 7 underwater kick metrics + detect_swim_boundaries (stroke_start/finish)
  - phase: 75-04
    provides: 10 Start-phase metrics + go_signal_s
provides:
  - /app/sessions/[id]/phases route (coach-facing race-phase report card)
  - phaseBaseline.js (last-5 same-stroke median±1.5·sMAD band) + phaseValence.js (DIRECTION_OF_GOOD)
  - phases/ component set (RangeStrip, HoverExplain, PhaseTimeline, PhaseVelocity, AlertSummary, PhaseReportCard)
affects: [ios-report-card, 75-swim-whole-batches]

tech-stack:
  added: []
  patterns:
    - "Read-only frontend: consumes stored metrics_json.phases via supabase-js (reads bypass FastAPI)"
    - "Pure engines (phaseBaseline/phaseValence) + presentational components on portal Tailwind tokens"
    - "Direction-of-good VALENCE coloring — the one place the tool asserts good/bad, still no absolute thresholds"

key-files:
  created:
    - web/lib/phaseBaseline.js
    - web/lib/phaseValence.js
    - web/components/portal/phases/RangeStrip.js
    - web/components/portal/phases/HoverExplain.js
    - web/components/portal/phases/PhaseVelocity.js
    - web/components/portal/phases/PhaseTimeline.js
    - web/components/portal/phases/AlertSummary.js
    - web/components/portal/phases/PhaseReportCard.js
    - web/app/app/sessions/[id]/phases/page.js
    - .claude/launch.json
  modified:
    - web/app/globals.css
    - web/app/app/sessions/[id]/page.js
    - web/components/portal/phases/HoverExplain.js

key-decisions:
  - "DIRECTION_OF_GOOD valence coloring is a deliberate, user-approved (2026-08-25) evolution of the old no-valence rule — direction-of-CHANGE coloring, NOT an absolute/normative threshold"
  - "Dismiss state is client-only (localStorage[phaseDismiss:<id>]) this slice; server persistence deferred"
  - "Strip domains are data-driven (0-based floor + headroom around value/band/median), NOT the mockup's synthetic constants — a real swim never clips off-scale"
  - "Phase insets = the phase's velocity slice (line-only, 0-based) via PhaseVelocity, not a dedicated per-kick/split chart"
  - "pulldown_* skipped unless breaststroke; reaction_time/streamline_drag show degraded pills, never a fake zero strip"

patterns-established:
  - "Report-card display doctrine: within-athlete contrast (median±1.5·sMAD of last 5), no absolute thresholds, valence only where direction-of-good is established"

duration: ~1h
started: 2026-08-25
completed: 2026-08-25
---

# Phase 75 Plan 05: Race-Phase Report-Card UI Summary

**The first visible surface for the race-phase model: a new `/app/sessions/[id]/phases` coach-portal route that renders the stored `metrics_json.phases` (Start + Underwater implemented) in the v3 visual language — a deterministic valence-broken-down alert line, a distance/time phase timeline, a phase-tinted velocity line, and per-phase 1D usual-range strips colored by direction-of-good, with every description + comparison on a page-dimming hover overlay. Baseline = the athlete's last 5 same-stroke swims (median ± 1.5·sMAD). Additive + isolated; the existing report card is untouched beyond one nav link.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 h (this session; Task 1 + 3 of 4 Task-2 primitives pre-existed uncommitted) |
| Completed | 2026-08-25 |
| Tasks | 3 auto + 1 human-verify — all complete |
| Files created | 9 (+ launch.json) |
| Files modified | 3 |
| Build | `npm run build` clean (compile + TypeScript + 19 pages); /phases serves 200 in dev, no console errors |
| Engine checks | 18/18 scratch assertions pass |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: baseline engine — last-5 same-stroke, robust band, n<2→null | Pass | Scratch: n=3 median/MAD/sMAD/band exact; 1-elem→band:null,n:1; nulls skipped |
| AC-2: valence engine — deterministic flag + direction-of-good | Pass | Scratch: up+above→good, up+below→bad, down+above→bad, neutral→neutral, in-band→not flagged, missing key→neutral |
| AC-3: /phases renders the v3 visual language | Pass | Human-verify approved (legend, alert line, timeline, bottom-pinned 0-based velocity, chart-on-top + 2-col strips, hover overlay) |
| AC-4: coach control + empty/degraded states | Pass | Human-verify approved (dismiss decrements + persists on reload; baseline-building; not-measured pills) |
| AC-5: visual verification checkpoint | Pass | Approved 2026-08-25 |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/phaseBaseline.js` | Created (prior) | `reducePhaseBaseline` (pure) + `fetchPhaseBaseline` — last-5 same-stroke median±1.5·sMAD band |
| `web/lib/phaseValence.js` | Created (prior) | `DIRECTION_OF_GOOD` map + `flagVerdict`/`statusWord` (pure) |
| `web/components/portal/phases/RangeStrip.js` | Created (prior) | One metric row: 1D usual-range strip, 3 states (full / baseline-building / not-measured) |
| `web/components/portal/phases/HoverExplain.js` | Created (prior) + modified | Page-dimming hover-explain overlay; added a `style` passthrough to `ExplainTrigger` |
| `web/components/portal/phases/PhaseVelocity.js` | Created (prior) | Line-only velocity SVG; `hero` (phase tints, bottom-pinned labels) + `inset` (window slice) |
| `web/components/portal/phases/PhaseTimeline.js` | Created | Segmented phase bar, distance/time toggle, Surfaced divider, hot-phase attention outline + hover payload |
| `web/components/portal/phases/AlertSummary.js` | Created | Deterministic count + valence chips (N worse / N changed / N better) + bulk restore |
| `web/components/portal/phases/PhaseReportCard.js` | Created | Assembly: DISPLAY map, dismiss state (localStorage), row model, legend + alert + timeline + velocity + sections + coming-soon |
| `web/app/app/sessions/[id]/phases/page.js` | Created | The route — supabase-js fetch (profiles + phases) + baseline, renders PhaseReportCard |
| `web/app/globals.css` | Modified (prior) | `--color-good/bad/neutral/usual` valence tokens (portal dark values) |
| `web/app/app/sessions/[id]/page.js` | Modified | One "Race phases ›" nav link beside "Annotate ›" (only change) |
| `.claude/launch.json` | Created | Dev-server config (`npm --prefix web run dev`, port 3000) for the human-verify preview |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Valence coloring is a deliberate evolution of the no-valence rule** | User-approved 2026-08-25. `DIRECTION_OF_GOOD` colors direction-of-CHANGE against a metric's established direction of good — it is NOT an absolute/age/national threshold. A flag still only means "outside HIS own usual range." | `DIRECTION_OF_GOOD` (phaseValence.js) is the single reviewable place the tool asserts good/bad; grey "changed" wherever "better" is a coaching call. **Do not "correct" this back to no-valence.** |
| Dismiss state client-only (localStorage) | Keeps 75-05 read-only against the FastAPI (no new endpoint). The count is still "the coach's" — it just lives in the browser for now. | Server persistence (a `dismissed` set in `metrics_json.phases` or a column via a small PATCH) is a documented follow-up. |
| Data-driven strip domains | The mockup's per-metric `domain:[0,X]` were hand-tuned to synthetic Leo data; a real athlete's value could exceed X and clip at the strip edge. | `computeDomain(value, base)` anchors magnitudes at 0 with headroom around value/band/median; signed metrics (Kick fade %) span below 0. Every magnitude scale still starts at 0. |
| Phase insets = velocity slice, line-only | Per-kick velocities and 5-m split arrays aren't in the stored `phases` data; PhaseVelocity's `inset` variant draws the phase window's velocity (its bumps ARE the kicks). | Dive line + underwater "kick line" ship now; the dedicated per-kick dot chart / split line stay deferred with the rest of Swim (matches the plan's "signal insets stay minimal"). |
| `pulldown_*` skipped on non-breaststroke | Registry gates pulldown to breaststroke; freestyle rows would be null. | Non-breast omits the two pulldown rows entirely; `reaction_time`→"needs coach GO signal", `streamline_drag`→"planned" (degraded pills, never a fake zero strip). |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 2 | Both minor / in-scope (see below) |
| Deferred | 0 (beyond the plan's own scope limits) | — |

- **`style` passthrough on `ExplainTrigger`** — a one-line generalization of a file this plan owns, so a whole timeline segment can be a hover trigger with its own `flex-grow`. In-scope (not an existing component).
- **`.claude/launch.json`** — incidental dev-server config for the preview, not a plan artifact.
- Fidelity calls (data-driven domains; velocity-slice insets) are recorded above under Decisions; both honor the plan's doctrine (0-based, line-only, no thresholds) rather than copying synthetic constants.

## Prior-session work verified (not assumed)

Task 1 (both engines), 3 of 4 Task-2 primitives (RangeStrip, HoverExplain, PhaseVelocity), and the globals.css valence tokens existed **uncommitted** at session start. Rather than trust them, the engines were re-verified with the plan's scratch checks (18/18 pass) and every primitive was read and exercised through the clean build + the assembled route.

## Issues Encountered

None. Build clean on the first full run.

## Next Phase Readiness

**Ready:**
- The race-phase model is now visible to coaches for the **Start + Underwater** phases.
- The row model + DISPLAY map are the seam for the remaining **Swim (9)** and **Whole (4)** metric batches (STATE item 7) — those metrics currently render as "coming soon" panels and `DIRECTION_OF_GOOD` already pre-fills their valence.
- iOS report card can mirror `phaseBaseline`/`phaseValence` (pure) when it ships.

**Concerns / owed:**
- **Server-side dismiss persistence** deferred (client localStorage this slice).
- **LLM plain-language headline** deferred — the alert line is a deterministic count only.
- **Imperial units + iOS** deferred — metric-only, web-first.
- Depends on the stored library being backfilled (STATE item 6, applied 2026-08-21) so `phases` is populated; a session predating the phase model shows the friendly "no race-phase breakdown yet" empty state.

**Blockers:** None.

---
*Phase: 75-report-card-phase-model, Plan: 05*
*Completed: 2026-08-25*
