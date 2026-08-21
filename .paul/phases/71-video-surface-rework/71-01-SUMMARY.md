---
phase: 71-video-surface-rework
plan: 01
subsystem: ui
tags: [video, next.js, supabase, report-card, session_videos, signed-url]

requires:
  - phase: 69-multi-camera-video
    provides: session_videos table + unified GET /videos + POST /videos (external upload)
provides:
  - Report-card inline video sourced from the unified GET /videos list (phone else first angle)
  - AddVideoModal — file-picker popup that attaches an external via POST /videos, no page nav
  - VideoPane/VideoTracePanel can play a camera by direct signed URL (not only legacy video_path)
affects: [71-02-annotate-video-hub]

tech-stack:
  added: []
  patterns:
    - "Video read surfaces consume the unified GET /videos list (url + origin_s per camera) rather than the legacy sessions.video_path column"
    - "External (session_videos) origin is never end-anchored — the end-anchor is a phone-only stop-together convention"

key-files:
  created:
    - web/components/portal/AddVideoModal.js
  modified:
    - web/app/app/sessions/[id]/page.js
    - web/components/portal/VideoPane.js
    - web/components/portal/VideoTracePanel.js

key-decisions:
  - "Reader-side fix only: no schema change, no data migration — the orphaned external reappears once surfaces read the unified list"
  - "Report-card modal posts externals (POST /videos); the unified reader shows them — no promote-to-primary"
  - "Not committed/pushed yet — 71-02 rewrites the same report-card video block, so both push together"

duration: ~15min
started: 2026-08-18T00:00:00Z
completed: 2026-08-18T00:15:00Z
---

# Phase 71 Plan 01: Report-card Video (modal add + inline unified-list watch)

**A web-uploaded external video now plays inline on the report card (one angle + velocity overlay) and is added via a popup — because the inline player reads the unified GET /videos list instead of the legacy `video_path` column. Fixes the Phase-69 store-split "vanishing video" bug on the report card.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min |
| Tasks | 3 completed |
| Files modified | 3 (+1 created) |
| Build | `next build` exit 0 (18/18 pages, TypeScript clean) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: External-only session plays inline on the report card | Pending UAT | Code complete + build green; not yet visually confirmed (user UAT'd the annotate page this session, not the report-card inline). No live auth/video in the sandbox. |
| AC-2: Add-video is a modal, no navigation | Pending UAT | `AddVideoModal` posts `POST /videos`, closes on success, refetches `GET /videos`. Needs a real login + clip to confirm. |
| AC-3: No regression to phone videos or annotate | **Pass** | Backward-compatible by construction — legacy `{path}` callers keep the `/video-url` fetch + phone end-anchor unchanged; annotate untouched by this plan (user's screenshot shows its video pane behaving as before). Build green. |
| AC-4: Upload limits surface a clear reason | Pending UAT | Modal maps 413→over-cap, 409→max-3, else message; client 50 MB pre-check. Needs UAT. |

## Accomplishments

- **Unified reader on the report card:** `videos` state ← `GET /videos`; `primaryCam = phone ?? first`; the inline `VideoTracePanel` is fed that camera. This is the fix — an external (previously only counted, never shown) now plays inline.
- **`VideoPane` plays a direct signed URL:** when `video.url` is present it skips the legacy `/video-url` fetch; the no-video gate accepts `url`; and — importantly — an external no longer inherits the phone-only end-anchor (`effectiveOriginS = originS ?? (video?.path ? endAnchoredOriginS : null)`), so an unsynced external stays honestly unaligned instead of jumping to a bogus offset.
- **`AddVideoModal`:** report-card popup (AddAthleteModal shell), file picker + optional label, 50 MB guard, actionable 413/409 messaging.

## Task Commits

**Not committed yet (deliberate).** 71-02 rewrites the same report-card video block (removes the "Manage / align" link) and the video components (removes push-off), so 71-01 + 71-02 will be committed/pushed together to avoid shipping a link to a page that is about to be deleted. Working tree only; verified via `next build`.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/AddVideoModal.js` | Created | Report-card "Add video" popup → `POST /videos`; 50 MB / max-3 / format errors |
| `web/app/app/sessions/[id]/page.js` | Modified | Inline video from unified `GET /videos` (`primaryCam`); "Add video" opens the modal; dropped the `video_path`-only source + its select columns |
| `web/components/portal/VideoPane.js` | Modified | Direct-`url` playback path; no-video gate accepts `url`; externals excluded from the end-anchor |
| `web/components/portal/VideoTracePanel.js` | Modified | `hasVideo` accepts a url-based camera |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Reader-side unification, no schema/migration | The bug is a reader/store split; reading `GET /videos` everywhere fixes it and revives the orphaned external | 71-02 continues the same pattern on the annotate page |
| Report-card modal posts externals (not promote-to-primary) | Uniform with the web upload path; the unified reader shows them regardless of store | `video_path` stays the phone's slot; web uploads are externals |
| Omit `onVideoChange` on the report-card panel | Avoids a signed-URL-churn `<video>` reload after the phone origin auto-save; origin is persisted server-side anyway | Modal refetch (`loadVideos`) is the only refresh path |
| Hold the commit for 71-02 | 71-02 rewrites the same block + removes push-off | Nothing on prod yet; localhost only |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | Plan executed as written |

**Total impact:** None — plan executed exactly as specified.

## Issues Encountered

None during execution. UAT (this session) surfaced two items that are **71-02 scope, not 71-01 defects**: (1) the annotate page still shows "no video" for an external — expected, since 71-01 was report-card only; (2) the user rejected the "Sync to push-off" auto-align and asked to fold the Videos page into annotate — recorded as CONTEXT D10–D13, reshaping 71-02.

## Next Phase Readiness

**Ready:**
- The unified-reader pattern + direct-`url` `VideoPane` are now available for the annotate page (71-02 reuses both).
- `AddVideoModal` + `POST /videos` upload path proven end-to-end in the build.

**Concerns:**
- AC-1/2/4 are UAT-pending (sandbox has no live auth/video — same "built blind" caveat as Phase 69). Confirm on localhost with a real session + clip.
- The report-card "Manage / align" link currently points at `/app/sessions/[id]/videos`, which 71-02 deletes — 71-02 must remove that link in the same change.

**Blockers:** None.

---
*Phase: 71-video-surface-rework, Plan: 01*
*Completed: 2026-08-18 — loop closed; phase NOT complete (71-02 next). No transition/commit triggered.*
