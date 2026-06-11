"""
merge_streams.py — time-align pose CSV with processed encoder CSV.

Uses pd.merge_asof with a 50ms tolerance on t_s.
Encoder data is the "left" key; pose rows are matched to the nearest
encoder timestamp within the tolerance window.

Usage:
    python merge_streams.py processed/session.csv pose/session.csv
    python merge_streams.py processed/session.csv pose/session.csv --output merged/session.csv
    python merge_streams.py processed/session.csv pose/session.csv --tolerance 0.1
"""

import argparse
import pandas as pd
from pathlib import Path


def merge_streams(encoder_path, pose_path, output_path, tolerance_s=0.05):
    enc  = pd.read_csv(encoder_path).sort_values("time_s").reset_index(drop=True)
    pose = pd.read_csv(pose_path).sort_values("t_s").reset_index(drop=True)

    # Rename pose t_s → time_s so merge_asof uses a single key name
    pose = pose.rename(columns={"t_s": "time_s"})

    merged = pd.merge_asof(
        enc,
        pose,
        on="time_s",
        direction="nearest",
        tolerance=tolerance_s,
    )

    n_matched = merged["l_elbow_angle_deg"].notna().sum()
    print(f"Encoder rows:  {len(enc)}")
    print(f"Pose rows:     {len(pose)}")
    print(f"Merged rows:   {len(merged)}  ({n_matched} with pose data, "
          f"{len(merged) - n_matched} unmatched)")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"Saved → {output_path}")

    return merged


def main():
    parser = argparse.ArgumentParser(description="Merge encoder and pose CSVs on timestamp.")
    parser.add_argument("encoder_csv", type=Path, help="Processed encoder CSV (time_s column)")
    parser.add_argument("pose_csv",    type=Path, help="Pose CSV from pose_extraction.py (t_s column)")
    parser.add_argument("--output",    type=Path, default=None,
                        help="Output path (default: merged/<encoder_stem>.csv)")
    parser.add_argument("--tolerance", type=float, default=0.05,
                        help="Max timestamp gap to allow a match, in seconds (default: 0.05)")
    args = parser.parse_args()

    if args.output is None:
        args.output = Path("merged") / args.encoder_csv.name

    merge_streams(args.encoder_csv, args.pose_csv, args.output, args.tolerance)


if __name__ == "__main__":
    main()
