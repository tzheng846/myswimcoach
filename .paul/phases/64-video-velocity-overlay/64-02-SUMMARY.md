---
phase: 64-video-velocity-overlay
plan: 02
subsystem: api
tags: [signal-processing, supabase, jsonb, backfill, fastapi, pytest]
requires:
  - phase: 52-sample-rate-contract
    provides: sessions.sample_rate_hz (per-session rate for the accel derivation)
provides:
  - acceleration_from_velocity(vel, fs) — the single source of truth for acceleration
  - sessions.acceleration_profile jsonb column (patch_10)
  - tools/backfill_acceleration.py (exact, idempotent backfill from stored velocity)
affects: [64-03, 66-acceleration-derivative]
tech-stack:
  added: []
  patterns: ["pure derivation extracted so /process AND the backfill share one function"]
key-files:
  created: [supabase/patch_10_acceleration_profile.sql, tools/backfill_acceleration.py]
  modified: [vel_acc_extraction.py, api.py, tests/test_metrics.py, tests/test_api.py, live_schema.json]
key-decisions:
  - "Store the derivative, don't recompute per request — accel is a pure fn of stored velocity"
  - "patch_10 nullable, no default — NULL means predates 64-02, mirroring patch_09"
  - "Backfill derives from velocity_profile, never the raw CSV"
patterns-established:
  - "One shared derivation function keeps new-session writes and the backfill bit-identical"
duration: ~1 session + live checkpoint
started: 2026-08-14
completed: 2026-08-14
---

# Phase 64 Plan 02: Store acceleration_profile Summary

**Extracted `acceleration_from_velocity` as the single source of truth, stored it as
`sessions.acceleration_profile` (patch_10), and backfilled all 70 existing rows exactly from their
stored velocity — no raw-CSV reprocessing.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Pipeline refactor behaviour-preserving | Pass | `array_equal` test — the extracted fn == the old inline form (the `+t[0]` offset cancels in `np.interp`) |
| AC-2: New sessions store acceleration | Pass | `/process` insert carries `acceleration_profile`, len == velocity, NaNs→null |
| AC-3: Existing rows backfill exactly | Pass | 70/70 written; spot-check == `acceleration_from_velocity(stored vel, fs)` |
| AC-4: Column additive + safe | Pass | patch_10 nullable/no-default; NULL reads unaffected |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `vel_acc_extraction.py` | Modified | `acceleration_from_velocity` extracted; `run_pipeline` routes through it |
| `api.py` | Modified | `_accel`→`accel`; insert writes `acceleration_profile` |
| `supabase/patch_10_acceleration_profile.sql` | Created | jsonb column, nullable, no default |
| `tools/backfill_acceleration.py` | Created | Dry-run default; `--apply`; idempotent on accel IS NULL |
| `tests/test_metrics.py`, `tests/test_api.py` | Modified | Byte-identical + insert-shape tests |
| `live_schema.json` | Modified | Column added so `TestSchemaContract` stays green |

## Deviations from Plan

None material. Suite 274→276. ⚠ The byte-identical test (`test_acceleration_from_velocity_matches_inline`)
PINS the old decimate→gradient→interp algorithm — which becomes a maintenance point for Phase 66
(the Savitzky–Golay swap must rewrite it).

## Commits + Checkpoint

Committed `f133c56` → Railway (health 200). patch_10 applied live by the user. Backfill applied:
**70/70 written, 0 failed**; idempotent re-run finds 0.

## Next Phase Readiness

**Ready:** `acceleration_profile` is populated for every session — 64-03 reads it like
`velocity_profile`.
**Concerns:** the derivation is a ~5 Hz decimate→gradient→linear-interp reconstruction, which reads
choppy on screen — the motivation for Phase 66 (SG derivative + re-backfill). **Display-only:**
`metrics.py` never consumes acceleration.

---
*Phase: 64-video-velocity-overlay, Plan: 02 — Completed 2026-08-14*
