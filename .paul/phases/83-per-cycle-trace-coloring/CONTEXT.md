# Phase Context

**Phase:** 83 — Per-Cycle / Per-Kick Trace Coloring (phase-section insets)
**Generated:** 2026-08-28 (`/paul:discuss`, AskUserQuestion ×3, 12 decisions)
**Status:** Ready for planning
**Stacks on:** Phase 75-06 (Swim + Whole metric batch) — **applied but uncommitted** in the working
tree. This phase builds on that tree and shares its owed backfill run (D11).
**Not to be confused with:** 75-09 (unified interactive phase-*tinted* trace — whole-swim, colored by
race phase). This phase colors *individual cycles and kicks* inside two phase insets.

---

## Why now

The report card's charts draw one continuous line. A coach cannot see where one stroke cycle ends and
the next begins, nor count downkicks off the trace. Every per-cycle number in `CycleCharts` and every
kick metric in the Underwater section is computed from boundaries the chart never shows — so the
numbers are unauditable by eye. Phase 75-05/75-07 built the phase-section insets; they are the natural
place to make segmentation *visible*.

User ask (verbatim intent): distinguish each individual kick / stroke cycle by giving it a different
trace color, **alternating blue and purple**; **prioritize human annotation, auto segmentation as
backup**.

---

## Grounded state (read from code, 2026-08-28)

### Stroke cycles — annotation-first is ALREADY FREE
`metrics_json.cycles` = `[{cycle_num, peak_idx, start_idx, end_idx}]` in **sample indices**
([metrics.py:131](../../../metrics.py)). `PUT /sessions/{id}/annotations` overwrites it with the
coach's cycles via `annotation_to_overrides` → `compute_session_metrics(manual=...)`, and
`segmentation_reliable` flips `True` **only** on that path (`PIPELINE.md §5`; hardcoded `False`
otherwise). **So "human first, auto fallback" needs NO new precedence logic** — read `metrics.cycles`,
read `segmentation_reliable` for provenance. This mirrors 75-06's `PhaseContext.cycles` finding.

### Underwater kicks — a real gap, not a free ride
`metrics.detect_underwater_kicks` ([metrics.py:847](../../../metrics.py)) returns **peak indices only**
— points, not segments — computed **on the fly** inside `phase_metrics._kick_analysis`
([phase_metrics.py:341](../../../phase_metrics.py)) and **never persisted**. There is **no human
kick-marking path** at all (that is 81-02, still owed). Consequences:

1. Per-kick bands need **edges invented** from peaks (D4).
2. The data needs **storage + transport** to reach the browser (D5).
3. Kicks are **auto-only for now** — no ground truth to prioritize. When 81-02 lands human kick marks,
   the same precedence pattern as cycles applies; this phase should not block it.
4. **Gated off for breaststroke** — `_kick_analysis` returns `None` when
   `stroke_type == "breaststroke"` because its underwater is the *pulldown*, not dolphin kicks
   ([phase_metrics.py:347](../../../phase_metrics.py)). The coloring must respect that gate (D9).

### Chart tech — the scope choice removes two problems

| Surface | Tech | Multi-color cost |
|---|---|---|
| `PhaseVelocity` insets (**IN SCOPE**) | hand-rolled SVG, `buildPath` per window | trivial — emit N paths |
| `VelocityChart` / `AccelerationChart` (out) | **recharts `<Line>`** | one stroke color per series; needs N masked series or an SVG rewrite |
| `TraceOverlay` (out) | hand-rolled SVG, imperative viewBox pan | cheap, but not asked for |

`PhaseVelocity` also takes **no `tracePrefs` color prop** (it uses `var(--color-primary)`), whereas
`VelocityChart` does — so scoping to insets **eliminates the conflict with the user's trace color
picker** entirely. Blue/purple can be hardcoded tokens without overriding anyone's preference.

### Where the insets live
`PhaseReportCard` renders one section per phase, each with `<PhaseVelocity variant="inset"
window={[i0,i1]} />` on top ([PhaseReportCard.js:361](../../../web/components/portal/phases/PhaseReportCard.js)),
strips in two columns, and — for Swimming only — `CycleCharts` beneath the strips (75-06 D10).
`CycleCharts` = 4 panels: Distance per Stroke, Coast, Cycle Duration, Arm Peak Velocity. It **also**
renders in the legacy no-`phases` fallback branch, where there is no inset partner.

---

## Decisions (user, 2026-08-28)

**D1 — Surface scope = PHASE SECTION INSETS ONLY.** The Underwater inset and the Swimming inset. **Out
of scope:** the report card's recharts velocity/acceleration pair, `TraceOverlay` (annotate + video
pages), the Compare page, the Whole-race inset, and iOS. *Rationale: the insets are hand-rolled SVG and
picker-free; the recharts pair would need a rewrite for a secondary payoff.*

**D2 — One cycle = one band.** Band spans `[start_idx, end_idx]` from `metrics_json.cycles`. **Not**
one band per arm entry. This keeps colors and every per-cycle number 1:1 — band *n* is exactly the
point *n* in all four `CycleCharts` panels, which is what makes D8's cross-highlight coherent.
*(Note: for free/back/fly a coach mark = one arm entry and a cycle = 2 marks — Phase 80's reframe.
Per-stroke banding was offered and declined.)*

**D3 — Everything outside a cycle/kick band is NEUTRAL GREY.** Dive, underwater glide, inter-cycle
gaps, post-finish. The segmented region should pop; un-segmented signal should read as "not a cycle."

**D4 — Kick band edges = TROUGH-TO-TROUGH.** Split at the velocity minimum between consecutive
detected peaks — the same rule stroke cycles already use (`segment_cycles_trough`). Each band is one
full kick with its peak centered. Pure `argmin` between peaks; **no new tuning constants**. First
band's leading edge and last band's trailing edge clamp to the underwater window bounds.

**D5 — Persist as `metrics_json.kicks`, shape mirroring `cycles`:**
`[{kick_num, peak_idx, start_idx, end_idx}]`. jsonb — **no migration**. Chosen over nesting inside
`metrics_json.phases.underwater` (that object is a metrics-registry payload; raw index arrays are a
different kind of thing) and over a new column.

**D6 — Colors: blue / purple alternating, PLUS a thin boundary tick at every band edge.** The tick is
an accessibility requirement, not decoration: blue and purple differ mainly in the red channel, so
protanopic/deuteranopic viewers may see them as near-identical and lose the ability to *count* bands.
The tick makes bands countable by structure regardless of hue, and doubles as a visible cycle-boundary
marker. Hue pair kept as asked — the tick is the mitigation.

**D7 — Outlier flag: CYCLE DURATION, amber OUTLINE over the band.** The cycle whose duration sits
furthest from the session median gets an amber outline/glow drawn *on top of* its blue or purple fill,
so the alternation stays readable and countable. Single dimension (rhythm — the clearest coaching
signal); a 4-metric net was offered and declined as over-flagging. **Within-athlete contrast only, no
absolute thresholds** (standing display doctrine). Kick analog = **inter-kick interval**.

**D8 — Cross-highlight: BIDIRECTIONAL, all 4 `CycleCharts` panels.** Hover a Swimming inset band → that
cycle's point lights in all four panels; hover a chart point → its band lights on the inset. Requires
hover state lifted into `PhaseReportCard`. **Degrades to no-op** in the legacy no-`phases` branch,
where `CycleCharts` has no inset partner.

**D9 — Count badge on each inset, carrying PROVENANCE.** e.g. `14 cycles · annotated` /
`9 kicks · auto`. This is where human-vs-auto surfaces on the chart itself — **a deliberate, scoped
exception to 75-06 D3** (which put provenance in the hover overlay only), because the coloring *is* the
segmentation and a coach must know whether they are looking at their own marks. **Breaststroke
Underwater inset: single-color, badge reads that its underwater is the pulldown, no kicks** (gate from
`_kick_analysis`).

**D10 — Per-band hover readout.** Hover a band → cycle number, duration, distance-per-stroke, peak
velocity (all already in `metrics_json.cycles`). Reuses the existing `HoverExplain` overlay pattern.
Per D8's chosen option, this is the *same* hover event that drives the cross-highlight.

**D11 — New Phase 83, stacked on the uncommitted 75-06 tree; ONE shared backfill.** Build on the
working tree as-is. A single `python tools/backfill_phases.py --apply` at the end populates 75-06's
Start/Swim/Whole metrics **and** the new `metrics_json.kicks` together. *Ordering constraint: the D5
backend persist must land BEFORE that run.* Tracked as its own phase number (not 75-10) so it stays
reviewable on its own alongside the queued 75-08 / 75-09.

**D12 — Color always renders regardless of provenance.** Auto cycles/kicks are colored the same as
annotated ones; the badge (D9) carries the caveat. This follows 75-06 D8's shape (provisional data is
*flagged*, not hidden) — but note color is not valence, so unlike D8 nothing is suppressed.

---

## Assumptions carried into planning (stated, not asked — correct me in PLAN)

- **A1** — `metrics_json.kicks` is written by the same seam that writes `phases`
  (`_rebuild_phases` / `POST /sessions/{id}/recompute`), so `/process`, recompute, and the backfill all
  populate it by one code path.
- **A2** — `PUT /annotations`' phases-drop repair (75-06 D4) must also preserve `kicks`, or annotating a
  session would silently erase its kick bands. **Verify this in PLAN** — same defect class.
- **A3** — The Start inset stays single-color (it contains no cycles or kicks by definition).
- **A4** — The Whole-race inset is untouched this phase (offered, not selected).
- **A5** — Blue/purple/grey/amber ship as **theme tokens**, defined for the portal's dark theme.

---

## Success criteria

1. Swimming inset draws one alternating blue/purple band per `metrics_json.cycles` entry, grey
   elsewhere, with a boundary tick at each edge.
2. Underwater inset does the same per kick — **except breaststroke**, which stays single-color.
3. Band count on an **annotated** session equals the coach's cycle count exactly; badge reads
   `annotated`. On an un-annotated session it equals the auto count; badge reads `auto`.
4. `metrics_json.kicks` is populated by `/process`, `POST /recompute`, and the backfill — and
   **survives** a `PUT /annotations` round-trip (A2).
5. Hovering a Swimming band shows that cycle's four numbers and simultaneously highlights its point in
   all four `CycleCharts` panels; hovering a chart point highlights the band.
6. The longest-deviation cycle carries an amber outline over (not instead of) its fill.
7. Suite green; `npm run build` clean.

## Risks / watch items

- **R1 — `metrics_json` size.** `cycles` + `kicks` on a long session adds rows to a jsonb blob already
  carrying velocity/distance/accel profiles. Kick counts are small (single digits), so low risk, but
  worth a sanity check in PLAN.
- **R2 — trough-derivation degenerates on 0 or 1 kicks.** A glide-only underwater returns an EMPTY peak
  array (documented in the detector); one peak yields no interior trough. Both must produce *no bands*,
  not a crash or a full-window band.
- **R3 — index-space drift.** Cycle/kick indices are in **decimated sample space at the session's own
  `sample_rate_hz`** — never assume 100 Hz. The insets already take `fsHz`; the new kick path must too.
- **R4 — cross-highlight state churn.** Lifting hover into `PhaseReportCard` re-renders the section on
  every mouse move. `CycleCharts` is recharts; watch for stutter and memoize.
- **R5 — 75-06 is uncommitted.** This phase's diff sits on top of unreviewed work. If 75-06 is revised
  during its UNIFY, this phase's `PhaseReportCard` edits may conflict.

---
*Next: `/paul:plan`*
