---
phase: 10-metrics-quality
plan: 01
status: complete
completed: 2026-05-25
---

# Summary: Plan 10-01 — Backend Cycle Quality + data_quality

## What was built

### Task 1 — metrics.py (complete)
Added a "cycle quality" block immediately before the `return` in `compute_session_metrics`. Four new keys on `session`:
- `total_cycles_raw` (int): `len(cycles)` before any phase filtering
- `outlier_cycle_count` (int): steady-state cycles with `duration_s < 0.80 × median(ss_cycle durations)`
- `implausible_cycle_count` (int): any cycle with `duration_s < 0.5s` or `> 4.0s`
- `kick_metrics_reliable` (bool): always `False` — LP filter limitation

### Task 2 — api.py (complete)
1. `csv` and `io` stdlib imports added at top.
2. Magnet dropout computed from raw CSV bytes before temp-file write: counts rows where `magnet_ok == "0"`, yields `magnet_dropout_pct` (float, 1 decimal).
3. `data_quality` dict assembled after metrics computation: `{magnet_dropout_pct, outlier_cycle_count, implausible_cycle_count, total_cycles_raw, warnings}`.
4. `warnings` list always contains kick-reliability message; conditionally adds implausible-cycle and magnet-dropout messages at thresholds (implausible > 0, dropout > 5%).
5. `data_quality` included in `metrics_json` stored to Supabase.
6. `data_quality` added to `/process` response dict.

## Acceptance criteria

| AC | Result |
|----|--------|
| AC-1: 4 quality keys in session dict | ✓ verified via Python inline test |
| AC-2: magnet_dropout_pct from raw CSV | ✓ computed before signal processing |
| AC-3: data_quality in response + Supabase | ✓ in return dict and metrics_json |
| AC-4: warnings populated for known thresholds | ✓ kick always present; conditional thresholds wired |

## Verification checklist
- [x] `python -c "import metrics as m"` — no import errors
- [x] `compute_session_metrics` returns 4 new session keys
- [x] `api.py` parses without syntax errors (`ast.parse`)
- [ ] POST /process response contains `data_quality` — requires Railway deploy

## Deviations from plan
None. One minor structural adjustment: `raw_bytes = await file.read()` moved before the `with tempfile.NamedTemporaryFile(...)` block (was inside it) so dropout computation runs before the file is written — functionally equivalent to the plan's intent.

## Deploy
Run `railway up` from `myswimcoach/` to deploy changes to Railway.

## Next
Plan 10-02: iOS data quality display in RecordScreen results + ReportCardScreen report card.
