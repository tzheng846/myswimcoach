---
phase: 57-annotation-workflow
plan: 01
subsystem: api
tags: [annotations, metrics, signal-processing, pytest, contract]

requires:
  - phase: 47-trial-annotation
    provides: the annotation contract (annotations.py), the PUT recompute path, session_annotations
  - phase: 52-sample-rate-contract
    provides: _session_fs + the "widen every .select() or the fallback hides the fix" lesson
provides:
  - arm-entry stroke-mark convention (MARKS_PER_CYCLE + marks_per_cycle)
  - annotation_to_overrides(stroke_type=...) pairing
  - swim-window rejection of out-of-window stroke marks
  - _window_v95 — swim-windowed v95 across metrics.py
  - marks_per_cycle + cycles_derived published on the annotation endpoints
affects: [57-02 annotate page, 57-03 annotation queue, 53 attention-allocation, 16-06 segmenter tuning]

tech-stack:
  added: []
  patterns:
    - "Safe-default parameter: a new optional argument whose omitted/unknown value reproduces
       pre-change behavior byte-for-byte, pinned by a parametrized identity test"

key-files:
  created: []
  modified: [annotations.py, metrics.py, api.py, tests/test_annotations.py, CLAUDE.md]

key-decisions:
  - "finish_s closes the last cycle ONLY at k==1; at k>1 it would manufacture a half-populated cycle"
  - "No separate stroke_start/first-mark relink — window rejection already covers the real overlap"
  - "coast_fraction does NOT depend on v95 — the plan was wrong; corrected rather than propagated"

patterns-established:
  - "Mutation-test the guard, not just the happy path: remove the condition, prove a test fails, revert"
  - "Measure a pipeline change on data that actually exercises it — raw/ has no dead tail, so the
     representative case had to be constructed"

duration: ~1 session (single sitting, 2026-08-05)
started: 2026-08-05
completed: 2026-08-05
---

# Phase 57 Plan 01: Annotation Contract + Pipeline Summary

**The annotated swim window is now authoritative — out-of-window stroke marks are rejected instead
of silently becoming cycles, `v95` is computed over the swim window rather than the full trace, and
one stroke mark now means one ARM ENTRY, pairing into cycles for freestyle and backstroke.**

## Performance

| Metric | Value |
|--------|-------|
| Date | 2026-08-05 |
| Tasks | 3 of 3 completed |
| Files modified | 5 |
| Suite | 176 → 236 (+60 new tests) |
| Failures | 0 |
| Checkpoints | none (autonomous:true) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Out-of-window marks rejected | **Pass** | `TestSwimWindowEnforcement` (7 tests) + `test_mark_past_finish_is_422_and_writes_nothing`. Verified the annotations table is never even reached — validation rejects before any write. |
| AC-2: Free/back pair; fly/breast do not | **Pass** | 5 arm entries → 2 cycles on freestyle, 4 on butterfly. Trailing odd entry contributes no cycle and stays in `stroke_marks_s`. |
| AC-3: k=1 path byte-identical to today | **Pass** | 28 parametrized cases (7 stroke values × 4 docs) asserting the 4-arg call equals the 3-arg call. |
| AC-4: v95 swim-windowed pipeline-wide | **Pass** | Both leaking sites windowed; empty window falls back to full trace; the two deliberately-excluded sites confirmed untouched by grep. |
| AC-5: stroke_type reaches both endpoints | **Pass** | Both `.select()`s widened (api.py:794, :847); `marks_per_cycle` on GET, `marks_per_cycle` + `cycles_derived` on PUT. |

## Accomplishments

- **Closed the silent-corruption hole in the annotation contract.** A stroke mark placed in the
  post-swim dead tail previously passed validation and became a cycle feeding `stroke_rate_spm` and
  `mean_dps_m`. It is now a 422 that names the offending index and the bound it crossed.
- **Taught the contract that a mark is an arm entry, without breaking anything that existed.**
  `MARKS_PER_CYCLE` covers only freestyle and backstroke; every other value — butterfly,
  breaststroke, the mobile picker's `im` and `udk`, unknown strings, `None` — falls to 1 and
  reproduces pre-Phase-57 output exactly. AC-3 pins this with 28 identity assertions.
- **Removed the dead-tail bias from `v95`** at both sites that leaked it, including
  `extract_cycle_peaks`, where it scales a peak-prominence *detection* floor rather than just a
  reported number.
- **Measured the change instead of asserting it** — and the measurement corrected the plan (below).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `annotations.py` | Modified | `MARKS_PER_CYCLE` + `marks_per_cycle()`; `annotation_to_overrides(…, stroke_type=None)` with `marks[0::k]` boundaries and the k==1 finish-append guard; `validate_annotation` swim-window rejection. Module + function docstrings rewritten. |
| `metrics.py` | Modified | New `_window_v95(vel, start, end)`; `compute_session_metrics` v95 moved below the override block and windowed to `[b_end, swim_end]`; `extract_cycle_peaks` windowed to the cycle span. |
| `api.py` | Modified | Both annotation `.select()`s widened with `stroke_type`; PUT passes it to `annotation_to_overrides`; GET returns `marks_per_cycle`; PUT returns `marks_per_cycle` + `cycles_derived`. |
| `tests/test_annotations.py` | Modified | +60 tests across `TestMarksPerCycle`, `TestArmEntryPairing`, `TestSwimWindowEnforcement`, `TestStrokeTypeReachesTheEndpoints`. |
| `CLAUDE.md` | Modified | New "v95 is swim-windowed, not full-trace (Phase 57)" section with the measured deltas and an explicit what-changed / what-didn't list. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `finish_s` appended as a cycle boundary **only when k==1** | At k=1 a mark is a cycle start and the wall legitimately ends the last cycle. At k=2 a boundary is a *same-side* arm entry; `finish_s` is a wall touch, so appending it manufactures a cycle holding one arm entry instead of two — skewing `stroke_rate_spm` and `mean_dps_m`. | Mutation-tested. The asymmetry looks like an inconsistency and must not be "simplified" away; the code carries a comment saying so. |
| No separate stroke_start↔first-mark relink mechanism | Rejecting marks before `stroke_start_s` already guarantees `marks[0] >= stroke_start_s`, the only genuine phase overlap. A remaining *gap* is real and legal. | Reduction from CONTEXT.md, recorded at plan time and held. 57-02 surfaces the gap as a non-blocking hint. |
| Pairing factor derived from `stroke_type`, not stored | Avoids a schema patch for information already present. | `stroke_type` is NOT patchable, so a wrong value is unfixable via the API — mitigated by publishing `cycles_derived` so the mismatch is visible. See Concerns. |
| `np.percentile` kept (not `nanpercentile`) in `_window_v95` | The pre-change code used `percentile`; switching NaN semantics would have been an unrequested behavior change riding along. | Only new failure mode is an empty window, which the guard handles. |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Plan correction | 1 | Plan asserted a false fact; corrected in code comments + CLAUDE.md |
| File relocation | 1 | Tests placed with their fixtures |
| Auto-fixed | 2 | Contradicted comments/docstrings |
| Scope additions | 0 | — |

**Total impact:** No scope creep. One factual error in the plan was caught by measurement and
corrected rather than propagated.

### 1. Plan correction — `coast_fraction` does not depend on `v95`

- **Found during:** Task 2c (measurement)
- **Issue:** The PLAN, CONTEXT.md, STATE.md and ROADMAP all stated that windowing `v95` would shift
  `coast_fraction`. It does not. `coast_thresh = _COAST_FRAC_THRESH * cyc["arm_peak_vel"]`
  (metrics.py:521) — scaled by each cycle's own arm-peak velocity, never by `v95`.
- **Fix:** Measured `mean_coast_fraction` delta = **+0.00%** on every file at every tail length.
  CLAUDE.md now lists precisely what moves (`dead_spot_s`, peak-detection prominence) and what does
  not (`coast_fraction`, `stroke_rate_spm`, segmentation).
- **Impact:** D2's accepted comparability cost is **narrower than the user was told** — it is
  `dead_spot_s` and peak detection only.

### 2. Test file relocation

- **Planned:** new endpoint tests in `tests/test_api.py`.
- **Actual:** `tests/test_annotations.py` — that is where the annotation-endpoint fixtures
  (`_annot_admin`, `AUTH`, `SESSION_ROW`, `api_client`) actually live. `tests/test_api.py` untouched.

### 3. Auto-fixed contradicted comments

- `annotations.validate_annotation` docstring asserted **the opposite** of the new behavior —
  *"stroke marks are not required to sit inside the stroke phase span."* Rewritten.
- `metrics.py:541` described `v95` as a *"global threshold, matches swim_metrics.ipynb"*, false
  after the change. Rewritten to state it is swim-windowed and that the notebook still is not.

## Verification Results

**Suite:** `pytest tests/ -q` → **236 passed** (baseline 176). No existing assertion was
re-baselined; every pre-existing test passed unmodified.

**Mutation test (T1):** removing the `k == 1` guard on the finish-append failed 2 tests —
`test_finish_closes_the_last_cycle_only_when_one_mark_is_one_cycle` and
`test_too_few_marks_to_pair`. Reverted; green.

**v95 measurement (T2c).** The `raw/` corpus turned out to be a poor instrument — those traces carry
a 0–5% post-swim tail, so they barely exercise the change. Re-run with a 45% tail appended, matching
the 2026-08-05 sessions:

| File | tail | v95 | `dead_spot_total_s` | cycles |
|---|---|---|---|---|
| `leo1` | 0% | +2.00% | +0.60% | unchanged (19) |
| `leo1` | 45% | **+12.15%** | +3.68% | unchanged (19) |
| `carlos_fr_1` | 0% | +1.54% | +0.00% | unchanged (20) |
| `carlos_fr_1` | 45% | **+6.37%** | +1.59% | unchanged (20) |
| `carlos_fl_1` | 0% | — | +0.00% | unchanged (8) |

`mean_coast_fraction` and `stroke_rate_spm`: +0.00% throughout. **Cycle counts unchanged on every
file at every tail length** — the plan's stop-and-report condition never fired.

Measurement scripts were written to the session scratchpad and deliberately **not** committed;
they reproduce from this table's description if needed again.

**Boundaries honored:** `web/` untouched by this plan (the `Footer.js` / `Nav.js` / `blog/` entries
in `git status` predate this session — see the session-start snapshot). `tests/test_api.py`,
`ratings.py`, `supabase/`, iOS all untouched. `TestSchemaContract` still green.

**Skill audit:** no `.paul/SPECIAL-FLOWS.md` in this repo — not applicable.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| First `assert_not_called()` on the annotations table raised `KeyError` | Not a code bug — `_annot_admin` creates table handles lazily, so the table was never instantiated *because* validation rejected first. Asserting the key's **absence** is the stronger claim; test rewritten. |
| `raw/` CSVs did not exercise the v95 change | Constructed the representative case (45% tail appended) rather than reporting a misleadingly small delta. |

## Next Phase Readiness

**Ready:**
- 57-02 (annotate page v2) can consume `marks_per_cycle` from `GET /sessions/{id}/annotations` — the
  pairing rule never needs duplicating in JavaScript — and `cycles_derived` from the PUT response for
  the "18 marks → 9 cycles" readout.
- The 422 error shape (`{detail: {errors: [...]}}`) carries human-readable window violations that the
  UI can render verbatim.

**Concerns:**
- **`stroke_type` correctness on the 19 collected sessions is UNVERIFIED.** It needs a live DB read
  this plan did not perform. `stroke_type` is not patchable through the API (CLAUDE.md), so a wrong
  value cannot be corrected and would silently halve a freestyle stroke rate. `cycles_derived` makes
  the mismatch visible, but someone has to look. **Check before annotating.**
- `dead_spot_s` computed before today is not comparable with values computed after. Recorded in
  CLAUDE.md; no backfill attempted.
- Nothing is committed — the user runs git. `api.py` + `metrics.py` need a push for Railway to pick
  up the contract change before the web work depends on it.

**Blockers:** None.

---
*Phase: 57-annotation-workflow, Plan: 01*
*Completed: 2026-08-05*
