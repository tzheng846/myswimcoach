---
phase: 79-dive-start-redefine
plan: 01
type: execute
status: complete
date: 2026-08-21
files_modified:
  - metrics.py                     # NEW detect_dive_start (+ _DIVE_CROSS_MS, _DIVE_FOOT_PROM_FRAC)
  - phase_metrics.py               # resolve_boundaries: dive_start via detector, "detected"/"auto"
  - annotations.py                 # build_seed prefers stored dive_start_s (mirror underwater)
  - tools/score_dive_start.py      # NEW read-only X + prominence sweep vs ground truth
  - tests/test_metrics.py          # detect_dive_start unit tests
  - tests/test_phase_metrics.py    # resolve_boundaries source/fallback cases
  - tests/test_annotations.py      # build_seed stored-vs-fallback
  - PIPELINE.md                    # §3 row + callout rewritten to the shipped rule
  - .paul/STATE.md                 # item 1 resolved; backfill owed recorded
chosen_X: 2.0
prom_frac: 0.15
tests_green: true            # pytest tests/ = 422 passed
db_writes: false            # backfill is USER-run
---

# 79-01 SUMMARY — `dive_start_s` = foot of the launch surge, not motion onset

## Headline
`dive_start_s` no longer keys on motion onset (`baseline_end`), which fired early on the
jump-and-sink block artifact. It is now **`detect_dive_start`**: the **foot of the first velocity
surge that clears X = 2.0 m/s** — the tug never reaches X, a real dive/push-off does — anchored at
the low trough just before the crossing. When nothing crosses X (a weak wall push-off) it **falls
back to `baseline_end`**, so it is never worse than the old rule. Measured against 36 hand-marked
sessions: **mean|err| 0.15 s vs baseline_end's 0.72 s.**

## What shipped
- **`metrics.detect_dive_start(t, vel, threshold=2.0, prom_frac=0.15)`** — pure, NaN-safe (runs on
  the stored `velocity_profile` via `/recompute`, which can carry magnet-dropout nulls; does not
  route through `_window_v95`). Algorithm: first finite index with `vel ≥ X`; then `find_peaks(-head)`
  with `prominence = prom_frac·X` and return the **last** (nearest) prominent trough left of the
  crossing. Returns `None` when no sample reaches X or no prominent trough precedes it → caller falls
  back to `baseline_end`. Never raises.
- **`phase_metrics.resolve_boundaries`** — where the coach has not marked `dive_start_s`, calls the
  detector on `ctx.t / ctx.vel`. Hit → `bounds["dive_start_s"] = idx/fs`, source **`detected`**.
  `None` → the existing `baseline_end` seed stands, source **`auto`**. A manual annotation still wins.
  Resolved **before** `underwater_start_s`, which seeds its search off `dive_start_s`.
- **`annotations.build_seed`** — prefers a stored `phases.boundaries.dive_start_s` over
  `baseline_end_s` (mirrors the 75-02 underwater block), so the annotate draft shows the new marker
  on recomputed/new rows while pre-79 rows fall back unchanged.
- **`tools/score_dive_start.py`** — read-only Supabase harness (service-role, no writes, no PII):
  X sweep + prominence sweep + per-stroke / per-session tables + AC-3 verdict. Reads
  `velocity_profile` directly and `baseline_end_s` from `metrics_json_auto` (circularity guard, same
  as `score_segmenter`).

## Tuning result  (`python tools/score_dive_start.py`, 36 hand-marked `dive_start_s`)

X sweep at prom_frac = 0.15 (production-effective: detector foot where a ≥X surge fires, else `baseline_end`):

| X (m/s) | fired | mean\|err\| | within 0.5 s |
|--------:|------:|------------:|-------------:|
| 1.25 | 18/36 | 0.13 s | 36/36 |
| 1.50 | 18/36 | 0.14 s | 36/36 |
| **2.00** | **16/36** | **0.15 s** | **36/36** |
| 2.50 | 10/36 | 0.21 s | 33/36 |
| 3.00 | 3/36 | 0.70 s | 27/36 |
| **INCUMBENT `baseline_end`** | — | **0.72 s** | 26/36 |

- **Detector-only** on the 16 real-surge sessions at X=2.0: **0.11 s, 16/16 within 0.5 s.**
- Per-stroke (production-effective, X=2.0): breast 0.11 s (4/4) · fly 0.11 s (15/15) · free 0.19 s
  (16/16) · udk 0.15 s (1/1).
- **Chosen X = 2.0** (prom_frac 0.15, both the module defaults). Accuracy is statistically tied
  across X∈[1.25, 2.0] — all 36/36 within 0.5 s — so X was picked for the **widest margin against the
  jump-and-sink tug**, the design's whole purpose, not to shave 0.02 s of in-corpus MAE. A lower X
  fires ~2 more sessions but risks the tug crossing the threshold on unseen weak push-offs.

## AC status
- **AC-1** ✅ `detect_dive_start` returns the surge foot after the artifact, `None` sub-threshold /
  monotonic-rise (`pytest tests/test_metrics.py -k dive_start`).
- **AC-2** ✅ `resolve_boundaries` → `detected` with a surge, `auto`/`baseline_end` fallback without,
  manual overrides; `build_seed` prefers the stored boundary, falls back on pre-79 rows.
- **AC-3** ✅ chosen-X MAE 0.15 s ≤ baseline_end 0.72 s. **underwater_start not regressed —
  measured, ΔMAE = 0.000 s.** `resolve_boundaries` *does* re-seed `detect_underwater_start` from the
  new `dive_start_s` (it moves the seed on **16/37** annotated sessions), yet recomputing underwater
  both ways gives an identical **0.114 s MAE, 34/37 within 0.5 s**. Reason: the new `dive_start` foot
  still sits just *before* the same dive-surge peak, so the surge-peak `argmax` (4 s window) and the
  first-trough-after are unchanged. Full suite green.
- **AC-4** ✅ eyeball approved by the coach 2026-08-21 (X=2.0). On dives the marker sits at the launch
  foot (skipping the tug); the udk session where `baseline_end` fired **12 s early** is now correct;
  on sub-X starts it falls back to the old motion-onset spot, not somewhere wrong.

## Verification
- `pytest tests/` → **422 passed** (1 pre-existing all-NaN-slice warning).
- Boundaries unchanged besides `dive_start_s`: underwater, breakout (fly / free-back), cycle
  segmenters, finish untouched. No Hampel/gradient filter added. No DB writes.

## ⚠ BACKFILL — USER-RUN, still owed
Redefining a stored boundary is a comparability break: every session in the library still carries the
**old** `baseline_end`-derived `dive_start_s` in its stored `metrics_json.phases`. Claude is blocked
from prod writes, so **the user runs**:

```bash
python tools/backfill_phases.py --apply
```

This re-runs `resolve_boundaries` over the stored velocity/distance/accel profiles (no raw-CSV read)
and rewrites `dive_start_s` — and any dependent phase metrics — across all sessions. Standing pattern
(57 / 59-03 / 61-01 / 65 / 76-77). Until it runs, new/recomputed sessions use the foot-of-surge rule
while untouched historical rows keep the old marker (mixed library — expected, resolved by the backfill).

## Commit note
Phase 79 is uncommitted and **intermingled in the working tree with Phase 78** (multiswimmer
diagnostic) and 75-03 (kick metrics). Separate the commits by file set — 79 = `metrics.py`,
`phase_metrics.py` (dive_start block), `annotations.py`, the 3 test files, `PIPELINE.md §3`,
`tools/score_dive_start.py`.
