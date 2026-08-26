# Phase 75 — Step 3 UI: Metric Consolidation (design context)

**Discussed:** 2026-08-21 (`/paul:discuss`, "concept only" — no surface committed yet)
**Feeds:** Phase 75 Step 3 (report-card UI), which the phase [CONTEXT.md](CONTEXT.md) deliberately deferred.
**Status:** Concept settled on the spine; threshold question left open by design; not yet planned.

This is a **design exploration**, not a build plan. It settles the information architecture so a later
`/paul:plan` (web first, iOS after — per the parent CONTEXT) starts from a decided model.

---

## The actual problem: two taxonomies, not "too many metrics"

There is no single metric set to "simplify." There are **two parallel taxonomies that don't line up**:

1. **The 4 Pillars** (`ratings.py` `PILLARS`): Speed · Stroke length · Consistency · Endurance.
   Banded, trend-aware, roll-up. Organized by *quality*.
2. **The Phase registry** (`phase_metrics.py` `REGISTRY`, ~37 `MetricSpec`s): organized by *race phase* —
   `start` (11) · `underwater` (14) · `swim` (9) · `whole` (4).

A swim does not have "a Speed number." It has speed *at the start*, *underwater*, *at breakout*, *in
steady swim*. The pillars flatten the phase axis; the registry flattens the quality axis. **Consolidation
= choosing which is the spine and which is the filter.**

## Decision (settled 2026-08-21)

**The single-session view's spine is the race-phase timeline: Start → Underwater → Breakout → Swim →
Finish.** Rationale:
- It mirrors the data model we just spent Phases 75–79 building (boundaries + per-phase metrics).
- It's the coach's real mental model of a race.
- It's already a computed metric — the `whole` bucket's `phase_time_budget` / `phase_dist_budget` *are*
  the timeline. The spine is not a new abstraction.

**Pillars survive, repositioned:** Speed/Stroke-length/Consistency/Endurance become the **cross-session /
roster** surface (which is how `roster_metrics.py` already consumes them), not the single-session anatomy.
Single session = phase timeline; athlete-over-time and team triage = pillars.

## Concept (the sketch shown 2026-08-21)

Four layers, alerting-first (progressive disclosure):
1. **Attention headline** — one LLM-phrased sentence naming the biggest deviation ("Underwater was 0.9 m
   shorter than usual"). Phrasing layer only, per the Attention-Allocation doctrine.
2. **Race timeline strip** — 5 segments sized by distance budget; the deviating phase is tinted; breakout
   is a thin marker at the UW→Swim boundary.
3. **Contrast marks inside the flagged phase** — each headline metric as a bullet/sparkline: today's value
   + the athlete's own recent band + median tick. Deviation lights up. **No absolute threshold needed —
   the band is the baseline.** This is the display doctrine (STATE item 8) drawn literally.
4. **Drill-down** — the full per-phase registry on demand, never on the first screen.

## The radar / polygon (idea from the attached "Specialty" chart) — parked, with reasons

- **Structural conflict:** a metrics radar requires every axis normalized to a shared 0→100 "good" scale.
  The display doctrine is explicitly *no absolute thresholds*, and the only thresholds that exist are
  breaststroke-derived + unvalidated for the other 3 strokes. A radar is the one chart the doctrine forbids.
- **Encoding flaws:** enclosed area is an artifact of axis order; axes aren't commensurable (DPS good-high,
  fatigue good-low); it can't show a delta (trend is the product).
- **Where it's legitimately good:** the attached chart is a *categorical fingerprint* (Free/Back/Breast/
  Fly/IM — commensurable, comparable across swimmers). That's an **athlete-profile "specialty" card**, not
  a per-session dashboard. ⚠ But it's fed by *per-event race performance*, which this tool does not
  measure (it captures tethered encoder velocity, not meet results) — so it has **no inputs today**.
  Park it; revisit only if event-time data is ever added.

## Open question left open by design: absolute thresholds — contrast-only vs norms

The user chose "argue both." Both were argued; not decided here.

- **Contrast-only (recommended default + first build):** every mark vs the athlete's own recent swims.
  Shippable day one, honest (we've measured this athlete, not the population), doctrine-consistent, dodges
  the unvalidated-thresholds landmine. Cost: can't answer "is 4.1 m *good*?" in absolute terms; **shows a
  brand-new athlete nothing** (no baseline).
- **Norms (absolute scale):** matches how coaches/parents think ("good for a 13-year-old"), gives the
  radar honest axes, interpretable without history, competitive vs TritonWear benchmarking. Cost is
  structural: **no normative dataset exists** (78-01: 4 annotated swimmers, ~15 humans total), units are
  tethered-encoder velocity (not comparable to published age-group standards), so norms = a data-collection
  program, not a UI toggle. Adjacent to Phase 53.

**Recommendation:** build contrast-only first; treat "does an absolute scale exist" as a
data-acquisition decision gated on a corpus, not a display choice. **The timeline spine is identical under
either**, so the UI is not blocked on this call.

## For the eventual plan to resolve

- **Metric → phase headline mapping:** of the ~37 registry specs, which 1–2 per phase are the *headline*
  contrast marks vs. drill-down? (Coarsely: Start → peak vel / glide; Underwater → uw_distance /
  dist_per_kick / breakout_vel; Swim → ivv / splits / sr_dps_coupling; Whole → the budget strip itself.)
- **Baseline definition for the band:** last N same-stroke sessions? Same as `ratings.py`'s baseline
  (athlete's previous same-stroke session)? Needs one source of truth.
- **New-athlete / no-baseline empty state** — the contrast model's real weak spot.
- **Reliability surfacing:** `segmentation_reliable` is hardcoded `False` on the auto path; back/breast
  breakout is unvalidated (STATE items 10–11). The UI must not present unvalidated phases as trusted.
- **Surface commitment:** concept-only for now; parent CONTEXT says web first, iOS after.
