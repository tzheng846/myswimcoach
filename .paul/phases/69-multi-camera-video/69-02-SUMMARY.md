---
phase: 69-multi-camera-video
plan: 02
subsystem: ui
tags: [react, nextjs, video, multi-camera, upload, sync]
requires:
  - phase: 69-multi-camera-video
    provides: 69-01 external-video API (GET/POST/PATCH/DELETE /videos)
provides:
  - dedicated /app/sessions/[id]/videos page (attach/label/sync/delete, adaptive grid)
  - CameraTile component (per-camera native playback + push-off sync + label + delete)
affects: [69-03 synced player + report-card declutter]
key-files:
  created:
    - web/app/app/sessions/[id]/videos/page.js
    - web/components/portal/CameraTile.js
  modified: []
key-decisions:
  - "Per-camera push-off sync reuses 67-01; primary persists via legacy POST /video, externals via PATCH /videos/{id}."
  - "50 MB client guard + compress/upgrade message carried from 67-02; add-camera capped at 3 externals."
duration: ~30min
started: 2026-08-17T02:20:00Z
completed: 2026-08-17T02:50:00Z
---

# Phase 69 Plan 02: Dedicated Videos Page Summary

**A new `/app/sessions/[id]/videos` page: an adaptive grid of camera tiles (phone + up to 3 external),
each with native-controls playback, a one-tap push-off sync, an editable label, and delete — plus an
"Add camera" upload with the 50 MB free-tier guard. This is the declutter destination for the report
card's video. Compile + lint verified; live UAT owed. Shipped `57d06c9`.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| Dedicated page, adaptive grid | Pass (compile) | `/app/sessions/[id]/videos` registered; grid 1→1col, ≥2→2col. |
| Attach / label / delete per camera | Pass (compile) | POST /videos (≤3 cap), PATCH label, DELETE via CameraTile; 50 MB guard + compress message. |
| Per-camera push-off sync | Pass (compile) | Scrub tile → "Sync to push-off" → origin = pushoff − currentTime; primary→POST /video, external→PATCH /videos/{id}. |
| Sync status visible | Pass | green "synced" / amber "needs sync" per tile (origin_s null-aware). |

## Verification Results
- `npx eslint` on both new files → **exit 0**.
- `npm run build` → **Compiled successfully, exit 0**; `/app/sessions/[id]/videos` in the route list.
- ⚠ Live UAT owed (needs patch_12 applied + real videos + auth) — no live data path in the sandbox.

## Files Created
| File | Purpose |
|------|---------|
| `web/app/app/sessions/[id]/videos/page.js` | The Videos page — fetch session + `GET /videos`, adaptive grid, attach. |
| `web/components/portal/CameraTile.js` | One camera: native playback, push-off sync, label, delete. |

## Deviations from Plan
None material. Individual (per-tile) playback here; the synced one-timeline player is 69-03.

## Next Phase Readiness
**Ready:** the page + tiles compose the camera list from `GET /videos`; 69-03 adds the synced player above and declutters the report card.
**Concerns:** ⚠ everything web in Phase 69 is compile-verified only; the whole phase's live UAT is bundled at the end (needs patch_12).
**Blockers:** none for 69-03.

---
*Phase: 69-multi-camera-video, Plan: 02 · Completed: 2026-08-17*
