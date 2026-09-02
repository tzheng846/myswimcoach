---
phase: 86-session-clock-accuracy
plan: 04
subsystem: testing
tags: [instrumentation, signal-processing, clock-sync, numpy, ffmpeg]

requires:
  - phase: 86-session-clock-accuracy
    provides: "86-03's VOID device run — 8 raw CSVs, 8 clips, 42 audio onsets — plus the diagnosis that the encoder tap detector over-triggers"
provides:
  - "A repaired tap-test instrument: strikes FOUND on decimated |velocity|, TIMED on raw |diff(counts)|"
  - "Two encoder-side integrity checks (interval-pattern, contention) that never read a residual"
  - "Three session health fields: encoder_overtrigger_ratio, interval_pattern_max_delta_s, vel_to_raw_offset_ms"
  - "A --measure-domain mode that reproduces the whole derivation from the corpus"
  - "A ring-down fixture that reproduces 86-03's defect and fails loudly if the repair regresses"
  - "TAP-TEST-PROTOCOL.md section 10 — the confirmatory run registered before it happens, bars unchanged"
affects: [86-05, session-clock-accuracy, video-overlay-sync]

tech-stack:
  added: []
  patterns:
    - "Detection domain / timing domain split — find where the signal is clean, time where it is fast"
    - "Clock-offset-free integrity checks — differences of gaps, so a constant offset cancels"
    - "Derivation rules pre-registered above the constants they produce, with the measurement committed first"

key-files:
  created: []
  modified:
    - scratch/tap_test.py
    - .paul/phases/86-session-clock-accuracy/TAP-TEST-PROTOCOL.md

key-decisions:
  - "Dropped the previous draft's pre-registration claim as false — the sweep had already been run on this corpus"
  - "Rejected coupling the audio onset count into the encoder detector; the fix went into the operator protocol instead"
  - "Moved the interval-pattern check from session-level (as planned) to a third pass over scatter-surviving taps"
  - "Applied AC-5's 2 ms bar to the encoder time against the fixture's known strike, not to a frame-quantised residual"

patterns-established:
  - "A repair is only trusted once a fixture reproduces the ORIGINAL defect and asserts both halves"
  - "In-sample numbers are labelled in-sample at every point of use, including STATE.md"

duration: 28min
started: 2026-09-02T00:15:37-07:00
completed: 2026-09-02T00:52:00-07:00
---

# Phase 86 Plan 04: Repair the tap-test instrument — Summary

**Strikes are now found on decimated `|velocity|` and timed on raw `|diff(counts)|`; 86-03's
over-triggering is gone (5.6 → 1.0) and with it every laundered tap (10 → 0), at the cost of an
acceptance rate that fell 83.3% → 66.7%. B1 REMAINS UNMEASURED.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~28 min (plan rewrite → APPLY complete) |
| Started | 2026-09-02T00:15:37-07:00 |
| Completed | 2026-09-02T00:52:00-07:00 |
| Tasks | 3 of 3 completed |
| Files modified | 2 (`scratch/tap_test.py`, `TAP-TEST-PROTOCOL.md`) |
| Device time spent | **0** — no pool, no operator, no EAS build |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: detection domain measured, not asserted | **Pass** | `--measure-domain scratch/taptest` prints all four blocks, three rule outputs, both assertions OK; read-only |
| AC-2: constants come from the rules | **Pass** | `TAP_FRAC=0.20` (inside 8 of 8 plateaus), `RAW_REFINE_WINDOW_S=0.25` (4 × 55.7 ms), `PAIR_TOL_S=0.05` (2 × 21.7 ms); every comment carries the measurement, n, derivation and the IN-SAMPLE flag |
| AC-3: found on velocity, timed on raw | **Pass** | `find_tap_candidates` → `refine_on_raw`; no reported tap time reads the decimated base; `vel_to_raw_offset_ms` recorded per tap |
| AC-4: mispair caught on encoder evidence, never on the residual | **Pass** (deviated, see below) | interval-pattern + contention checks live; grep confirms no rejection rule reads `residual_*` or any median of one |
| AC-5: 86-03's defect reproduced and pinned | **Pass** (amended, see below) | Ring-down fixture, zero injected error: 86-03 accepts 6 taps carrying over 150 ms (worst +190 ms); 86-04 pairs that tap to the real strike within **0.46 ms** |
| AC-6: nothing that already worked was broken | **Pass** | self-test 5/5 offsets within 2.00 ms, rejection path 11/1, no container-offset leak; `--validate-timebase raw/` **39/39 at 0.000000 ms**; pytest **566 passed** |
| AC-7: void data yields a diagnosis, never a result | **Pass** | Every re-run figure labelled IN-SAMPLE and stated as an upper bound; no recomputed end-anchored residual appears in any verdict section; B1 reads *unmeasured* in STATE.md, PROJECT.md and the protocol |
| AC-8: confirmatory run registered before it happens | **Pass** | `git diff` on the protocol is **111 insertions, 0 deletions** — pure addition; new `## 10.` plus a dated `## Amendments` entry |

**8 of 8.**

## The headline: the repair worked and acceptance still fell

|  | 86-03 (void run) | 86-04 (repaired, in-sample) |
|---|---|---|
| Acceptance | 35/42 = **83.3%** | 28/42 = **66.7%** |
| Accepted taps over 50 ms from their session median | **10** | **0** |
| Worst deviation from session median | **315.1 ms** | **33.7 ms** |
| Worst `encoder_overtrigger_ratio` | **5.6** (28 events / 5 onsets) | **1.00** |
| `readout_spread_frames` at or under 1.2 | all 8 | all 8 (improved on 5) |

**This is the correct trade, and it was written down before the re-run.** 86-03's failure mode was
*confident wrong answers*: over-triggering let an audio onset select the wrong ring-down crossing,
and because AC-4 compared audio against frames — two readouts of the same video — the encoder
mispair left both in agreement and was stamped ACCEPTED carrying 180–320 ms. What replaced it is
visible rejections.

**B3 still fails on this corpus (66.7% below the 90% bar).** That is expected, pre-stated
(`<measurement_honesty>` predicted an ~81–83% ceiling), and **not fixable here** — the data was
collected through the broken instrument, so no amount of re-analysis produces a passing run.

### Per-session (all IN-SAMPLE, upper bound, not an estimate)

| session | accepted | onsets | overtrigger | interval delta ms | spread | contended | max scatter ms |
|---|---|---|---|---|---|---|---|
| Tap_test_1 | 1 | 5 | 0.40 | — | — | 0 | 0.0 |
| Tap_test_2 | 2 | 5 | 0.60 | 5.4 | 0.03 | 0 | 2.2 |
| Tap_test_3 | 4 | 5 | 0.80 | 29.9 | 0.50 | 0 | 33.7 |
| Tap_test_4 | 3 | 6 | 0.83 | 38.4 | 0.50 | 0 | 22.5 |
| Tap_test_5 | 4 | 5 | 1.00 | 26.4 | 0.83 | 0 | 14.9 |
| Tap_test_6 | 5 | 5 | 1.00 | 11.1 | 0.81 | 0 | 21.5 |
| Tap_test_7 | 5 | 5 | 1.00 | 8.1 | 1.11 | 0 | 19.2 |
| Tap_test_8 | 4 | 6 | 0.83 | 15.3 | 0.57 | 1 | 13.4 |

Rejections by class — **7 unmatched** (no encoder tap within `MATCH_WINDOW_S` 1.4 s), **5 readout
disagreement** (−102.6, −87.1, −76.3, −74.4, +322.8 ms; fewer than 86-03's 7), **2 contention**.

**The interval-pattern check never fired.** Worst observed 38.4 ms against a 50 ms tolerance. It
cost nothing on this corpus and stands as a guard for 86-05.

### The velocity-to-raw lag, which is why the domains are split

Pooled **+16.3 ms (n = 34, SD 22.6, range −10.9 to +55.7)**; per-session means **−5.0, −2.8, +7.6,
+10.5, +17.5, +25.2, +35.0, +39.4 ms**. Against a 33 ms bar, with a spread that varies session to
session and therefore does **not** cancel as a constant, timing on velocity would have manufactured
exactly the clock error the test exists to detect. It is now recorded per tap as
`vel_to_raw_offset_ms`, and section 10 makes it a **void** condition if it ever collapses toward zero.

## AC-7's required verdict on the soft-strike explanation: SUPPORTED FOR 4 OF 7, REFUTED FOR 3

The plan required the unmatched-onset amplitude evidence to either support the soft-strike
explanation or withdraw it. It does **both**, and the split is the useful part:

| onset | amp / session peak | reading |
|---|---|---|
| Tap_test_1 @ 1.229 s | **19.0%** | soft strike, real — peak-relative threshold dropped it |
| Tap_test_1 @ 14.314 s | **7.2%** | soft strike, real |
| Tap_test_3 @ 0.688 s | **9.0%** | soft strike, real |
| Tap_test_4 @ 11.727 s | **16.7%** | soft strike, real |
| Tap_test_1 @ 10.838 s | 1.9% | noise floor — **not a strike** |
| Tap_test_2 @ 1.861 s | 1.7% | noise floor — **not a strike** |
| Tap_test_2 @ 9.891 s | 3.3% | noise floor — **not a strike** |

So 4 unmatched onsets are genuine strikes the velocity threshold missed (protocol fix #3: strike
with consistent force), and **3 are onsets where nothing happened on the wheel at all** — the phone
heard something that was not a strike. The audio onset count is therefore *not* clean ground truth,
which is a finding the plan did not anticipate (see Deferred, below).

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Task 1: measure the detection domain | `2043026` | apply | +366 lines: `--measure-domain`, four measurement blocks, three rule outputs. **No constant touched.** |
| Task 2: find on velocity, time on raw | `b40bcaf` | apply | +306/−11: three constants, `find_tap_candidates`, `refine_on_raw`, interval + contention checks, health fields, ring-down fixture |
| Task 3: re-analyse, register 86-05 | `78711b6` | apply | +111/−0 on the protocol: dated amendment + `## 10. Confirmatory run (86-05)` |

Plan rewrite: `527f7f0` · APPLY state: `b149f34`

**Task 1 was committed alone, before any constant moved.** That ordering is not recoverable after
the fact and is the only thing that makes the derivation auditable — the measurement provably
predates the constants it produced.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `scratch/tap_test.py` | Modified, 1061 → **1722** lines | The instrument: domain measurement, split detection/timing, encoder-side checks, health fields, ring-down fixture |
| `.paul/phases/86-session-clock-accuracy/TAP-TEST-PROTOCOL.md` | Modified, +111/−0 → **375** lines | Dated amendment with the derivations and in-sample caveat; new `## 10.` registering 86-05 |

Regenerated (untracked): 8 JSON sidecars in `scratch/taptest/`. The 8 raw CSVs and clips were not
touched. The `scratch/_tap_domain*.py` probes stay untracked — `--measure-domain` supersedes them
inside the instrument, where anyone with the corpus can reproduce the numbers.

## Decisions Made

| Decision | Rationale | Impact |
|---|---|---|
| **Replace the pre-registration claim with `<pre_registration_status>`** | The previous draft claimed the constant was pre-registered. The sweep had already been run on this corpus, so the claim was **false** — and asserting it anyway is precisely the failure Phase 86 exists to prevent. | The constants are now honestly labelled in-sample everywhere they appear. What *is* pre-registered is narrower and still load-bearing: each constant must equal what its stated rule produces, and all three froze before 86-05's data exists. |
| **Do not let the audio onset count hint the encoder detector** | It would raise acceptance by coupling the two sensors the test keeps independent. | The fix went into the operator protocol (section 10, rows 2–4). The honest cost of under-detection is *n*, which is cheap to buy on deck. |
| **Keep interval-pattern matching as a verification, not a pairing mechanism** | `MATCH_WINDOW_S` at 1.4 s against ~3 s spacing already turns a missed encoder tap into an honest rejection. Adding a second pairing mechanism would be complexity with no gain. | Simpler; `MATCH_WINDOW_S` untouched, now load-bearing in the right direction. |
| **`baseline_counts_s=20.0` in the ring-down fixture** | The corpus is a wheel on a desk, not a wheel spinning at 200 counts/s. | Also the more faithful model — see Auto-fixed #2. |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 3 | All essential; each would have read as success |
| AC amended | 1 | AC-5's bar relocated to an equivalent, reachable target |
| Scope additions | 0 | — |
| Deferred | 2 | Routed to section 10's operator protocol, not to a second round of tuning |

### Auto-fixed

**1. Plan defect — the interval check ran too early and rejected session-wide.**
- **Found during:** Task 2 verification. The standing AC-4 desync gate regressed **11/1 → 0/12**.
- **Issue:** The plan (Task 2 step 4, and AC-4 as written) specified a *session-level* rejection.
  The check compares encoder gaps against **audio** gaps, so a single shifted audio onset condemned
  all 12 taps — the exact opposite of the fine-grained rejection AC-4 wanted.
- **Fix:** Moved it to a **PASS 3**, running over taps the scatter check has already left standing.
  The scatter check is precisely what identifies an untrustworthy audio readout, so the ordering is
  load-bearing.
- **Verification:** Desync gate back to 11/1; the check never fires spuriously on the corpus.
- **Commit:** `b40bcaf`

**2. The ring-down fixture's baseline rotation defeated the repair for an unrelated reason.**
- **Found during:** Task 2, AC-5. Repaired detector returned 22 taps for 12 strikes.
- **Issue:** At 200 counts/s the fixture's baseline is **8.5% of peak `|velocity|`**, so a planted
  ring fraction *f* arrived as roughly 0.085 + 0.85·*f*. A 0.15 ring landed at **0.208**, over the
  0.20 cut. Probed empirically rather than theorised.
- **Fix:** `baseline_counts_s=20.0`.
- **Commit:** `b40bcaf`

**3. `|velocity|` of an overshooting impulse has two lobes.**
- **Found during:** Task 2, after fix #2 — still 22 taps, but only **12 distinct**. The clean
  fixture showed the same shape (25 taps / 12 distinct).
- **Issue:** One strike raised two candidates that refined to the **identical raw sample**, inflating
  `encoder_overtrigger_ratio` — the very field meant to expose over-triggering.
- **Fix:** Exact-equality dedup in `detect_taps`, keeping the **first** candidate's offset. Not the
  smallest: the lobes straddle the strike, so taking the smaller would bias the reported
  velocity-to-raw lag toward zero — and section 10 makes that lag collapsing toward zero a **void**
  condition.
- **Commit:** `b40bcaf`

### AC amended

**AC-5's 2 ms residual bar is unreachable and was relocated.** A single tap carries uniform
±half-frame (16.7 ms at 30 fps) quantisation *by construction* — the same mistake 86-03 made and
corrected in its own AC-1. The 2 ms bar was applied to the **encoder time against the fixture's
known strike** instead: exact, no frame quantisation, and it tests what the AC actually cares about
(did the repaired detector pick the strike or a ring-down crossing?). Result: **0.46 ms**. The
frame-quantised residual (−9.59 ms) is *reported, not asserted*. Recorded as a dated amendment in
the protocol.

## Deferred — 2 findings, deliberately not acted on

Both are causes for the operator protocol to fix, not licence for a second round of tuning on a
corpus that is already spent. The plan is explicit: *"a second failed repair on the same corpus means
the discriminator is wrong, which is a new plan, not a third round of tuning."*

**1. Under-detection starves the rejection rule that depends on it — a feedback loop.**
`av_offset` is only estimated with **3 or more paired taps**; below that it silently falls back to
0.0 and the scatter check is miscentred. **Tap_test_1 paired only 2** (`av_offset_estimated: False`),
so its single disagreement rejection is not trustworthy. Each failure mode makes the other worse. →
Registered as section 10 operator change #2 (8 or more strikes per session), with the `av_offset`
reason stated.

**2. The audio onset count is not clean ground truth either.**
Tap_test_8's first two onsets are **0.52 s apart** against a population of 2.54–4.42 s, sitting on
the audio detector's own 0.5 s refractory edge. Reported against
`AUDIO_RETRIGGER_LIMIT_S = 2 × REFRACTORY_S` — twice the detector's stated resolution limit, not a
tuned number — and it **flags, never drops**. That one false onset produced **both** contention
rejections, and it is also why the `RAW_REFINE_WINDOW_S` assertion cleared by 0.01 s instead of
1.02 s. → Registered as section 10 operator change #4 (3 s or more between strikes, now load-bearing
twice).

## Verification Results

```
--measure-domain scratch/taptest   all 4 blocks, 3 rule outputs, both assertions OK, exit 0
--self-test                        PASS  5 offsets within 2.00 ms · rejection 11/1 ·
                                         no container-offset leak · ring-down reproduced & repaired
--validate-timebase raw/           39/39 clean files at 0.000000 ms / 0.000000 mm
pytest tests/ (conda interpreter)  566 passed, 1 warning in 90.12s
protocol git diff                  111 insertions, 0 deletions — append-only
boundary grep                      no frozen constant assignment changed; find_taps intact;
                                   no rejection rule reads a residual
```

Skill audit: no `.paul/SPECIAL-FLOWS.md` in this repo — not applicable.

## Next Phase Readiness

**Ready:**
- The instrument is repaired, self-testing, and its defect is pinned by a fixture that fails loudly
  on regression.
- **86-05 is fully specified.** `## 10. Confirmatory run (86-05)` carries B1–B4 unchanged in value
  and all five operator changes. An operator can run it without further design.

**Concerns:**
- Every number in this SUMMARY computed on the void corpus is **IN-SAMPLE** and an **upper bound**.
  The repaired detector was derived from this data.
- The three constants are tuned, not pre-registered. Their pre-registration is against **86-05**,
  whose data does not exist yet.
- `PAIR_TOL_S` rests on **3 of 8 sessions and 12 intervals** — a thin basis, stated as such at every
  point of use.

**Blockers for 86-05:**
- **`videoStartPhoneMs` is not persisted.** A mobile change plus an EAS build. Until it lands, **B2
  and B4 are unmeasurable**. This is the only gate that costs a build.
- A pool session with 8 or more consistent-force strikes per rep.

---

## PHASE 86 IS NOT COMPLETE — THE PLAN COUNT NOW READS 4 OF 4 AND IS WRONG

With this SUMMARY, Phase 86 has **4 PLANs and 4 SUMMARYs**. That equality is the trigger for the
phase-transition heuristic, and **it must not fire here** — it is the same plan-count trap that
wrongly called 83-01, 83-02 and 88-04 done.

**Phase 86 exists to replace estimates with measurements.** It has replaced three and left its
headline one unmeasured:

| | Status |
|---|---|
| **B1 — end-anchored residual, what a coach actually sees** | 🔴 **UNMEASURED** |
| B2, B4 — start-anchored comparison | 🔴 Unmeasurable until `videoStartPhoneMs` persists |
| Camera warm-up | 🔴 Unmeasured and doubtful |
| `rtt/2` | 🟡 Still an estimate |

86-04 spent no device time and produced **no B1 measurement by construction**. Closing the phase on
counts would bank a void run and an in-sample instrument diagnostic as a finished measurement.
**86-05 is owed. No phase commit, no transition.**

---
*Phase: 86-session-clock-accuracy, Plan: 04*
*Completed: 2026-09-02*
