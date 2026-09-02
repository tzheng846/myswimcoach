# Tap Test Protocol — Phase 86-03

**Pre-registered 2026-09-01, before any device data exists.** Committed ahead of the run so the bars
cannot move to meet the data. Amending this file after data collection begins is allowed only as an
explicit, dated, and justified entry in `## Amendments` at the bottom — never as a silent edit.

Instrument: [`scratch/tap_test.py`](../../../scratch/tap_test.py). Its self-test and time-base
validation both pass as of this commit; see `## Instrument status`.

---

## 1. What is being measured

The product contains **two different video-to-trace mappings**, and 86-03's planning found they are
not interchangeable:

| | Formula | Who uses it | Moved by 86-02? |
|---|---|---|---|
| **End-anchored** | `deviceDuration − videoDuration` | the shipped iOS overlay and the web annotate page, via `sessions.video_origin_s` | **No** — `sessionStartPhoneMs` cancels |
| **Start-anchored** | `(videoStartPhoneMs − sessionStartUtcMs) / 1000` | an external camera, which has no end-anchor of its own | **Yes** |

Session time of a video event at video time `v` is `v + origin`, so for each strike:

```
residual = (t_video + origin) − t_encoder
```

**Positive residual = the video readout lands later in session time than the encoder's**, i.e. the
origin is too large.

Three deliverables, in priority order:

1. **The end-anchored residual** — the number a coach actually sees, never once validated against
   ground truth. This is the primary target and it is independent of everything 86-02 did.
2. **Camera warm-up** = `end_anchored_origin − start_anchored_origin`, positive when the first frame
   arrives that long after the `recordAsync()` call. Currently a "~2 s" guess in a code comment
   ([VideoOverlayScreen.js:52](../../../../swimnetics-mobile/src/screens/VideoOverlayScreen.js:52)).
   This would be its first measurement.
3. **A bound on `rtt/2`** — a bound, not an isolation. See §5 B4.

---

## 2. What you need

- An **EAS build carrying 86-02**. This is the only gate. It is the same build 86-02's AC-7 and
  Phase 84's owed device-verify batch are waiting on.
- The encoder wheel, powered and BLE-connected.
- Something hard to strike it with.

**No pool. No swimmer. No water.** The wheel on a desk is sufficient, and this is the single biggest
reason the test is cheap to run. Do not defer it until poolside time is available.

---

## 3. Before collecting anything: confirm 86-02 actually works

**A measurement of broken code measures nothing.** Record one ordinary session and confirm it
uploads with all three fields non-NULL:

```sql
select id, session_start_utc_ms, sync_error_ms, clock_offset_ms
from sessions order by recorded_at desc limit 1;
```

If any is NULL, stop and fix 86-02 first — that is its AC-7, and it is a prerequisite here, not a
side effect.

---

## 4. Collecting

For **each session** (repeat for **8 or more**):

1. Select the **Test** athlete, so tap sessions do not pollute a real roster.
2. **Record with Video.** Microphone permission must be **GRANTED** — a muted clip has no audio
   track, and the analyzer refuses to run without one.
3. Keep the phone still and the wheel in frame. Note the phone-to-wheel distance (see §6 — it
   affects only the cross-check, never the residual, so a rough metre is fine).
4. Strike the wheel sharply **5 or more times, spaced about 3 seconds apart**. Spacing matters: the
   analyzer pairs strikes within a 1.4 s window, so taps closer than ~3 s can be mispaired.
5. Stop. Read `videoStartPhoneMs` off the in-app log line at
   [RecordScreen.js:854](../../../../swimnetics-mobile/src/screens/RecordScreen.js:854) and write it
   down with the session id and the distance.
6. Pull the raw CSV and the clip to a local folder.

**Why many short sessions rather than one long one.** Every tap inside one recording shares the same
clock error and the same camera warm-up, so extra taps in a session sharpen the *instrument* but add
nothing about the *clock*. Only a new session resamples `sync_error_ms`. Eight sessions × five taps
is worth far more than one session × forty.

---

## 5. Pre-registered bars

### B1 — the coach-facing number (end-anchored residual) · PASS/FAIL

- **|pooled mean| < 33 ms** (one frame at 30 fps), and
- **between-session SD < 50 ms**.

Rationale: 33 ms is the granularity at which a coach could perceive misalignment when scrubbing a
30 fps clip. Below one frame the overlay is as good as the medium allows.

### B2 — camera warm-up · REPORTED, NOT PASS/FAIL

It has never been measured, so there is nothing to pass. Report the pooled mean and SD, and state:

- whether the "~2 s" in the code comment is right;
- whether the between-session **SD < 100 ms**, which would make it a compensable constant rather
  than a per-session unknown.

### B3 — the instrument · PASS/FAIL, VOIDS THE RUN

- **≥ 90 % of taps accepted**, and
- **`readout_spread_frames` ≤ 1.2** on every session.

The spread is the audio-vs-frame disagreement across a session's taps. Honest taps spread over
exactly one frame, because the frame readout quantises a uniformly-distributed strike time. Much
more than that means the two streams are not describing the same events, and no residual from that
session means anything.

### B4 — the 86-02 correction · REPORTED WITH ITS INTERVAL, CONCLUSION OPTIONAL

Regress each session's `residual_start_anchored` on that session's recorded `sync_error_ms` and
report the slope with a 95 % confidence interval.

- Slope ≈ 0 is consistent with the correction being right.
- Slope ≈ +2 is consistent with 86-02 having the sign backwards.

**Draw no conclusion if the interval contains both 0 and 2.** With `sync_error_ms` spanning perhaps
30 ms across sessions and warm-up jitter plausibly ±100 ms, that is the likely outcome, and saying
so is the honest result. This bar exists to be reported, not to be passed.

---

## 6. Corrections and rejection rules, fixed in advance

**Speed of sound.** The audio readout is corrected by `distance / 343 m/s` — 5.8 ms at 2 m, the same
order as the effect. Record the distance for every session.

⚠ **The residual does not depend on the distance.** The absolute value is anchored on the *frame*
readout, and light does not travel at 343 m/s. The distance affects only the audio cross-check.
A sloppy distance therefore degrades the cross-check, not the answer.

**Rejection.** A tap is rejected when its audio and frame readouts disagree, about that session's
own A/V offset, by more than **1.5 frames** — which means the tap was mispaired or its strike was
missed in one stream. Rejections are counted and reported; they are never silently dropped.

⚠ **The bound is deliberately NOT half a frame**, which is what the PLAN's AC-4 asked for. See
`## Amendments`.

**Container offset.** A whole-session constant between the audio and video timelines (AAC encoder
priming is the usual cause) is estimated per session, reported, and flagged above one frame — but it
is **not** removed from the answer, because the answer never uses the audio timeline for its
absolute value.

---

## 7. Precision you can expect

The frame readout quantises each strike to ±half a frame, uniformly. So the **mean** over `n` taps
has

```
SE = (1/fps) / sqrt(12·n)
```

At 30 fps: **9.6 ms for one tap, 3.0 ms over 10, 1.5 ms over 40.** Eight sessions × five taps gives
about **1.5 ms**, comfortably inside B1's 33 ms bar.

**Collect taps; do not chase per-tap precision.** No single tap is worth anything on its own.

---

## 8. Analysis

```bash
python scratch/tap_test.py --raw SESSION.csv --video SESSION.mp4 --session-start-utc-ms 1756... --video-start-phone-ms 1756... --mic-distance-m 1.0 --json-out SESSION.json
```

Then aggregate the JSON sidecars across sessions and report every number as **mean ± SE with its rep
count**, per B1–B4.

**Do not change the correction, the origin formula, or any threshold in response to the result.** If
the data says something is wrong, that is a finding and a next plan.

---

## 9. A null result is a result

If B1 comes back under one frame, that is worth recording: it retires a standing suspicion, and it
converts `VideoOverlayScreen.js`'s claim that the end-anchor is warm-up-agnostic from an assertion
into a measurement. Do not treat "nothing was broken" as a failed experiment.

---

## 10. Confirmatory run (86-05)

*Registered 2026-09-02, before the run exists. §9 was already taken, hence §10.*

86-03's run was VOID and 86-04 repaired the instrument offline against the same 8 sessions. **That
corpus is now spent** — it developed the instrument, so it can never measure the clock. B1 is still
unmeasured, and this section registers the run that measures it.

### Bars — UNCHANGED IN VALUE

B1, B2, B3 and B4 in §5 are carried forward **exactly as written**. 86-04 moved no bar. The only
thing that changed is the instrument underneath them, and it changed before this run's data exists.

### What the operator must do differently

| # | Change | Why |
|---|---|---|
| 1 | **Persist `videoStartPhoneMs`** | A mobile change + EAS build. Until it lands, **B2 and B4 are unmeasurable** — see the 2026-09-01 amendment. This is the only gate that costs a build. |
| 2 | **≥ 8 strikes per session** | 86-03 got 5+ accepted on only 4 of 8 sessions, and the repaired detector deliberately drops soft strikes rather than guessing. There is a second reason: `av_offset` needs **≥ 3 paired taps** or it silently falls back to 0.0, and a miscentred scatter check then rejects honest taps. Tap test 1 hit exactly that in the re-run. |
| 3 | **Strike with consistent force** | Detection is peak-relative to the session's *hardest* strike, so a soft one falls under the bar. This is a protocol fix on purpose: letting the detector use the audio onset count as a hint would couple the two sensors the test keeps independent. |
| 4 | **≥ 3 s between strikes** | Unchanged from §4, but now load-bearing twice: it protects the 1.4 s pairing window **and** keeps audio onsets outside the audio detector's own 0.5 s refractory. One gap of 0.52 s in the 86-03 corpus produced a false extra onset that cost two taps to contention. |
| 5 | **Supply `--crop`** | So frame differencing sees the wheel and not the striking hand. |

### What to report

Everything §8 already asks for, plus the three health fields 86-04 added:
`encoder_overtrigger_ratio` (want ~1.0; 86-03 reached 5.6), `interval_pattern_max_delta_s`, and the
per-tap `vel_to_raw_offset_ms`. **If `vel_to_raw_offset_ms` ever collapses toward zero, the timing
has migrated into the velocity domain and the run is void** — that lag is real and must stay visible.

**Do not change the correction, the origin formula, or any threshold in response to the result.**
§8's rule, restated here because 86-04 was the plan that had to obey it.

---

## Instrument status

As of this commit, on 43 real raw CSVs and synthetic fixtures:

- `--self-test`: **PASS.** Five injected offsets (−500, −50, 0, +50, +500 ms) recovered within
  **0.33 ms** against a 2 ms bar; the single-tap rejection path fires; a container offset provably
  does not leak into the residual.
- `--validate-timebase raw/`: **39/39 clean files agree with the production pipeline sample by
  sample, to 0.000000 ms and 0.000000 mm.** One file excluded for a stated, provable reason.

Three defects the instrument found while being built, all fixed and all relevant to the run:

1. **An off-by-one in the tap detector.** `jerk[k]` spans samples `k → k+1`, so the strike lands on
   `k+1`. Reporting `k` put every tap one raw sample (3.7 ms) early — a constant positive residual
   that would have been quietly attributed to the clock.
2. **Encoder dropouts look exactly like strikes.** Aliased count steps appear in **37 of 40** real
   recordings, up to 66 in one file. The detector now refuses any step above 1024 counts/sample
   (12.7 m/s at the tether — faster than Usain Bolt), so garbage cannot be read as a tap.
3. **A naive `micros()` unwrap invents time.** `raw/leo3.csv` has 17 backward timestamp steps in a
   46 s recording; treating each as a uint32 rollover put its time base 20.3 hours out. Only a step
   below −2³¹ is a rollover.

And one finding that justifies a decision the PLAN had only asserted: the **decimated trace sits a
median of 103 ms — worst 353 ms — away from raw** at distance landmarks, because a small vertical
difference becomes a large horizontal one wherever the distance curve is flat (a glide, the drift
into the wall). Reading the raw CSV rather than the processed trace is load-bearing, not a
preference.

---

## Amendments

*Anything added here after the run begins must be dated and justified.*

- **2026-09-01, before any data — AC-1's tolerance.** The PLAN asked for a flat 2 ms. That is not a
  reachable bar for a frame-quantised instrument, since a single tap carries a uniform ±half-frame
  error by construction. Rather than loosen the bar, the *fixture* was changed: sub-frame phases are
  **stratified**, one tap per twelfth of the frame interval, so quantisation cancels exactly and the
  2 ms bar tests the arithmetic as originally written. The field precision limit is §7 instead.
- **2026-09-01, before any data — AC-2's landmark.** The PLAN compared a landmark against a
  coach-marked `dive_start_s` at one raw sample. Not achievable, and the AC was wrong to ask: a
  coach's dive mark is a human judgement about where a race begins, not a threshold crossing.
  Replaced with a **sample-by-sample** comparison against `vel_acc_extraction`'s own time base and
  count-to-distance mapping, which tests exactly the off-by-one the AC existed to catch, and does so
  more strictly.
- **2026-09-01, before any data — AC-4's rejection bound.** The PLAN said reject beyond half a
  frame. The self-test showed this is actively harmful: the bound must be centred on the session's
  true A/V offset, that centre can only be estimated from a handful of taps, and a noisy centre
  rejects precisely the taps at the extremes of the phase distribution — one tail of a uniform
  distribution, not bad data. Dropping them **biases the surviving mean**, which is the number being
  measured. Observed directly: 11 of 12 fixture taps accepted and the recovered offset off by
  +9.6 ms in a fixture with zero true error. The bound is now 1.5 frames, which catches mispaired
  and missed taps and cannot touch an honest one; the half-frame expectation survives as B3's
  reported spread.
- **2026-09-01, before any data — camera warm-up sign.** The PLAN wrote it as
  `start_anchored − end_anchored`, which makes a real warm-up negative. Defined here as
  `end_anchored − start_anchored`.
- **2026-09-01, AFTER the run — `--video-start-phone-ms` made optional.** The first amendment made
  after data exists, and it is an instrument capability change, not a bar change: no bar, threshold,
  rejection rule or formula moved. §4 step 5 told the operator to hand-transcribe `videoStartPhoneMs`
  off the on-screen log. It was not recorded for the 2026-09-01 run, and it is **never persisted** —
  `grep videoStartPhoneMs` over the mobile tree finds it only in React state and the
  `RecordScreen.js:854` log line; it is not in the DB and not in the clip container, whose
  `creation_time` is 1-second resolution against a 33 ms bar. The analyzer now accepts its absence
  and reports `start_anchored_origin_s`, `camera_warm_up_s` and every `residual_start_anchored_s` as
  `None`, so **B1 stays computable while B2 and B4 are reported as unmeasured rather than invented**.
  The self-test is unchanged and still passes identically. ⚠ The protocol asking an operator to copy
  down a number the app throws away is the design defect this exposed; fixing it means persisting
  `videoStartPhoneMs`, which is a mobile change and out of 86-03's scope.

- **2026-09-02, AFTER the run — 86-04's instrument repair. NO BAR MOVED.** Detection changed
  domain; every threshold in §5 and §6 is untouched. Recorded here in full because the constants
  behind it were **tuned on the void corpus, not pre-registered against it** — the sweep was run
  before 86-04 was written, and saying otherwise would be the exact failure this file exists to
  prevent. What *is* pre-registered is that each constant equals what its stated rule produces, and
  that all three froze before 86-05's data exists.

  **What was wrong.** The detector hunted raw `|d(counts)|` against a `median + 10·MAD` floor. A
  struck wheel rings, so one strike produced 10–28 crossings that the 0.5 s refractory could not
  collapse, and a ring-down artifact could take a real strike's place. The strike was never hard to
  see — it was hard to see *in that domain*.

  **What changed.** `FIND` on decimated `|velocity|` at `TAP_FRAC = 0.20` of the session's own
  maximum (flat event count across 10–35% on all 8 sessions, where raw jerk never stabilises; **no
  refractory constant at all** — the smoothing collapses ring-down for free). `TIME` on raw
  `|d(counts)|` within `RAW_REFINE_WINDOW_S = 0.25 s`, because the velocity peak lags the raw strike
  by **+16.3 ms pooled (n = 34, SD 22.6), per-session means −5.0 to +39.4 ms** — against a 33 ms bar,
  and varying session to session so it would not cancel as a constant, timing there would manufacture
  the very clock error this test detects. `CHECK` by contention (two onsets, one tap) and by interval
  pattern at `PAIR_TOL_S = 0.05 s` — a difference of gaps, so any constant clock offset cancels
  exactly, which is what makes it an admissible check rather than a look at the answer. Reproduce all
  three constants with `python scratch/tap_test.py --measure-domain scratch/taptest`.

  **Result on the void corpus, IN-SAMPLE and an upper bound — not a measurement of anything.**

  | | 86-03 | 86-04 |
  |---|---|---|
  | acceptance | 35/42 = **83.3%** | 28/42 = **66.7%** |
  | worst `encoder_overtrigger_ratio` | **5.6** | **1.0** |
  | accepted taps > 50 ms from their session median | **10** | **0** |
  | worst deviation from session median | **315.1 ms** | **33.7 ms** |
  | `readout_spread_frames` ≤ 1.2 | all 8 | all 8 (improved on 5) |

  **Acceptance got worse and that is the correct trade.** The laundering is gone: no accepted tap
  now sits more than 34 ms from its session median, where 86-03 had ten beyond 50 ms and one at
  315 ms. 86-04 traded confident wrong answers for visible rejections. **B3 still FAILS on this
  corpus** (66.7% < 90%), which is expected and was written down before the re-run — the corpus was
  collected through the broken instrument and cannot be rescued by a better one.

  **The 14 rejections, honestly classified:** 7 unmatched (velocity found no strike — 4 of them show
  a real 7–19% velocity excursion at the onset, 3 sit at the noise floor), 5 audio-vs-frame
  disagreement (the pre-existing §6 rule, video-side, and *fewer* than 86-03's 7), 2 contention. The
  interval-pattern check **never fired**: its worst session delta was 38.4 ms against a 50 ms
  tolerance.

  ⚠ **One rejection is not trustworthy, and the reason is worth keeping.** `av_offset` is estimated
  only when ≥ 3 taps pair; below that it falls back to **0.0**, and §6's scatter check is then
  centred on zero instead of the session's real A/V offset. Tap test 1 paired only 2, so its single
  disagreement rejection is measured against the wrong centre. **Under-detection can starve the
  estimator that the rejection rule depends on** — a feedback loop between the two failure modes.
  Not fixed here: 86-04's own rule is one lever at a time, and §10's "≥ 8 strikes per session"
  addresses the cause rather than the symptom.

  ⚠ **The audio onset count is not clean ground truth either.** Tap test 8's first two onsets are
  **0.52 s** apart against a population of 2.54–4.42 s, sitting on the audio detector's own 0.5 s
  refractory edge — indistinguishable from one strike re-triggering it. That false onset is what
  produced both contention rejections, and it means part of the velocity-vs-audio count mismatch is
  audio **over**-triggering rather than velocity under-detection. Flagged, never dropped.

  **Three defects found while applying the repair, each of which would have looked like success:**
  (1) the interval check ran before the scatter check and rejected session-wide, so one shifted
  audio onset condemned all 12 fixture taps — the standing desync gate went 11/1 → 0/12; it now runs
  last, over taps whose audio readout has already been vouched for. (2) The fixture's 200 counts/s
  baseline is 8.5% of peak `|velocity|`, so a planted ring fraction arrived inflated and the repair
  "failed" for a reason unrelated to ring-down. (3) `|velocity|` of an overshooting impulse has two
  lobes, so one strike raised two candidates refining to the *identical* raw sample — inflating the
  very health field meant to expose over-triggering.

  **AC amendment (86-04's own AC-5).** It asked for `|residual| ≤ 2 ms` on a single fixture tap.
  Not reachable: one tap carries a uniform ±half-frame (16.7 ms) quantisation error by construction,
  the same mistake corrected in 86-03's AC-1 above. The 2 ms bar is applied instead to the **encoder
  time against the fixture's own known strike** — exact, no frame quantisation in the path, and it
  tests what the AC actually cares about: real strike, or ring-down artifact hundreds of ms away.
  Verified both ways: the fixture makes 86-03 accept 6 taps carrying > 150 ms (worst +190 ms) from
  zero injected error, and 86-04 pairs that same tap to the real strike within **0.46 ms**.
