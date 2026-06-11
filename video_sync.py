"""
video_sync.py
─────────────
Renders a processed tether session CSV as a velocity overlay on a video.

Two ways to align the tether data with the video:

A) Wall-clock offset (phone workflow — no visual cue needed)
   The phone both records the video and retrieves the session, so one wall
   clock bridges them: the app computes sessionStartPhoneMs from the device's
   META response, and the video file's creation timestamp gives
   videoStartPhoneMs (e.g. via ffprobe). Then:

       video_origin_s = (sessionStartPhoneMs - videoStartPhoneMs) / 1000

       python video_sync.py \\
           --video   footage/session.mp4 \\
           --processed processed/tony_1.csv \\
           --video-origin-s 12.34 \\
           --output  output/tony_1_overlay.mp4

B) Visual sync marker (external camera / GoPro workflow)
  1. During recording, press 's' in logger.py to stamp a sync marker.
     This writes raw/sync_<label>_<datetime>.txt with lines: index,timestamp_us
  2. In any video player, find the frame number where the sync cue is visible
     (e.g. the clap frame). Note it.
  3. Run this script:

       python video_sync.py \\
           --video   footage/session.mp4 \\
           --processed processed/tony_1.csv \\
           --sync-tether-us 1234567890 \\
           --sync-frame 142 \\
           --output  output/tony_1_overlay.mp4

     --sync-tether-us : value from the sync .txt file (column 1)
     --sync-frame     : frame number visible in the video at the sync cue

Multi-rep use: run once per rep, passing --rep N to pick which sync marker from
the sidecar file, and --sync-frame for that rep's cue frame.

Output: MP4 with a scrolling velocity strip at the bottom + current speed in
the top-right corner. Audio is preserved via ffmpeg.

Dependencies: opencv-python, numpy, pandas, matplotlib, (ffmpeg on PATH)
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Width of the velocity strip in pixels (fraction of frame height)
STRIP_HEIGHT_FRAC = 0.18
# Seconds of velocity trace visible in the scrolling window
WINDOW_S = 10.0
# Colour of the trace line
TRACE_COLOR = "#00BFFF"
# Background alpha for text overlays
TEXT_BG_ALPHA = 0.45


def load_sync_file(sync_path: Path, rep: int) -> int:
    """Return the timestamp_us for the given rep index from a sync sidecar file."""
    lines = sync_path.read_text().strip().splitlines()
    for line in lines:
        parts = line.split(",")
        if int(parts[0]) == rep:
            return int(parts[1])
    raise ValueError(f"Rep {rep} not found in {sync_path}")


def render_strip(vel_window: np.ndarray, current_vel: float,
                 width: int, height: int) -> np.ndarray:
    """Render a single velocity strip frame as a BGR numpy array (height×width×3)."""
    dpi = 100
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")

    x = np.linspace(0, WINDOW_S, len(vel_window))
    ax.plot(x, vel_window, color=TRACE_COLOR, linewidth=1.5)

    # Vertical cursor at the right edge (current position)
    ax.axvline(x=WINDOW_S, color="white", linewidth=1.0, alpha=0.5)

    ax.set_xlim(0, WINDOW_S)
    vmax = max(np.nanmax(np.abs(vel_window)) * 1.1, 0.5)
    ax.set_ylim(-0.05, vmax)
    ax.set_ylabel("vel (m/s)", color="white", fontsize=7)
    ax.tick_params(colors="white", labelsize=6)
    for spine in ax.spines.values():
        spine.set_edgecolor("#444444")
    ax.xaxis.set_visible(False)

    fig.tight_layout(pad=0.3)

    fig.canvas.draw()
    # buffer_rgba: tostring_rgb() was removed in matplotlib 3.8
    buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    buf = buf.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    buf = np.ascontiguousarray(buf[:, :, :3])
    plt.close(fig)

    # Resize to exact dimensions
    strip = cv2.resize(buf, (width, height))
    return cv2.cvtColor(strip, cv2.COLOR_RGB2BGR)


def overlay_text(frame: np.ndarray, text: str, pos, font_scale: float = 1.4):
    """Draw text with a semi-transparent dark background rectangle."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    pad = 6
    overlay = frame.copy()
    cv2.rectangle(overlay, (x - pad, y - th - pad), (x + tw + pad, y + baseline + pad),
                  (0, 0, 0), -1)
    cv2.addWeighted(overlay, TEXT_BG_ALPHA, frame, 1 - TEXT_BG_ALPHA, 0, frame)
    cv2.putText(frame, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


def main():
    parser = argparse.ArgumentParser(description="Overlay tether velocity on GoPro video")
    parser.add_argument("--video", required=True, help="Input video file")
    parser.add_argument("--processed", required=True, help="Processed tether CSV (time_s, vel_ms, ...)")

    parser.add_argument("--video-origin-s", type=float, default=None,
                        help="Tether time (s) at video t=0, e.g. "
                             "(sessionStartPhoneMs - videoStartPhoneMs) / 1000. "
                             "Alternative to --sync-tether-us/--sync-file + --sync-frame.")

    sync_group = parser.add_mutually_exclusive_group()
    sync_group.add_argument("--sync-tether-us", type=int,
                            help="Sync marker timestamp_us from logger (raw value)")
    sync_group.add_argument("--sync-file", help="Path to sync sidecar .txt file")

    parser.add_argument("--rep", type=int, default=0,
                        help="Rep index when using --sync-file (default 0)")
    parser.add_argument("--sync-frame", type=int, default=None,
                        help="Frame number in the video where the sync cue is visible")
    parser.add_argument("--output", default=None, help="Output video path (default: <input>_overlay.mp4)")
    args = parser.parse_args()

    # Exactly one sync method: --video-origin-s, OR a sync marker + --sync-frame
    has_marker = args.sync_tether_us is not None or args.sync_file is not None
    if args.video_origin_s is not None:
        if has_marker or args.sync_frame is not None:
            parser.error("--video-origin-s cannot be combined with "
                         "--sync-tether-us/--sync-file/--sync-frame")
    else:
        if not has_marker or args.sync_frame is None:
            parser.error("provide either --video-origin-s (wall-clock workflow), or "
                         "one of --sync-tether-us/--sync-file plus --sync-frame "
                         "(visual-marker workflow)")

    # Resolve sync timestamp (visual-marker workflow only)
    if args.video_origin_s is None:
        if args.sync_file:
            sync_us = load_sync_file(Path(args.sync_file), args.rep)
        else:
            sync_us = args.sync_tether_us
        sync_tether_s = sync_us / 1e6

    # Load tether data
    df = pd.read_csv(args.processed)
    t_tether = df["time_s"].to_numpy()
    v_tether = df["vel_ms"].to_numpy()

    # Open video
    video_path = Path(args.video)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"ERROR: cannot open {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # t=0 in video maps to this tether time
    if args.video_origin_s is not None:
        t_video_origin = args.video_origin_s
    else:
        t_video_origin = sync_tether_s - args.sync_frame / fps

    strip_h = int(frame_h * STRIP_HEIGHT_FRAC)
    out_h = frame_h + strip_h

    # Output path (no audio yet — added by ffmpeg at the end)
    out_path = Path(args.output) if args.output else video_path.with_name(
        video_path.stem + "_overlay.mp4")
    tmp_path = out_path.with_suffix(".noaudio.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp_path), fourcc, fps, (frame_w, out_h))

    window_frames = int(WINDOW_S * fps)

    print(f"Rendering {total_frames} frames at {fps:.1f} fps...")
    if args.video_origin_s is not None:
        print(f"Tether origin: {t_video_origin:.3f} s  |  from --video-origin-s")
    else:
        print(f"Tether origin: {t_video_origin:.3f} s  |  sync frame: {args.sync_frame}")

    for frame_idx in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        t_now = t_video_origin + frame_idx / fps

        # Velocity at current moment
        current_vel = float(np.interp(t_now, t_tether, v_tether,
                                      left=np.nan, right=np.nan))

        # Velocity window: [t_now - WINDOW_S, t_now]
        t_win_start = t_now - WINDOW_S
        t_win = np.linspace(t_win_start, t_now, window_frames)
        vel_win = np.interp(t_win, t_tether, v_tether, left=np.nan, right=np.nan)

        strip = render_strip(vel_win, current_vel, frame_w, strip_h)

        combined = np.vstack([frame, strip])

        # Current speed readout
        vel_text = f"{current_vel:.2f} m/s" if not np.isnan(current_vel) else "---"
        overlay_text(combined, vel_text, (frame_w - 200, 50))

        writer.write(combined)

        if frame_idx % 100 == 0:
            pct = frame_idx / total_frames * 100
            print(f"  {pct:.0f}%  frame {frame_idx}/{total_frames}", end="\r")

    cap.release()
    writer.release()
    print(f"\nFrames written to {tmp_path}")

    # Mux original audio back with ffmpeg
    print("Muxing audio...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(tmp_path),
        "-i", str(video_path),
        "-map", "0:v:0",
        "-map", "1:a:0?",       # optional audio (? = don't error if absent)
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg audio mux failed — output is silent video at:", tmp_path)
        print(result.stderr[-500:])
    else:
        tmp_path.unlink()
        print(f"Done → {out_path}")


if __name__ == "__main__":
    main()
