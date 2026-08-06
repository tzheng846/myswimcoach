---
phase: 47-trial-annotation
plan: 02
subsystem: ui
tags: [nextjs, recharts, coach-portal, video, annotation]

requires:
  - phase: 47-trial-annotation (47-01)
    provides: locked annotation API contract (GET/PUT/DELETE annotations, video POST, video-url) + annotations.py PHASE_KEYS/build_seed/validate_annotation
affects: [47-03 iOS video upload, 47-04 recompute + ground-truth export, 16-06 wavelet tuning]

tech-stack:
  added: []
  patterns:
    - "New chart component (AnnotationChart) instead of extending the shared VelocityChart — protects report-card/compare from annotation-only concerns"
    - "apiUpload alongside apiFetch in lib/api.js for multipart (no Content-Type header)"
    - "Signed video URL refetched on every page mount, never persisted client-side (3600s TTL)"

key-files:
  created:
    - web/app/app/annotate/[id]/page.js
    - web/components/portal/AnnotationChart.js
    - web/components/portal/AnnotationEditor.js
    - web/components/portal/VideoPane.js
  modified:
    - web/lib/api.js
    - web/app/app/sessions/[id]/page.js

key-decisions:
  - "Click-to-place only this pass — no drag-to-move (deferred polish)"
  - "err.body added to apiFetch's thrown error so structured 422 {errors:[...]} responses surface in the editor"

patterns-established:
  - "Annotation editor state lives entirely in the page component; chart + editor are presentational"

duration: ~35min
started: 2026-07-11
completed: 2026-07-12
---

# Phase 47 Plan 02: Web Annotation GUI Summary

**Shipped the coach-portal annotation tool: `/app/annotate/[id]` — click a tool, click the
velocity trace, place a swim-phase boundary or stroke mark, pre-seeded from the auto-segmenter,
with a synced video pane (playhead, seek, origin nudge) when a video is attached. Checkpoint
approved on-device against a local backend; committed and pushed to `main` (e7f72f4).**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min (spanning two sessions) |
| Tasks | 2 auto + 1 human-verify checkpoint, all complete |
| Files modified | 6 (4 created, 2 modified) |
| Build | `npm run build` green, 18 routes, `/app/annotate/[id]` registered dynamic |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Click-to-mark editing, pre-seeded | Pass | Seed loads from GET; phase/stroke/seek tools route through one `handleChartClick`; Reset restores the seed |
| AC-2: Save round-trip | Pass | PUT full doc; dirty indicator clears on success; 422 errors render inline without losing editor state |
| AC-3: Video pane with sync | Pass | Playhead = origin_s + currentTime; Seek tool jumps video via a ref; ±0.1s nudge + Save-sync persist; velocity-only sessions fully functional with an Attach-video fallback |
| AC-4: Portal integration | Pass | "Annotate ›" link on the report card; build stays green |

## Accomplishments

- **End-to-end annotation loop works**: pre-seeded marks → click-edit → save → reload shows the
  saved doc (not the seed) — confirmed live against a local backend at the checkpoint.
- **Video sync verified**: attach → playhead tracks playback → Seek tool jumps video → nudge +
  Save sync persists across reload.
- **Shared VelocityChart untouched**: report card and compare page are unaffected; annotation
  concerns live entirely in new components.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/annotate/[id]/page.js` | Created | Data load (session + annotations), editor state, save/reset orchestration |
| `web/components/portal/AnnotationChart.js` | Created | Click-to-mark velocity chart; exports `PHASE_META`/`phaseLabel` |
| `web/components/portal/AnnotationEditor.js` | Created | Tool palette, phase/mark lists, save controls |
| `web/components/portal/VideoPane.js` | Created | Signed-URL playback, sync, upload |
| `web/lib/api.js` | Modified | Added `apiUpload`; `apiFetch` gained `err.body` for structured errors |
| `web/app/app/sessions/[id]/page.js` | Modified | Added "Annotate ›" link |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| New AnnotationChart vs extending VelocityChart | Click-to-mark + playhead concerns are annotation-only; avoids risking the report-card/compare chart | Two chart components going forward; acceptable duplication |
| `err.body` added to apiFetch | Only way to surface the 422 `{errors:[...]}` list without a parallel fetch path | No behavior change for existing callers (all read `.message`/`.status`) |

## Deviations from Plan

None beyond the `err.body` addition noted above, which was implied by AC-2 ("422 shows the errors list inline") and is additive/non-breaking.

## Issues Encountered

None — checkpoint approved on first pass.

## Next Phase Readiness

**Ready:**
- 47-03 (iOS): video upload target (`POST /sessions/{id}/video`) and origin convention are exercised and working from the web side.
- 47-04 (recompute): `stroke_marks_s` production format matches what the recompute step will consume; the editor already proves the round-trip through validation.

**Concerns:**
- Drag-to-move marks was intentionally deferred — click-to-place can be slow for dense stroke counts on long trials. Worth revisiting if annotation volume grows.

**Blockers:** None.

---
*Phase: 47-trial-annotation, Plan: 02*
*Completed: 2026-07-12*
