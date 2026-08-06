---
phase: 16-freestyle-support
plan: 03
status: complete
---

# Summary: Pan Matrix Profile / motif-heatmap spike

## Verdict

The spike runs and (after a mid-run API bug fix) produces a real, readable
multi-length conservation surface — but it answers a different question than
the one freestyle segmentation needs, and that gap is the headline finding.
`stumpy.stimp` shows *which subsequence lengths are well-conserved when*; it
does not produce a segmentation, or even a rule for picking one length over
another at a given moment. The user could read structure off the heatmap that
the pipeline itself has no mechanism to act on — the same "why can a human see
it and the machine can't" gap that prompted this plan in the first place, now
observed concretely rather than hypothesized.

- **API bug, found and fixed mid-spike**: `pmp.PAN_` is binarized by stumpy's
  design (`pan(threshold=0.2, ..., binary=True)` — confirmed by reading
  `stumpy/stimp.py` directly), returning only `{0., 1.}` at an untuned
  threshold. The spike's docstring had assumed it was the continuous
  conservation-strength gradient `mp_distance` already plots. Switched to
  `pmp.pan(binary=False, contrast=False)` (range ≈ `[0.1, 0.64]`), which is
  the actual continuous surface. Re-ran; the corrected heatmaps showed real
  structure where the binarized version had shown a sparse scatter of dashes.
- **Real structure is visible — vertical and diagonal bands.** User's read
  across 8 sessions: *"There are clear distinct vertical dark bands. Sometimes
  there are clear diagonal bands."* Vertical bands = a length that stays
  well-conserved across a stretch of time (a stable stroke-shape regime,
  exactly what 16-01/16-02 were chasing); diagonal bands = the conserved
  length *drifting* over time (the regime itself changing shape/duration
  continuously, not switching between discrete templates).
- **Open thread, deliberately left unresolved**: user also observed *"all of
  them drift toward shorter bands as time increases."* Two readings stayed
  live — (a) a real physiological finding (tempo increasing as the swim
  progresses — fatigue or pacing), or (b) a structural artifact of the masked
  self-join (longer windows have systematically fewer valid match candidates
  near the masked tail, which could *manufacture* an apparent bias toward
  shorter conserved lengths late in the session regardless of the swimmer's
  actual tempo). A cross-check (`_drift_check.py` — compare measured
  inter-peak stroke period early vs. late in each session, independent of
  PMP) was drafted to distinguish the two, but the user pivoted to wavelet/CWT
  before it ran. Left unrun and the scratch file removed — re-derivable in
  minutes from `segment_cycles`'s existing trough-cycle output if anyone
  revisits PMP.

## What was built

`segment_motif_spike.py` — standalone spike file (same standalone-file +
human-eyeball-checkpoint convention as 16-01/16-02). `find_pmp(t, vel, ...)`
runs `stumpy.stimp` to convergence over the masked active region (same
baseline/tail masking as prior spikes — the dive/pulldown contamination 16-02
found is still present and unaddressed here, by design: out of scope for this
plan) and returns a `(PAN, M, fs)` triple; `_add_motif_heatmap` renders it as
a length × time heatmap with `m_len` marked for reference against 16-01/16-02's
fixed-length choice.

## Why this matters more than a pass/fail on PMP itself

16-01 found single-template motif-matching regime-locks (one shape, picked
once, can't track drift). 16-02 found chains and CAC don't do better, plus
surfaced the dive/pulldown contamination problem. This spike's premise was:
*if* the real obstacle is "we're matching at the wrong fixed length," searching
across lengths should reveal the right one(s) to use, locally, over time.

It does reveal something — the bands are real, reproducible, and exactly the
kind of "regime + drift" structure the diagnosis predicted. But a heatmap is a
*visualization* of where conservation is strong, not a *decision rule* for
"use length L starting at time T." Converting "I can see a diagonal band" into
"the algorithm now knows to switch lengths here" would be a whole second spike
— ridge-tracking across the length axis, then re-deriving cycle boundaries
from whatever length the ridge points to at each moment. That's substantial
new machinery layered on top of a technique (self-join shape-matching) that
16-01/16-02 already showed has a structural ceiling (regime-locking,
contamination) independent of which length it's locked to.

In short: PMP answers "where would shape-matching work best, and at what
scale, if you were going to do it" — but doesn't remove any of the reasons
16-01/16-02 found shape-matching itself to be the wrong tool.

## Recommendations (closes out the shape-matching line, reaffirms 16-01 #1)

This is the third spike in a row (single-template, chains/CAC, multi-length
PMP) where a shape-matching variant produces *some* signal a human can read
but no clean machine-actionable rule, while drift and contamination keep
showing up as the dominant confounds regardless of technique. That convergence
is itself the finding: the family is structurally mismatched to "stroke shape
that continuously drifts," not just under-tuned.

1. **Wavelet/CWT stroke-rate ridge — now the clear next step, not just the
   front-runner.** Reframes the question from "does this shape match that
   shape" (the thing all three spikes here showed breaking down under drift
   and contamination) to "what's the dominant oscillation frequency right now"
   — a question where drift is the expected, trackable output (a ridge *is*
   a time-varying rate estimate) rather than a confound to fight. See
   16-01-SUMMARY's mechanism sketch (`Φ(t) = ∫rate(t')dt'`, integer-crossings
   → boundaries) and `CLAUDE.md`'s "Wavelet notes" (Morlet `cmor1.5-1.0`,
   3-second rolling-mean detrend recipe).
2. **Shape-matching family (motifs, chains, CAC, PMP) — close the thread.**
   Four spikes is enough to call it: every variant either regime-locks, fails
   to outperform the simplest version, is structurally inapplicable on short
   sessions, or (here) surfaces real structure with no path to a decision
   rule — and all of them sit on top of the same masked region 16-02 showed
   contains a non-stroke phase. Park this family; don't spend a fifth spike
   on a new shape-matching variant without a reason to think the family-level
   diagnosis above doesn't apply to it too.
3. **Dive/pulldown re-masking — still cheap, still untried, now lower
   priority.** 16-02 flagged `detect_initial_phase`'s `initial_phase_end_idx`
   as a near-free re-masking probe. Still true, but with the shape-matching
   family being parked, its main value (derisking a shape-matching fallback)
   mostly evaporates. Worth revisiting only if wavelet/CWT stalls.

Pose/IMU sub-phase work and HMM labeling remain correctly parked, per 16-01 —
both still blocked on data that doesn't yet exist.
