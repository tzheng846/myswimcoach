---
phase: 59-segmenter-evaluation
plan: 04
subsystem: testing
tags: [segmentation, exploration, loso, learned-model, matched-filter, trough, tether-sag]

requires:
  - phase: 59-segmenter-evaluation (59-01)
    provides: the harness, the annotated corpus, and the incumbent scores
  - phase: 59-segmenter-evaluation (59-03)
    provides: detect_swim_window, which Task 1 wired into the harness's production framing
provides:
  - "tools/segmenter_candidates.py — 6 candidates, LOSO-scored, per-stroke ranked"
  - "A per-stroke recommendation for 59-05"
  - "CONTEXT D13 answered: the trough segmenter does not transfer, with the mechanism"
  - "A measured negative on tether-sag as an explanation for poor segmenter agreement"
affects: [59-05 ship, a future tether/hardware plan, 53-attention-allocation]

tech-stack:
  added: []
  patterns:
    - "Leave-one-session-out as the default for any tuned candidate"
    - "Verify a negative result is not an implementation artifact before reporting it"

key-files:
  created: [tools/segmenter_candidates.py]
  modified: [tools/score_segmenter.py, tests/test_segmenter_eval.py]

key-decisions:
  - "Resolve the plan's own AC-1-vs-boundary contradiction in favour of AC-1"
  - "Ground truth going forward is the TRACE, not the video (user decision)"
  - "Proceed to 59-05 as scored despite the sag question (user decision)"

patterns-established:
  - "A low-capacity model can be LOSO-safe where a high-capacity one would not be"
  - "Test a physical hypothesis against the data before acting on it"

duration: ~1.5h
started: 2026-08-09
completed: 2026-08-09
---

# Phase 59 Plan 04: Segmenter Exploration — Summary

**Six candidates scored leave-one-session-out: butterfly has a clear winner (0.317 → 0.591), freestyle has a marginal one, the trough segmenter is definitively dead, and the learned model did not overfit — contradicting 59-01's prediction for a reason worth understanding.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1.5 h |
| Tasks | 3 auto, 0 checkpoints (`autonomous: true`) |
| Files | 1 created, 2 modified — **all outside `metrics.py`** |
| Suite | 269 pass |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Harness measures production | **Pass** | `_windows()` now mirrors `compute_session_metrics` including the `None` fallback. Re-baseline recorded below. |
| AC-2: LOSO for tunable candidates | **Pass** | L1 scored leave-one-session-out and in-sample, side by side. |
| AC-3: Candidate budget across families | **Pass** | 6 candidates + 2 incumbents; all four families represented. |
| AC-4: Trough question answered | **Pass** | 0.000 on every stroke, and verified not an artifact — mechanism below. |
| AC-5: Ranked per-stroke recommendation | **Pass** | Printed with F1 (LOSO), MAE and boundary-count ratio. |

## Results (annotated window, F1 @±0.15 s, median per session)

| candidate | freestyle | butterfly | breaststroke |
|---|---|---|---|
| wavelet (incumbent) | 0.458 | 0.317 | 0.232 |
| peakpick (incumbent) | 0.437 | **0.524** | 0.308 |
| R1 snap→vel min | 0.352 | 0.241 | 0.232 |
| R2 snap→steep rise | **0.485** | 0.233 | 0.239 |
| C1 matched filter | 0.437 | 0.000 | 0.146 |
| C2 trough untrimmed | 0.000 | 0.000 | 0.000 |
| C3 autocorr grid | 0.358 | 0.472 | 0.258 |
| **L1 learned (LOSO)** | 0.375 | **0.591** | **0.359** |
| L1 learned (in-sample) | 0.375 | 0.600 | 0.296 |

**Recommendation for 59-05:** butterfly → L1 or peakpick (+0.27, large); freestyle → R2 (+0.027, marginal); breaststroke → L1 (+0.13, but n=2 — weak).

## Findings

### The learned model did not overfit, and 59-01's prediction was wrong
LOSO vs in-sample differ by ~0.01 (butterfly 0.591/0.600, freestyle 0.375/0.375). **Mechanism: logistic
regression on 5 features is too low-capacity to memorise 236 marks.** ⚠ This does NOT license a
bigger model — a higher-capacity learner on this corpus would behave exactly as 59-01 feared. The
result is "a small model generalises here", not "the corpus is big enough to train on".

### The wavelet is the wrong tool for butterfly
Beaten nearly 2× by two unrelated methods (L1 0.591, peakpick 0.524 vs 0.317). Consistent with
59-01's finding that the ridge sometimes locks onto the two-dolphin-kick harmonic.

### Refinement works for freestyle, but trades events for precision
R2 wins at every tolerance below ±0.30 (±0.05: 0.167 vs 0.136; ±0.10: 0.382 vs 0.255) and **loses at
±0.30** (0.774 vs 0.836). It tightens placement while dropping a few events. That trade is 59-05's
call, not this plan's.

### CONTEXT D13 answered — the trough segmenter does not transfer
0.000 on every stroke on the **untrimmed** trace. **Verified not an implementation artifact:** it
finds 9–33 troughs per session, but on freestyle/butterfly **zero land inside the swim window** —
they sit in the baseline (t≈0–2 s) and the dead tail (t≈14–27 s). *During actual stroking, velocity
never drops below 0.20 × v95.* Breaststroke does get 12 in-window troughs (it has real glides) yet
still scores 0.000 until ±0.30 (0.176) — a systematic **phase offset**: right events, wrong point of
the cycle. The method is breaststroke-shaped and should stop being carried as a candidate.
⚠ It could not have shipped as a registry value regardless: the 59-02 contract hands a segmenter the
already-sliced window, and C2 needs the trace that was cut away.

### Tether sag investigated — real, directional, but too small to explain the gap
Raised by the user after Task 3: the encoder sits ~0.5 m above water on an **inextensible, free-spool**
line, so sag grows with paid-out length and could decouple the trace from the swimmer late in a swim.
Two tests:

**(a) Does error grow within a swim?** Yes, monotonically, and with the sign sag predicts (trace
boundaries *later* than video marks):

| position in swim | mean \|error\| | signed mean |
|---|---|---|
| first third | 0.150 s | +0.008 s |
| middle | 0.197 s | +0.041 s |
| last third | 0.235 s | +0.066 s |

13/19 sessions show larger error in the last third.

**(b) Do chart-timed and video-timed labels disagree as predicted?** **No.** The corpus is
inhomogeneous — 58-02 shipped mark-at-playhead on 2026-08-07, so only the 08-07 batch could be
video-timed and everything earlier was necessarily clicked on the chart. If sag decoupled the two at
the scale needed, chart-timed labels should score clearly higher. They do not:

| label source | n | median F1 | mean |
|---|---|---|---|
| chart-timed (pre 08-07) | 8 | 0.308 | 0.428 |
| video-timed (08-07) | 12 | 0.379 | 0.370 |

**Conclusion:** the ~60 ms drift is real and points the right way, but it is an order of magnitude too
small to explain F1 ≈ 0.3, and it leaves no fingerprint on label provenance. *"The CWT was right all
along and the annotations were wrong"* is **not supported at corpus level.**
⚠ An aggregate test cannot refute a specific per-session observation, and n=8 vs 12 is thin. The
decisive experiment is narrow and cheap: **mark one swim from the trace alone and from video alone,
and measure the divergence against distance directly.** Not done here.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Resolve AC-1 vs the boundaries section in favour of AC-1 | The 59-01 pins CONTAIN production-window values, so "re-baseline the column" and "the pins must not move" cannot both hold | 8 pins re-baselined; the annotated column did not move, proving containment |
| Ground truth = the **trace**, not video | The product only ever has the trace; scoring against video sets an unreachable target, and Phase 53's within-athlete contrast needs self-consistency, not absolute biomechanics | ⚠ **Inverts 59-01's quality ordering** — the 08-07 batch that was best-*covered* is now the least appropriate ground truth, since its marks describe the swimmer |
| Proceed to 59-05 as scored | Butterfly's 0.317 → 0.591 gap is far larger than a 60 ms drift could explain, so that conclusion survives the sag question | 59-05 planned from this table |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Plan self-contradiction resolved | 1 | Required; documented |
| Scope additions | 1 | Sag investigation, user-raised |
| Deferred | 2 | Both recorded below |

**1. [Plan defect] AC-1 and the boundaries section contradicted each other.** AC-1 required
re-baselining the production-window column; the boundaries said the 59-01 pins "must not move". The
pins contain production-window values. Resolved in favour of AC-1 (the explicit intent), 8 pins
across 4 fixture sessions updated. **The annotated column did not move** — the containment proof.

Production-window re-baseline (59-01 → now, entries F1): wavelet freestyle 0.31 → **0.35**, butterfly
0.33 → 0.32, breaststroke 0.48 → **0.18**; peakpick butterfly 0.37 → **0.44**, breaststroke 0.21 → 0.27.

**2. [Scope addition] The tether-sag investigation.** Not in the plan; raised by the user mid-flight
as a challenge to the validity of the ground truth itself. Two measurements run before answering.
Reported above.

### Deferred
- **The trace-vs-video divergence experiment** — both mark sets on one session, measured against
  distance. The only test that can settle the user's observation.
- **The hardware fix** — lowering the encoder toward water level. Future collection only; does
  nothing for the existing corpus.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| C2 scored 0.000 everywhere — possible broken implementation | Verified by inspecting raw trough positions: real troughs, all outside the swim window. A genuine mechanism, not an artifact. |
| `git diff` appeared to show `metrics.py` modified | 59-03's work is uncommitted, so the diff is cumulative. Line counts (289/4/49/94) identical to 59-03's close ⇒ untouched by 59-04. |

## Next Phase Readiness

**Ready**
- 59-05 can be planned directly from the table. Candidates already match the 59-02 registry contract.
- Boundary-count ratios measured for `k`: wavelet 2.27, peakpick 3.47, L1 2.17, R2 2.25.
  ⚠ **A winner that is not ~2.27 means the pairing divisor must be RE-MEASURED, not inherited.**

**Concerns**
- ⚠ **The ground-truth definition changed mid-phase.** Scores in 59-01 through 59-04 were computed
  against a corpus that mixes chart-timed and video-timed marks. Under the new "trace is truth" rule
  the 08-07 batch is the *less* appropriate half. Nothing was re-scored on that basis.
- ⚠ **sklearn is `tools/`-only.** Shipping L1 puts it on the Railway production path — an explicit
  decision for 59-05, not a side effect.
- ⚠ Breaststroke rests on **n=2**. Any breaststroke recommendation is weak.
- ⚠ Carried from 59-03 and untouched: butterfly/breaststroke window regression, 17/36 fallback rate.

**Blockers**
- None.

**⚠ Phase 59 is 4 of 5 plans.** 59-05 (ship the winner) remains.

---
*Phase: 59-segmenter-evaluation, Plan: 04*
*Completed: 2026-08-09*
