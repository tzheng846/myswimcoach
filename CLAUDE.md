# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Backend for Swimnetics — a biomechanical swim coaching tool. An AS5600 magnetic rotary encoder on a tethered wheel logs angle counts at ~270 Hz. The iOS app records via BLE, uploads a raw CSV to this FastAPI server, which runs the signal pipeline and returns metrics JSON. Results are saved to Supabase and displayed on the phone.

**Full-system map (folder roles, connection matrix, known drift): see [CODEBASE-AUDIT.md](CODEBASE-AUDIT.md) (2026-06-12).**

## System connections

```
iOS app (separate repo: Desktop/swimnetics-mobile)
  → POST /process (multipart, Bearer JWT)
      → vel_acc_extraction.py + metrics.py
      → saves session to Supabase Postgres
      → uploads raw CSV to Supabase Storage (raw-csvs bucket)
  → PATCH/DELETE /sessions/:id (name, notes, star)
  → GET /devices, PATCH/DELETE /devices/:chip_id, POST /athletes

Website (web/ — Next.js 16, Vercel target; marketing + coach portal + parent reports)
  → reads athletes/sessions/reports via supabase-js (RLS)
  → writes via this API (POST /athletes, PATCH/DELETE /sessions); exception:
    reports rows are written directly via supabase-js
  → public parent pages /report/[token] ← GET /reports/{token} (no auth, service role)

Supabase: ujrotuijxrbscjhzekjk.supabase.co
Railway:  https://swimnetics-api-production.up.railway.app
```

The Streamlit `app.py` is a desktop analysis tool — not the primary product path. The iOS app is. `coach.py` (AI coaching prompts) is imported only by `app.py`, not by `api.py`.

## Pipeline

```
logger → raw/<session>.csv → vel_acc_extraction.py → processed/<session>.csv → metrics.py
                                                                              → api.py
```

**Raw CSV columns:** `timestamp_us`, `angle_counts`, `magnet_ok`

**Processed CSV columns:** `time_s`, `dist_m`, `vel_ms`, `accel_ms2` at 100 Hz

## Key files

| File | Role |
|------|------|
| `api.py` | FastAPI server — all endpoints (see "api.py — FastAPI endpoints" below) |
| `vel_acc_extraction.py` | Signal processing: counts → velocity @ 100 Hz |
| `metrics.py` | Breaststroke feature extraction (pure functions, no I/O) |
| `web/` | Next.js 16 website — marketing site + coach portal + parent report pages |
| `supabase/` | schema.sql + patches — ⚠ stale vs live DB (see CODEBASE-AUDIT.md §5.2) |
| `ESP_32_V5/` | Current firmware 1.1.0 (buffer-and-dump); older sketch dirs are legacy |
| `app.py` | Streamlit desktop UI (dev/analysis tool, not production path) |
| `coach.py` | AI coaching prompt builder — used only by app.py |
| `tests/` | Pytest suite — test_metrics.py + test_api.py (supabase mocked, no network) |

## Running

```bash
# FastAPI (production entry point)
uvicorn api:app --reload --port 8000

# Pipeline (standalone)
python vel_acc_extraction.py raw/session.csv
python metrics.py processed/session.csv --plot

# Tests
pytest tests/
```

Dependencies: see `requirements.txt` (Railway install) + `requirements-dev.txt`. Note: dev tools `fetch_sessions.py`/`pipeline_view.py` also need `python-dotenv`, which is not in requirements.txt.

## Key constants to update per deployment

In `vel_acc_extraction.py`:
- `WHEEL_DIAMETER_M = 0.06` — single source of truth (the RecordScreen.js copy was removed with the live velocity graph in Phase 21-02)
- `TARGET_FS_HZ = 100` — output sample rate after decimation
- `EXCLUDED_SEGMENTS` — `(start_s, end_s)` pairs to NaN out; applied only in the standalone `process_file()` path, never in `run_pipeline()` used by api.py

## Signal processing architecture

`vel_acc_extraction.py` processing order:
1. Drop rows where `magnet_ok == 0`
2. Unwrap angle counts (handles 0→4095 rollovers)
3. Convert counts → meters using wheel circumference / 4096
4. Resample to uniform native-rate grid via linear interpolation
5. `scipy.signal.decimate` to `TARGET_FS_HZ` (Chebyshev lowpass — no separate filter needed)
6. `np.gradient` → velocity
7. Decimate velocity to ~5 Hz, `np.gradient` → acceleration, interpolate back to full rate

**No Hampel or other post-gradient filters.** Velocity troughs between strokes are real signal.

## metrics.py — breaststroke feature extraction

All functions are pure (no I/O, no plots).

**Public API:**
- `detect_phases(t, vel)` — returns `{baseline_end, steady_start}` indices
- `segment_cycles(t, vel, T_cycle)` — trough-based segmentation (glide-phase minima)
- `extract_cycle_peaks(vel, cycles)` — mutates in-place; adds arm/kick peak data
- `compute_session_metrics(t, vel, dist)` → `{session, cycles, data_quality, initial_phase}`

**Session metric keys:** `lap_time_s`, `total_dist_m`, `baseline_end_s`, `stroke_rate_spm`, `stroke_count`, `mean_vel_ms`, `max_vel_ms`, `mean_arm_peak_vel_ms`, `cv_arm_peak_vel`, `mean_isi_s`, `cv_isi`, `mean_dps_m`, `mean_impulse_m`, `mean_coast_fraction`, `mean_trough_vel_ms`, `fatigue_index_pct`, `pct_cycles_with_kick`, `mean_arm_kick_ratio`, `mean_arm_kick_delay_s`

**Data quality keys:** `magnet_dropout_pct`, `cycle_count`, `outlier_cycle_count`, `plausible_fraction`, `kick_metrics_reliable`

**Known limitation:** kick-related metrics are unreliable — `kick_metrics_reliable = False` is always set. Difficulty resolving arm-pull and kick as two distinct velocity peaks when biomechanically close in time.

**Planned: multi-stroke segmentation.** `segment_cycles_trough` anchors on breaststroke's glide-phase trough — freestyle and butterfly have no such dead spot (continuous/near-simultaneous propulsion, no near-zero velocity). Direction: matrix-profile motif-matching (`stumpy`: self-join → consensus-stroke template → `match()`) — a shape-based, stroke-agnostic criterion ("does this window's trajectory resemble a stroke") rather than a threshold on velocity depth. HMM-based sub-phase labeling (arm-pull vs. kick, left-arm vs. right-arm) is a separate, later effort — the pose pipeline (`merge_streams.py`) would supply its training labels.

## api.py — FastAPI endpoints

- `GET /health` — Railway health check (no auth)
- `POST /process` — upload CSV, run pipeline, save to Supabase, return metrics JSON; enforces tier limits (402)
- `PATCH /sessions/{session_id}` — update name, notes, is_starred (only — stroke_type is NOT patchable)
- `DELETE /sessions/{session_id}` — deletes the DB row + raw CSV from storage (storage removal non-fatal)
- `GET /sessions/{session_id}/export` — 100 Hz CSV download; ⚠ no caller anywhere (iOS builds its CSV client-side)
- `GET /reports/{token}` — public parent report payload (no auth, service role)
- `GET /devices`, `PATCH/DELETE /devices/{chip_id}` — device list (+session counts), rename, deregister
- `POST /athletes` — create athlete; enforces athlete limit (402)
- `POST /billing/checkout-session`, `POST /billing/portal-session`, `GET /billing/status`, `POST /billing/webhook` — Stripe; ⚠ no client UI calls these yet

Auth: Supabase Bearer JWT verified via `supabase-py auth.get_user()`. All endpoints require auth except `/health`, `/reports/{token}`, `/billing/webhook`, and `/billing/complete`.

Supabase admin client (service role key) used for writes. Anon client used for auth verification.

## Diagnostic / experimental files

- `vel_acc_extraction_testing.py` — wavelet diagnostics
- `vel_acc_extraction_test2.py` — alternate Butterworth + SG approach
- `vel_acc_extraction_testing3.py` — interactive FS slider + FFT/CWT

These are exploratory. `vel_acc_extraction.py` is the production file.

## Wavelet notes

The Morlet CWT (`cmor1.5-1.0`) on raw velocity produces dark nodes at stroke boundaries because velocity genuinely touches near-zero between strokes. Detrend with a 3-second rolling mean before CWT for a clean stroke-rate ridge.
