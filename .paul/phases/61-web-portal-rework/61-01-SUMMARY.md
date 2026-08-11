---
phase: 61-web-portal-rework
plan: 01
subsystem: metrics
tags: [python, numpy, signal-processing, ratings, thresholds, supabase]

requires:
  - phase: 59-segmenter-evaluation
    provides: per-stroke segmenter dispatch + the cycles this plan re-aggregates
  - phase: 52-sample-rate-contract
    provides: sessions.sample_rate_hz, read per-row by tools/rampup_impact.py
provides:
  - metrics.py with no steady/ramp_up cycle split — stroke_count IS the total cycle count
  - ratings.py anchors for cv_arm_peak_vel + fatigue_index_pct re-derived from measured data
  - tools/rampup_impact.py — reproducible read-only impact measurement
  - tests/test_ratings.py::TestBands::test_consistency_bands — first coverage of cv band edges
affects: [61-02 report card, 61-04 compare redesign, 53 attention allocation]

tech-stack:
  added: []
  patterns:
    - "Mutation-test a threshold table before trusting a green suite (found cv anchors untested)"
    - "Measure impact from STORED metrics_json cycles — no CSV download, no pipeline re-run"

key-files:
  created: [tools/rampup_impact.py]
  modified: [metrics.py, ratings.py, coach.py, app.py, inspect_cycles.py, pipeline_view.py, tests/test_ratings.py]

key-decisions:
  - "D5 shipped in full: ramp_up removed, reaffirmed 3x with measurements on screen"
  - "D15 anchors = percentile-clamped; fatigue best clamped at 0, not measured p10 of -15.8"
  - "Added test_consistency_bands after mutation testing exposed zero coverage"
  - "CORRECTION: bands never collapsed; the real defect D15 fixes is SCORE saturation"

patterns-established:
  - "ramp_up was a FINISH filter, not a ramp-up filter — position median 0.91, verified 2 corpora"
  - "Report deltas over AFFECTED sessions; corpus-wide medians hide the change as +0.0%"

duration: ~50min (approximate — single session, no per-task timestamps captured)
started: 2026-08-11
completed: 2026-08-11
---

# 61-01 SUMMARY — Remove the cycle-phase split (D5) + re-anchor two bands (D15)

**Status:** ✅ COMPLETE — all 5 ACs met. Suite **273 → 274** (+1 new test). Zero web or mobile
files touched. Segmentation provably unmoved.

---

## ⭐ The headline: `ramp_up` was never ramp-up

The filter removed by this plan gated on `arm_peak < 0.50 × p75` — a **velocity** test, not a
positional one. Measured two independent ways:

| corpus | evidence |
|---|---|
| `raw/` (43 CSVs) | **0 of 13** affected sessions had a leading run; **13/13 scattered**. `carlos_fr_1`=[9] of 10, `leo1`=[18] of 19, `leo2`=[0,16] of 17, `leo4`=[4,5] of 6 |
| live DB (67 sessions) | excluded-cycle **median normalized position 0.91**; **59%** in the final 20% of the swim |

It was marking **the swimmer decelerating into the wall**, not accelerating from rest. The name
was wrong in `metrics.py`, in Phase 60's record, and in the first draft of Phase 61's CONTEXT.md.
`tools/rampup_impact.py --positions` keeps this reproducible.

---

## ⚠ A CORRECTION TO THE RECORD

During the grilling that preceded this plan I asserted that removing `ramp_up` would **collapse
the bands** — "Consistency becomes a constant, 11/11 read `needs_work`." **That was wrong.** It
came from measuring band flips on the untrusted `raw/` corpus and reporting them as a fraction of
the 11 *affected* sessions rather than of the corpus.

Measured properly on the live corpus, bands do **not** collapse:

| driver | before | after D5, old anchors |
|---|---|---|
| `cv_arm_peak_vel` | good 36 / ok 28 / nw 36 | good 36 / ok 23 / **nw 42** |
| `fatigue_index_pct` | good 43 / ok 23 / nw 34 | good 36 / ok 21 / **nw 43** |

Max share 43%, against AC-3's 60% threshold. **D15's original justification did not survive
measurement.**

**But D15 was still needed, on different and properly-measured grounds: the 0–100 SCORE
saturates.** `_score` is anchored on `worst`/`best`, and D5 doubled the upper tail past `worst`:

| driver | sessions scoring exactly 0 |
|---|---|
| `cv_arm_peak_vel` | **8% → 36%** |
| `fatigue_index_pct` | **4% → 26%** |

19 sessions all reading 0 for Consistency when they are not equally bad. That is what the
re-anchor fixes, and it is why D15 shipped.

---

## What moved (measured, `tools/rampup_impact.py`, live corpus n=53)

40% of sessions (21/53) have ≥1 previously-excluded cycle. Deltas are over those **affected**
sessions only — the corpus-wide median is +0.0% because the unaffected 60% dominate it.

| metric | old median | new median | old p90 | new p90 | affected Δ |
|---|---|---|---|---|---|
| `stroke_count` | 8.000 | 8.000 | 14.000 | 15.000 | **+15.5%** |
| `stroke_rate_spm` | 42.628 | 42.718 | 60.795 | 61.270 | +0.2% |
| `mean_arm_peak_vel_ms` | 1.732 | 1.639 | 1.982 | 1.957 | −12.1% |
| `cv_arm_peak_vel` | 0.149 | 0.176 | 0.277 | **0.638** | **+70.1%** |
| `mean_isi_s` | 1.408 | 1.405 | 2.265 | 2.282 | −0.2% |
| `cv_isi` | 0.145 | 0.213 | 0.552 | 0.532 | +19.2% |
| `mean_dps_m` | 1.657 | 1.564 | 2.520 | 2.474 | −12.5% |
| `fatigue_index_pct` | 12.835 | 15.621 | 35.414 | **73.562** | **+109.9%** |

⚠ **FOURTH COMPARABILITY BREAK** after Phases 57, 59-03 and 59-05. Sessions stored before this
change keep their old numbers and their `phase` key; nothing was backfilled.

## Anchors shipped (D15, user chose `percentile-clamped`)

| metric | old | new |
|---|---|---|
| `cv_arm_peak_vel` | 0.30 / 0.20 / 0.10 / 0.03 | **0.65 / 0.22 / 0.09 / 0.05** |
| `fatigue_index_pct` | 40 / 20 / 8 / 0 | **75 / 24 / 5 / 0** |

`fatigue` best clamped at **0** rather than the measured p10 of −15.8: negative fatigue means the
swimmer sped up, and −15.8 would price a 100 at "you must accelerate through the swim." Cost: 23%
tie at 100. `mean_vel_ms` and `mean_dps_m` anchors deliberately untouched.

**AC-3 final:** Consistency good 34 / ok 26 / nw 40, score floor 11%, 36 distinct scores.
Endurance good 30 / ok 30 / nw 40, score floor 11%, 31 distinct. Both PASS.

---

## ⭐ Mutation testing found an unrelated coverage hole

Scaling `cv_arm_peak_vel`'s four anchors by 10× left **all 273 tests green**. Endurance had band
pins (`test_lower_is_better_bands`); **Consistency had none** — its band boundaries could be set
to anything without a single test noticing, and D15's cv anchors would have shipped unverified.

Added `TestBands::test_consistency_bands`, confirmed it fails under the same mutation. **This is
the only test added, and it is an addition, not a re-baseline.**

## Test re-baselining: NONE REQUIRED

Zero assertions changed. Expected movers named in the plan (`test_ratings.py:14/51-53`,
`test_api.py:799-956`) all still hold, because those are hand-built fixtures whose values happen
to fall the same side of both old and new anchors. Nothing was deleted, skipped, or weakened.

⚠ Two anchors sit **exactly** on a fixture value — cv good `0.09` vs `test_api.py`'s `0.09`, and
fatigue good `5.0` vs `test_ratings.py`'s `5.0` — and `_band` uses `value <= thr[...]`, so they
land in `good` by equality. Deterministic (identical literals → identical doubles) but fragile;
flagged in a `ratings.py` comment.

---

## Files changed

| file | change |
|---|---|
| `metrics.py` | tagging block deleted; `ss_cycles`/`n_ss` → `cycles`/`n_cycles` at all 12 sites; plotting single-colour; 3 stale comments |
| `ratings.py` | two anchor sets re-measured + a comment block recording why |
| `coach.py` | `ph: S=steady R=ramp_up` column dropped from the LLM prompt |
| `app.py` | `_compute_q1_q4` over all cycles |
| `inspect_cycles.py` | `_steady()` no longer filters; labels |
| `pipeline_view.py` | phase colouring + phase column removed |
| `tests/test_ratings.py` | **+1 test** (`test_consistency_bands`) |
| `tools/rampup_impact.py` | **NEW**, read-only measurement CLI |

## AC results

| AC | result |
|---|---|
| AC-1 one population | ✅ 12/12 live sessions recomputed: `stroke_count == len(cycles)`, no `phase` key |
| AC-2 movement measured | ✅ table above, from a committed reproducible tool |
| AC-3 pillars discriminate | ✅ both at 40% max share (≤60%), score floor 11% |
| AC-4 no reader broken | ✅ all 5 readers updated; `coach.py` verified not to depend on the key in either direction |
| AC-5 suite green, nothing loosened | ✅ 274 passed; 0 re-baselined; 0 deleted/skipped/weakened |

---

## ⚠ Deviations from the plan

1. **"Before and after" runs of `rampup_impact.py` were a plan-design error of mine.** The tool
   reads stored `metrics_json` and computes *both* populations in one pass, so a second run after
   the code change returns identical output — no stored row changed. One run gives both columns.
   AC-1 was instead verified by recomputing live sessions through the new code.
2. **Two bugs I introduced and caught during the task**, recorded because the verify step is what
   caught them, not review: a dangling `{ph}` left in `coach.py`'s row format (would have
   `NameError`d on every coach-chat request carrying per-cycle data), and a `col_data` index
   misalignment in `pipeline_view.py` after removing a column (`IndexError`).
3. **`tests/test_ratings.py` gained a test.** The plan's file list included it for re-baselining;
   no re-baselining was needed, and it was used for an addition instead.

## Plan vs actual (task reconciliation)

| Task | Planned | Actual |
|---|---|---|
| 1 — measurement tool + BEFORE baseline | `tools/rampup_impact.py`, run before any change | ✅ As planned. ⚠ Tool's own delta column was wrong on first run (median over the whole corpus reported +0.0%); fixed to report over affected sessions before the baseline was accepted |
| 2 — remove cycle-phase from metrics.py + 5 readers | 6 files | ✅ As planned; 2 self-inflicted bugs caught by verify (see Deviations) |
| 3 — checkpoint: anchors | 3 options offered | ✅ `percentile-clamped` chosen. ⚠ Options were **re-derived** before presenting, because the plan's stated premise (band collapse) had been disproven by Task 1's measurement |
| 4 — apply anchors + re-baseline | Expected movers named | ✅ Anchors applied; **zero re-baselining needed**; +1 test added instead |

Skill audit: no `.paul/SPECIAL-FLOWS.md` exists — step skipped, no required skills configured.

## Next phase readiness

**Ready**
- 61-02 (report card) and 61-04 (Compare) can now build charts whose dots and numbers describe the
  same population. That was this plan's whole purpose and it is done.
- `tools/rampup_impact.py` is reusable for any future "what would this change move" question.

**Concerns**
- ⚠ **Not deployed.** `metrics.py`, `coach.py` and `ratings.py` are all on the Railway path. Until
  deployed, the web portal reads metrics computed by the OLD code, so 61-02's charts would be
  correct in the repo and wrong in production.
- ⚠ Anchors are corpus percentiles from **one swimmer, 53 sessions**. They discriminate; they are
  not validated. Coach review still owed. Phase 53 may delete absolute bands entirely.
- ⚠ `stroke_count` changed meaning. Any doc, prompt, or UI copy calling it "steady strokes" is now
  wrong; `coach.py` was fixed, but stored parent reports and past exports carry the old semantics.

**Blockers:** None for 61-02.

## Carried out

- ⚠ **Stored sessions are on the old scale.** No backfill; the corpus was already mixed from
  57/59-03/59-05. 61-02/03/04's charts describe newly-computed sessions correctly and stored ones
  on the old scale — same as every prior break.
- ⚠ **The anchors are corpus percentiles from one swimmer's 53 sessions, not coaching judgement.**
  Coach review still owed, as it was before. Phase 53 may remove absolute bands entirely.
- ⚠ **`fetch_sessions.py:30` still hardcodes `FS = 100.0`** — out of scope, still wrong.
- ⚠ Deploy owed: `metrics.py` + `coach.py` + `ratings.py` are on the Railway path.
