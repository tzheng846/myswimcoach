import argparse
import webbrowser
import numpy as np
import pandas as pd
from scipy.signal import decimate
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from pathlib import Path

SESSION_STEM = "kenneth_3"

INPUT_FILE  = f"raw/{SESSION_STEM}.csv"
OUTPUT_FILE = f"processed/{SESSION_STEM}.csv"

# ── Excluded time ranges ──────────────────────────────────────────────────
# List of (start_s, end_s) pairs to remove from analysis (NaN'd out).
# Empty list = keep everything.
EXCLUDED_SEGMENTS = [


]

Path("processed").mkdir(parents=True, exist_ok=True)

# ── Wheel physical constants ──────────────────────────────────────────────
WHEEL_DIAMETER_M  = 0.06
WHEEL_CIRCUM_M    = np.pi * WHEEL_DIAMETER_M
COUNTS_PER_REV    = 4096
METERS_PER_COUNT  = WHEEL_CIRCUM_M / COUNTS_PER_REV

# ── Decimation settings ───────────────────────────────────────────────────
# Native rate is inferred from the data (~270 Hz for current sessions).
# TARGET_FS_HZ is the output rate after decimation; decimation factor is
# rounded to the nearest integer and the actual output rate is printed.
TARGET_FS_HZ = 100.0   # ~5x decimation from 270 Hz


def load_data(input_file):
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows")
    print(df.head())
    required = {"timestamp_us", "angle_counts", "magnet_ok"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{input_file} is missing columns {missing}. "
            f"Expected a raw encoder CSV — did you point at the processed/ folder by mistake?"
        )
    n_bad = (df["magnet_ok"] == 0).sum()
    if n_bad > 0:
        print(f"Dropping {n_bad} rows with magnet_ok=0")
    df = df[df["magnet_ok"] == 1].copy().reset_index(drop=True)
    n_nan = df["timestamp_us"].isna().sum()
    if n_nan > 0:
        print(f"Dropping {n_nan} rows with NaN timestamps")
        df = df.dropna(subset=["timestamp_us"]).reset_index(drop=True)
    n_dup = df["timestamp_us"].duplicated().sum()
    if n_dup > 0:
        print(f"Dropping {n_dup} duplicate timestamps")
        df = df.drop_duplicates(subset="timestamp_us").reset_index(drop=True)
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




def interpolate_to_uniform(signal, t, target_fs_hz):
    t_uniform = np.arange(t[0], t[-1], 1.0 / target_fs_hz)
    signal_uniform = np.interp(t_uniform, t, signal)
    return signal_uniform, t_uniform


def decimate_signal(dist_native, native_fs, target_fs):
    factor = round(native_fs / target_fs)
    if factor < 1:
        factor = 1
    dist_dec = decimate(dist_native, factor, zero_phase=True)
    actual_fs = native_fs / factor
    t_dec = np.arange(len(dist_dec)) / actual_fs
    return dist_dec, t_dec, actual_fs


def run_pipeline(df, target_fs_hz=100.0):
    """
    Core signal processing: loaded DataFrame → arrays at ~target_fs_hz.

    No I/O, no plots, no excluded-segment masking (caller's responsibility).
    Any change to the signal processing pipeline belongs here so that both
    the CLI (process_file) and the API (api.py) stay in sync automatically.

    Returns (t_dec, dist_dec, vel, accel, actual_fs).
    """
    _, angle_unwrapped_counts = unwrap_angle(df)
    dist_m = counts_to_distance(angle_unwrapped_counts, METERS_PER_COUNT)
    t = df["time_s"].values

    pos_diffs = np.diff(t)
    pos_diffs = pos_diffs[pos_diffs > 0]
    if len(pos_diffs) == 0:
        raise ValueError("No positive timestamp diffs — file may be corrupt")
    native_fs = 1.0 / np.median(pos_diffs)

    duration_s = float(t[-1] - t[0])
    if duration_s < 2.0:
        raise ValueError(
            f"Recording too short ({duration_s:.2f} s) — need at least 2 s to decimate"
        )

    dist_native, _ = interpolate_to_uniform(dist_m, t, native_fs)
    dist_dec, t_dec, actual_fs = decimate_signal(dist_native, native_fs, target_fs_hz)
    t_dec = t_dec + t[0]

    vel = np.gradient(dist_dec, 1.0 / actual_fs)
    vel = np.maximum(vel, 0.0)   # swimmer always moves forward; negatives are filter/encoder artefacts

    vel_for_accel, t_for_accel, fs_for_accel = decimate_signal(vel, actual_fs, 5.0)
    t_for_accel = t_for_accel + t[0]
    accel_coarse = np.gradient(vel_for_accel, 1.0 / fs_for_accel)
    accel = np.interp(t_dec, t_for_accel, accel_coarse)

    return t_dec, dist_dec, vel, accel, actual_fs


def export_results(t_uniform, dist_filt, vel, accel, output_file, raw_total_dist):
    out = pd.DataFrame({
        "time_s":    t_uniform,
        "dist_m":    dist_filt,
        "vel_ms":    vel,
        "accel_ms2": accel,
    })
    out.to_csv(output_file, index=False, float_format="%.4f")
    print(f"\nExported {len(out)} rows → {output_file}")
    print(f"  Peak velocity:      {np.nanmax(vel):.3f} m/s")
    print(f"  Peak acceleration:  {np.nanmax(accel):.3f} m/s²")
    print(f"  Total distance:     {raw_total_dist:.3f} m")
    return out


def plot_results(out, output_html):
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
        x=out["time_s"], y=out["vel_ms"],
        name="Velocity (m/s)", line=dict(color="#185fa5", width=1.5)
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=out["time_s"], y=out["accel_ms2"],
        name="Acceleration", line=dict(color="#d85a30", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(24,95,165,0.10)",
    ), row=3, col=1)
    fig.add_hline(y=0, line=dict(color="#888780", width=0.8, dash="dot"), row=3, col=1)
    fig.update_layout(
        title="AS5600 Swim Data",
        height=700,
        template="plotly_white",
        legend=dict(orientation="h", y=-0.08),
        font=dict(size=11),
    )
    fig.update_xaxes(title_text="Time (s)", row=3, col=1)
    fig.write_html(str(output_html))
    webbrowser.open(str(output_html))


def plot_wavelet(t_dec, vel, actual_fs):
    import pywt

    window = int(actual_fs * 3)
    trend = pd.Series(vel).rolling(window, center=True, min_periods=1).mean().values
    vel_detrended = vel - trend

    freqs_target = np.linspace(0.3, 3.0, 120)
    scales = pywt.frequency2scale('cmor1.5-1.0', freqs_target / actual_fs)
    coeffs, freqs_out = pywt.cwt(vel_detrended, scales, 'cmor1.5-1.0',
                                 sampling_period=1.0 / actual_fs)
    power_db = 10 * np.log10(np.abs(coeffs) ** 2 + 1e-12)
    vmin = np.percentile(power_db, 2)
    vmax = np.percentile(power_db, 98)

    fig_wt, ax = plt.subplots(figsize=(14, 4))
    fig_wt.suptitle(f"Velocity Wavelet Scalogram (Morlet CWT, detrended) — {actual_fs:.1f} Hz")
    ax.pcolormesh(t_dec, freqs_out, power_db, shading='gouraud', cmap='inferno',
                  vmin=vmin, vmax=vmax)
    ax.set_ylabel("Freq (Hz)")
    ax.set_xlabel("Time (s)")
    ax.set_ylim(0.3, 3.0)
    plt.tight_layout()
    plt.show()


def process_file(csv_file, output_file, target_fs_hz):
    df = load_data(str(csv_file))
    t_dec, dist_dec, vel, accel, actual_fs = run_pipeline(df, target_fs_hz)
    raw_total_dist = float(dist_dec[-1])   # capture before exclusion masking

    slack_mask_dec = np.zeros(len(t_dec), dtype=bool)
    for start_s, end_s in EXCLUDED_SEGMENTS:
        slack_mask_dec[(t_dec >= start_s) & (t_dec <= end_s)] = True
    if EXCLUDED_SEGMENTS:
        print(f"Excluded {len(EXCLUDED_SEGMENTS)} time range(s)")
    dist_dec[slack_mask_dec] = np.nan
    vel[slack_mask_dec]      = np.nan
    accel[slack_mask_dec]    = np.nan

    print(f"Decimated to: {actual_fs:.1f} Hz")
    print(f"Vel range:   {np.nanmin(vel):.3f} to {np.nanmax(vel):.3f} m/s")
    print(f"Accel range: {np.nanmin(accel):.3f} to {np.nanmax(accel):.3f} m/s²")

    out = export_results(t_dec, dist_dec, vel, accel, str(output_file), raw_total_dist)
    html_path = Path(str(output_file).replace(".csv", ".html"))
    plot_results(out, html_path)


def main():
    parser = argparse.ArgumentParser(description="Process swim encoder CSV data.")
    parser.add_argument("input", nargs="?", default=INPUT_FILE,
                        help="CSV file or folder of CSV files (default: %(default)s)")
    parser.add_argument("--fs", type=float, default=TARGET_FS_HZ,
                        help="Target output rate in Hz after decimation (default: %(default)s). "
                             "Factor is rounded to nearest integer. Native rate printed at runtime.")
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

    errors = []
    for csv_file in csv_files:
        output_file = Path("processed") / f"{csv_file.stem}.csv"
        print(f"\n{'=' * 50}")
        print(f"Processing: {csv_file}  ->  {output_file}")
        print(f"{'=' * 50}")
        try:
            process_file(csv_file, output_file, args.fs)
        except Exception as e:
            print(f"  SKIPPED — {e}")
            errors.append((csv_file, e))

    if errors:
        print(f"\n{len(errors)} file(s) skipped:")
        for path, err in errors:
            print(f"  {path.name}: {err}")


if __name__ == "__main__":
    main()
