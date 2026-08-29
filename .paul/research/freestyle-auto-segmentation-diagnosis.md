# Research: State of freestyle auto stroke-cycle segmentation

**Date:** 2026-08-25 · **Type:** codebase diagnosis (no production code changed) ·
**Home phase:** [80 — Stroke-Cycle Segmentation](../phases/80-stroke-cycle-segmentation/CONTEXT.md)
**Deliverable:** interactive 3-column viewer →
`.paul/phases/80-stroke-cycle-segmentation/figs/human_vs_seg_3col.html`
(script: `.../human_vs_seg_3col.py`)

## Question

Diagnose auto **stroke** segmentation for freestyle, using the most-recent *shipped* technique,
**inside the human-annotated swim window** (`[stroke_start_s, finish_s]`), at **per-stroke**
granularity (every arm entry) — not the 2-strokes-per-cycle production output.

## Vocabulary (already formalized in the codebase — `annotations.py` D-2026-08-05)

- **stroke** = one **arm entry** (hand touches water). Human `stroke_marks_s` are strokes.
- **cycle** = 2 strokes (freestyle alternates arms; `annotations.MARKS_PER_CYCLE["freestyle"] = 2`).
- This diagnosis works at **stroke** granularity, so the production `k=2` cycle-pairing
  (`_pair_boundaries`) is deliberately bypassed. A cycle count is just `strokes / 2`.

## Method

- **Corpus:** all 22 annotated freestyle sessions from Supabase (Tony 8 / Leo 8 / Max 6).
  21 well-labeled; 1 flagged `⚠partial` (coverage < 0.7 — too few marks to score, still plotted).
- **Window:** every panel clamped to the human `[stroke_start_s, finish_s]` (Phase 80 D5), so the
  swim-window detection error (a Phase 75–79 concern) is removed and only the *segmenter* is judged.
- **Shipped technique:** `metrics.segment_cycles_wavelet` — Morlet-CWT ridge → cumulative phase →
  one boundary per integer crossing. Run **un-paired** = the stroke detector. Its shipped knob is
  `_RIDGE_LOW_BAND_BIAS = 0.5`.
- **Detectors compared** (identical except `low_band_bias`, via `metrics._cwt_ridge`):
  - col 2 **Shipped ridge (bias 0.5)** — what production actually uses.
  - col 3 **No low-band (bias 0.0)** — the Phase-80 candidate (not shipped).
- Reused `visualize_freestyle_seg.load_freestyle()` / `strokes_wavelet()` / `_win()` and
  `segmenter_eval.coverage()` — no re-implementation. Success metric = **stroke COUNT + CADENCE**
  (Phase 80 D1), not ±0.15 s boundary placement.

## Results (reproduced live this run — not cited)

**Overall, well-labeled (n=21):** (±1 stroke = ±½ cycle)

| detector | exact-count | within ±1 | median \|ΔN\| | median \|rate err\| |
|---|---|---|---|---|
| shipped ridge (bias 0.5) | **6/21 = 29%** | 15/21 = 71% | 1.0 | **3.8%** |
| no low-band (bias 0.0) | **8/21 = 38%** | 16/21 = 76% | 1.0 | **3.2%** |

**Per swimmer** (within ±1 stroke; exact-count in parens):

| swimmer | n | shipped 0.5 | fix 0.0 |
|---|---|---|---|
| Tony | 7 | 86% (exact 3) | 86% (exact 4) |
| Leo  | 8 | **88% (exact 3)** | 50% (exact 2) |
| Max  | 6 | 33% (exact 0) | **100% (exact 2)** |

At ±1 the story sharpens: shipped is adequate on Tony/Leo (86–88%) but collapses on Max (33%);
bias 0.0 makes Max perfect (100%) but halves Leo (88→50%, over-counts moderate tempo). No single
global bias wins across all three swimmers → **adaptive bias**, not a flip (see read 3 below).

## Diagnosis (three reads)

1. **Cadence is already trustworthy; COUNT is the failure.** Median stroke-rate error is ~3–4%, but
   the shipped detector nails the exact stroke count on only **29%** of sessions (usually ±1). The
   coach-facing *rate* is fine; the *count* is not. There is **no constant offset to forgive** —
   matched boundaries sit within ~0.07 s (Phase 80), so the error is genuine miscount, not a shift.
   (This is why Phase 80 D1(c)'s offset-tolerance is inert for freestyle.)

2. **The low-band bias is Max's undercount.** Shipped bias 0.5 gets **0/6** exact on Max (the fast,
   never-tuned swimmer) — the DP ridge locks onto a subharmonic and drops strokes. Turning the
   low-band bias off recovers them (**0% → 33%**, median \|ΔN\| 2.0 → 1.0). Visible per-session in the
   green vs blue columns of the viewer.

3. **A *global* bias flip is the wrong fix — it trades swimmers.** bias 0.0 helps Tony (43→57%) and
   Max (0→33%) but **regresses Leo (38→25%)**, where it over-counts moderate-tempo cycles (median
   \|ΔN\| 1.0 → 1.5). So the direction is an **adaptive** low-band bias (off only when the ridge rails
   low / tempo is fast — the Phase 65-02 low-rail-guard pattern), not a blanket zero. This *confirms*
   Phase 80 CONTEXT's 2026-08-23b instinct with fresh per-swimmer evidence.

## Adaptive-bias prototype (2026-08-25) — 4th column

Prototyped an **adaptive low-band bias** mirroring the Phase 65-02 low-rail guard
(`detect_swim_window:621-630`): keep shipped bias 0.5 by default; flip to 0.0 **only** when a
guard detects subharmonic lock — the shipped ridge's median frequency < `SUBHARM_FRAC (0.70) ×`
the **independent** autocorr stroke frequency (`_estimate_period`). Anchoring on the autocorr
estimate (not on the bias-0.0 ridge) is what stops it firing on Leo. Prototype lives in the
viewer only (`human_vs_seg_4col.html` / `.py`); **`metrics.py` untouched**.

Well-labeled (n=21):

| detector | exact | within ±1 | median \|rate err\| |
|---|---|---|---|
| shipped 0.5 | 29% | 71% | 3.8% |
| global fix 0.0 | 38% | **76%** | 3.2% |
| **adaptive guard** | 29% | **76%** | 3.8% |

Per swimmer, within ±1: Tony 86/86/86 · Leo 88/**50**/**88** · Max 33/**100**/50 (shipped/fix/adaptive).

**Reads:**
1. **Pareto win** — adaptive matches the global fix's aggregate (76% within ±1) **without** Leo's
   regression (88% vs the flip's 50%). Never worse than shipped unless the guard fires.
2. **Only half-recovers Max (33→50%).** Guard fired on 3/21 sessions; caught only Max's one
   *dramatic* subharmonic (`00:35`: ridge 0.29 Hz vs autocorr 1.53, ratio 0.19 → 8→17 strokes,
   exact). Max's other 5 misses sit at ratio ~0.95 — not median-subharmonic, so the guard stays
   (correctly) put and (unhelpfully) wrong.
3. **A frequency-ratio guard can't catch the rest of Max** — his mild misses (ratio 0.90–0.99)
   overlap Leo's *healthy* tracking; no threshold separates them without re-triggering Leo.

**New lead the prototype exposed:** `Max 00:45/00:52` show `f_ship` = 1.95/**2.00 Hz** = the CWT
scale-grid **ceiling** (`1/_PERIOD_MIN_S = 2.0 Hz`) yet still undercount → Max's fast tempo is
railing the *high* end of the grid, a `_PERIOD_MIN_S` / scale-grid problem the low-band bias cannot
fix. → **adaptive bias is necessary, not sufficient**; fully closing Max needs a second lever
(widen the scale grid past 2.0 Hz and/or a dropped-stroke merge/prominence post-filter). Cleaner
Step-2 target than a bias flip.

## Caveats

- 3 swimmers, 1 annotator (Tony's hand-touch-water rule); cross-swimmer generalisation still
  untested on the ~11 unannotated DB swimmers (Phase 78). The fix looks best on the one swimmer
  (Max) it wasn't tuned on, which is the encouraging direction — but n=6.
- Diagnosis only. The *improve* step (adaptive-bias LOSO sweep, held-out Max) is Phase 80 Step 2 —
  not done here.

## Pointers

- Interactive viewer: `.paul/phases/80-stroke-cycle-segmentation/figs/human_vs_seg_3col.html`
- Generator: `.paul/phases/80-stroke-cycle-segmentation/human_vs_seg_3col.py`
- Fuller decision history + notebook: `.paul/phases/80-stroke-cycle-segmentation/CONTEXT.md`
- Mechanism of record: `PIPELINE.md` §5 (stroke-cycle segmentation), §8 (validation reality)
