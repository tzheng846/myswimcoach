# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **START HERE — the current, dated sources of truth.** Do **not** describe pipeline mechanism or the
> "current phase" from the orientation below or from memory; the sections here are stable orientation
> only, and these two files are authoritative and kept current:
> - **How the pipeline works** — signal, race-phase model, boundary detectors, metrics registry:
>   **[PIPELINE.md](PIPELINE.md)**
> - **What's in flight / owed right now:** **[.paul/STATE.md](.paul/STATE.md)**
> - Data map (stores, endpoints, jsonb field dictionary): [DATA-FLOW.md](DATA-FLOW.md) (2026-08-13) ·
>   Phase index: [.paul/ROADMAP.md](.paul/ROADMAP.md)

## What this project does

Backend for Swimnetics — a biomechanical swim coaching tool. An AS5600 magnetic rotary encoder on a tethered wheel logs angle counts at ~270 Hz. The iOS app records via BLE, uploads a raw CSV to this FastAPI server, which runs the signal pipeline and returns metrics JSON. Results are saved to Supabase and displayed on the phone.

**Data flow — where every byte lives, who writes it, who reads it back, and why: see
[DATA-FLOW.md](DATA-FLOW.md) (2026-08-13).** Authoritative for stores, the field dictionary
(including inside every jsonb payload), the endpoints and their callers, and the
reads-bypass-the-API pattern.

**Folder roles, build/deploy state, version-control gaps: see [CODEBASE-AUDIT.md](CODEBASE-AUDIT.md)
(2026-06-18).** ⚠ Its §4 connection matrix is superseded by DATA-FLOW.md.

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

The Streamlit `app.py` is a desktop analysis tool — not the primary product path. The iOS app is. `coach.py` (AI coaching prompts) is the **shared** system-prompt builder used by both `app.py` (Streamlit demo) and `api.py` (the `/coach/chat` endpoint).

## Pipeline

```
logger → raw/<session>.csv → vel_acc_extraction.py → processed/<session>.csv → metrics.py
                                                                              → api.py
```

**Raw CSV columns:** `timestamp_us`, `angle_counts`, `magnet_ok`

**Processed CSV columns:** `time_s`, `dist_m`, `vel_ms`, `accel_ms2` at the decimated rate (~89.5 Hz — see [PIPELINE.md §1](PIPELINE.md); it is NOT 100)

## Key files

| File | Role |
|------|------|
| `api.py` | FastAPI server — all endpoints (see "api.py — FastAPI endpoints" below) |
| `vel_acc_extraction.py` | Signal processing: counts → velocity at the decimated rate. See [PIPELINE.md §1](PIPELINE.md) |
| `metrics.py` | Stroke feature extraction — all four strokes (pure, no I/O). Phase-boundary detectors + cycle segmenters. See [PIPELINE.md §3,5,7](PIPELINE.md) |
| `phase_metrics.py` | Race-phase metric registry (`MetricSpec`) + `compute_phases()` engine (pure). Powers `metrics_json.phases`. See [PIPELINE.md §6](PIPELINE.md) |
| `annotations.py` | Trial-annotation contract (pure) — phase-key canon, `build_seed` (draft from metrics_json), `validate_annotation`, `annotation_to_overrides` (times → `compute_session_metrics(manual=...)` indices) |
| `web/` | Next.js 16 website — marketing site + coach portal + parent report pages |
| `supabase/` | schema.sql + patches — ⚠ stale vs live DB (see CODEBASE-AUDIT.md §5.2 / DATA-FLOW.md). patch_09 = `sessions.sample_rate_hz`; later patches (video/session_videos/recording_token) tracked in DATA-FLOW.md |
| `ESP_32_V5/` | Current firmware 1.1.0 (buffer-and-dump); older sketch dirs are legacy |
| `app.py` | Streamlit desktop UI (dev/analysis tool, not production path) |
| `coach.py` | AI coaching prompt builder — shared by app.py (Streamlit) + api.py `/coach/chat` |
| `ratings.py` | Coach-friendly rating engine (pure) — 4 pillars + 0–100 score + trend; shared by `GET /sessions/{id}/ratings` + web/iOS pillar cards. Contract: `.paul/phases/36-metric-ratings/RATINGS-SPEC.md`. DRAFT breaststroke thresholds |
| `drills.py` | Drill library + metric tag-matching recommender (pure) — used by `/coach/chat` |
| `roster_metrics.py` | Team/roster aggregation (pure) — powers `/coach/chat` team questions |
| `tests/` | Pytest suite (supabase mocked, no network) |

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

Dependencies: see `requirements.txt` (Railway install) + `requirements-dev.txt`. Note: dev tools `fetch_sessions.py`/`fetch_annotations.py`/`pipeline_view.py` also need `python-dotenv`, which is not in requirements.txt. `fetch_annotations.py` dumps the annotation ground-truth set to `annotations_export.json` (segmenter tuning).

## Key constants to update per deployment

In `vel_acc_extraction.py`:
- `WHEEL_DIAMETER_M = 0.06` — single source of truth
- `TARGET_FS_HZ = 100` — the **requested** output rate; NOT the achieved one (see [PIPELINE.md §1](PIPELINE.md))
- `EXCLUDED_SEGMENTS` — `(start_s, end_s)` pairs to NaN out; applied only in the standalone `process_file()` path, never in `run_pipeline()` used by api.py

## Signal processing & metrics → see [PIPELINE.md](PIPELINE.md)

The full mechanism — sample rate (per-session, never assume 100 Hz), the `vel_acc_extraction.py`
processing order, `v95` windowing, stroke-cycle segmentation (wavelet / `_learned_boundaries`,
table-driven per stroke), the **race-phase model + the three breakout detectors**, and the
`phase_metrics.py` metric registry — is documented as **current fact** in
[PIPELINE.md](PIPELINE.md). Load-bearing rules that bite if forgotten:

- **No Hampel or post-gradient filter.** Velocity troughs between strokes are real signal.
- **Never assume 100 Hz.** Decimation is by an integer factor (~89.5 Hz typical); read the rate from
  `sessions.sample_rate_hz` (NULL → fall back to `annotations.FS_HZ` = 100; do **not** backfill NULL
  with 100 — it erases "genuinely 100" vs "unknown").
- **`kick_metrics_reliable` and `segmentation_reliable` are always `False`** on the auto path; the
  latter flips `True` only when metrics are recomputed from human cycle bounds (`manual=`).
- **Detrend before CWT** — see Wavelet notes below.

## api.py — FastAPI endpoints

- `GET /health` — Railway health check (no auth)
- `POST /process` — upload CSV, run pipeline, save to Supabase, return metrics JSON (incl. the additive `phases` object from `phase_metrics.compute_phases`); enforces tier limits (402)
- `POST /sessions/{session_id}/recompute` — re-derive `metrics_json.phases` from the STORED velocity/distance/accel profiles (no raw-CSV read); the backfill seam for newly-added phase metrics
- `PATCH /sessions/{session_id}` — update name, notes, is_starred (only — stroke_type is NOT patchable)
- `DELETE /sessions/{session_id}` — deletes the DB row + raw CSV from storage (storage removal non-fatal)
- `GET /sessions/{session_id}/export` — CSV download at the session's own rate (`sample_rate_hz`); ⚠ no caller (iOS builds its CSV client-side)
- `GET /sessions/{session_id}/ratings` — coach-friendly pillar ratings from `ratings.py`; auth + ownership; baseline = athlete's previous same-stroke session
- `POST /coach/chat` — AI coaching chat; bounded tool-use loop (`coach.py` + `roster_metrics.py` + `drills.py`), coach-scoped; requires `ANTHROPIC_API_KEY` (503 if unset)
- `GET /sessions/{session_id}/annotations` — saved annotation (or null) + auto-seeded draft + video info + duration_s
- `PUT /sessions/{session_id}/annotations` — upsert the annotation, then **auto-recompute** `metrics_json` from the human boundaries via `compute_session_metrics(manual=...)` when ≥2 cycle boundaries exist; original auto result backed up ONCE in `sessions.metrics_json_auto`; 422 `{errors:[...]}` on bad docs
- `DELETE /sessions/{session_id}/annotations` — remove the annotation + restore `metrics_json` from `metrics_json_auto`
- `POST /sessions/{session_id}/video` + `GET /sessions/{session_id}/video-url` — attach a session video / time-limited signed URL; video bytes never proxy through the API. (Multi-camera externals: see DATA-FLOW.md / `session_videos`.)
- `GET /annotations/export` — all of the coach's annotated sessions (segmenter ground truth); mirrored by `fetch_annotations.py`
- `GET /reports/{token}` — public parent report payload (no auth, service role)
- `GET /devices`, `PATCH/DELETE /devices/{chip_id}` — device list, rename, deregister
- `POST /athletes` — create athlete; enforces athlete limit (402)
- `POST /billing/*` — Stripe; ⚠ no client UI calls these yet

Auth: Supabase Bearer JWT verified via `supabase-py auth.get_user()`. All endpoints require auth except `/health`, `/reports/{token}`, `/billing/webhook`, and `/billing/complete`. Admin client (service role) for writes; anon client for auth verification.

## Diagnostic / experimental files

- `vel_acc_extraction_testing.py` — wavelet diagnostics
- `vel_acc_extraction_test2.py` — alternate Butterworth + SG approach
- `vel_acc_extraction_testing3.py` — interactive FS slider + FFT/CWT

These are exploratory. `vel_acc_extraction.py` is the production file.

## Wavelet notes

The Morlet CWT (`cmor1.5-1.0`) on raw velocity produces dark nodes at stroke boundaries because velocity genuinely touches near-zero between strokes. Detrend with a 3-second rolling mean before CWT for a clean stroke-rate ridge.
