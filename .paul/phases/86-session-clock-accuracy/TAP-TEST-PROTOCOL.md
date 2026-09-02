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
- **2026-09-02, AFTER the run — `--video-start-phone-ms` made optional.** The first amendment made
  after data exists, and it is an instrument capability change, not a bar change: no bar, threshold,
  rejection rule or formula moved. §4 step 5 told the operator to hand-transcribe `videoStartPhoneMs`
  off the on-screen log. It was not recorded for the 2026-09-02 run, and it is **never persisted** —
  `grep videoStartPhoneMs` over the mobile tree finds it only in React state and the
  `RecordScreen.js:854` log line; it is not in the DB and not in the clip container, whose
  `creation_time` is 1-second resolution against a 33 ms bar. The analyzer now accepts its absence
  and reports `start_anchored_origin_s`, `camera_warm_up_s` and every `residual_start_anchored_s` as
  `None`, so **B1 stays computable while B2 and B4 are reported as unmeasured rather than invented**.
  The self-test is unchanged and still passes identically. ⚠ The protocol asking an operator to copy
  down a number the app throws away is the design defect this exposed; fixing it means persisting
  `videoStartPhoneMs`, which is a mobile change and out of 86-03's scope.
