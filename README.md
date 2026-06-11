# Swimnetics — Backend

Biomechanical swim coaching from a tethered AS5600 magnetic encoder wheel. Coaches clip the device to a diving block, attach the tether to a swimmer, and record a session from an iPhone. The pipeline extracts stroke-level metrics and delivers them back to the app in seconds — no laptop at poolside.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  iOS App  (swimnetics-mobile — React Native + Expo bare)        │
│  ├── BLE: connects to ESP32 via Nordic UART Service             │
│  ├── Records raw CSV (angle_counts @ ~270 Hz)                   │
│  ├── Uploads via multipart POST /process                        │
│  └── Displays velocity chart, stroke metrics, session history   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (Bearer JWT)
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI  on Railway  (api.py)                                  │
│  ├── POST /process → vel_acc_extraction.py + metrics.py         │
│  ├── PATCH /sessions/:id  → name, notes, star, stroke_type      │
│  ├── DELETE /sessions/:id                                       │
│  ├── GET /health                                                │
│  └── Auth: Supabase JWT verified via supabase-py auth.get_user  │
└────────────┬──────────────────────────┬─────────────────────────┘
             │                          │
┌────────────▼──────────┐  ┌────────────▼──────────────────────── ┐
│  Supabase Postgres    │  │  Supabase Storage                     │
│  ├── coaches          │  │  └── raw-csvs/  (uploaded session CSV)│
│  ├── athletes         │  └───────────────────────────────────────┘
│  ├── sessions         │
│  │   metrics_json     │
│  │   velocity_profile │
│  │   distance_profile │
│  └── (devices, teams) │
└───────────────────────┘
```

**Related repos:**
- iOS app: `Desktop/swimnetics-mobile/`
- Railway deployment: https://swimnetics-api-production.up.railway.app
- Supabase project: `ujrotuijxrbscjhzekjk.supabase.co`

---

## Python Pipeline

```
raw/<session>.csv
    └── vel_acc_extraction.py   → time_s, dist_m, vel_ms, accel_ms2 @ 100 Hz
            └── metrics.py      → session metrics dict + per-cycle list
                    └── api.py  → JSON response to iOS app
                                → saves to Supabase sessions table
```

### `vel_acc_extraction.py`

Converts raw encoder counts to velocity and acceleration.

1. Drop `magnet_ok == 0` rows
2. Unwrap angle counts (0→4095 rollover)
3. Convert counts → meters (`count / 4096 × π × 0.06`)
4. Resample to uniform grid, decimate to 100 Hz (Chebyshev lowpass via `scipy.signal.decimate`)
5. `np.gradient` → velocity; decimate to 5 Hz → acceleration → interpolate back

Key constants (edit per deployment):
- `WHEEL_DIAMETER_M = 0.06` — must match `computeVelFromSamples` in `RecordScreen.js`
- `TARGET_FS_HZ = 100`

### `metrics.py`

Pure breaststroke feature extraction. No I/O, no plots.

**Top-level:** `compute_session_metrics(t, vel, dist)` → `{session: dict, cycles: list, data_quality: dict}`

**Session keys:** `lap_time_s`, `total_dist_m`, `baseline_end_s`, `stroke_rate_spm`, `stroke_count`, `mean_vel_ms`, `max_vel_ms`, `mean_arm_peak_vel_ms`, `cv_arm_peak_vel`, `mean_isi_s`, `cv_isi`, `mean_dps_m`, `mean_impulse_m`, `mean_coast_fraction`, `mean_trough_vel_ms`, `fatigue_index_pct`, `pct_cycles_with_kick`, `mean_arm_kick_ratio`, `mean_arm_kick_delay_s`

**Data quality keys:** `magnet_dropout_pct`, `cycle_count`, `outlier_cycle_count`, `plausible_fraction`, `kick_metrics_reliable`

Segmentation: trough-based (glide-phase minima where `vel < 0.20 × v95`). Dive detection identifies the pre-stroke underwater pulldown phase; strokes are counted from the first post-dive trough only.

### `api.py`

FastAPI server. Single entry point for the iOS app.

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | none | Railway health check |
| `POST /process` | Bearer JWT | Upload CSV → run pipeline → save session → return JSON |
| `PATCH /sessions/:id` | Bearer JWT | Update name, notes, is_starred, stroke_type |
| `DELETE /sessions/:id` | Bearer JWT | Soft-delete a session |

`/process` response shape:
```json
{
  "session": { ...metrics... },
  "cycles": [ ...per-cycle dicts... ],
  "data_quality": { "magnet_dropout_pct": 0.4, "plausible_fraction": 0.95, ... },
  "time": [0.0, 0.01, ...],
  "velocity": [0.0, 0.12, ...],
  "distance": [0.0, 0.001, ...],
  "initial_phase": { "dive_detected": true, "dive_duration_s": 1.2, ... },
  "session_id": "uuid"
}
```

---

## Development Setup

```bash
pip install -r requirements.txt
```

Environment variables (set in Railway for production; `.env` for local):
```
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

Run locally:
```bash
uvicorn api:app --reload --port 8000
```

Run the Python pipeline directly:
```bash
python vel_acc_extraction.py raw/session.csv
python metrics.py processed/session.csv --plot
```

Run tests:
```bash
pytest tests/
```

---

## Hardware

- **ESP32-S3** + **AS5600** magnetic rotary encoder
- Logs `timestamp_us`, `angle_counts`, `magnet_ok` at ~270 Hz
- Communicates with iOS via Bluetooth LE (Nordic UART Service)
- BOM ~$30; wheel diameter 0.06 m (matches `WHEEL_DIAMETER_M`)
- Firmware in `ESP_32_V5/` or `as5600_logger_esp32/`

BLE protocol (locked):
```
NUS Service:  6E400001-B5A3-F393-E0A9-E50E24DCCA9E
TX (notify):  6E400003-...  — streams 14-byte packets (2 × 7-byte samples)
RX (write):   6E400002-...  — accepts START\n / STOP\n commands
Sample:       [uint32 timestamp_us][uint16 angle_counts][uint8 magnet_ok]
```

---

## Streamlit App (`app.py`)

Desktop/iPad analysis tool. Not the primary product path. Used for deep-dive analysis: per-cycle charts, compare mode, AI coaching via Claude API. Runs locally or on Streamlit Cloud.

```bash
streamlit run app.py
```

Requires `ANTHROPIC_API_KEY` in `.env`.

---

## Other Files

| File | Status | Purpose |
|------|--------|---------|
| `vel_acc_extraction_testing*.py` | Experimental | Diagnostic variants (wavelet, Butterworth, FS slider) |
| `swim_metrics.ipynb` | Exploratory | Jupyter analysis notebook |
| `logger.py` / `logger_ble.py` | Legacy | Early serial/BLE loggers; ESP32 firmware handles this now |
| `COACHING_PHILOSOPHY.md` | Active | UX principles for metric presentation |
| `STRATEGY.md` | Active | Product strategy and business model |
| `HANDOFF.md` | Historical | Early segmentation work (May 2026); trough method selected |
| `dataset_structure.md` | Off-roadmap | Video/pose dataset; video analysis permanently deferred |
