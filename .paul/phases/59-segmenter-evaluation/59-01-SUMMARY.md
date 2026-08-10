---
phase: 59-segmenter-evaluation
plan: 01
subsystem: testing
tags: [segmentation, ground-truth, scoring, scipy, wavelet, pytest, supabase]

requires:
  - phase: 47-trial-annotation
    provides: the annotation contract + `session_annotations` rows this scores against
  - phase: 57-annotation-workflow
    provides: one-mark-per-arm-entry semantics + `annotation_to_overrides` pairing rule
  - phase: 58-video-ground-truth
    provides: the video tooling that produced the best-labeled batch (2026-08-07)
provides:
  - "segmenter_eval.py — pure, optimal-assignment scoring of predicted vs human event times"
  - "tools/score_segmenter.py — corpus-wide CLI over cycles AND phase markers, two windows"
  - "tests/fixtures/segmenter_truth.json — 4-session offline ground-truth fixture"
  - "The first quantitative measurement of segment_cycles_wavelet, detect_phases and detect_initial_phase"
affects: [59-02 dispatch refactor, 59-03 cycle-pairing fix, 59-04 exploration, 59-05 ship, 16-06 (retired), 53-attention-allocation]

tech-stack:
  added: []
  patterns:
    - "Pure scorer at repo root + thin CLI in tools/ (mirrors metrics.py / tools/schema_contract.py)"
    - "Regression imports the real CLI by path so test and tool cannot drift"
    - "Exact-value pinning (1e-6) rather than a floor, so a later refactor can prove inertness"

key-files:
  created:
    - segmenter_eval.py
    - tools/score_segmenter.py
    - tests/test_segmenter_eval.py
    - tests/fixtures/segmenter_truth.json
  modified: []

key-decisions:
  - "Exclusion list = the 4 proposed partial-label sessions; two criteria kept, not one threshold"
  - "Exploration of NEW segmenters became its own plan — a scoping gap the user found mid-apply"
  - "The 1.75x cycle-pairing fix ships as its own plan, independent of segmenter choice"

patterns-established:
  - "Circularity guard: phase predictions seed from metrics_json_auto, never metrics_json"
  - "Optimal assignment (linear_sum_assignment), never greedy nearest-match"
  - "Excluded sessions still score for recall; only precision/F1 drop them"

duration: ~90min
started: 2026-08-09
completed: 2026-08-09
---

# Phase 59 Plan 01: Segmenter Evaluation Harness — Summary

**The production segmenter has a score for the first time in the project's life: freestyle F1 0.46 at ±0.15 s, and the phase detector turns out to be the larger error source — the auto swim window is more than 5 s too wide on 19 of 22 sessions.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~90 min |
| Tasks | 3 auto + 1 checkpoint:decision, all completed |
| Files created | 4 (no product file modified) |
| Suite | 237 → **262** passed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Scorer pure, optimal, correct on known inputs | **Pass** | 18 unit tests. `test_optimal_beats_greedy` pins the case where greedy reports 1 match and optimal finds 2; `test_result_is_order_independent` pins order-invariance. |
| AC-2: Cycles scored, 3 segmenters × 2 framings × 2 windows | **Pass** | CLI exits 0 over all 23 sessions; per-stroke tables + `sweep_entries` at 5 tolerances; per-session `stroke_rate_spm` error reported. |
| AC-3: Phases scored non-circularly | **Pass** | All 23 sessions have `metrics_json_auto`; verified in use (session `4219daea` seeds `initial_phase_end_idx`=1056 → 11.73 s, matching a live re-run of `detect_initial_phase`). `test_circularity_guard_prefers_the_auto_backup` pins both branches. 0 unscorable. |
| AC-4: Partial labels excluded from precision, kept in recall | **Pass** | Checkpoint answered `proposed`. `aggregate()` reports `precision`/`recall`/`f1` over the included subset and `recall_all` over everything; coverage printed next to each session. |
| AC-5: Regression offline, existing suite untouched | **Pass** | 262 passed; regression passes with `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` unset; `git diff --stat` on metrics.py/api.py/annotations.py/ratings.py/vel_acc_extraction.py is **empty**. |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `segmenter_eval.py` | Created | Pure scorer — `match_series` (optimal assignment), `score_series`, `sweep`, `coverage`, `aggregate`. No I/O. |
| `tools/score_segmenter.py` | Created | CLI over the live corpus or a cached JSON. Runs wavelet / trough / peak-pick on the annotated and production windows, scores cycles and arm entries, plus the four phase markers. |
| `tests/fixtures/segmenter_truth.json` | Created | 4 sessions (2 free, 1 fly, 1 breast) from the 2026-08-07 batch. Full traces, 9125 samples, **113 KB**. |
| `tests/test_segmenter_eval.py` | Created | 18 unit + 7 regression tests. |

## Findings

### The greedy priors held
The preliminary numbers in CONTEXT.md were produced with a greedy matcher and flagged as unsafe to cite. Optimal assignment reproduced them almost exactly — freestyle at ±0.30 s: **recall 0.82 (prior 0.82), precision 0.68 (prior 0.67)**. The CONTEXT figures can now be cited.

### The wavelet finds the right events and places them badly
Freestyle entries-F1 climbs 0.19 → 0.36 → 0.46 → 0.57 → **0.74** across tolerances 0.05 → 0.30 s. A steep climb means the events are real and the timing is scattered. **There is no constant lag to correct**: per-session bias is −0.04 s (free), +0.08 s (fly), +0.13 s (breast) against a within-session spread of ~0.10 s. 59-05 should not chase a global shift.

### The phase detector is the larger error source — never measured before
The auto swim window versus the human swim window, 22 scorable sessions:

| | |
|---|---|
| median excess | **+7.83 s** |
| `stroke_start_s` | 3.88 s early (MAE), bias −3.88 s |
| `finish_s` | 3.55 s late (MAE), bias +3.55 s |
| within 1 s / 1–5 s / >5 s | **1 / 2 / 19** |

This is why every production-window score sits below its annotated-window twin. `detect_initial_phase` looks for a dive surge then a pulldown peak (`metrics.py:272-307`) — breaststroke's shape — while running on all four strokes. D10 paid for itself on its first run.

### The trough segmenter's 0.00 is a misfeed, not a failure — this invalidates D13 as posed
`segment_cycles_trough` scores 0.00 on every stroke and returns `None` on 16 of 23 annotated-window runs. Cause: it requires velocity below `0.20 × v95`, and Phase 57 made the swim window authoritative, removing the dead tail where those deep troughs lived. It is being handed a window it was never designed for.

**Consequence:** CONTEXT D13 ("score both, let 59-01 decide") cannot be answered from this run. Breaststroke routing needs the trough segmenter re-scored on the **untrimmed** trace first. Carried to 59-04.

### A 20-line baseline beats the shipping segmenter 2× on butterfly
Recall at ±0.15 s — peak-pick **0.84** vs wavelet **0.41** on butterfly; peak-pick 0.57 vs 0.51 on freestyle. The baseline was written purely as a comparator. That a throwaway beats production on one stroke is the strongest single argument for per-stroke dispatch, and the reason the user opened 59-04.

### The wavelet ridge is strikingly window-sensitive
Session `4219daea`, entries framing: moving the window start by **0.58 s** collapses F1 from **0.54 to 0.11**. Pinned in the regression deliberately. Combined with the window finding above, this suggests fixing phase detection may raise segmentation scores without touching the segmenter.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Exclusion list = the 4 proposed | Checkpoint answered `proposed` | Two criteria kept (coverage AND ISI-vs-trace-period), which is why `08-05 20:06` (cov 0.86) is excluded while `08-05 20:10` (cov 0.84) is not. A single `coverage < 0.85` rule was offered and declined — commented in the source so nobody "tidies" it. |
| Exploration of new segmenters gets its own plan | User asked where brainstorming happens and found a real scoping gap — no plan covered it | Phase becomes 5 plans: 59-02 refactor → 59-03 pairing fix → 59-04 explore → 59-05 ship |
| The ~1.75× fix ships separately | It is a cycle-*definition* bug, independent of which segmenter wins | Users stop seeing a doubled freestyle rate weeks earlier; the comparability break lands in a diff containing nothing else |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Essential — the CLI could not print its own report |
| Approach changes | 1 | Reduces drift risk |
| Scope additions | 0 | — |

**1. CLI output made ASCII-only.** Found during Task 2 verification. The Windows console is cp1252 and `print()` of the plan's own warning glyphs (`⚠`, `±`, `—`) raised `UnicodeEncodeError` **after** the Supabase fetch had already succeeded — the run died at the report, not the work. Only printed strings were changed; source comments and docstrings keep their glyphs. Verified by a clean second run from the cached input.

**2. The regression imports `tools/score_segmenter.py` by path.** The plan's import list for the test named only stdlib + numpy + scipy + metrics + annotations + segmenter_eval. Re-implementing candidate invocation inside the test would let the test and the tool drift apart silently — exactly what this suite exists to prevent. No new dependency; the offline requirement is still proven (`test_no_network_credentials_needed`, plus a full run with the env vars unset).

**3. Fixture size stated:** 113 KB, 4 sessions, 9125 samples, velocity rounded to 4 dp, full traces (phase scoring needs the pre-swim samples).

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Mid-run doubt about the "+7.4 s window" claim — the first session picked for the visual happened to be the single best in the corpus (+0.59 s) | Pulled the full per-session distribution rather than generalising from one example. The aggregate claim held (median +7.83 s, 19/22 > 5 s); the example was swapped for a representative session. |
| `recursive grep` over the repo root timed out (large media files at root) | Used the Grep tool with globs instead. |

## Skill Audit

No `.paul/SPECIAL-FLOWS.md` — skill audit skipped.

## Not Committed

Per standing preference, git is run by the user. Nothing here has been committed.

```bash
git add segmenter_eval.py tools/score_segmenter.py tests/test_segmenter_eval.py tests/fixtures/segmenter_truth.json .paul/
```

⚠ `tests/fixtures/segmenter_truth.json` is a real data file (113 KB). `.gitignore` does not exclude `*.json`, and `!/tests` un-ignores the directory, so it will be tracked normally.

## Next Phase Readiness

**Ready**
- Any candidate segmenter can now be scored in one command, offline, against human truth.
- 59-02's acceptance test already exists: re-run the harness and require byte-identical output.
- The measurement 59-03 needs (boundaries-per-cycle per stroke) is in `segmenter_report.json`.

**Concerns**
- **The corpus is ONE swimmer**, one pool, one device. Every number describes how well a segmenter tracks that person. Stated in the fixture `_readme`, the test header and the CLI banner — keep it that way.
- **Breaststroke n=2, backstroke n=0.** Breaststroke routing rests on two sessions plus historical validation; backstroke has no evidence at all and will inherit freestyle's implementation (CONTEXT D12).
- The exclusion list goes stale as labeling continues. The harness prints the coverage statistic it was derived from so the next reader can tell.

**Blockers**
- None.

**⚠ Phase 59 is 1 of 5 plans, NOT complete.** The plan-count heuristic (1 PLAN, 1 SUMMARY) would fire a phase transition here — do not. 59-02 through 59-05 are scoped in STATE.md and are not yet written. ROADMAP's Phase 59 plan list still shows the superseded 3-plan shape and is corrected as part of this UNIFY.

---
*Phase: 59-segmenter-evaluation, Plan: 01*
*Completed: 2026-08-09*
