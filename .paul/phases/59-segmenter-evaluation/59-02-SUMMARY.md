---
phase: 59-segmenter-evaluation
plan: 02
subsystem: api
tags: [segmentation, metrics, dispatch, registry, refactor, pytest]

requires:
  - phase: 59-segmenter-evaluation (59-01)
    provides: the fixture + regression that serve as this plan's acceptance test, and the
              measurement (marks_per_cycle != boundaries_per_cycle) that dictates the seam's shape
provides:
  - "metrics.SEGMENTER_BY_STROKE — per-stroke segmenter override table (ships EMPTY)"
  - "metrics.resolve_segmenter(stroke_type) — dispatch with a documented callable contract"
  - "compute_session_metrics(..., stroke_type=None) — the parameter 59-05 will act on"
  - "POST /process forwards its stroke_type Form field into the pipeline"
affects: [59-03 cycle-pairing fix, 59-04 exploration, 59-05 ship the winner]

tech-stack:
  added: []
  patterns:
    - "Override table, not exhaustive map: empty means 'nothing has earned an override yet'"
    - "Refactor inertness proven by byte-hash of a full before/after report, not by assertion"
    - "A seam must have a test proving a registered override is actually CALLED"

key-files:
  created: []
  modified: [metrics.py, api.py, tests/test_metrics.py, tests/test_api.py, CLAUDE.md]

key-decisions:
  - "Registry ships empty rather than four entries pointing at the wavelet"
  - "Registry contract pinned now so 59-05 wraps segment_cycles_trough instead of widening it"
  - "api.py:888 deliberately not touched — dead by construction behind the cycle_bounds guard"

patterns-established:
  - "Inertness claims are proven by hashing a full report captured BEFORE the first edit"
  - "Tests that are expected to fail in a later plan say so in their docstring"

duration: ~35min
started: 2026-08-09
completed: 2026-08-09
---

# Phase 59 Plan 02: Per-Stroke Segmenter Dispatch — Summary

**`metrics.py` now routes segmentation through a per-stroke table instead of a hardcoded call, and the table ships empty — proven inert by a byte-identical before/after report (sha256 `4609a7b0…` both times).**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min |
| Tasks | 3 auto, 0 checkpoints (`autonomous: true`) |
| Files modified | 5 |
| Suite | 262 → **268** |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Nothing moves | **Pass** | Fixture report captured before the first edit and again after all three tasks: `sha256 4609a7b03cbb18f565d20b4fb604886e7b8d82b0347a00bd62b1d90c778d018e` both times. All 7 regression assertions pass with pins unedited; `git diff` on `tests/test_segmenter_eval.py` and the fixture is empty. |
| AC-2: The seam dispatches | **Pass** | `test_a_registered_override_is_actually_called` monkeypatches a sentinel into `SEGMENTER_BY_STROKE["butterfly"]`, asserts it receives the segmentation slice and that its cycles reach the result. Unregistered strokes still resolve to the wavelet in the same run. |
| AC-3: Existing callers untouched | **Pass** | `stroke_type` appended as the LAST parameter, so no positional call can break. The 6 non-passing call sites (app.py ×3, coach.py, inspect_cycles.py, api.py:888) are unmodified; `test_stroke_type_does_not_change_results_yet` pins equality across all four strokes on a real session. |
| AC-4: /process forwards stroke_type | **Pass** | Two tests: the *value* arrives (`"butterfly"`, not merely a present key), and an omitted Form field forwards `None` rather than `""`. |
| AC-5: Docs describe the seam | **Pass** | CLAUDE.md signature updated, registry documented with its contract, 16-06 recorded as superseded by Phase 59's five plans, and a new "Marks per cycle ≠ boundaries per cycle" section carrying 59-01's measurement. |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified | `SEGMENTER_BY_STROKE = {}` + `_DEFAULT_SEGMENTER` + `resolve_segmenter()`; `stroke_type=None` on `compute_session_metrics`; the hardcoded `segment_cycles_wavelet(t_seg, vel_seg)` becomes `resolve_segmenter(stroke_type)(t_seg, vel_seg)`; two stale comments corrected. |
| `api.py` | Modified | One logical change at the `/process` metrics call — forwards the `stroke_type` already in scope from `:139`. |
| `tests/test_metrics.py` | Modified | `TestSegmenterDispatch` — 4 tests. |
| `tests/test_api.py` | Modified | `TestStrokeTypeForwardedToMetrics` — 2 tests. |
| `CLAUDE.md` | Modified | Signature, registry + contract, 16-06 supersession, and the marks-vs-boundaries section. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Registry ships **empty** | "No stroke has earned its own segmenter yet" is the literal truth. Four entries all pointing at the wavelet is a table that says nothing and still has to be edited in 59-05. | `resolve_segmenter` falls through to the default for every value `stroke_type` can hold. |
| Registry **contract written now** | 59-05 builds against it. `segment_cycles_trough(t, vel, T_est=None)` does **not** match `(t, vel) -> cycles \| None`. | 59-05 must wrap the trough segmenter (`T_est` from `_estimate_period`), not widen the seam. Recorded in the code, CLAUDE.md and ROADMAP. |
| `api.py:888` **not** touched | Guarded by `if manual.get("cycle_bounds")` at `:882`, and cycle bounds bypass segmentation entirely (`metrics.py:479-495`). Passing `stroke_type` there would be dead by construction. | The omission is deliberate, not missed. Recorded in CLAUDE.md so a future reader does not "fix" it. |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | A false claim caught before it shipped |
| Scope additions | 1 | One extra test |
| Deferred | 0 | — |

**Total impact:** no scope creep; the plan executed essentially as written.

### Auto-fixed

**1. [Docs] CLAUDE.md asserted a fix that has not happened.**
- **Found during:** Task 3 (CLAUDE.md), immediately after writing it
- **Issue:** the new marks-vs-boundaries section said the ~1.75× freestyle defect was *"fixed in Phase 59-03"*. **59-03 has not been written.** Left alone, CLAUDE.md would have told every future reader — human or agent — that a live defect was already resolved.
- **Fix:** rewritten to "⚠ RELATED DEFECT, STILL LIVE as of Phase 59-02 (owned by 59-03, not yet fixed)", with the consequence stated explicitly: auto and annotation-recomputed freestyle metrics are not on the same scale, so comparing them is invalid until 59-03 lands.
- **Verification:** re-read in place; the claim now matches the repo state.

### Scope addition

**`test_registry_ships_empty`** — the plan specified three dispatch tests; four were written. The extra asserts `SEGMENTER_BY_STROKE == {}` so that 59-05 populating the table trips a test deliberately rather than changing behavior silently. Its docstring names both readings of a failure (59-05 landed, or something populated it by accident).

## Issues Encountered

None. No verification failed, no boundary was approached.

## Skill Audit

No `.paul/SPECIAL-FLOWS.md` — skipped.

## Not Committed

Git is run by the user. Nothing here is committed.

```bash
git add metrics.py api.py tests/test_metrics.py tests/test_api.py CLAUDE.md .paul/
```

⚠ `metrics.py` and `api.py` are on the **Railway deploy path**. This plan changes no behavior, so a deploy is safe — but it is the first Phase-59 change that reaches production code at all, and 59-01's four files were purely additive by comparison.

## Next Phase Readiness

**Ready**
- 59-05 can ship a per-stroke choice by editing one dict, with the trough-adapter requirement already written down rather than rediscovered.
- 59-03 can pair boundaries into cycles with `stroke_type` already threaded to the one place that needs it.
- The inertness technique itself is reusable: capture a full report before the first edit, hash both ends.

**Concerns**
- `test_stroke_type_does_not_change_results_yet` is **expected to fail in 59-05**. Its docstring says so and says to re-baseline deliberately rather than weaken it. If someone weakens it instead, the inertness guarantee silently disappears.
- Likewise the 7 pinned values in `tests/test_segmenter_eval.py` will legitimately move in 59-03 and 59-05. They must be re-baselined with the new numbers recorded in that plan's SUMMARY, never edited to make a diff green.
- Still live and untouched: the ~1.75× freestyle rate (59-03) and the +7.8 s phase window (59-01's larger finding, still unowned by any written plan).

**Blockers**
- None.

**⚠ Phase 59 is 2 of 5 plans, NOT complete.** The plan-count heuristic (2 PLAN files, 2 SUMMARY files) would fire a phase transition — it must not. 59-03 through 59-05 are scoped in ROADMAP.md and STATE.md and are not yet written.

---
*Phase: 59-segmenter-evaluation, Plan: 02*
*Completed: 2026-08-09*
