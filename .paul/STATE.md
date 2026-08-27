# Project State

*Lean current-state snapshot — updated as work lands. How the pipeline **works** lives in
[PIPELINE.md](../PIPELINE.md) (repo root); the phase index in [ROADMAP.md](ROADMAP.md); the data map
in [DATA-FLOW.md](../DATA-FLOW.md). The full pre-2026-08-20 running log (4,905 lines) is archived at
[.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md).*

## Current Position

- **Milestone:** v0.5 Commercial Foundation
- **Arc:** Race-phase report-card model (Phases 75–77) — segment the 4 phase boundaries, then compute
  per-phase metrics, then build the UI.
- **Phase 77** (fly breakout) — closed + committed (`d6e00c8`, `0ff29e7`).
- **Phase 76** (free/back breakout) — closed + committed (`046b8d1`).
- **Phase 75-03** (7 underwater kick metrics + `detect_underwater_kicks`) — **✅ CLOSED 2026-08-21.**
  Eyeball (AC-4) approved on ground-truth windows; hypothesis 1 (peaks+prominence) accepted. The
  review surfaced + FIXED a bigger defect: stored `stroke_start`/`finish` were stale and the backfill
  couldn't refresh them → new `metrics.detect_swim_boundaries` + `detected` branch in
  `resolve_boundaries` (auto `stroke_start` err **3.56 s → 0.40 s**). Suite 426 green.
  See [75-03-SUMMARY.md](phases/75-report-card-phase-model/75-03-SUMMARY.md).
- **Phase 75-04** (Start-phase metrics batch — Step 2) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY), 2026-08-21.**
  [75-04-SUMMARY.md](phases/75-report-card-phase-model/75-04-SUMMARY.md). 10 of 11 Start metrics implemented in
  one pass (D12 gate **waived**); `streamline_drag` stays planned. New `PUT /sessions/{id}/go-signal` stores the
  GO time in `metrics_json` (jsonb, no migration) → `reaction_time` derives (motion onset − GO; anchor is the
  jump, not `dive_start`). `recompute_phases` refactored into shared `_rebuild_phases` (reads the stored GO time).
  Suite **443 green** (+17). Committed `defed65`. ⚠ **owed: user-run `python tools/backfill_phases.py --apply`**
  to populate the 9 non-reaction Start metrics across the stored library. Key finding: registry tiers are stale —
  75-02/79 turned the "high" glide/break-into-kick metrics cheap (PIPELINE §6 flagged).
- **Phase 75 Step 3** (report-card UI, Plan 75-05) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-25**
  (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). New `/app/sessions/[id]/phases` route renders Start + Underwater
  in the v3 visual language (1D usual-range strips, valence coloring, hover-explain, dismissable alert
  line, phase timeline); Swim/Whole = "coming soon". First Phase-75 surface visible in any UI.
  See [75-05-SUMMARY.md](phases/75-report-card-phase-model/75-05-SUMMARY.md). **Phase 75 stays 🚧 —
  Swim (9) + Whole (4) metrics + their UI still owed (item 7); those become new plans (75-06+).**
- **Phase 75-07** (report-card CONSOLIDATION — the race-phase view is now the PRIMARY `/app/sessions/[id]`) —
  **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-26** (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). Code committed
  **`040ce0d`** (frontend only) + docs. Classic analytics (SessionSummaryCard / PillarCards / MetricGrid /
  Simple-Advanced) removed; **`PhaseReportCard` is the body** with velocity / Time-to-Distance / video threaded
  via a new **`middleSlot`** seam; Swimming section = the existing per-cycle line charts (`CycleCharts`);
  standalone legend gone; delete → header **⋯ overflow**; **coach chat = floating bottom-right blob** (z above
  the hover scrim); `/app/sessions/[id]/phases` → **server-component redirect** to the primary page. Kept the
  **interim** classic VelocityChart+AccelerationChart (un-regressed). Build clean (19 pages); redirect
  (`NEXT_REDIRECT …;307`) + SSR verified; **AC-6 human-verify approved**. Decisions: coach-chat `simple`
  dropped (full depth, coach audience); ⋯ = Delete only (Export/Manage-videos not trivial). Pillars **not
  deleted**, just unrendered (relocate to a roster surface later).
  See [75-07-SUMMARY.md](phases/75-report-card-phase-model/75-07-SUMMARY.md).
  **Next in the merge:** **75-08** (compare-vs-last-X slider + alert "N Changes" rebuild + `phaseBaseline` as a
  persisted pref + timeline hover dot+range strips) → **75-09** (unified interactive phase-tinted trace, gated
  on the "new functionality" decision). ⚠ **75-06** (Swim/Whole *metrics*,
  [75-06-DISCOVERY.md](phases/75-report-card-phase-model/75-06-DISCOVERY.md)) composes independently at
  Swimming/Whole. CONTEXT + PLAN: [75-07-CONTEXT.md](phases/75-report-card-phase-model/75-07-CONTEXT.md) ·
  [75-07-PLAN.md](phases/75-report-card-phase-model/75-07-PLAN.md).
- **Phase 78** (multi-swimmer segmentation diagnostic — owed item 2) — **✅ CLOSED + committed
  2026-08-21** (`status: complete`, AC-1/2/3 met — pure diagnostic, no detector changes). Resolved
  (fork **b**): *scored* corpus = **4 swimmers** (Tony/Leo/Chantee/Dane),
  but the DB holds **~15 humans** — Titus (8), AlexGroup (9, a stand-in = 8 named testers), Jenna (2),
  Michael (1) are **real but unannotated** (37/92 sessions labeled). Validation is confined by
  *annotation coverage*, not data. See [78-01-SUMMARY.md](phases/78-multiswimmer-seg-diagnostic/78-01-SUMMARY.md).
  New owed gaps below (items 9–12).
- **Phase 79** (redefine `dive_start_s` = foot of first ≥X surge — owed item 1) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY), 2026-08-21, X=2.0.** Code committed **`e1934ba`**; docs (PIPELINE §3 / STATE /
  ROADMAP) landed; **backfill applied 2026-08-21.**
  ([79-01-SUMMARY.md](phases/79-dive-start-redefine/79-01-SUMMARY.md)).
- **Phase 81** (annotation video marking) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-26**, committed
  **`a73db03`** (frontend only). Shipped **well beyond** the plan's keyboard slice via three live redirections:
  the **active annotate camera is now a stage-fullscreen video overlay** whose control bar carries the
  **marker buttons** (Dive/UW/Stroke/Finish + stroke-mark, at the current frame) + **4/8/All window presets**
  — so a coach marks in **fullscreen without exiting** (the actual ask). Placed marks render as strip ticks
  (in-fullscreen confirmation, `TraceOverlay` used as-is). `overlayMode = active && synced` gate: native
  controls until synced (scrub to Set-sync landmark), custom marking stage once synced. Keys **1/2/4/5+M**
  retained as an alias. **Shared report-card components (VideoTracePanel/VideoPane/PlaybackControls/
  TraceOverlay) UNTOUCHED → zero report regression.** New shared `placeBoundary()` (chart-tool/keys/buttons
  DRY). ESLint + compile clean. ⚠ **Blocking human-verify NOT run** (annotate page is Supabase-auth-gated;
  shipped on user instruction + lint/compile + mockup approval) — owed against a live synced-video session.
  See [81-01-SUMMARY.md](phases/81-annotation-video-marking/81-01-SUMMARY.md). **Phase 81 stays 🚧 — 81-02
  (key-3 UW-kick marker + ALL backend: annotations/phase_metrics/api recompute) still owed.** Enables STATE
  item 9 (annotate the backlog fast).
- **Working tree — segmentation arc + 75-05/75-07 UI + 81-01 committed.** 75-03 = `7035157`, Phase 79 =
  `e1934ba`, Phase 78 + doc reconciliation = `76d2a18`, **75-05 report-card UI = `9dd5f7a`**, **75-07
  report-card merge = `040ce0d`**, **81-01 annotate marking = `a73db03`** (frontend only; `.claude/launch.json`
  is gitignored, stays local). Stored library **backfilled 2026-08-21** (`tools/backfill_phases.py --apply`):
  all four boundaries re-resolved from live detectors. Dirty files left uncommitted belong to **other
  streams:** `ESP_32_V5/ESP_32_V5.ino` (firmware), `.gitignore`, `assets/icon/`, `scratch/`,
  `segmenter_report.json`, the untracked Phase-80 dir, and the 75-04/75-06 discovery docs.

## Segmentation status — the 4 phase boundaries
Mechanisms in [PIPELINE.md §3](../PIPELINE.md).

| Boundary | State |
|---|---|
| `dive_start_s` | ✅ `detect_dive_start` (79) — foot of first ≥2 m/s surge; median 0.15 s vs 36 marks (vs `baseline_end` 0.72 s); falls back to `baseline_end` on sub-X starts |
| `underwater_start_s` | ✅ `detect_underwater_start`, median 0.13 s |
| `stroke_start_s` (breakout) | ✅ free 0.42 s (Tony+Leo) · fly 0.38 s (Tony/Leo; ⚠ 0.87 s Chantee) · ⛔ **back n=0 unvalidated** · ⚠ **breaststroke = incumbent, untuned** (Phase 78). **Now `detected` via `detect_swim_boundaries` in `resolve_boundaries`** (75-03), so backfill/recompute refresh it (was stale seed, 3.56 s → 0.40 s) |
| `finish_s` | `detect_swim_window` end — **now `detected` via `detect_swim_boundaries`** (75-03), no longer the stale last-cycle seed. Still weakest marker (item 12) |

## Owed / next actions (priority order)

**1. ✅ RESOLVED (Phase 79, eyeball approved 2026-08-21). → [79-01-SUMMARY.md](phases/79-dive-start-redefine/79-01-SUMMARY.md).**
`dive_start_s` now = **`detect_dive_start`** ([metrics.py](../metrics.py)): the foot of the first surge
that clears **X = 2.0 m/s** — the last prominent trough (prominence ≥ 0.15·X) left of the first upward
crossing. Wired in `resolve_boundaries` as source `detected`; `build_seed` reads the stored boundary back
for the annotate draft (mirrors the 75-02 underwater precedent). When no sample reaches X (weak wall
push-off) → **falls back to `baseline_end`** (source `auto`), so never worse than the old rule. Swept
(`tools/score_dive_start.py`, 36 hand-marked sessions): **0.15 s mean|err| vs `baseline_end` 0.72 s**;
detector-only 0.11 s (16/16); all 36/36 within 0.5 s. X=2.0 chosen for tug-margin (accuracy statistically
tied across X∈[1.25,2.0]). ✅ **BACKFILL APPLIED 2026-08-21** (user-run `python tools/backfill_phases.py
--apply`): stored `dive_start_s` re-resolved across the library, comparability break closed (standing
pattern 57/59-03/61-01/65/76-77). Code committed `e1934ba`; docs landed with the Phase 78 commit.

**2. ✅ RESOLVED + CLOSED (Phase 78, committed `76d2a18`; pure diagnostic, AC-1/2/3). → [78-01-SUMMARY.md](phases/78-multiswimmer-seg-diagnostic/78-01-SUMMARY.md).**
Answer = fork **(b): validation is confined by ANNOTATION COVERAGE, not data.** "One swimmer" was
false (4 annotated: Tony 18, Leo 14, Chantee 3, Dane 2) — but so is "clean multi-swimmer set."
**92 sessions exist, only 37 (40%) annotated.** STATE's roster instinct was RIGHT: **Titus** (8) and
**AlexGroup** (9, a stand-in whose session names are testers Henry/Ben/Desi/Spencer/Alina/Tate/
Olivia/Anna) are real, plus Jenna (2), Michael (1) — **all unannotated**, so no scorer sees them.
Where measured, detectors hold (underwater 0.13 s, free breakout 0.42 s across both swimmers; fly
0.38 s but 0.87 s on Chantee). PIPELINE §8 + the `score_segmenter.py` banner corrected. The fix that
matters is item 9. Residual gaps → items 9–12.

**3. ✅ DONE (2026-08-21).** 75-03 eyeball run on ground-truth windows
(`tools/plot_kicks.py --annotated-only`), hypothesis 1 approved, `75-03-SUMMARY.md` written. The
review also surfaced + fixed the stale-`stroke_start` backfill defect (see item 6). Two known
over-detection cases logged (`udk` alternating peaks; shallow-freestyle ripple) — not blockers.

**4. Fix `tools/breakout_band_probe.py` (DEFER-77-A).** The probe plots the exploratory/rejected
detector, not the shipped one — 3 defects, one root cause. Defect (a): `:270` passes `cand_idx` (the
probe's own `_detect_breakout`) to `_plot` instead of `ship_idx`, so even the freestyle plots draw a
detector materially different from production. **This blocks Phase 76's owed AC-4** (item 5). Fix (a)
before item 5, all three before the next breakout human-verify. Detail in
[77-01-SUMMARY.md](phases/77-fly-breakout-detection/77-01-SUMMARY.md) DEFER-77-A.

**5. Run Phase 76's AC-4 eyeball.** Never run — both 76 corrections were found by measurement, not the
checkpoint. Needs item 4(a) first.

**6. ✅ DONE (2026-08-21) — Backfills applied (user-run).** ⚠ CORRECTED 2026-08-21: the earlier
claim that `backfill_phases.py --apply` refreshes 76/77's `stroke_start` was **wrong** — it only re-ran
`compute_phases`, which read the stale stored `initial_phase_end_idx`. **Fixed** (75-03):
`resolve_boundaries` resolves `stroke_start`/`finish` via `metrics.detect_swim_boundaries`, so a single
`python tools/backfill_phases.py --apply` refreshes **all four** boundaries + 75-03's kick metrics from
live detectors. **Ran 2026-08-21** — comparability break landed across the library (dive_start +
all-four-boundary refresh in one pass). Standing pattern (57 / 59-03 / 61-01 / 65 / 79).

**7. Remaining Step-2 metrics** ([phase_metrics.REGISTRY](../phase_metrics.py)):
Start ✅ **DONE (75-04)** — 10/11 implemented; `streamline_drag` deferred; `reaction_time` via
`PUT /sessions/{id}/go-signal` (phone↔encoder clock sync + GO-button UI still deferred). ⚠ backfill owed.
**Swim (9 — IVV, breakout velocity, splits, dead-spot; mostly cheap) and Whole race (4) remain — next batches.**

**8. Step-3 UI.** Phase-organized web report card (Dive/Push-off / Underwater / Swim), then iOS.
Display doctrine = within-athlete contrast, **no absolute thresholds**. Design docs:
[CONTEXT-ui-consolidation.md](phases/75-report-card-phase-model/CONTEXT-ui-consolidation.md) (spine =
race-phase timeline; pillars → roster surface) +
[75-05-DISCOVERY-ui-visual-language.md](phases/75-report-card-phase-model/75-05-DISCOVERY-ui-visual-language.md)
(2026-08-22). **Visual language re-settled 2026-08-25 in the rendered mockup `scratch/report-card-concept-v3.html`
(the source of truth; v1/v2 are earlier drafts):** (1) each metric = a **1D usual-range strip**
(shaded median±1.5·MAD band + median tick + today dot on a 0-based scale) — the Today-vs-Usual paired
bars are **out** (two equal bars carried no info); (2) color = **direction-of-good valence** — green
better / red worse / **grey "changed, unclear"** where "better" is a coaching call — via a new
reviewable `DIRECTION_OF_GOOD` map (⚠ a deliberate, user-approved evolution of the old no-valence rule;
still no absolute thresholds); (3) **almost no always-on prose** — descriptions + comparisons live in a
page-dimming **hover overlay**; (4) per-phase layout = **inset chart on top, metrics in 2 columns**;
(5) terse titles ("Dive / Push-off" — dive & wall-push are the *same* Start window per registry, so no
metric split). Top = the deterministic **alert line** (count + "N worse / N changed / N better" chips,
**coach-dismissable**). Baseline = **last 5 same-stroke swims**, band = **median ± 1.5·MAD** (robust for
n=5; was mean±SD). Placement = **new `/app/sessions/[id]/phases` route** (isolated, additive).
**→ PLAN [75-05-PLAN.md](phases/75-report-card-phase-model/75-05-PLAN.md) (created 2026-08-22, REVISED to
the v3 language 2026-08-25) — ✅ APPLIED + human-verify approved 2026-08-25 (loop: PLAN ✓ → APPLY ✓ →
UNIFY ○). → [75-05-SUMMARY.md](phases/75-report-card-phase-model/75-05-SUMMARY.md).** Shipped: new
`/app/sessions/[id]/phases` route rendering Start + Underwater as 1D usual-range strips (median±1.5·sMAD
of last 5 same-stroke), valence-colored via a new reviewable `DIRECTION_OF_GOOD` map (a user-approved
evolution of the no-valence rule — **still no absolute thresholds**), a deterministic dismissable alert
line, phase timeline, phase-tinted velocity line, and a page-dimming hover-explain overlay; Swim/Whole =
"coming soon". New pure libs `web/lib/phaseBaseline.js` + `web/lib/phaseValence.js`; components under
`web/components/portal/phases/`. Build clean; engine scratch checks 18/18. Deferred (documented in
SUMMARY): server-side dismiss persistence (client localStorage now), LLM headline, imperial/iOS, richer
signal insets. **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-25, committed `9dd5f7a`.** Next
Phase-75 work = Swim/Whole metric batches (item 7) + their strips, as new plans 75-06+.

**9. ⭐ Annotate the backlog — 20 real-swimmer sessions sit unscored (Phase 78, highest leverage).**
Titus 8, AlexGroup 9 (8 named testers), Jenna 2, Michael 1 — all 0 annotations. Labeling them converts
"generalises, probably" into a measured cross-swimmer number, and **unlocks backstroke** (annotate the 2
existing bk sessions: Tony + AlexGroup/Tate) and far more breaststroke. Then **re-run
`python tools/annotated_roster.py` + the 3 scorers** — the diagnostic is now a repeatable audit.

**10. ⛔ Backstroke breakout unvalidated (n=0) — Phase 78.** 2 labelable bk sessions exist (Tony,
AlexGroup/Tate). Stop claiming "back" in Phase 76's "free/**back**" until at least those are scored.

**11. ⚠ Fly breakout thins outside Tony/Leo — Phase 78.** Chantee (post-tuning, 3 sessions) sits at
0.87 s median (0/3 ≤0.5 s) vs Tony 0.26 s / Leo 0.29 s. Re-check after item 9; don't oversell fly
breakout as "generalises."

**12. ⚠ `finish_s` is the weakest phase marker (MAE 2.76 s, worst 6.43 s) — Phase 78.** Inherited from
`detect_swim_window`; no phase has ever owned tuning it. Candidate for a dedicated pass.

## Recent arc (compressed)
- **75-01** skeleton — `MetricSpec` registry (37 specs) + `metrics_json.phases` jsonb + `POST /sessions/{id}/recompute` backfill seam.
- **75-02** — `detect_underwater_start` + 4 underwater window metrics; backfilled all 108 sessions.
- **75-03** (closed 2026-08-21) — `detect_underwater_kicks` + 7 kick metrics (hypothesis 1 approved);
  also `detect_swim_boundaries` + `stroke_start`/`finish` `detected` branch so backfill refreshes all
  four boundaries (auto `stroke_start` 3.56 s → 0.40 s).
- **76** — free/back breakout by kick-band **disappearance**.
- **77** — fly breakout by arm-cycle **appearance**.
- **79** — `dive_start` redefined to foot-of-surge (`detect_dive_start`, X=2.0); MAE 0.72 s → 0.15 s.
- **75-04** (closed 2026-08-21) — 10 Start metrics (peak/time-to-peak/max-accel, dive duration, 4 glide,
  break-into-kick, reaction_time) + `PUT /sessions/{id}/go-signal`; `streamline_drag` deferred. Suite 443.

## Pointers
- **How it works:** [PIPELINE.md](../PIPELINE.md) — signal, phase model, detectors, metrics registry
- **Phase index / milestones:** [ROADMAP.md](ROADMAP.md)
- **Data map (stores, endpoints, jsonb):** [DATA-FLOW.md](../DATA-FLOW.md)
- **Requirements / product intent:** [PROJECT.md](PROJECT.md)
- **Full historical log:** [.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md)
