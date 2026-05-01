# myswimcoach

Extracting and analyze wimmer's stroke metrics.

## Hardware

- Logs `timestamp_us`, `angle_counts`, `magnet_ok` to CSV via `logger.py`

## Pipeline

```
logger.py  →  raw CSV  →  vel_acc_extraction.ipynb  →  processed/  →  swim_metrics.ipynb
```

**`vel_acc_extraction.ipynb`** — converts raw encoder counts to velocity and acceleration
- Unwraps angle, converts counts to meters
- Resamples to uniform 50 Hz grid
- Butterworth lowpass filter
- Outputs `time_s, dist_m, vel_ms, accel_ms2`

**`swim_metrics.ipynb`** — extracts 8 biomechanical metrics from the processed CSV
1. Stroke Rate (FFT)
2. Stroke Count & Timing (peak detection)
3. Pull / Recovery Asymmetry
4. Velocity Variability (CV)
5. Dead Spot Duration
6. Propulsive Impulse per Stroke
7. Stroke Smoothness (Jerk)
8. Fatigue Index

## Usage

```bash
# 1. record a session
python logger.py

# 2. open vel_acc_extraction.ipynb, set INPUT_FILE, run all cells
# output → processed/<session>.csv

# 3. open swim_metrics.ipynb, update the filename, run all cells
```

## Dependencies

```
numpy  scipy  pandas  matplotlib
```
