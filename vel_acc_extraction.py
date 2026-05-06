import argparse
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from scipy.stats import median_abs_deviation
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from pathlib import Path

SESSION_STEM = "kenneth_3"

INPUT_FILE  = f"raw/{SESSION_STEM}.csv"
OUTPUT_FILE = f"processed/{SESSION_STEM}.csv"

Path("processed").mkdir(parents=True, exist_ok=True)

# ── Wheel physical constants ──────────────────────────────────────────────
WHEEL_DIAMETER_M  = 0.044
WHEEL_CIRCUM_M    = np.pi * WHEEL_DIAMETER_M
COUNTS_PER_REV    = 4096
METERS_PER_COUNT  = WHEEL_CIRCUM_M / COUNTS_PER_REV

# ── Filter settings ───────────────────────────────────────────────────────
TARGET_FS_HZ    = 50.0
CUTOFF_HZ       = 2.0
FILTER_ORDER    = 4
MAD_THRESHOLD   = 6.0
MAX_PHYSICAL_MS = 3.0


def load_data(input_file):
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows")
    print(df.head())
    n_bad = (df["magnet_ok"] == 0).sum()
    if n_bad > 0:
        print(f"Dropping {n_bad} rows with magnet_ok=0")
    df = df[df["magnet_ok"] == 1].copy().reset_index(drop=True)
    df["time_s"] = (df["timestamp_us"] - df["timestamp_us"].iloc[0]) / 1e6
    print(f"Session duration: {df['time_s'].iloc[-1]:.2f} s")
    return df


def unwrap_angle(df):
    angle_rad = df["angle_counts"].values * (2 * np.pi / COUNTS_PER_REV)
    angle_unwrapped_rad = np.unwrap(angle_rad)
    angle_unwrapped_counts = angle_unwrapped_rad * (COUNTS_PER_REV / (2 * np.pi))
    return angle_unwrapped_rad, angle_unwrapped_counts


def counts_to_distance(angle_unwrapped_counts, meters_per_count):
    dist_raw = angle_unwrapped_counts * meters_per_count
    dist_raw -= dist_raw[0]
    if dist_raw[-1] < 0:
        dist_m = -dist_raw   # wheel mounted backwards
    else:
        dist_m = dist_raw
    return dist_m


def compute_raw_velocity(dist_m, t):
    vel_raw = np.gradient(dist_m, t)
    vel_clipped = np.clip(vel_raw, -MAX_PHYSICAL_MS, MAX_PHYSICAL_MS)
    n_clipped = np.sum(np.abs(vel_raw) > MAX_PHYSICAL_MS)
    print(f"Spike clip: {n_clipped} samples clipped ({n_clipped/len(vel_raw)*100:.1f}%)")
    print(f"Vel after clip: min={vel_clipped.min():.3f}  max={vel_clipped.max():.3f}")
    return vel_raw, vel_clipped


def interpolate_to_uniform(vel_clipped, t, target_fs_hz):
    t_uniform = np.arange(t[0], t[-1], 1.0 / target_fs_hz)
    vel_uniform = np.interp(t_uniform, t, vel_clipped)
    return vel_uniform, t_uniform


def apply_filters(vel_uniform, target_fs_hz, filter_order):
    # Two cutoffs: velocity display preserves stroke shape; acceleration needs
    # a lower cutoff because differentiation amplifies noise by 2π × frequency.
    vel_cutoff_hz   = (target_fs_hz / 2) * 0.10
    accel_cutoff_hz = (target_fs_hz / 2) * 0.02
    b_vel,   a_vel   = butter(filter_order, vel_cutoff_hz   / (target_fs_hz / 2), btype="low")
    b_accel, a_accel = butter(filter_order, accel_cutoff_hz / (target_fs_hz / 2), btype="low")
    vel_filt      = filtfilt(b_vel,   a_vel,   vel_uniform)
    vel_for_accel = filtfilt(b_accel, a_accel, vel_uniform)
    accel_filt    = np.gradient(vel_for_accel, 1.0 / target_fs_hz)
    print(f"Vel cutoff:   {vel_cutoff_hz:.2f} Hz")
    print(f"Accel cutoff: {accel_cutoff_hz:.2f} Hz")
    print(f"Vel range:    {vel_filt.min():.3f} to {vel_filt.max():.3f} m/s")
    print(f"Accel range:  {accel_filt.min():.3f} to {accel_filt.max():.3f} m/s²")
    return vel_filt, accel_filt


def export_results(t_uniform, dist_m, t, vel_filt, accel_filt, output_file):
    out = pd.DataFrame({
        "time_s":    t_uniform,
        "dist_m":    np.interp(t_uniform, t, dist_m),
        "vel_ms":    vel_filt,
        "accel_ms2": accel_filt,
    })
    out.to_csv(output_file, index=False, float_format="%.4f")
    print(f"\nExported {len(out)} rows → {output_file}")
    print(f"  Peak velocity:      {vel_filt.max():.3f} m/s")
    print(f"  Peak acceleration:  {accel_filt.max():.3f} m/s²")
    print(f"  Total distance:     {out['dist_m'].max():.3f} m")
    return out


def plot_results(out, t, vel_clipped):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=("Distance (m)", "Velocity (m/s)", "Acceleration (m/s²)"),
        vertical_spacing=0.08,
    )
    fig.add_trace(go.Scatter(
        x=out["time_s"], y=out["dist_m"],
        name="Distance", line=dict(color="#1d9e75", width=1.5)
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=t, y=vel_clipped,
        name="Vel raw (clipped)", line=dict(color="#b4b2a9", width=0.8),
        opacity=0.5
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=out["time_s"], y=out["vel_ms"],
        name="Vel filtered", line=dict(color="#185fa5", width=2)
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=out["time_s"], y=out["accel_ms2"],
        name="Acceleration", line=dict(color="#d85a30", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(24,95,165,0.10)",
    ), row=3, col=1)
    fig.add_hline(y=0, line=dict(color="#888780", width=0.8, dash="dot"), row=3, col=1)
    fig.update_layout(
        title="AS5600 Swim Data — Cleaned Pipeline",
        height=700,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.08),
        font=dict(size=11),
    )
    fig.update_xaxes(title_text="Time (s)", row=3, col=1)
    fig.show()


def process_file(csv_file, output_file):
    df = load_data(str(csv_file))
    angle_unwrapped_rad, angle_unwrapped_counts = unwrap_angle(df)
    dist_m = counts_to_distance(angle_unwrapped_counts, METERS_PER_COUNT)
    t = df["time_s"].values
    vel_raw, vel_clipped = compute_raw_velocity(dist_m, t)
    vel_uniform, t_uniform = interpolate_to_uniform(vel_clipped, t, TARGET_FS_HZ)
    vel_filt, accel_filt = apply_filters(vel_uniform, TARGET_FS_HZ, FILTER_ORDER)
    out = export_results(t_uniform, dist_m, t, vel_filt, accel_filt, str(output_file))
    plot_results(out, t, vel_clipped)


def main():
    parser = argparse.ArgumentParser(description="Process swim encoder CSV data.")
    parser.add_argument("input", nargs="?", default=INPUT_FILE,
                        help="CSV file or folder of CSV files (default: %(default)s)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        csv_files = sorted(input_path.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files found in {input_path}")
            return
    elif input_path.suffix == ".csv":
        csv_files = [input_path]
    else:
        print(f"Error: {input_path} is not a CSV file or directory")
        return

    Path("processed").mkdir(parents=True, exist_ok=True)

    for csv_file in csv_files:
        output_file = Path("processed") / f"{csv_file.stem}.csv"
        print(f"\n{'=' * 50}")
        print(f"Processing: {csv_file}  →  {output_file}")
        print(f"{'=' * 50}")
        process_file(csv_file, output_file)


if __name__ == "__main__":
    main()
