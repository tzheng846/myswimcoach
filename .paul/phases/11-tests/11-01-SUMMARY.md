---
phase: 11-tests
plan: 01
status: complete
completed: 2026-05-25
---

# Summary: Plan 11-01 — Pipeline Tests

## What was built

### Files created
- `tests/conftest.py` — shared fixtures: synthetic 30s encoder CSV (sine-wave breaststroke), dropout variant (10% magnet_ok=0), FastAPI TestClient with require_auth mocked
- `tests/test_metrics.py` — 10 unit tests for `compute_session_metrics`
- `tests/test_api.py` — 11 integration tests for `POST /process`
- `requirements-dev.txt` — pytest, httpx (not in requirements.txt, not deployed to Railway)

### Test counts
- 10 metrics unit tests: shape + types + edge cases (flat signal, short signal, head_waist offset)
- 11 API integration tests: HTTP 200, response shape, data_quality keys, kick warning always present, dropout computed from fixture
- **21 total — all passing**

## Key issue resolved
The local `myswimcoach/supabase/` SQL migrations directory is a Python namespace package that shadows the installed `supabase` library. Fixed by injecting a `MagicMock` into `sys.modules['supabase']` at conftest.py module load time. The mock is never exercised — SUPABASE_URL is empty in tests and `require_auth` is overridden.

## Acceptance criteria

| AC | Result |
|----|--------|
| AC-1: session dict has all standard + quality keys | ✓ |
| AC-2: flat/short signal edge cases pass without crash | ✓ |
| AC-3: POST /process 200 + correct response shape | ✓ |
| AC-4: dropout_pct ≈ 10.0% from 10% dropout fixture | ✓ |

## Verification
```
cd myswimcoach
python -m pytest tests/ -v
# → 21 passed in 3.52s
```

## Run command
```bash
cd myswimcoach
python -m pytest tests/ -v
```

## Next
- Deploy api.py + metrics.py changes: `railway up` from `myswimcoach/`
- Plan 10-02: iOS data quality display in RecordScreen + ReportCardScreen
