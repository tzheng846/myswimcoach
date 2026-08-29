---
phase: 75-report-card-phase-model
plan: 06
topic: Swim + Whole metric batch — implement the 12 remaining registry metrics and render them on the website, annotations-first
created: 2026-08-28
source: /paul:discuss (2026-08-28), user-driven; AskUserQuestion ×2 (6 forks locked)
discovery: 75-06-DISCOVERY.md (HIGH confidence, 2026-08-25)
status: Vision settled; ready for /paul:plan 75-06
---

# Phase 75 Plan 06 — Context: Swim + Whole metrics (fill the panels)

## Goal

**Fill the two unbuilt panels on the primary session report card** at `/app/sessions/[id]`. 75-05 shipped
Start + Underwater as 1D usual-range strips; 75-07 made that view the primary report. Swim currently shows
only the legacy per-cycle charts (no registry metrics at all) and Whole race is a `<ComingSoon>` stub
([PhaseReportCard.js:342](../../../web/components/portal/phases/PhaseReportCard.js)). 75-06 implements the
remaining registry metrics and renders them.

**User's governing rule (2026-08-28):** *"Just like any other metrics, prioritize existing annotations first,
then fall back to auto segmentation."*

## Grounded state — what the rule already gets for free

Verified in code during discussion, not assumed:

1. **Boundary-level precedence already exists and needs no work.** `resolve_boundaries`
   ([phase_metrics.py:129](../../../phase_metrics.py)) resolves all four boundaries as
   `manual` (coach annotation) > `detected` (live detector) > `auto` (seed), and stamps `boundaries.sources`.
   Every Swim/Whole metric is window arithmetic over `ctx.bounds`, so all 12 inherit annotations-first
   automatically. **No new precedence machinery for the window layer.**

2. **The actual gap is per-cycle data.** `PhaseContext` carries no `cycles`
   ([phase_metrics.py:91-101](../../../phase_metrics.py)) — the reason 75-06-DISCOVERY deferred the two
   Layer-B metrics. But `metrics_json["cycles"]` is in scope at **both** `compute_phases` call sites
   (`/process` [api.py:216](../../../api.py); `_rebuild_phases` [api.py:1063](../../../api.py)), and
   `PUT /annotations` already **overwrites** `cycles` with `compute_session_metrics(manual=...)` output
   ([api.py:936-951](../../../api.py)). So threading `ctx.cycles` in delivers annotations-first-with-auto-
   fallback for per-cycle metrics essentially for free — the stored cycles are already the coach's whenever
   an annotation exists.

3. **DEFECT that breaks the rule outright.** `PUT /annotations` rebuilds `metrics_json` as a fresh 4-key dict
   `{session, cycles, initial_phase, data_quality}` ([api.py:949-955](../../../api.py)) — it **drops `phases`
   and `go_signal_s`**. The moment a coach annotates a session (≥2 cycle bounds), that session loses its
   entire phase-metrics object until someone re-runs `tools/backfill_phases.py`. **The best-ground-truth
   sessions are exactly the ones currently showing nothing.** Fixing this is in scope (D4).

4. **`boundaries.sources` is computed and stored but surfaced nowhere in the UI** (grep: zero hits across
   `web/components/portal/phases/*`). A coach cannot tell a hand-marked window from a detected one.

## Locked decisions (AskUserQuestion, 2026-08-28)

**D1 — Vector metrics render as ONE ROW PER ELEMENT.** Four metrics are vector-valued (`splits`,
`phase_time_budget`, `phase_dist_budget`, `vel_envelope`) and the shipped `RangeStrip` + baseline + valence
engine is strictly scalar-per-metric. Rather than reduce-to-scalar or build a multi-value primitive, each
element becomes its own strip with its own median ± 1.5·MAD usual range. Rationale: reuses the shipped
engine untouched, and a coach compares a 15 m split to *his own* 15 m split. **Cost accepted: ~15 vector rows.**

**D2 — Include the two Layer-B per-cycle metrics, annotations-first.** `sr_dps_coupling` and
`dead_spot_timing` ship (reversing 75-06-DISCOVERY's defer), because threading cycles makes them
trustworthy on annotated sessions and merely provisional on auto ones — exactly the user's stated rule.
They render on every session, with a degraded treatment when the cycles are auto.
**`breathing_dip` is DROPPED, not deferred** — a 1-D axial encoder cannot observe which strokes were breaths
(`grep breath` = 0 hits repo-wide). It should be removed from the registry or marked permanently blocked.

**D3 — Provenance shows in the hover overlay only.** Add a source line to the existing page-dimming
`HoverExplain` ("window from your marks" / "auto-detected"), fed from `boundaries.sources`. No always-on
badge — the v3 visual language deliberately stripped standing chrome, and hover is where the explanation
already lives.

**D4 — Fix the endpoint AND backfill.** `PUT /annotations` must preserve `phases`/`go_signal_s` and rebuild
`phases` from the newly-written manual cycles. Then a user-run `python tools/backfill_phases.py --apply`
populates the library — which also closes the **never-run 75-04 Start backfill** (commit `5c398b4` "mark
backfill applied" predates `defed65` "start-phase metrics", so no stored session has Start metrics today).

**D5 — Whole race = 4th section with a full-trace inset.** `whole` has no single window, which breaks the
`SECTIONS` `win: [start, end]` contract and the `flagsByPhase` → timeline-segment mapping. Resolution: its
inset is the entire trace (`dive_start_s` → `finish_s`); its flags count toward the top alert line but
highlight no timeline segment. Keeps all four panels visually consistent.

**D6 — `vel_envelope` = per-phase peak velocity, 4 rows.** Peak within Start / Underwater / Swim, plus an
overall peak. Consistent with D1 and with `phase_time_budget` / `phase_dist_budget` also being per-phase
vectors. The scalar "peak → finish decay" reading is rejected (overlaps the swim metrics, loses shape).

## The batch — 12 metrics

**Swim (8 of 9 specs; [phase_metrics.py:649-658](../../../phase_metrics.py))**

| Key | Layer | Derivation |
|---|---|---|
| `ivv` | A | std/mean of `vel` over `[stroke_start_s, finish_s]` — exact clone of shipped `_compute_uw_ivv` |
| `breakout_vel` | A | short window-mean of `vel` around `stroke_start_s` (a single sample is noisy) |
| `breakout_vel_loss` | A | underwater mean/peak minus first post-breakout trough |
| `breakout_vs_steady` | A | breakout-window mean ÷ **trimmed** mid-swim mean (exclude the weak `finish_s` tail) |
| `splits` | A (vector, 5 rows) | segment mean velocity per 5 m from `dive_start_s` as the 0 m anchor, @ 5/10/15/20/25 m; `None` beyond distance actually covered |
| `accel_asymmetry` | A | positive-vs-negative accel fraction over the swim window; `None` when `ctx.accel` empty |
| `sr_dps_coupling` | **B** | correlation of per-cycle stroke rate vs DPS across cycles in the swim window |
| `dead_spot_timing` | **B** | mean time from cycle start to that cycle's velocity minimum (unit `s`) |

**Whole (4 specs)**

| Key | Layer | Derivation |
|---|---|---|
| `phase_time_budget` | A (vector, 3 rows) | Start / Underwater / Swim duration as a share of total |
| `phase_dist_budget` | A (vector, 3 rows) | same three windows, share of total Δ`dist` |
| `vel_envelope` | A (vector, 4 rows) | peak `vel` within Start / Underwater / Swim + overall (D6) |
| `jerk_smoothness` | A | mean \|Δaccel\|/Δt over the swim window; `None` when `ctx.accel` empty |

**Row count: ~23 new rows** (Swim 12, Whole 11). Panel length is a real UI risk — see Risks.

## Approach

**Backend (`phase_metrics.py`)**
- Extend `PhaseContext` with `cycles` and a segmentation-reliability flag; both optional so every existing
  construction site keeps working (the 75-02 precedent).
- Thread them at both call sites from `metrics_json["cycles"]` / `data_quality.segmentation_reliable`.
- 12 new `_compute_*` functions + flip the specs to `status="implemented"`. Follow the standing contract:
  pure, return a raw value or `None`, never raise (`compute_phases` swallows anyway).

**Backend (`api.py`)**
- D4 repair in `PUT /annotations`: merge into the existing `metrics_json` rather than replacing it, then
  rebuild `phases` from the manual cycles.

**Frontend (`web/components/portal/phases/PhaseReportCard.js`)**
- `SECTIONS` (line 55-58): add `swim` (`win: [stroke_start_s, finish_s]`) and `whole` (full-trace inset, D5).
- `DISPLAY` (line 25-52): currently **zero** Swim/Whole entries, so every new row would fall back to the bare
  registry label with no hover text. All 12 (plus per-element labels) need label/unit/desc authored.
- `flagsByPhase` (line 241): `{start, underwater, swim}` — add `whole` (D5).
- Remove the Whole `<ComingSoon>` (line 342). **Keep `CycleCharts` in the Swimming section** — 75-07 put it
  there deliberately; the registry strips join it, they don't replace it.
- `HoverExplain`: provenance line (D3).
- `phaseValence.js` `DIRECTION_OF_GOOD` already pre-fills all 13 keys — but per-element keys (D1) are new and
  need entries; `breathing_dip` should come out with the spec.

**Then:** user-run `python tools/backfill_phases.py --apply` (D4). The tool already reads
`session_annotations.phases`, so annotated sessions keep their manual boundaries through the backfill.

## Risks / known-weak inputs

- **Panel length.** ~23 new rows across two sections. May need grouping or collapse — a planning call.
- **Layer-B on auto sessions.** `sr_dps_coupling` + `dead_spot_timing` ride `segmentation_reliable=False`
  ([metrics.py:1706](../../../metrics.py)). Phase 80 measured freestyle **exact cycle count on 6/21 (29%)**
  sessions (median |Δcount| = 1), though median stroke-rate error is only 3.8% — so cadence-derived
  quantities are far safer than count-derived ones. Degraded visual treatment is required, not optional.
- **`finish_s` is the weakest boundary** (MAE 2.76 s, worst 6.43 s — Phase 78 / STATE item 12). It bounds
  `ivv`, `breakout_vs_steady`, and every swim-share budget. Trimming the tail (per the `breakout_vs_steady`
  derivation) is the mitigation.
- **`ctx.accel` is empty on pre-Phase-64 sessions** → `accel_asymmetry` and `jerk_smoothness` return `None`.
- **Jerk is a 2nd derivative of an axial signal** — noise-amplified even though `ctx.accel` is already the
  SG-derivative (PIPELINE §1.7). Present as a within-athlete relative proxy only.
- **Registry `tier` is stale** (STATE item 7 / PIPELINE §6): 75-02/79 turned several "high" specs cheap. Tier
  by layer (A vs B), not by the registry tag.

## Open questions for /paul:plan

1. **How do per-element rows key into the engine?** Baseline, valence, and dismiss-state all key off a single
   string metric key. Two options: emit a list-valued spec and have the UI expand it into synthetic keys
   (`splits_15m`, `phase_time_budget_underwater`, …), or register N scalar specs in `REGISTRY` directly.
   Either way the per-element keys must be **stable** — they become baseline-history keys.
2. **Degraded visual for Layer-B on auto sessions** — a muted strip, a "provisional" tag, or suppressed
   valence coloring? Must not read as a normal confident metric.
3. **`dead_spot_timing` exact definition** — confirm "mean time from cycle start to that cycle's velocity
   minimum" (absolute seconds, per registry unit `s`) vs a normalized within-cycle fraction.
4. **Order within the Swimming section** — registry strips above or below `CycleCharts`.
5. **`breathing_dip` disposal** — delete the spec, or keep it with an explicit permanently-blocked status so
   the reasoning stays visible in the registry.
