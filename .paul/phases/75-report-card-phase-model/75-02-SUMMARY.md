---
phase: 75-report-card-phase-model
plan: 02
completed: 2026-08-19
status: complete
files_modified:
  - metrics.py
  - annotations.py
  - phase_metrics.py
  - api.py
  - tests/test_metrics.py
  - tests/test_annotations.py
  - tests/test_api.py
  - tests/test_phase_metrics.py
  - tests/test_recompute.py
  - tools/score_underwater.py       (new)
  - tools/backfill_phases.py        (new)
---

# 75-02 SUMMARY — underwater start boundary + the four window metrics

## What shipped

1. **`metrics.detect_underwater_start(t, vel, baseline_end_idx)`** — the coach's own rule
   ("the underwater phase begins at the first big velocity dip"): from `baseline_end`, take the
   start-surge peak within 4 s, then the first velocity trough after it whose prominence is
   ≥ `0.40 × v95`. Returns a full-trace index or **None when it does not find one** — the same
   refuse-to-answer convention as `detect_swim_window`.
2. **`phase_metrics.resolve_boundaries(ctx)`** — the four race-phase boundaries resolved once per
   session with per-key provenance, precedence **coach annotation → auto** (P2). Emitted as
   `metrics_json.phases.boundaries` with a `sources` sub-dict; `schema_version` bumped **1 → 2**.
3. **Six specs flipped `planned → implemented`** — `uw_duration`, `uw_distance`, `uw_avg_speed`,
   `uw_surface_ratio`, plus `pulldown_peak_vel` / `pulldown_duration` for breaststroke only (P7).
4. **Both api.py call sites wired** — `/process` passes the seed + `initial_phase`;
   `POST /recompute` additionally reads `session_annotations.phases` so a coach's marks win there.
5. **`tools/score_underwater.py`** (accuracy harness) and **`tools/backfill_phases.py`** (library
   backfill). The backfill was applied to all 108 live sessions on 2026-08-19.

355 tests pass (317 before this plan, 324 after Task 1's detector tests were written at plan time).

## Measured accuracy — AC-1

Scored against the 38 hand-marked `underwater_start_s` annotations:

| prom frac | median err | mean abs err | within 0.5 s | within 1.0 s | missed |
|---|---|---|---|---|---|
| 0.25 | 0.00 s | 0.43 s | 29/38 | 29/38 | 0 |
| 0.30 | +0.01 s | 0.24 s | 33/38 | 33/38 | 0 |
| 0.35 | +0.01 s | 0.18 s | 35/38 | 36/38 | 0 |
| **0.40 (shipped)** | **+0.01 s** | **0.13 s** | **35/38** | **37/38** | **0** |
| 0.50 | +0.02 s | 0.24 s | 33/38 | 35/38 | 1 |
| 0.60 | +0.07 s | 0.74 s | 24/38 | 30/38 | 1 |

Per stroke at 0.40: breaststroke n=4 mean 0.03 s · butterfly n=17 mean 0.13 s · freestyle n=16
mean 0.15 s · udk n=1 0.10 s. The 0.30–0.40 plateau is broad and flat — not a knife-edge fit.
Three sessions land >0.5 s out; the worst is freestyle `a95d19e9` at **−1.73 s**.

**Incumbent replaced:** `baseline_end_s + dive_duration_s` (the top of the dive surge) fires on only
10 of 38, mean |err| **1.23 s**, 1/10 within 0.5 s, and is null on 84 of 108 live sessions because
`detect_initial_phase` needs TWO peaks to set `dive_detected`.

⚠ **CIRCULARITY CAVEAT — carry this forward.** The coach placed those 38 marks while looking at the
velocity trace on the annotate page, so "first big dip" may partly describe **how the mark is
clicked** rather than independent physiology. It remains the annotation contract's own definition of
the boundary, which is what makes it the right target for an auto seed — but the 0.13 s figure is
agreement with a human reading the same curve, not validation against ground truth. See the P4
finding below, which makes this caveat load-bearing rather than academic.

## Live outcome after the backfill

```
sessions: 108        schema_version histogram: {2: 108}
underwater_start_s sources: detected 64, manual 38, none 6
non-null uw_duration: 60 of 108      range 0.58 s – 15.89 s
rows still carrying session/cycles/initial_phase/data_quality: 108
```

The detector answers on **102 of 108**; 6 traces carry no qualifying dip and return null rather than
a guess.

⭐ **60 of 108 sessions ended up with a non-null `uw_duration`. The other 48 blank because the END
boundary is wrong, not the start.** That 48 is the real-world size of the breakout problem and is
the argument for scheduling it: the start boundary is now good to 0.13 s and 44% of the library
still cannot produce an underwater duration.

## Idempotency — AC-5, and the feedback loop it hid

A trap the plan did not anticipate: after the backfill, `metrics_json` **contains** `phases`, and
`build_seed` now reads `phases.boundaries.underwater_start_s`. A second pass therefore feeds pass
one's own output back into its own input. Simulated in memory across all 108 sessions:

```
identical: 108   drift: 0   skipped: 0
sessions where build_seed's underwater_start_s CHANGED between passes: 45
```

45 seeds moved and **zero boundaries shifted**, because `resolve_boundaries` deliberately ignores
the seed's `underwater_start_s` (it is the dive-peak value this plan replaces). That comment in
`phase_metrics.resolve_boundaries` is load-bearing — adding a seed fallback there would create a
genuine self-reinforcing loop. Do not "fix" it.

## ⚠ DEVIATION — P4 was wrong: the seed has no reader

**The plan's objective bullet 4 ("annotating a session drops from four marks to one") and P4 ("the
first-dip rule replaces the dive-peak derivation EVERYWHERE, including the annotate-page seed") were
written without checking whether anything renders the seed. Nothing does.**

`GET /sessions/{id}/annotations` returns `seed`, and the only file in `web/` that mentions it is
`web/app/app/annotate/[id]/page.js:123` — in a comment explaining why it is deliberately discarded:

> Phase 57 (D6): the editor starts BLANK. `annRes.seed` is still returned by the API and still
> useful to other callers, but applying it here would seed ground truth from the very segmenter
> this annotation exists to evaluate — circular, and it anchors the annotator toward the errors
> 16-06 is meant to find.

User's own observation on discovering this (2026-08-19): *"annotate does not show auto segmentation.
In fact as far as im aware there are no places for viewing auto segmenting for anything except
stroke segmenting."* Confirmed correct.

**Consequence:** AC-4 is satisfied *as written* — `build_seed` prefers the stored boundary, the
tests prove it, and the ordering walk still governs it — but its *purpose* is unmet. It is a correct
answer with no consumer. The plan's success criterion "the annotate page's pre-placed underwater
mark visibly improves on unannotated sessions" **cannot be met and is struck**, not deferred.

**Decision (user, 2026-08-19): close 75-02 as a data-layer plan; do NOT wire the seed into the
annotate page.** The argument for leaving it alone is the circularity caveat above: pre-placing the
detector's answer would turn a *suspected* circularity into a *structural* one — future coach marks
would be anchored to the detector, and scoring the detector against them would be measuring it
against itself. Phase 57 D6 is right; P4 was wrong. A read-only "ghost" overlay that displays the
auto boundaries without pre-filling anything saveable was offered and declined for now; it remains
the cheapest way to make auto segmentation *inspectable* without contaminating ground truth, and is
a reasonable Step-3 candidate.

## Boundaries respected

`detect_swim_window` / `detect_initial_phase` / `detect_phases` untouched. `compute_session_metrics`
and the cycle segmenter untouched — `git diff metrics.py` is a **single additive hunk** containing
only `detect_underwater_start` and its two constants, which is AC-6's guard. No schema change; every
byte rides in `metrics_json` jsonb. No mobile or `web/` changes.

## Next: 75-03 — the kick detector

**75-03 = the underwater kick detector + all seven kick metrics**: `kick_count`, `dist_per_kick`,
`kick_tempo`, `kick_consistency`, `per_kick_decay`, `first_kick_impulse`, `uw_ivv`. Split out of
this plan at plan time (P6) to keep it at PAUL sizing and give the detector its own verification
loop.

**Validation method, per the user's choice:** synthetic unit tests **plus Claude-generated plots of
the underwater segment with detected kicks marked**, for the user to eyeball. Note that 75-03
inherits the window this plan built — it is measurable on the 60 sessions that have one, and the
kick metrics will blank on the other 48 for the same end-boundary reason.

## Still open: the breakout / end boundary

Deferred by explicit user directive (*"assume whatever the input for end boundary is correct"*), and
it is now the single biggest limiter on Phase 75 — it costs 48 of 108 sessions their underwater
metrics. It is the same open problem as ROADMAP TODO #69 and Phase 58's removed breakout marker, and
deserves a phase of its own.

**Two levers already refuted — do NOT re-test these:**
1. **Threshold on velocity.** `finish` is not threshold-sensitive: mean |vel| in the over-run region
   is **0.403 m/s, 8× `_BASELINE_THRESH`**. The swimmer really is still moving — fast but APERIODIC.
2. **Rhythm step-down** (first inter-peak interval > 1.5× the running base), tested 2026-08-19:
   **worse** than the incumbent — 17 of 37 no-detect, mean |err| **2.95 s** where it fired.

Also recorded: the current auto `stroke_start` is ~3–4 s off the coach's mark in **both** directions,
and the freestyle auto window has a median width of just **0.42 s** (18/32 under 0.5 s), which is why
unannotated freestyle blanks under `_MIN_UW_DURATION_S`.

## Phase 75 is NOT complete

CONTEXT's three-step workflow (D11/D14) runs Step 2 for as many plans as there are metric
increments, then Step 3 (the UI). **Nothing from Phase 75 is visible in any UI yet — by design.**
The user's observation stands as the Step-3 brief: there is currently no place to view auto
segmentation for anything except stroke segmenting.
