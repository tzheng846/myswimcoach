# Phase Context

**Phase:** 57 — Annotation Workflow (annotate-tool v2)
**Generated:** 2026-08-05
**Status:** Ready for planning
**Predecessor:** Phase 47 (Trial Annotation) — shipped the contract + GUI + recompute this phase revises

---

## Why now

**19 real sessions were collected 2026-08-05:** 10 freestyle, 4 breaststroke, 4 butterfly,
1 backstroke. They are the first trustworthy corpus the project has had — every CSV in `raw/`
predates the 2026-06-22 encoder-integrity fixes and the user trusts 2–3 of 43.

Annotating them is the immediate next action, and it is the blocking input to two open tracks:

- **Phase 53 Track A4** — annotate all sessions → `segmentation_reliable=True` + recomputed
  metrics → A5 saturation/repeatability analysis, which is the GO/NO-GO for the whole attention
  engine.
- **Phase 16-06** — the `GET /annotations/export` ground truth for wavelet segmenter tuning.

The Phase-47 tool works but was built and verified against a handful of sessions. Doing 19 in a
sitting exposes throughput, precision and semantic gaps that did not matter at n=1.

---

## Repo-verified starting conditions

These were checked against the code, not assumed. Several contradict the framing of the request.

1. **Trailing trim already works — silently.** `finish_s` → `swim_end_idx`
   (`annotations.py:158` → `metrics.py:439`) already truncates the analysis window. In the user's
   screenshot Finish=21.42 s, so the 21→39 s tail is already excluded from the recompute. What is
   missing is *feedback*, not mechanism: the chart still renders all 38.98 s (swim occupies half the
   width at ~18 px/s) and nothing states that Finish discards everything after it.

2. **Non-overlap is already structurally guaranteed — and completely unstated.**
   `validate_annotation` enforces non-decreasing marker order (`annotations.py:222-229`), so the five
   markers *are* contiguous half-open intervals by construction: dive=[dive_start, uw_start),
   uw=[uw_start, breakout_start), etc. The UI shows a bare number ("Dive 1.31 s") that reads as a
   duration, never as a start time, and never shows the resulting span.

3. **A null marker silently stretches its neighbour.** There is no distinction between "this phase
   did not happen" and "I have not marked it yet."

4. **Only 3 of the 5 markers reach the metrics.** `annotation_to_overrides` maps dive_start →
   `baseline_end_idx`, stroke_start → `ip_end_idx`, finish → `swim_end_idx`. `underwater_start_s`
   and `breakout_start_s` feed nothing, and `initial_phase` (dive_duration, pulldown) is carried over
   from the *auto* result unchanged at `api.py:896`. Two of the five clicks move no number.

5. **Stroke marks are not constrained to the swim window.** `validate_annotation` deliberately does
   not check (`annotations.py:190-192`) and `annotation_to_overrides` turns every consecutive pair
   into a cycle regardless — a stray mark in the dead tail becomes a garbage cycle feeding
   `stroke_rate_spm` and `mean_dps_m`. This is the "parts must not overlap" complaint, in the data.

6. **`stroke_start_s` and the first stroke mark can disagree.** Seeded to coincide, then drift
   independently once edited. Nothing relinks them.

7. **`v95` is computed over the FULL trace** (`metrics.py:431`), including the dead tail, then drives
   the per-cycle dead-spot threshold and (indirectly) coast fraction. A long trailing tail biases it
   down on every session, annotated or not.

8. **One entry point, no queue.** The only route in is the report-card link
   (`web/app/app/sessions/[id]/page.js:188`). No annotated/not indicator, no prev/next, no undo, no
   drag-to-move, no keyboard nudge.

9. **Reaction time is anchored to the cue — but offset by an unmeasured, variable 170–400 ms.**
   `useStartSequence.run()` resolves *at the blare*, then `startRecording()` writes BLE START
   (`RecordScreen.js:454`), so t=0 is cue-anchored. But two latencies sit between blare and first
   buffered sample: the `await writeCmd('START')` BLE round trip, and the firmware's warmup discard
   of **150–300 ms, variable** — it exits on a stability condition, not a fixed delay
   (`ESP_32_V5.ino:383-392`; the comment at :144 names the race-start blare explicitly). Block
   reaction time is ~0.6–0.8 s, so `dive_start_s` understates it by 25–50%, and by a different amount
   each trial. **No firmware change can retroactively fix the 19 sessions already collected.**

---

## Goals

1. **Make the swim window visible and authoritative.** The annotated window is what gets analyzed —
   the chart should show it, and nothing outside it should be able to contaminate a metric.
2. **Make the phase model explicit.** Every marker states that it is a *start*, what interval it
   opens, what interval it closes, and whether it affects any number.
3. **Produce uncontaminated ground truth.** The annotation must not be anchored by the segmenter it
   exists to evaluate.
4. **Make 19 sessions (~500 marks) tractable in one sitting.**

---

## Decisions (user, 2026-08-05, AskUserQuestion ×4 rounds)

### D1 — Trailing trim: view + hard boundary
Chart auto-fits the x-axis to the annotated swim window, with a toggle back to the full trace. The
window becomes **authoritative**: stroke marks outside `[stroke_start, finish]` are rejected, and
`v95` is computed on the swim window. Stored profiles are **never** truncated — no destructive edit,
fully reversible.

### D2 — `v95` fix applies to the whole pipeline
Not scoped to the annotation path. Two definitions of `v95` in one codebase is exactly the split that
produced the Phase-52 drift. **Accepted consequence:** `dead_spot_s` and `coast_fraction` shift on
every session computed from here on, so old and new numbers stop being comparable — needs a note in
CLAUDE.md and a test-suite re-baseline.

### D3 — Stroke marks: one mark per arm entry, everywhere
Cycles are derived by **pairing**. The pairing factor is stroke-dependent and follows from physiology,
not from a user choice:

| Stroke | Arms | Marks per cycle |
|---|---|---|
| Freestyle, backstroke | alternating | **2** |
| Butterfly, breaststroke | simultaneous | **1** |

`stroke_rate_spm` therefore stays cycles/min for all four strokes, while the raw marks preserve
alternation timing — the training label the future HMM arm-side work would need.

**Explicitly reconfirmed** after the user learned most sessions have no video (see R1). User chose
per-arm-entry over both the safer alternatives.

### D4 — Reaction time: record it, label it a lower bound, ship no metric
The front is **never** auto-trimmed. `dive_start_s` is saved and displayed with an explicit caption
that it excludes an unmeasured 170–400 ms of BLE + warmup latency. **No `reaction_time_s` metric
ships** — nothing downstream may read it as calibrated. The user confirmed the race-start sequence
was enabled on all 19 recordings, so every t=0 in this batch is cue-anchored and the caption can be
unconditional.

### D5 — UW kick + Breakout stay ground-truth-only, and the UI says so
No new metric semantics inside the recompute path. Those two markers feed the 16-06 export and
nothing else; the UI labels them plainly so the coach knows two of five clicks move no number.

### D6 — No preloaded marks. The editor starts blank.
User: *"in annotation, it should not have any preloaded."* Methodologically correct and stronger than
the option offered — seeding ground truth from the segmenter being evaluated is circular, and it
anchors the annotator toward the very errors 16-06 exists to find. Supersedes the Phase-47 auto-seed
behavior (`page.js:67`, `const src = annRes.annotation ?? annRes.seed`).

### D7 — No auto-assist
No peak-picker, no even-spacing fill. Follows from D6 and from not adding a second detection method to
a codebase already shipping one at placeholder quality.

### D8 — Batch throughput is in scope
An annotation queue listing sessions with an annotated/not indicator, plus prev/next inside the
annotate page so there is no round trip through the session list.

---

## Risks the user accepted knowingly

**R1 — ~500 hand-placed marks on an ambiguous signal.** D3 + D6 + D7 + no video compound: roughly 40
marks per freestyle session, placed from the velocity trace alone, where each cycle shows ~2 peaks
that cannot be attributed to a specific arm without footage. Offered per-session convention and
per-cycle-only alternatives; user chose per-arm-entry everywhere. **Mitigation the plan must carry:**
the marks record *alternation timing*, not verified arm identity, and the UI must say that rather than
implying verified ground truth. Precision affordances (zoom, undo, drag-to-move, keyboard nudge,
live marks→cycles readout) become load-bearing, not polish.

**R2 — the v95 re-baseline breaks comparability** with every previously computed session (D2).

---

## Approach notes

- **Contract changes** live in `annotations.py` (pure): reject out-of-window marks, express the
  arm-entry→cycle pairing in `annotation_to_overrides`, relink `stroke_start_s` to the first mark.
- **Pipeline change** is one line of intent in `metrics.py` (v95 over `[b_end, swim_end]`) plus test
  re-baselining — the widest-blast-radius edit in the phase; keep it isolated and separately verifiable.
- **Web** carries the bulk: window-fit chart + full-trace toggle, explicit interval display, blank
  start, undo/drag/nudge, queue page + prev/next.
- **`api.py`** keeps returning `seed` in `GET /annotations` (removing the field is a contract change
  benefiting nothing); the page simply stops applying it. Worth a plan-time sanity check that no other
  consumer reads it.
- **No new column.** The pairing factor is derived from `sessions.stroke_type`, not stored — no
  patch_10, no user-applied SQL. **Assumption to validate at plan time:** `stroke_type` is correct on
  all 19 rows. It is *not patchable* (CLAUDE.md: "stroke_type is NOT patchable"), so a wrong value is
  unfixable through the API — the UI must show the derived pairing prominently ("Freestyle → 2 marks
  per cycle · 18 marks → 9 cycles") so a wrong `stroke_type` is immediately visible rather than
  silently halving a stroke rate.

---

## Out of scope

- Firmware change to report the actual warmup duration in META (would make reaction time real, but
  cannot help the 19 sessions already collected).
- Any `reaction_time_s` metric, calibration constant, or schema column for it.
- Recomputing `initial_phase` from human dive/UW/breakout marks (D5).
- iOS — annotation is web-only.
- Destructive trimming of `velocity_profile` / `distance_profile` (D1).
- Left/right *arm identity* labelling. Alternation is captured; absolute side is not, and no consumer
  exists for it.
- Multi-length / turn support. The phase model remains a single ordered pass.

---

## Open questions for planning

1. Does anything besides the annotate page read `seed` from `GET /annotations`? (grep at plan time)
2. How many stored sessions already carry annotation-recomputed metrics that the v95 change would
   make inconsistent with their siblings? Related to the unresolved Phase 52-02 count.
3. Should the queue page live at `/app/annotate` (index) or as a filter on the existing sessions list?
4. Rule for a dangling odd final arm entry in free/back — **proposed:** drop it from `cycle_bounds`
   (a half-cycle would skew `stroke_rate_spm`) but keep it in `stroke_marks_s` so the ground truth
   stays complete. Needs confirmation.

---

## Concurrency note

Two PAUL sessions have been observed writing this repo (STATE.md, 2026-08-05). Commit `.paul/`
between sessions so conflicts surface as merge conflicts rather than silent last-write-wins.
