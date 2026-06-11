"""
pose_extraction.py — extract joint positions and angles from swimming footage.

Runs ViTPose-L on each frame, computes elbow/knee angles, writes a CSV
time-aligned to the encoder signal via a sync offset.

Usage:
    python pose_extraction.py video.mp4 --sync-offset 2.14
    python pose_extraction.py video.mp4 --sync-offset 2.14 --output pose/session.csv
    python pose_extraction.py video.mp4 --sync-offset 2.14 --model work_dirs/vitpose_swimxyz/checkpoint-final
    python pose_extraction.py video.mp4 --sync-offset 2.14 --bbox 100 50 1820 1030

Sync offset: video timestamp (seconds) of the LED flash frame = encoder t=0.
             Frames before the flash get negative t_s; frames after get positive.

Bbox: x1 y1 x2 y2 in pixels. Defaults to full frame. Use this to crop to
      the swimmer's lane if there are false detections elsewhere.

Output CSV columns:
    t_s,
    l_shoulder_x, l_shoulder_y, r_shoulder_x, r_shoulder_y,
    l_elbow_x,    l_elbow_y,    r_elbow_x,    r_elbow_y,
    l_wrist_x,    l_wrist_y,    r_wrist_x,    r_wrist_y,
    l_hip_x,      l_hip_y,      r_hip_x,      r_hip_y,
    l_knee_x,     l_knee_y,     r_knee_x,     r_knee_y,
    l_ankle_x,    l_ankle_y,    r_ankle_x,    r_ankle_y,
    l_elbow_angle_deg, r_elbow_angle_deg,
    l_knee_angle_deg,  r_knee_angle_deg,
    min_visibility
"""

import argparse
import numpy as np
import pandas as pd
import cv2
import torch
from pathlib import Path
from transformers import VitPoseForPoseEstimation, VitPoseImageProcessor

# COCO17 keypoint indices used here
_L_SHOULDER, _R_SHOULDER = 5, 6
_L_ELBOW,    _R_ELBOW    = 7, 8
_L_WRIST,    _R_WRIST    = 9, 10
_L_HIP,      _R_HIP      = 11, 12
_L_KNEE,     _R_KNEE     = 13, 14
_L_ANKLE,    _R_ANKLE    = 15, 16

_BODY_INDICES = [
    _L_SHOULDER, _R_SHOULDER,
    _L_ELBOW,    _R_ELBOW,
    _L_WRIST,    _R_WRIST,
    _L_HIP,      _R_HIP,
    _L_KNEE,     _R_KNEE,
    _L_ANKLE,    _R_ANKLE,
]


def _angle_deg(a, b, c):
    """
    Angle at joint b formed by points a→b→c, in degrees.
    All inputs are (2,) arrays [x, y].
    Returns NaN if either segment has zero length.
    """
    ba = a - b
    bc = c - b
    n_ba = np.linalg.norm(ba)
    n_bc = np.linalg.norm(bc)
    if n_ba < 1e-6 or n_bc < 1e-6:
        return np.nan
    cos_angle = np.dot(ba, bc) / (n_ba * n_bc)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))


def _process_frame(kp, scores):
    """
    Given COCO17 keypoints (17, 2) and scores (17,), return a flat dict
    with joint coordinates, computed angles, and min_visibility.
    All coordinates are in pixels.
    """
    def pt(idx):
        return kp[idx]  # (x, y)

    row = {}

    # Joint coordinates
    for name, idx in [
        ("l_shoulder", _L_SHOULDER), ("r_shoulder", _R_SHOULDER),
        ("l_elbow",    _L_ELBOW),    ("r_elbow",    _R_ELBOW),
        ("l_wrist",    _L_WRIST),    ("r_wrist",    _R_WRIST),
        ("l_hip",      _L_HIP),      ("r_hip",      _R_HIP),
        ("l_knee",     _L_KNEE),     ("r_knee",     _R_KNEE),
        ("l_ankle",    _L_ANKLE),    ("r_ankle",    _R_ANKLE),
    ]:
        row[f"{name}_x"] = float(kp[idx, 0])
        row[f"{name}_y"] = float(kp[idx, 1])

    # Elbow angles: shoulder → elbow → wrist
    row["l_elbow_angle_deg"] = _angle_deg(pt(_L_SHOULDER), pt(_L_ELBOW), pt(_L_WRIST))
    row["r_elbow_angle_deg"] = _angle_deg(pt(_R_SHOULDER), pt(_R_ELBOW), pt(_R_WRIST))

    # Knee angles: hip → knee → ankle
    row["l_knee_angle_deg"] = _angle_deg(pt(_L_HIP), pt(_L_KNEE), pt(_L_ANKLE))
    row["r_knee_angle_deg"] = _angle_deg(pt(_R_HIP), pt(_R_KNEE), pt(_R_ANKLE))

    row["min_visibility"] = float(scores[_BODY_INDICES].min())

    return row


def extract_pose(video_path, sync_offset_s, output_path, model_name, bbox=None, stride=1, device="cuda"):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video: {width}x{height} @ {fps:.2f} fps, {total_frames} frames")
    print(f"Sync offset: {sync_offset_s:.3f} s  |  stride: {stride}")

    # Default bbox = full frame [x1, y1, x2, y2]
    if bbox is None:
        bbox = [0, 0, width, height]

    print(f"Loading model: {model_name}")
    processor = VitPoseImageProcessor.from_pretrained(model_name)
    model = VitPoseForPoseEstimation.from_pretrained(model_name).to(device)
    model.eval()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    rows = []
    frame_idx = 0

    with torch.inference_mode():
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % stride == 0:
                t_s = frame_idx / fps - sync_offset_s

                # cv2 loads BGR; convert to RGB for the processor
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                inputs = processor(
                    images=rgb,
                    boxes=[[bbox]],
                    return_tensors="pt"
                )
                inputs = {k: v.to(device) for k, v in inputs.items()}

                outputs = model(**inputs, dataset_index=torch.tensor([0], device=device))
                results = processor.post_process_pose_estimation(
                    outputs, boxes=[[bbox]]
                )[0]  # first (only) image

                # results is a list with one entry per person box
                person = results[0]
                kp     = person["keypoints"].cpu().numpy()   # (17, 2)
                scores = person["scores"].cpu().numpy()       # (17,)

                row = _process_frame(kp, scores)
                row["t_s"] = t_s
                rows.append(row)

                if frame_idx % (stride * 100) == 0:
                    print(f"  frame {frame_idx}/{total_frames}  t={t_s:.2f}s  min_vis={row['min_visibility']:.2f}")

            frame_idx += 1

    cap.release()

    # Build DataFrame with t_s first
    col_order = ["t_s",
                 "l_shoulder_x", "l_shoulder_y", "r_shoulder_x", "r_shoulder_y",
                 "l_elbow_x",    "l_elbow_y",    "r_elbow_x",    "r_elbow_y",
                 "l_wrist_x",    "l_wrist_y",    "r_wrist_x",    "r_wrist_y",
                 "l_hip_x",      "l_hip_y",      "r_hip_x",      "r_hip_y",
                 "l_knee_x",     "l_knee_y",     "r_knee_x",     "r_knee_y",
                 "l_ankle_x",    "l_ankle_y",    "r_ankle_x",    "r_ankle_y",
                 "l_elbow_angle_deg", "r_elbow_angle_deg",
                 "l_knee_angle_deg",  "r_knee_angle_deg",
                 "min_visibility"]

    df = pd.DataFrame(rows)[col_order]
    df.to_csv(output_path, index=False)
    print(f"\nSaved {len(df)} rows → {output_path}")
    print(f"Mean min_visibility: {df['min_visibility'].mean():.3f}")
    nan_runs = (df["l_elbow_angle_deg"].isna()).sum()
    print(f"NaN elbow angle frames: {nan_runs}/{len(df)}")


def main():
    parser = argparse.ArgumentParser(description="Extract pose from swimming footage.")
    parser.add_argument("video",        type=Path,  help="Input video file")
    parser.add_argument("--sync-offset", type=float, required=True,
                        help="Video timestamp (s) of LED flash frame = encoder t=0")
    parser.add_argument("--output",      type=Path,  default=None,
                        help="Output CSV path (default: pose/<video_stem>.csv)")
    parser.add_argument("--model",       type=str,   default="usyd-community/vitpose-plus-large",
                        help="HuggingFace model name or local checkpoint path")
    parser.add_argument("--bbox",        type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                        default=None,
                        help="Person bounding box in pixels (default: full frame)")
    parser.add_argument("--stride",      type=int,   default=1,
                        help="Process every Nth frame (default: 1 = every frame)")
    parser.add_argument("--cpu",         action="store_true",
                        help="Force CPU inference (slow)")
    args = parser.parse_args()

    if args.output is None:
        args.output = Path("pose") / f"{args.video.stem}.csv"

    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    extract_pose(
        video_path=args.video,
        sync_offset_s=args.sync_offset,
        output_path=args.output,
        model_name=args.model,
        bbox=args.bbox,
        stride=args.stride,
        device=device,
    )


if __name__ == "__main__":
    main()
