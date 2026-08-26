---
phase: 75-report-card-phase-model
plan: 07
topic: Report-Card Consolidation — make the race-phase view the PRIMARY session report, absorbing the classic report card's essentials
created: 2026-08-26
source: /paul:discuss (2026-08-26), user-driven; iterated against a rendered mockup
mockup: scratch/report-card-merged-mockup.html · artifact https://claude.ai/code/artifact/9562c55b-2d10-4374-9648-1e1447cd7684
status: Vision settled + mockup approved through rev 2; ready for /paul:plan 75-07
---

# Phase 75 Plan 07 — Context: Report-Card Consolidation (the merge)

## Goal

**Replace the classic session report card at `/app/sessions/[id]` with the race-phase model** (built as the
additive `/phases` route in 75-05), folding the report card's still-essential pieces back into it. One page,
race-phase-spine, with the coach's day-to-day tools threaded through it. This is the surface commitment the
75-05 SUMMARY and CONTEXT-ui-consolidation deferred: 75-05 shipped the phase view *beside* the report card;
75-07 makes it *the* report card.

**Scope note vs 75-06:** `75-06-DISCOVERY.md` owns the Swim+Whole *metric* batch (filling the "coming soon"
panels). 75-07 is the *consolidation* — independent of 75-06; they compose at the Swimming/Whole sections
(75-06 adds registry strips; 75-07 fills Swimming with per-cycle charts and keeps Whole as coming-soon).
Either can ship first.

## Locked decisions (AskUserQuestion, 2026-08-25)

1. **Analytics body → replaced entirely.** Phase strips become the single-session anatomy. Remove
   `SessionSummaryCard`, `PillarCards`, `MetricGrid`, and the **Simple/Advanced toggle** from the session page.
   Pillars relocate to the roster/athlete-over-time surface later (per CONTEXT-ui-consolidation) — **stop
   rendering, don't delete** the components (verify no other caller before dropping imports).
2. **Per-cycle breakdown → inside the Swimming phase section** (replaces the "Swimming — coming soon" panel).
3. **Delete → header ⋯ overflow menu** (keeps the `window.confirm` guard). Delete is currently list-only.
4. **Velocity trace → one unified hero.** Merge the phase-tinted line (`PhaseVelocity`) with the interactive
   `VelocityChart` + `AccelerationChart`: phase-tinted AND cursor-scrub, cycle overlays, accel toggle, m/yd,
   and a `◆` marker synced to Time-to-Distance. This is where the (still-undefined) "new functionality" lands.

## Rev-2 refinements (mockup iteration, 2026-08-26)

1. **Drop redundant distance** from the identity meta (implicit in the event) → `25 m Freestyle · 15.8 s`.
   Also drop "vs his last N swims" from the meta — it moves to the compare slider (#3).
2. **Remove the legend card entirely** (the "his usual range / this swim / better / worse / changed / hover
   dotted" teaching strip). The dotted-underline affordance + chips carry it implicitly.
3. **Alert card rebuilt:** a big **"N Changes"** count + valence **color-tag chips** (N worse / N changed /
   N better). Remove the "N metrics differ from his usual…" sentence and the "× each to dismiss" hint (row-level
   × dismiss stays). **Add a "Compare vs last X swims" slider** in the same card — **X = the baseline window
   (2–8, default 5), persistent across sessions** (localStorage, like the view/unit prefs). Changing X refetches
   the baseline and recomputes flags live.
4. **"Race phases" card:** drop the "start → finish" subtitle.
5. **Underwater timeline hover:** the phase-segment hover must show a **labeled dot+range mini-strip per metric**
   (`today 1.30 m · usual 1.42–1.70 m`, today-dot valence-colored) — the bare "1.30m vs 1.55m" made it unclear
   which number was the current swim.
6. **Swimming per-cycle charts → line charts** (points + trend line + mean), not bars.

## Layout / information architecture (top → bottom)

Header (‹ Sessions · prev/next · ★ · ⋯[Delete]) → editable name + meta + Annotate › + annotation-provenance
chip → **Alert card (N Changes + chips + compare slider)** → Race-phases timeline (by dist/time) →
**Unified velocity hero** → Time-to-Distance → Video overlay (unchanged) → Dive/Push-off (inset + strips) →
Underwater (inset + strips) → **Swimming = per-cycle line charts** → Whole race (coming soon) → Notes.
**Coach chat = floating blob, bottom-right** (standard AI chat UI, session-grounded).

## Baked-in assumptions (user did not object)

- **Coach chat is this-session-page only** (session-grounded), not app-wide.
- **Legacy sessions (no `metrics_json.phases`):** the universal elements (unified trace, Time-to-Distance,
  per-cycle, video, notes, header) still render; the phase strips/timeline/alert show the existing
  "no race-phase breakdown yet" empty state. Most stored sessions were backfilled 2026-08-21 (STATE #6).
- **Web-first, dark-only** (portal is dark by design); the **m/yd toggle returns** on the unified trace.
  iOS mirrors later.
- **Preserve** the "recomputed from annotation" provenance chip and the dropout-warning strip from the
  classic card.

## Key seams / files for the plan

| File | Change |
|------|--------|
| `web/app/app/sessions/[id]/page.js` | The big rebuild — reframe around the phase spine; remove pillars/grid/summary/Simple-Advanced; add ⋯-delete; drop legend; trim meta |
| `web/app/app/sessions/[id]/phases/page.js` | Redundant once merged — redirect → `/sessions/[id]`, or remove |
| `web/components/portal/phases/PhaseReportCard.js` | Becomes the session-page body; remove the legend block; wire in the non-phase cards; Swimming section hosts per-cycle |
| `web/components/portal/phases/AlertSummary.js` | Rebuild to "N Changes" + chips + the **compare slider** (new); the slider must not be destroyed on re-render (static node + one listener) |
| `web/components/portal/phases/PhaseTimeline.js` | Hover payload → dot+range mini-strips (rev-2 #5) |
| `web/components/portal/phases/PhaseVelocity.js` + `VelocityChart.js` + `AccelerationChart.js` | **Unify** — highest build risk. Likely bring phase tint + bottom phase labels + Surfaced marker + the TtoD `◆` marker INTO the interactive `VelocityChart` (keep cursor/cycles), retire the static hero variant. Resolve the "new functionality" first |
| `web/lib/phaseBaseline.js` | `BASELINE_LIMIT` const → a **user pref N (2–8, default 5, persisted)**; `fetchPhaseBaseline` takes N; changing N refetches + recomputes |
| `web/components/portal/CycleCharts.js` | Move into the Swimming section; convert to **line charts** |
| `web/components/portal/CoachChat.js` | Reposition/restyle to a fixed bottom-right FAB + panel (was inline) |
| `web/components/portal/{VideoTracePanel,TimeToX}.js` | Reused as-is (video overlay is "perfect — don't change") |

## Open questions for /paul:plan 75-07

1. **⭐ Velocity "new functionality" (blocks the trace build).** Undefined. Candidates floated: brush-to-zoom a
   phase · overlay his usual-band envelope on the trace · click a phase band → jump to its section · ghost a
   second swim underneath. Resolve before building the unified trace.
2. **Unified-trace implementation seam.** Extend `VelocityChart` (interactive, cycle-coupled) with phase tint +
   phase labels + Surfaced + TtoD marker, and retire `PhaseVelocity`'s hero variant? Or make `PhaseVelocity`
   interactive? (Recommend the former — VelocityChart already has cursor + cycles + marker sync.)
3. **Compare slider = live baseline refetch**, not just a relabel — confirm it refetches `fetchPhaseBaseline(…, N)`
   and recomputes flags; persist N; range 2–8 / default 5; scope to the phase strips (does NOT touch `ratings.py`).
4. **Pillars relocation:** confirm `PillarCards`/`MetricGrid`/`SessionSummaryCard` have no other caller before
   removing imports (relocation to the roster surface is a separate future phase, not this plan).
5. **Coach-chat blob** interaction details (z-index over the hover-explain scrim; open/close; unread cue).
6. **Delete** wiring on the report page (`apiFetch DELETE /sessions/:id` + confirm + redirect to the athlete's
   session list) — endpoint exists; only the UI is new here.

## Approach / constraints

- Reuse the shipped `phases/` component set and doctrine (within-athlete contrast, median ± 1.5·sMAD,
  no absolute thresholds, valence via `DIRECTION_OF_GOOD`).
- Reads bypass the API (supabase-js); writes via `apiFetch` (PATCH/DELETE).
- Portal dark tokens (`web/app/globals.css`); no new type system.
- This is **more destructive than 75-05** (which was additive): it rewrites the primary session route. Plan for
  a clean cutover and verify the legacy-session degrade path.

---
*Discussion completed 2026-08-26. Ready for `/paul:plan 75-07`.*
