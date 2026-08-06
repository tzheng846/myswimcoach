---
phase: 52-sample-rate-contract
plan: 01
subsystem: api
tags: [signal-processing, decimation, supabase, migration, annotations, nextjs]

requires:
  - phase: 51-api-correctness
    provides: "API-AUDIT.md findings F2 + F3 — the audit that located the discarded sample rate and every consumer assuming 100 Hz"
provides:
  - "sessions.sample_rate_hz (patch_09) — the authoritative per-session rate"
  - "the true decimated rate persisted at write time instead of discarded"
  - "6 backend + 3 web consumers reading the stored rate instead of assuming 100"
  - "a NULL-means-100 fallback that leaves every pre-migration row byte-identical"
affects: [annotations, metrics recompute, export, web time axes, 52-02 backfill, Phase 53 measurement]

tech-stack:
  added: []
  patterns:
    - "Never assume 100 Hz — read the rate from the session row (api.py:_session_fs, row.sample_rate_hz, annotations fs_hz arg)"
    - "NULL means 'predates the migration', not 'is 100' — do not backfill with a default"

key-files:
  created:
    - supabase/patch_09_sessions_sample_rate.sql
  modified:
    - api.py
    - annotations.py
    - seed_demo_team.py
    - CLAUDE.md
    - web (annotate page, sessions page, VelocityChart)

key-decisions:
  - "Option A: persist the real rate per session rather than correct a constant — fixes the class, survives firmware/device changes"
  - "Nullable column with NO default — a default of 100 would erase the distinction 52-02's backfill needs"
  - "Human-action gate moved after the code tasks: writing code touches nothing live"

patterns-established:
  - "sessions.sample_rate_hz is the single source of truth for a session's clock"

duration: "~1 session (2026-08-03)"
started: 2026-08-03
completed: 2026-08-03
---

# Phase 52 Plan 01: Sample-Rate Contract Summary

**The system stopped lying about its own clock — `sessions.sample_rate_hz` now records the true decimated rate (~89.5 Hz, never the requested 100), and all nine consumers read it, with NULL falling back to 100 so every pre-migration row behaves exactly as it always did.**

> **Reconciliation note.** This plan was applied on 2026-08-03 in a prior session. This SUMMARY was written 2026-08-05 from the detailed APPLY record in STATE.md, not from first-hand execution. Verification figures below are quoted from that record; the two unverified checkpoint items are carried forward honestly rather than closed.

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 5 code tasks + 2 checkpoints |
| Suite | 149 → 170 passing (+21) |
| Web build | green, 18 routes |
| Commit | `89205ca` "Persist per-session sample rate" → origin/main |

## The defect

`decimate_signal` decimates by an **integer** factor:

```
factor    = round(native_fs / target_fs)   # round(268.5 / 100) = 3
actual_fs = native_fs / factor             # 89.5 Hz, NOT 100
```

`api.py:143` then discarded the returned `actual_fs`, so the true rate was destroyed at write time. Nine consumers assumed exactly 100 — including the annotation recompute time axis and three web files that build their own `i / 100` axes from direct supabase-js reads.

**Real impact:** a 47.1 s swim displayed as 42.2 s, and recomputing metrics from a saved annotation shifted every time-derived metric by ~11.7%.

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: New sessions store the real rate | **Pass** | Verified live — a new session stored `sample_rate_hz ≈ 89`, not 100 |
| AC-4: Pre-migration rows unchanged | **Pass** | A Jun-23 NULL-rate session rendered exactly as before: axis 0→13.08 s, lap 13.1 s, 3 cycles |
| AC-2: Annotate-page duration correct on a new session | **Unverified** | Needs a swim recorded after the migration; none existed at checkpoint time |
| AC-3: Recompute-from-annotation plausible | **Unverified** | Same blocker |

**AC-2/AC-3 remain genuinely open.** To close: record one session, open `/app/annotate/[id]`, confirm the chart's last x matches the real swim length, save marks, sanity-check `stroke_rate_spm`.

## Accomplishments

- **Fixed the class, not the instance.** Persisting the measured rate per session survives firmware and device changes; correcting a constant would not have.
- **Zero-risk migration by construction.** The column is nullable with **no default**, and every reader falls back to `annotations.FS_HZ` (100) on NULL — so un-backfilled rows behave byte-identically. No mid-flight shift, no backend/web drift.
- **Bounded the damage precisely, twice.** Stored cycle *indices* are not corrupted (the time→index round trip uses the same wrong constant both ways, so marks land on the clicked sample — they must NOT be "repaired"), and the original auto metrics are correct (`compute_session_metrics` runs on the true `t_dec` clock inside `/process`). Damage is confined to sessions recomputed from an annotation.
- **Found three consumers the audit missed.** API-AUDIT's F2 listed the backend paths; planning discovered the web builds its own time axes from supabase-js reads (annotate page, sessions page, VelocityChart cycle overlay), plus `seed_demo_team.py:424`.

## Verification Results

```
pytest tests/                → 170 passed (was 149, +21 new)
web build                    → green, 18 routes
python -c "import api"       → clean
tools/schema_contract.py     → exactly 4 violations, ALL known Phase-51 athletes.coach_id sites,
                               ZERO false positives from the new sample_rate_hz refs
```

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Ordering change | 1 | None — safety-neutral |
| Boundary crossing | 1 | Disclosed; necessary |

**1. Human-action gate moved.** Planned between T1 and T2; executed after all code tasks. Writing code touches nothing live, so gating it cost a round-trip for no safety benefit.

**2. Boundary crossing — `supabase/live_schema.json` regenerated here.** 52-01's boundaries assigned that file to 51-02, but it was regenerated via `tools/introspect_schema.py` (7 tables, 67→68 cols). Necessary: a snapshot predating the migration would make 51-02's contract test fail on correct code. It did cross a stated line, and is recorded as such.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `CLAUDE.md` carried unrelated pre-existing Phase-47 doc catch-up that could not be split from the same file's diff | Committed together in `89205ca`; noted rather than hidden |
| `seed_demo_team.py` was untracked and the only copy, flagged in STATE for two sessions | Entered git for the first time in `89205ca` (565 lines) |

## Next Phase Readiness

**Ready:**
- `sessions.sample_rate_hz` is the documented single source of truth; CLAUDE.md carries the "never assume 100 Hz" section.
- Phase 53's `tools/analyze_repeatability.py` can read `actual_fs` directly, so it is unblocked.

**Concerns:**
- **AC-2/AC-3 unverified** — the only real gap in this plan.
- **52-02 is owed.** Concrete example from the checkpoint: a Jun-23 session's ~1308 samples display as 13.08 s under the 100 Hz fallback; at the true ~89.5 Hz the trace is really ~14.6 s. `lap_time_s` (13.1 s) was always correct — computed on the true clock inside `/process`. That residual is exactly what 52-02 must repair. How many stored sessions carry recomputed metrics is still **unknown** and needs a data read; the SQL is in `API-AUDIT.md`.
- Two consumers still assume 100, both deliberately out of scope: iOS `ReportCardScreen.js` client-side CSV export, and `web/components/portal/CompareChart.js` (two sessions may have two different rates — a design question).

**Blockers:** None.

---
*Phase: 52-sample-rate-contract, Plan: 01*
*Applied: 2026-08-03 · Summary written: 2026-08-05*
