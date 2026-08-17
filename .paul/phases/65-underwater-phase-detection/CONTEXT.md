# Phase Context

**Phase:** 65 — Underwater Phase Detection (free / back / fly)
**Discussed:** 2026-08-15 (`/paul:discuss`, 3 rounds)
**Status:** Ready for `/paul:plan`
**Decisions:** 10 (D1–D10) + 3 stated assumptions. **Zero open blocking questions.**

⚠ **PYTHON-FIRST, with a web reporting tail.** Core fix is `metrics.py` phase detection; the
"report it" half touches `annotations.py` seeding + `web/`. Breaststroke and the segmenter (Part 2)
are untouched by construction. The 274-test suite is a guard, and gains cases.

---

## Why now

The user, reviewing an auto-segmented recording, found the segmenter treating the **start** as
strokes. Verbatim, across three messages:

> *"split into two parts, first one segments the phase of stroke. second part segments the cycles
> of stroke. But upon reviewing auto segment result of new recording yesterday, it recognized the
> part of dive as a cycle of stroke, when it should have been recognized as the dive."*

> *(butterfly session "indigo ray")* *"a triangle was placed at the peak velocity of the dive
> segment. It mistakenly latched onto the dolphin kicks as well."*

> *"it persists for other strokes as well … fly, free, back are the same in terms of phases — only
> breaststroke is different having underwater pulldown. So ideally by fixing butterfly we fix the
> other two at the same time."*

**The user's mental model is correct** (verified in code, see table below): the pipeline is two
parts — Part 1 finds phase boundaries (`b_end`, `ip_end`, `swim_end`), Part 2 segments cycles, and
runs **only** on `vel[ip_end:swim_end]` (`metrics.py:801-802,832`). The dive + underwater dolphin
kicks are excluded *by being before `ip_end`*. The bug is that **`ip_end` (the breakout) lands too
early — back inside the underwater kicks** — so Part 2 carves the dive spike and the dolphin kicks
into "cycles," poisoning every per-cycle average.

⚠ **This is USER-REPORTED across free/back/fly, which overrides 59-03's in-sample numbers.** Phase
59-03 claimed `ip_end` median error 3.93 → ~2 s and was tuned on one swimmer, mostly freestyle
(breaststroke n=2, backstroke n=0). A ~2 s slop at the start comfortably swallows a dive + a couple
of kicks. The user has *seen* it fail on all three dolphin-kick strokes; that is the ground truth
this phase answers to.

---

## The precise decomposition (verified, not assumed)

The scope splits into three parts of very different size:

1. **THE BUG — auto breakout misplacement (the hard part).** For free/back/fly, `ip_end` /
   `stroke_start_s` is detected inside the underwater kick phase. Fix it so it lands *past* the
   kicks. Lives in `metrics.py` phase detection.
2. **REPORTING — underwater metrics (cheap, once #1 lands).** No `underwater_duration_s` /
   `underwater_dist_m` exists today. Both are trivial from `[b_end, ip_end]` and the `dist` array
   once `ip_end` is right. New session keys + web display.
3. **ANNOTATE — ~80% ALREADY BUILT.** `annotations.py:44-49` already models `dive → underwater →
   stroke → finish` as a first-class, coach-correctable, exportable phase; `stroke_start_s` **is**
   the breakout. The coach can already drag it and it's already ground truth. What's broken here is
   only that the **auto seed** (`build_seed`, `annotations.py:121-123`) inherits the same wrong
   `initial_phase_end_idx`. Fix #1 fixes the seed for free.

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Scope = the three dolphin-kick strokes (freestyle, backstroke, butterfly).** They share one phase anatomy: dive → underwater dolphin kicks → breakout → surface stroking. Fixing "butterfly" is really fixing this shared case. Routed on `stroke_type` (same seam the segmenter uses). |
| **D2** | **Breaststroke is EXCLUDED and stays byte-identical.** Its underwater is a single pull-out, not repeated kicks — `detect_initial_phase`'s dive+pulldown model is its design case. Breaststroke must route to the unchanged path; a regression test guards it. |
| **D3** | **HARDCODED CONSTRAINT: one lap, no turns.** The swimmer swims exactly ONE length. There is exactly one underwater phase per recording (the start), one surface-stroking window, one finish. No mid-swim/turn underwater handling — the pipeline's single-`[ip_end, swim_end]`-window model is sufficient by construction, and no data contains a turn. |
| **D4** | **The bug is a COARSE region error, not sub-second imprecision.** `ip_end` is landing back among the kicks, so *many* kicks become cycles. The target is "past the underwater kicks," not the exact surfacing frame. ⚠ Phase 58 already ruled the surfacing instant *"not reliably readable"* and removed the separate breakout marker, accepting that the first stroke cycle *contains* the breakout (`annotations.py:22-27`). That tolerance stands — one atypical first cycle is fine; counting the kicks is not. |
| **D5** | **Fix BOTH `ip_end` sources.** `compute_session_metrics` sets `ip_end` from `detect_swim_window` (primary) with `detect_initial_phase`'s first-trough as fallback (`metrics.py:787-793`). Fix only one and the dive leaks through the other. A manual annotation still wins last, unchanged. |
| **D6** | **"Report + annotate it" (user's choice) = fix the auto seed + ADD underwater metrics; the annotation contract already exists.** No new phase boundary is invented — `dive_start_s / underwater_start_s / stroke_start_s / finish_s` already exist. Deliver: (a) correct auto `stroke_start_s`, (b) `underwater_duration_s` + `underwater_dist_m` in the session metrics, (c) web surfaces them. |
| **D7** | **MEASUREMENT FIRST (plan task 1).** Pull real free/back/fly sessions from Supabase (start with "indigo ray"), instrument `compute_session_metrics`, and record for each: did `detect_swim_window` fire or fall back; where `ip_end` landed vs. the true breakout; the ridge-frequency trace + `f_ref`; and which velocity feature actually separates underwater kicks from surface strokes. The detection approach is chosen from this data, not guessed now. |
| **D8** | **Leading detection hypothesis: the underwater kicks LACK an arm-pull surge.** Dolphin kicks are rhythmic and fast but have no arm pull; surface strokes have a distinct high-amplitude arm-pull peak, mean velocity typically DROPS at breakout (a good underwater is faster than the surface), and stroke frequency steps down from the ~2× kick rate. For butterfly specifically, `detect_swim_window` likely fails because the CWT ridge locks onto the 2× dolphin-kick harmonic (`metrics.py:412`), making the kick rate its own `f_ref` — the gate can't reject its own yardstick. To confirm/refute in D7. |
| **D9** | **Comparability break accepted; fix-forward.** free/back/fly stored sessions re-scale (stroke count, stroke rate, per-cycle metrics). DB backfill is a SEPARATE task, per the project's standing pattern (Phases 57 / 59-03 / 59-05 / 61-01). The user explicitly waved off this cost: *"don't worry about it. the whole point is trying to fix the issue."* |
| **D10** | **Web surfaces underwater; mobile is a separate follow.** Underwater metrics land in `metrics_json` (available to both repos). The web report card + annotate page display them. The iOS repo (separately owned) is OUT of this phase's diff, consistent with the myswimcoach/mobile split. |

### Stated assumptions (user did not object; correct in plan if wrong)

- **A1 — underwater phase for metrics = `[dive_start_s (≈ b_end), stroke_start_s (≈ ip_end)]`.** The
  dive spike is the *start* of the underwater phase, not a separately-fixed split. The existing
  `underwater_start_s` (dive-peak) front marker is secondary; the boundary this phase fixes is
  `stroke_start_s` / `ip_end` (the breakout). Plan picks whether duration is measured from
  `dive_start` or `underwater_start`.
- **A2 — Part 2 (the cycle segmenter) is NOT touched.** It is correct on a clean window (that was
  59-05). Only Part 1 (phase detection) changes. `swim_end` / finish is also out — it looked correct
  in the screenshot (trailing marks stop before the dead tail).
- **A3 — the fix accretes a `stroke_type` dependency onto the front end of
  `compute_session_metrics`.** It already receives `stroke_type` for the segmenter; now phase
  detection reads it too. The annotation-recompute path does not pass it, but that path only fires
  when `cycle_bounds` exist (manual), which bypasses auto detection — so it is unaffected. Confirm.

---

## What was verified this session (repo, 2026-08-15)

| Claim | Evidence |
|---|---|
| Two-part flow; Part 2 runs only on `[ip_end, swim_end]` | `metrics.py:801-802` (slice), `:832` (segmenter call) |
| `ip_end` = `detect_swim_window` primary, `detect_initial_phase` fallback, manual wins last | `metrics.py:774-793` |
| `detect_swim_window` settles at a frequency and has a ≥4-cycle plausibility gate that returns `None` | `metrics.py:544-571`, gate at `:561` → caller keeps old boundaries |
| Butterfly ridge locks to the 2× dolphin-kick harmonic (documented weakness) | `metrics.py:412` |
| Fallback `ip_end` = first deep trough after baseline | `detect_initial_phase`, `metrics.py:611,615` |
| Segmenter table IS populated (free/back → paired wavelet, fly/breast → paired learned) | `metrics.py:434-453` |
| ⚠ Two comments still claim the table is EMPTY — stale, contradict CLAUDE.md | `metrics.py:462`, `:823-826` (drive-by doc fix candidate) |
| Underwater already a first-class annotation phase: dive → underwater → stroke → finish | `annotations.py:8-16,44-49` |
| `stroke_start_s` **is** the breakout; the separate breakout marker was removed in Phase 58 as "not reliably readable" | `annotations.py:22-27` |
| The auto SEED inherits the wrong `ip_end` | `build_seed` reads `initial_phase.initial_phase_end_idx`, `annotations.py:121-123` |
| Annotation → metrics override maps `stroke_start_s` → `ip_end_idx` | `annotations.py:191-192` |
| No underwater duration/distance metric exists today | absent from the session keys in `compute_session_metrics` (`metrics.py:905-936`) |

---

## Risks and things this will expose

- **R1 — auto breakout may be genuinely hard from velocity alone.** Phase 58 already found the
  surfacing instant unreadable enough to drop the marker. Mitigants baked into scope: the target is
  *coarse* (D4), the coach can already hand-correct `stroke_start_s`, and every correction feeds the
  ground-truth export — the same annotate → tune loop Phases 47 and 59 ran. A perfect auto detector
  is not the bar; "past the kicks, most of the time, correctable when not" is.
- **R2 — must not regress the free/back sessions `detect_swim_window` currently handles.** The fix
  is stroke-routed and additive; a fixture/regression test on a known-good freestyle session is an
  acceptance criterion.
- **R3 — comparability break (D9)** for stored free/back/fly. Expected, accepted, backfill deferred.
- **R4 — measurement needs Supabase access.** Plan task 1 pulls sessions via `fetch_sessions.py`
  (needs `.env` + `python-dotenv` + network). If unavailable, the user provides raw CSVs. This is a
  hard dependency for D7 → the whole detection design.
- **R5 — butterfly ridge harmonic (D8).** If the fix is "make `detect_swim_window` robust for fly,"
  it must handle the ridge tracking 2× kicks. If instead a dedicated arm-pull-surge breakout
  detector is cleaner, it may supersede `detect_swim_window`'s `ip_end` for these strokes entirely —
  an architecture call for plan, informed by D7.

---

## For `/paul:plan` — open design calls (resolve with D7 data)

1. **What detects the breakout for free/back/fly?** Two shapes: (a) *repair* `detect_swim_window`'s
   frequency logic so the fly ridge harmonic stops poisoning `f_ref`; or (b) a *new* dedicated
   underwater→surface detector keyed on the arm-pull surge (what the kicks lack, D8), which replaces
   the `ip_end` source for these strokes. Pick after measuring.
2. **Underwater metric set.** `underwater_duration_s` + `underwater_dist_m` are in. Kick count is a
   stretch (needs peak-counting the underwater segment) — include or defer?
3. **Where underwater duration is measured from** — `dive_start` vs `underwater_start` (A1).

---

## Files likely in scope

| File | Change |
|---|---|
| `metrics.py` | Stroke-aware breakout detection for free/back/fly — fix `detect_swim_window` and/or a new detector, at the `ip_end` resolution `:774-793`; add `underwater_duration_s` + `underwater_dist_m` to the session dict. Breaststroke path unchanged. |
| `annotations.py` | Verify `build_seed` now seeds `stroke_start_s` past the kicks (inherits the metrics fix); pass underwater metrics through if the annotate page displays them. |
| `api.py` | Likely none — annotation endpoints already return `metrics_json`; underwater metrics ride along. Confirm. |
| `web/app/app/sessions/[id]/page.js` + annotate page | Display `underwater_duration_s` / `underwater_dist_m`; phase markers already render. |
| `tests/test_metrics.py`, `tests/test_annotations.py` | Breakout detection on free/back/fly; underwater metrics; **breaststroke + freestyle regression guards**; seed correctness. |

Untouched: the Part-2 segmenter, breaststroke detection, `swim_end`/finish, `supabase/`, the mobile repo.

---

## Carried out (recorded, not scoped here)

- Mid-swim turns / multi-length underwater phases (D3 — no data, no pipeline seam).
- Mobile display of underwater metrics (D10 — separate repo).
- DB backfill of re-scaled free/back/fly sessions (D9 — separate task).
- Sub-second breakout precision (D4 — Phase 58 already ruled it not readable; not the goal).
- Kick count metric, if design call #2 defers it.
- The stale "table is EMPTY" comments at `metrics.py:462,823-826` — drive-by fix if the plan touches that region, not a reason to.

---

## Success criteria

- [ ] For free/back/fly, auto `ip_end` / `stroke_start_s` lands **past** the underwater dolphin-kick
      phase — the dive spike and the kicks are no longer segmented as cycles. Verified on "indigo ray"
      plus ≥1 real freestyle and ≥1 real backstroke session.
- [ ] Breaststroke auto detection is **byte-identical** to today (routing + regression test).
- [ ] The free/back sessions `detect_swim_window` handles today do **not** regress.
- [ ] Session metrics gain `underwater_duration_s` + `underwater_dist_m` for the three strokes.
- [ ] `build_seed` opens the annotate page with `stroke_start_s` past the kicks (auto seed fixed).
- [ ] Web report card / annotate page display the underwater phase duration + distance.
- [ ] Python suite green, with new tests for detection, underwater metrics, and the regression guards.
- [ ] Plan task 1 (D7) is documented: which source caused the early `ip_end`, and the chosen
      discriminating signal.
