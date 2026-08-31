# Project State

*Lean current-state snapshot — updated as work lands. How the pipeline **works** lives in
[PIPELINE.md](../PIPELINE.md) (repo root); the phase index in [ROADMAP.md](ROADMAP.md); the data map
in [DATA-FLOW.md](../DATA-FLOW.md). The full pre-2026-08-20 running log (4,905 lines) is archived at
[.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md).*

## Current Position

- **Milestone:** v0.5 Commercial Foundation
- **Phase 75-06** (Swim + Whole metric batch) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28**
  (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). ✅ **Committed `20c0432`** (whole-tree commit, 2026-08-29).
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
  ✅ **Committed `20c0432`** with the rest of the tree, 2026-08-29.
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
- **Phase 83-05** (cycle/kick OVERLAY panel) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-29,
  AC-8 approved after two live corrections.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. **Frontend only;
  no Python, no schema, no backfill — suite still 497.** The replacement for 83-03's cut classifier:
  instead of *asserting* which stroke is odd, every cycle (or downkick) is drawn on ONE shared axis
  beneath its phase inset, in neutral grey, with a left number gutter that hover-previews and
  click-pins. New pure `web/lib/cycleTraces.js` + `CycleOverlay.js`; `PhaseReportCard` lifts the pin
  state and resolves `active = hovered ?? pinned` ONCE (D9). Seconds axis by default, normalized
  `% of cycle` toggle adding a pointwise-median line gated at 5 traces. **`PhaseVelocity.js`,
  `cycleBands.js` and `CycleCharts.js` are byte-identical — absent from `git diff`**, unlike 83-02
  which broke its own zero-diff AC.
  ⚠ **Two live corrections at the verify, both now shipped:**
  (1) **the gutter wraps at 10 rows** — a 15-dolphin-kick underwater made a single column stand
  taller than the chart beside it (`grid-auto-flow: column`; 9→1 col, 15→2×8, 25→3×9). The
  `0 · breakout` row moved OUTSIDE the grid so its long label cannot set every column's width.
  (2) **AC-3 was OVERRIDDEN by the user** — the breakout row is no longer inert; hovering it now
  highlights the gold `n: 0` band in the inset. It stays dim (no trace of it in the pack) and nothing
  in CycleCharts reacts, since 0 is outside that keyspace. ⚠ Numbered `dropout`/`too-short` rows are
  **still inert** — the same argument applies to them but was not generalised.
  ⚠ **Two boundary widenings, both forced by contradictions inside the PLAN itself:**
  (a) `cycleShape.js` gained **two `export` keywords** (Task 1 mandates importing `resample` +
  `median`; the boundary said "header comment only"). `analyzeShapes` + `K` untouched and, by grep,
  **still imported nowhere**. (b) **`niceMax` is DUPLICATED** from the DO-NOT-CHANGE `PhaseVelocity.js`
  — guarded by a render check asserting the two function bodies are **byte-identical**, so the copy
  cannot drift.
  ✅ **New reusable harness: `scratch/overlay_render_check.mjs`** (40 checks) — transpiles the
  component with the bundled `typescript` package, server-renders it with `react-dom/server`, and
  asserts on markup. **Needs no auth, so it works despite the Supabase-gated portal.** It targets
  83-01's two silent-failure classes directly: no path may render `stroke: none`, every trace must
  carry real `d="M…"` geometry. Plus `scratch/overlay_checks.mjs` (32 data checks). Build clean
  19 pages; eslint clean apart from the pre-existing `set-state-in-effect`.
  ⚠ **Ships the item-18 kick-tiling artifact knowingly** (D8) — but see the item-18 correction below:
  at 15 kicks the two tiling bands are 2 of 15, not "2 of 5", and the live pack read as tight.
  ⚠ **D5's auto-session posture survived the verify unchanged** — no caution copy was requested, so
  auto sessions carry only the existing `auto` badge to signal that spread may be segmentation.
  ⚠ **STATE item 17 stays open** — `resample` + the median are wired, the MAD gate is not.
  ⚠ **Peak-alignment surfaced as a better axis mode than align-center and was DECLINED** → new item 19.
  ✅ **Committed + pushed `45a858b`** (2026-08-29).
  ⚠ **Phase 83 stays 🚧 — NOT transitioned, NO phase commit.** PLAN/SUMMARY counts are now **4/4**, the
  exact heuristic that has falsely signalled "done" at 83-01, 83-02 AND 83-03. **83-04 (inset window
  framing) is scoped in STATE but still has no PLAN.**
  See [83-05-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-05-SUMMARY.md) ·
  [83-05-PLAN.md](phases/83-per-cycle-trace-coloring/83-05-PLAN.md) ·
  [83-05-CONTEXT.md](phases/83-per-cycle-trace-coloring/83-05-CONTEXT.md).
- **Phase 85** (Marketing home page refresh) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-29,
  AC-8 approved on the live local site; PHASE TRANSITIONED, 1/1 plans.** Frontend only, no Python touched, suite still 497.
  The marketing site had not moved since `17086cb` (2026-06-22); it now leads with the race-phase
  report card. Shipped: the Swimnetics mark enters the web surface for the first time (nav lockup
  inverted over the hero, footer lockup, `app/icon.png` + `app/apple-icon.png` replacing
  `favicon.ico`); hero copy per D21 with the floating chart card gone; new `PhaseStory` (one whole-lap
  real trace, three phase windows tinted in place, grey post-finish tail) + reusable `PhaseRadar`
  (axis count read from the data); `UsualRange`, `CyclePack`, `VideoSync`, `Device`; `Features.js`
  and `SampleChart.js` retired. Geometry is **baked at author time** into `web/lib/marketingGeom.js`
  by `scratch/_export_marketing_geom.py`, so a public page makes **no Supabase call** — whole-lap
  polyline decimated 1762 → 882 points (10 KB), cycles left whole.
  ⚠ **Copy rule now enforced by a check, not by eye:** `scratch/marketing_render_check.mjs`
  (**45 checks green**) counts BOTH dash forms (the FAQ was 10 `&mdash;` entities to 2 literals, so a
  character-only grep read it as clean), flags the banned strings, and — the 83-05 pattern — headlessly
  server-renders the components to assert no `stroke: none`, no empty `points`, and the usual-range
  coherence rule (a coloured strip sits OUTSIDE its band, a grey one inside).
  ⚠ **Four deviations:** (1) the copy check is scoped to the **marketing surface**, not all of
  `web/components` — the portal carries ~285 comment dashes, says "GoPro" legitimately in its upload
  help, and holds `changed (unclear)` inside the `AlertSummary.js` that **D27 forbids this plan to
  touch**; a permanently red check is a check nobody reads. (2) **AC-7's "still 19 pages" is now 20**,
  measured: `favicon.ico` is worth one static page and the two icon file conventions are worth two.
  (3) The three phase cards align their radars with a per-card **CSS grid row** (`1fr` on the blurb)
  rather than the mockup's reserved `min-height`, which held at 1280 but broke at 880 where the
  underwater blurb wraps to a fifth line and pushed its radar 21 px low; still never a flex column,
  and the radar SVG measures 227/159/119 px at 1280/880/700 so nothing collapsed. (4) `Brand` uses
  `next/image` because `@next/next/no-img-element` IS enabled in this config.
  ⚠ `web/src/data/sample-session.json` is now an **orphan** (SampleChart was its only reader), left in
  place. `/privacy` and `/blog` keep their em dashes by D5, including in their `<title>`.
  ✅ **Committed + pushed `a75c373` (2026-08-29) — Vercel auto-deploys `main`, so this is the public
  site now.** Excluded from the commit: `scratch/_home_session.json` (the raw probe dump carries the
  source athlete), `scratch/_mockup_template.html` (`*.html` is gitignored), and the round-1 leftovers.
  ✅ **Phase 85 IS complete and WAS transitioned — unlike 83, the plan-count heuristic is trustworthy
  here.** The trap that misfired at 83-01/02/03/05 is a phase with known remaining scope; Phase 85 has
  none: all four CONTEXT goals shipped in one plan, and D27's portal chip rename was scoped as a
  SEPARATE phase from the start, not as 85-02.
  See [85-01-SUMMARY.md](phases/85-website-home-refresh/85-01-SUMMARY.md) ·
  [85-01-PLAN.md](phases/85-website-home-refresh/85-01-PLAN.md) ·
  [85/CONTEXT.md](phases/85-website-home-refresh/CONTEXT.md).
- **Phase 84-01** (Mobile user feedback — NATIVE CONFIG half: items 1 icon + 4 orientation) —
  **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-30 — all three code tasks done and statically verified;
  the build-gated human-verify was DEFERRED by decision, not failed.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`
  (SUMMARY written 2026-08-30 01:38; STATE's loop marker corrected 2026-08-30 during the 84-02 UNIFY).
  Phase 84 is
  **7 items → 5 plans**; this is the first, chosen because it is the only lane touching **no JS at
  all**, so it cannot collide with the mobile repo's uncommitted Phase 74 work or with item 7's
  GO marker. Target repo is **`Desktop/swimnetics-mobile`** (separate, user-owned git).
  ⚠ **G1 — CONTEXT open question 2 is answered NO: there is no OTA channel.** No `expo-updates`
  dependency, no `updates` key in `app.json`, no channels in `eas.json` — only build/submit
  profiles. **All seven Phase-84 items ship in an EAS build.** The native/JS split survives as a
  *verification-cost* driver only, not a sequencing one.
  ⚠ **Three CONTEXT claims about this phase were checked against code and are WRONG:**
  (1) **`sharp` is not in the mobile repo** — it is in `myswimcoach/web/node_modules` (0.34.5);
  the plan uses Python **Pillow** in the backend repo instead, where the source art already lives.
  (2) **`assets/icon/Swimnetics_icon.svg` is not a vector** — it is an SVG wrapper around a
  base64 **1004×960 RGBA PNG** (56.4% transparent, `#7200FF` + a white interior highlight), with
  **zero ink margin on all four sides** and the `<image>` anchored top-left in a 1028×1028 viewBox.
  So 1024 is a 2% upscale, alpha **must** be flattened (iOS rejects alpha; Phase 85's web icons are
  deliberately transparent and that precedent does **not** transfer), and padding has to be invented
  rather than inherited — rendering the SVG would put the mark off-centre up-and-left.
  (3) **`AthleteDetailScreen` has no access to `rating_colors`** — its pillars come from
  `route.params.athlete`, not a fetch, so **item 5 needs navigation-param plumbing, not just a
  lookup swap**. (Item 5 is a **four**-surface problem; `AthletesScreen.js:84` is the fourth and
  already correct.)
  ✅ CONTEXT's item-4 and item-6 root causes both **verified exactly**: `Info.plist:44-49` lists two
  landscape values with **no** JS orientation code anywhere and **no** `~ipad` variant key (a clean
  2-line deletion); and neither `PanResponder` in `VelocityChart.js` sets
  `onPanResponderTerminationRequest`. `expo-file-system` is **fine** — absent from `package.json` but
  a transitive dep of `expo` (~56.0.8) and present in the lockfile, so H6 stands as written.
  Plan = rasterizer → **decision checkpoint** (background + fill fraction, judged at 120 px) →
  install → plist edit → **human-verify gated on an EAS build** (⚠ `npx expo-doctor` first, standing
  SDK-56 rule). No commit in either repo; no build spent by the plan itself — batching it with the
  later Phase-84 plans is a decision left to the checkpoint.
  ✅ **APPLY 2026-08-30 — decision checkpoint answered `approve`: background `#FFFFFF`, fill 80%**
  (the rasterizer's shipped defaults; `BG`/`FILL` at `scratch/make_app_icons.py:31` are the one-line
  knobs if it is ever revisited). Tasks 1–3 all landed: rasterizer byte-deterministic across three
  runs; three opaque `RGB` PNGs installed at 1024/180/120 with no tRNS; `Contents.json`
  byte-identical to HEAD; `Info.plist` diff is `0 insertions, 2 deletions` and `plistlib` reads
  `UISupportedInterfaceOrientations == ['UIInterfaceOrientationPortrait']` with no `~ipad` variant.
  Zero `.js` in the plan's diff; the four Phase-74 entries (`CLAUDE.md`, `CycleCharts.js`,
  `BleContext.js`, `RecordScreen.js`) are present and untouched. Nothing staged, nothing committed.
  ⚠ **AC-3 deviation — the AC is unachievable, not the code.** Its aspect clause demands ≤1 part in
  1000; 1024 hits 0.0137% but 180/120 land at 0.2252%. Brute-forcing every integer `(w,h)` inside
  the AC's own ±1% fill window gives a floor of **0.164% @ 180** and **0.180% @ 120** — integer pixel
  dimensions cannot do better at that scale (144 px wide at 1.0458:1 wants h=137.69, and neither 137
  nor 138 is within 0.1%). Centring and fill clauses pass. Loosen the AC at UNIFY; do not chase it.
  ⚠ **Windows/OneDrive staleness bit TWICE during APPLY, and the second time matters.** (a) `ls` +
  `git status` of `AppIcon.appiconset/` returned the May-21 placeholders minutes after the install had
  written the new bytes. (b) The tree's opening `git status` listed **4** modified files; the closing
  one listed **9**. **Verify mobile-repo state by hashing content, and re-read `git status` at the END
  of a session as well as the start — one opening read is not trustworthy on that tree.**
  🔴 **What (b) surfaced: 84-02's code is ALREADY SUBSTANTIALLY APPLIED in both repos, with no
  SUMMARY.** Mobile: `RecordScreen.js` 120/8 (`goPressPhoneMsRef`/`goSignalSRef`, the `go_signal_s`
  upload param, the silent GO button), `startSequencePrefs.js` 17/4 (key bumped to
  `startSequenceEnabled.v2`, default flipped OFF, fail-closed), `RecordingConfigScreen.js` 24/12
  (`SHOW_START_SEQUENCE_TOGGLE = false`). Backend: `api.py` 20/5 (optional `go_signal_s` form field,
  invalid values dropped-and-logged not 422'd, the stale clock-sync docstring corrected) and
  `tests/test_api.py` 70/4 (four new GO tests). **Its suite was NOT run and its checkpoints were NOT
  answered — do not treat 84-02 as done, and do not re-apply it blind.**
  ⚠ **A commit meant to be "84-01 only" must be path-scoped to `ios/mobile/**`** — a bare
  `git commit -a` in either repo would sweep in 84-02.
  ✅ **Checkpoint 2 answered `defer`: the EAS build was NOT spent.** G1 says all seven Phase-84 items
  need a build anyway, so the working tree holds these two while 84-02/84-03 land and one build carries
  everything. **Owed: `npx expo-doctor` then `eas build --platform ios --profile preview`, then device
  verify** — the icon and the orientation lock are both native and invisible in Metro, a dev-client
  refresh, or any simulator on the old binary. Rotation must be tested with the device's own rotation
  lock OFF or the test proves nothing.
  See [84-01-SUMMARY.md](phases/84-mobile-user-feedback/84-01-SUMMARY.md) ·
  [84-01-PLAN.md](phases/84-mobile-user-feedback/84-01-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-02** (Mobile user feedback — item 7, the coach GO marker + race-start sequence off) —
  **✅ LOOP CLOSED 2026-08-30 — but the APPLY session was NEVER RECORDED and this UNIFY is a
  reconciliation of found work, not a write-up of a session anyone logged.** Loop:
  `PLAN ✓ → APPLY ✓(unrecorded) → UNIFY ✓`. **Cross-repo**
  (`api.py` + `tests/test_api.py` here; `RecordScreen.js` + `startSequencePrefs.js` in
  `swimnetics-mobile`). `depends_on: []` — shares 84-01's EAS build but has **zero file overlap**
  with it. **This plan closes STATE item 15** and fills `reaction_time`, which is **0/99 today**.
  ⚠ **G6 — the "phone↔encoder clock sync is deferred" claim is STALE and has now misled two
  documents** (`api.py:1160` and 75-04's CONTEXT D13). `RecordScreen.js:445-447` has computed it
  since Phase 47: `sessionStartPhoneMs = phoneNowMs − elapsedUs/1000` off the 8-byte META reply, so
  `go_signal_s = (goPressPhoneMs − sessionStartPhoneMs)/1000`. **Only the button was ever missing.**
  Both docstrings are corrected by Task 1.
  ⚠ **G7/G8/G9 — three plumbing facts that shape the mobile half.** META lands at *retrieval*, i.e.
  after the swim, so the press must stash raw `Date.now()` and convert later, at the one site where
  `startPhoneMs` is already in scope. `uploadAndProcess` is a `useCallback` that cannot read state,
  so the value rides **two refs** on the established `videoUriRef` mirror pattern (`:105`) — not new
  state and not a dep-array change. Ordering already works unchanged: META → DUMP → saveCSV →
  uploadAndProcess.
  ⚠ **G10 — disabling the horn is NOT just a default flip.** `startSequencePrefs.js` reads
  `v === null ? true : v === '1'`, so flipping the default misses **everyone who explicitly toggled
  it on** — precisely the users who chose it. The plan **bumps the SecureStore key to
  `startSequenceEnabled.v2`** so every stored value is discarded once. `useStartSequence.js`,
  `StartSequenceOverlay.js` and the audio assets stay **byte-identical** (D9 is "for now").
  ⚠ **Deliberate asymmetry with `PUT /go-signal`:** that endpoint 422s on a bad value because the
  request is only about the GO time. On `/process` the request carries the **swim**, so a negative,
  non-finite or unparseable marker is **dropped and logged, and the session still processes 200**.
  An AC and a test both pin this, because it is the thing a future reader is most likely to
  "fix" into a 422.
  ⚠ **Deploy ordering is a real constraint, not bookkeeping:** backend must be live on Railway
  BEFORE the app that sends the field, or every session recorded in the gap loses its marker with
  no error anywhere — the exact silent-loss shape item 2 exists to hunt.
  ⚠ **G11 — `tests/test_api.py:117` already asserts `phases["go_signal_s"] is None  # no GO button
  yet`.** It keeps passing (the field is optional) but its comment goes false and the populated
  path has no coverage; Task 1 amends it and adds four tests.
  ⚠ **B4 — no backfill is possible.** No stored session carries a GO time and none can be
  reconstructed, so `reaction_time` fills only for sessions recorded *after* this ships — a
  permanent discontinuity that `phaseBaseline.js` (last-5-same-stroke) will see as a metric that
  simply begins one day.
  ⚠ **The metric embeds the coach's own thumb latency** — a within-coach *relative* measure, never
  an absolute block reaction. The plan requires the human-verify to **judge the number, not just its
  presence**; if it reads as noise the fix is a hardware starter signal, not more code.
  ✅ **UNIFY 2026-08-30 — reconciled and verified. 7 AC pass · 1 partial · 1 failed-by-decision ·
  3 clauses deferred to the device.** All three code tasks are applied in both trees.
  **`pytest tests/` = 505 passed** (8 of them this plan's `TestGoSignalOnProcess`; baseline 497 —
  ⚠ STATE's older "485 green" figure is the 75-06 count and is stale). The mobile repo has no test
  runner, so all three changed JS files were parsed with `web/node_modules/typescript` (83-05
  `createRequire` pattern) — clean, with a mutant self-test proving the check non-vacuous.
  ✅ **Decision checkpoint was answered `hide` — in code, not at a recorded checkpoint:**
  `SHOW_START_SEQUENCE_TOGGLE = false` in `RecordingConfigScreen.js`, hook/overlay/audio all intact.
  That answer knowingly **breaks AC-9's four-file blast radius (it is 5) and supersedes AC-7's
  "the toggle can still turn it back on" clause** — both costs the `hide` option itself listed.
  A second, unplanned fix rode along: the `startSequence` seed state was flipped `true → false`
  because the async pref read made the toggle flash on, and a fast Continue could ship
  `startSequence: true` to `RecordScreen` despite a stored OFF.
  ⚠ **One AC-3 exception is deliberate and pinned by a test:** `go_signal_s="banana"` **does** 422 —
  it fails at FastAPI's `Optional[float]` coercion above any handler code. Every value that reaches
  the handler (negative, `nan`, `±inf`) is dropped-and-logged with a 200.
  🔴 **OWED and currently unmet — deploy ordering.** `api.py` is uncommitted and unpushed. If the app
  ships before Railway has the field, every session recorded in the gap loses its marker with **no
  error anywhere** — the exact silent-loss shape item 2 exists to hunt. **Backend push must precede
  the EAS build.** ⚠ A commit scoped to this plan must be **path-scoped**: `RecordScreen.js` also
  carries Phase 74's uncommitted retrieval work (stall 30 s → 8 s, `MAX_RETRIEVAL_ATTEMPTS`, the
  `sendDumpHandshake` retry, post-save `CLEAR`), which is **not** 84-02's.
  ⏸ **Human-verify DEFERRED by standing phase decision** — no Phase-84 item gets a human check until
  the phase is finished and one EAS build carries everything. When it happens, **judge the number,
  not just its presence.**
  See [84-02-SUMMARY.md](phases/84-mobile-user-feedback/84-02-SUMMARY.md) ·
  [84-02-PLAN.md](phases/84-mobile-user-feedback/84-02-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-03** (Mobile user feedback — item 5, indicator formalization) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-31; device verify DEFERRED to the EAS-build batch.** Loop:
  `PLAN ✓ → APPLY ✓ → UNIFY ✓`. ✅ **Committed + pushed 2026-08-31.** Harness re-run at close:
  `node scratch/indicator_check.mjs` = **30/30, exit 0**. → [84-03-SUMMARY.md](phases/84-mobile-user-feedback/84-03-SUMMARY.md).
  ⚠ **STATE's earlier 🔴 NOT APPLIED marker (written 02:31 during the phase-84 UNIFY sweep) was
  overtaken by events, not wrong at the time** — file mtimes put the apply at **02:29–02:35**, i.e.
  straddling that sweep. The `/paul:apply` run at 03:xx therefore **verified rather than re-applied**;
  it wrote no mobile code. Present and green: `src/lib/indicators.js` + `src/components/ui/BandDot.js`
  (new), all four surfaces rewired, and `scratch/indicator_check.mjs` (229 lines) — **`node
  scratch/indicator_check.mjs` = 30/30, exit 0**, including the two static checks the plan expected red
  until Task 3. AC-1…AC-6 satisfied; `BAND_COLOR`/`BAND_FALLBACK`/`VERDICT`/`verdictColor` gone from
  `src/` outside the module; mobile diff = exactly 4 modified + 2 new under `src/`; **no `.py` and no
  `web/` change** (the dirty `api.py`/`tests/test_api.py` are 84-02's `go_signal_s` field — read, not
  assumed). **Owed: AC-7 only** — the Metro trace of one athlete across roster → detail → dashboard →
  report card, plus the judgement call on G27's title-case + "No data" copy change. **User deferred it
  2026-08-30 so the whole phase is verified in one sitting**, alongside 84-01/84-02's build-gated
  checks; this lane needs no EAS build of its own.
  Mobile-repo only, `depends_on: []`,
  **zero file overlap with 84-01 or 84-02** — it is the one Phase-84 lane that touches none of
  `RecordScreen.js` / `BleContext.js` / `CycleCharts.js`, so it is provably clear of the uncommitted
  Phase 74 work. Third of the phase's five plans.
  ⚠ **G20 — the headline finding, and it demotes CONTEXT's diagnosis: `provisional` is STRUCTURALLY
  UNREACHABLE.** `ratings.py:206` is `provisional = (thr_table is None) or (thr is None)`, and both
  halves are dead — `thr_table` falls back to the breaststroke table so it is never None (`:251`), and
  all four pillar primary keys (`mean_vel_ms`, `mean_dps_m`, `cv_arm_peak_vel`, `fatigue_index_pct`)
  **have threshold rows** (`:110,111,133,134`). `tests/test_ratings.py:142` confirms it from the other
  side: the test named `test_provisional_driven_by_missing_threshold` could not construct a provisional
  pillar and asserts `is False` instead. So **CONTEXT's item-5 consequence — "a provisional pillar is
  invisible on the dashboard, colored as if trustworthy on the athlete page, and warned about on the
  report card" — describes a state that cannot occur.** `PillarCards`' provisional banner has never
  rendered; `DashboardScreen`'s provisional exclusion has never excluded anything; `summarize_team`'s
  provisional skip never skips. There is **no device test for provisional**, so the plan proves that
  path on synthetic input in the harness and says so out loud.
  ⚠ **G21 — the band hexes are byte-identical between `ratings.py:33` and `tokens.js:40-42`**
  (`#2d9e5f` / `#d4860a` / `#c0392b`), so `AthleteDetailScreen`'s hardcoded `BAND_COLOR` renders
  **exactly the same pixels** as the three surfaces that read the payload. Real defect, but *latent
  drift*, not a live bug — that screen will not look different afterwards.
  ✅ **G22 — what the user actually saw is four indicator FORMS for one band:** a dot (roster), a
  lowercase word (athlete page), a 0-100 number (dashboard), a title-case word over a meter (report
  card). Fully observable, and the thing D3 settles. That is the item's real justification.
  ✅ **G23 — `unknown` IS reachable** (primary metric missing/NaN, e.g. `cv_arm_peak_vel` on a
  low-cycle session) and is where the four surfaces genuinely diverge — muted dot / `—` / "Not enough
  data" / silently dropped from the average — every one of them reached through an *accidental*
  undefined lookup rather than a defined answer. It is the band the plan can be device-verified against.
  ⚠ **G24 — `rating_colors` has only 3 keys**, so a server-first lookup is not total; the client must
  own the `unknown` color. Do NOT add `unknown` to `RATING_COLORS`.
  ⚠ Also corrected: STATE's own note that `AthletesScreen.js:84` is "already correct" — true for the
  **color source only**; it is provisional-blind and gives `unknown` an accidental answer like the
  other three. And **G28: the mobile repo has no test runner and no lint script** (`package.json`
  scripts = start/android/ios/web), so "verify" cannot mean `npm test` — the plan brings a headless
  harness (`scratch/indicator_check.mjs`, 83-05 / 85-01 precedent) that imports the RN-free module by
  rewriting one specifier into a `data:` module (G29). One user-visible change ships: the athlete
  page's labels go title case and `—` becomes "No data" (G27).
  Plan = shared `src/lib/indicators.js` + `BandDot.js` + harness → **decision checkpoint** (what the
  dashboard needs-attention card leads with; specimen-judged, no build) → rewire roster + athlete page
  (incl. the `ratingColors` nav param 84-01's G-fact 3 called for) → rewire report card + dashboard →
  **human-verify over Metro** (this lane needs no EAS build, unlike 84-01/84-02). No commit in either
  repo; no backend or `web/` change.
  ✅ **DECISION (user-ratified 2026-08-30, APPLY Task 1.5) — Option A:** the dashboard
  needs-attention card **leads with four band dots** (the same `BandDot` the roster draws, in
  `ratings.PILLARS` order) and demotes the 0-100 roll-up to a small secondary `caption`. Provisional
  treatment = **hollow ring in the band color**. This is now the app's single convention: the next
  surface that renders a band follows it. ⚠ The code had already been written to Option A before it
  was put to the user; the ratification is what makes it a decision rather than an accident.
  See [84-03-PLAN.md](phases/84-mobile-user-feedback/84-03-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-04** (Mobile user feedback — item 6, the brush-bar gesture) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-31; device verify DEFERRED to the EAS-build batch (user call).** Loop:
  `PLAN ✓ → APPLY ✓ → UNIFY ✓`. ✅ **Committed + pushed 2026-08-31.** Harness re-run at close:
  `node scratch/gesture_check.mjs` = **7/7, exit 0**. → [84-04-SUMMARY.md](phases/84-mobile-user-feedback/84-04-SUMMARY.md). The earlier 🔴 NOT APPLIED marker (phase-84 UNIFY sweep) is now
  cleared: `onPanResponderTerminationRequest: () => false` is present on **both**
  `PanResponder.create` configs in `VelocityChart.js` (now `:75` body / `:104` brush, each with its
  own reason comment — the two reasons differ and both are written down), and
  `scratch/gesture_check.mjs` (new, 190 lines) is **7/7 PASS, exit 0**, including the mutant
  self-test that strips the property from an in-memory copy and asserts the checks FAIL. Mobile diff
  = **+11 lines, one file, nothing else**; `ReportCardScreen.js` / `VideoOverlayScreen.js` /
  `chartWindow.js` byte-identical to HEAD; `RecordScreen.js` untouched by this plan. TS transpile of
  the JSX: **0 syntactic diagnostics**, so Metro will not choke. AC-1/2/3 satisfied.
  **Owed: AC-4 + AC-5 only** — the on-device drag, and the judgement on G36's two dead zones.
  ⚠ **The plan said this lane needs no EAS build (Metro is enough); the user chose to defer it to
  the build batch anyway**, so it now verifies in one sitting with 84-01/84-02/84-03. → owed item 23.
  ⚠ **Deviation, recorded:** AC-2 names the pre-existing mobile baseline as four Phase-74 files
  (`CLAUDE.md`, `CycleCharts.js`, `BleContext.js`, `RecordScreen.js`). That list was stale by apply
  time — 84-01/84-02/84-03 had landed, so the real baseline is **14 modified + 2 untracked**. The
  substance of AC-2 holds (exactly one file added to that set); the literal enumeration does not.
  Mobile-repo only, `depends_on: []`,
  **one component file**. Fourth of the phase's five plans; chosen next because it is the only
  remaining item that touches neither `RecordScreen.js` (84-02's file, and the mobile repo's
  uncommitted Phase 74 work) nor `CameraView` — items 2 and 3 both do.
  ⚠ **G33 — the bug is WORSE on a surface CONTEXT never examined.** `RecordScreen.js:994` renders the
  post-recording results chart with `interactive brush dark` and **no `onInteractionStart` /
  `onInteractionEnd`**, inside the `ScrollView` at `:919` — so that brush has **no scroll lock at
  all**, where the report card at least sets `scrollEnabled=false`. This is the argument for fixing
  it in `VelocityChart.js` rather than per consumer: one edit repairs a surface nobody reported AND
  keeps the plan out of 84-02's file.
  ✅ **G31 — CONTEXT's root cause verified in RN 0.85.3's own source.** `PanResponder.js:520-522` is
  `onPanResponderTerminationRequest == null ? true : …`, and neither config in `VelocityChart.js`
  (`:75-94` body, `:99-118` brush) sets it. ✅ **G32 — `onShouldBlockNativeResponder` needs no change**
  (`:468-470` already defaults `true` in this RN, not the historical Android-only `false`), so the fix
  is one property per responder, not two.
  ✅ **G34 — CONTEXT open question 6 answered NO, twice over.** `VideoOverlayScreen.js:219` passes
  neither `interactive` nor `brush`, and both responders are gated on exactly those props at render
  (`:343` / `:311`), so **neither responder is attached there**; independently its container is a
  `SafeAreaView` with no `ScrollView` in the file.
  ⚠ **G35 — "make the bar taller" is the obvious wrong fix.** A responder does not lose a gesture by
  leaving the view's bounds; once granted, moves keep arriving and the ONLY loss path is termination.
  `hitSlop` or a bigger `BRUSH_H` would improve the grab, not the drag.
  ⚠ **G36 — the fix's cost is the exact mirror of the bug:** two thin dead zones where a drag that
  *starts* on the 30 px strip (or horizontally on the chart body) can no longer scroll the page until
  the finger lifts. Deliberately **no decision checkpoint** — that is a device-feel judgment nobody
  can make from a chair, so the plan implements D6 as written and puts the tradeoff in the
  human-verify with the directional fallback (`Math.abs(g.dy) > Math.abs(g.dx) * 2`) pre-specified,
  making a "no" a one-line swap instead of a re-plan.
  ⚠ **G38 — the guard is source-level and the plan says so.** `VelocityChart.js` imports
  `react-native` + `react-native-svg`, so 84-03's one-specifier-rewrite trick does not apply; the new
  `scratch/gesture_check.mjs` parses the AST (via `web/node_modules/typescript`, 83-05's
  `createRequire` pattern) and proves it is not vacuous by re-running its checks over a stripped
  copy. It asserts CONFIGURATION, never gesture behaviour — only the device verify proves the drag.
  ✅ **G37 — `VelocityChart.js` is the only file in the app with a `PanResponder`**, so there is no
  second instance of this bug and no shared gesture helper to extract.
  Plan = fix both responders → AST guard with mutant self-test → **human-verify over Metro** (no EAS
  build, no encoder needed). No commit in either repo. ✅ First two tasks done and verified; the
  third (human-verify) is the deferred one.
  **Remaining Phase-84 scope after this: items 2 (upload diagnostic) + 3 (camera options)** — grouped
  into the fifth plan because both touch `RecordScreen.js` and the same `CameraView` JSX, both need
  encoder-plus-camera to verify, and CONTEXT's **D5** already routes `videoQuality` into item 2's
  lane. ⚠ Two facts read while scoping that bear on that plan: expo-camera 56.0.8's iOS default is
  **1080p**, not 4K (`CameraViewModule.swift:184`), so H1's "4K blows past 50 MB" is overstated and
  the TS docstring calling the 16:9 values Android-only is wrong (`CameraRecordingOptions.swift:17-30`
  maps all of them); and **there is no pre-recording camera preview** — `onCameraReady` writes START
  and calls `recordAsync` immediately, so a lens/`facing` control has nowhere safe to live (changing
  `facing` mid-record hits `updateDevice()` and reconfigures the session). Zoom is safe mid-record but
  maps **exponentially** (`videoZoomFactor = maxZoomFactor ^ zoom`, `CameraSessionManager.swift:218`)
  against a device-dependent max that JS cannot read, so "2×/4×" preset labels would be a lie.
  See [84-04-PLAN.md](phases/84-mobile-user-feedback/84-04-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-05** (Mobile user feedback — items 2 upload-failure + 3 camera options) — **✅ APPLY
  code-complete 2026-08-30, **LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-31**; device verify DEFERRED to
  the phase-wide EAS build (user decision), so the human-verify checkpoint is OWED, not approved.**
  Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. ✅ **Committed + pushed 2026-08-31.** Harness re-run at close:
  `node scratch/upload_retry_check.mjs` = **36/36**; `pytest tests/` = **505 passed**.
  → [84-05-SUMMARY.md](phases/84-mobile-user-feedback/84-05-SUMMARY.md).
  Decision at the Task 2 checkpoint: **option-a, `videoQuality="720p"`** (one prop, no codec risk;
  option-b's `videoBitrate` route needs a `getAvailableVideoCodecsAsync()` guard whose failure mode
  is *rejecting `recordAsync`*, on the critical path seconds before START, to buy 67 s vs 72 s).
  Verified here: probe reproduces G1/G2/G4, `upload_retry_check.mjs` **36/36**, `pytest` **505**
  (no drift), Metro bundles (1296 modules), nothing staged or committed in either repo.
  ⚠ **G12 was already stale when written:** 84-03 and 84-04 are **applied**, not merely planned —
  `indicators.js` / `BandDot.js` exist and `VelocityChart.js` carries the gesture edit. Neither was
  touched here; only the AC-8 pre-existing baseline is larger than G12 listed. **The fifth and last
  Phase-84 plan**; cross-repo (two new files in `tools/` + `scratch/` here, five files in
  `swimnetics-mobile`). `depends_on: []`, but ⚠ it **shares `RecordScreen.js` and
  `RecordingConfigScreen.js` with 84-02** (loop closed, device verify still owed, **uncommitted**) —
  there is no path-scoping that separates the two. The backend drift baseline is 84-02's
  **505 passed**, not the older 485/497 figures still quoted above. 84-03 and 84-04 stay independent:
  neither of their files is touched here.
  🔴 **Item 2's cause is now MEASURED, not hypothesised** — a read-only probe was run against the
  live project during planning. **H1 (the 50 MB cap) is CONFIRMED and quantified:** 37 stored phone
  clips give a **median encode rate of 1.38 MB/s** (range 0.90–2.20) at iOS's default 1080p, so the
  cap is reached at **≈36 s of video** — ≈23 s on the fastest device — while `recordAsync` allows
  300 s and auto-stop allows 300 s. The bucket's own distribution shows the ceiling: 97 phone clips,
  **max 48.3 MB, nothing ≥50 MB**, 5 at ≥45 MB. **9 sessions carry the lost-clip fingerprint**
  (`video_origin_s` set, `video_path` NULL); recovering each clip's length from
  `deviceDuration − origin` prices **6 of them at 54–110 MB** and two more inside the device spread,
  so **6–8 of 9 are H1**. One (25 MB, 2026-08-20) is unexplained and stays the residual.
  ✅ **CONTEXT open question 1 answered NO — H2 is REFUTED and Phase 82 is NOT a prerequisite.** A
  1-byte probe object uploaded to the `videos` bucket **succeeded (200)** with the bucket at 2.63 GB
  against the 1 GB free-tier figure, then was deleted. Storage is not rejecting writes.
  ⚠ **The 413 is invisible three times over** (G5): the queue wraps it as `Server error (413)` and
  then **retries it twice over ~13 s** on an outcome that cannot change; `UploadToast.js:66` renders
  a constant `"Video upload failed"` and never shows `job.lastError`; and the chip is dismissible and
  dies with the app. That stack is exactly the reported *"sometimes it just isn't there."*
  ✅ **CONTEXT open question 4 answered "not here"** — queue persistence (H3) stays out of scope:
  G4 attributes 6–8 of 9 losses to H1, and two facts soften H3 materially — `saveVideoToLibrary`
  copies **every** recording to Photos (the footage is never lost, only the attachment), and the web
  annotate page can attach a clip to an existing session (Phase 67). **H4 is not a bug** (the early
  returns happen precisely when there is no `session_id` to attach to); **H6 is not implicated**.
  ⚠ **New fragility found while checking H6:** `expo-file-system` is **absent from `package.json`
  and not hoisted** — it exists only at `node_modules/expo/node_modules/expo-file-system`, yet two
  modules import `expo-file-system/legacy` and it resolves today. The plan reuses the existing
  specifier and adds no new one.
  ✅ **expo-camera's iOS internals decide where each control lives** (read at `~56.0.8`): `zoom` →
  `device.lockForConfiguration()` only, so it is **safe mid-record**; `facing` → session input swap
  and `videoQuality` → `session.beginConfiguration()`, so **both must be set before recording**. And
  there is **no pre-recording preview** (`onCameraReady` writes START and calls `recordAsync` at
  once), so zoom in the live overlay is the only place a coach can actually frame a shot.
  ⚠ **No zoom preset may claim a magnification factor**: `videoZoomFactor = maxZoomFactor ** zoom`
  against a device- and format-dependent maximum JS cannot read, so `zoom=0.5` is 4× on one phone and
  11× on another. Only `zoom=0` is truthfully 1×.
  ⚠ **Two CONTEXT/docs claims corrected:** iOS defaults to **1080p, not 4K** (`CameraViewModule.swift:184`),
  so H1's "4K blows past 50 MB" was overstated — 1080p alone does it; and the TS docstring calling the
  16:9 `videoQuality` values Android-only is **wrong** (`CameraRecordingOptions.swift:17-30` maps all
  of them). `videoBitrate` is honoured **only** when `recordAsync` is also given an available codec —
  which is what makes the resolution-preserving option two coupled changes, not one prop.
  Plan = commit the probe as `tools/probe_video_uploads.py` → **decision checkpoint** on the quality
  lever (720p recommended / 1080p at 6 Mbps / both) → pure `uploadRetry.js` + queue pre-flight size
  refusal + no-retry-on-4xx + a chip that names the reason, guarded by a new headless
  `scratch/upload_retry_check.mjs` that cross-checks the constant against `api.py` → camera controls
  → **build-gated human-verify** (⚠ `expo-doctor` first; needs encoder **plus** camera). No commit in
  either repo; `api.py`'s `MAX_VIDEO_BYTES` deliberately untouched (Phase 82 / Pro territory, and it
  is a RAM guard as well as a quota one).
  See [84-05-PLAN.md](phases/84-mobile-user-feedback/84-05-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 82** (Storage Quota Cleanup) — **🚧 PLAN created 2026-08-27, awaiting APPLY.** Supabase free
  tier is over quota (2.53 GB vs 1 GB cap — ⚠ but the *"new uploads may already be blocked"* worry is
  **REFUTED**: 84-05 planning uploaded and deleted a probe object successfully on 2026-08-30 at
  2.63 GB, so this is a cost/hygiene phase, not an outage). Two leak sources found
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
- **Phase 86** (session clock accuracy — absolute, measured session start) — **📋 86-01 PLAN created
  2026-08-30, APPLY DELIBERATELY GATED.** New phase, not in ROADMAP's 1–85 index and not derived from
  any owed item; it comes out of the SwimClips integration conversation but the first two plans are
  **useful with or without that partnership** — they fix a live bug in the shipped video overlay.
  **The problem:** every sample is stamped `micros()` (boot-relative, wraps at 71.6 min). Absolute time
  exists only as `sessionStartPhoneMs`, computed on the phone from META
  (`RecordScreen.js:457`), used for the local overlay, and **thrown away** — never sent to the server.
  `api.py` never sets `recorded_at`, so the DB default `NOW()` stores **upload time, not swim time**.
  So nothing in the system can answer *"what UTC instant was sample #0?"* — and the phone's own
  mapping carries an **unmeasured 20–80 ms error** (BLE flight time between `sendMeta()` sampling
  `micros()` and iOS firing the callback), which is a real defect in the current overlay.
  ✅ **Firmware is OUT of scope for the whole phase** — verified, not assumed: `sendMeta()` already
  returns `device_now_us` captured at send time (`ESP_32_V5.ino:426`) and `pendingMeta` is a plain
  re-arming flag (`:528`), so **META is idempotent and repeatable**. The round trip runs against the
  existing command; the only blocker is the phone-side `metaSeenRef` one-shot (`RecordScreen.js:440`).
  No flash, no device access, no risk to buffer-and-dump. (Firmware IS git-tracked and not ignored —
  checked, since CODEBASE-AUDIT warns `.gitignore` swallows it.)
  ⚠ **`GET /time` must be UNAUTHENTICATED, and that is correctness, not convenience:** `require_auth`
  (`api.py:74`) calls `sb.auth.get_user(token)` — a **network round trip to Supabase per request**.
  The client uses this endpoint to measure its own RTT and derive clock offset from RTT/2; an
  uncontrolled network call inside the handler lands *inside the interval being measured*. It reads
  like an auth oversight, so the reason is pinned in a code comment and an AC.
  ⚠ **GATED ON PHASE 84.** `api.py` holds **uncommitted 84-02** work in the same `process_session`
  signature 86-01 edits, and `tests/test_api.py` holds its `_post_csv` helper; the mobile repo has 14
  modified files incl. `RecordScreen.js` (84-02's file, and 84-05 is planned against it). Applying now
  entangles two phases in one blob that cannot be committed, deployed or rolled back separately.
  **Prerequisite: Phase 84 committed and its backend deployed.**
  ⚠ **Deploy ordering is load-bearing** (same constraint as 84-02, now doubled): `api.py` live on
  Railway **before** the 86-02 build that sends the fields, or FastAPI drops the unknown form fields
  silently and sessions recorded in the gap lose their start with no error anywhere.
  ⚠ **No backfill is possible** — only the phone can produce this at record time, so all 99 existing
  sessions hold NULL permanently. Consumers must treat NULL as *unknown* and never substitute
  `recorded_at`; same reasoning that forbids backfilling NULL `sample_rate_hz` with 100.
  **Decisions (2026-08-30):** storage = **new columns, BIGINT epoch ms** (`patch_14`, unapplied) rather
  than `metrics_json.phases` — this is session provenance like `sample_rate_hz` (patch_09), not a
  metric, and `phases` is rewritten by recompute and `PUT /annotations`; `recorded_at` semantics
  **deliberately unchanged** (fixing it is a library-wide comparability break → new owed item 22).
  **3 plans: 86-01 backend (written) · 86-02 mobile round-trip + send · 86-03 the tap test.**
  ⚠ **Every accuracy figure in this phase is an ESTIMATE until 86-03 runs** — hence its own plan.
  See [86-01-PLAN.md](phases/86-session-clock-accuracy/86-01-PLAN.md).
- **✅ Working tree RESOLVED 2026-08-29 — committed + pushed as `20c0432`.** The shared-`api.py`
  deadlock (75-06's cycle threading + `PUT /annotations` repair tangled with 82-01's session-delete
  storage cleanup, hunk-level staging unavailable) was broken by taking the **whole tree in one
  commit**: 75-06 + 82-01 + 83-01/02/03 + Phase-80 notebook/scripts + research docs + app icons,
  **74 files**. ⚠ **This pushed to `main`, which auto-deploys** — Railway (api.py: the delete-cleanup
  and the annotations repair) and Vercel (web). Excluded deliberately: `*.html` (already gitignored,
  incl. the 14 MB Phase-80 plotly figures) and `scratch/_cycle*.mjs` (generated copies of
  `web/lib/` sources).
- **Committed history:** 75-03 = `7035157`, Phase 79 = `e1934ba`, Phase 78 + doc reconciliation =
  `76d2a18`, **75-05 report-card UI = `9dd5f7a`**, **75-07 report-card merge = `040ce0d`**, **81-01
  annotate marking = `a73db03`** (frontend only; `.claude/launch.json` is gitignored, stays local),
  **75-06 + 82-01 + 83-01/02/03 whole-tree = `20c0432`** (2026-08-29, pushed to `main`),
  **83-05 overlay panel = `45a858b`** (2026-08-29, pushed to `main` — frontend + docs only, so this
  deploy is Vercel-only; `scratch/_cycle*.mjs` excluded again as generated copies of `web/lib/` sources),
  **Phase 85 marketing home = `a75c373`** (2026-08-29, pushed to `main` — Vercel-only; excludes
  `scratch/_home_session.json`, which carries the source athlete's raw session).
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

**15. 🟡 CODE COMPLETE, NOT SHIPPED (84-02 loop closed 2026-08-30). → [84-02-SUMMARY.md](phases/84-mobile-user-feedback/84-02-SUMMARY.md).**
The GO button, the `/process` form field and the horn-off all exist in the working trees and the
suite is green (505), but **nothing is committed, pushed or built**, so `reaction_time` is still
**0/99** and stays there until the backend is live on Railway *and* the EAS build ships — in that
order, or every session recorded in the gap loses its marker silently. Original entry below.
Backend done in 75-04
(`PUT /sessions/{id}/go-signal`); no UI writes to it, so 0/99 sessions carry a GO time.
⚠ **CORRECTED 2026-08-29 (Phase 84 discuss):** the "also needs the phone↔encoder clock sync that
75-04 deferred" clause is **STALE**. The mobile app has computed that correlation since Phase 47 —
`RecordScreen.js:446` derives `sessionStartPhoneMs = phoneNowMs − elapsedUs/1000` from the 8-byte
META reply, which is encoder t=0 on the phone clock. The only missing piece was ever the button.
**→ PLANNED as [84-02-PLAN.md](phases/84-mobile-user-feedback/84-02-PLAN.md), created 2026-08-29** (Phase 84 item 7, CONTEXT D8–D13): a silent GO marker pressed while recording is
live (both plain and video states), stashed as raw `Date.now()` and converted after META, sent as a
new `/process` form field rather than a follow-up `PUT` (item 2's silent-loss lesson). The Phase-41
race-start sequence is **switched off** with it (D9) — the phone speaker is inaudible poolside, so
the horn was a false affordance; that also removes the negative-`go_signal_s` problem, since the
blare fired *before* `writeCmd('START')`. ⚠ The resulting metric is a **within-coach relative**
number — the coach's thumb latency is inside it — and no backfill is possible.

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

**18. ⚠ Kick bands TILE their window — the first and last are not kicks (found 2026-08-29, 83-05 discuss).**
`segment_kick_bands` builds `edges = [i0, ...troughs..., i1]` ([metrics.py:926](../metrics.py)), so band 1
spans `underwater_start` → first trough (the **push-off glide**) and band N spans last trough →
`stroke_start` (the **breakout transition**). Only the interior bands are true trough-to-trough kicks.
Harmless in 83-02's banded inset — the bands simply tile — but it means the badge's "N kicks" **overcounts
by up to 2**, and any surface that compares bands to each other (83-05's overlay) shows ~2 of ~5 traces
departing for a reason that has nothing to do with the swimmer. ⚠ **CORRECTED 2026-08-29 (83-05 verify):
the "~2 of ~5" figure is worst-case, not typical** — the artifact is a FIXED cost of two bands, so its
visual weight scales inversely with kick count. On the live 15-kick session used for 83-05's AC-8 it is
2 of 15 and the overlay pack read as tight. The badge overcount and the defect are still real.
**Fix:** emit only interior spans and let
the inset draw honest grey for the glide and the breakout edge. Cost is Python + `SCHEMA_VERSION` bump +
backfill across the 63 sessions carrying bands, which is why 83-05 accepts the artifact rather than
absorbing a backend change (83-05 D8).

**19. Peak-alignment as an overlay axis mode (83-05, declined for that plan).** The overlay's
seconds mode anchors every trace on the cycle **start** — a segmentation artifact — so all error
accumulates rightward, which is the fan visible at the right of the underwater pack. Anchoring instead
on each cycle's **velocity peak** (the arm-pull, read from the signal itself) would make the spread real
stroke variation, keep durations honest (no rescaling, unlike normalized), and **largely dissolve 83-05
D5's accepted caveat** that auto-session spread may be segmentation rather than stroke. Align-CENTER was
considered and argued against: the midpoint inherits jitter from both boundaries and corresponds to no
physical event. Cost ~30 lines in `web/lib/cycleTraces.js` + a third toggle state; frontend only, no
schema. User declined for 83-05 — revisit if the pack ever reads too loose to judge.

**20. Portal alert chip still reads "changed (unclear)" while the site says "Normal" (Phase 85 D26/D27).**
The **gate already matches on both surfaces** — `flagVerdict` in `web/lib/phaseValence.js` returns
`flagged: false` for anything inside the band, so an alert already means out-of-range everywhere. What
does NOT match is the wording of the out-of-range-but-direction-ambiguous bucket:
`web/components/portal/phases/AlertSummary.js:38` labels it `changed (unclear)`, and D26 renames it
**"to review"**. One component, one string, deliberately deferred out of Phase 85 (D27, marketing-only
scope). ⚠ Note the marketing page shows **no example of that bucket at all**, an accepted
simplification, so a coach meets it first in the portal.

**21. ❓ Should `ratings.py`'s dead `provisional` flag be re-armed, retired, or left dormant?
(84-03 planning finding, 2026-08-30.)** `provisional = (thr_table is None) or (thr is None)`
(`ratings.py:206`) can never be True: `thr_table` falls back to breaststroke (`:251`) and all four
pillar primary keys have threshold rows. Phase 54 deliberately defused the `seg_reliable` gate that
used to drive it — because it made *every* pillar provisional and silenced the needs-attention list
entirely (`:201-204`) — and kept the parameter so restoring it is one line. Consequence today: three
provisional code paths in the mobile app and one in `summarize_team` are unreachable, and the app has
**no way to tell a coach that a reading came off unvalidated segmentation** even though
`segmentation_reliable` is still hardcoded `False` on the auto path. Three options, all real:
re-arm it and accept that nearly everything reads provisional; retire the flag and delete the dead
branches; or leave it dormant as the landing site for a future finer-grained trust signal. 84-03
handles it correctly by construction and **deliberately does not decide it** — this is a ratings
decision, not an indicator-vocabulary one. Related: [83-03's cut MAD classifier](#) and item 17 both
point the same way, at a cross-session trust baseline rather than a per-session boolean.


**22. ❓ `sessions.recorded_at` stores UPLOAD time, not swim time (found 2026-08-30, Phase 86 planning).**
`api.py` never sets it, so it falls back to the schema default `NOW()` — which fires when the row is
written, not when the swim happened. DATA-FLOW.md documents it as *"when swum"*, so the map and the
behaviour disagree. Usually harmless (upload follows the swim within minutes) but wrong whenever a
session is uploaded late from the queue, and it is the field a reader would reach for first when
looking for absolute time. Phase 86 **deliberately does not fix it**: `recorded_at` is already read by
history and baseline queries across 99 sessions, so changing its meaning is a library-wide
comparability break of the same class as the boundary backfills. 86-01 adds
`session_start_utc_ms` **beside** it rather than correcting it. Open question: correct `recorded_at`
to the true swim time once `session_start_utc_ms` exists (and accept the break), leave it as upload
time and rename/redocument it honestly, or keep both with the distinction written down. ⚠ Note it can
only ever be corrected for sessions recorded **after** Phase 86 ships — the older 99 have no other
record of when they were swum, so any fix creates a permanent discontinuity, the same shape as
`reaction_time` (item 15).

**23. 🟡 84-04's device verify (AC-4 + AC-5) DEFERRED TO THE EAS-BUILD BATCH — user call, 2026-08-30.**
The code is applied and statically green (see Phase 84-04 above): both `VelocityChart` responders now
answer `false` to a termination request, so the parent `ScrollView` can no longer steal a brush drag
mid-gesture. ⚠ **This lane does not technically need a build** — it is pure JS and Metro against the
installed dev build would prove it today — but the user chose to fold it into the one sitting that
verifies 84-01/84-02's genuinely build-gated items, so it now waits on the same build. What is owed
is **two things, not one**: (a) **AC-4**, the symptom is gone — a sideways brush drag survives
vertical drift on both the report card AND the post-recording results chart (G33's unreported
surface, which never had a scroll lock at all); and (b) **AC-5**, a *judgement*, not a pass/fail —
G36's accepted cost is two thin dead zones where a drag that STARTS on the 30 pt strip, or
horizontally on the chart body, can no longer scroll the page until the finger lifts. If that reads
wrong on the device, the fallback is pre-specified and needs no re-plan:
`onPanResponderTerminationRequest: (evt, g) => Math.abs(g.dy) > Math.abs(g.dx) * 2` in each config —
restores page-scroll-from-the-strip at the cost of reintroducing the original bug for a near-vertical
drag. Also worth 10 seconds in the same sitting: confirm **Video Overlay is unchanged** (G34 says it
has no responders attached at all, so any difference there means G34 is wrong).
⚠ `scratch/gesture_check.mjs` proves the CONFIGURATION only. It cannot see a gesture, and its banner
says so — a green run is not evidence for (a) or (b).

**24. 🔴 BLE DISCONNECTS DURING THE DATA DUMP (user-reported 2026-08-31, from pool testing).**
⚠ **This is NOT the failure Phase 74 was built for.** Phase 74 addressed a **stall** ("the end-of-dump
marker never arrived"); the new report is a **disconnect**. Phase 74's retained-buffer work makes a
disconnect *survivable* (a re-issued META → DUMP re-streams the session) but addresses no disconnect
**cause**. Different bug, same phase area.
✅ **Feedback loop BUILT, not yet run: `tools/dump_stress.py`** — drives the real META → DUMP → `0xEE`
handshake from the laptop over `bleak`, N cycles against one buffered session, and reports a
**disconnect rate** plus where each failure died (clustered = deterministic boundary; scattered =
timing/link). It never sends `CLEAR`, so Phase 74's retained buffer means you record **once** and
stress many. Its whole point is the phone-vs-firmware split: *drops here too* → firmware/link;
*clean here* → phone side.
🔴 **Blocked on two things:** (a) this PC's Bluetooth radio is OFF (`MediaTek Bluetooth Adapter →
Present: False`, `bthserv` Stopped) — hardware exists, just switched off; (b) the encoder must be
powered, in range, holding a buffered session.
⚠ **The single most discriminating measurement is a serial line at 115200:**
`[DUMP] Aborted at N/M — disconnected` → the ESP32 is alive and the link dropped cleanly;
a boot banner → the ESP32 **RESET**. Completely different causes.
⚠ **Instrumentation gap:** the firmware has **no `esp_reset_reason()`, no task-watchdog config, and no
brownout handling** (verified by grep) — so a reset is currently only inferable from the boot banner.
Three lines in `setup()` would make it explicit; worth adding at the next flash.
**Ranked, UNTESTED hypotheses** (each falsifiable):
1. **Bluedroid heap starvation** — `BLE_HEAP_HEADROOM` leaves the stack just **32 KB**; the sample
   buffer takes the rest (60 s ≈ 113 KB). *Predicts:* failure rate tracks recording LENGTH. Testable
   with no code change — dump a 10 s session vs a 55 s one.
2. **Supervision timeout** — firmware never calls `updateConnParams`; iOS picks them; 675 back-to-back
   indications with no latency margin + pool-deck 2.4 GHz contention. *Predicts:* failures scatter and
   worsen with distance.
3. **Phone-side re-render storm** — `RecordScreen.js:513` calls `setSampleCount` **once per packet**,
   ~675 React re-renders during a dump. *Predicts:* bleak clean, phone drops. This is the hypothesis
   `dump_stress.py` exists to kill.
4. **The dump loop never yields** — `dumpBuffer()` runs on the Arduino loopTask with no
   `delay`/`vTaskDelay`/`yield`; `loop()` does not return for ~20 s. ⚠ Ranked 4th because
   `notify(false)` blocks on a FreeRTOS semaphore, which *does* yield — the idle task should still feed
   the WDT. *Predicts:* a RESET in the serial log, not `[DUMP] Aborted`.
5. **Brownout** — motor + BLE on one supply. *Predicts:* correlates with battery level; vanishes on USB.
**Next action:** turn Bluetooth on, power the encoder with a buffered session, then
`python tools/dump_stress.py -n 25 --csv scratch/dump_runs.csv`. Belongs with **Phase 74**.

**25. 📋 The post-recording results page duplicates the report card (found 2026-08-31, not scoped).**
`RecordScreen`'s results view and `ReportCardScreen` render the **same Start Phase and Session cards
from effectively copy-pasted JSX**, and duplicate three helpers verbatim (`MetricItem`,
`computeTimeToX`, `TimeToX` — `RecordScreen.js:1184/1198/1210` ↔ `ReportCardScreen.js:625/639/651`).
The Efficiency cards have **already diverged** (Phase 60 replaced four scalars with `CycleCharts` on
the report card only), and the identical D10 comment in both files exists because they *did* disagree
and were synced by hand.
✅ **Two things only the results page can do**, and they are why it should shrink rather than vanish:
it renders from the in-memory `POST /process` response so it still shows a session whose **save
failed**, and its video button uses the **local** `videoUri` rather than the uploaded `video_path`
(which item 24's sibling — 84-05's 50 MB finding — shows is exactly when the upload may not exist yet).
🔴 **The structural cause: the results page has NO route to the report card.** `navigate('ReportCard')`
is called only from `AthleteDetailScreen` / `DashboardScreen` / `SessionHistoryScreen`; RecordScreen's
only `navigate` is to `VideoOverlay`. After a swim the coach's only exit is "Record Again", so the
results page grew a full analysis surface because it was a dead end.
**Sketch:** keep save status + failure paths + local video + capture confirmation; cut Start Phase /
Efficiency / TimeToX / the chart; **add a "View Report Card" button** (that one button is what makes the
cuts safe); extract the shared helpers. Also decide the fate of the ISO timestamp at
`RecordScreen.js:1155` — developer debug output on a coach-facing screen, which **Phase 86 is about to
make load-bearing**.
⚠ **Touches `RecordScreen.js`, so it must land AFTER Phase 84 is committed**, not inside it.


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

- **83-05** (closed 2026-08-29) — Overlay panel: every cycle/kick on one shared axis beneath its inset,
  grey pack + wrapping number gutter with hover-preview and click-to-pin, three-surface highlight,
  seconds/normalized toggle with a gated median line. New `web/lib/cycleTraces.js` + `CycleOverlay.js`;
  the three protected components stayed byte-identical. Two live corrections: gutter wraps at 10 rows,
  and AC-3 was overridden so the breakout row highlights `n: 0`. New reusable **headless render-check
  harness** — the concrete answer to 83-01's "build and lint are blind to this".

- **85** (closed 2026-08-29, phase transitioned 1/1) — Marketing home page rebuilt around the
  race-phase report card, ten weeks after the site last moved. Real trace geometry baked at author
  time into `web/lib/marketingGeom.js` (whole lap decimated 1762 → 882 pts), so a public page makes
  no Supabase call; the Swimnetics mark enters the web surface; `Features.js` + `SampleChart.js`
  retired. New reusable gate `scratch/marketing_render_check.mjs` (45 checks) counts BOTH dash forms
  — the FAQ was 10 `&mdash;` entities to 2 literals, so every character-only grep had read it as
  clean — and headlessly renders the components for the 83-01 silent-failure classes.

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
