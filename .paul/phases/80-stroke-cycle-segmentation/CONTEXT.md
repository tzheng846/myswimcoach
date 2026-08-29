# Phase Context

**Phase:** 80 — Stroke-Cycle Segmentation: Count-Centric Re-measurement + Tuning
**Generated:** 2026-08-21 (AskUserQuestion ×2 + 2 free-text refinements)
**Status:** Ready for planning
**Predecessor:** Phase 59 (Segmenter Evaluation) — built the harness + per-stroke dispatch, closed
2026-08-09. **This phase overturns Phase 59's D3** (see D1 below).
**Not to be confused with:** the race-phase boundary work (Phases 75–79). That segments the trial into
Start / Underwater / Swim. **This phase is the OTHER segmentation** — cutting the Swim window into
individual stroke *cycles* for the per-cycle metrics (`metrics.py` §5/§7, `PIPELINE.md`).

---

## Why now

Stroke-cycle segmentation has not been touched since Phase 59 (2026-08-09). The entire arc since —
75 (report-card phase model), 76/77 (breakout), 78 (multi-swimmer diagnostic), 79 (dive_start) — was
the four *phase* boundaries. Nothing in STATE.md's owed list (items 9–12) points at cycle
segmentation. The user is opening a new thread on it deliberately.

Goal (AskUserQuestion, 2026-08-21): **measure it honestly, then improve it.** Not to flip
`segmentation_reliable`, not to unblock the Swim-phase metrics — those were offered and not chosen.

The pivot that defines the phase came in free text: **the success metric is stroke COUNT and CADENCE,
not boundary placement.** A segmentation whose every boundary is uniformly time-shifted (e.g. ~1 s) is
a **success** — right number of strokes, right rhythm. Phase 59 gated on boundary-matching F1 at
±0.15 s, which punishes a constant offset exactly as hard as it punishes garbage. By the user's
definition that gate measured the wrong thing.

---

## Grounded state (current code/docs, 2026-08-21)

### Mechanism — unchanged since Phase 59
Table-driven dispatch `SEGMENTER_BY_STROKE` ([metrics.py:443](../../../metrics.py)):

| stroke | segmenter | cycle rule |
|---|---|---|
| freestyle, backstroke | `segment_cycles_wavelet` | CWT ridge → cumulative phase → 1 boundary per arm entry, **paired k=2** |
| butterfly, breaststroke | `_learned_boundaries` (5-feat logistic, dot-product + sigmoid, no sklearn in prod) | **paired k=2** |
| unknown / im / udk | bare wavelet | k=1 |

`segmentation_reliable` is **hardcoded `False`** on every auto session (`PIPELINE.md §5`); flips `True`
only when a coach hand-annotates cycle bounds. Cycle *regularity* is already a gate separate from F1
(`tests/test_metrics.py::TestCycleRegularityGate`) — a segmenter with better F1 but drifting phase is
rejected. **That gate is the seed of this phase's cadence metric.**

### The honest-measurement target (numbers to reproduce, NOT to cite)
- **Phase 59 headline F1**, scored on the *annotated* swim window (±0.15 s): butterfly 0.526,
  breaststroke 0.444, freestyle 0.458.
- **My scratch aggregate of the uncommitted `segmenter_report.json`** (production-detected window,
  cycle F1): fly ~0.27, free ~0.17, breast ~0.05, udk 0.00. ⚠ **Prior to reproduce, not a result** —
  I am not certain my one-liner grabbed the right node in that report. If it holds, it says
  *window-detection error dominates end-to-end cycle error*, and the coach's charts ride on the lower
  number. Reconciling headline-vs-production is the first honest-measurement deliverable.

### The harness already exists — reuse, do not rebuild
Phase 59 shipped `segmenter_eval.py` (pure), `tools/score_segmenter.py` (CLI), a checked-in fixture
(`tests/fixtures/segmenter_truth.json`), and `tests/test_segmenter_eval.py`. The scorer is a generic
named-series matcher. `segmenter_report.json` (uncommitted, root) is a recent run's per-session dump.
This phase adds count/cadence/offset metrics *alongside* the existing F1 machinery.

### Ground-truth reality (Phase 78 + this discussion)
- **Single annotator (Tony), one rule:** mark = **hand touches water**, for **free / fly / back**.
  Breaststroke's mark convention is undefined (symmetric, no clean hand-entry instant).
- Coverage: 37/92 sessions annotated, 4 swimmers (Tony 18, Leo 14, Chantee 3, Dane 2). By stroke:
  free 16, fly 16, breast 4 (Leo 2, Dane 2), **back 0 labeled** (2 DB sessions exist unlabeled), udk 1.
- **The new metric lowers the labeling cost:** count + rough timing is enough — no 0.15 s-precise
  marks needed. This is what lets breaststroke and backstroke into scope (D2).

---

## Decisions (user, 2026-08-21)

**D1 — Success = COUNT + CADENCE primary; placement is OFFSET-ONLY. Overturns Phase 59 D3.**
Three tiers:
- **(a) Count** — `|Δ#cycles|` and exact-count rate (% sessions where predicted #cycles == true).
- **(b) Cadence / rhythm** — shift-invariant: stroke-rate error vs the human-derived rate, interval CV,
  alternation stability. **This exists to catch count's blindspot** — the user's own example: "8
  strokes all within 1 second" satisfies a pure count loss yet is garbage; cadence rejects it.
- **(c) Placement — reported as a single OFFSET, never penalized when constant.** Measure the systematic
  bias (median predicted−true) and its dispersion. A constant offset is acceptable *by definition*; a
  *variable* offset is a failure — but that failure is really a cadence failure, so (b) already owns it.
  Placement is "secondary for sure" (user).

**D2 — All four strokes in scope, breaststroke included. Dissolves Phase 59 D5/D13's carve-out.**
User: *"labeling rule doesn't even matter. That's the whole point."* Because we never score tight
placement, the exact human-mark convention is irrelevant — any consistent per-stroke mark yields
count + cadence + bias. So breast (undefined rule) and back (n=0 today) become measurable once cheap
count labels exist.

**D3 — Ground truth is single-annotator (Tony), hand-touch-water for free/fly/back.** Stated up front,
house rule (Phase 59 R1). ⚠ The new metric makes this caveat *smaller* than it was for a placement
metric: a systematic annotator offset is absorbed by (c), not scored as error. Cross-swimmer
generalisation is still untested on ~11 DB swimmers (Phase 78).

## 2026-08-23 — Freestyle data pass (notebook) + narrowed decisions

Ran a data-grounded pass on **all 22 annotated freestyle sessions** — 3 swimmers: **Tony 8, Leo 8,
Max 6**. Max is a new 08-22 labeling push; the state above knew only Tony/Leo for freestyle (it said
free 16). Notebook `freestyle_segmentation.ipynb` (executed, figures inline); scratch
`scratch/phase80_freestyle.py`, figs in `figs/`. All numbers re-derived from the DB, not cited.

**Findings (freestyle):**
- **Cadence is already good; COUNT is the failure.** Production wavelet paired-k2 hits the exact cycle
  count on only **6/21 (29%)** well-labeled sessions (median |Δcount| = 1 cycle), yet median
  **stroke-rate error = 3.8%**. The coach-facing *rate* is already trustworthy; the *count* is not.
- **Bias ≈ 0** (matched-boundary median signed error ±0.01 s; matched MAE ≈ 0.07 s). ⚠ **This overturns
  D1's central premise for freestyle:** there is no constant offset to forgive — the error is
  *miscount*, not a uniform shift, and the "8-in-1-s" degenerate is not the observed failure. **D1(c)
  offset-tolerance is inert here; D1(a) count + D1(b) cadence are the whole game.**
- **The wavelet undercounts fast tempo (Max).** The DP ridge's low-band bias
  (`_RIDGE_LOW_BAND_BIAS = 0.5`) tracks a subharmonic on Max's dense high-cadence signal → dropped
  cycles (worst −4, SPM −33%). Unpaired wavelet already undercounts arm entries (16 vs 19), pairing
  compounds it. Tony/Leo (moderate tempo) are largely fine → a real cross-swimmer generalisation miss,
  concentrated on the swimmer the incumbent was never tuned on.
- **peakpick (find_peaks on 3-s-detrended velocity) beats the wavelet** overall (median F1 0.542 vs
  0.471 @±0.15 s) and *dramatically* on Max (0.19 → 0.81). Failure mode is the opposite — over-counts
  intra-cycle bumps. Recorded as the **rejected-but-documented fallback** (see D6 risk).
- **Tolerance sweep climbs** (wavelet 0.09→0.82 across ±0.05→±0.30 s) with matched MAE ≈ 0.07 s → events
  roughly right, misses are count/recall not gross misplacement.
- **Partial labels contaminate** — 4 sessions carry 3–8 marks over 6+ real cycles → F1 = 0.00 by
  construction. `segmenter_eval.coverage()` (ratio ∈ ~[0.7, 1.4]) must gate them before any aggregate.
- **The production swim WINDOW is a second, independent error source** (annotated→production median F1
  roughly halves; several windows start at t≈0 across the dive). **Out of scope this phase** (D5) —
  logged for a future window pass (STATE items 11/12).

**Decisions locked this session (narrow the 2026-08-21 set — user, AskUserQuestion):**
- **D4 — Freestyle only, this phase.** Measure + improve freestyle (3 swimmers / 22 sessions).
  Breast/back/fly deferred; D2's all-four *metric design* still stands, but the *improve* scope is
  freestyle. Supersedes the "all four strokes" framing above **for this phase**.
- **D5 — Measure on the ANNOTATED window; interior segmenter only.** The swim-window error is real but
  stays a Phase 75–79 concern. Scoring is on `[stroke_start_s, finish_s]`; the production-window
  reconciliation (old Q3) is downgraded from deliverable to logged finding.
- **D6 — Improve by RE-TUNING the wavelet only (no segmenter swap).** Keep `segment_cycles_wavelet`;
  levers = ridge **low-band bias** (prime suspect for Max's undercount — Phase 65-02 already zeroes it
  on a low-rail guard), pairing **k**, scale grid (`_PERIOD_MIN_S`). peakpick stays out of production.
  ⚠ **Risk (mine, flagged to user):** if a LOSO bias/k sweep can't close Max's undercount to target,
  D6 (swap) must be **revisited**, not silently shipped as a still-undercounting wavelet — the plan
  needs that gate.

### 2026-08-23b — stroke-detection probe (D6 hypothesis CONFIRMED, + a reframe)
User reframe: **the human marks ARE strokes (arm entries); a cycle = 2 strokes — so detect strokes,
not cycles.** Detecting strokes directly (the wavelet ridge's integer phase-crossings, **no k=2
pairing**) removes the step that halves the count and compounds the fast-tempo undercount. Probe:
`scratch/stroke_probe.py`; script fig `figs/05_detecting_strokes.png` + `visualize_freestyle_seg.py`
stroke table. Scored **stroke count vs marks directly** (well-labeled sessions):

| stroke detector | exact-count | median \|ΔN\| | rate err |
|---|---|---|---|
| wavelet ridge **bias 0.5** (shipped, unpaired) | 29% | 1.0 | 3.8% |
| **wavelet ridge bias 0.0 (no low-band)** | **38%** | 1.0 | **3.2%** |
| peakpick | 0% | 7.0 | 46% |

- **The low-band bias IS Max's undercount (D6 confirmed).** Max's −4 session: 18 true strokes →
  shipped ridge **8** → bias-0 **17**; his 00:45: 19 → 14 → **19 exact**. Turning the bias off recovers
  the dropped strokes with no other change.
- **peakpick is rejected on the real metric.** Its ±0.15 s F1 (0.54) looked best but is high-recall
  *over*-detection — 0% exact count, ~3× overcount (Leo 11→38), 46% rate error. Scoring count directly
  exposes it. (Corrects this session's earlier "peakpick beats the wavelet" read.)
- **Cost of a blanket bias flip:** slight +1 *over*count on moderate tempo (Tony/Leo) and looser
  placement (F1 0.53→0.42). → the real fix is likely an **adaptive** low-band bias (bias 0 only when
  the ridge rails low / fast tempo — the Phase 65-02 low-rail-guard pattern), not a global 0. Plus a
  small merge/prominence post-filter for the +1s. Placement loss is acceptable under D1 (count > placement).
- **Reframe for the plan:** target = **stroke detection at the fundamental** (adaptive-bias ridge,
  drop k-pairing), report **stroke count + stroke rate**; a cycle is `strokes / 2`. Still D6 (re-tune
  `segment_cycles_wavelet`'s ridge), not a swap.

## Approach (synthesis — confirm at plan time, these are mine not the user's)

**Sequence: measure → improve** (the Phase 78 shape, for cycle boundaries this time). **Narrowed by
D4/D5/D6 — freestyle only, annotated window, re-tune wavelet.**
- **Step 1 — count/cadence metric + freestyle re-measurement.** Extend `segmenter_eval.py` with the
  count + cadence metrics behind a `coverage()` gate; score the incumbent on the **annotated** window
  (`[stroke_start_s, finish_s]`), per swimmer (Tony/Leo/Max). Reproduce this session's numbers as the
  committed baseline (29% exact-count, 3.8% SPM err, bias≈0). No detector changes. The notebook is the
  prototype; the fixture/CLI form is the deliverable.
- **Step 2 — re-tune `segment_cycles_wavelet` for freestyle (D6).** Sweep `_RIDGE_LOW_BAND_BIAS`
  (prime suspect), pairing `k`, and `_PERIOD_MIN_S`, **LOSO by swimmer** (hold Max out — the fast
  regime is the generalisation test, not fit). Ship only if it beats the incumbent count/cadence on
  held-out Max **and** doesn't regress Tony/Leo. If it can't → escalate to the D6 swap gate.
- Keep the existing ±0.15 s F1 reported but demoted, for continuity with the 59 fixture regression.

## Open questions for planning

- **Q1 (still the crux) — the count/cadence metric's exact form**, now with freestyle evidence
  (bias≈0, so *drop* offset-tolerance weight — D1(c) is inert). Shape: (a) **exact-count rate** +
  median |Δcount|; (b) **stroke-rate %err** + interval CV, both behind a `coverage()` gate. Must still
  reject the "8-in-1-s" degenerate and be validated on **synthetic cases** (uniform shift → pass;
  crammed → fail; dropped/extra → fail), not only the corpus.
- **Q6 (new) — the tuning protocol.** LOSO **by swimmer** (Tony/Leo/Max), not by session, so Max's fast
  regime is a held-out generalisation test. Fix the pass/fail threshold up front (e.g. held-out-Max
  exact-count rate ↑ and |SPM err| ↓ vs incumbent, no Tony/Leo regression). This is R2's mitigation.
- **Q2 — count ground truth for back/breast → DEFERRED by D4** (freestyle only this phase).
- **Q3 — production-window reconciliation → DOWNGRADED by D5** to a logged finding (window is a
  separate Phase 75–79 concern), not a Step-1 deliverable.
- **Q4 — re-tune vs swap → ANSWERED: re-tune the wavelet only (D6)**, with the swap gate as fallback.
- **Q5 — comparability / backfill.** If re-tuning moves freestyle `stroke_count` / `stroke_rate_spm`,
  that's a comparability break of the Phase-57/59-D7 class. Report-only (dry run) in the tuning plan,
  DB write a later plan? (Phase 59 D20 precedent.) **Still open.**

## Risks

- **R1 — the cadence metric IS the phase.** A weak definition either smuggles placement-sensitivity
  back in (re-making 59's mistake) or lets degenerates through. Mitigation: Q1's synthetic test battery
  before any corpus number is trusted.
- **R2 — single swimmer / single annotator.** New metric is offset-tolerant, but tuning to this corpus
  is still tuning to these 4 people (Phase 78). State at the top; the fixture must not become the
  definition of "correct".
- **R3 — the annotation wall is softened, not gone.** Back/breast still need *some* count truth; if the
  labeling push doesn't happen, those strokes stay measured-and-flagged, not tuned.
- **R4 — the 59 fixture regression pins F1.** Overturning D3 must not silently delete that assertion;
  the new metrics get their own fixture assertions and F1 stays as a demoted continuity check.

## Out of scope

- Flipping `segmentation_reliable` (not chosen; a trust decision, not this measure/improve arc).
- Unblocking the Swim-phase metrics (75-04+) — separate, even though `splits` / `sr_dps_coupling` /
  `dead_spot_timing` will benefit downstream.
- The four *phase* boundaries and their detectors (Phases 75–79) — this is cycle boundaries only;
  the swim-window error (D5) is logged but not fixed here.
- **Breaststroke / backstroke / butterfly (D4)** — freestyle only this phase; the count/cadence metric
  is designed once (D1/D2) but only exercised + tuned on freestyle now.
- Training a learned model on this corpus (Phase 59 D2 still holds — too small, too homogeneous).
- iOS / web report-card UI changes.

---

*Numbers in the 2026-08-23 section are re-derived live in `freestyle_segmentation.ipynb`, per the house
rule that CONTEXT numbers are reproduced, not cited. The 2026-08-21 F1 priors above are superseded for
freestyle by that pass (annotated-window wavelet ≈ 0.47, reproducing Phase 59's 0.458).*
