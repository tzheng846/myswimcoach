# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Backend for Swimnetics — a biomechanical swim coaching tool. An AS5600 magnetic rotary encoder on a tethered wheel logs angle counts at ~270 Hz. The iOS app records via BLE, uploads a raw CSV to this FastAPI server, which runs the signal pipeline and returns metrics JSON. Results are saved to Supabase and displayed on the phone.

**Full-system map (folder roles, connection matrix, known drift): see [CODEBASE-AUDIT.md](CODEBASE-AUDIT.md) (2026-06-18).**

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

The Streamlit `app.py` is a desktop analysis tool — not the primary product path. The iOS app is. `coach.py` (AI coaching prompts) is the **shared** system-prompt builder used by both `app.py` (Streamlit demo) and `api.py` (the `/coach/chat` endpoint, Phase 31/33).

## Pipeline

```
logger → raw/<session>.csv → vel_acc_extraction.py → processed/<session>.csv → metrics.py
                                                                              → api.py
```

**Raw CSV columns:** `timestamp_us`, `angle_counts`, `magnet_ok`

**Processed CSV columns:** `time_s`, `dist_m`, `vel_ms`, `accel_ms2` at the decimated rate (~89.5 Hz — see "Sample rate" below; it is NOT 100)

## Key files

| File | Role |
|------|------|
| `api.py` | FastAPI server — all endpoints (see "api.py — FastAPI endpoints" below) |
| `vel_acc_extraction.py` | Signal processing: counts → velocity at the decimated rate (~89.5 Hz — see "Sample rate" below) |
| `metrics.py` | Breaststroke feature extraction (pure functions, no I/O) |
| `annotations.py` | Trial-annotation contract (pure) — phase-key canon, `build_seed` (draft from metrics_json), `validate_annotation`, `annotation_to_overrides` (times → `compute_session_metrics(manual=...)` indices). Phase 47 |
| `web/` | Next.js 16 website — marketing site + coach portal + parent report pages |
| `supabase/` | schema.sql + patches — ⚠ stale vs live DB (see CODEBASE-AUDIT.md §5.2). patch_07 (session_annotations + `videos` bucket + sessions.video_path/video_origin_s) and patch_08 (sessions.metrics_json_auto) APPLIED LIVE 2026-07-11/12; patch_09 (sessions.sample_rate_hz, Phase 52) |
| `ESP_32_V5/` | Current firmware 1.1.0 (buffer-and-dump); older sketch dirs are legacy |
| `app.py` | Streamlit desktop UI (dev/analysis tool, not production path) |
| `coach.py` | AI coaching prompt builder — shared by app.py (Streamlit) + api.py `/coach/chat` |
| `ratings.py` | Coach-friendly rating engine (pure) — 4 pillars + 0–100 score + trend; shared source of truth for `GET /sessions/{id}/ratings` + web/iOS pillar cards. Contract: `.paul/phases/36-metric-ratings/RATINGS-SPEC.md`. DRAFT breaststroke thresholds (coach review owed) |
| `drills.py` | Drill library + metric tag-matching recommender (pure) — used by `/coach/chat` |
| `roster_metrics.py` | Team/roster aggregation (pure) — powers `/coach/chat` team questions |
| `tests/` | Pytest suite — test_metrics.py + test_api.py + test_ratings.py + test_annotations.py (supabase mocked, no network) |

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

Dependencies: see `requirements.txt` (Railway install) + `requirements-dev.txt`. Note: dev tools `fetch_sessions.py`/`fetch_annotations.py`/`pipeline_view.py` also need `python-dotenv`, which is not in requirements.txt. `fetch_annotations.py` dumps the annotation ground-truth set to `annotations_export.json` (Phase 47 → 16-06 tuning).

## Key constants to update per deployment

In `vel_acc_extraction.py`:
- `WHEEL_DIAMETER_M = 0.06` — single source of truth (the RecordScreen.js copy was removed with the live velocity graph in Phase 21-02)
- `TARGET_FS_HZ = 100` — the **requested** output rate. It is not the achieved one (see below)
- `EXCLUDED_SEGMENTS` — `(start_s, end_s)` pairs to NaN out; applied only in the standalone `process_file()` path, never in `run_pipeline()` used by api.py

## Sample rate — never assume 100 Hz (Phase 52)

`decimate_signal` decimates by an **integer** factor, so the requested `TARGET_FS_HZ` is
essentially never achieved:

```
factor    = round(native_fs / target_fs)   # round(268.5 / 100) = 3
actual_fs = native_fs / factor             # 268.5 / 3 = 89.5 Hz, NOT 100
```

`run_pipeline` returns `actual_fs` as its fifth value. **`sessions.sample_rate_hz` (patch_09) is
the authoritative per-session rate**, written by `/process` and by `seed_demo_team.py`.

- Reading a stored profile? Get the rate from the row — `api.py:_session_fs(row)` on the backend,
  `row.sample_rate_hz` on the web. `annotations.py` takes it as an `fs_hz` argument.
- **NULL means the session predates Phase 52** and has no recorded rate. Every reader falls back to
  `annotations.FS_HZ` (100), which reproduces exactly how those rows always behaved. Do not
  backfill it with 100 — that would erase the distinction between "genuinely 100" and "unknown".
- Historical note: before Phase 52 the rate was discarded at write time and six consumers assumed
  100, which made the annotate page under-report duration by ~11% and shifted every time-derived
  metric on any session recomputed from an annotation (API-AUDIT.md F2 + F3).
- Still assuming 100, both out of scope in Phase 52: iOS `ReportCardScreen.js` client-side CSV
  export, and `web/components/portal/CompareChart.js` (two sessions may have two different rates).

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
- `segment_cycles_wavelet(t, vel)` — **production segmenter for ALL strokes** (Phase 16-05): Morlet CWT ridge → instantaneous stroke rate → integer-phase-crossing boundaries. Same cycle-dict shape as the trough segmenter. Shipped at placeholder quality (`segmentation_reliable=False`).
- `segment_cycles_trough(t, vel, T_cycle)` — trough-based segmentation (glide-phase minima); **kept as a never-called backup** (user decision: wavelet only, no fallback)
- `extract_cycle_peaks(vel, cycles)` — mutates in-place; adds arm/kick peak data
- `compute_session_metrics(t, vel, dist, head_waist_m=0.0, manual=None)` → `{session, cycles, data_quality, initial_phase}`. `manual` (Phase 47) = human-annotation overrides — any subset of `baseline_end_idx` / `ip_end_idx` / `swim_end_idx` (exclusive) / `cycle_bounds` (full-trace `(start, end)` pairs; bypasses the wavelet segmenter). Omitted keys fall back to auto-detection; `manual=None` path is identical to pre-47 behavior. Human `cycle_bounds` set `segmentation_reliable=True`.

**Session metric keys:** `lap_time_s`, `total_dist_m`, `baseline_end_s`, `stroke_rate_spm`, `stroke_count`, `mean_vel_ms`, `max_vel_ms`, `mean_arm_peak_vel_ms`, `cv_arm_peak_vel`, `mean_isi_s`, `cv_isi`, `mean_dps_m`, `mean_impulse_m`, `mean_coast_fraction`, `mean_trough_vel_ms`, `fatigue_index_pct`, `pct_cycles_with_kick`, `mean_arm_kick_ratio`, `mean_arm_kick_delay_s`

**Data quality keys:** `magnet_dropout_pct`, `cycle_count`, `outlier_cycle_count`, `plausible_fraction`, `kick_metrics_reliable`, `segmentation_reliable`

**Known limitation:** kick-related metrics are unreliable — `kick_metrics_reliable = False` is always set. Difficulty resolving arm-pull and kick as two distinct velocity peaks when biomechanically close in time.

## v95 is swim-windowed, not full-trace (Phase 57)

`v95` — the 95th percentile of `|vel|` that every velocity threshold in `metrics.py` is scaled by —
is computed over the **swim window**, via `_window_v95(vel, start, end)`:

- `compute_session_metrics` → `vel[baseline_end : swim_end]`. The statement sits *below* the
  phase-detection and manual-override blocks because those produce its bounds — do not hoist it back
  up next to `fs`.
- `extract_cycle_peaks` → the span the cycles cover, `vel[cycles[0].start_idx : cycles[-1].end_idx]`.
- An empty window falls back to the full trace rather than raising.

Before Phase 57 both took the percentile over the **entire** trace. A recording keeps running after
the swimmer touches, so a long near-zero tail dragged the percentile down. Measured on real CSVs
(`raw/leo1`, `raw/carlos_fr_1`): v95 rises **+1.5–2%** on traces with no tail and **+6–12%** with the
~45% tail typical of the 2026-08-05 sessions.

**What actually changed, and what didn't** (measured, not assumed):
- `dead_spot_s` shifts — `_DEAD_SPOT_THRESH × v95`. Observed +0.6% (no tail) to +3.7% (45% tail).
- Arm/kick peak **detection** shifts — `_PEAK_MIN_PROM_FRAC × v95` is a prominence floor, so this
  can in principle add or drop a peak. Cycle counts were unchanged on every file tested.
- `coast_fraction` does **not** change. It is scaled by each cycle's own `arm_peak_vel`, not v95.
- `stroke_rate_spm` and segmentation do not change.

Consequence to keep in view: `dead_spot_s` computed before this change is not comparable with one
computed after. Two other `v95` sites are deliberately untouched — `segment_cycles_trough` (the
never-called backup) and `detect_initial_phase` (already windowed on `vel_search`).

**Segmentation: wavelet ridge, placeholder quality (Phase 16-05).** `segment_cycles_wavelet` is the live segmenter for all four strokes — `segmentation_reliable = False` is set for every wavelet-segmented session (it flips True only when metrics are recomputed from human annotation boundaries via `manual=`, Phase 47), because the 16-04 breaststroke cross-check was weak (3/8 sessions within ±5 SPM of the trusted trough rate; some ridges rail the 120-SPM ceiling). It is shipped deliberately as a placeholder per user decision ("not enough data; ship as placeholder; wavelet only, no fallback") — the trough segmenter is the breaststroke-validated method but is retained only as never-called backup. The open tuning work (rate accuracy, boundary placement, ceiling-railing) is a future plan; see `.paul/phases/16-freestyle-support/16-04-SUMMARY.md`. HMM-based sub-phase labeling (arm-pull vs. kick, left-arm vs. right-arm) is a separate, later effort — the pose pipeline (`merge_streams.py`) would supply its training labels.

## api.py — FastAPI endpoints

- `GET /health` — Railway health check (no auth)
- `POST /process` — upload CSV, run pipeline, save to Supabase, return metrics JSON; enforces tier limits (402)
- `PATCH /sessions/{session_id}` — update name, notes, is_starred (only — stroke_type is NOT patchable)
- `DELETE /sessions/{session_id}` — deletes the DB row + raw CSV from storage (storage removal non-fatal)
- `GET /sessions/{session_id}/export` — CSV download at the session's own rate (`sample_rate_hz`); ⚠ no caller anywhere (iOS builds its CSV client-side)
- `GET /sessions/{session_id}/ratings` — coach-friendly pillar ratings (band / 0–100 score / trend) from `ratings.py`; auth + ownership; baseline = athlete's previous same-stroke session. Consumed by web + iOS pillar cards (Phase 36; see RATINGS-SPEC.md)
- `POST /coach/chat` — AI coaching chat; bounded tool-use loop (`coach.py` + `roster_metrics.py` + `drills.py`), coach-scoped; returns `{reply, data}`; requires `ANTHROPIC_API_KEY` (503 if unset). Phase 31/33
- `GET /sessions/{session_id}/annotations` — saved annotation (or null) + auto-seeded draft from metrics_json + video info + duration_s; consumed by the web annotate page (Phase 47)
- `PUT /sessions/{session_id}/annotations` — upsert the annotation, then **auto-recompute** `metrics_json` from the human boundaries via `compute_session_metrics(manual=...)` when ≥2 cycle boundaries exist; original auto result backed up ONCE in `sessions.metrics_json_auto`; recompute failure is non-fatal (`recompute_error` in response, annotation kept); 422 `{errors:[...]}` on bad docs
- `DELETE /sessions/{session_id}/annotations` — remove the annotation + restore `metrics_json` from `metrics_json_auto`
- `POST /sessions/{session_id}/video` — attach a session video (multipart → private `videos` bucket at `{session_id}.mp4`) and/or update `video_origin_s` (session-clock time at video t=0; 44-03 end-anchor convention)
- `GET /sessions/{session_id}/video-url` — time-limited signed URL (3600 s); video bytes never proxy through the API
- `GET /annotations/export` — all of the coach's annotated sessions (ground truth for 16-06 segmenter tuning); mirrored locally by `fetch_annotations.py`
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
