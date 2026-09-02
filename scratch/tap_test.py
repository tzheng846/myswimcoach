#!/usr/bin/env python3
"""
tap_test.py — Phase 86-03 offline tap-test analyzer.

Measures how well a video clip aligns to the encoder trace, by striking the wheel while it is in
frame and comparing when the strike happened in each stream.

WHAT IT REPORTS, AND WHY THERE ARE TWO OF THEM
----------------------------------------------
The product contains two different video-to-trace mappings, and 86-03's planning found that they are
NOT interchangeable:

  end_anchored_origin_s   = device_duration_s - video_duration_s
      What actually ships. VideoOverlayScreen.js:69 computes it, it is persisted to
      sessions.video_origin_s, and both the iOS overlay and the web annotate page read it back.
      It is a difference of two DURATIONS, so sessionStartPhoneMs cancels exactly and Phase 86's
      BLE round-trip correction never moved it. This is the number a coach actually sees.

  start_anchored_origin_s = (video_start_phone_ms - session_start_utc_ms) / 1000
      The absolute mapping. This is what 86-02 corrected, and what an external camera would have to
      use, having no end-anchor of its own. Carries the camera warm-up that got the start anchor
      dropped in Phase 60.

Session time of a video event at video time v is `v + origin` (VideoOverlayScreen.js:49), so:

  residual = (t_video + origin) - t_encoder

SIGN CONVENTION: positive residual = the video readout lands LATER in session time than the
encoder's, i.e. the origin is too large.

  camera_warm_up_s = end_anchored_origin_s - start_anchored_origin_s
      Positive = the first frame arrives this long after the recordAsync() call. (The 86-03 PLAN
      wrote this difference the other way round; that would make a real warm-up negative. Corrected
      here — see the APPLY notes in 86-03-SUMMARY.)

TWO INDEPENDENT READOUTS OF THE SAME TAP
----------------------------------------
(a) Audio onset — ~0.02 ms resolution, corrected for sound travel time (d / 343 m/s). At 2 m that
    is 5.8 ms, the same order as the effect being measured, so it is a correction and not a
    rounding detail.
(b) Frame index — quantised, and biased LATE by half a frame on average: the first frame showing a
    strike sits uniformly in (0, 1/fps] after it. The frame estimate is therefore de-biased by
    0.5/fps before comparison, after which |audio - frame| <= 0.5/fps holds for every honest tap.

WHICH ONE ANCHORS THE ANSWER: the frames, and ONLY the frames. `video_origin_s` maps the PLAYER's
currentTime to session time, and currentTime is the video timeline, so the frame readout is the
correct absolute reference. Audio sits on its own timeline, which the container can offset by an
unknown constant (AAC encoder priming, ~21 ms at 48 kHz — measured on this machine by --self-test).
Anchoring on audio would import that constant straight into the answer.

So audio is used for detection, for the per-tap cross-check, and as a diagnostic; the residual is
computed from the frame readout alone. Two consequences worth knowing:
  * Precision is frame-quantisation-limited. Per tap the error is uniform over +/- half a frame, so
    the MEAN over n taps has SE = (1/fps)/sqrt(12*n) — 1.5 ms at 30 fps over 40 taps, far inside the
    33 ms bar B1 sets. Collect taps; do not chase per-tap precision.
  * The residual is immune to the phone-to-wheel distance, because light does not travel at 343 m/s.
    The distance still matters for the audio cross-check, so it is still recorded and corrected.

A tap whose audio and frame readouts disagree, about that session's own A/V offset, by more than
half a frame is REJECTED — which catches a mispaired or missed tap. A whole-session container
offset is reported (and flagged above one frame) rather than silently failing every tap.

FINDING THE STRIKE — TWO DOMAINS, ON PURPOSE (86-04)
----------------------------------------------------
86-03's run was VOIDED by its own B3 bar because this module's detector over-triggered: it hunted
raw |d(counts)| against a median+10*MAD floor, the struck wheel rings, and one strike produced 10-28
crossings that a 0.5 s refractory could not collapse. The strike was never hard to see — it was hard
to see IN THAT DOMAIN.

  FIND on decimated |velocity|, peak-relative      the smoothing collapses ring-down for free;
                                                   the event count is flat across 10-35% of the
                                                   session maximum on all 8 corpus sessions,
                                                   where raw jerk never stabilises
  TIME on raw |d(counts)|, argmax in a window      3.7 ms, no filter anywhere in the path
  CHECK by interval pattern + contention           encoder-side, and clock-offset-free

Velocity cannot carry the timing: its peak lags the raw strike by +16.3 ms pooled (n=34, SD 22.6),
per-session means -5.0 to +39.4 ms. Against B1's 33 ms bar, and varying session to session so it
would not cancel as a constant, timing there would MANUFACTURE the very clock error this module
exists to detect. Hence the split, and hence vel_to_raw_offset_ms is recorded on every tap.

MODES
-----
  --self-test              synthetic fixtures with injected offsets     (AC-1, AC-3, AC-4, AC-5)
  --validate-timebase DIR  raw time base vs the production pipeline           (AC-2)
  --measure-domain DIR     which domain the strike is visible in, and the constants the rules
                           produce from that measurement                      (86-04 AC-1)
  (default)                analyze one real rep

Needs ffmpeg + ffprobe on PATH. Read-only: never writes to Supabase, never touches a stored session.
"""

import argparse
import contextlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

SPEED_OF_SOUND_MS = 343.0
COUNTS_PER_REV = 4096
WHEEL_DIAMETER_M = 0.06  # mirrors vel_acc_extraction; asserted against it by --validate-timebase
UINT32 = 2 ** 32

# A tap is one physical strike; nothing real re-triggers inside this window.
REFRACTORY_S = 0.5
# Coarse pairing window. Must exceed the residual being measured and stay below half the tap
# spacing the protocol asks for (3 s), or taps can be mispaired.
MATCH_WINDOW_S = 1.4
# Gross-disagreement bound for the audio/frame cross-check, in frames.
#
# WHY NOT HALF A FRAME. The theoretical spread of (audio - de-biased frame) IS +/- half a frame, so
# half a frame looks like the natural bound — and rejecting there is what the PLAN's AC-4 asked for.
# It is wrong, and the self-test caught it: the bound has to be centred on the session's true A/V
# offset, that centre can only be ESTIMATED from a handful of taps, and a noisy centre rejects
# precisely the taps at the extremes of the phase distribution. Those taps are not bad data — they
# are one tail of a uniform distribution — so dropping them BIASES the surviving mean, which is the
# very number being measured. Observed directly: 11 of 12 fixture taps accepted and the recovered
# offset off by +9.6 ms, in a fixture with zero true error.
#
# The cross-check's real job is to catch a MISPAIRED or MISSED tap, which sits frames away, not
# fractions of one. 1.5 frames is far outside the honest +/- 0.5 spread, so it never touches a good
# tap and cannot bias anything. The half-frame expectation survives as a reported health metric —
# `readout_spread_frames` — rather than as a filter. See 86-03-SUMMARY.
GROSS_DISAGREEMENT_FRAMES = 1.5

# Largest count step between two raw samples that any physical motion could produce.
#
# The wheel is 60 mm, so one revolution is 188.5 mm and one count is 46.0 um. At 270 Hz a step of
# 1024 counts is 47 mm in 3.7 ms — 12.7 m/s at the tether. Usain Bolt does 12.3. Anything at or
# above this is a failed I2C read, not motion.
#
# This matters more here than anywhere else in the codebase: a garbage sample is a large isolated
# jump in the counts, which is EXACTLY the signature this module hunts for when it looks for a
# strike. Without this bound the tap detector would happily lock onto encoder dropouts. Measured
# across raw/: aliased steps of half a revolution or more appear in 27 of 40 real recordings, up
# to 66 in a single file.
MAX_PLAUSIBLE_COUNTS_PER_SAMPLE = 1024


# ── shell ──────────────────────────────────────────────────────────────────────

def _run(cmd, stdin_bytes=None, want_bytes=True):
    """Run a subprocess, raising with the tool's own stderr on failure."""
    proc = subprocess.run(
        cmd,
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-6:]
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}):\n  " + "\n  ".join(tail))
    return proc.stdout if want_bytes else proc.stdout.decode("utf-8", "replace")


def have_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        try:
            _run([tool, "-version"])
        except (OSError, RuntimeError):
            return False
    return True


# ── encoder side ───────────────────────────────────────────────────────────────

def read_raw(path):
    """
    Raw encoder CSV -> session time and unwrapped counts.

    Deliberately does NOT import vel_acc_extraction: AC-2 compares this reader against the
    production pipeline, and a check that shares its arithmetic checks nothing. The unwrap here is
    modular integer arithmetic; production uses np.unwrap on radians.
    """
    df = pd.read_csv(path)
    required = {"timestamp_us", "angle_counts", "magnet_ok"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns {missing} — is this a raw encoder CSV?")

    df = df[df["magnet_ok"] == 1].copy()
    df = df.dropna(subset=["timestamp_us", "angle_counts"])
    df = df.drop_duplicates(subset="timestamp_us").reset_index(drop=True)
    if len(df) < 100:
        raise ValueError(f"{path}: only {len(df)} usable rows")

    ts = df["timestamp_us"].to_numpy(dtype=np.int64)
    # micros() is uint32 and rolls over at 71.6 min. Only a step below -2^31 is a rollover: a
    # SMALL backward step is corruption, not a wrap, and adding 2^32 to it invents hours of time.
    # That is not hypothetical — raw/leo3.csv has 17 backward steps in a 46 s recording, and
    # treating them as rollovers put its time base 20.3 hours from production's.
    steps = np.diff(ts)
    n_rollover = int((steps < -(UINT32 // 2)).sum())
    n_backward = int((steps < 0).sum()) - n_rollover
    steps = np.where(steps < -(UINT32 // 2), steps + UINT32, steps)
    t_s = np.concatenate([[0.0], np.cumsum(steps) / 1e6])

    counts = df["angle_counts"].to_numpy(dtype=np.int64)
    d = np.diff(counts)
    # A step of half a revolution or more between samples is 135 rev/s at 270 Hz — physically
    # impossible on a swim, so it is an aliased or garbage reading. These are COMMON (27 of 40
    # files in raw/), which is why the tap detector carries a plausibility bound.
    n_alias = int((np.abs(d) >= COUNTS_PER_REV // 2).sum())
    # A step of EXACTLY half a revolution is the one case where modular arithmetic and np.unwrap
    # disagree — they break the tie in opposite directions, a whole revolution of distance apart.
    # Everything else about the two conventions is identical, so this is the only count that
    # predicts a divergence from production.
    n_tie = int((np.abs(d) == COUNTS_PER_REV // 2).sum())
    d = ((d + COUNTS_PER_REV // 2) % COUNTS_PER_REV) - COUNTS_PER_REV // 2
    unwrapped = np.concatenate([[0.0], np.cumsum(d)]).astype(float)

    pos = np.diff(t_s)
    pos = pos[pos > 0]
    if len(pos) == 0:
        raise ValueError(f"{path}: no positive timestamp diffs")
    native_fs = float(1.0 / np.median(pos))

    return {
        "t_s": t_s,
        "counts": unwrapped,
        "native_fs": native_fs,
        "duration_s": float(t_s[-1] - t_s[0]),
        "n": len(t_s),
        "n_rollover": n_rollover,
        "n_backward": n_backward,
        "n_alias": n_alias,
        "n_tie": n_tie,
    }


def _mad(x):
    med = float(np.median(x))
    return med, float(np.median(np.abs(x - med))) or 1e-12


def find_taps(t_s, counts, k=10.0, refractory_s=REFRACTORY_S):
    """
    Locate strikes as threshold crossings of |d(counts)| against a robust baseline.

    A strike is an impulse against an otherwise quiet trace, so median + k*MAD separates it without
    assuming anything about amplitude. Each crossing is refined to the sample of steepest rise, and
    crossings inside the refractory window collapse to one tap.
    """
    jerk = np.abs(np.diff(counts))
    # Encoder dropouts look exactly like strikes. Zero them before thresholding so a garbage
    # sample can never be reported as a tap (see MAX_PLAUSIBLE_COUNTS_PER_SAMPLE).
    jerk = np.where(jerk >= MAX_PLAUSIBLE_COUNTS_PER_SAMPLE, 0.0, jerk)
    med, mad = _mad(jerk)
    thresh = med + k * mad

    above = jerk > thresh
    if not above.any():
        return [], thresh

    taps = []
    i = 0
    n = len(above)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j < n and above[j]:
            j += 1
        seg = jerk[i:j]
        peak = i + int(np.argmax(seg))
        # jerk[k] spans samples k -> k+1, so the strike lands on k+1, not k. Getting this wrong
        # reports every tap one raw sample (3.7 ms at 270 Hz) early, which reads as a constant
        # positive residual and would have been quietly attributed to the clock. Caught by
        # --self-test, which is what a synthetic fixture with known truth is for.
        t_peak = float(t_s[min(peak + 1, len(t_s) - 1)])
        if not taps or (t_peak - taps[-1]) > refractory_s:
            taps.append(t_peak)
        elif jerk[peak] > thresh:
            pass  # inside refractory of the previous strike — same physical event
        i = j
    return taps, float(thresh)


# ── 86-04: the detection domain ────────────────────────────────────────────────
#
# find_taps above is the 86-03 detector. It over-triggers on the struck wheel's ring-down (10-28
# events for ~5 strikes), which is what voided 86-03's run. The strike was never hard to see — it
# was hard to see IN THAT DOMAIN. The helpers below measure the alternative and are used by
# --measure-domain; 86-04 Task 2 builds the production detector on them.
#
# find_taps must SURVIVE regardless: the ring-down fixture needs the 86-03 detector in order to
# reproduce the defect, so deleting it would delete the test.

# Threshold grid for the peak-relative sweep. Fractions of the session's own maximum, not of a
# noise floor: a MAD threshold is strictly WORSE in the velocity domain (430-542 crossings vs
# 101-302 in raw), so the win comes from peak-relative thresholding in the SMOOTHED domain, not
# from the domain alone.
FRAC_GRID = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60)

# ── the three constants 86-04 derives, and the honest status of all three ──────
#
# ⚠ THESE ARE TUNED IN-SAMPLE ON THE VOID CORPUS, NOT PRE-REGISTERED AGAINST IT. The sweep was run
# on that data before 86-04 was written, so every number below is fitted to it. What IS
# pre-registered is narrower and still load-bearing: each constant equals exactly what its stated
# rule produces from --measure-domain's output, all three freeze before 86-05's data exists, and
# the corpus is SPENT — it developed the instrument, so it can never measure the clock.
#
# Reproduce all three: `python scratch/tap_test.py --measure-domain scratch/taptest`

# Detection threshold, as a fraction of the session's own maximum |velocity|.
#
# RULE: the grid value inside the most sessions' plateaus, ties toward the smaller (a lower
# threshold cannot miss a strike a higher one found).
# MEASURED: inside all 8 of 8 sessions' plateaus; 0.25/0.30/0.35 tie with it and give an identical
# event count on every session, so the tie-break is the only thing separating them.
#
# Peak-relative, NOT median+k*MAD. A MAD threshold is strictly worse here — 430-542 crossings in
# velocity against 101-302 in raw — so the win comes from peak-relative thresholding in the
# SMOOTHED domain, not from the domain by itself.
TAP_FRAC = 0.20

# Half-width of the raw-domain search around each velocity candidate.
#
# RULE: ceil(4 * max|velocity-to-raw offset| / 0.05) * 0.05, asserted below half the smallest
# observed inter-strike gap.
# MEASURED: max|offset| 55.7 ms over 34 taps -> 0.25 s. Both assertions hold, but the second only
# by 0.01 s, and the reason is a data defect rather than a physical bound: ONE audio gap in the
# corpus is 0.52 s against a population of 2.54-4.42 s. See AUDIO_RETRIGGER_LIMIT_S. Excluding it
# the assertion clears by 1.02 s.
RAW_REFINE_WINDOW_S = 0.25

# Tolerance on the encoder-vs-audio interval-pattern check.
#
# RULE: ceil(2 * max|interval delta| / 0.01) * 0.01.
# MEASURED: max|delta| 21.7 ms -> 0.05 s. ⚠ THIN BASIS: only the 3 sessions where the velocity and
# audio counts agree can contribute, so this rests on 12 intervals. Stated rather than laundered.
#
# The check compares DIFFERENCES OF GAPS, so any constant offset between the encoder clock and the
# video clock cancels exactly. That is what makes it a legitimate encoder-side check rather than a
# disguised look at the answer it is supposed to police.
PAIR_TOL_S = 0.05

# Search half-width used BY --measure-domain ONLY, to pair a velocity candidate with its raw
# strike while the real window is still being derived. Deliberately generous: if the largest
# observed offset ever approaches it, the window is binding and the measurement is worthless —
# --measure-domain checks exactly that and says so.
DOMAIN_PROBE_WINDOW_S = 0.25

# How close a velocity candidate must be to an audio onset to count as "found it", when tallying
# which onsets the velocity domain misses. Coarse on purpose — this is a count, not a timing.
UNMATCHED_ONSET_WINDOW_S = 0.5

# Below this, two audio onsets cannot be told apart from one strike that re-triggered the audio
# detector — an echo, or the wheel's own acoustic ring. NOT a tuned number: it is twice
# audio_onsets()'s own refractory, so it is the detector's stated resolution limit and nothing
# more. Onsets inside it are FLAGGED and reported, never silently dropped: the audio count is the
# independent sensor 86-04 leans on, and an inflated one would misattribute audio over-triggering
# to velocity under-detection.
AUDIO_RETRIGGER_LIMIT_S = 2 * REFRACTORY_S


def velocity_profile(csv_path):
    """
    Decimated |velocity| from the production pipeline.

    Imports vel_acc_extraction, which --validate-timebase already depends on. Note this is the
    OPPOSITE dependency posture to read_raw, which avoids the import on purpose so that AC-2
    compares two independent implementations. Here we WANT production's own smoothing, because
    that smoothing is the thing being exploited.
    """
    sys.path.insert(0, str(REPO_ROOT))
    import vel_acc_extraction as vae  # noqa: E402

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):  # load_data prints; callers want a clean table
        df = vae.load_data(str(csv_path))
        t_dec, _dist, vel, _accel, fs = vae.run_pipeline(df, target_fs_hz=vae.TARGET_FS_HZ)
    av = np.nan_to_num(np.abs(np.asarray(vel, dtype=float)), nan=0.0)
    return np.asarray(t_dec, dtype=float), av, float(fs)


def peak_relative_events(t, y, frac):
    """
    Argmax of each contiguous run above `frac * max(y)`.

    NO REFRACTORY ARGUMENT, and none should be added: collapsing ring-down is what the velocity
    domain does for free, and reintroducing a refractory constant would put back the tuning knob
    86-04 exists to remove.
    """
    peak = float(np.max(y)) if len(y) else 0.0
    if peak <= 0:
        return []
    above = y > frac * peak
    out, i, n = [], 0, len(above)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j < n and above[j]:
            j += 1
        out.append(float(t[i + int(np.argmax(y[i:j]))]))
        i = j
    return out


def raw_jerk(counts):
    """|d(counts)| with the dropout guard find_taps applies, shared so both domains see the same
    signal. Element k spans samples k -> k+1."""
    j = np.abs(np.diff(counts))
    return np.where(j >= MAX_PLAUSIBLE_COUNTS_PER_SAMPLE, 0.0, j)


def find_tap_candidates(csv_path):
    """
    Velocity-domain candidates: reliable in COUNT, coarse in TIME.

    Do not report these times as taps — refine_on_raw does the timing. The velocity peak lags the
    raw strike by +16.3 ms pooled, and the per-session means run -5.0 to +39.4 ms; against B1's
    33 ms bar, and varying session to session so it would not cancel as a constant, timing here
    would manufacture exactly the clock error this instrument exists to detect.
    """
    t_dec, av, _fs = velocity_profile(csv_path)
    return peak_relative_events(t_dec, av, TAP_FRAC)


def refine_on_raw(t_s, counts, t_candidate):
    """
    Time one candidate on the raw counts: argmax of |d(counts)| within RAW_REFINE_WINDOW_S.

    3.7 ms resolution with no filter anywhere in the path, which is the whole reason the timing
    lives in this domain. Returns None when the window holds no raw samples at all.

    jerk[k] spans samples k -> k+1, so the strike lands on k+1 — which is what `t_s[1:]` indexes.
    Getting this wrong reports every tap one raw sample early, a constant positive residual that
    would be quietly attributed to the clock. It is defect 1 in the protocol's Instrument status,
    found by --self-test, and it is just as easy to reintroduce here as it was in find_taps.
    """
    jerk = raw_jerk(counts)
    t_jerk = t_s[1:]
    m = (t_jerk > t_candidate - RAW_REFINE_WINDOW_S) & (t_jerk < t_candidate + RAW_REFINE_WINDOW_S)
    if not m.any():
        return None
    return float(t_jerk[m][int(np.argmax(jerk[m]))])


def detect_taps(csv_path, enc):
    """
    The 86-04 detector: find on velocity, time on raw.

    Returns (taps, offsets) where offsets[i] is the velocity-to-raw lag for taps[i], recorded so
    the +16.3 ms bias stays observable per tap instead of being silently absorbed.
    """
    taps, offsets, seen = [], [], set()
    for cand in find_tap_candidates(csv_path):
        t_raw = refine_on_raw(enc["t_s"], enc["counts"], cand)
        if t_raw is None:
            continue
        # Two candidates that refine to the SAME raw sample are the same physical strike, by
        # definition — a tap list holding one instant twice is simply wrong, and the duplicate
        # would inflate encoder_overtrigger_ratio, the very health field meant to expose
        # over-triggering. This is not a tuning knob and there is no tolerance in it: the times
        # are the identical array element or they are different strikes.
        #
        # It happens because |velocity| of an impulse that overshoots has TWO lobes, so one strike
        # can raise two runs above the cut. Real strikes are single-sided (the corpus gives one
        # velocity event per strike), but the synthetic fixture's ringing impulse is not, and it
        # doubled 10 of 12 strikes there.
        #
        # The FIRST candidate's offset is kept, not the smallest: the two lobes straddle the
        # strike, so picking the smaller |offset| would bias the reported velocity-to-raw lag
        # toward zero — and that lag is a diagnostic for exactly this kind of drift.
        if t_raw in seen:
            continue
        seen.add(t_raw)
        taps.append(t_raw)
        offsets.append(cand - t_raw)
    return taps, offsets


def longest_plateau(counts_by_frac):
    """
    Longest run of constant event count across FRAC_GRID, as a [start, end) index pair.

    Ties break toward the EARLIER (lower-fraction) run, matching the tie-break direction of the
    TAP_FRAC rule itself: a lower threshold cannot miss a strike a higher one found.
    """
    best = (0, 0)
    i, n = 0, len(counts_by_frac)
    while i < n:
        j = i
        while j < n and counts_by_frac[j] == counts_by_frac[i]:
            j += 1
        if (j - i) > (best[1] - best[0]):
            best = (i, j)
        i = j
    return best


# ── video side ─────────────────────────────────────────────────────────────────

def video_duration_s(path):
    out = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], want_bytes=False)
    return float(out.strip())


def frame_times(path):
    """Real per-frame presentation times. iOS writes variable frame rate — never assume 1/fps."""
    out = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path),
    ], want_bytes=False)
    vals = []
    for line in out.splitlines():
        line = line.strip().rstrip(",")
        if line and line != "N/A":
            vals.append(float(line))
    return np.array(vals, dtype=float)


def audio_onsets(path, k=12.0, refractory_s=REFRACTORY_S, sr=48000):
    """Onsets from a short-window energy envelope, refined back to 20% of each peak."""
    raw = _run([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-map", "a:0", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-",
    ])
    if len(raw) < 2 * sr // 10:
        raise RuntimeError(
            f"{path}: no usable audio track. The clip was recorded muted — microphone permission "
            f"must be GRANTED, or readout (a) does not exist."
        )
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0

    win = max(1, sr // 1000)  # 1 ms
    env = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode="same"))
    med, mad = _mad(env)
    thresh = med + k * mad

    above = env > thresh
    if not above.any():
        return []

    onsets = []
    i, n = 0, len(above)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j < n and above[j]:
            j += 1
        peak = i + int(np.argmax(env[i:j]))
        # Walk back to where the attack began: 20% of this peak, within 50 ms.
        floor_v = 0.2 * env[peak]
        back = max(0, peak - int(0.05 * sr))
        idx = peak
        while idx > back and env[idx] > floor_v:
            idx -= 1
        t = idx / sr
        if not onsets or (t - onsets[-1]) > refractory_s:
            onsets.append(float(t))
        i = j
    return onsets


def frame_events(path, crop=None, k=8.0, refractory_s=REFRACTORY_S, size=64):
    """
    Frame-difference events. Downscales to `size`x`size` grey so a whole clip fits in memory.

    Returns the presentation time of the FIRST frame showing the strike — biased late by up to one
    frame; the caller de-biases by half a frame.
    """
    times = frame_times(path)
    vf = []
    if crop:
        vf.append(f"crop={crop}")
    vf.append(f"scale={size}:{size}")
    vf.append("format=gray")
    raw = _run([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-vf", ",".join(vf), "-f", "rawvideo", "-",
    ])
    px = size * size
    n_frames = len(raw) // px
    if n_frames < 2:
        raise RuntimeError(f"{path}: decoded {n_frames} frames")
    frames = np.frombuffer(raw[: n_frames * px], dtype=np.uint8).reshape(n_frames, px).astype(np.float32)

    if len(times) < n_frames:
        # Fall back to a constant rate only if ffprobe gave us nothing usable.
        dur = video_duration_s(path)
        times = np.arange(n_frames) * (dur / max(1, n_frames))
    times = times[:n_frames]

    diff = np.abs(np.diff(frames, axis=0)).mean(axis=1)
    med, mad = _mad(diff)
    thresh = med + k * mad

    events = []
    above = diff > thresh
    i, n = 0, len(above)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j < n and above[j]:
            j += 1
        peak = i + int(np.argmax(diff[i:j]))
        t = float(times[peak + 1])  # diff[i] compares frame i+1 against i
        if not events or (t - events[-1]) > refractory_s:
            events.append(t)
        i = j
    return events, times


# ── the measurement ────────────────────────────────────────────────────────────

def analyze_rep(raw_path, video_path, session_start_utc_ms, video_start_phone_ms,
                mic_distance_m, crop=None, label=None, detector="86-04"):
    # video_start_phone_ms may be None: it is recorded only in the app's on-screen log, so an
    # operator can come back with clips and CSVs but without it. The END-anchored residual (B1,
    # the coach-facing number) does not use it at all, so it is still fully computable; the
    # start-anchored residual and camera warm-up are then reported as None rather than invented.
    enc = read_raw(raw_path)
    # `detector` exists ONLY so the ring-down fixture can run the same clip through both
    # instruments and assert that the repair actually changed the outcome. The field path never
    # sets it: a fixture that only demonstrates the fix would not fail if the fix regressed.
    if detector == "86-03":
        taps, _ = find_taps(enc["t_s"], enc["counts"])
        vel_offsets = [None] * len(taps)
    else:
        taps, vel_offsets = detect_taps(raw_path, enc)
    offset_by_tap = {t: o for t, o in zip(taps, vel_offsets)}

    vid_dur = video_duration_s(video_path)
    onsets = audio_onsets(video_path)
    fevents, ftimes = frame_events(video_path, crop=crop)

    fps = (len(ftimes) - 1) / (ftimes[-1] - ftimes[0]) if len(ftimes) > 2 else 30.0
    half_frame = 0.5 / fps

    end_origin = enc["duration_s"] - vid_dur
    have_start = video_start_phone_ms is not None and session_start_utc_ms is not None
    start_origin = ((float(video_start_phone_ms) - float(session_start_utc_ms)) / 1000.0
                    if have_start else None)
    warm_up = (end_origin - start_origin) if have_start else None

    sound_delay = mic_distance_m / SPEED_OF_SOUND_MS

    # PASS 1 — pair each audio onset with an encoder tap and a frame event.
    #
    # The residual comes from the FRAME readout alone (see the module docstring). `av_offset` --
    # the session's median audio-minus-frame -- is used only to centre the per-tap cross-check and
    # as a diagnostic, so a container offset can never leak into the measured answer.
    pairs = []
    for onset in onsets:
        t_audio = onset - sound_delay
        # Coarse pairing uses the end-anchored origin, which is right to well within a second even
        # if its residual is what we are measuring. A mispair fails loudly rather than silently.
        approx_session = t_audio + end_origin
        if not taps:
            continue
        near = min(taps, key=lambda tp: abs(tp - approx_session))
        if abs(near - approx_session) > MATCH_WINDOW_S:
            pairs.append({"onset": onset, "t_audio": t_audio, "enc": None, "fr": None})
            continue
        # De-bias the frame readout: the first frame showing the strike sits uniformly in
        # (0, 1/fps] after it, so its expected value is half a frame late.
        fr = min(fevents, key=lambda fe: abs(fe - onset)) if fevents else None
        pairs.append({"onset": onset, "t_audio": t_audio, "enc": near,
                      "fr": fr, "fr_est": (fr - half_frame) if fr is not None else None})

    diffs = [p["t_audio"] - p["fr_est"] for p in pairs
             if p["enc"] is not None and p.get("fr_est") is not None]
    if len(diffs) >= 3:
        av_offset = float(np.median(diffs))
        av_estimated = True
    else:
        av_offset = 0.0
        av_estimated = False

    # ── ENCODER-SIDE CHECKS (86-04) ───────────────────────────────────────────────────────────
    # 86-03's only rejection rule compared audio against frames — two readouts of the VIDEO — so an
    # ENCODER mispair left both in perfect agreement and was marked ACCEPTED carrying 180-320 ms.
    # Both checks below look at the encoder side, and neither reads a residual.

    # (a) CONTENTION. Two audio onsets selecting the same encoder tap means at least one is wrong.
    # One-to-one pairing is a structural property, not a statistical one, so both are rejected
    # rather than the "better" one being kept — choosing between them would need the residual.
    # `detector == "86-03"` selects the whole 86-03 INSTRUMENT, not merely its detector: that
    # instrument had no encoder-side check at all, and leaving these on would let the repair catch
    # the defect the fixture is trying to reproduce.
    checks_on = detector != "86-03"

    used = {}
    for p in pairs:
        if p["enc"] is not None:
            used[p["enc"]] = used.get(p["enc"], 0) + 1
    contended = {t for t, n in used.items() if n > 1} if checks_on else set()

    # (b) INTERVAL PATTERN runs in PASS 3, on the taps that survived PASS 2 — see there for why the
    # ordering is load-bearing.

    # PASS 2 — residuals on the frame timeline, rejection on scatter about the session's own offset.
    records = []
    for p in pairs:
        rec = {"video_time_s": round(p["onset"], 6)}
        if p["enc"] is None:
            rec.update(status="UNMATCHED",
                       reason=f"no encoder tap within {MATCH_WINDOW_S}s")
            records.append(rec)
            continue
        if p.get("fr_est") is None:
            rec.update(status="REJECTED", reason="no frame event to cross-check against",
                       encoder_time_s=round(p["enc"], 6))
            records.append(rec)
            continue

        scatter = (p["t_audio"] - p["fr_est"]) - av_offset
        vo = offset_by_tap.get(p["enc"])
        rec.update({
            "video_time_sound_corrected_s": round(p["t_audio"], 6),
            "frame_time_s": round(p["fr"], 6),
            "frame_estimate_s": round(p["fr_est"], 6),
            "audio_minus_frame_s": round(p["t_audio"] - p["fr_est"], 6),
            "scatter_about_av_offset_s": round(scatter, 6),
            "encoder_time_s": round(p["enc"], 6),
            # Recorded, never applied: the velocity candidate's lag behind the raw strike. If this
            # ever collapses toward zero the timing has silently migrated into the wrong domain.
            "vel_to_raw_offset_ms": None if vo is None else round(vo * 1000, 3),
            "residual_end_anchored_s": round((p["fr_est"] + end_origin) - p["enc"], 6),
            "residual_start_anchored_s": (round((p["fr_est"] + start_origin) - p["enc"], 6)
                                          if have_start else None),
        })
        if p["enc"] in contended:
            rec["status"] = "REJECTED"
            rec["reason"] = (f"contention: encoder tap at {p['enc']:.3f}s is the nearest tap for "
                             f"{used[p['enc']]} audio onsets, so at least one pairing is wrong "
                             f"and choosing between them would need the residual")
        elif abs(scatter) > GROSS_DISAGREEMENT_FRAMES / fps:
            rec["status"] = "REJECTED"
            rec["reason"] = (f"readouts disagree by {scatter * 1000:+.1f} ms about this "
                             f"session's A/V offset — beyond {GROSS_DISAGREEMENT_FRAMES} frames "
                             f"({GROSS_DISAGREEMENT_FRAMES / fps * 1000:.1f} ms), so this tap is "
                             f"mispaired or its strike was missed in one stream")
        else:
            rec["status"] = "ACCEPTED"
        records.append(rec)

    # PASS 3 — the interval-pattern check, on the taps PASS 2 left standing.
    #
    # ⚠ THE ORDERING IS LOAD-BEARING, and running this earlier is a real defect — caught by the
    # standing AC-4 desync gate, which went from 11 accepted / 1 rejected to 0 / 12. This check
    # compares ENCODER gaps against AUDIO gaps, so a bad AUDIO onset fails it just as loudly as a
    # bad encoder tap, and because the verdict is session-wide one bad onset would condemn every
    # honest tap beside it. PASS 2's scatter check is precisely the thing that identifies an
    # untrustworthy audio readout, so running it first leaves this check looking at a clean audio
    # sequence — after which any disagreement really is encoder-side, which is what it is for.
    #
    # A difference of differences, so any constant offset between the two clocks cancels exactly.
    # It cannot be gamed by the quantity being measured, and it reads no residual.
    seq = [r for r in records if r.get("status") == "ACCEPTED"]
    interval_max_delta = None
    if len(seq) >= 2:
        enc_gaps = np.diff([r["encoder_time_s"] for r in seq])
        aud_gaps = np.diff([r["video_time_sound_corrected_s"] for r in seq])
        interval_max_delta = float(np.max(np.abs(enc_gaps - aud_gaps)))
    interval_failed = (checks_on and interval_max_delta is not None
                       and interval_max_delta > PAIR_TOL_S)
    if interval_failed:
        for r in seq:
            r["status"] = "REJECTED"
            r["reason"] = (f"interval pattern: encoder gaps disagree with audio gaps by up to "
                           f"{interval_max_delta * 1000:.1f} ms, beyond PAIR_TOL_S "
                           f"({PAIR_TOL_S * 1000:.0f} ms) — the two sensors are not describing "
                           f"the same sequence of strikes")

    accepted = [r for r in records if r.get("status") == "ACCEPTED"]
    # Health metric, not a filter: honest taps spread over exactly one frame, because the frame
    # readout quantises a uniformly-distributed strike time. Much more than that means the two
    # streams are not describing the same events.
    sc = [r["scatter_about_av_offset_s"] for r in accepted
          if r.get("scatter_about_av_offset_s") is not None]
    spread_frames = (max(sc) - min(sc)) * fps if len(sc) >= 2 else None
    return {
        "label": label or Path(raw_path).stem,
        "raw": str(raw_path),
        "video": str(video_path),
        "session_start_utc_ms": session_start_utc_ms,
        "video_start_phone_ms": video_start_phone_ms,
        "mic_distance_m": mic_distance_m,
        "sound_delay_ms": round(sound_delay * 1000, 3),
        "device_duration_s": round(enc["duration_s"], 6),
        "video_duration_s": round(vid_dur, 6),
        "native_fs_hz": round(enc["native_fs"], 3),
        "fps": round(fps, 4),
        "half_frame_ms": round(half_frame * 1000, 3),
        "end_anchored_origin_s": round(end_origin, 6),
        "start_anchored_origin_s": round(start_origin, 6) if have_start else None,
        "camera_warm_up_s": round(warm_up, 6) if have_start else None,
        "detector": detector,
        "n_encoder_taps": len(taps),
        "n_audio_onsets": len(onsets),
        "n_frame_events": len(fevents),
        # The number that would have made 86-03's defect obvious on session 1 instead of at
        # aggregation: 28 encoder events against 5 onsets is 5.6.
        "encoder_overtrigger_ratio": round(len(taps) / max(1, len(onsets)), 3),
        "encoder_overtrigger_suspicious": bool(len(taps) / max(1, len(onsets)) > 2.0),
        "interval_pattern_max_delta_s": (round(interval_max_delta, 6)
                                         if interval_max_delta is not None else None),
        "interval_pattern_failed": bool(interval_failed),
        "n_contended_taps": len(contended),
        "vel_to_raw_offset_ms": [round(o * 1000, 3) for o in vel_offsets if o is not None],
        "readout_spread_frames": round(spread_frames, 3) if spread_frames is not None else None,
        "readout_spread_suspicious": bool(spread_frames is not None and spread_frames > 1.2),
        "av_offset_ms": round(av_offset * 1000, 3),
        "av_offset_estimated": av_estimated,
        "av_offset_suspicious": bool(abs(av_offset) > 1.0 / fps),
        "n_accepted": len(accepted),
        "n_rejected": len(records) - len(accepted),
        "taps": records,
    }


def summarize(reps):
    """Pooled statistics. Every number carries its rep count; SE is reported, never hidden."""
    def stats(vals):
        if not vals:
            return None
        a = np.array(vals, dtype=float)
        n = len(a)
        sd = float(a.std(ddof=1)) if n > 1 else float("nan")
        return {
            "n": n,
            "mean_ms": round(float(a.mean()) * 1000, 3),
            "sd_ms": round(sd * 1000, 3) if n > 1 else None,
            "se_ms": round(sd / math.sqrt(n) * 1000, 3) if n > 1 else None,
        }

    acc = [t for r in reps for t in r["taps"] if t.get("status") == "ACCEPTED"]
    total = sum(len(r["taps"]) for r in reps)
    return {
        "n_sessions": len(reps),
        "n_taps_total": total,
        "n_accepted": len(acc),
        "acceptance_rate": round(len(acc) / total, 4) if total else None,
        "residual_end_anchored": stats([t["residual_end_anchored_s"] for t in acc]),
        "residual_start_anchored": stats([t["residual_start_anchored_s"] for t in acc
                                          if t.get("residual_start_anchored_s") is not None]),
        "audio_minus_frame": stats([t["audio_minus_frame_s"] for t in acc
                                    if t.get("audio_minus_frame_s") is not None]),
        "scatter_about_av_offset": stats([t["scatter_about_av_offset_s"] for t in acc
                                          if t.get("scatter_about_av_offset_s") is not None]),
        "av_offset_ms_per_session": [r["av_offset_ms"] for r in reps],
        "camera_warm_up": stats([r["camera_warm_up_s"] for r in reps
                                 if r.get("camera_warm_up_s") is not None]),
        "per_session_end_anchored_mean_ms": [
            round(float(np.mean([t["residual_end_anchored_s"] for t in r["taps"]
                                 if t.get("status") == "ACCEPTED"])) * 1000, 3)
            if r["n_accepted"] else None
            for r in reps
        ],
    }


# ── AC-2: the raw time base against the production pipeline ────────────────────

def _crossing_time(t, y, level):
    """First upward crossing of `level`, linearly interpolated between samples."""
    idx = np.nonzero(y >= level)[0]
    if len(idx) == 0:
        return None
    i = int(idx[0])
    if i == 0:
        return float(t[0])
    y0, y1 = float(y[i - 1]), float(y[i])
    if y1 == y0:
        return float(t[i])
    frac = (level - y0) / (y1 - y0)
    return float(t[i - 1] + frac * (t[i] - t[i - 1]))


def validate_timebase(raw_dir, limit=None, verbose=True):
    """
    AC-2 — grounded on real data, not on self-generated fixtures.

    PLAN AMENDMENT, recorded rather than quietly applied. The PLAN's AC-2 compared this reader's
    landmark against a coach-marked `dive_start_s` at a one-raw-sample tolerance. That bar is not
    achievable and the AC was wrong to ask for it: a coach's dive mark is a human judgement about
    where a race begins, not a threshold crossing, so the two can differ by far more than 3.7 ms
    without anything being broken.

    A first attempt replaced it with a landmark — the first crossing of a distance level — compared
    between this reader and the decimated pipeline output. That failed too, for a reason worth
    keeping: where the distance curve is FLAT (a breaststroke glide, the drift into the wall) a
    tiny vertical difference becomes a huge horizontal one, and the check measured plateau geometry
    rather than the time base. Those crossings are reported below as a DIAGNOSTIC, because they are
    the direct evidence for reading raw rather than processed.

    What AC-2 actually needs to catch is an off-by-one or a wrong epoch in the raw -> session-time
    conversion, which would bias every rep by a constant. That is testable EXACTLY, sample by
    sample, against production: `vel_acc_extraction.load_data` builds the same time base by plain
    subtraction where this module accumulates modular steps, and `unwrap_angle` +
    `counts_to_distance` build the same distance with np.unwrap on radians where this module uses
    modular integer counts. The implementations share no arithmetic, so agreement is meaningful.
    """
    sys.path.insert(0, str(REPO_ROOT))
    import vel_acc_extraction as vae  # noqa: E402

    files = sorted(Path(raw_dir).glob("*.csv"))
    if limit:
        files = files[:limit]
    if not files:
        raise SystemExit(f"no CSVs in {raw_dir}")

    rows, skipped, diag = [], [], []
    for f in files:
        try:
            enc = read_raw(f)
            df = vae.load_data(str(f))
        except Exception as exc:  # noqa: BLE001 — a bench file that cannot load is not a failure
            skipped.append((f.name, str(exc).split("\n")[0][:70]))
            continue

        prod_t = df["time_s"].to_numpy(dtype=float)
        if len(prod_t) != len(enc["t_s"]):
            skipped.append((f.name, f"row counts differ ({len(prod_t)} vs {len(enc['t_s'])})"))
            continue

        _, prod_counts = vae.unwrap_angle(df)
        prod_dist = vae.counts_to_distance(prod_counts, vae.METERS_PER_COUNT)

        mine = enc["counts"] * (math.pi * WHEEL_DIAMETER_M / COUNTS_PER_REV)
        mine = mine - mine[0]
        if float(mine[-1]) < 0:
            mine = -mine  # the same backwards-wheel rule production applies

        dt_ms = float(np.max(np.abs(enc["t_s"] - prod_t))) * 1000.0
        dd_mm = float(np.max(np.abs(mine - prod_dist))) * 1000.0
        sample_ms = 1000.0 / enc["native_fs"]
        rows.append({
            "file": f.name, "n": enc["n"], "sample_ms": sample_ms,
            "dt_ms": dt_ms, "dd_mm": dd_mm,
            "n_rollover": enc["n_rollover"], "n_backward": enc["n_backward"],
            "n_alias": enc["n_alias"], "n_tie": enc["n_tie"],
        })

        # Diagnostic only: how far the DECIMATED trace can sit from raw in time. This is the
        # evidence for the plan's "read raw, not processed" decision.
        try:
            t_dec, dist_dec, _, _, _ = vae.run_pipeline(df)
            span = float(np.nanmax(dist_dec) - np.nanmin(dist_dec))
            if span >= 0.5:
                worst = 0.0
                for frac in (0.25, 0.50, 0.75):
                    level = float(np.nanmin(dist_dec)) + frac * span
                    a = _crossing_time(enc["t_s"], mine, level)
                    b = _crossing_time(np.asarray(t_dec), np.asarray(dist_dec), level)
                    if a is not None and b is not None:
                        worst = max(worst, abs(a - b) * 1000.0)
                diag.append((f.name, worst))
        except Exception:  # noqa: BLE001 — the diagnostic must never fail the check
            pass

    if not rows:
        raise SystemExit("no files compared — nothing to validate")

    TOL_MS, TOL_MM = 1e-3, 1e-3   # float noise; these are the same arithmetic by two routes
    # ONLY an exact half-revolution tie predicts a divergence — the two unwrap conventions break
    # that tie in opposite directions, a whole revolution of distance apart. Aliased-but-not-tied
    # steps and backward timestamps are data-quality facts worth reporting, but both conventions
    # handle them identically, so excluding those files would throw away most of the evidence for
    # no reason. (A first cut did exactly that and dropped 27 of 40 files that in fact agreed to
    # the last floating-point digit.)
    dirty = [r for r in rows if r["n_tie"] > 0]
    clean = [r for r in rows if r["n_tie"] == 0]
    bad = [r for r in clean if r["dt_ms"] > TOL_MS or r["dd_mm"] > TOL_MM]

    if verbose:
        print(f"\n{'file':<46} {'rows':>7} {'max dt ms':>11} {'max dd mm':>11}  ok")
        print("-" * 88)
        for r in sorted(rows, key=lambda x: -max(x["dt_ms"], x["dd_mm"]))[:12]:
            if r in dirty:
                ok = "DIRTY"
            else:
                ok = "OK" if (r["dt_ms"] <= TOL_MS and r["dd_mm"] <= TOL_MM) else "FAIL"
            note = ""
            if r["n_backward"]:
                note += f" back={r['n_backward']}"
            if r["n_alias"]:
                note += f" alias={r['n_alias']}"
            if r["n_tie"]:
                note += f" tie={r['n_tie']}"
            if r["n_rollover"]:
                note += f" rollover={r['n_rollover']}"
            print(f"{r['file'][:46]:<46} {r['n']:>7} {r['dt_ms']:>11.6f} "
                  f"{r['dd_mm']:>11.6f}  {ok}{note}")
        print(f"  ... {len(rows)} files compared, worst 12 shown")
        if skipped:
            print(f"\nskipped {len(skipped)}:")
            for name, why in skipped[:8]:
                print(f"  {name}: {why}")

        print(f"\nAC-2: {len(clean) - len(bad)}/{len(clean)} clean files agree with production "
              f"to within {TOL_MS} ms and {TOL_MM} mm, SAMPLE BY SAMPLE")
        if clean:
            print(f"  worst time-base delta {max(r['dt_ms'] for r in clean):.6f} ms · "
                  f"worst distance delta {max(r['dd_mm'] for r in clean):.6f} mm · "
                  f"raw sample period ~{np.mean([r['sample_ms'] for r in clean]):.2f} ms")
        n_alias_files = sum(1 for r in rows if r["n_alias"] > 0)
        n_back_files = sum(1 for r in rows if r["n_backward"] > 0)
        print(f"  data quality across all {len(rows)} files: aliased count steps in "
              f"{n_alias_files}, backward timestamps in {n_back_files}, "
              f"uint32 rollovers in {sum(1 for r in rows if r['n_rollover'] > 0)}")
        if dirty:
            print(f"  {len(dirty)} file(s) excluded as DIRTY, each for a stated data defect:")
            for r in dirty:
                why = []
                if r["n_backward"]:
                    why.append(f"{r['n_backward']} backward timestamp step(s)")
                if r["n_tie"]:
                    why.append(f"{r['n_tie']} count step(s) of EXACTLY half a revolution")
                if r["n_alias"]:
                    why.append(f"{r['n_alias']} aliased step(s) total")
                if r["n_rollover"]:
                    why.append(f"{r['n_rollover']} genuine uint32 rollover(s)")
                print(f"    {r['file']}: {'; '.join(why)} "
                      f"-> dd={r['dd_mm']:.1f} mm (one revolution is 188.5 mm)")
            print("  Excluded because the two unwrap conventions provably differ there, not")
            print("  because either is wrong. A file like this is unfit to carry a tap test.")

        dirty_names = {r["file"] for r in dirty}
        diag = [d for d in diag if d[0] not in dirty_names]
        if diag:
            worst = sorted(diag, key=lambda d: -d[1])
            vals = np.array([d[1] for d in diag])
            print(f"\nDIAGNOSTIC (no verdict) — raw vs DECIMATED landmark crossing, {len(diag)} files:")
            print(f"  median {np.median(vals):.1f} ms · worst {worst[0][1]:.1f} ms ({worst[0][0]})")
            print("  The decimated trace can sit hundreds of ms from raw in TIME wherever the")
            print("  distance curve is flat — a glide, or the drift into the wall. This is why the")
            print("  tap readout comes off the raw CSV and not the processed trace.")

        print("\nNOTE: this validates the raw time base and the count->distance mapping against an")
        print("independent implementation. It does NOT validate the tap detector — a dive is a")
        print("sustained acceleration and a tap is an impulse. Do not quote it as more than that.")

    return (not bad), rows, skipped


# ── 86-04 AC-1: measure the detection domain ───────────────────────────────────

def measure_domain(tap_dir, verbose=True):
    """
    86-04 AC-1 — measure which domain the strike is visible in, and what the three derivation
    rules produce from that measurement.

    READ-ONLY. Touches nothing but stdout. Changes no constant: 86-04's Task 1 commits this
    measurement BEFORE Task 2 moves anything, and that ordering is not recoverable after the fact.

    ⚠ THIS IS IN-SAMPLE AND THE PLAN SAYS SO. The sweep was run on the void corpus before the plan
    was written, so the constants it produces are TUNED on this data, not pre-registered against
    it. What is pre-registered is that each constant must equal what its rule produces here, and
    that all of them freeze before 86-05's data exists. This corpus is spent: it develops the
    instrument, so it can never measure the clock.

    Reads each session's *.csv and its *.json sidecar (audio onsets from the void run, which are
    the independent sensor). Never opens a video.
    """
    files = sorted(Path(tap_dir).glob("*.csv"))
    if not files:
        raise SystemExit(f"no CSVs in {tap_dir}")

    sessions = []
    for csv in files:
        enc = read_raw(csv)
        t_dec, av, fs = velocity_profile(csv)
        jerk = raw_jerk(enc["counts"])
        t_jerk = enc["t_s"][1:]  # jerk[k] spans k -> k+1, so it is timed at k+1

        side = csv.with_suffix(".json")
        onsets, sound_delay, end_origin = [], 0.0, None
        if side.exists():
            j = json.loads(side.read_text(encoding="utf-8"))
            onsets = sorted(float(r["video_time_s"]) for r in j.get("taps", []))
            sound_delay = float(j.get("sound_delay_ms") or 0.0) / 1000.0
            end_origin = j.get("end_anchored_origin_s")
        sessions.append({
            "name": csv.stem, "t_dec": t_dec, "av": av, "fs": fs,
            "t_jerk": t_jerk, "jerk": jerk,
            "onsets": onsets, "sound_delay": sound_delay,
            "end_origin": None if end_origin is None else float(end_origin),
        })

    # ── block 1: the sweep, both domains ──
    if verbose:
        print("\n=== 1. EVENT COUNT vs PEAK-RELATIVE THRESHOLD ===")
        print("Fractions are of each session's OWN maximum. Audio onsets are the independent count.")
        print(f"\n{'session':<14}" + "".join(f"{f:>6.0%}" for f in FRAC_GRID)
              + f"{'audio':>8}  {'plateau':>13}")
        print("-" * 88)

    membership = {f: 0 for f in FRAC_GRID}
    for s in sessions:
        counts = [len(peak_relative_events(s["t_dec"], s["av"], f)) for f in FRAC_GRID]
        a, b = longest_plateau(counts)
        s["vel_counts"] = counts
        s["plateau"] = (a, b)
        for i in range(a, b):
            membership[FRAC_GRID[i]] += 1
        if verbose:
            print(f"{s['name']:<14}" + "".join(f"{c:6d}" for c in counts)
                  + f"{len(s['onsets']):8d}"
                  + f"   {FRAC_GRID[a]:.0%}-{FRAC_GRID[b - 1]:.0%} @{counts[a]}")

    if verbose:
        print(f"\n{'(raw jerk)':<14}" + "".join(f"{f:>6.0%}" for f in FRAC_GRID) + "   for contrast")
        print("-" * 88)
        for s in sessions:
            rc = [len(peak_relative_events(s["t_jerk"], s["jerk"], f)) for f in FRAC_GRID]
            a, b = longest_plateau(rc)
            print(f"{s['name']:<14}" + "".join(f"{c:6d}" for c in rc)
                  + f"{'':8}   {FRAC_GRID[a]:.0%}-{FRAC_GRID[b - 1]:.0%} @{rc[a]}")

    best_n = max(membership.values())
    tap_frac = min(f for f in FRAC_GRID if membership[f] == best_n)  # ties -> smaller
    if verbose:
        print("\n  RULE: the grid value inside the most sessions' plateaus; ties -> the smaller.")
        print("  in-plateau counts: "
              + "  ".join(f"{f:.0%}={membership[f]}" for f in FRAC_GRID))
        print(f"  -> TAP_FRAC = {tap_frac:.2f}  (inside {best_n} of {len(sessions)} plateaus)")

    # ── block 2: timing offsets, velocity peak vs raw strike ──
    pooled, per_session, min_gap, all_gaps = [], [], None, []
    for s in sessions:
        ev = peak_relative_events(s["t_dec"], s["av"], tap_frac)
        s["vel_events"] = ev
        deltas = []
        for te in ev:
            m = (s["t_jerk"] > te - DOMAIN_PROBE_WINDOW_S) & (s["t_jerk"] < te + DOMAIN_PROBE_WINDOW_S)
            if not m.any():
                continue
            tr = float(s["t_jerk"][m][int(np.argmax(s["jerk"][m]))])
            deltas.append((te - tr) * 1000.0)
        per_session.append((s["name"], deltas))
        pooled += deltas
        # Onsets whose gap is inside the audio detector's own resolution limit cannot be told
        # apart from a re-trigger of a single strike. Recorded per session for the report below.
        s["flagged_onsets"] = set()
        for a, b in zip(s["onsets"], s["onsets"][1:]):
            gap = b - a
            all_gaps.append((s["name"], a, b, gap))
            if gap < AUDIO_RETRIGGER_LIMIT_S:
                s["flagged_onsets"].add(b)
            min_gap = gap if min_gap is None else min(min_gap, gap)

    if verbose:
        print("\n=== 2. TIMING: velocity peak minus raw strike, at TAP_FRAC ===")
        print("This is why detection and timing live in different domains.")
        print(f"\n{'session':<14}{'n':>4}{'mean ms':>10}{'sd':>8}{'min':>9}{'max':>9}")
        print("-" * 88)
        for name, d in per_session:
            if not d:
                print(f"{name:<14}{0:>4}{'-':>10}")
                continue
            a = np.array(d)
            print(f"{name:<14}{len(a):>4}{a.mean():>+10.1f}{a.std(ddof=0):>8.1f}"
                  f"{a.min():>+9.1f}{a.max():>+9.1f}")

    p = np.array(pooled) if pooled else np.array([0.0])
    max_off_s = float(np.max(np.abs(p))) / 1000.0
    raw_window = math.ceil(4 * max_off_s / 0.05) * 0.05
    window_binding = max_off_s > 0.8 * DOMAIN_PROBE_WINDOW_S
    gap_ok = min_gap is not None and raw_window < min_gap / 2.0

    if verbose:
        fs0 = sessions[0]["fs"]
        print(f"{'POOLED':<14}{len(p):>4}{p.mean():>+10.1f}{p.std(ddof=0):>8.1f}"
              f"{p.min():>+9.1f}{p.max():>+9.1f}"
              f"   | B1 bar 33 ms | 1 decimated sample {1000.0 / fs0:.1f} ms")
        print("\n  RULE: RAW_REFINE_WINDOW_S = ceil(4 * max|offset| / 0.05) * 0.05,")
        print("        asserted below half the smallest observed inter-strike gap.")
        print(f"  max|offset| = {max_off_s * 1000:.1f} ms  ->  RAW_REFINE_WINDOW_S = {raw_window:.2f} s")
        print(f"  ASSERT probe window not binding: max|offset| is "
              f"{max_off_s / DOMAIN_PROBE_WINDOW_S:.0%} of the {DOMAIN_PROBE_WINDOW_S} s probe "
              f"window -> {'FAIL (measurement worthless)' if window_binding else 'OK'}")
        print(f"  ASSERT {raw_window:.2f} < min_gap/2 = "
              f"{'n/a' if min_gap is None else f'{min_gap / 2:.2f}'} s "
              f"(smallest observed inter-strike gap "
              f"{'n/a' if min_gap is None else f'{min_gap:.2f}'} s) -> "
              f"{'OK' if gap_ok else 'FAIL'}")

    # The gap population itself, because the assertion above passed by 0.01 s and the reader is
    # entitled to know why it was that tight rather than being handed a bare OK.
    flagged = [g for g in all_gaps if g[3] < AUDIO_RETRIGGER_LIMIT_S]
    if verbose and all_gaps:
        gv = np.array([g[3] for g in all_gaps])
        clean = gv[gv >= AUDIO_RETRIGGER_LIMIT_S]
        print(f"\n  AUDIO ONSET GAPS ({len(gv)} across {len(sessions)} sessions): "
              f"min {gv.min():.2f}  median {np.median(gv):.2f}  max {gv.max():.2f} s "
              f"(protocol asks ~3 s)")
        if flagged:
            print(f"  !! {len(flagged)} gap(s) INSIDE the audio detector's own resolution limit "
                  f"({AUDIO_RETRIGGER_LIMIT_S:.1f} s = 2x its refractory):")
            for name, a, b, gap in flagged:
                print(f"       {name}: onsets {a:.3f} and {b:.3f} s are {gap:.2f} s apart")
            print("     These CANNOT be told apart from one strike re-triggering the audio")
            print("     detector (an echo, or the wheel's own acoustic ring). So the audio onset")
            print("     count is NOT clean ground truth, and part of the velocity-vs-audio count")
            print("     mismatch below is audio OVER-triggering, not velocity under-detection.")
            print(f"     Excluding them the smallest gap is {clean.min():.2f} s, and the window")
            print(f"     assertion would clear by {clean.min() / 2 - raw_window:.2f} s instead of "
                  f"{min_gap / 2 - raw_window:.2f} s.")
            print("     NOT ACTED ON. 86-04's rule is evaluated on the gaps as observed, and it")
            print("     PASSES as written. This is disclosure, not a correction.")

    # ── block 3: interval pattern, encoder vs audio ──
    # Differences of gaps, so ANY constant clock offset between the two sensors cancels exactly.
    # That is what makes this a legitimate encoder-side check and not a look at the answer.
    ivals, n_sess_matched = [], 0
    if verbose:
        print("\n=== 3. INTERVAL PATTERN: encoder gaps vs audio gaps (clock-offset-free) ===")
        print(f"\n{'session':<14}{'vel':>5}{'audio':>7}{'max |delta| ms':>17}{'mean':>9}")
        print("-" * 88)
    for s in sessions:
        ev, on = s["vel_events"], s["onsets"]
        if len(ev) == len(on) and len(ev) > 1:
            d = (np.diff(ev) - np.diff(on)) * 1000.0
            ivals += list(np.abs(d))
            n_sess_matched += 1
            if verbose:
                print(f"{s['name']:<14}{len(ev):>5}{len(on):>7}"
                      f"{np.max(np.abs(d)):>17.1f}{d.mean():>+9.1f}")
        elif verbose:
            print(f"{s['name']:<14}{len(ev):>5}{len(on):>7}"
                  f"{'COUNT MISMATCH - no pattern test':>34}")

    max_ival_s = (max(ivals) / 1000.0) if ivals else 0.0
    pair_tol = math.ceil(2 * max_ival_s / 0.01) * 0.01
    if verbose:
        print("\n  RULE: PAIR_TOL_S = ceil(2 * max|interval delta| / 0.01) * 0.01")
        print(f"  max|delta| = {max_ival_s * 1000:.1f} ms  ->  PAIR_TOL_S = {pair_tol:.2f} s")
        print(f"  !! THIN BASIS: {n_sess_matched} of {len(sessions)} sessions, "
              f"{len(ivals)} intervals. Reported as such, not laundered into confidence.")

    # ── block 4: which onsets the velocity domain misses, and whether anything was there ──
    if verbose:
        print("\n=== 4. UNMATCHED AUDIO ONSETS: was there a strike the velocity domain missed? ===")
        print("Velocity amplitude at each unmatched onset, as a fraction of the session peak.")
        print("A soft-but-real strike sits a few percent up; nothing-there sits at the floor.")
        print(f"\n{'session':<14}{'onset v_s':>11}{'session s':>11}{'amp/peak':>10}   reading")
        print("-" * 88)
    n_unmatched, n_total_onsets, n_unmatched_flagged = 0, 0, 0
    for s in sessions:
        n_total_onsets += len(s["onsets"])
        if s["end_origin"] is None:
            continue
        peak = float(np.max(s["av"])) or 1.0
        for onset in s["onsets"]:
            t_sess = onset - s["sound_delay"] + s["end_origin"]
            if s["vel_events"] and min(abs(e - t_sess) for e in s["vel_events"]) <= UNMATCHED_ONSET_WINDOW_S:
                continue
            n_unmatched += 1
            is_flagged = onset in s["flagged_onsets"]
            n_unmatched_flagged += int(is_flagged)
            m = (s["t_dec"] > t_sess - 0.15) & (s["t_dec"] < t_sess + 0.15)
            amp = float(np.max(s["av"][m])) / peak if m.any() else float("nan")
            if verbose:
                reading = ("no local velocity window" if math.isnan(amp)
                           else "soft strike, real" if amp >= 0.05
                           else "at the noise floor - not a strike")
                if is_flagged:
                    reading += "  [audio re-trigger suspect]"
                print(f"{s['name']:<14}{onset:>11.3f}{t_sess:>11.3f}{amp:>10.1%}   {reading}")
    if verbose:
        if not n_unmatched:
            print("  (none)")
        print(f"\n  {n_unmatched} of {n_total_onsets} audio onsets unmatched at TAP_FRAC = "
              f"{tap_frac:.2f}  ->  ceiling {1 - n_unmatched / max(1, n_total_onsets):.0%} "
              f"acceptance, against B3's 90%")
        if n_unmatched_flagged:
            print(f"  of which {n_unmatched_flagged} sit inside the audio detector's resolution")
            print("  limit, so they may never have been separate strikes at all.")
        print("  86-04 PREDICTED this before the re-run. Under-detection is the SAFE failure: a")
        print("  missed strike leaves its onset unmatched and REJECTED, visible rather than")
        print("  laundered into a confident wrong answer the way 86-03's over-triggering was.")
        print("\n" + "=" * 88)
        print("CONSTANTS THE RULES PRODUCE (86-04 Task 2 must enter exactly these):")
        print(f"  TAP_FRAC            = {tap_frac:.2f}")
        print(f"  RAW_REFINE_WINDOW_S = {raw_window:.2f}"
              f"   [{'OK' if (gap_ok and not window_binding) else 'ASSERTION FAILED'}]")
        print(f"  PAIR_TOL_S          = {pair_tol:.2f}")
        print("=" * 88)

    ok = bool(gap_ok and not window_binding)
    return ok, {"tap_frac": tap_frac, "raw_refine_window_s": raw_window,
                "pair_tol_s": pair_tol, "n_unmatched": n_unmatched,
                "n_onsets": n_total_onsets, "min_gap_s": min_gap,
                "max_offset_ms": max_off_s * 1000, "max_interval_delta_ms": max_ival_s * 1000,
                "n_interval_sessions": n_sess_matched, "n_intervals": len(ivals)}


# ── AC-1 / AC-3 / AC-4: synthetic fixtures ─────────────────────────────────────

def _make_raw_csv(path, taps_s, fs=270.0, duration_s=30.0, ringdown=None, baseline_counts_s=200.0):
    """
    `ringdown` is a list of (delay_s, amplitude_fraction) re-triggers appended after each strike —
    the wheel still rocking seconds after being hit. Absent, the fixture is a clean impulse train.

    The fractions matter as much as the delays. Real re-triggers cross the 86-03 detector's
    median+10*MAD floor (which sits at ~1 count on a quiet trace) while staying BELOW 20% of the
    strike's velocity excursion — which is exactly why the raw domain sees 10-28 events for ~5
    strikes and the velocity domain sees 5. A fixture outside that regime would not model the
    defect: too loud and the repair fails too, too quiet and neither instrument notices.

    `baseline_counts_s` is the steady rotation underneath, and a ring-down fixture must lower it.
    Measured: at the default 200 counts/s the baseline is 8.5% of the session's peak |velocity|, so
    an amplitude fraction f arrives at the detector as roughly 0.085 + 0.85f — planting 0.15 lands
    at 0.208, over the 0.20 cut, and the re-triggers become visible to the repaired detector for a
    reason that has nothing to do with ring-down. The tap corpus is a wheel on a DESK, near
    stationary between strikes, so a low baseline is also the more faithful model of it.
    """
    n = int(duration_s * fs) + 1  # +1 so (n-1)/fs is EXACTLY duration_s
    t = np.arange(n) / fs
    counts = baseline_counts_s * t  # a slow steady rotation underneath

    def _impulse(i, amp):
        if 0 <= i < n - 12:
            # A strike: a sharp jerk that rings down over ~12 samples.
            counts[i:i + 12] += amp * np.exp(-np.arange(12) / 2.5) * np.cos(np.arange(12) * 1.1)

    for tap in taps_s:
        _impulse(int(round(tap * fs)), 140.0)
        for delay_s, frac in (ringdown or ()):
            _impulse(int(round((tap + delay_s) * fs)), 140.0 * frac)
    ts = (np.arange(n) * (1e6 / fs)).astype(np.int64)
    pd.DataFrame({
        "timestamp_us": ts,
        "angle_counts": np.round(counts).astype(np.int64) % COUNTS_PER_REV,
        "magnet_ok": np.ones(n, dtype=int),
    }).to_csv(path, index=False)


def _make_clip(path, events_s, fps=30, duration_s=20.0, sr=48000, size=(160, 120), lossless=True):
    n_frames = int(round(duration_s * fps))
    w, h = size
    frames = np.full((n_frames, h * w), 40, dtype=np.uint8)
    for ev in events_s:
        i = int(math.floor(ev * fps)) + 1  # first frame at/after the event
        for k in range(2):
            if 0 <= i + k < n_frames:
                frames[i + k, :] = 230

    n_samp = int(round(duration_s * sr))
    audio = np.zeros(n_samp, dtype=np.float32)
    click = (np.exp(-np.arange(int(0.005 * sr)) / (0.0008 * sr))
             * np.sin(2 * np.pi * 2200 * np.arange(int(0.005 * sr)) / sr))
    for ev in events_s:
        i = int(round(ev * sr))
        j = min(n_samp, i + len(click))
        if 0 <= i < n_samp:
            audio[i:j] += 0.8 * click[: j - i]
    pcm = np.clip(audio, -1, 1)
    pcm = (pcm * 32767).astype("<i2").tobytes()

    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as af:
        af.write(pcm)
        apath = af.name
    try:
        acodec = ["-c:a", "pcm_s16le"] if lossless else ["-c:a", "aac", "-b:a", "128k"]
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
            "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", apath,
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            *acodec, "-shortest", str(path),
        ], stdin_bytes=frames.tobytes())
    finally:
        os.unlink(apath)


def self_test(keep=False):
    if not have_ffmpeg():
        print("SELF-TEST SKIPPED: ffmpeg/ffprobe not on PATH")
        return 2

    DEVICE_DUR = 50.0
    VIDEO_DUR = 40.0
    DELTA_V = DEVICE_DUR - VIDEO_DUR          # true origin, both anchors
    SESSION_START = 1_756_000_000_000
    FPS = 30

    # Sub-frame phases must vary, and in the fixture they are STRATIFIED rather than random.
    #
    # Evenly-spaced taps at a whole number of frame periods all land at the same phase, so their
    # quantisation errors are identical instead of averaging out and the recovered offset comes
    # back biased by that shared error. Random phases fix that but leave a sampling error of
    # (1/fps)/sqrt(12n) — 2.8 ms over 12 taps at 30 fps — which would force AC-1's bar open to
    # ~8 ms for reasons that have nothing to do with whether the analyzer is correct.
    #
    # Stratifying puts one tap in each twelfth of the frame interval, so the mean quantisation
    # error is zero BY CONSTRUCTION and AC-1's original 2 ms bar tests the arithmetic exactly.
    # The order is shuffled so tap index is not monotone in phase.
    #
    # This is a property of the FIXTURE, not of the field. A real run is quantisation-limited and
    # its precision is the SE above — which is why the protocol counts taps rather than trusting
    # any single one.
    N_TAPS = 12
    rng = np.random.default_rng(8603)
    phases = [(i + 0.5) / N_TAPS / FPS for i in range(N_TAPS)]
    rng.shuffle(phases)
    TAPS = [round(12.0 + 3.0 * i + phases[i], 6) for i in range(N_TAPS)]
    OFFSETS_MS = [-500, -50, 0, 50, 500]
    TOL_MS = 2.0

    tmp = Path(tempfile.mkdtemp(prefix="taptest_"))
    failures = []
    print(f"self-test fixtures in {tmp}")
    print(f"tolerance +/-{TOL_MS:.2f} ms · {len(TAPS)} taps at {FPS} fps, "
          f"sub-frame phases stratified so quantisation cancels")
    print(f"\n{'injected':>9} {'end-anch':>10} {'start-anch':>11} {'acc':>4} {'rej':>4}  verdict")
    print("-" * 60)

    raw_csv = tmp / "fixture_raw.csv"
    _make_raw_csv(raw_csv, TAPS, duration_s=DEVICE_DUR)

    for off_ms in OFFSETS_MS:
        off = off_ms / 1000.0
        events = [tp - DELTA_V + off for tp in TAPS]
        clip = tmp / f"fixture_{off_ms:+d}.mkv"
        _make_clip(clip, events, duration_s=VIDEO_DUR)

        rep = analyze_rep(
            raw_csv, clip,
            session_start_utc_ms=SESSION_START,
            video_start_phone_ms=SESSION_START + int(DELTA_V * 1000),
            mic_distance_m=0.0,
            label=f"inject{off_ms:+d}",
        )
        s = summarize([rep])
        e = s["residual_end_anchored"]
        a = s["residual_start_anchored"]
        if e is None or a is None:
            failures.append(f"{off_ms:+d} ms: no accepted taps")
            print(f"{off_ms:>+8d}  {'-':>10} {'-':>11} {rep['n_accepted']:>4} "
                  f"{rep['n_rejected']:>4}  FAIL (nothing accepted)")
            continue
        ok = (abs(e["mean_ms"] - off_ms) <= TOL_MS and abs(a["mean_ms"] - off_ms) <= TOL_MS
              and rep["n_accepted"] == len(TAPS))
        if not ok:
            failures.append(
                f"{off_ms:+d} ms: end {e['mean_ms']:.2f}, start {a['mean_ms']:.2f}, "
                f"accepted {rep['n_accepted']}/{len(TAPS)}")
        print(f"{off_ms:>+8d}  {e['mean_ms']:>10.2f} {a['mean_ms']:>11.2f} "
              f"{rep['n_accepted']:>4} {rep['n_rejected']:>4}  {'OK' if ok else 'FAIL'}")

    # AC-4: ONE tap whose readouts disagree must be rejected while the rest survive. A
    # whole-session shift is deliberately NOT the test - that is a container offset, which
    # av_offset absorbs by design, so asserting rejection there would assert the wrong behaviour.
    print("\nAC-4 rejection path (ONE tap's audio shifted 3 frames):")
    shift = 3.0 / FPS
    ev_v = [tp - DELTA_V for tp in TAPS]
    ev_a = list(ev_v)
    ev_a[3] += shift
    clip = tmp / "fixture_desync.mkv"
    _make_desync_clip(clip, ev_v, ev_a, duration_s=VIDEO_DUR)
    rep = analyze_rep(raw_csv, clip, SESSION_START, SESSION_START + int(DELTA_V * 1000),
                      mic_distance_m=0.0, label="desync")
    rejected_ok = rep["n_rejected"] == 1 and rep["n_accepted"] == len(TAPS) - 1
    print(f"  accepted {rep['n_accepted']}, rejected {rep['n_rejected']} "
          f"(want {len(TAPS) - 1}/1) -> {'OK' if rejected_ok else 'FAIL'}")
    if not rejected_ok:
        failures.append(f"single-tap desync: accepted {rep['n_accepted']}, "
                        f"rejected {rep['n_rejected']}")

    # AC-5: 86-03's defect, reproduced from a fixture with ZERO injected clock error and pinned
    # BOTH ways. Asserting only that the repair works would not fail if the repair regressed.
    #
    # The mechanism, which is the one that voided 86-03: ring-down re-triggers spaced further apart
    # than the 0.5 s refractory are each detected as taps, and the last one lands INSIDE the
    # refractory of the next real strike — so the real strike is discarded and an artifact 300 ms
    # early takes its place. Audio and frames still agree perfectly with each other, because both
    # are readouts of the VIDEO, so 86-03's only rejection rule sees nothing wrong and ACCEPTS it.
    print("\nAC-5 ring-down (zero injected error; 86-03 launders it, 86-04 must not):")
    RINGDOWN = [(0.62, 0.15), (1.24, 0.12), (1.86, 0.10), (2.70, 0.08)]
    raw_ring = tmp / "fixture_ringdown.csv"
    _make_raw_csv(raw_ring, TAPS, duration_s=DEVICE_DUR, ringdown=RINGDOWN,
                  baseline_counts_s=20.0)
    clip = tmp / "fixture_ringdown.mkv"
    _make_clip(clip, [tp - DELTA_V for tp in TAPS], duration_s=VIDEO_DUR)

    old = analyze_rep(raw_ring, clip, SESSION_START, SESSION_START + int(DELTA_V * 1000),
                      mic_distance_m=0.0, label="ringdown-8603", detector="86-03")
    new = analyze_rep(raw_ring, clip, SESSION_START, SESSION_START + int(DELTA_V * 1000),
                      mic_distance_m=0.0, label="ringdown-8604", detector="86-04")

    laundered = [t for t in old["taps"] if t.get("status") == "ACCEPTED"
                 and abs(t["residual_end_anchored_s"]) > 0.150]
    print(f"  86-03: {old['n_encoder_taps']} encoder taps for {old['n_audio_onsets']} onsets "
          f"(over-trigger {old['encoder_overtrigger_ratio']:.1f}x), "
          f"{len(laundered)} ACCEPTED with |residual| > 150 ms")
    if not laundered:
        failures.append("ring-down fixture did not reproduce 86-03's defect — the fixture no "
                        "longer models the failure mode, so the other half proves nothing")
        print("  -> FAIL (nothing to repair; fixture is not exercising the defect)")
    else:
        worst = max(laundered, key=lambda t: abs(t["residual_end_anchored_s"]))
        print(f"         worst: v={worst['video_time_s']:.3f} carried "
              f"{worst['residual_end_anchored_s'] * 1000:+.0f} ms and was ACCEPTED")
        same = [t for t in new["taps"] if t["video_time_s"] == worst["video_time_s"]]
        rec = same[0] if same else None
        if rec is None:
            fixed = False
            how = "that tap vanished from the repaired run entirely"
        elif rec.get("status") != "ACCEPTED":
            fixed = True
            how = f"REJECTED ({str(rec.get('reason'))[:60]}...)"
        else:
            # PLAN AMENDMENT, recorded rather than quietly applied. 86-04's AC-5 asked for
            # |residual| <= 2 ms on this ONE tap. That is not reachable and the AC was wrong to
            # ask: a single tap carries a uniform +/- half-frame (16.7 ms) quantisation error by
            # construction, which is why the other fixtures stratify 12 taps so it cancels. The
            # same mistake was made and corrected in 86-03's AC-1 — see the protocol's Amendments.
            #
            # The 2 ms bar is applied instead to the ENCODER time against the fixture's own known
            # strike, which is exact, has no frame quantisation anywhere in it, and tests the
            # thing AC-5 actually cares about: was this paired to the real strike, or to a
            # ring-down artifact hundreds of ms away? The residual is reported beside it.
            err = min(abs(rec["encoder_time_s"] - tp) for tp in TAPS)
            fixed = err <= 0.002
            how = (f"ACCEPTED, paired to the real strike within {err * 1000:.2f} ms "
                   f"(residual {rec['residual_end_anchored_s'] * 1000:+.2f} ms — frame-quantised, "
                   f"so it is reported, not asserted)")
        print(f"  86-04: {new['n_encoder_taps']} encoder taps for {new['n_audio_onsets']} onsets "
              f"(over-trigger {new['encoder_overtrigger_ratio']:.1f}x); that tap is now {how}")
        print(f"  -> {'OK' if fixed else 'FAIL'}")
        if not fixed:
            failures.append(f"ring-down: repaired instrument still mishandles the tap at "
                            f"v={worst['video_time_s']:.3f} — {how}")

    # Informational, not a bar: how far AAC priming moves the audio readout on THIS ffmpeg. A real
    # iOS clip is AAC in mp4, so a constant audio-vs-frame offset in the field is expected to look
    # like this rather than like a clock error.
    print("\nAAC priming probe (informational — real clips are AAC/mp4):")
    try:
        clip = tmp / "fixture_aac.mp4"
        _make_clip(clip, [tp - DELTA_V for tp in TAPS], duration_s=VIDEO_DUR, lossless=False)
        rep = analyze_rep(raw_csv, clip, SESSION_START, SESSION_START + int(DELTA_V * 1000),
                          mic_distance_m=0.0, label="aac")
        print(f"  av_offset = {rep['av_offset_ms']:+.2f} ms "
              f"(flagged suspicious: {rep['av_offset_suspicious']}), "
              f"accepted {rep['n_accepted']}/{len(TAPS)}")
        st = summarize([rep])["residual_end_anchored"]
        if st:
            leak_ok = abs(st["mean_ms"]) <= TOL_MS
            print(f"  end-anchored residual {st['mean_ms']:+.2f} ms (n={st['n']}) -> "
                  f"{'OK' if leak_ok else 'FAIL'}: a container offset must not leak into it")
            if not leak_ok:
                failures.append(f"AAC container offset leaked into the residual "
                                f"({st['mean_ms']:+.2f} ms)")
    except Exception as exc:  # noqa: BLE001
        print(f"  probe failed (non-fatal): {exc}")

    if not keep:
        for p in tmp.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass

    print()
    if failures:
        print(f"SELF-TEST FAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"SELF-TEST PASS - {len(OFFSETS_MS)} injected offsets recovered within "
          f"{TOL_MS:.2f} ms, rejection path fires, no container-offset leak, "
          f"86-03's ring-down laundering reproduced and repaired")
    return 0


def _make_desync_clip(path, video_events, audio_events, fps=30, duration_s=20.0,
                      sr=48000, size=(160, 120)):
    """Same as _make_clip but with the two streams deliberately disagreeing."""
    n_frames = int(round(duration_s * fps))
    w, h = size
    frames = np.full((n_frames, h * w), 40, dtype=np.uint8)
    for ev in video_events:
        i = int(math.floor(ev * fps)) + 1
        for k in range(2):
            if 0 <= i + k < n_frames:
                frames[i + k, :] = 230

    n_samp = int(round(duration_s * sr))
    audio = np.zeros(n_samp, dtype=np.float32)
    click = (np.exp(-np.arange(int(0.005 * sr)) / (0.0008 * sr))
             * np.sin(2 * np.pi * 2200 * np.arange(int(0.005 * sr)) / sr))
    for ev in audio_events:
        i = int(round(ev * sr))
        j = min(n_samp, i + len(click))
        if 0 <= i < n_samp:
            audio[i:j] += 0.8 * click[: j - i]
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()

    with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as af:
        af.write(pcm)
        apath = af.name
    try:
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
            "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", apath,
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "pcm_s16le", "-shortest", str(path),
        ], stdin_bytes=frames.tobytes())
    finally:
        os.unlink(apath)


# ── cli ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Phase 86-03 tap-test analyzer")
    ap.add_argument("--self-test", action="store_true", help="synthetic fixtures (AC-1/3/4)")
    ap.add_argument("--keep-fixtures", action="store_true")
    ap.add_argument("--validate-timebase", metavar="DIR",
                    help="raw time base vs the production pipeline (AC-2)")
    ap.add_argument("--measure-domain", metavar="DIR",
                    help="86-04 AC-1: which domain the strike is visible in (read-only)")
    ap.add_argument("--limit", type=int, default=None)

    ap.add_argument("--raw", help="raw encoder CSV for one rep")
    ap.add_argument("--video", help="clip for one rep")
    ap.add_argument("--session-start-utc-ms", type=int)
    ap.add_argument("--video-start-phone-ms", type=int)
    ap.add_argument("--mic-distance-m", type=float, default=1.0)
    ap.add_argument("--crop", default=None, help="ffmpeg crop, w:h:x:y")
    ap.add_argument("--label", default=None)
    ap.add_argument("--json-out", default=None, help="sidecar for cross-session aggregation")
    args = ap.parse_args()

    if args.self_test:
        return self_test(keep=args.keep_fixtures)

    if args.validate_timebase:
        ok, _, _ = validate_timebase(args.validate_timebase, limit=args.limit)
        return 0 if ok else 1

    if args.measure_domain:
        ok, _ = measure_domain(args.measure_domain)
        return 0 if ok else 1

    missing = [n for n, v in (
        ("--raw", args.raw), ("--video", args.video),
        ("--session-start-utc-ms", args.session_start_utc_ms),
    ) if v is None]
    if missing:
        ap.error("missing " + ", ".join(missing))

    rep = analyze_rep(args.raw, args.video, args.session_start_utc_ms,
                      args.video_start_phone_ms, args.mic_distance_m,
                      crop=args.crop, label=args.label)
    s = summarize([rep])

    print(f"\n{rep['label']}")
    print(f"  device {rep['device_duration_s']:.3f} s · video {rep['video_duration_s']:.3f} s · "
          f"{rep['fps']:.2f} fps (half frame {rep['half_frame_ms']:.1f} ms)")
    print(f"  end-anchored origin   {rep['end_anchored_origin_s']:+.4f} s   <- what the coach sees")
    if rep["start_anchored_origin_s"] is None:
        print("  start-anchored origin  NOT AVAILABLE - no --video-start-phone-ms supplied")
        print("  camera warm-up         NOT AVAILABLE - needs videoStartPhoneMs (B2, B4 unmeasured)")
    else:
        print(f"  start-anchored origin {rep['start_anchored_origin_s']:+.4f} s   <- what 86-02 corrected")
        print(f"  camera warm-up        {rep['camera_warm_up_s']:+.4f} s")
    print(f"  sound delay corrected {rep['sound_delay_ms']:.2f} ms "
          f"({rep['mic_distance_m']:.2f} m) - cross-check only, never the residual")
    flag = "  <-- SUSPICIOUS (>1 frame)" if rep["av_offset_suspicious"] else ""
    print(f"  A/V container offset  {rep['av_offset_ms']:+.2f} ms "
          f"(estimated: {rep['av_offset_estimated']}){flag}")
    if rep["readout_spread_frames"] is not None:
        sflag = "  <-- SUSPICIOUS (>1.2)" if rep["readout_spread_suspicious"] else ""
        print(f"  readout spread        {rep['readout_spread_frames']:.2f} frames "
              f"(one frame is expected){sflag}")
    print(f"  taps: {rep['n_accepted']} accepted, {rep['n_rejected']} rejected "
          f"(encoder {rep['n_encoder_taps']}, audio {rep['n_audio_onsets']}, "
          f"frames {rep['n_frame_events']})")
    for t in rep["taps"]:
        if t.get("status") == "ACCEPTED":
            print(f"    v={t['video_time_s']:8.3f}  enc={t['encoder_time_s']:8.3f}  "
                  f"end={t['residual_end_anchored_s'] * 1000:+8.2f} ms  "
                  + ("start=      n/a" if t["residual_start_anchored_s"] is None
                     else f"start={t['residual_start_anchored_s'] * 1000:+9.2f} ms"))
        else:
            print(f"    v={t['video_time_s']:8.3f}  {t['status']}: {t.get('reason')}")
    for key in ("residual_end_anchored", "residual_start_anchored", "scatter_about_av_offset"):
        st = s[key]
        if st:
            se = f" ± {st['se_ms']:.2f}" if st["se_ms"] is not None else ""
            print(f"  {key:<26} {st['mean_ms']:+8.2f}{se} ms  (n={st['n']})")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
