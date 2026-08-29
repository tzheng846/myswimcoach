# Project State

*Lean current-state snapshot — updated as work lands. How the pipeline **works** lives in
[PIPELINE.md](../PIPELINE.md) (repo root); the phase index in [ROADMAP.md](ROADMAP.md); the data map
in [DATA-FLOW.md](../DATA-FLOW.md). The full pre-2026-08-20 running log (4,905 lines) is archived at
[.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md).*

## Current Position

- **Milestone:** v0.5 Commercial Foundation
- **Phase 75-06** (Swim + Whole metric batch) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28**
  (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). ⚠ **UNCOMMITTED — see the working-tree note below.**
  **The race-phase registry is now complete** (37 → **47 specs**; `streamline_drag` is the only
  `planned` one left). 23 Swim + Whole metrics implemented and rendered as the report card's last two
  sections; the two `<ComingSoon>` stubs are gone. Suite **485 green** (+38); web build clean.
  **User rule that shaped it:** *prioritize existing annotations first, then fall back to auto
  segmentation* — boundary-level precedence already existed (`resolve_boundaries`: manual > detected >
  auto), so the new work was **per-cycle**: `PhaseContext.cycles` + `segmentation_reliable`, plus a
  `needs_cycles` spec flag that becomes an emitted **`provisional`** (schema_version 2 → **3**), which
  the UI renders with valence forced neutral. **Verified on the live library: `dead_spot_timing` =
  43 TRUSTED (coach cycles) / 44 provisional**, exactly matching the 43 annotated sessions.
  ✅ **Backfill applied (user-run, twice):** 99 sessions, all schema_version 3, **0 stale keys** — this
  also closed the never-run **75-04 Start backfill** (Start now 95–97/99). Decisions: D7 vector metrics
  → **N scalar specs**, never list-valued (`phaseBaseline` looks up by key across history, so list
  indices would misalign); D11 **`breathing_dip` DELETED**, not deferred — a 1-D axial encoder cannot
  observe breaths. ⚠ **AC-7 human-verify NOT run** (portal is Supabase-auth-gated) — owed, same posture
  as 81-01; includes judging the ~23-row panel length.
  See [75-06-SUMMARY.md](phases/75-report-card-phase-model/75-06-SUMMARY.md) ·
  [75-06-CONTEXT.md](phases/75-report-card-phase-model/75-06-CONTEXT.md) ·
  [75-06-PLAN.md](phases/75-report-card-phase-model/75-06-PLAN.md).
  **New owed items from this plan → 13–16 below.**
- **Phase 83-01** (Per-cycle trace coloring — cycles half) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28,
  AC-7 approved.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. **Frontend only, zero Python — suite still 485 green.** The
  Swimming-section inset now draws one alternating blue/purple band per `metrics_json.cycles` entry over
  a neutral-grey base, a boundary tick at every edge, an amber halo on the duration-outlier cycle, a
  `N cycles · annotated|auto` badge, a per-band hover readout, and bidirectional cross-highlight with the
  four `CycleCharts` panels. Annotations-first needed **no precedence code** — `PUT /annotations` already
  replaces `metrics_json.cycles` with the coach's, so reading the stored array *is* the precedence.
  New pure `web/lib/cycleBands.js` is shape-agnostic and **83-02 reuses it for kicks unmodified**
  (verified: a `{kick_num, interval_s}` fixture bands + flags correctly via `durationKey`).
  **Unlike 75-06 and 81-01, the human-verify WAS run** — user approved on the live portal 2026-08-28.
  ⚠ **Two silent-failure bugs found during verification, both fixed — both matter to 83-02:**
  (1) `PhaseVelocity`'s new `bands` prop was **shadowed** by the hero variant's existing phase-tint local
  inside `geom`, so the prop was never read (now aliased `cycleBands`); (2) **Tailwind v4 tree-shakes
  `@theme` tokens that no utility class references** — the three new colours are read only as raw `var()`
  in an SVG `stroke`, so they compiled away and every band rendered `stroke: none`, i.e. invisible. The
  block is now **`@theme static`** ([globals.css](../web/app/globals.css)); any future token consumed only
  via `var()` needs the same. Neither bug is visible to `next build` or `eslint` — only to a render check.
  Deviations from PLAN: `web/app/app/sessions/[id]/page.js` joined `files_modified` (plan-sanctioned —
  `segmentationReliable` threaded explicitly, never inferred from an annotation row); `@theme static`
  rather than a plain block; the hover readout **replaces** the inset caption instead of adding a line
  beneath it, so the four charts don't shift down mid-gesture; badge pluralises (`1 cycle`).
  ⚠ **Stacks on the 75-06 tree, which is loop-closed but still UNCOMMITTED** (D11) — base verified
  **485 passing** 2026-08-28. The web-side diff is now 75-06 + 83-01 mixed in `PhaseReportCard.js`, and
  `web/lib/phaseValence.js` is 75-06's alone — same hunk-staging problem as `api.py`, one more reason the
  next commit takes the whole tree.
  ⚠ **Phase 83 itself stays 🚧 — NOT transitioned, NO phase commit.** 83-01 is 1 of 2 plans; the
  plan-count heuristic would have called the phase done, but 83-02 is the kicks half.
  See [83-01-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-01-SUMMARY.md) ·
  [83/CONTEXT.md](phases/83-per-cycle-trace-coloring/CONTEXT.md) ·
  [83-01-PLAN.md](phases/83-per-cycle-trace-coloring/83-01-PLAN.md).
- **Phase 83-02** (Per-cycle trace coloring — kicks half) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28,
  apply outcome approved.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. **Backend + frontend.** New pure
  `metrics.segment_kick_bands` splits trough-to-trough at the plain argmin between consecutive detected
  peaks (**no new tuning constant**, D4); `compute_phases` emits **`phases.kick_bands`** beside
  `boundaries`; `SCHEMA_VERSION` **3 → 4**; the Underwater inset renders it through 83-01's `buildBands`
  and `PhaseVelocity` with **zero configuration** (`duration_s` was chosen so the default `durationKey`
  applies). Badge reads `N kicks · auto` — kicks are **auto-only**, no reliability half, until 81-02 ships
  a coach kick-marking path. Breaststroke gated off (`pulldown · not kicks`). Suite **485 → 497 green**
  (+12); web build clean, 19 pages.
  ⚠ **CONTEXT D5 REVERSED at the decision checkpoint** — bands live **inside `phases`**, not at top-level
  `metrics_json.kicks`. D5's premise ("`phases` is a pure metrics-registry payload") is factually
  incomplete: `phases` already carries `schema_version`, `go_signal_s`, `boundaries`. A top-level key
  needs writes at **all three** `PhaseContext` sites — the exact bug 75-06 shipped — and `PUT /annotations`
  would carry it forward **stale** against a window the coach just replaced. Inside `phases` it re-derives
  with the boundaries and cannot go stale. Cost: kicks read from `phases.kick_bands` while cycles come from
  `metrics.cycles`; **81-02 may want a coach-writable kick array outside the derived object.**
  ✅ **Backfill applied (user-run), verified against STORED state** — 99/99 sessions at `schema_version` 4,
  **0** missing the key, **63 of 81 non-breaststroke carry bands** (84/99 have a resolvable underwater
  window — matches item 14). `tools/backfill_phases.py` gained a `with_kick_bands` counter because AC-7
  requires the run to make a zero *visible*; it had none.
  ⚠ **Two deviations worth carrying forward:** (1) **AC-5 failed by the letter** — `web/lib/cycleBands.js`
  is genuinely untouched, but **`PhaseVelocity.js` was modified**: the user directed removal of the
  **peak dot** from the hero chart and all four insets mid-verify (its `argmax` helper deleted as an
  orphan). (2) Tasks 2–3 were found **already applied** in the tree from a cut-off prior session, and
  Task 4 was **half**-applied — the `kickBands`/`hoverKick` memos existed but nothing in the render read
  them, so no band was ever drawn; only the render wiring was written this session.
  ⚠ **`web/lib/cycleBands.js:9` now carries a false comment** (says 83-02 passes `metrics_json.kicks`
  through it) — left alone under the DO-NOT-CHANGE boundary; **83-03 fixes it**, since it edits that file.
  ⚠ **Phase 83 still 🚧 — NOT transitioned, NO phase commit.** Plan/summary counts are now equal (2/2),
  which is exactly the heuristic that would wrongly call the phase done — same trap as 83-01. **83-03 is
  next.**
  See [83-02-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-02-SUMMARY.md) ·
  [83-02-PLAN.md](phases/83-per-cycle-trace-coloring/83-02-PLAN.md).
- **Phase 83-03** (Breakout band + shape-anomaly investigation) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-29.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. AC-8 approved on the
  SECOND attempt — the first verify was **RETRACTED** by the user. Frontend only; no Python, no
  schema change.
  ⚠ **The plan's central feature was CUT on evidence.** A read-only probe over the stored library
  (90 usable sessions / 618 cycles, `scratch/shape_viability_probe.py` + `shape_sweep_probe.py`)
  measured the shipped MAD gate: it fired on **75% of sessions at k=3.0** (15.5% of all bands) and
  still **39% at an absurd k=8.0**. There is no k where a clean swim is quiet and a ragged one is
  not. Cause = **sample size**: a lap holds a **median of 7 cycles**, so the MAD is small and
  unstable — a within-lap outlier test on n=7 is not an abnormality test. Dropping cycle 1 helps
  marginally (67% → 55% at k=4.0) and costs 10 sessions their eligibility. This also contradicts the
  product's own SPC doctrine (baseline from HISTORY, not from within the sample).
  **→ `web/lib/cycleShape.js` is kept but PARKED and unwired**, with the numbers in its header; the
  red anomaly colour, halo, `anomalies` plumbing and flag hover copy are all removed. **New owed
  item 17.**
  ✅ **What DID ship — the breakout gold, now on measured ground.** The user's annotation convention
  (recorded 2026-08-29, see below) makes the Swimming inset's grey lead-in **structural**:
  `stroke_start_s` is the coach's **streamline-break** mark while `stroke_marks_s[0]` is the first
  hand **returning overhead**, so the breakout pull itself lies between them and belongs to no cycle
  (freestyle `k=2`, cycles = `marks[0::2]`). Measured: on all **43 annotated** sessions that gap is
  **positive**, median **1.04 s** (0.08–1.63) — never negative. `buildBands({breakoutFirst})` inserts a
  **SYNTHETIC `n: 0` band** spanning `i0` → the lowest-n cycle's start, painted `--color-cycle-breakout`
  gold. ⚠ **Corrected mid-verify:** the first re-cut *merged* the pull into cycle 1 (gold = streamline
  break → end of cycle 1) and the user rejected it — **"gold is two strokes instead of one"**. The
  breakout is ONE stroke; cycle 1 keeps its own colour. **No gap ⇒ no gold band** (never invent a
  zero-width stroke). `n: 0` is outside CycleCharts' keyspace, so hovering it highlights nothing there —
  correct, it has no row. Badge counts non-breakout bands so "5 cycles" stays 5.
  ⚠ **Gold is gated on `segmentationReliable`** — on **AUTO** sessions cycle 1 is NOT the breakout:
  **28 of 47** start BEFORE `stroke_start_s`, worst **−12.9 s**. Auto sessions keep the grey.
  Verified: `scratch/shape_checks.mjs` **15/15**, `next build` clean 19 pages, eslint clean apart
  from the pre-existing `set-state-in-effect`, **no Python touched**, suite **497**. Production CSS
  greps confirm `--color-cycle-breakout` survives tree-shaking and `--color-cycle-anomaly` is gone.
  ⚠ The retracted verify's other two complaints — the pink halo and the ambiguous shape-vs-duration
  hover copy — were **dissolved** by cutting the flag, not fixed.
  ⚠ **Process lesson recorded:** `k = 3.0` was justified in the PLAN by Gaussian reasoning that needs
  dozens of samples; **the cycle count was never checked before the gate was written.** Measure a
  threshold's fire rate on real data before shipping it.
  ⚠ **`annotations.py:25` is WRONG about the breakout** — it says "THE FIRST STROKE CYCLE CONTAINS THE
  BREAKOUT", but under the coach's marking convention the pull sits AHEAD of cycle 1. Left alone
  (Python boundary); owed a future correction, and anything reasoning from that docstring is suspect.
  ⚠ Also fixed `cycleBands.js:9`'s false `metrics_json.kicks` comment (owed from 83-02).
  ⚠ **Phase 83 stays 🚧 — NOT transitioned, NO phase commit.** PLAN/SUMMARY counts are now 3/3, the
  exact heuristic that would wrongly call the phase done — the same trap flagged at 83-01 and 83-02.
  **83-04 has no PLAN yet.**
  See [83-03-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-03-SUMMARY.md) ·
  [83-03-PLAN.md](phases/83-per-cycle-trace-coloring/83-03-PLAN.md) — ⚠ the PLAN's AC-1/2/4/5/6
  describe the CUT feature and no longer match the tree; read the SUMMARY, not the PLAN.
- **Phase 83-04** (inset window framing) — **📋 dropped out of 83-03 when option B was chosen; not yet
  planned.** Two usability findings from 83-02's verify, both confirmed against the code:
  (1) **a single-dolphin-kick underwater stretches ~0.5 s across the full chart width** — there is no
  minimum span; (2) **every inset hard-clips to its own phase**
  ([PhaseVelocity.js:67](../web/components/portal/phases/PhaseVelocity.js)) — the grey the user read as
  out-of-phase context is actually the band **base trace** showing un-segmented time *inside* the
  window, so context padding is genuinely **new behaviour, not a consistency fix**. Scope: pad
  Start/Underwater/Swimming past their boundaries with the extension drawn grey, plus a minimum span in
  **seconds** (never samples — the rate is per-session, ~89.5 Hz typical). Bands must keep clamping to
  the **phase** window, not the padded one. Whole-race inset is already the full trace ⇒ no-op there.
- **Phase 82** (Storage Quota Cleanup) — **🚧 PLAN created 2026-08-27, awaiting APPLY.** Supabase free
  tier is over quota (2.53 GB vs 1 GB cap; new uploads may already be blocked). Two leak sources found
  in `DELETE /sessions/{id}`: `video_path` never removed from the `videos` bucket, and `session_videos`
  externals `ON DELETE CASCADE` at the DB level without their storage objects being removed — together
  716 MB (28%) of the 2.5 GB video bucket is orphaned. Confirmed exhaustive against `live_schema.json`
  (only these two tables reference `session_id`). Plan: fix both leak sources in `api.py` + tests, ship
  a dry-run-by-default `tools/cleanup_orphan_videos.py`, then a human-action checkpoint to actually run
  `--apply` and reclaim the space. User separately decided to close the remaining ~800 MB gap by
  upgrading to Supabase Pro ($25/mo, out-of-band billing action) rather than compressing/deleting
  ground-truth video. See [82-CONTEXT.md](phases/82-storage-quota-cleanup/CONTEXT.md) ·
  [82-01-PLAN.md](phases/82-storage-quota-cleanup/82-01-PLAN.md).
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
- **⚠ Working tree — 75-06 and 82-01 are BOTH uncommitted, and they SHARE `api.py`.** This is the one
  thing to resolve before the next commit. `api.py` + `tests/test_api.py` carry **82-01's**
  session-delete storage cleanup (applied, never committed); `api.py` *also* carries **75-06's** cycle
  threading + the `PUT /annotations` phases repair. Committing either plan cleanly needs hunk-level
  staging (`git add -p`), which is unavailable in this environment — so **nothing from 75-06 was
  committed.** 75-06's own files: `phase_metrics.py`, `tools/backfill_phases.py`,
  `web/components/portal/phases/PhaseReportCard.js`, `web/lib/phaseValence.js`,
  `tests/test_phase_metrics.py`, `tests/test_annotations.py`, `PIPELINE.md`, `.paul/PROJECT.md`.
- **Committed history:** 75-03 = `7035157`, Phase 79 = `e1934ba`, Phase 78 + doc reconciliation =
  `76d2a18`, **75-05 report-card UI = `9dd5f7a`**, **75-07 report-card merge = `040ce0d`**, **81-01
  annotate marking = `a73db03`** (frontend only; `.claude/launch.json` is gitignored, stays local).
  Stored library backfilled 2026-08-21 (all four boundaries) and again **2026-08-28** (75-06 metrics +
  the 75-04 Start metrics). Other dirty files belong to **other streams:** `ESP_32_V5/ESP_32_V5.ino`
  (firmware), `.gitignore`, `assets/icon/`, `scratch/`, `segmenter_report.json`, the untracked Phase-80
  dir, and the 75-04/75-06 discovery docs.

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

**7. ✅ RESOLVED + CLOSED (75-06, 2026-08-28). → [75-06-SUMMARY.md](phases/75-report-card-phase-model/75-06-SUMMARY.md).**
The Step-2 metric registry is **complete**: Start 10/11 (75-04) + Underwater 13/13 (75-02/03) +
**Swim 12/12 and Whole 11/11 (75-06)** = 46 of 47 specs implemented; `streamline_drag` is the only
one still `planned`. Backfill applied — Start 95–97/99, Swim window 97/99, Whole 84–98/99.
⚠ `reaction_time` is **0/99 and cannot fill**: the `PUT /sessions/{id}/go-signal` endpoint shipped in
75-04 but the coach **GO button never did**, so no session has a GO time (item 15).

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
`detect_swim_window`; no phase has ever owned tuning it. Candidate for a dedicated pass. ⚠ Note the
2026-08-28 domain fact (PIPELINE.md): the mark **belongs before velocity reaches zero** — swimmers
drift into the wall after touching — so any retune must not chase stillness.

**13. ⚠ 75-06 AC-7 human-verify OWED.** The four phase sections have never been looked at on a live
session (portal is Supabase-auth-gated). Specifically owed: confirm no "coming soon" remains, hover
shows window provenance + the provisional note, provisional rows are not colored, and — the one thing
deliberately left to the user's eye — **judge whether ~23 new rows need grouping or collapse.**

**14. ⚠ ~15 sessions have an UNRESOLVABLE underwater window.** Every underwater-dependent metric
ceilings at 84/99 (`uw_*`, `breakout_vel_loss`, `phase_*_budget_underwater`, `vel_envelope_underwater`).
This is why a coach can open a session and find the whole Underwater panel blank with no inset chart.
Pre-existing (not caused by 75-06) and never diagnosed. Candidate for its own pass alongside item 12.

**15. `reaction_time` cannot fill until the coach GO button ships.** Backend done in 75-04
(`PUT /sessions/{id}/go-signal`); no UI writes to it, so 0/99 sessions carry a GO time. Also needs the
phone↔encoder clock sync that 75-04 deferred.

**16. ❓ Are 5/10/15/20/25 m the right split points?** `splits_25m` fills on **2 of 99** sessions —
structurally, not by failure: the tether is waist-mounted, so a 25-yard lap (22.86 m) records only
~21.9 m of travel (PIPELINE.md). `splits_20m` is 56/99. Options: drop the 25 m split, move to four
splits, or re-anchor to yardage. **Not changed unilaterally — user decision.**

**17. Shape-anomaly detection needs a CROSS-SESSION baseline (83-03 finding, measured).** Per-lap
self-comparison is dead: median 7 cycles/lap makes the MAD gate fire on 75% of sessions at k=3.0 and
39% at k=8.0 — no usable threshold exists. The algorithm in `web/lib/cycleShape.js` is correct and
duration-invariant (12/12 scratch checks); only its **reference population** was wrong. The fix is to
build the median profile from the athlete's **last N same-stroke SESSIONS** — the same within-athlete
contrast `web/lib/phaseBaseline.js` already uses for every metric strip, and the SPC posture the
product doctrine asks for. Needs prior sessions' velocity arrays reachable from the browser, so it is
a **backend/data question, not a frontend one**. Probes: `scratch/shape_viability_probe.py`,
`scratch/shape_sweep_probe.py` (read-only, re-runnable).

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
- **83-02** (closed 2026-08-28) — Underwater inset draws one band per detected downkick. `phases.kick_bands`
  (schema 4) trough-to-trough, no new constant; reuses 83-01's lib unmodified; breaststroke gated off;
  63/81 non-breaststroke backfilled. D5 reversed: bands ride inside `phases` so all three write sites get
  them from one change and they cannot go stale against an annotated window. Peak dot removed everywhere.
- **83-01** (closed 2026-08-28) — Swimming inset draws one alternating blue/purple band per stored cycle
  over grey, + ticks, amber outlier halo, annotated-vs-auto badge, hover readout, bidirectional highlight
  with `CycleCharts`. New pure `web/lib/cycleBands.js` (83-02 reuses it for kicks unmodified). Two
  silent-failure bugs caught only by a render check: a shadowed prop, and Tailwind v4 tree-shaking
  `@theme` tokens read only via `var()` (→ `@theme static`).
- **75-06** (closed 2026-08-28) — 23 Swim + Whole metrics; registry complete at 46/47. `PhaseContext.cycles`
  + `provisional` flag (schema 3) = annotations-first for per-cycle metrics (43 trusted / 44 provisional
  live). Fixed `PUT /annotations` destroying `phases`, and a THIRD `PhaseContext` site in
  `tools/backfill_phases.py` that had left both per-cycle metrics 0/99. Suite 485.

- **83-03** (closed 2026-08-29) — Gold breakout band = the coach's streamline-break mark → their first
  stroke mark, a SYNTHETIC `n: 0` band, annotated sessions only. **The plan's shape-anomaly flag was
  MEASURED AND CUT**: at 7 cycles a lap the MAD gate fired on 75% of sessions (k=3.0) and 39% at k=8.0
  — no threshold separates clean from ragged. `web/lib/cycleShape.js` parked unwired; fix needs a
  cross-session baseline (item 17). First human-verify retracted; gold re-cut twice.

## Pointers
- **How it works:** [PIPELINE.md](../PIPELINE.md) — signal, phase model, detectors, metrics registry
- **Phase index / milestones:** [ROADMAP.md](ROADMAP.md)
- **Data map (stores, endpoints, jsonb):** [DATA-FLOW.md](../DATA-FLOW.md)
- **Requirements / product intent:** [PROJECT.md](PROJECT.md)
- **Full historical log:** [.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md)
