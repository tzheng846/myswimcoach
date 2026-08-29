# Phase Context — 83-05

**Phase:** 83 — Per-Cycle / Per-Kick Trace Coloring · **Plan 83-05: cycle/kick OVERLAY panel**
**Generated:** 2026-08-29 (`/paul:discuss`, AskUserQuestion ×3, 11 decisions)
**Status:** Ready for planning
**Stacks on:** 83-01 / 83-02 / 83-03, all closed and committed in `20c0432`.
**Numbering:** **83-04 stays "inset window framing"** (context padding + minimum span, still unplanned).
This is **83-05**. The two are independent — see R5.

---

## Why now

83-03 tried to *classify* an odd stroke and the classification was **measured and cut**: at a median of
7 cycles per lap the MAD gate fired on 75% of sessions at `k=3.0` and still 39% at an absurd `k=8.0`.
No `k` separates a clean swim from a ragged one, because a within-lap outlier test on n=7 is not an
abnormality test.

The correct response to "no threshold exists" is not a better threshold. It is to **stop asserting and
start showing**. Lay every cycle on one axis and let the coach's eye do what the statistic cannot at
n=7.

User ask (verbatim intent): *"lay all the individual stroke/kick on top of each other... put it right
next to the phase graphs... numbers on the side so the user can hover over the numbers, and the
according wave will highlight and others will dim."*

---

## Rating of the proposal — 8.5 / 10

**Why it's right:**

1. **It is the honest answer to 83-03's own measurement**, not a retreat from it.
2. **Zero backend.** `PhaseReportCard` already holds `velocity`, `fsHz`, `cycles`,
   `phases.kick_bands`, `boundaries`. No schema bump, no backfill, no Python — compare to owed item 17,
   which needs prior sessions' velocity arrays in the browser.
3. **Phase alignment is free.** Both `segment_cycles_trough` and `segment_kick_bands` (83-02 D4) cut
   **trough-to-trough**, so every trace already starts at a local minimum. Overlay plots normally die
   on alignment; this one is aligned by construction.
4. **`cycleShape.js` is resurrected for the part that was never wrong** — `resample()` (duration-
   invariant, 15/15 scratch checks) and the pointwise median. Only the MAD gate stays parked.
5. **The hover plumbing already exists.** `hoverCycle`/`setHoverCycle` is lifted into
   `PhaseReportCard` and drives inset ↔ `CycleCharts` bidirectionally. A third surface joins free.

**The 1.5 held back:**

- **On AUTO sessions the overlay shows the segmenter, not the swimmer.** Boundary F1 = 0.458; 47 of 90
  sessions are auto. A ragged pack may be ragged *cuts*. Accepted with a badge (D5) rather than gated —
  unlike 83-03's gold band, the overlay asserts nothing on its own, it only shows what was cut.
- **The kick pack ships with a known artifact** (D8) — accepted deliberately, owed upstream.

---

## Grounded state (read from code, 2026-08-29)

### Everything the panel needs is already in the browser
`PhaseReportCard` receives `velocity`, `fsHz`, `cycles`, `phases`, `session`, `unit`,
`segmentationReliable`. `phases.kick_bands` (schema 4) is `[{kick_num, peak_idx, start_idx, end_idx,
duration_s}]`; `metrics_json.cycles` is `[{cycle_num, peak_idx, start_idx, end_idx}]`. Both in **sample
indices at the session's own `sample_rate_hz`** — never assume 100 Hz.

### `cycleShape.js` is parked but correct
`resample(velocity, start, end, points)` returns exactly `points` linearly-interpolated values, or
**null** if the span is <2 samples or carries **any** non-finite value (a dropout must exclude a band,
never be filled). The pointwise-median loop is guarded by `MIN_ITEMS = 5`. Only `analyzeShapes`'
one-sided MAD gate is the measured failure.

### ⚠ FINDING — kick bands TILE their window; stroke cycles do not
`segment_kick_bands` builds `edges = [i0, ...troughs..., i1]` ([metrics.py:926](../../../metrics.py)),
so the bands tile the underwater window exactly:
- **band 1** = `underwater_start` → first trough = the **push-off glide**, not a kick
- **band N** = last trough → `stroke_start` = the **breakout transition**, not a kick
- only the **interior** bands are true trough-to-trough kicks

Harmless in the banded inset (bands just tile). In an **overlay** it means **~2 of a typical 5 traces
are systematically odd-shaped by construction, every session** — the same false-signal class the
breakout exclusion (D6) exists to remove. Stroke cycles are unaffected: they are real segments with
gaps, which is exactly why 83-03 measured a 1.04 s gap before cycle 1.

### `PhaseVelocity.js` is deliberately not the home for this
83-02 already broke an AC by editing it, and 83-01 lost a whole verify cycle to a **shadowed prop**
inside its `geom`. The overlay is a **new component**; `PhaseVelocity` stays untouched (A5).

---

## Decisions (user, 2026-08-29)

**D1 — X-axis: real seconds by DEFAULT, with a normalized (% of cycle) TOGGLE.**
Seconds mode: each trace starts at `x = 0` and ends at its own true duration, longest cycle sets the
axis width — shape **and** tempo in one picture. Normalized mode: `cycleShape.resample()` to a fixed
grid — shape directly comparable, duration deliberately invisible (it is reported by `CycleCharts`
anyway). Two geom paths, one piece of state.

**D2 — Placement: DIRECTLY BELOW the inset, inside the SAME bordered box, full width.**
Not side-by-side (would squeeze the 1000-wide inset to ~660 and force a responsive fork). The number
gutter runs down the **left** of the overlay. The two charts read as one unit.

**D3 — Traces are ALL NEUTRAL GREY; the active one takes the accent and the rest dim.**
`var(--color-cycle-idle)` for the pack, `var(--color-cycle-a)` + heavier stroke for the active trace,
the others dropped to low opacity. Rejected: alternating blue/purple (7+ lines becomes two
indistinguishable clumps) and a sequential early→late ramp (offered for its free fatigue signal,
declined). **Consequence to accept:** a trace carries no identity until hovered, so the inset says
"purple" where the overlay says "grey" — the shared **number** is the identity, not the colour.

**D4 — Scope: Swimming (cycles) AND Underwater (kicks).**
Breaststroke Underwater needs no new gate — `kick_bands` is already `[]` there (pulldown, not dolphin
kicks), so the panel simply does not render. Start and Whole get nothing.

**D5 — Renders on BOTH annotated and auto sessions, carrying the existing `annotated|auto` badge.**
No caution copy, no gate. Rationale: the overlay makes no claim of its own, it only shows what was cut
— unlike 83-03's gold band, which asserted "this span is the breakout." ⚠ Known cost: on the 47 auto
sessions, spread may be segmentation rather than stroke and nothing visually separates the two.

**D6 — The BREAKOUT trace is EXCLUDED, and its absence is noted in the gutter.**
The synthetic `n: 0` gold band is one pull out of streamline — structurally unlike every stroke after
it, so it would be a permanent "odd wave," the exact noise the panel exists to remove. The gutter
carries a **dimmed, non-interactive `0 · breakout` row** above `1, 2, 3…` so the missing trace is
accounted for exactly where the coach counts. Numbering below still starts at 1, matching the inset
and `CycleCharts`.

**D7 — Reference median line: NORMALIZED MODE ONLY.**
A pointwise median needs a common x-grid, which only normalized mode has; drawing it in seconds mode
would require a constructed duration that corresponds to no real cycle. Drawn thick and faint beneath
the pack. Uses `cycleShape`'s existing median loop, **not** `analyzeShapes`' gate.

**D8 — Kick overlay INCLUDES ALL bands for now, including the two window-clamped edges; the upstream
fix is written up as an owed item.** The clean fix is to re-cut `segment_kick_bands` to emit only
interior trough-to-trough spans and stop tiling, letting the inset show honest grey for the glide and
the breakout transition — but that is Python + a schema bump + a backfill across 63 sessions, which
would turn a frontend plan into a backend one. Deferred consciously, **not** overlooked.
**→ new STATE owed item.**

**D9 — Interaction: hover to preview, CLICK TO PIN.**
Click a gutter number to lock the highlight so the coach can look away, scroll, or point at the
screen; click it again to release. This is also the only affordance that works on touch, where hover
has no analog. Resolution rule: **`active = hovered ?? pinned`** — hovering another number previews it
without destroying the pin.

**D10 — The overlay joins the EXISTING lifted hover state; it does not own a second one.**
Swimming becomes three-way: gutter number ↔ inset band ↔ point in all four `CycleCharts` panels, all
off `hoverCycle`. Underwater stays two-way off `hoverKick` (it has no `CycleCharts` partner).

**D11 — Owed item 17 (cross-session shape baseline) is DEFERRED, not retired.**
Different questions: the overlay answers *"which stroke looks off in THIS lap"* by eye; item 17
answers *"does this lap look off versus his history"* automatically, which is the SPC posture the
product doctrine asks for and needs backend work. `cycleShape.js` becomes **partly wired** —
`resample()` + the median feed normalized mode; the MAD gate stays parked and unimported.

---

## Assumptions carried into planning (stated, not asked — correct me in PLAN)

- **A1 — Normalization is X-ONLY.** Y stays **raw m/s on a 0-based scale**, sharing the inset's
  `niceMax` over the same phase window so the two stacked charts read as one vertical scale.
  Normalizing Y would hide fatigue, which is real signal.
- **A2 — No trace cap.** 618 cycles across 90 sessions ≈ 6.9 mean; kick counts are single digit. If a
  long swim ever exceeds ~20, revisit — do not build a cap speculatively.
- **A3 — Toggle state is panel-local and NOT persisted.** Default = seconds on every render.
- **A4 — `metrics_json` is untouched.** No new persisted field, no `SCHEMA_VERSION` bump, no backfill,
  no Python. If PLAN finds otherwise, that is a scope change worth surfacing.
- **A5 — `PhaseVelocity.js` is NOT modified.** New component (working name `CycleOverlay`) + whatever
  small pure helper it needs. `web/lib/cycleBands.js` also stays untouched — the overlay reads the
  stored arrays directly, since it needs *unclamped* spans, not window-clipped bands.
- **A6 — Colour tokens.** The pack reuses the existing `--color-cycle-idle` / `-a`. **Any NEW token
  read only via `var()` in an SVG attribute MUST go in the `@theme static` block**
  ([web/app/globals.css:68](../../../web/app/globals.css)) — Tailwind v4 tree-shakes plain `@theme`
  tokens no utility class references, which is the 83-01 bug that rendered every band invisible and is
  invisible to both `next build` and `eslint`.
- **A7 — `cycleShape.js`'s header comment must be UPDATED when it is partly wired.** It currently
  states "PARKED, NOT WIRED. Nothing imports this." Leaving that false is the same defect class as
  `cycleBands.js:9`, which 83-03 had to come back and fix.

---

## Success criteria

1. The Swimming section renders an overlay panel beneath its inset, inside the same box: one grey
   trace per stored cycle, a left gutter of numbers, seconds x-axis by default.
2. Hovering gutter number `n` accents that trace, dims the rest, **and** simultaneously highlights band
   `n` on the inset and point `n` in all four `CycleCharts` panels. Clicking pins it; clicking again
   releases; hovering another previews without clearing the pin.
3. The breakout is absent from the pack and present in the gutter as a dimmed, inert `0 · breakout`
   row. Cycle numbering still starts at 1 and matches the inset.
4. Toggling to normalized redraws every trace to a common grid and adds the thick faint median line.
   Toggling back restores true durations. **The gutter's numbers and their order are identical in both
   modes** (see R2).
5. The Underwater section renders the same panel from `phases.kick_bands` — including its two
   window-clamped edge bands (D8) — and renders **nothing** for breaststroke.
6. The panel appears on both annotated and auto sessions and carries the existing `annotated|auto` /
   `auto` badge.
7. `npm run build` clean. **Suite stays 497** — no Python is touched.
8. Verified by an actual **render check on a live session**, not by build+lint. 83-01 shipped two
   silent-failure bugs that both passed `next build` and `eslint`.

---

## Risks / watch items

- **R1 — the kick-edge artifact ships (D8).** ~2 of ~5 underwater traces will always depart from the
  pack for a reason that has nothing to do with the swimmer. Accepted; **must be written into STATE as
  an owed item**, not left in this file only.
- **R2 — the two modes can disagree about which traces EXIST.** `resample()` returns null on any
  non-finite sample in the span, so a dropout-carrying cycle silently vanishes from normalized mode —
  while seconds mode still draws it (`buildPath` just lifts the pen across the gap). PLAN must decide
  the rule and keep the **gutter stable across modes** (a number that disappears mid-toggle is worse
  than a trace that does). Suggested: the gutter is built once from the stored array; a trace
  unavailable in the current mode renders its row dimmed, like the breakout.
- **R3 — median needs `MIN_ITEMS = 5` usable traces.** A 3-cycle lap gets a pack and no median line.
  That must degrade silently, not render an empty or a 2-sample "median".
- **R4 — hover/pin re-render churn.** `CycleCharts` is recharts and now re-renders on every mouse move
  across a third surface. 83's original R4 flagged this; memoize and watch for stutter.
- **R5 — 83-04 (inset window framing) is independent but adjacent.** It pads the inset's *window*; the
  overlay reads *stored spans* and clamps nothing, so padding cannot move a trace. Neither blocks the
  other; whichever lands second must not assume the other's shape.
- **R6 — three surfaces now share one hover key.** `n` is `cycle_num + 1` in `cycleBands`, `i + 1` in
  `CycleCharts`, and must be the same in the gutter. A fourth consumer is where an off-by-one gets
  introduced.

---
*Next: `/paul:plan`*
