---
phase: 78-multiswimmer-seg-diagnostic
plan: 01
type: research
status: complete
date: 2026-08-21
files_modified:
  - tools/annotated_roster.py            # NEW read-only census + full-roster coverage gap
  - tools/score_segmenter.py             # banner string only ("ONE SWIMMER" -> real count)
  - PIPELINE.md                          # §8 rewritten with the resolved roster + coverage gap
  - .paul/STATE.md                       # item 2 resolved; owed gaps carried forward
zero_production_detector_changes: true
tests_green: true
---

# 78-01 SUMMARY — 4 swimmers annotated, but ~15 exist: a coverage gap, not "one swimmer"

## Headline
The "**ONE SWIMMER**" stamp is false, **and** the naive answer "so it's a clean multi-swimmer
corpus, delete the caveat" is *also* false. The real shape (resolved fork **(b)**):

- **The scored corpus is 4 swimmers** — Tony, Leo, Chantee, Dane — because **only those 4 have
  ever been annotated**.
- **The DB holds ~15 distinct humans.** STATE's roster instinct was right: **Titus (8 sessions)
  and AlexGroup (9 sessions) are real**, plus Jenna (2) and Michael (1). **AlexGroup is exactly the
  stand-in it was called** — its 9 session *names* are individual testers: **Henry, Ben, Desi,
  Spencer, Alina, Tate, Olivia, Anna**.
- **All of them are unannotated.** 92 sessions exist, **only 37 (40%) are annotated**; 5 athletes /
  23 sessions carry **zero** annotations and are invisible to every scorer.

So no detector was fit on a hidden *one-swimmer* subset — but **the validation is confined to 4 of
~15 swimmers purely by annotation coverage.** The labeled data did not "go unused"; the *unlabeled*
data (Titus, the 8 AlexGroup testers, Jenna, Michael) was never scored at all. The caveat is **not
deleted — it is re-scoped**: cross-swimmer generalisation is *tested on 4 swimmers, unknown on ~11
more sitting in the DB right now.*

## Full-roster coverage  (`python tools/annotated_roster.py`, read-only)
| Athlete | Total | Annotated | Note |
|---|---:|---:|---|
| Tony | 37 | 18 | |
| Leo | 27 | 14 | |
| **AlexGroup** | 9 | **0** | STAND-IN → Henry/Ben/Desi/Spencer/Alina/Tate/Olivia/Anna |
| **Titus** | 8 | **0** | free ×4, fly ×4 |
| Test | 3 | 0 | junk/test data |
| Chantee | 3 | 3 | |
| **Jenna** | 2 | **0** | |
| Dane | 2 | 2 | |
| **Michael** | 1 | **0** | |
| **Total** | **92** | **37 (40%)** | 4 of 9 athlete rows annotated |

**Annotated-only census by stroke:** free 16 (Tony 8, Leo 8) · fly 16 (Tony 10, Leo 3, Chantee 3) ·
breast 4 (Leo 2, Dane 2) · udk 1 (Leo) · **back 0**. Backstroke is n=0 in scoring because its **2 DB
sessions (Tony 1, AlexGroup/Tate 1) are both unannotated**, not because backstroke wasn't swum.

## Per-detector verdict (on the 4-swimmer *annotated* corpus)

| Detector | Full-corpus number | Per-swimmer | Verdict |
|---|---|---|---|
| **underwater_start_s** (75-02) | mean\|err\| **0.13 s**, 34/37 ≤0.5 s, 0 miss | breast 0.03 · free 0.15 · fly 0.13 s | ✅ **still good** on all 4 annotated swimmers |
| **breakout freestyle** (76) | median **0.42 s**, 10/16 ≤0.5 s | Tony 0.58 s (4/8) · Leo 0.34 s (6/8) | ✅ **still good** — both swimmers, not one |
| **breakout butterfly** (77) | median **0.38 s**, 9/16 ≤0.5 s, 1 refuse | Tony 0.26 (6/10) · Leo 0.29 (3/3) · **Chantee 0.87 (0/3)** | ⚠ **good but uneven** — headline is Tony/Leo; **degrades on Chantee** (only post-tuning swimmer). Still ≪ incumbent 2.67 s |
| **breakout backstroke** (the "back" in 76's "free/back") | — | annotated **0** (2 unlabeled sessions exist) | ⛔ **insufficient n = 0** — never validated; labels *are collectable* (annotate Tony bk + Tate bk) |
| **breakout breaststroke** | — (incumbent, untuned) | Leo 2 / Dane 2, no stroke_start marks | ⛔ **insufficient n** — pre-existing owed item |
| **cycle segmentation wavelet** (59) | annotated/cycles F1 free 0.31, fly 0.32, breast 0.41 (trough collapses on free) | free T8/L8 · fly T10/L3/C3 · breast L2/D2 | ✅ **unchanged** — always measured on this 4-swimmer set; n=1 was never true |
| **dive_start_s** | MAE 0.72 s, p50 0.25 s, **worst 12.4 s** (n=36) | all 4 | ⚠ **known defect** → **Phase 79** |
| **finish_s** (inherited) | MAE 2.76 s, bias +2.10 s, worst 6.43 s (n=36) | all 4 | ⚠ **weakest marker** — no phase owns it |

## What changed in the repo (measurement-only, per boundaries)
- **NEW** `tools/annotated_roster.py` — read-only. Part A = annotated census; **Part B = full-roster
  annotation-coverage** so the unannotated swimmers (Titus/AlexGroup/Jenna/Michael) are impossible to
  miss, with the AlexGroup stand-in expanded to its per-session tester names.
- `tools/score_segmenter.py:329` — "ONE SWIMMER" banner corrected to the real count + coverage gap.
- `PIPELINE.md §8` — roster + coverage gap rewritten.
- **No detector, no constant, no pure function touched.** `pytest tests/` → 420 passed.

## Owed / carried forward to STATE
1. **⭐ Annotate the backlog — 20 real-swimmer sessions sit unscored.** Titus 8, AlexGroup 9 (8 named
   testers), Jenna 2, Michael 1. This is the single highest-leverage fix: it converts "generalises,
   probably" into a measured cross-swimmer number, and **unlocks backstroke** (annotate Tony bk +
   AlexGroup/Tate bk) and far more breaststroke. Then **re-run this exact diagnostic.**
2. **Backstroke breakout unvalidated (n=0)** — but 2 labelable sessions exist. Stop claiming "back" in
   "free/back" until at least those are scored.
3. **Fly breakout thins outside Tony/Leo** — Chantee (post-tuning) 0.87 s. Re-check after item 1.
4. **finish_s is the weakest phase marker** (MAE 2.76 s), owned by no phase. Candidate for a pass.

## AC checklist
- **AC-1** ✅ census prints totals, per-stroke swimmers, by-athlete sessions, **full-roster coverage**,
  and the AlexGroup expansion (correctly — by the athlete row, its session names = testers).
- **AC-2** ✅ all three scorers re-run live (37 sessions); reports cached in scratchpad; each scored
  session attributable to a swimmer via `roster.json`.
- **AC-3** ✅ per-detector, per-swimmer verdict above; "one swimmer" resolved as fork **(b)** (confined
  by annotation coverage, not deleted); PIPELINE §8 + banner corrected.
