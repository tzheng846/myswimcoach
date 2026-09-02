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

MODES
-----
  --self-test              synthetic fixtures with injected offsets           (AC-1, AC-3, AC-4)
  --validate-timebase DIR  raw time base vs the production pipeline           (AC-2)
  (default)                analyze one real rep

Needs ffmpeg + ffprobe on PATH. Read-only: never writes to Supabase, never touches a stored session.
"""

import argparse
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
                mic_distance_m, crop=None, label=None):
    # video_start_phone_ms may be None: it is recorded only in the app's on-screen log, so an
    # operator can come back with clips and CSVs but without it. The END-anchored residual (B1,
    # the coach-facing number) does not use it at all, so it is still fully computable; the
    # start-anchored residual and camera warm-up are then reported as None rather than invented.
    enc = read_raw(raw_path)
    taps, _ = find_taps(enc["t_s"], enc["counts"])

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
        rec.update({
            "video_time_sound_corrected_s": round(p["t_audio"], 6),
            "frame_time_s": round(p["fr"], 6),
            "frame_estimate_s": round(p["fr_est"], 6),
            "audio_minus_frame_s": round(p["t_audio"] - p["fr_est"], 6),
            "scatter_about_av_offset_s": round(scatter, 6),
            "encoder_time_s": round(p["enc"], 6),
            "residual_end_anchored_s": round((p["fr_est"] + end_origin) - p["enc"], 6),
            "residual_start_anchored_s": (round((p["fr_est"] + start_origin) - p["enc"], 6)
                                          if have_start else None),
        })
        if abs(scatter) > GROSS_DISAGREEMENT_FRAMES / fps:
            rec["status"] = "REJECTED"
            rec["reason"] = (f"readouts disagree by {scatter * 1000:+.1f} ms about this "
                             f"session's A/V offset — beyond {GROSS_DISAGREEMENT_FRAMES} frames "
                             f"({GROSS_DISAGREEMENT_FRAMES / fps * 1000:.1f} ms), so this tap is "
                             f"mispaired or its strike was missed in one stream")
        else:
            rec["status"] = "ACCEPTED"
        records.append(rec)

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
        "n_encoder_taps": len(taps),
        "n_audio_onsets": len(onsets),
        "n_frame_events": len(fevents),
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


# ── AC-1 / AC-3 / AC-4: synthetic fixtures ─────────────────────────────────────

def _make_raw_csv(path, taps_s, fs=270.0, duration_s=30.0):
    n = int(duration_s * fs) + 1  # +1 so (n-1)/fs is EXACTLY duration_s
    t = np.arange(n) / fs
    counts = 200.0 * t  # a slow steady rotation underneath
    for tap in taps_s:
        i = int(round(tap * fs))
        if 0 <= i < n - 12:
            # A strike: a sharp jerk that rings down over ~12 samples.
            ring = 140.0 * np.exp(-np.arange(12) / 2.5) * np.cos(np.arange(12) * 1.1)
            counts[i:i + 12] += ring
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
          f"{TOL_MS:.2f} ms, rejection path fires, no container-offset leak")
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
