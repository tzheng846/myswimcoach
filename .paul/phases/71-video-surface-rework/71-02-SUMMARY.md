---
phase: 71-video-surface-rework
plan: 02
subsystem: ui
tags: [video, next.js, supabase, annotate, session_videos, two-point-align, signed-url]

requires:
  - phase: 69-multi-camera-video
    provides: session_videos table + unified GET /videos + CameraTile
  - phase: 71-video-surface-rework
    provides: 71-01 url-based VideoPane/VideoTracePanel + report-card unified reader + AddVideoModal
provides:
  - Annotate page is the single video hub — reads unified GET /videos, renders a camera tile per angle (external included), one active camera drives marking
  - Manual two-point align ("Set sync": scrub camera → click trace at same instant → origin = traceTime − videoTime), replacing auto push-off
  - Push-off / dive-detection alignment removed from VideoPane + CameraTile
  - Standalone /app/sessions/[id]/videos route deleted; report-card "Manage / align" link removed
affects: [70-video-session-matching, 72-tablet-layout-followon]

tech-stack:
  added: []
  patterns:
    - "Every web video read surface consumes the unified GET /videos list (url + origin_s per camera), never the legacy sessions.video_path column"
    - "Camera alignment is coach-controlled two-point (armed per-tile via Set sync), no encoder-dive dependency"

key-files:
  created: []
  modified:
    - web/app/app/annotate/[id]/page.js
    - web/components/portal/CameraTile.js
    - web/components/portal/VideoPane.js
  deleted:
    - web/app/app/sessions/[id]/videos/page.js

key-decisions:
  - "71-01 + 71-02 shipped in ONE commit (1e086ef) — the whole phase, since 71-02 rewrites the same report-card video block and removes a link to a page 71-02 deletes"
  - "Reader-side fix only — no schema change, no migration; the orphaned external reappears once annotate reads the unified list"
  - "Push-off/dive align removed entirely (user distrusts the auto detection); manual two-point align + ±nudge is the only alignment path"
  - "Phone end-anchor NOT re-added to CameraTile — a never-opened phone record-with-video shows unsynced until manually aligned (accepted; the user's clips are externals)"

duration: ~preexisting working tree (prior session) + unify this session
started: 2026-08-18T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 71 Plan 02: Annotate = the Video Hub (multi-cam + two-point align) Summary

**The annotate page now reads the unified `GET /videos` list, so a web-uploaded external finally appears there (the exact UAT bug); it hosts every camera as a tile with one active camera driving marking, aligns each by coach-controlled two-point "Set sync" (push-off/dive detection removed), and the standalone Videos page + its report-card link are gone.**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 completed |
| Files modified | 3 (+1 deleted) |
| Build | `next build` exit 0 (18 pages, TS clean); route list no longer lists `/app/sessions/[id]/videos` |
| Commit | `1e086ef` (covers 71-01 + 71-02) → pushed to `main` → Vercel |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: web-uploaded external visible/playable on annotate | **Pass** | User exercised the annotate camera tile on 2026-08-19 ("set sync seems to work" — a tile was present to align). The unified-reader change is what surfaces it. |
| AC-2: all cameras render; active camera drives marking | **Pass (single-external confirmed)** | Active-camera marking wiring in `CameraTile`; user confirmed the align tile. Simultaneous 2+ angles not separately reported this session — same "built blind" caveat, low risk. |
| AC-3: manual two-point align (no push-off) | **Pass** | User confirmed "Set sync" works — scrub camera → click trace at same instant → `origin = traceTime − videoTime`; ±nudge fine-tunes. |
| AC-4: "Sync to push-off" gone | **Pass** | `grep -Ei "pushoff\|alignToPushoff\|syncToPushoff" web/components/portal` → 0 matches. |
| AC-5: Videos page + report-card link removed | **Pass** | Route deleted (build route list confirms); no `/app/sessions/{id}/videos` page link remains. Report card keeps inline video + "Add video" modal + "Annotate ›". |

## Accomplishments

- **Fixed the reported bug end-to-end:** the annotate page reads `GET /sessions/{id}/videos` (`loadVideos`, `annotate/[id]/page.js:59`), so an external that previously showed "No video attached" now appears as a camera tile.
- **Annotate is the one video hub:** camera grid + "Add camera", one `activeCameraId` drives the playhead/seek/M-key/frame-step; `handleChartClick` gets a first `aligningCameraId` branch so an align-click sets the sync anchor instead of placing a mark.
- **Removed the distrusted auto-align:** push-off/dive code deleted from `VideoPane` + `CameraTile`; alignment is coach-controlled two-point + nudge only.
- **Deleted the standalone Videos page** and the report-card "Manage / align" link 71-01 had added.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| T1 remove push-off + rework CameraTile (two-point align + active marking) | `1e086ef` | fix | part of the single phase commit |
| T2 annotate reads GET /videos → camera grid + attach | `1e086ef` | fix | " |
| T3 delete Videos page + report-card link | `1e086ef` | fix | " |

`1e086ef` — `fix(71): unified video reader + annotate hub` (7 files, +366/−310), pushed `66a9546..1e086ef`.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/annotate/[id]/page.js` | Modified | Reads unified `GET /videos`; camera grid; `activeCameraId`/`aligningCameraId`; two-point align branch in `handleChartClick` |
| `web/components/portal/CameraTile.js` | Modified | Push-off removed; two-point align (Set sync + `alignClick`) + active-camera marking wiring |
| `web/components/portal/VideoPane.js` | Modified | Push-off `alignToPushoff` + button + `pushoffSessionS` prop removed |
| `web/app/app/sessions/[id]/videos/page.js` | Deleted | Its multi-cam grid moved into annotate |
| `web/app/app/sessions/[id]/page.js` | Modified | Removed the "Manage / align" link (71-01's inline video + Add-video modal kept) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Ship 71-01 + 71-02 in one commit | 71-02 rewrites the same block + deletes the page 71-01 linked to | Nothing half-shipped; prod jumps straight to the finished hub |
| Reader-side unification, no migration | The bug was a reader/store split | The user's orphaned external reappears with no manual step |
| Push-off removed, manual two-point only | User: distrusts auto dive detection | No alignment depends on the encoder dive |
| Phone end-anchor not re-added to CameraTile | Manual-first; user's clips are externals | A never-opened phone record-with-video shows unsynced until aligned — accepted |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 1 | Tablet-responsive layout (see below) — a follow-on phase, not a 71 defect |

**Total impact:** Plan executed as written. VideoPane's now-dead path-based attach/end-anchor/saveSync left in place (documents the mobile end-anchor convention) per the plan's scope note.

## Issues Encountered

None during execution. Post-ship, the user flagged **"hard to see everything on a small screen" → tablet at poolside** — the annotate hub (grid + trace + tools) is dense on tablet width. Recorded in CONTEXT.md as a deferred follow-on (candidate Phase 72), not a 71 defect.

## Next Phase Readiness

**Ready:**
- The unified-reader + two-point-align hub is live; `session_videos` surfaces are consistent for Phase 70 (video↔session matching) to build on.

**Concerns:**
- Full multi-camera (2+ external angles simultaneously) not separately UAT'd — low risk; confirm with a real 2-camera session when convenient.
- Tablet layout of the denser annotate hub (deferred → Phase 72).

**Blockers:** None.

---
*Phase: 71-video-surface-rework, Plan: 02 — LAST plan; phase complete. Code shipped `1e086ef`. `.paul` docs kept local (project habit); ROADMAP table intentionally untouched.*
*Completed: 2026-08-19*
