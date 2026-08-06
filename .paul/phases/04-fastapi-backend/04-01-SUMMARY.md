---
phase: 04-fastapi-backend
plan: 01
subsystem: api
tags: [fastapi, uvicorn, python, signal-processing, metrics]

requires: []
provides:
  - "POST /process endpoint: raw CSV → session metrics + cycles + velocity JSON"
  - "GET /health endpoint for Railway health checks"
  - "Procfile for Railway deployment"
affects: [05-ios-testflight, 06-auth-athlete-profiles]

tech-stack:
  added: [fastapi, uvicorn[standard], python-multipart]
  patterns: [_clean() helper for numpy/NaN JSON serialization, bypass process_file to avoid HTML side-effects]

key-files:
  created: [api.py, Procfile]
  modified: [requirements.txt]

key-decisions:
  - "api.py in project root — avoids sys.path hacks, vel_acc_extraction + metrics importable directly"
  - "Call pipeline sub-functions directly, not process_file — skips HTML generation side-effect"
  - "NaN/numpy sanitized via _clean() — nan → null for JSON safety"

patterns-established:
  - "_clean(obj): recursive dict/list/ndarray sanitizer — use for any numpy→JSON conversion"
  - "Pipeline entry: load_data → unwrap_angle → counts_to_distance → interpolate_to_uniform → decimate_signal → gradient → compute_session_metrics"

duration: ~30min
started: 2026-05-20T00:00:00Z
completed: 2026-05-20T00:00:00Z
---

# Phase 4 Plan 01: FastAPI Backend Summary

**FastAPI server wrapping the full Python signal pipeline — `POST /process` accepts raw encoder CSV, returns session metrics + per-cycle data + velocity trace as JSON.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Completed | 2026-05-20 |
| Tasks | 3 of 3 complete |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Health check | Pass | `GET /health` → `{"status":"ok"}` |
| AC-2: Process endpoint returns valid JSON | Pass | All 4 keys present; 20 cycles, 3376 samples |
| AC-3: NaN values serialized safely | Pass | `python -m json.tool` validates clean; nan → null |
| AC-4: Bad input returns error | Pass | HTTPException 500 with detail message |

## Verification Results

```
GET  /health          → {"status":"ok"}
POST /process (leo_br_1.csv):
  stroke_rate_spm:  41.85 SPM  ✓ (range 30–60)
  mean_vel_ms:       0.88 m/s  ✓ (range 0.5–2.0)
  cycles count:          20    ✓
  time/velocity:       3376    ✓ (equal length)
  json.tool validation:  pass  ✓ (no bare NaN)
```

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `api.py` | Created | FastAPI app — /health + /process endpoints + _clean() helper |
| `requirements.txt` | Modified | Added fastapi, uvicorn[standard], python-multipart |
| `Procfile` | Created | Railway deployment: `uvicorn api:app --host 0.0.0.0 --port $PORT` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Call sub-functions directly, not `process_file` | `process_file` calls `plot_results` which writes HTML to disk | Clean API with no file side-effects |
| `api.py` in project root | `vel_acc_extraction.py` and `metrics.py` are also in root — no path manipulation needed | Simpler imports |
| `_clean()` recursive sanitizer | `json.dumps` raises on `float('nan')`; numpy integers aren't JSON-serializable | All endpoints can use it safely |

## Deviations from Plan

**1. PowerShell 5.1 curl incompatibility (client-side only)**
- **Found during:** Human verify checkpoint
- **Issue:** PowerShell 5.1 aliases `curl` to `Invoke-WebRequest`; `-X`, `-F` flags don't exist; `-Form` requires PS 6+
- **Fix:** Used Bash tool's Unix curl for verification; provided PS 5.1 manual multipart workaround for user
- **Impact:** Server unaffected — deviation was in verification method only

## Next Phase Readiness

**Ready:**
- `POST /process` is the foundation the iOS app calls after uploading a raw CSV
- Response schema (`session`, `cycles`, `time`, `velocity`) is stable — iOS chart can consume `time` + `velocity` directly
- `Procfile` ready for Railway deployment whenever needed

**Concerns:**
- No auth on `/process` yet — any caller can submit CSVs; acceptable until Phase 6 adds middleware
- `EXCLUDED_SEGMENTS` is always `[]` — fine for now but will need per-request override if coaches want to trim rest periods

**Blockers:** None

---
*Phase: 04-fastapi-backend, Plan: 01*
*Completed: 2026-05-20*
