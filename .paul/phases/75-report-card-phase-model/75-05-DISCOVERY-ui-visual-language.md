---
phase: 75-report-card-phase-model (Step-3 UI → visual language)
topic: How to deliver 37 race-phase metrics visually, no walls of numbers — the encoding vocabulary
depth: deep
confidence: HIGH
created: 2026-08-22
---

# Discovery: The visual language for the report-card dashboard

**Recommendation:** Don't design 37 charts. Design **one dominant mark** (a horizontal
*contrast bar* = position-on-a-common-scale: today's dot + the athlete's own recent band + median
tick + diverging deviation tint) rendered as **small multiples**, plus **three shared "signal
insets"** (start curve, kick-stem plot, split ladder) that each render 5–6 metrics from a single
trace, all hung on the already-settled **race-phase timeline spine** and revealed by **progressive
disclosure** (headline → timeline → flagged contrast marks → drill-down). The 37 metrics collapse
to: 1 timeline strip + 1 hero velocity envelope + 3 phase insets + ~25 identical contrast bars, of
which only the deviating 3–5 are surfaced by default. **No metric is a bare number; none needs a
bespoke chart.**

**Confidence:** HIGH — the mark vocabulary is the direct intersection of four independent,
authoritative sources (Cleveland–McGill perceptual ranking, Stephen Few's bullet graph, Tufte's
sparkline-with-reference-band, and pre-attentive processing), and each maps cleanly onto every
registry metric. MEDIUM only on the three Layer-B swim insets (`sr_dps_coupling`,
`dead_spot_timing`, `breathing_dip`), whose *data* is blocked/unvalidated per
[75-04-DISCOVERY.md](75-04-DISCOVERY.md) — the UI must degrade for those, not invent them.

> ## ⟳ Revision 2026-08-22b — the chart-literacy constraint (supersedes the specific marks below)
>
> **User feedback (decisive):** the audience includes non-technical parents and coaches "who don't
> get it or don't want to put in the effort." Limit the vocabulary to charts *everyone already
> reads* — **line, bar, pie/donut** — and cut anything that needs a data-trained eye. Box-and-whisker
> is out; **so is the dot-on-a-band "contrast bar" recommended below** (it is a box-plot relative —
> it silently assumes the reader decodes "band = normal range, tick = median").
>
> **What holds unchanged:** the *spine* (race-phase timeline), the *doctrine* (within-athlete
> comparison, no absolute thresholds), *small multiples*, *progressive disclosure*, and the four
> source principles (position-encoding, reference-to-baseline, repeat-one-form, one pre-attentive
> pop). Only the **rendered form of the mark changes.**
>
> **The pushback that survives:** you still cannot show a bare "peak velocity = 2.68 m/s" — to a
> parent that is an unjudgeable number. The comparison-to-baseline is the entire value, so it must be
> shown — in the *simplest chart there is*: **two bars, "Today" vs "Usual."** Everyone reads "his bar
> is shorter than his usual bar." No band, no SD, no learned encoding.
>
> **Revised vocabulary — the whole set:**
>
> | Metric shape | v1 (retired) | Revised — floor-level literacy |
> |---|---|---|
> | any scalar | dot-on-band contrast bar | **grouped bar: Today vs Usual** + plain word ("↓ below usual") |
> | the kick group | stem/lollipop plot | **plain bar chart** — one bar per kick; decay = bars shrink |
> | splits | "ladder" | **line chart** — pace across the lap; two lines Today vs Usual |
> | velocity envelope | line chart | **line chart** (kept — friendliest of all) |
> | phase budgets | segmented strip | **segmented bar, left→right** = the race in order (kept; a pie/donut is the parts-of-a-whole alternative but loses the sequence) |
> | radar / box-plot / dot-band | — | **cut** |
>
> **The real accessibility lever is not a chart — it's the sentence.** The LLM-phrased headline
> ("He surfaced early — his underwater was about a body-length shorter than usual") *interprets for*
> the reader; charts are backup. Progressive disclosure now maps onto literacy: **words for everyone →
> simple charts for those who lean in → full grid on a click.** Color never carries meaning alone —
> always paired with an arrow (↑/↓) and a plain word.
>
> Rendered in the mockup (`scratch/report-card-concept.html`): Today-vs-Usual bars, per-kick bar
> chart, today-vs-usual pace line, velocity line, left-to-right strip. Everything below this callout
> describes the retired v1 marks; read it for the *principles*, not the specific chart types.

## Objective

[CONTEXT-ui-consolidation.md](CONTEXT-ui-consolidation.md) settled the **spine** (race-phase
timeline) and the **doctrine** (contrast-only vs the athlete's own band; no absolute thresholds;
attention-allocation; LLM in the phrasing layer only). It explicitly left open, "for the eventual
plan to resolve," the thing this discovery answers:

- Given ~37 metrics across 4 phases, **what visual does each one get** so there is never a wall of
  numbers?
- Is there a *small* vocabulary of mark types (not 37 chart types) that covers them all?
- What does "good UI" actually prescribe here — grounded in sources, not taste?
- Where does the design have to **degrade gracefully** (blocked data, no baseline, unvalidated phase)?

## Scope

**Include:** the encoding vocabulary and the metric→visual map for all 37 `REGISTRY` specs; the
research basis; the layout that carries them; empty/blocked states.

**Exclude:** the framework/library choice (React vs. server-rendered, chart lib) — that's a
`/paul:plan` call; the contrast-vs-norms question (settled as contrast-first in the parent context,
and *the visual language is identical either way* — norms would only add a second reference band);
any metric implementation (Swim/Whole batches are their own plans).

## The research: four sources, one convergent answer

| Source | The principle | What it forces in this design |
|---|---|---|
| **Cleveland & McGill** — graphical perception ranking | Decoding accuracy: **position on a common scale > position on unaligned scales > length > angle/slope > area > color/shading**. Position is 1.4–2.5× more accurate than length, ~2× more than angle. | The default mark must be **position on a common scale**. It **rules out the radar/polygon** (angle+area, the two *worst* channels) — which the doctrine already forbids for a second reason. Gauges/donuts are out for the same reason. |
| **Stephen Few** — *Information Dashboard Design*; the **bullet graph** (2005) | Replace gauges: one metric vs. a reference range in a compact linear bar. Maximize data-ink; **organize by importance; keep related together; don't over-alert.** | The contrast bar **is** a bullet graph re-pointed from "vs target" to "vs the athlete's own band." Small, linear, dense, honest. "Organize by importance / don't over-alert" **is** attention-allocation. |
| **Tufte** — sparklines + **reference band** + **small multiples** | Word-sized graphics; a light band = the *normal range* (mean ± SD) behind the line; repeat one small design across many items **on a consistent scale** to compare shapes at a glance. | The band behind each contrast bar = the athlete's recent mean ± SD. **Small multiples** are how 25 scalar metrics live on one screen without 25 chart types. Consistent scale per metric across sessions. |
| **Pre-attentive processing** (Ware; NN/g progressive disclosure) | Hue/intensity, position, length, orientation are decoded in **milliseconds, pre-consciously**. Users scan dashboards in a Z-pattern, abandon >5–7 competing elements above the fold; progressive disclosure cuts cognitive load ~55%. | Use **one** pre-attentive pop (a diverging tint) for the *deviating* metric so the eye finds it with zero reading. Everything else stays quiet. **3-tier disclosure**: summary → context → detail. |

Corroboration that the doctrine is already the state of the art: an athletics
performance-analytics interface computes **"Excess Performance = each performance vs the athlete's
personal baseline (career mean and SD)"** — literally the contrast-bar model — and the standard way
to show deviation-from-a-midpoint is a **diverging palette split around a neutral center**. We are
not inventing; we are applying the consensus.

## The vocabulary: one mark + three insets + the spine

### 1. The **contrast bar** (the workhorse — default for every scalar metric)

A single horizontal track per metric:

```
 label            ┌──────────░░░░▓▓▓░░░──────●──────┐   value  ▲+18%
                  └──────────────┊──────────────────┘
   min-scale      band = athlete's recent mean±SD   ● = this session   ┊ = median tick
```

- **Position on a common scale** (Cleveland–McGill #1) — the dot's x-position *is* the value.
- **Reference band** (Tufte) — the athlete's own recent same-stroke sessions, mean ± SD. **This is
  the baseline; no absolute threshold is needed or implied.**
- **Diverging tint** (pre-attentive) — the dot/track lights warm or cool *only when it falls outside
  the band*. In-band = neutral grey, silent. This is the single pop the eye is allowed.
- **Delta label** — "+0.9 m", "−12%" vs the median, in the diverging color. The number is present
  but *subordinate to* the visual — it annotates the dot, it is not the primary object.
- Rendered as **small multiples**: identical geometry, stacked, so a phase's 4–6 metrics read as one
  scannable column and the outlier jumps out.

This one mark honestly covers ~25 of 37 metrics. **That is the anti-wall-of-numbers move**: a
scalar stops being a digit in a grid and becomes a dot on a band.

### 2. **Signal insets** (one per phase — each renders 5–6 metrics from a single trace)

Where several metrics are all reductions of the *same underlying curve*, don't emit N bars — draw
the curve once and let the metrics be features of it. The raw signal is the densest possible visual
(every metric is *derived* from it, so it can't lie about them):

- **Start inset — the launch curve** `velocity(t)` over `[dive_start → peak → underwater_start]`,
  glide sub-slice shaded.
  Reads off it directly: `peak_vel` (crest height), `time_to_peak_vel` (crest x), `glide_duration`
  / `glide_distance` (shaded width/area), `glide_decel` (slope of the shaded tail),
  `break_into_kick_vel` (endpoint dot). **6 metrics, one curve.**
- **Underwater inset — the kick-stem plot** each detected downkick peak as a dot at (time,
  velocity) over the UW window.
  `kick_count` = number of dots; `kick_tempo` = dot spacing; `kick_consistency` = evenness of
  spacing; `per_kick_decay` = slope of the peak trend line; `first_kick_impulse` = height of the
  first rise. **5 metrics, one plot.** (Breaststroke swaps in a pulldown curve for
  `pulldown_peak_vel` / `pulldown_duration`.)
- **Swim inset — the split ladder** velocity at 5/10/15/20/25 m as a short bar/line vs distance,
  each split carrying its *own* mini band. Plus the **breakout marker** dropped onto the hero
  envelope. Reads: `splits`, `breakout_vel` (marker height), `breakout_vel_loss` (the down-step
  from UW peak to post-breakout trough).

Each inset lives *inside* its phase's drill-down (tier 3), so tier 1 stays calm.

### 3. The **spine** (the frame — the four `whole` metrics *are* the chrome, not cards)

- **Race timeline strip** — 3–5 segments (Start · Underwater · Breakout marker · Swim), width =
  `phase_dist_budget` (toggle to `phase_time_budget`). Position-on-a-common-scale again. The
  deviating phase is tinted. **`phase_time_budget` and `phase_dist_budget` are this strip** — they
  are never rendered as numbers.
- **Hero velocity envelope** — the full `vel_envelope`, `velocity(t)`, phase-tinted under the
  strip. The one big chart. `jerk_smoothness` optionally rides it as a subtle roughness cue rather
  than a card.

So the four whole-race metrics disappear into the spine + hero — exactly right, because they *are*
the anatomy, not entries in it.

## The layout: attention-allocation, 3-tier progressive disclosure

Drawn literally from the parent context's 4-layer sketch, now grounded:

1. **Attention headline** (tier 1, always) — one LLM-phrased sentence naming the biggest band-break:
   *"Underwater was 0.9 m shorter than this swimmer's usual."* Phrasing layer only.
2. **Timeline strip + hero envelope** (tier 1) — the whole race at a glance; deviating phase tinted.
3. **Flagged phase's headline contrast bars** (tier 2) — 1–2 marks per phase surfaced because they
   broke the band; the rest collapsed. (Headline picks, coarsely, per the parent context: Start →
   `peak_vel` / glide; UW → `uw_distance` / `dist_per_kick`; Swim → `ivv` / `splits`.)
4. **Drill-down** (tier 3) — the phase's signal inset + the *full* small-multiples registry for that
   phase. Never on the first screen.

This satisfies the ">5–7 elements above the fold" ceiling and the "don't over-alert" rule: the first
screen shows a sentence, a strip, a curve, and the 3–5 things that actually moved.

## Full metric → visual map (all 37)

**Legend:** **CB** = contrast bar (default) · inset = the phase's shared signal · spine = the frame.

### Start (11)
| Metric | Visual | Notes |
|---|---|---|
| `peak_vel` | CB + crest of Start inset | headline candidate |
| `time_to_peak_vel` | CB + crest x-position on inset | explosiveness |
| `max_accel` | CB | none pre-Phase-64 (accel empty) → hidden, not zero |
| `dive_duration` | CB + = width of Start segment on the spine | |
| `glide_duration` | Start inset (shaded width) + CB | |
| `glide_distance` | Start inset (shaded span) + CB | |
| `glide_avg_speed` | CB | |
| `glide_decel` | Start inset (slope of shaded tail) + CB | |
| `streamline_drag` | **planned slot** — greyed "coming soon" chip | deferred (tether-confounded) |
| `break_into_kick_vel` | Start inset endpoint dot + CB | |
| `reaction_time` | GO→onset **gap bar** | only if `go_signal_s` set, else hidden |

### Underwater (13)
| Metric | Visual | Notes |
|---|---|---|
| `uw_duration` | CB + = width of UW segment on spine | |
| `uw_distance` | CB | headline candidate |
| `uw_avg_speed` | CB | |
| `uw_surface_ratio` | **paired bars** (UW vs surface speed) | ratio as two aligned bars, not a gauge |
| `kick_count` | inset (# dots) + CB | |
| `dist_per_kick` | CB | headline candidate |
| `kick_tempo` | inset (dot spacing) + CB | |
| `kick_consistency` | inset (spacing evenness) + CB | CV; lower better |
| `uw_ivv` | velocity **oscillation ribbon** + CB | band around UW velocity |
| `per_kick_decay` | inset (peak-trend slope) + CB | |
| `first_kick_impulse` | inset (first rise height) + CB | |
| `pulldown_peak_vel` | CB (breast only) | inset swaps to pulldown curve |
| `pulldown_duration` | CB (breast only) | |

### Swim (9)
| Metric | Visual | Notes |
|---|---|---|
| `ivv` | oscillation ribbon over swim window + CB | Layer-A window form |
| `breakout_vel` | marker dot on hero envelope + CB | headline candidate |
| `breakout_vel_loss` | **delta step** (UW peak → post-breakout trough) on envelope + CB | |
| `breakout_vs_steady` | paired bars | |
| `splits` | **split ladder** inset (v vs 5/10/15/20/25 m, per-split band) | headline candidate |
| `sr_dps_coupling` | CB **⚠ Layer-B** — badge "needs reliable cycles" | degrade; per 75-04 |
| `dead_spot_timing` | within-normalized-cycle position marker **⚠ Layer-B** | or window "dead-spot fraction" reframe |
| `accel_asymmetry` | **split bar** (accel vs decel share) | accel display-only (SG); empty pre-64 |
| `breathing_dip` | **BLOCKED** — not shown; "not measurable on 1-D encoder" note | per 75-04 (no breath signal) |

### Whole (4) — the frame, never cards
| Metric | Visual | Notes |
|---|---|---|
| `phase_time_budget` | **spine strip** (time mode) | |
| `phase_dist_budget` | **spine strip** (distance mode, default) | |
| `vel_envelope` | **hero chart** `velocity(t)`, phase-tinted | |
| `jerk_smoothness` | subtle roughness cue on the envelope + CB | |

## Why not the alternatives (recorded so we don't relitigate)

- **Radar / polygon** — rejected twice over: Cleveland–McGill's two *worst* channels (angle + area),
  enclosed area is an axis-order artifact, axes aren't commensurable, and it can't show a delta
  (trend is the product). The doctrine independently forbids it (needs a shared 0–100 "good" scale =
  absolute thresholds we don't have). Legitimate only as a *categorical* stroke-specialty fingerprint
  — which has **no inputs today** (needs meet results, not encoder velocity). Parked.
- **Gauges / donuts / KPI number grid** — the exact "wall of numbers / gauge clutter" Few's bullet
  graph was designed to replace; low data-ink, poor channel. This is the thing to avoid.
- **37 bespoke chart types** — defeats small-multiples scannability and blows the pre-attentive
  budget. One mark + three insets is the point.

## Recommendation

**Build the contrast-bar-as-small-multiples vocabulary + three signal insets on the timeline spine,
with 3-tier attention-allocation disclosure.** It is the literal intersection of the four sources and
covers every registry metric with **one** primary mark type. It is shippable against contrast-only
data (no normative corpus needed), honest (measures this athlete, not a population), and identical in
structure if norms are ever added (they'd just add a second band).

**Caveats / must-degrade:**
- **No-baseline empty state** (new athlete) is the contrast model's real weak spot — the band can't
  render. First session must show the *insets and spine* (which need no baseline — they're this
  session's own signal) and mark contrast bars "baseline building (n/N)". Do not show an empty grid.
- **Provenance must be visible** — `boundaries.sources` (`manual`/`detected`/`auto`/`none`) should
  tint the phase segment's confidence; never present an `auto`/unvalidated phase (back/breast
  breakout, STATE items 10–11) as trusted.
- **Blocked/Layer-B metrics degrade, never fake** — `breathing_dip` hidden with a reason;
  `sr_dps_coupling`/`dead_spot_timing` badged "needs reliable cycles" or shipped only in their
  window-reframe (per 75-04). `max_accel`/`accel_asymmetry` hidden on pre-Phase-64 sessions.
- **One accessible diverging palette** for deviation (color-blind-safe; never color as the *only*
  cue — position carries the value, color only flags the break).

## Open questions

- **Baseline window = the band** — last N same-stroke sessions, or `ratings.py`'s "previous
  same-stroke session"? Needs one source of truth before the band can be drawn. — Impact: **high**
  (the band is the whole model).
- **Headline-metric picks per phase** — the coarse list above needs ratifying (which 1–2 per phase
  are tier-2 vs. tier-3). — Impact: **medium**.
- **Deviation threshold for "lights up"** — ±1 SD (the band edge) or a coach-tunable sensitivity?
  Over-alerting is the named failure mode. — Impact: **medium**.
- **`sr_dps_coupling` / `dead_spot_timing`** — ship the Layer-A window reframe now, or hold for
  reliable cycles? Decides whether they get a real inset or a badged CB. — Impact: **medium** (per
  75-04).
- **Surface**: concept only today; parent CONTEXT says web first, iOS after. iOS collapses insets to
  the timeline + headline + one CB column. — Impact: **low** (spine is identical).

## Quality Report

**Sources consulted (2026-08-22):**
- Cleveland & McGill graphical-perception ranking — [FlowingData, "Graphical perception – learn the
  fundamentals first"](https://flowingdata.com/2010/03/20/graphical-perception-learn-the-fundamentals-first/).
- Stephen Few, bullet graph & *Information Dashboard Design* — [Bullet graph
  (Wikipedia)](https://en.wikipedia.org/wiki/Bullet_graph); [Best Practices for Scaling Sparklines
  (Perceptual Edge PDF)](https://www.perceptualedge.com/articles/visual_business_intelligence/best_practices_for_scaling_sparklines.pdf).
- Tufte sparklines / reference band / small multiples — [Sparkline theory and practice
  (edwardtufte.com)](https://www.edwardtufte.com/notebook/sparkline-theory-and-practice-edward-tufte/);
  [Small Multiples (Juice Analytics)](https://www.juiceanalytics.com/writing/better-know-visualization-small-multiples).
- Progressive disclosure / cognitive-load ceiling — [Progressive disclosure
  (Wikipedia)](https://en.wikipedia.org/wiki/Progressive_disclosure); [What Is Progressive Disclosure
  in UX? (UXPin)](https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/).
- Pre-attentive attributes (Ware's form/color/position/motion) — [Preattentive attributes of visual
  perception (UX Collective)](https://uxdesign.cc/preattentive-attributes-of-visual-perception-and-their-application-to-data-visualizations-7b0fb50e1375).
- Athlete-baseline (mean ± SD) deviation model + diverging palette — [Performance Anomaly Detection
  in Athletics (arXiv 2604.21953)](https://arxiv.org/pdf/2604.21953); [Diverging Colour Palettes
  (uploadarticle)](https://uploadarticle.com/diverging-colour-palettes-data-storytelling/).

**Verification:**
- "Position beats angle/area" and the exact ranking: verified across the Cleveland–McGill summaries.
- "Bullet graph replaces gauges; organize-by-importance / don't-over-alert": verified in Few sources.
- "Reference band = mean ± SD behind a sparkline; consistent scale for small multiples": verified in
  Tufte/Few sparkline sources.
- "Progressive disclosure = summary/context/detail, cuts load, >5–7 elements hurts": verified in
  NN/g-derived sources.
- Registry contents (37 specs, phases/units/tiers/status): read directly from
  [phase_metrics.py](../../../phase_metrics.py) `REGISTRY`.

**Assumptions (not verified against literature):**
- That a *window-form* IVV/oscillation ribbon is an acceptable stand-in for textbook per-cycle IVV
  (product-doctrine judgement, consistent with the shipped `uw_ivv`; carried from 75-04).
- That coaches read the timeline spine (distance-weighted) as the primary orientation — asserted in
  the parent context, not user-tested.

---
*Discovery completed: 2026-08-22*
*Confidence: HIGH (mark vocabulary) / MEDIUM (Layer-B insets, data-blocked)*
*Ready for: /paul:plan 75 Step-3 UI (web first) — baseline-window + headline-picks decided first*
