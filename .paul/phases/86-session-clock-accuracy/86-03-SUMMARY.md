---
phase: 86-session-clock-accuracy
plan: 03
subsystem: measurement
tags: [tap-test, video-sync, pre-registration, instrument-defect, void-run]

# Dependency graph
requires:
  - phase: 86-01
    provides: "patch_14's three columns + GET /time — live, and the reason the 8 sessions carry clock fields at all"
  - phase: 86-02
    provides: "the BLE-corrected session_start_utc_ms this plan set out to evaluate; its AC-7 is CLOSED by this run"
provides:
  - "scratch/tap_test.py — offline tap analyzer, self-test PASS, time base validated 39/39 sample-by-sample"
  - "TAP-TEST-PROTOCOL.md — pre-registered bars, 5 dated amendments"
  - "a VOID run under its own B3 bar, and the named instrument defect that voided it"
  - "86-02's AC-7: PASSED on 8 of 8 device sessions"
affects: [86-04-or-successor, swimclips-integration, video-overlay]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pre-registered pass bars committed before data, amended only in a dated public log"
    - "an instrument bar (B3) that can VOID a run, evaluated before the result bar (B1) is read"
    - "two independent readouts of the same event, with disagreement as a rejection rule"

# Metrics
tests-added: 0       # tap_test.py is an instrument, not a standing harness (plan boundary)
tests-passing: 566   # pytest unchanged
sessions-collected: 8
taps-accepted: 35
taps-total: 42
acceptance-rate: 0.833   # bar >= 0.90 -> FAIL
---

# Phase 86 Plan 03: Tap Test Summary

**Status: CLOSED 2026-09-02 with a VOID RUN.** The device run happened, the data is good enough to
diagnose but not good enough to trust, and **B3 — the instrument bar, which the protocol declares
voids the run — FAILED at 83.3% tap acceptance against a 90% bar.** B1's numbers are therefore
reported below but carry no evidential weight. Recording the run as void was the user's explicit
call at the failure checkpoint.

**The run was not wasted.** It closed 86-02's only unmet AC, it bounded the phase's flight-time
estimate, and it found a defect in the instrument's own rejection rule that no amount of self-testing
would have surfaced.

---

## What actually happened

Tasks 1–3 were applied and committed in a prior session (`3f4d2c7`, `b45e38e`) and were re-verified
from a clean tree at the start of this one, not taken on trust:

| Gate | Result |
|---|---|
| `tap_test.py --self-test` | PASS — 5 injected offsets recovered worst-case **0.33 ms** against a 2 ms bar; rejection path fires 11/1; no container-offset leak |
| `--validate-timebase raw/` | **39/39** clean files agree with `vel_acc_extraction` **sample by sample** at 0.000000 ms / 0.000000 mm |
| `pytest tests/` | **566 passed**, exit 0 (conda interpreter — `.venv` has no pytest) |

Task 4's build gate lifted: an EAS build carrying 86-02 shipped, and 8 tap sessions were recorded
("Tap test 1"–"Tap test 8", the Test athlete, wheel on a desk). All 16 files — 8 raw CSVs and 8
clips — were pulled from Supabase Storage. Every clip carries an **AAC audio track**, so the
protocol's mic-permission requirement was met; all are HEVC at a nominal 30 fps, 15.0–21.5 s.

---

## Bar verdicts

### B1 — end-anchored residual · PASS on both bars, **BUT GATED BY B3, SO NOT A RESULT**

- Pooled mean **+14.17 ms**, SD 95.02, **SE 16.06**, **n = 35 accepted taps** — bar |mean| < 33 ms → *would* PASS
- Between-session SD **44.03 ms**, n = 8 sessions — bar < 50 ms → *would* PASS

**These are not reported as the phase's answer.** B3 is a precondition, not a companion metric, and it
failed. A pooled mean computed over a set that includes known mispairs is not an estimate of anything.

### B2 — camera warm-up · **UNMEASURED**

`videoStartPhoneMs` was not recorded for any of the 8 sessions, and it is **never persisted**: it
exists only in React state and the `RecordScreen.js:854` on-screen log line. Not in the DB; not in the
clip container, whose `creation_time` has 1-second resolution against a 33 ms bar. Without it there is
no start-anchored origin and therefore no warm-up. See the 2026-09-02 amendment.

⚠ **One suggestive observation, explicitly NOT a measurement of B2.** `deviceDuration − videoDuration`
is **0.6913 s, SD 28.4 ms** across all 8 sessions. That quantity is start-lag *plus* stop-lag, and it
does not isolate warm-up. But a ~2 s warm-up — the figure in the `VideoOverlayScreen.js:52` comment —
would require a stop-lag near **−1.3 s**, which is not physically sensible. **The "~2 s" comment is
doubtful and deserves the dedicated measurement B2 was meant to be.**

### B3 — the instrument · **FAIL. VOIDS THE RUN.**

- Acceptance **35/42 = 83.3%**, bar ≥ 90% → **FAIL**
- `readout_spread_frames` ≤ 1.2 on every session (0.28–1.11) → PASS

The spread bar passing while acceptance fails is the diagnosis in miniature: **the video side is
healthy and the encoder side is not.**

### B4 — the 86-02 correction · **UNMEASURED**

Needs the start-anchored residual, which needs `videoStartPhoneMs`. No regression was run, and none
is reported. The predicate for the bar existing at all did hold: `sync_error_ms` spanned
**0.5–30.0 ms** across the 8 sessions (mean 18.50 ± 4.37, SD 12.36), close to the ~30 ms span the
protocol anticipated, so a future run with `videoStartPhoneMs` recorded would have real range to
regress against.

---

## Per-session data

| Session | enc | audio | frames | acc | rej | accept% | spread (fr) | end origin (s) | median resid | MAD |
|---|---|---|---|---|---|---|---|---|---|---|
| Tap test 1 | 13 | 5 | 8 | 3 | 2 | 60% | 0.28 | 0.7123 | −27.6 ms | 7.7 |
| Tap test 2 | 11 | 5 | 7 | 3 | 2 | 60% | 0.29 | 0.6794 | +17.9 | 4.4 |
| Tap test 3 | **28** | 5 | 8 | 5 | 0 | 100% | 0.59 | 0.7160 | +6.3 | **56.1** |
| Tap test 4 | 10 | 6 | 8 | 4 | 2 | 67% | 0.70 | 0.6756 | −16.4 | 12.6 |
| Tap test 5 | 16 | 5 | 7 | 4 | 1 | 80% | 0.83 | 0.6752 | +23.0 | **62.8** |
| Tap test 6 | 10 | 5 | 5 | 5 | 0 | 100% | 0.81 | 0.6641 | −45.1 | 15.1 |
| Tap test 7 | 11 | 5 | 5 | 5 | 0 | 100% | 1.11 | 0.6658 | −10.3 | 7.2 |
| Tap test 8 | 21 | 6 | 7 | 6 | 0 | 100% | 0.87 | 0.7419 | +37.8 | 9.7 |

7 rejections, all for the pre-registered reason (audio and frame readouts disagreeing by more than
1.5 frames about the session's own A/V offset). None were silently dropped.

---

## 🔴 The defect that voided the run, and why it matters beyond this plan

**The encoder tap detector over-triggers.** `enc` counts 10–28 events where roughly 5 strikes
occurred; audio found 5–6 and frames 5–8. A struck wheel *rings*, `REFRACTORY_S = 0.5` does not span
the ring-down, and `MATCH_WINDOW_S = 1.4` is then wide enough to pair an audio onset with a ringing
event instead of with the strike.

**AC-4's rejection rule is structurally blind to this failure mode.** It compares the audio readout
against the frame readout — two readouts of the *video*. When the **encoder** side is mispaired, both
video readouts still agree perfectly, so the tap is marked ACCEPTED and carries a 180–320 ms residual
into the pooled mean.

The signature is unmistakable in the per-tap data:

```
Tap test 6:  -45.1  -60.2  -53.0  -23.6   +246.5      <- four tight, one gross
Tap test 3:   +3.1  +321.4   +6.3  +176.5   -49.7      <- three plausible, two gross
Tap test 8:  +47.5  +47.5  +39.8  +35.9  -186.6  +16.8
```

**10 of the 35 *accepted* taps sit more than 50 ms from their own session's median.** Protocol §7
predicts a within-session SD of ~9.6 ms from frame quantisation alone; only Tap tests 2, 4 and 7 are
anywhere near that. The rest are 5–16× too wide, which cannot be a clock error — `<measurement_honesty>`
established that clock error and warm-up are both *constant within a recording*, so any within-session
scatter beyond frame quantisation is the instrument, by construction.

**This is the most valuable output of the run:** a rejection rule that cannot see the failure mode
that actually occurs is worse than no rejection rule, because it launders bad taps as good ones.

⚠ **Contributing factor, not the cause:** no `--crop` was supplied, so frame differencing ran
full-frame and could register hand motion as well as the strike. The spread bar passing on all 8
sessions says this was secondary.

---

## What the run DID establish

**✅ 86-02's AC-7 PASSES — its only unmet AC, and the first time any of it has run on a phone.**
All 8 sessions uploaded with non-NULL `session_start_utc_ms`, `sync_error_ms` and `clock_offset_ms`.
The probe burst, the `Math.round` guard, the plausibility window and the concurrent `/time` probe all
survived contact with a real device. **This closes 86-02.**

**✅ The end-anchored origin arithmetic is independently corroborated.** On the two sessions that
carry a stored `sessions.video_origin_s`, the analyzer's independently computed
`deviceDuration − videoDuration` agrees with what the app persisted to **+3.5 ms** (Tap test 3) and
**+10.9 ms** (Tap test 2). Two points only, but they were computed by different code on different
inputs, and 86-03's central claim — that the shipped overlay uses the end-anchor — is now *evidenced*
rather than read off a source line.

**✅ The "20–80 ms" BLE flight-time estimate is now bounded by measurement.** `sync_error_ms` is
`minRTT/2` by construction, so the 8 observed values **0.5–30.0 ms (mean 18.50 ± 4.37)** are direct
one-way flight estimates. The upper end of the phase's stated "20–80 ms" is not supported; the
implied minimum round trip spans 1–60 ms.

⚠ `clock_offset_ms` ranged **−52.5 to +49.0 ms** (mean −5.81 ± 10.00, SD 28.28). Reported only —
this plan does not test it, and both tap readouts share the phone clock so it cancels regardless.

---

## Phase 86 accuracy claims: measured or still estimated

| Claim | Where | Verdict |
|---|---|---|
| 86-02 sends all three clock fields on a real device | 86-02 AC-7 | ✅ **MEASURED** — 8/8 sessions non-NULL |
| The shipped overlay uses the end-anchor, not what 86-02 corrected | 86-03 objective | ✅ **EVIDENCED** — stored `video_origin_s` matches the computed end-anchor to 3.5 / 10.9 ms |
| BLE one-way flight is "20–80 ms" | 86-02 / sessionClock.js:12 | ✅ **BOUNDED, and the range is wrong** — measured 0.5–30.0 ms (n=8) |
| End-anchored residual (what the coach sees) | B1 | ❌ **STILL UNMEASURED** — run void under B3 |
| Camera warm-up "~2 s" | VideoOverlayScreen.js:52 | ❌ **STILL UNMEASURED**, and now **doubtful**: duration difference is 0.691 s ± 28 ms |
| `rtt/2` assumes symmetric BLE legs | 86-02 D5 | ❌ **STILL AN ESTIMATE** — B4 not run |
| `clock_offset_ms` correctness | out of scope by design | ❌ **NOT TESTED**, and cannot be by this instrument |

---

## Acceptance Criteria Results

| AC | Verdict |
|---|---|
| AC-1 analyzer recovers a known offset | ✅ PASS — worst 0.33 ms of 2 ms, 5 offsets |
| AC-2 raw-CSV time base correct | ✅ PASS — 39/39 files, sample-by-sample, 0.000000 ms |
| AC-3 both mappings reported separately | ⚠ **PARTIAL** — the end-anchored number is reported alone; the start-anchored half is `None`, never collapsed into a single "sync error". The AC's intent (never conflate them) holds; its letter (emit both) could not be met without `videoStartPhoneMs` |
| AC-4 disagreeing readouts rejected | ⚠ **PASS BY THE LETTER, FAILS IN SUBSTANCE** — 7 taps rejected and counted, but the rule cannot see encoder mispairs, which is what actually went wrong |
| AC-5 bars pre-registered | ✅ PASS — committed in `3f4d2c7`, before the run; all amendments dated, 4 pre-data and 1 post-data |
| AC-6 the run happens (8 sessions × 5+ accepted taps) | ❌ **FAIL** — 8 sessions collected, but only 4 of 8 reached 5 accepted taps (3, 3, 5, 4, 4, 5, 5, 6) |
| AC-7 the phase's estimates are settled | ⚠ **PARTIAL** — every number above carries its rep count and SE, and the measured/estimated table is complete; but the headline estimate B1 existed to settle remains unsettled |

---

## Files Created/Modified

- `scratch/tap_test.py` — **modified this session**: `--video-start-phone-ms` made optional, emitting
  `None` for the start-anchored quantities rather than inventing them. 24 insertions, 11 deletions.
  Self-test re-run after the change and passes identically. This is the plan's own `files_modified`
  entry, and the change touches no bar, threshold or formula.
- `.paul/phases/86-session-clock-accuracy/TAP-TEST-PROTOCOL.md` — one dated post-run amendment added.
- `.paul/phases/86-session-clock-accuracy/86-03-SUMMARY.md` — this file.
- `scratch/taptest/` — 8 raw CSVs, 8 clips, 8 JSON sidecars (data, untracked).
- `scratch/_tap_pull.py`, `_tap_fetch.py`, `_tap_run.sh`, `_tap_agg.py` — read-only probes, untracked.

**No production source was modified.** `swimnetics-mobile/**`, `api.py`, `vel_acc_extraction.py`,
`metrics.py`, `phase_metrics.py` and every stored session are untouched, per the plan's boundaries.
No correction, origin formula or threshold was changed in response to the result.

---

## Issues Encountered

1. **B3 failed and voided the run** — the primary outcome, diagnosed above.
2. **`videoStartPhoneMs` is unrecoverable** — the protocol asked an operator to hand-copy a number
   the app never persists. The design defect is the app's, not the operator's.
3. **The plan's Task 5 verify says "no source file outside `.paul/` is modified"**, and
   `scratch/tap_test.py` was modified. Reconciled: the plan's own `files_modified` and its
   `<verification>` checklist both name `tap_test.py` explicitly, so the Task 5 line means *production*
   source. Stated here rather than left for a reader to trip over.
4. **No `--crop` was supplied**, so frame differencing ran full-frame. Secondary to the encoder defect.

---

## Next Phase Readiness

**Phase 86 does NOT close.** 86-01 and 86-02 are closed (86-02's AC-7 passing here is what closes it),
but 86-03 ends void, so the phase's stated purpose — replacing estimates with measurements — is only
partly met. The plan-count heuristic would read 3 of 3 and call it done; that is the same trap flagged
for 83-01, 83-02 and 88-04.

**A successor plan has a clear, cheap brief, and the data for it is already on disk:**

1. **Fix the encoder tap detector.** Measure the wheel's ring-down from the 8 raw CSVs already
   downloaded and set the refractory period from that measurement — committed on its own terms,
   *before* looking at what it does to B1. The temptation to tune until B1 looks tidy is real: a
   post-hoc per-session median over this run gives **−1.79 ± 9.88 ms (n=8)**, temptingly close to
   zero, and it is exactly the number pre-registration exists to stop anyone from quoting.
2. **Add an encoder-side pairing check**, so a mispair is rejected instead of laundered. AC-4's rule
   is necessary and not sufficient.
3. **Persist `videoStartPhoneMs`** (mobile change) so B2 and B4 are ever measurable.
4. Re-analysis needs **no new device run**; a re-*run* is only needed for B2/B4.

⚠ Until a successor lands, **no document may quote a measured end-anchored accuracy figure**, and the
"~2 s" camera warm-up comment stands as unverified — now with a concrete reason to doubt it.
