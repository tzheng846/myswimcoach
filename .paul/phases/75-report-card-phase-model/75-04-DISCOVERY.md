---
phase: 75-report-card-phase-model (Step-2 Swim metrics → 75-04)
topic: Re-tier the 9 Swim-phase metrics after the Phase 75–79 boundary-reliability change
depth: standard
confidence: HIGH
created: 2026-08-21
---

# Discovery: Re-tiering the 9 Swim metrics after boundary reliability changed

**Recommendation:** Re-cut the tiers along the **reliability *layer* each metric rides**, not
code-cheapness. The 75–79 work improved the **phase-window boundaries** (`stroke_start_s`/`finish_s`);
it did **not** touch **per-cycle stroke segmentation** (`segmentation_reliable` is still hardcoded
`False`, and cycles aren't even in `PhaseContext`). Six metrics are window/distance arithmetic and are
now de-risked — ship them next (one at a time, D12). Three are per-cycle and are **not** unblocked by
this change; one of those (`breathing_dip`) needs a signal the encoder can't produce.

**Confidence:** HIGH — every load-bearing claim is grep/read-verified in `phase_metrics.py` +
`metrics.py` (citations inline). The two definition-dependent calls (`accel_asymmetry`,
`dead_spot_timing`) are MEDIUM because their tier depends on which framing you choose.

## Objective

The taxonomy tiers (low/med/high) were assigned in [CONTEXT.md](CONTEXT.md) as **implementation-effort**
tags: *already-derivable-from-existing-data → low/medium, needs-new-signal-processing → high*
([phase_metrics.py:441](../../../phase_metrics.py)). Since then, Phases 75–79 changed boundary
reliability materially. Questions:

- Which of the 9 Swim metrics does the boundary change actually help?
- Do any tiers move now that `stroke_start_s`/`finish_s` are `detected` (refreshable by backfill)?
- What, if anything, is **blocked** — and by what?

## Scope

**Include:** the 9 `swim`-phase specs in `REGISTRY` ([phase_metrics.py:488](../../../phase_metrics.py)),
what each needs, and which reliability layer it depends on.

**Exclude:** implementing any metric (that's 75-04+, gated per D12), the Step-3 UI, and the Start/Whole
buckets. No new detector is proposed here.

## The one finding everything hangs on: two reliability layers, only one improved

There are **two independent segmentation layers**, and the taxonomy's "cheap" tags blurred them:

| Layer | What it is | Where | State after 75–79 |
|---|---|---|---|
| **A — phase-window boundaries** | the 4 marks `dive_start / underwater_start / stroke_start / finish` | `resolve_boundaries()` → `ctx.bounds`; provenance `manual→detected→auto→none` | **IMPROVED.** `stroke_start_s` was a stale seed **3.56 s → 0.40 s**; now `detected` via `detect_swim_boundaries`, refreshed by `backfill_phases.py` / `POST /recompute` |
| **B — per-cycle stroke segmentation** | cutting the swim into individual stroke *cycles* | `SEGMENTER_BY_STROKE` (wavelet / `_learned_boundaries`) inside `compute_session_metrics` | **UNCHANGED.** `session["segmentation_reliable"] = bool(manual_bounds)` → **`False` on every auto session** ([metrics.py:1706](../../../metrics.py)) |

Two consequences that decide the tiering:

1. **`PhaseContext` carries no cycles.** It has `t, vel, dist, accel, fs, stroke_type, …, bounds` —
   and nothing per-cycle ([phase_metrics.py:73](../../../phase_metrics.py)). The per-cycle values the
   CONTEXT called "already exist (cheap!)" — `dead_spot_s`, `trough_vel_ms`, `stroke_rate_spm`,
   `mean_dps_m` — live **only inside `compute_session_metrics`** ([metrics.py:1591-1658](../../../metrics.py)),
   which the phases engine does not call. A Layer-B swim metric would have to **re-segment inside its
   compute fn**, and it would inherit `segmentation_reliable = False`.
2. **Layer A got a reliable *start* but the *end* is still weak.** `finish_s` is the weakest marker
   (MAE **2.76 s**, worst 6.43 s — STATE item 12). Any window metric that integrates *to the finish*
   (steady-state window, 20/25 m splits) inherits that noise. `stroke_start_s` is the reliable end of
   the window; `finish_s` is not.

**So the honest re-tier is by layer, not by "cheap."** Layer-A metrics genuinely dropped in
risk/effort. Layer-B metrics did **not** move — and a couple were mis-tagged "low/medium" purely
because the *code* is short.

## Findings — per metric

Precedents that make Layer-A metrics cheap AND trustworthy already exist and are implemented:
`_compute_uw_ivv` (window std/mean, detector-independent, [phase_metrics.py:419](../../../phase_metrics.py)),
`_compute_uw_surface_ratio` (window Δd/Δt ratio, [:281](../../../phase_metrics.py)), `_compute_uw_avg_speed`
(window Δd/Δt, [:273](../../../phase_metrics.py)). Swim metrics can mirror these one-for-one.

### Layer A — window / distance arithmetic (de-risked by 75–79) → ship next

| Metric | Key | Orig | Needs | Re-tier | Note |
|---|---|---|---|---|---|
| Breakout velocity | `breakout_vel` | low | `vel` at `stroke_start_s` | **low — ship FIRST** | Was **de-facto blocked**: reading velocity at a 3.56 s-stale mark gave the wrong sample. Now `stroke_start` is `detected` (free 0.42 s / fly 0.38 s), so this is finally a correct single read. Prefer a small window-mean around the mark over one noisy sample. |
| Split velocities | `splits` | low | `dist`→time lookup at 5/10/15/20/25 m | **low — unaffected** | Pure distance-profile lookup; **never needed the boundaries**. `dive_start_s` (now 0.15 s) gives a clean 0 m anchor. Caveat: 20/25 m may fall near the noisy `finish_s`/tail — clamp to the trace. |
| Intracyclic velocity variation | `ivv` | medium | std/mean of `vel` over `[stroke_start, finish]` | **low (↓ from medium)** | Exact clone of the implemented `uw_ivv` — **detector-independent**, needs only the window. The CONTEXT called it "per-cycle slices exist (cheap!)" (Layer B), but the *window* form is simpler, needs no cycles, and is the one the tool's within-athlete doctrine actually wants. |
| Breakout vs steady-state | `breakout_vs_steady` | medium | breakout-window mean ÷ mid-swim mean | **low–medium** | Mirrors `uw_surface_ratio`. Feasible now. **Caveat:** the "steady-state" window must exclude the weak-`finish_s` tail — define it as a mid-swim span (e.g. `stroke_start`+Δ … `finish`−Δ), not "everything to finish." |
| Velocity loss at breakout | `breakout_vel_loss` | medium | underwater peak/mean vs first post-breakout trough/mean | **medium (unblocked)** | Feasible now that both `underwater_start`/`stroke_start` are trustworthy. Effort is in **defining the loss window** (underwater peak → surfacing trough), not detection. Keep medium. |
| Acceleration asymmetry | `accel_asymmetry` | medium | pos-vs-neg accel over the swim window | **medium (window framing)** | Feasible as a **window** stat over `ctx.accel`. Two caveats: `ctx.accel` **may be empty on pre-Phase-64 sessions** — the fn must return `None` then ([phase_metrics.py:76-90](../../../phase_metrics.py)); and accel is **display-only** SG-derivative (PIPELINE §1.7). If instead you mean *per-cycle* accel/decel asymmetry, it's Layer B (see below). |

### Layer B — per-cycle (NOT unblocked by 75–79)

| Metric | Key | Orig | Why it's Layer B | Re-tier |
|---|---|---|---|---|
| Stroke-rate ↔ DPS coupling | `sr_dps_coupling` | **low** | Needs per-cycle SR + DPS series (`stroke_rate_spm`, `mean_dps_m` are cycle-derived, [metrics.py:1629/1655](../../../metrics.py)) → rides on `segmentation_reliable = False`; cycles not in `PhaseContext`. | **mis-tagged — treat as high-risk.** "low" = *code is short*, not *number is trustworthy*. A session-mean ratio is cheap but weakly meaningful; the true within-swim coupling needs reliable cycles. |
| Dead-spot timing within cycle | `dead_spot_timing` | medium | "within cycle" ⇒ needs cycle bounds to place the trough's *phase*. `dead_spot_s` exists but is per-cycle ([metrics.py:1606](../../../metrics.py)). | **high unless reframed.** Cheap reframe that IS Layer A: window-level "dead-spot fraction" (% of swim window under `_DEAD_SPOT_THRESH·v95`) — loses "timing within cycle" but needs no segmentation. |
| Breathing-stroke velocity dip | `breathing_dip` | high | Needs (a) reliable cycles **and** (b) knowing *which* cycles are breaths — a signal the **1-D axial encoder does not observe**. `grep breath` in `metrics.py` = **zero hits**; no breathing code exists. | **BLOCKED — stays high, flag before any work.** CONTEXT line 152 ("Phase 73 says breathing is visible") is a hypothesis, not a detector. Distinguishing a breathing dip from ordinary IVV requires a periodicity assumption (breathe every N) or external ground truth. Needs a design decision, not implementation. |

## Recommendation

**1. Re-tier by layer.** Adopt the table above:

- **Ship next (Layer A), in this order, one at a time per D12:**
  `breakout_vel` → `splits` → `ivv` → `breakout_vs_steady` → `breakout_vel_loss` → `accel_asymmetry`.
  All are window/distance arithmetic with an implemented precedent; no new detector; no schema change
  (jsonb, D10). `ivv` moves **medium → low**; `breakout_vel` moves from *de-facto-blocked → low*.

- **Defer (Layer B):** `sr_dps_coupling` and `dead_spot_timing`. Re-tag `sr_dps_coupling` off "low" —
  its cheapness is code, not trust. Either (a) wait for cycle-segmentation trust, or (b) reframe each
  as a **window** statistic (dead-spot *fraction*; session-level SR·DPS product) and ship the reframe
  as Layer A. Recommend (b) if the report card needs them soon.

- **Blocked:** `breathing_dip`. Do not schedule until there's a decision on how a breath is identified
  on a 1-D trace (assumption vs external truth). This is the answer to "what's blocking."

**2. One cross-cutting caveat for the whole batch:** `finish_s` is still weak. Define every "to the
end" window against a **trimmed** finish, and clamp late splits to the trace, so Layer-A metrics don't
silently inherit Layer-B-grade error at the tail.

**Rationale:** The boundary work bought a reliable *swim window*, which is exactly what
window-arithmetic metrics need — and the codebase already proves the pattern in the underwater bucket
(`uw_ivv`, `uw_surface_ratio`, `uw_avg_speed` all implemented and shipping). It bought **nothing** for
metrics that need individual stroke cycles, because that layer was never in scope for 75–79 and isn't
reachable from `PhaseContext`.

**Caveats:**
- `accel_asymmetry` and `dead_spot_timing` tiers flip depending on window-vs-per-cycle framing — the
  user should pick the framing before 75-04 planning (see Open Questions).
- `breakout_vel` at a single sample is noisy; use a short mean window around `stroke_start_s`.

## Open Questions

- **`ivv` definition** — window std/mean (Layer A, recommended, matches `uw_ivv`) vs per-cycle mean IVV
  (Layer B). — Impact: **high** (decides whether `ivv` is low or high).
- **`accel_asymmetry` framing** — window pos/neg accel (Layer A) vs per-cycle accel/decel (Layer B). —
  Impact: **medium**.
- **`dead_spot_timing` reframe** — accept window-level "dead-spot fraction" (ship now) or hold out for
  true within-cycle timing (blocked on segmentation)? — Impact: **medium**.
- **`breathing_dip`** — is there any acceptable breath-identification assumption, or is it out of reach
  on the 1-D trace? — Impact: **high** (decides schedule-or-drop).
- **`breakout_vs_steady` / late splits vs weak `finish_s`** — what trim/steady window is acceptable? —
  Impact: **medium**.

## Quality Report

**Sources consulted (all 2026-08-21, this repo):**
- `phase_metrics.py` — `REGISTRY` swim specs (L488-497), `PhaseContext` (L73-102), `resolve_boundaries`
  (L129-210), implemented precedents `_compute_uw_ivv`/`_uw_surface_ratio`/`_uw_avg_speed`.
- `metrics.py` — `segmentation_reliable = bool(manual_bounds)` (L1706), `detect_swim_boundaries`
  (L1371), per-cycle `dead_spot_s`/`trough_vel_ms`/`stroke_rate_spm`/`mean_dps_m` (L1591-1658);
  `grep breath` → 0 hits.
- `PIPELINE.md` §3 (boundary detectors + accuracy), §5 (cycle segmentation + `segmentation_reliable`),
  §8 (validation reality: `finish_s` MAE 2.76 s).
- `.paul/STATE.md` (boundary table + owed items 7/12); `CONTEXT.md` (original feasibility tags, D5/D10/D12).

**Verification:**
- "Boundary work improved Layer A, not Layer B": Verified — `stroke_start` now `detected`
  (resolve_boundaries L196-207) vs `segmentation_reliable` unchanged (metrics.py:1706).
- "Cycles absent from PhaseContext": Verified — dataclass fields, phase_metrics.py:91-101.
- "No breathing signal exists": Verified — zero `breath` matches in metrics.py.
- "`finish_s` weak": Verified — PIPELINE §8 / STATE item 12.

**Assumptions (not verified against literature):**
- That the within-athlete/no-absolute-threshold doctrine makes a **window** IVV acceptable in place of
  textbook per-cycle IVV. (Product-doctrine judgement, consistent with the shipped `uw_ivv`.)

---
*Discovery completed: 2026-08-21*
*Confidence: HIGH*
*Ready for: /paul:plan 75-04 (Swim window metrics — breakout_vel first)*
