---
phase: 88-splits-picker-and-units
plan: 02
subsystem: ui
tags: [react, next, report-card, boundaries, dive-start, provenance]

requires:
  - phase: 75-02
    provides: phases.boundaries + boundaries.sources per-boundary provenance from resolve_boundaries
  - phase: 61-02
    provides: the D7 caveat line under Time-to-Distance that this plan repurposed
provides:
  - anchorS / anchorSource — the session page's single hoisted distance origin
  - TimeToX on raw dive_start_s, head-waist retired from computation
  - scratch/anchor_check.mjs — headless harness pinning the anchor, the retirement and all provenance branches
affects: [88-04, any future mobile phase carrying head-waist retirement to iOS]

tech-stack:
  added: []
  patterns:
    - "Per-boundary provenance is boundaries.sources.<key>, never data_quality.recomputed_from_annotation"
    - "A prop renamed with its meaning (baselineEndS → anchorS), not left naming the old boundary"

key-files:
  created:
    - scratch/anchor_check.mjs
  modified:
    - web/components/portal/TimeToX.js
    - web/app/app/sessions/[id]/page.js

key-decisions:
  - "D1 held: both halves — the anchor swap AND the head-waist retirement"
  - "D4 held: Python dead code named, not deleted (repo convention)"
  - "D8 held: provenance reads boundaries.sources.dive_start_s"

patterns-established:
  - "One hoisted anchor per page; every distance-origin consumer reads it rather than re-deriving"

duration: ~1h (across two sessions)
started: 2026-08-31
completed: 2026-08-31
---

# Phase 88 Plan 02: One Anchor Summary

**The session report card collapsed from three definitions of "0 m" onto one: Time-to-Distance now
measures from raw `phases.boundaries.dive_start_s` — the same instant the split rows use — with the
head–waist offset retired from computation and the 61-02 caveat line rewritten as the page's single
statement of its anchor and that anchor's provenance. Web-only; nothing stored changed.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1h across two sessions (mid-apply handoff) |
| Completed | 2026-08-31 |
| Tasks | 4 (3 auto + 1 human-verify — see Deviations) |
| Files modified | 2 + 1 created |
| Stored data touched | **None** |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: One anchor | **Pass** | `anchorS` hoisted from `phases?.boundaries?.dive_start_s`; `anchor_check.mjs` asserts `TimeToX` is fed the hoisted value rather than a re-derived `baselineEndS` prop |
| AC-2: Head-waist moves no number | **Pass** | `grep -c headWaistM` and `grep -c waistTarget` on `TimeToX.js` = 0; `grep -c head_waist` on the session page = 0; harness confirms a *stray* `headWaistM` prop changes nothing in the rendered markup |
| AC-3: The page says where 0 m is and where it came from | **Pass** | All three provenance branches (`manual` / `detected`+`auto` / `none`) plus the null-anchor no-render case are asserted |
| AC-4: Nothing else on the card moved | **Pass** | `stroke_toggle_check` 63/63, `overlay_render_check` 40/40, `marketing_render_check` 45/45, all unedited except the one 88-03 MAP line (see Deviations) |

## Verification Results

| Check | Result |
|---|---|
| `node scratch/anchor_check.mjs` | **17/17 pass**, exit 0 |
| `grep -c headWaistM web/components/portal/TimeToX.js` | 0 |
| `grep -c waistTarget web/components/portal/TimeToX.js` | 0 |
| `grep -c head_waist web/app/app/sessions/[id]/page.js` | 0 |
| `cd web && npm run build` | clean, 20 routes |
| `node scratch/stroke_toggle_check.mjs` | 63/63 |
| `node scratch/overlay_render_check.mjs` | 40/40 |
| `node scratch/marketing_render_check.mjs` | 45/45 |

`anchor_check.mjs` covers: the anchor driving the reading against hand arithmetic at two anchors
0.5 s apart; absence of both retired identifiers read from the source text (a render cannot prove
a name is gone); imperial `20yd` equalling metric `18.288 m` on the same arrays; unreachable
presets still hidden on a 12 m swim; and all four caveat-line branches.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/TimeToX.js` | Modified | `baselineEndS` → `anchorS` throughout; `headWaistM` and `waistTarget` deleted; header comment rewritten with the D5 do-not-wire-back note |
| `web/app/app/sessions/[id]/page.js` | Modified | `head_waist_m` dropped from the athlete select; `anchorS`/`anchorSource` hoisted; caveat line rewritten on `boundaries.sources.dive_start_s` |
| `scratch/anchor_check.mjs` | Created | 17-assertion headless render harness |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Checkpoint not separately confirmed | 1 | See below — recorded, not hidden |
| Boundary crossed by an adjacent plan | 1 | 88-03's MAP line in a protected harness |
| Scope additions | 0 | — |

### 1. ⚠ The blocking human-verify (Task 4) was not separately confirmed

The plan gated this change behind a `checkpoint:human-verify` **because it moves numbers a coach
has already read** — ~0.4–0.5 s from the head-waist half on the 37 "Tony" sessions, and up to
**12.39 s** from the anchor half on the 27 of 99 sessions where `dive_start_s` and
`baseline_end_s` diverge by more than 0.1 s. The user directed UNIFY to run after confirming the
backfill, without separately reporting the six browser checks. The mechanical half of that
checkpoint is fully covered by `anchor_check.mjs` (17/17) and the three untouched harnesses, but
**the on-screen sanity read against a real Tony session and a real divergent session was not
performed.** Recorded here rather than marked approved. Dev server was live at
`http://localhost:3000` if a retro-check is wanted.

### 2. `scratch/stroke_toggle_check.mjs` was edited, and this plan's boundaries forbade it

One line — an `@/lib/unitConvert` MAP entry plus that file in the compile list — added by **88-03**,
not by this plan, because `PhaseReportCard.js` now imports `unitConvert`. Both 88-01 and 88-02
listed that harness as must-pass-UNEDITED. It passes (63/63), and the edit is a harness plumbing
line rather than a changed assertion, but the boundary was crossed by an out-of-wave plan and is
recorded as such.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Session interrupted mid-apply; applied state untrusted | Re-verified every AC independently — greps re-run, harness re-run, build re-run |
| 88-03 (wave 2) partially applied into the tree | Left in place; it is correct and green. Flagged to the user and recorded in both wave 1 summaries. |

## Next Phase Readiness

**Ready:**
- `anchorS` / `anchorSource` are hoisted in `page.js` — **88-04's picker consumes them directly**
  (that plan's stated dependency) rather than deriving a fourth origin.
- The caveat line is the page's one standing statement of where 0 m is; 88-04 adds no second banner.

**Concerns:**
- ⚠ **iOS still applies its own head-waist-adjusted TimeToX.** The two surfaces now disagree by
  ~0.4–0.5 s on the 37 Tony sessions. Out of scope per CONTEXT; owed to a mobile phase.
- ⚠ **Dead code deliberately left in Python (D4):** `metrics.time_to_distance` (zero callers),
  `compute_session_metrics`'s unused `head_waist_m` kwarg, `api.py:183/228`'s form field,
  `tests/test_metrics.py:156`'s kwarg-accepted test. Repo convention is to name dead code, not
  delete it. `athletes.head_waist_m`, `POST /athletes` and the athletes-page editor also remain
  writable by CONTEXT D7 — a comment at the retirement point in `TimeToX.js` says so, so the next
  reader does not wire it back.
- ⚠ Compare, group-comparison and parent-report pages were not audited for the anchor.

**Blockers:** None.

---
*Phase: 88-splits-picker-and-units, Plan: 02*
*Completed: 2026-08-31*
