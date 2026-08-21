# 76-01 SUMMARY — Breakout Detection (kick-band disappearance)

**Phase:** 76 · **Plan:** 01 · **Closed:** 2026-08-20
**Status:** ✅ Loop closed — with two corrections found at UNIFY, both measured.
**Checkpoint AC-4 (human-verify on real DB plots): NOT RUN — carried out, owed.**

---

## What shipped

| | |
|---|---|
| `metrics.detect_breakout_kickband` (:872) | breakout = the sustained ~2 Hz dolphin-kick band going quiet. Refuses (`None`) on degenerate input, no kick run, too-short kick run, or no in-window quiet. |
| `metrics._kick_band_power` (:849) | dedicated wider CWT (0.5–5.0 Hz). The production ridge's 0.25–2.0 Hz grid **cannot see** the kick band — that blindness is why six prior levers failed. |
| free/back branch in `compute_session_metrics` | per-stroke `ip_end` override, after `detect_swim_window`, **before** the manual override (Phase 47 precedence intact). |
| `metrics._breakout_leaves_swim` + `_BREAKOUT_MIN_SWIM_CYCLES` | **added at UNIFY** — the collapse guard (below). |
| `tools/breakout_band_probe.py` | Task 3 **completed at UNIFY** — now scores the SHIPPED detector on the production path. |
| tests | `TestBreakoutKickband`, `TestBreakoutIntegration`, `TestBreakoutCollapseGuard`. Suite **388 green**. |

## Measured result (committed scorer, live DB, 16 annotated freestyle `stroke_start_s` marks)

| detector | median \|err\| | ≤0.5 s | ≤1.0 s |
|---|---|---|---|
| incumbent (`detect_swim_window`) | 2.07 s | 2/16 | 4/16 |
| **shipped, production path** | **0.42 s** | **10/16** | **12/16** |

AC-1 ✅ · AC-2 ✅ (≤0.6 s, ≥9/16 — met after correction 2) · AC-3 ✅ · AC-4 ⛔ not run · AC-5 ✅

## ⭐ Correction 1 — the branch shipped a `stroke_count = 0` session

APPLY left the suite **RED** and it was not caught: `TestSegmenterDispatch::test_alternating_strokes_pair_wavelet_boundaries` failed with freestyle **`stroke_count` 11 → 0**.

Reproduced: on the committed `processed/breaststroke_sample.csv` driven as freestyle, the detector answered at **t = 25.54 s** of a 31.1 s trace (`ip_end` 15.95 → 25.54 s), leaving ~3 s to segment. The refuse-gate did not fire — a breaststroke trace carries no kick band, so "the band went quiet" is true somewhere arbitrary.

The hole is **structural, not fixture-specific**: the detectors answer a LOCAL question and cannot see what their answer does to the swim they leave behind, and the clamp to `[b_end, swim_end)` does not catch it. A confidently EMPTY session is the one outcome the refuse-to-answer convention exists to prevent.

**Fix — `_breakout_leaves_swim`:** the plausibility gate `_window_from_ridge` already applies to the swim window (`_WINDOW_MIN_CYCLES = 4.0`), applied to the window an override would LEAVE. Refuse when `[breakout, swim_end)` spans under `_BREAKOUT_MIN_SWIM_CYCLES = 2.0` at the rhythm the ridge tracks there.

The floor sits in a **measured gap**, not fitted to the fixture:

| | surviving-window cycles |
|---|---|
| the collapsing fixture | **1.60** |
| every real freestyle detection (n=12 with a detection) | min **2.45**, median 9.5 |
| butterfly collapses (9 sessions) | 0.47 – 1.72 |

**Cost: zero.** No freestyle session is vetoed; median \|err\| is unchanged with the guard on. It vetoes 7 butterfly collapses (+6.5 to +11.1 s), which is exactly the pathology — informational only, since fly does not route here.

## ⭐ Correction 2 — the headline number was the probe's, not production's

Task 3 was **never done in APPLY**: `tools/breakout_band_probe.py` scored its own exploratory reimplementation (`_detect_breakout`, unbounded), not `metrics.detect_breakout_kickband`. That is precisely the drift the plan wrote the task to prevent, and it had already happened.

Pointing the probe at production (`ship_err` column) showed **0.86 s median, 7/16 ≤0.5 s — outside AC-2** — against the **0.30 s / 11-of-16** that had propagated into STATE.md, PROJECT.md and the Phase 77 CONTEXT.

Ablation isolated the cause. Not the underwater-start source (annotated vs auto: 0.86 vs 0.87 — no effect) and not the `swim_end` bound (which *helps*: 1.92 → 0.86). It was **`_KICK_MIN_RUN_S = 1.0`**, vetoing 4 of 16 sessions the detector had already placed to within 0.5 s (−0.32, −0.47, +0.02, −0.18) because their underwater was short but real; all 4 fell back to the incumbent at +1.85 … +3.25 s.

Sweep on the production path, all 16 sessions:

| `_KICK_MIN_RUN_S` | median | ≤0.5 s | ≤1.0 s | refusals |
|---|---|---|---|---|
| 0.00 (gate off) | 0.42 s | 10/16 | 13/16 | 0 |
| **0.50 (shipped)** | **0.42 s** | **10/16** | **12/16** | 1 |
| 0.60 | 0.42 s | 9/16 | 11/16 | 2 |
| 0.75 | 0.81 s | 7/16 | 9/16 | 4 |
| 1.00 (as applied) | 0.81 s | 7/16 | 9/16 | 4 |

**0.5 s** is mid-plateau (0.0–0.6 all give 0.42 s) rather than a knife-edge fit, keeps a real floor rather than disabling the gate, and the new collapse guard now independently covers the late-wrong-answer case this constant was half-proxying.

`test_none_when_kick_run_too_short` was rewritten to raise the floor above a known-good 3 s kick run instead of shrinking the run under the floor — `_KICK_SMOOTH_S` is 0.4 s, so a burst short enough to beat a 0.5 s floor is smeared past it by the smoothing. It now tests the mechanism and stays valid at any measured floor.

## Carried out — owed

1. **AC-4 human-verify never ran.** `python tools/breakout_band_probe.py --plot` renders the traces; the user has not eyeballed them. Both corrections were found by measurement, not by the checkpoint the plan put there to catch exactly this.
2. **Backfill (D5).** ~37 stored free/back sessions carry the pre-76 `stroke_start_s`. Comparability break, standing pattern (57 / 59-03 / 61-01 / 65). Separate post-approval step; Claude is blocked from prod writes.
3. **Butterfly is untouched and still wrong** (3.00 s shipped vs 2.67 s incumbent — it does not route here). That is Phase 77.
4. **Downstream claims to correct**, since the 0.30 s figure spread before it was checked: PROJECT.md, the Phase 77 CONTEXT, and any note citing "11/16 within 0.5 s". The true production figures are 0.42 s and 10/16.

## Files

`metrics.py` · `tests/test_metrics.py` · `tools/breakout_band_probe.py`
Untouched as required: `api.py`, `annotations.py`, `phase_metrics.py`, `supabase/`, mobile, web.
