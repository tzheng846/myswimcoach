---
phase: 16-freestyle-support
plan: 02
status: complete
---

# Summary: Time-series chains + Arc Curve spike

## Verdict

Neither candidate solves the regime-locking problem 16-01 found, and a third,
independent structural problem surfaced mid-checkpoint that's arguably more
consequential than either candidate's pass/fail result.

- **Chains do not outperform single-template motif-matching.** Tested across
  all 11 sessions now in play (16-01's 4 + 7 more added mid-checkpoint:
  `sid_br_1/2`, `jimmy_br_1`, `connor_br_1..4`). User's verdict: *"chain never
  seem to outperform motif. Under good data conditions, motif match did the
  best."* On `leo_br_1`, the one session read in per-anchor detail, the chain
  didn't escape regime-locking — it relocated it (picked up some slow strokes
  the template missed, dropped 5 fast ones the template caught).
- **Arc Curve / CAC produced no valley anyone read as a real regime-change
  signal**, and on short sessions it cannot in principle: FLUSS's exclusion
  zone exceeded the active region's length on `jimmy_br_1`, structurally
  pinning the "detected" change to the boundary regardless of the signal.
- **New finding — the "active swim region" both spikes mask on isn't
  internally homogeneous.** It contains a dive-surge + underwater-pulldown
  phase that production code already detects and excludes from stroke counts
  (`detect_initial_phase`), but which the spike's masking (only
  `detect_phases`'s `baseline_end`/`swim_end`) leaves inside the region handed
  to the self-join — see below. In several sessions this phase is a sizeable
  fraction of what gets treated as "uniform repeating strokes."

## What was built

Extended `segment_motif_spike.py` (still standalone — no production file
touched, per the plan's boundary) to thread `find_motif_anchors`'s
previously-discarded matrix-profile columns into two new passes that reuse the
same masked self-join — no new self-join, no new dependency, no new threshold
logic:
- `find_chain_anchors` — `stumpy.allc(IL, IR)` on `mp[:,2:4]` → longest
  unanchored chain → same `{cycle_num, peak_idx, start_idx, end_idx}` shape as
  motif anchors, via a new shared helper `_anchors_from_marks`
- `find_regime_change` — `stumpy.fluss(I, L=m_len, n_regimes=2)` on `mp[:,1]`,
  sliced + rebased to the active region first. (Naive full-array FLUSS hijacks
  onto the masked baseline — the same *shape* of bug as 16-01's Round 1, just
  surfacing in a different function. Verified the slice+rebase fix against all
  4 original sessions before trusting any CAC output.)

Mid-checkpoint, reworked the figure layout at user request: the original
combined trough+motif+chain overlay (three colors/dash-styles of vertical line
sharing one axes) became unreadable once anchor density grew across the wider
session set ("having red green and gray line is too confusing"). Now one
segmentation method per row — 5 rows × n cols (trough / motif / chain /
matrix-profile / arc-curve), same velocity trace and shared time axis — so
methods are compared by scanning down a column rather than disambiguating
overlapping colors.

Final session set tested: `leo_br_1`, `carlos_fr_1`, `carlos_fl_1`,
`swim_lucas_fl_1` (16-01's set, per plan) + `sid_br_1`, `sid_br_2`,
`jimmy_br_1`, `connor_br_1..4` (added mid-checkpoint at user request, to widen
the read past 16-01's 4-session sample).

## Chains: relocate regime-locking, don't escape it

`leo_br_1` was the one session read in per-anchor detail (user's read,
verbatim): *"green line is trying to segment the slower paces in leo_br_1...
On the faster strokes of leo_br_1, it missed 5 strokes."* 16-01's template had
locked onto `leo_br_1`'s *fast* strokes only (11 anchors, all fast — slow ones
undetected); the chain (6 anchors) did roughly the mirror image. Net effect:
not "more total coverage" but two different partial slices of the same
22-cycle session, each anchored on whichever shape-family the discovery
process happened to start nearest. That's not an escape from the Round 2
diagnosis — it's the same failure mode wearing a different hat: single-
*sequence* approaches (a match list or a chain — structurally the same kind of
object) lock onto whichever regime they start in and don't cross into others.
Across the wider 7-session set, the user's verdict generalized cleanly: chains
never beat the template, and the template does best when the input is
otherwise clean.

## Arc Curve / CAC: no usable signal, and provably broken on short sessions

No session in either set produced a CAC valley the user read as lining up with
a real shape-population boundary. `jimmy_br_1` demonstrated *why* CAC can fail
in a way that's not about signal quality at all:

```
masked baseline [0:265] ...  active region 9.3s (931 samples), m_len=180
CAC regime change @ idx=265        ← exactly equals baseline_end
```

`jimmy_br_1` has the longest `m_len` in the set (180 samples ← `T_est=1.8s`,
also its lowest cycle count: 5). FLUSS's default exclusion zone is
`5 × m_len = 900` samples per side — almost the entire 931-sample active
region. There's no interior left to search; the "detected" change is
structurally pinned to the boundary by the algorithm's own bookkeeping,
independent of the underlying signal. **CAC/FLUSS is likely inapplicable to
recordings short relative to the stroke-cycle window length** — a hard
limitation, not a tuning question.

## New finding: the "active" region contains a non-stroke phase

User's read across the wider set: *"once other phases are included, such as
breaststroke pulldown, it breaks down."* Checked this directly against
`metrics.detect_initial_phase` (which already exists in production to identify
"dive surge" and "pulldown" peaks and exclude them from stroke counts —
`STATE.md`: *"Peaks before trough = dive/pulldown; not counted as strokes"*) —
it bears out precisely:

| session | pulldown? | duration | % of what the spike treats as "active" |
|---|---|---|---|
| sid_br_1 | yes | 0.09s | 5% |
| sid_br_2 | no | — | 0% |
| jimmy_br_1 | yes | 0.09s | 23% |
| connor_br_1 | yes | 1.08s | 29% |
| connor_br_2 | yes | 0.12s | 19% |
| connor_br_3 | yes | 1.16s | 25% |
| connor_br_4 | yes | 1.35s | 25% |

In `connor_br_1/3/4`, roughly a **quarter to nearly a third** of the region the
spike (and 16-01 before it) feeds wholesale into `stumpy.stump` is dive-surge +
underwater pulldown — a single large pull-and-glide, structurally nothing like
a repeating oscillatory stroke cycle. That's a different *kind* of signal
inside a region every method here assumes is one uniform population — not
"drift" (16-01's framing: the same motion gradually changing shape) but an
actual phase boundary the masking doesn't know about.

(Checked whether contamination % cleanly predicts each session's motif-match
coverage — it doesn't: `connor_br_4` has both high pulldown share (25%) *and*
high coverage (10/11), so other variables are clearly mixed in too, e.g.
`connor_br_2`'s cycle count (16) is nearly double any other session's, hinting
at a faster/more-variable stroke rate as its own confound. What *is* clean is
narrower but solid: the masking leaves a structurally-different motion type
inside the region every shape-based method here assumes is uniform strokes —
a real, quantified gap, not a guess about why any one session struggled.)

**A plausible fix already exists in production code, cheap to test**:
`detect_phases` only returns `baseline_end`/`swim_end`, but
`detect_initial_phase` already computes a finer `initial_phase_end_idx` (the
"first deep trough" after baseline) that the spike's masking doesn't reach
for. Re-masking `[baseline_end:initial_phase_end_idx]` in addition to
baseline/tail — still production-derived boundaries, still no new threshold
logic — is a natural, nearly-free next probe for anyone continuing down the
shape-matching road. Not run here (out of scope for this plan; chains/CAC was
the question on the table, and the chains verdict above means the
shape-matching *family* looks weak even before considering input
contamination).

## Recommendations (sharpens 16-01-SUMMARY's ranking, doesn't replace it)

16-01 ranked wavelet/CWT ridge #1 and multi-template `stumpy.motifs` #2. This
spike's results widen that gap:

1. **Wavelet/CWT stroke-rate ridge — strengthened to a clear front-runner.**
   Three single-sequence shape-matching variants have now failed the same way
   (template, chain) or proven structurally inapplicable in places (CAC) — and
   none of the three would even see clean input, given the dive/pulldown
   contamination above. A frequency-domain reframing ("what's the dominant
   oscillation *right now*") sidesteps every one of these failure modes by
   construction, including contamination (a brief non-periodic pulldown
   wouldn't derail a rate estimate the way it derails shape-matching). See
   16-01-SUMMARY's mechanism sketch (`Φ(t) = ∫rate(t')dt'`, integer-crossings
   → boundaries).
2. **Multi-template `stumpy.motifs` — weaker case than 16-01 had it.** Ranked
   #2 there as "shrinks the blind spot rather than closes it." This spike adds
   a second, independent reason to discount it further: even a perfect
   multi-template merge still operates on an active region containing a
   structurally distinct dive/pulldown phase — contamination that affects
   every shape-based candidate equally, template count notwithstanding.
3. **Dive/pulldown re-masking — worth a cheap, fast, independent look**,
   precisely because the boundary-detection code already exists and is already
   production-tested (near-zero new-code cost). Most likely outcome per the
   chains verdict: shape-matching gets *less bad* but the regime-locking
   ceiling remains — which would still point back to #1. But "cheap to check,
   could meaningfully derisk a fallback" makes it worth a look regardless.

Pose/IMU sub-phase work and HMM labeling remain correctly parked, per 16-01 —
both still blocked on data that doesn't yet exist.
