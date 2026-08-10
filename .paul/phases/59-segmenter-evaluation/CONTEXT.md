# Phase Context

**Phase:** 59 — Segmenter Evaluation (ground-truth scoring harness + per-stroke dispatch)
**Generated:** 2026-08-08 · **Revised:** 2026-08-09 (AskUserQuestion ×3 rounds, 12 questions)
**Status:** Ready for planning
**Predecessor:** Phase 58 (Video Ground Truth) — 58-01/02/03/05 closed; **58-04 (`VideoPane`
end-anchor) still owed**. ⚠ STATE.md still lists 58-05 as "awaiting approval"; ROADMAP.md records it
COMPLETE 2026-08-07. ROADMAP is the newer of the two — it is edited from a second PAUL environment.
**Supersedes:** the long-referenced "16-06 segmenter tuning" slot (see D1)

---

## Why now

The user has finished a labeling push and asked: *"now that I've labeled a bunch of sessions, what
is my next step? I need to train a segmenter."*

The premise is right — labeled data is the unlock — but the specific ask is not what the data
supports. **23 sessions / 236 marks / one swimmer / one pool / one device / zero backstroke is not a
training set; a learned model would memorize this swimmer.** It is a perfectly usable *evaluation and
tuning* set, and evaluation is what has never existed: `segmentation_reliable = False` is a hardcoded
constant in `metrics.py`, not a measurement. Nothing in the repo can currently answer "is this
segmenter better than that one?"

So the phase inverts the request: **build the instrument before running the experiment** — the same
move Phase 53 made with `repeatability.py`.

The user asked that this discussion not lean on stored memory, which they suspect is stale (they
named `segmentation_reliable=False` as an example). Everything below was measured against the live
database and current source on 2026-08-08, not recalled.

---

## What was measured (2026-08-08, live DB + current code)

### The corpus

`python fetch_annotations.py` → **23 annotated sessions, 236 stroke marks**:

| stroke | sessions | note |
|---|---|---|
| freestyle | 14 | 2 partial (see D4) |
| butterfly | 7 | |
| breaststroke | 2 | too few to tune against |
| backstroke | **0** | `MARKS_PER_CYCLE["backstroke"] = 2` is entirely unvalidated |

Two from 2026-06-23; 21 from the 2026-08-05 and 2026-08-07 batches. The 08-07 sessions are the first
labeled with 58-02's video tooling and are visibly the best of the set.

### The labels are internally consistent — verified, not assumed

Per session, mean mark ISI was compared against the dominant oscillation period of that session's own
velocity trace inside the annotated swim window (autocorrelation, 0.3–3.0 s search). **In 20 of 23
sessions the two agree within ±5%**; ISI coefficient of variation is 0.01–0.20.

This independently confirms freestyle marks were placed at **arm entries** (2 per cycle), not per
cycle, as the Phase-57 contract requires: freestyle ISIs (0.70–1.42 s) look slow for a cycle rate and
correct for an entry rate, and the trace agrees with them.

### `sessions.velocity_profile` makes the harness cheap

The live schema carries `velocity_profile jsonb` and `sample_rate_hz double precision` per session.
**No raw-CSV downloads, no Storage round trip** — one table read gets both the trace and its rate.

Checked rather than assumed: the two June sessions have `sample_rate_hz = NULL` (pre-Phase-52) but
genuinely ran at ~100 Hz (2033 samples ÷ 20.3 s `lap_time_s` = 100.1; 1309 ÷ 13.1 = 99.9), so the
`annotations.FS_HZ` fallback is *accurate* for them, not an ~11% scale error. Safe to score. Every
August session reports 89.9928 Hz.

### First-ever score of the production segmenter

`segment_cycles_wavelet` run on each session's stored velocity profile, sliced to the **annotated**
swim window `[stroke_start_s, finish_s]` — deliberately generous, since it removes phase-detection
error and isolates the segmenter — boundaries matched greedily 1-to-1 against human marks.

| comparison | tolerance | recall | precision |
|---|---|---|---|
| wavelet vs human **cycle** boundaries (`marks[0::k]`) | ±0.20 s | 0.57 | 0.28 |
| wavelet vs human **arm entries** (all marks), freestyle | ±0.30 s | 0.82 | 0.67 |
| same, butterfly | ±0.30 s | 0.68 | 0.40 |
| same, breaststroke (n=2) | ±0.30 s | 0.57 | 0.31 |

Median timing error where a boundary matched: **0.06–0.16 s**.

Read: **the ridge tracks the right oscillation and usually lands within ~0.1 s of a human mark. It
disagrees about what one oscillation *means*, and that disagreement is stroke-specific.**

### `marks_per_cycle` ≠ `boundaries_per_cycle` — the finding that shapes D9

The human labeling convention and the segmenter's output rate are **different numbers**:

- **freestyle** — wavelet emits **1.15–1.5× the arm-entry count** (≈2.3–2.75× the cycle count).
  Consistent, mild over-segmentation on top of a 2:1 structural ratio.
- **butterfly** — **1.18–2.18× the cycle count**, unstable session to session: the ridge sometimes
  locks onto the two-dolphin-kick harmonic rather than the stroke.

So there is no single divisor to apply, and `annotations.MARKS_PER_CYCLE` cannot be reused for the
auto path. This is the concrete reason the harness must come before any pairing fix.

### A live product defect fell out of it

`compute_session_metrics(t, vel, dist, head_waist_m, manual)` **never receives `stroke_type`**.
`annotations.marks_per_cycle` is called from exactly two places — `annotation_to_overrides`
(`annotations.py:203`) and the annotation endpoints (`api.py:820`, `:926`). Nothing on the auto path
knows a freestyle cycle is two arm entries, so every wavelet boundary is counted as one cycle.

Measured on the well-labeled 08-07 freestyle batch — `metrics_json_auto.session.stroke_rate_spm`
versus annotation-recomputed `metrics_json.session.stroke_rate_spm`:

```
18:13  65.8 → 37.7  (1.75×)     18:43  63.5 → 31.0  (2.05×)
18:18  51.7 → 30.3  (1.71×)     18:47  41.8 → 28.3  (1.48×)
18:20  44.2 → 21.2  (2.08×)     18:50  52.5 → 33.5  (1.57×)
18:31  46.0 → 26.1  (1.76×)     19:11  83.7 → 43.3  (1.93×)
```

**Every freestyle session in the app and on the web is displaying roughly double the true cycle
rate**, and `stroke_count` with it. Butterfly 0.86–1.32×, breaststroke 1.11–1.45×. Same
silent-plausible-corruption shape as Phases 51/52/57: the number looks like a stroke rate, sits in a
believable range, and is wrong by a factor. It also means the *auto* and *annotated* halves of the
same session are not on the same scale, so any comparison between them is currently invalid for
freestyle.

⚠ **Caveats that must survive into the plan.** Greedy 1-to-1 matching is order-dependent (an optimal
assignment may shift the numbers); scoring used the *annotated* window, not the production
`vel[ip_end:swim_end]`, so production will score worse; precision is a **lower bound** wherever
labels are partial (D4). **The scripts live in the session scratchpad and are NOT committed.** Treat
every number above as a strong prior to reproduce, not an established result.

---

## Decisions (user, 2026-08-08 / 2026-08-09, AskUserQuestion ×3 rounds)

**D1 — New Phase 59; 16-06 retired.** "16-06 segmenter tuning" has been the named future slot since
Phase 16-04. It is superseded. ⚠ Reconciliation scope is **living documents only**: `CLAUDE.md`,
`.paul/PROJECT.md`, `.paul/ROADMAP.md` (incl. the Phase 16 row), `.paul/STATE.md`,
`CODEBASE-AUDIT.md`. The ~25 historical `*-PLAN.md` / `*-SUMMARY.md` files mentioning 16-06 are a
**record and must not be rewritten** — the norm that kept patch_07's Breakout comments untouched in
58-02.

**D2 — Harness first; algorithm chosen by the numbers.** No tuning or replacement in the first plan.
Score wavelet, the never-called `segment_cycles_trough`, and a peak-pick baseline across the corpus,
then let the table choose. The user explicitly did *not* pick "tune the wavelet" or "replace it" up
front.

**D3 — Primary gate: boundary-matching F1 at ±0.15 s, per stroke, with a tolerance sweep.** Stroke-
rate error and timing MAE reported alongside but do not gate. A segmenter can produce the correct
*rate* with every boundary in the wrong place, and the per-cycle metrics (`mean_dps_m`, `cv_isi`,
`mean_coast_fraction`, `mean_impulse_m`) all depend on where boundaries actually land.

**D4 — Partial labels handled by a hand-curated exclusion list, not a schema change.** Four proposed,
derived from coverage math, **to be confirmed by the user at plan time** (they are the annotator):

| session_id | when | stroke | reason |
|---|---|---|---|
| `e20cd07d-ab8d-4e15-988c-e9f72103ead8` | 06-23 16:46 | freestyle | 3 marks; coverage 0.71 |
| `8a51ece7-a182-475f-b529-46cea7dd76fe` | 08-05 19:50 | freestyle | 3 marks; coverage 0.50 |
| `149f6520-d3a4-4949-849f-fccf0ab812e1` | 08-05 20:06 | freestyle | mark ISI 1.32× the trace's own oscillation period → likely missed entries |
| `6b206400-4747-4289-a8cb-ba3f07987c2a` | 08-05 20:57 | butterfly | `finish_s` null — no swim window to score against |

Excluded sessions are still **scored for recall and reported**, just kept out of precision/F1
aggregates. ⚠ The list goes stale as labeling continues — the harness must print the coverage
statistic it was derived from. An explicit completeness flag in the annotation contract was offered
and declined for now; it remains the correct long-term answer and is exactly the vocabulary Phase 58
D4 said does not exist.

**D5 — Tuning scope is freestyle + butterfly (21 sessions).** Covers both the alternating case and
the simultaneous case. Breaststroke (n=2) and backstroke (n=0) are **scored and reported but never
tuned against** — the report must say so, or the next reader mistakes two sessions for validation.

**D6 — Committed pure module + CLI + checked-in fixture + pytest regression.** Without the fixture the
harness needs network and `.env`, and a guardrail requiring credentials is not a guardrail.

**D7 — The cycle-definition fix lands in this phase, after the harness** (now in 59-03 per D14). ⚠ It
is a **comparability break** of the same class as Phase 57's v95 change — `stroke_rate_spm` and
`stroke_count` move on every existing freestyle and backstroke session, and `CLAUDE.md` owes a note
that rates computed before and after are not comparable.

**D8 — `segmentation_reliable` stays hardcoded `False`.** The harness reports measured agreement per
stroke; the product flag does not move until a tuned segmenter earns it. (This answers the user's
"I feel like a lot of it is stale — things like `segmentation_reliable=False`": it is not stale, it
is *unmeasured*, and after 59-01 it becomes a claim with a number behind it.)

**D9 — Per-stroke segmenter dispatch; `metrics.py` owns its own registry.** User: *"the metrics should
be split by each individual stroke — they have different markers. Breaststroke has exclusively pull
down, the other three has dolphin kick, cycle differences etc."*
`compute_session_metrics(..., stroke_type=None)` plus a stroke→implementation registry inside
`metrics.py`. **No import edge from `metrics.py` to `annotations.py`** (there is none today), because
the two tables mean different things: `annotations.MARKS_PER_CYCLE` is the **labeling convention**,
the `metrics.py` registry is **segmenter behavior**, and the measurement above proves they are not the
same number. `stroke_type=None` → today's path exactly, so all **8** existing call sites (api.py ×2,
app.py ×3, coach.py, inspect_cycles.py) are unaffected by default.
⚠ SUPERSEDES an earlier suggestion in this document's first revision to pass a plain `marks_per_cycle`
int — dispatch requires the stroke identity itself, not a divisor.

**D10 — The harness also scores the four phase boundaries.** The annotations already carry human
`dive_start_s` / `underwater_start_s` / `stroke_start_s` / `finish_s`, and **`detect_phases` and
`detect_initial_phase` have never been scored against them either.** Same fixture, same matching code.
This directly measures how wrong `detect_initial_phase` is off breaststroke — it looks for a dive
surge then a pulldown peak (`metrics.py:272-307`), which is not what freestyle or butterfly does — and
that measurement is the evidence base for any later stroke-aware initial-phase work.

**D11 — Generic mark-type scorer; UW kick anticipated, not built.** User: *"not yet implemented but
underwater kicks will also have a segmentation."* The scorer takes any **named series** of predicted
vs truth times, so adding a `uw_kick` target later is a caller change, not a rewrite. ⚠ Recorded gap:
**the annotation contract has nowhere to store UW kick marks today** — `annotations.PHASE_KEYS` is
four phase times and `stroke_marks_s` is one flat list. A second mark series is a contract + UI +
validation change (`annotations.py`, `api.py`, the annotate page) and is **out of scope here**.

**D12 — Backstroke inherits the freestyle implementation, documented as unvalidated.** Same
alternating-arm structure, same 2-entries-per-cycle physiology, and `MARKS_PER_CYCLE` already treats
them identically. ⚠ It must be **visible** in the code and the write-up that this is inherited and
unmeasured — the silent version of this is exactly what Phase 54's borrowed rating bands produced,
and 58-03 later found nothing on screen said so.

**D13 — Breaststroke: score both wavelet and trough, decide in the behavior plan.** The harness runs
both on the 2 labeled breaststroke sessions and reports both; routing is decided on numbers in 59-03.
⚠ The write-up must state the choice rests on **2 sessions** plus the historical v0.1–v0.4 validation
of the trough method, not on a corpus.

**D14 — Refactor first, behavior second.** 59-02 is a **pure dispatch refactor** — every stroke still
routes to the wavelet, **zero metric movement**, provable by re-running 59-01's harness and getting
identical numbers. 59-03 then changes behavior per stroke, where every moved number is expected and
measured. Rationale the plan must preserve: this codebase has a documented history of silent metric
drift (Phases 51/52/57), and a structural refactor sharing a diff with a behavior change makes an
unexpected movement unattributable.

**D15 — Working artifact: committed module + CLI + tests, plus an uncommitted scratch notebook.**
⚠ **Correcting an error in this document's first revision:** it argued against a notebook on the
grounds that `.gitignore:4` ignores `*.ipynb`. The user corrected that — the gitignore exists to keep
bulk data and private material out of GitHub, **not** to forbid a file type. The real and only
constraint is that a pytest guardrail needs importable functions, which argues for a module *in
addition to*, not *instead of*, a notebook. The notebook is generated for tuning sweeps and plots, is
not maintained, and is not committed.

---

## Amendment — 2026-08-09, before planning 59-03 (AskUserQuestion ×8)

⚠ **A CLAIM MADE EARLIER IN THIS DOCUMENT IS WRONG AND IS CORRECTED HERE.** D7 and the 59-01
SUMMARY both say the ~1.75× cycle-rate fix is "independent of which segmenter wins, so it does not
wait for exploration." It is independent of the *segmenter* — but **not of the swim window**, and
those two errors partially cancel. Measured on the 12 fully-labeled freestyle sessions:

| variant | median auto/human | within ±15% |
|---|---|---|
| today | 1.647 | 0/12 |
| pairing only | **0.761** | 4/12 |
| window only | **2.135** | 0/12 |
| pairing + `ip_end` | 0.907 | 7/12 |
| pairing + `finish` | 0.843 | 6/12 |
| **pairing + both** | **1.010** | **10/12** |

Shipping pairing alone flips the error from +65% to −24%; shipping the window alone makes it
strictly worse. Only both together land on 1.0. **Neither is independently shippable.**
⚠ The 1.010 figure uses the HUMAN window as an ORACLE. It is the ceiling a perfect detector would
reach, not what a real one delivers.

**WHY THE WINDOW IS WRONG — two hypotheses tested and BOTH REFUTED, so this is not a tuning fix:**
- `ip_end` is NOT picking the wrong trough. In **12 of 23** sessions the first trough already IS the
  one nearest the human mark, and the error is still −0.6 to −6.1 s. Several freestyle sessions
  contain exactly ONE qualifying trough in the entire 15 s search and it sits 5–6 s early. The
  trough is the wrong FEATURE, not the wrong instance.
- `swim_end` is NOT threshold-sensitive. Mean |vel| in the over-run region is **0.403 m/s — eight
  times** `_BASELINE_THRESH` (0.05). The swimmer is genuinely still moving fast after the human's
  `finish_s`. This is a SEMANTIC gap, not a sensitivity gap.

**THE REFRAMING (D16).** Both boundaries fail the same way. `detect_phases` asks "where does motion
start and stop"; `detect_initial_phase` asks "where is the first deep trough". The human is marking
**"where does cyclic stroking start and stop."** Post-touch drift is fast but NOT rhythmic;
underwater dolphin kicking is rhythmic but at the wrong frequency. That distinction is what the CWT
ridge already encodes, and 59-01's harness scores a candidate in one command.

**DECISIONS (user, 2026-08-09):**

**D16 — 59-03 bundles cycle pairing AND the swim-window fix.** Splitting them ships an intermediate
state worse than today in one direction or the other, so the phase's usual one-change-per-plan rule
argues *for* bundling here. It makes 59-03 the largest plan in the phase.

**D17 — Full pairing: a cycle becomes TWO segmenter boundaries**, not a divisor applied to the
headline numbers. This is what `annotation_to_overrides` already does with `marks[0::k]`, and it is
the only option that puts auto and annotated on genuinely the same scale — every per-cycle metric
(`mean_dps_m`, `cv_isi`, `mean_coast_fraction`, `mean_impulse_m`) is then computed over a real full
cycle. ⚠ Accepted cost: those metrics change meaning for free/back, a comparability break of the
Phase-57 v95 class. ⚠ Expect `cv_isi` to get NOISIER even as the rate gets correct — the wavelet
over-segments 1.15–1.5×, so "boundary i and i+1 are opposite arms" breaks locally.

**D18 — `finish` is redefined as the end of CYCLIC STROKING**, matching what the annotator marked,
deliberately excluding post-touch drift even though that motion is real. Checking the annotations
against video first was offered and declined (R1 is still unanswered across four checkpoints).

**D19 — The window fix is RESEARCH and 59-03 absorbs it**, opening with a design task that builds
and scores candidates in `tools/` before anything reaches `metrics.py`. Splitting it into its own
research plan was offered and declined; the deciding factor was that the user-visible number only
improves if both halves land together.

**D20 — Stored rows: DRY-RUN REPORT ONLY in 59-03; the DB write is a later plan.** 37 sessions are
affected (36 freestyle + 1 backstroke), all with `velocity_profile` so all backfillable offline.
⚠ **14 of them are ALREADY on the human scale** (annotation-recomputed), so the corpus is ALREADY
mixed — annotating a session today already halves its rate relative to its neighbours. 59-03 does
not introduce that inconsistency, it changes which axis it falls on. Mirrors Phase 52, whose 52-02
backfill is still deliberately unwritten.

**D21 — Gate: median auto/human in 0.85–1.15 AND median |log ratio| strictly better than today's
0.50.** Two-part so an imperfect detector can still pass, while a regression cannot. The ±10% gate
was offered and rejected as unachievable — the oracle itself only reaches 10/12.

**Design consequence for the pairing implementation:** the divisor must NOT be imported from
`annotations.MARKS_PER_CYCLE`. That table is exact physiology for HUMAN marks; on the auto path the
factor 2 works only because the wavelet happens to emit boundaries at roughly arm-entry rate — an
empirical property of *that* segmenter which 59-05 may change. Cleanest expression: the pairing is a
WRAPPER registered in `SEGMENTER_BY_STROKE`, which is exactly what the 59-02 seam was built for.

## Goals

1. **A committed, offline, reproducible answer to "how good is this segmenter?"** — per stroke, per
   session, F1 at a stated tolerance, against human ground truth, covering both cycle boundaries and
   the four phase boundaries. None of this exists today in any form.
2. **Make segmentation per-stroke**, so freestyle, butterfly and breaststroke can each get the method
   that actually fits their markers — decided by measurement, not by argument.
3. **Stop shipping a freestyle stroke rate that is ~1.75× the truth**, with the fix verified against
   ground truth rather than asserted.
4. **Retire the 16-06 pointer** so the living docs describe work that is actually planned.

## Approach sketch (plan boundaries, not a plan)

**59-01 — the harness.** New files only; no product path touched. `autonomous:true` is plausible.
- `segmenter_eval.py` *(new, root)* — pure: named-series matching, precision/recall/F1, tolerance
  sweep, coverage statistic. No I/O, so the pytest regression uses it without network. Mirrors the
  house convention (`metrics.py` / `ratings.py` / `annotations.py` / `roster_metrics.py` are all pure).
- `tools/score_segmenter.py` *(new)* — CLI: reads `velocity_profile` + `sample_rate_hz` + annotations,
  runs wavelet / trough / peak-pick, prints per-stroke tables for cycles **and** phase boundaries.
  Mirrors `tools/schema_contract.py` (module docstring with usage, no import side effects).
- `tests/fixtures/segmenter_truth.json` *(new)* — ~4 sessions, swim-window slices + labels.
- `tests/test_segmenter_eval.py` *(new)* — unit tests for the scorer + a regression pinning F1 against
  the fixture.
- A scratch notebook for sweeps (D15), generated and not committed.
- No new dependencies: numpy / scipy / pywt in `requirements.txt`; `python-dotenv` already in
  `requirements-dev.txt`.

**59-02 — pure dispatch refactor (D9 + D14).** `metrics.py` gains `stroke_type=None` and the registry;
every stroke still routes to the wavelet. **Acceptance is byte-identical harness output.** Touches
`metrics.py`, `api.py:175`, `tests/test_metrics.py`.

**59-03 — per-stroke implementations + the cycle-pairing fix (D7 + D12 + D13).** Behavior changes
here, all measured against 59-01. Touches `metrics.py`, tests, `CLAUDE.md` (comparability note).

Doc reconciliation for D1 rides whichever plan closes the phase.

---

## Open questions for planning

- **Q1 (D4).** Does the user confirm the four proposed exclusions, and are there others they know are
  partial that the coverage heuristic did not catch?
- **Q2 (D6).** Fixture size budget and format — full swim-window traces are ~1.5–3.5 k floats each;
  the plan must decide rounding/trimming and state the repo-size cost. JSON, since the fixture must be
  loadable without pandas in a unit test.
- **Q3 (D10).** Does the harness score the wavelet on the production window (`ip_end:swim_end` from
  `detect_phases`) as well as the annotated window? Recommendation: **both** — the gap between them
  measures how much error belongs to phase detection rather than segmentation, and nobody has ever
  separated the two. D10 makes this nearly free.
- **Q4.** 58-04 (`VideoPane` end-anchor) is still owed. Finish first or run in parallel? **No file
  contention** — 59 is `segmenter_eval.py` + `tools/` + `metrics.py` + tests; 58-04 is web +
  `VideoPane`. 58-05 also recommends dropping 57-03's separate queue page in favour of prev/next on
  the annotate page; unrelated to 59, but it is the other open annotation-throughput thread.

## Risks

- **R1 — the corpus is one swimmer.** Every number describes how well a segmenter tracks *this*
  person's stroke. Tuning to F1 on it may be tuning to them. The write-up must state this at the top,
  not in a footnote, and the fixture must not become a de facto definition of "correct".
- **R2 — labels are timing, not identity.** Per Phase 57, freestyle marks record alternation timing,
  not verified left/right arm identity. The harness scores boundary *placement* only.
- **R3 — the exclusion list is a judgement call embedded in a metric.** Mitigated by printing the
  coverage statistic and scoring excluded sessions for recall anyway, so its effect is visible.
- **R4 — D7 moves numbers users have already seen.** Freestyle stroke rates roughly halve. A
  correction, not a regression, but it will look like a bug to anyone who saw the old value —
  including in any parent report already sent.
- **R5 — `annotations_export.json` is not present in the repo.** The harness must fetch or accept a
  path; it cannot assume the export exists.
- **R6 — D12's inheritance is the Phase-54 failure mode by construction.** Backstroke gets an
  implementation validated on a different stroke. Accepted deliberately; the mitigation is that it is
  documented in code and in the report, not that it is safe.

## Out of scope

- Training any learned model (D2 rationale: n far too small and too homogeneous).
- Changing `segmentation_reliable` (D8).
- An annotation-completeness flag in the contract or UI (D4 — declined for now, still correct later).
- **UW kick segmentation itself, and the second mark series the contract would need** (D11) — the
  scorer is merely built so it does not have to be rewritten when that arrives.
- Splitting `detect_initial_phase` or the metric set per stroke (the "full stroke-aware pipeline"
  option) — D10 *measures* how badly it fits, which is the input to that later phase, but 59 does not
  rewrite it.
- Re-labeling or re-collecting sessions; backstroke data collection.
- Anything Phase 53 owns — thresholds, ratings bands, the attention/SPC engine.
- iOS, and the web annotate page (58-04/05 own those).
- Rewriting historical PLAN/SUMMARY files to remove 16-06 references (D1).

---

*Measurements in this document were produced by throwaway scripts in the session scratchpad and are
NOT committed. 59-01 must re-derive them; treat them as priors to reproduce, not results to cite.*
