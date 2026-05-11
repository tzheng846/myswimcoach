# myswimcoach

Biomechanical swim coaching from an AS5600 magnetic rotary encoder attached to a tethered swim wheel. Extracts stroke metrics and delivers AI coaching feedback via Claude.

## Hardware

- AS5600 magnetic rotary encoder (~270 Hz) logs `timestamp_us`, `angle_counts`, `magnet_ok` to CSV via `logger.py`

## Pipeline

```
logger.py  →  raw/  →  vel_acc_extraction.py  →  processed/  →  metrics.py
                                                               →  coach.py (CLI)
                                                               →  app.py (Streamlit)
```

**`vel_acc_extraction.py`** — converts raw encoder counts to velocity and acceleration
- Unwraps angle counts, converts to meters using wheel circumference
- Resamples to uniform 100 Hz grid via decimation (Chebyshev lowpass)
- Outputs `time_s, dist_m, vel_ms, accel_ms2`

**`metrics.py`** — breaststroke feature extraction (no I/O, pure functions)
- Detects ramp-up vs. steady phase, segments cycles by arm-pull peaks
- Session metrics: stroke rate, fatigue index, DPS, coast fraction, CV, and more
- Per-cycle metrics: arm peak velocity, trough velocity, impulse, duration

**`coach.py`** — CLI coaching feedback via Claude API
- Reads a processed CSV, computes metrics, streams AI coaching feedback
- Stroke-specific biomechanics context (freestyle or breaststroke)

**`app.py`** — Streamlit web UI
- Interactive velocity + acceleration chart with labeled cycle markers
- Time and cycle range sliders (bidirectionally synced)
- Session stats cards with hover tooltips
- Per-cycle line charts (arm peak, trough, coast fraction, DPS)
- Multi-turn chat with Claude using session data as context

## Usage

```bash
# 1. Record a session (requires Arduino on serial port)
python logger.py

# 2. Process a file or folder
python vel_acc_extraction.py raw/session.csv
python vel_acc_extraction.py raw/

# 3. CLI coaching feedback
python coach.py processed/session.csv --stroke breaststroke
python coach.py processed/session.csv --stroke freestyle --start 12 --end 55

# 4. Launch the web app
streamlit run app.py
```

## Setup

```bash
pip install -r requirements.txt
```

Add your Anthropic API key to a `.env` file in the repo root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

For Streamlit Cloud deployment, add the key under **App settings → Secrets** instead.

## Dependencies

```
numpy  scipy  pandas  plotly  anthropic  streamlit
```
