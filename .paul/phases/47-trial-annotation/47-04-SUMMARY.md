---
phase: 47-trial-annotation
plan: 04
subsystem: api
tags: [fastapi, metrics-pipeline, recompute, ground-truth, supabase]

requires:
  - phase: 47-trial-annotation (47-01)
    provides: annotation contract + session_annotations table + annotations.py
  - phase: 47-trial-annotation (47-02)
    provides: annotate GUI whose Save now triggers the recompute
provides:
  - Recompute-on-save — annotations with >=2 boundaries rewrite metrics_json via the real pipeline
  - metrics.py `manual` overrides (windows + cycle_bounds; segmentation_reliable=True on human bounds)
  - Once-only metrics_json_auto backup (patch_08, LIVE) + restore-on-delete
  - GET /annotations/export + fetch_annotations.py (16-06 ground-truth set)
affects: [16-06 wavelet tuning, ratings/dashboard/chat (now reflect corrected metrics), 47-03 iOS upload]

tech-stack:
  added: []
  patterns:
    - "Human overrides injected into compute_session_metrics stages, not a parallel pipeline"
    - "Non-fatal recompute: annotation save never lost; errors surfaced as recompute_error"
    - "Overwrite + once-only backup: consumers need zero changes to see corrections"

key-files:
  created: [supabase/patch_08_metrics_backup.sql, fetch_annotations.py]
  modified: [metrics.py, annotations.py, api.py, tests/test_annotations.py, tests/test_metrics.py, web/app/app/annotate/[id]/page.js]

key-decisions:
  - "AUTO recompute on PUT (no separate endpoint/button)"
  - "Overwrite metrics_json + once-only metrics_json_auto backup; DELETE restores"
  - "Full phase use: dive→baseline_end, stroke→ip_end, finish→swim_end (exclusive idx+1)"
  - "data_quality: dropout/warnings carried from raw-CSV processing; cycle counts refreshed; recomputed_from_annotation=true"

patterns-established:
  - "swim_end_idx is an exclusive slice end (finish idx + 1) — locked in annotation_to_overrides"
  - "Manual cycle bounds are full-trace indices; wavelet path still offsets by ip_end"

duration: ~30min
started: 2026-07-12
completed: 2026-07-12
---

# Phase 47 Plan 04: Recompute + Ground-Truth Export Summary

**Annotations now drive the metrics: saving stroke boundaries recomputes the session through
the real pipeline (human windows + cycles, wavelet bypassed), overwrites metrics_json with a
once-only auto backup, and every consumer — report card, pillars, dashboard, AI chat — shows
the corrected numbers. Checkpoint approved end-to-end; pushed to main (627419c).**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 auto + 1 combined checkpoint (patch_08 + E2E), all complete |
| Test suite | 148 passed (was 131; +17) |
| Files | 8 (2 created, 6 modified) |
| Deploy | patch_08 applied live; commit 627419c → origin/main (Railway + Vercel) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: metrics.py manual overrides, default path untouched | Pass | Bounds used verbatim; segmentation_reliable flips; manual=None identical (tested); degenerate bounds skipped |
| AC-2: Recompute on save, backup once, restore on delete | Pass | Backup only when metrics_json_auto null; <2 boundaries → recomputed:false, annotation kept; recompute failure → recompute_error, annotation kept; DELETE restores |
| AC-3: Ground-truth export | Pass | Endpoint coach-scoped (401/403 tested) + fetch_annotations.py mirrors it locally |
| AC-4: End-to-end visible | Pass | Checkpoint: save → "Saved — metrics recomputed." → report card reflects manual boundaries |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified | `manual` kwarg: baseline/ip/swim window overrides + cycle_bounds injection |
| `annotations.py` | Modified | `annotation_to_overrides` (times→indices; marks+finish→cycle pairs) |
| `api.py` | Modified | PUT recompute block; DELETE restore; GET /annotations/export |
| `supabase/patch_08_metrics_backup.sql` | Created | sessions.metrics_json_auto (APPLIED LIVE 2026-07-12) |
| `fetch_annotations.py` | Created | Local ground-truth dump (dotenv + service key, fetch_sessions.py pattern) |
| `web/app/app/annotate/[id]/page.js` | Modified | Save message reports recomputed / too-few-boundaries / recompute_error |
| `tests/*` | Modified | +17 tests (overrides, mapping, recompute/backup/restore, export) |

## Deviations from Plan

**1. Degenerate-bounds clamp (auto-fixed):** first implementation coerced a <2-sample cycle
up to 2 samples instead of skipping it; caught by the planned test, fixed to skip. No other
deviations — export uses full `metrics_json` select (simpler than the JSON-path select the
plan sketched; lap_time extracted in Python).

## Next Phase Readiness

**Ready:**
- Phase 47 remaining: 47-03 only (iOS auto-upload video after Record-with-Video; POST /sessions/{id}/video is exercised and live).
- 16-06 wavelet tuning now has a data path: annotate sessions → `python fetch_annotations.py` → labels + raw_csv_path pairs.

**Concerns:**
- `initial_phase` is carried from the original auto detection even when manual windows differ — dive/pulldown display values may not match hand-marked phases. Acceptable for now (annotation stores the truth); revisit if it confuses.
- Recomputed sessions change ratings baselines (trend vs previous session compares manual-corrected vs auto sessions). Inherent to overwrite-by-design.

**Blockers:** None.

---
*Phase: 47-trial-annotation, Plan: 04*
*Completed: 2026-07-12*
