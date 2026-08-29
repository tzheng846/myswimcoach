---
phase: 75-report-card-phase-model (Step-2 Swim + Whole metrics → 75-06)
topic: Scope the 75-06 batch that fills the "coming soon" Swim + Whole panels — feasibility, layer, UI seam
depth: standard
confidence: HIGH
created: 2026-08-25
---

# Discovery: The 75-06 Swim + Whole metric batch (fill the "coming soon" panels)

**Recommendation:** Ship the **10 Layer-A metrics** (6 Swim + all 4 Whole) as the 75-06 batch; render the
**3 Layer-B/blocked Swim metrics** (`sr_dps_coupling`, `dead_spot_timing`, `breathing_dip`) as
clearly-labeled degraded pills, not compute. The single scoping fork is **not feasibility — it's UI shape**:
4 of the 10 shippable metrics are **vector-valued** (`splits`, `phase_time_budget`, `phase_dist_budget`,
`vel_envelope`) and the shipped `RangeStrip`/baseline/valence engine is strictly **scalar-per-metric**.
Decide reduce-to-scalar vs. new multi-value primitive before planning.

**Confidence:** HIGH — every feasibility/layer claim is grep/read-verified in `phase_metrics.py`,
`metrics.py`, and the shipped `web/components/portal/phases/*` (citations inline). The Swim-9 layer split is
carried unchanged from [75-04-DISCOVERY.md](75-04-DISCOVERY.md) (re-verified still-true, not re-derived); the
Whole-4 layer analysis and the UI-seam analysis are new here. MEDIUM only on the two framing calls
(`dead_spot_timing`, `vel_envelope` definitions) — Open Questions.

## Objective

75-05 shipped the report-card UI with **Start + Underwater** live and two **"coming soon"** panels
(`PhaseReportCard.js:328-329`). 75-06 fills them. Before planning:

- Which of the 13 unimplemented specs (**Swim 9 + Whole 4**) are actually shippable now, and which are blocked?
- What changed since the Swim-9 discovery (2026-08-21) now that **75-04 Start + 75-05 UI** have shipped?
- **What does "fill the panels" cost on the UI side** — is the seam a drop-in, or is there real design work?
- What's the concrete 75-06 batch + sequence?

## Scope

**Include:** the 9 `swim` + 4 `whole` specs in `REGISTRY` ([phase_metrics.py:649-664](../../../phase_metrics.py));
their reliability layer; the `PhaseReportCard`/`RangeStrip`/`DIRECTION_OF_GOOD` seam that renders them.

**Exclude:** implementing any metric (that's 75-06 APPLY); the per-cycle segmenter itself (Phase 80);
iOS; server-side dismiss persistence + LLM headline (75-05 deferrals, unrelated).

---

## Reminder — what's already documented (the user asked)

Three prior artifacts already cover most of the Swim half. **Nothing below is new work; it's the standing record.**

1. **[CONTEXT.md](CONTEXT.md) — the taxonomy** (the compute-everything spec, D4). It feasibility-tagged every
   metric ✅/🟡/🔶/⛔ and it is where the `low/medium/high` registry `tier` came from. **The Swim/Whole tags there:**
   - Swim: IVV, breakout-vel, breakout-loss, breakout-vs-steady, splits, SR↔DPS, dead-spot, accel-asymmetry all
     tagged 🟡 *cheap*; breathing-dip 🔶; L/R arm asymmetry ⛔ (dropped — tether can't separate arms).
   - Whole: phase time/dist budget 🟡, velocity envelope ✅, jerk-smoothness 🟡.
   - ⚠ Those 🟡 "cheap" tags **blurred two layers** — the correction is #2.

2. **[75-04-DISCOVERY.md](75-04-DISCOVERY.md) — the Swim-9 re-tier** (HIGH, 2026-08-21). Its one load-bearing
   finding: there are **two independent reliability layers**, and 75–79 improved only one.
   - **Layer A — phase-window boundaries** (`dive/underwater/stroke_start/finish`): **improved**. `stroke_start_s`
     went stale-seed **3.56 s → 0.40 s**, now `detected` + backfill-refreshable.
   - **Layer B — per-cycle stroke segmentation**: **unchanged.** `segmentation_reliable = bool(manual_bounds)`
     → **`False` on every auto session**, and **`PhaseContext` carries no cycles** — a per-cycle metric would have
     to re-segment inside its compute fn and inherit that `False`.
   - Verdict: 6 Swim metrics are Layer-A window/distance arithmetic → ship; 3 are Layer-B/blocked.
   - ⚠ **Filename caveat:** it says "→ 75-04" because it was written expecting Swim to be the *next* batch. Start
     jumped the queue as 75-04 (D12 gate waived, 10 metrics in one pass — [75-04-SUMMARY.md](75-04-SUMMARY.md)),
     so Swim/Whole is now **75-06**. The analysis is unaffected.

3. **[75-05-SUMMARY.md](75-05-SUMMARY.md) — the UI seam.** The row model + `DISPLAY` map + `DIRECTION_OF_GOOD`
   are "the seam for the remaining Swim (9) and Whole (4)"; those "currently render as coming-soon panels and
   `DIRECTION_OF_GOOD` already pre-fills their valence." True but partial — see the UI-seam finding below.

**Re-verified still-true today (2026-08-25):** `segmentation_reliable = bool(manual_bounds)`
([metrics.py:1706](../../../metrics.py)); `PhaseContext` fields = `t,vel,dist,accel,fs,stroke_type,go_signal_s,
annotation_phases,seed_phases,initial_phase,bounds` — **no cycles** ([phase_metrics.py:91-101](../../../phase_metrics.py)).
Start (75-04) + UI (75-05) shipping changed **nothing** about the Swim/Whole layer split. Also note STATE's flag
that the registry `tier` field is now stale (75-02/79 made "high" Start/UW metrics cheap) — **tier by layer, not by
the registry tag.**

---

## Findings — per metric

### Swim (9) — carried from 75-04-DISCOVERY, still valid

| Metric | Key | Layer | 75-06? | Needs |
|---|---|---|---|---|
| Breakout velocity | `breakout_vel` | A | ✅ ship first | `vel` window-mean around `stroke_start_s` (a single sample is noisy — use a short mean) |
| Intracyclic velocity variation | `ivv` | A | ✅ | std/mean of `vel` over `[stroke_start, finish]` — **exact clone of shipped `_compute_uw_ivv`** |
| Split velocities | `splits` | A | ✅ (⚠ vector) | `dist`→time lookup @ 5/10/15/20/25 m; `dive_start_s` = clean 0 m anchor. **Array-shaped — see UI seam** |
| Velocity loss at breakout | `breakout_vel_loss` | A | ✅ | underwater mean/peak − first post-breakout trough; effort is *defining the loss window*, not detection |
| Breakout vs steady-state | `breakout_vs_steady` | A | ✅ | breakout-window mean ÷ **trimmed** mid-swim mean (exclude weak `finish_s` tail) |
| Acceleration asymmetry | `accel_asymmetry` | A | ✅ (window form) | pos-vs-neg fraction over `ctx.accel` swim window; **`None` when accel empty** (pre-Phase-64) |
| Stroke-rate ↔ DPS coupling | `sr_dps_coupling` | **B** | ⛔ defer | per-cycle SR+DPS series → rides `segmentation_reliable=False`; registry "low" = *code is short*, not *trustworthy* |
| Dead-spot timing within cycle | `dead_spot_timing` | **B** | ⛔ defer / reframe | "within cycle" needs cycle bounds; cheap **window** reframe = "dead-spot fraction" (loses per-cycle timing) |
| Breathing-stroke velocity dip | `breathing_dip` | **BLOCKED** | ⛔ do not schedule | needs to know *which* cycles are breaths — **a signal the 1-D axial encoder does not observe** (`grep breath` = 0 hits) |

### Whole race (4) — NEW analysis (no prior discovery covered these)

| Metric | Key | Layer | 75-06? | Needs / caveat |
|---|---|---|---|---|
| Phase time budget | `phase_time_budget` | A | ✅ (⚠ vector) | per-phase duration ÷ total, from the 4 boundaries only. Cheap + trustworthy. **One % per phase → vector.** Swim share inherits weak `finish_s` |
| Phase distance budget | `phase_dist_budget` | A | ✅ (⚠ vector) | per-phase Δ`dist` ÷ total. Same vector shape; same `finish_s` tail sensitivity on the swim share |
| Velocity envelope | `vel_envelope` | A | ✅ (⚠ shape open) | CONTEXT tags ✅. "peak → decay by phase" — **definition open**: per-phase peak-velocity vector, or a scalar peak→finish decay? |
| Whole-swim smoothness (jerk) | `jerk_smoothness` | A | ✅ (⚠ noise) | mean\|Δaccel\|/Δt over swim; `None` when `ctx.accel` empty. **Caveat: jerk is a 2nd derivative of the axial signal → noise-amplified**; `ctx.accel` is already the SG-derivative (PIPELINE §1.7). Report as a *relative within-athlete* proxy only |

**All 4 Whole metrics are Layer A** (boundary/profile arithmetic; none need per-cycle segmentation). The whole
`whole` panel is shippable — its only real cost is UI shape (3 of 4 are vector/definition-open) + the jerk noise caveat.

### The UI seam — "fill the panels" is real work, not a flag flip

75-05 pre-wired **`DIRECTION_OF_GOOD`** for all 13 keys ([phaseValence.js:40-54](../../../web/lib/phaseValence.js)) ✅.
But filling the panels still requires, in [PhaseReportCard.js](../../../web/components/portal/phases/PhaseReportCard.js):

1. **`SECTIONS`** (line 55-58) has only `start` + `underwater`. Add `swim` (+ its `win: [stroke_start_s, finish_s]`
   inset) and `whole`. **`whole` has no single window** — the inset/`win` concept doesn't apply; needs a layout call.
2. **`DISPLAY`** (line 25-52) has **zero** Swim/Whole entries → every new row falls back to `{label: m.label, desc:""}`
   = registry label, **no hover explanation**. All 10 need label/unit/desc authored (mockup wording exists for some).
3. **`flagsByPhase`** (line 241) = `{start, underwater, swim}` — **no `whole`** bucket; the alert line + timeline
   would drop whole-race flags. Add `whole`, and decide how a cross-phase flag shows on the phase timeline (it maps
   to no segment).
4. **Remove** the two `<ComingSoon>` panels (line 328-329).
5. ⭐ **`RangeStrip` + `phaseBaseline` + `flagVerdict` are strictly scalar.** `splits`, `phase_time_budget`,
   `phase_dist_budget`, and (maybe) `vel_envelope` are **vector-valued**. This is the dominant design fork (Open Q1).

## Recommendation

**The 75-06 batch = the 10 Layer-A metrics.** Ship order (each is window/distance/profile arithmetic with an
implemented precedent — `_compute_uw_ivv` / `_uw_surface_ratio` / `_uw_avg_speed`; no new detector; jsonb, no migration):

1. `breakout_vel` → 2. `ivv` → 3. `breakout_vel_loss` → 4. `breakout_vs_steady` → 5. `accel_asymmetry`
   → 6. `splits` *(scalar-reduce or vector — Q1)* → 7. `phase_time_budget` → 8. `phase_dist_budget`
   → 9. `vel_envelope` *(shape — Q2)* → 10. `jerk_smoothness` *(noise caveat)*.

Then the **UI wiring** (SECTIONS+DISPLAY+whole-bucket+drop ComingSoon) as the closing task.

**Defer, render as degraded pills (the UI already does this for `reaction_time`/`streamline_drag`):**
`sr_dps_coupling`, `dead_spot_timing` (Layer B — unblock only via cycles-in-`PhaseContext`, which ties to Phase 80),
`breathing_dip` (blocked — needs a breath-identification decision, not code).

**Result:** Swim panel = **6 of 9** live + 3 labeled pills; Whole panel = **4 of 4** live. No panel stays "coming soon."

**Rationale:** the 75–79 boundary work bought a reliable *swim window*, which is exactly what window-arithmetic needs,
and the underwater bucket already proves the pattern in shipped code. It bought nothing for per-cycle metrics — that
layer was never in 75–79 scope and isn't reachable from `PhaseContext`. Batch (not one-at-a-time) matches the
75-04 precedent and the user's "batch" framing; D12's one-at-a-time gate is effectively relaxed to per-batch approval.

**Cross-cutting caveats for the whole batch:**
- **`finish_s` is the weakest boundary** (MAE 2.76 s — STATE #12). Every "to-the-finish" metric (swim budgets,
  `breakout_vs_steady`, 20/25 m splits) inherits tail noise → define steady/ivv windows against a **trimmed** finish
  and **clamp late splits to the trace**.
- **`accel_asymmetry` + `jerk_smoothness` need `ctx.accel`**, empty on pre-Phase-64 sessions → both must `None` out.

## Open Questions (resolve at `/paul:plan 75-06`)

- **Q1 — vector metrics (highest impact).** `splits` + both budgets are inherently multi-valued; `RangeStrip`/baseline
  are scalar. Ship **scalar reductions** now (splits → e.g. swim-avg speed or 15→25 m fade; budgets → the swim-phase %)
  to fill panels fast, **or** build a small **multi-value primitive** (per-phase / per-split mini-bars)? — Impact: **high**
  (changes both the stored return shape and the UI). *Recommend scalar-reduce for 75-06, multi-value primitive as 75-07.*
- **Q2 — `vel_envelope` definition.** Per-phase peak-velocity vector, or scalar peak→finish decay? — Impact: **medium**
  (ties into Q1: scalar keeps it in the shipped strip).
- **Q3 — `dead_spot_timing`.** Accept the **window** "dead-spot fraction" reframe (ship in 75-06 as Layer A) or hold for
  true within-cycle timing (blocked on Phase 80 cycles)? — Impact: **medium**. *Recommend hold; don't ship a renamed metric under the taxonomy's label.*
- **Q4 — whole-race on the timeline.** A cross-phase flag maps to no timeline segment — where does it surface (its own
  panel header count? excluded from the segmented bar)? — Impact: **low**.
- **Q5 — `breathing_dip`.** Any acceptable breath-identification assumption (breathe-every-N periodicity) on a 1-D
  trace, or formally drop it? — Impact: **medium** (schedule-or-drop). *Recommend drop/park; it is not shippable honestly.*

## Quality Report

**Sources consulted (all this repo, 2026-08-25 unless noted):**
- `phase_metrics.py` — `REGISTRY` swim+whole specs (L649-664), `PhaseContext` fields (L73-101), the implemented
  Layer-A precedents `_compute_uw_ivv`/`_uw_surface_ratio`/`_uw_avg_speed` (L273-436).
- `metrics.py` — `segmentation_reliable = bool(manual_bounds)` (L1706), per-cycle values live only in
  `compute_session_metrics` (not in the phases engine).
- `web/lib/phaseValence.js` — `DIRECTION_OF_GOOD` pre-fills all 13 (L40-54).
- `web/components/portal/phases/PhaseReportCard.js` — `DISPLAY` (no Swim/Whole, L25-52), `SECTIONS` (start+uw only,
  L55-58), `flagsByPhase` (no `whole`, L241), `<ComingSoon>` panels (L328-329), scalar `RangeStrip` call (L307-322).
- `.paul/phases/75-report-card-phase-model/` — CONTEXT.md (taxonomy + tags), **75-04-DISCOVERY.md** (Swim-9 layer
  split, 2026-08-21), 75-04-SUMMARY.md (D12 waived), 75-05-SUMMARY.md (UI seam). `.paul/STATE.md` (items 7/12).

**Verification:**
- "Swim layer split still valid": Verified — `segmentation_reliable` unchanged (metrics.py:1706); no cycles in
  `PhaseContext` (phase_metrics.py:91-101). Start/UI shipping touched neither.
- "All 4 Whole metrics are Layer A": Verified — each is boundary/profile arithmetic; none reference cycles.
- "UI seam is not a flag flip": Verified — `DISPLAY`/`SECTIONS`/`flagsByPhase` lack Swim/Whole; `RangeStrip` scalar.
- "`breathing_dip` blocked": Verified — `grep breath` in metrics.py = 0 hits (carried from 75-04-DISCOVERY, still 0).

**Assumptions (not verified against literature):**
- Within-athlete/no-absolute-threshold doctrine makes a **window** IVV / dead-spot-fraction acceptable in place of the
  textbook per-cycle forms (product-doctrine judgement, consistent with shipped `uw_ivv`).
- Scalar reductions of `splits`/budgets are coach-useful enough to ship ahead of a multi-value primitive (Q1).

---
*Discovery completed: 2026-08-25*
*Confidence: HIGH*
*Ready for: /paul:plan 75-06 (Swim + Whole Layer-A batch — breakout_vel first; resolve Q1 vector-shape before planning)*
