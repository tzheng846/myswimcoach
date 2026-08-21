---
phase: 70-video-session-matching
plan: 01
subsystem: ui
tags: [video, next.js, supabase, matching, thumbnails, session_videos, web-only]

requires:
  - phase: 69-multi-camera-video
    provides: session_videos table + POST /sessions/{id}/videos (external upload)
  - phase: 71-video-surface-rework
    provides: unified GET /videos reader — an assigned external then shows on the session's report card + annotate
provides:
  - /app/match — batch surface: stage many local clips, client-side content thumbnails, per-clip session picker, assign via POST /videos
  - "Match videos" portal nav entry
affects: [70-qr-slate-followon]

tech-stack:
  added: []
  patterns:
    - "Client-side video thumbnails via an offscreen <video> + canvas frame-grab on a same-origin object URL (no server, no schema)"
    - "Matching = assign-by-upload: reuse POST /sessions/{id}/videos; no dedicated match endpoint"

key-files:
  created:
    - web/app/app/match/page.js
  modified:
    - web/app/app/layout.js

key-decisions:
  - "Web-only core (user-chosen 2026-08-19) — no backend/schema/iOS; Phase 69 already built the upload path, iOS never handles external footage"
  - "Metadata (mtime/duration/size) is DISPLAY-ONLY soft hint — never sorts/ranks/auto-selects a session (D2)"
  - "Client-side thumbnails (CONTEXT design-call #2) — server-light, no schema, works on unuploaded local files"
  - "New top-level /app/match, not the per-session Videos page (Phase 71 deleted that); matching is inherently cross-session"

duration: ~loop (single session)
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 70 Plan 01: Video↔Session Matching (manual core) Summary

**A new `/app/match` page lets a coach dump many opaque external clips, recognize each swim by a client-side content thumbnail (filenames/timestamps untrusted), and assign each to a session by reusing Phase-69's `POST /sessions/{id}/videos` — no backend, schema, or mobile change.**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 2 completed |
| Files | 1 created, 1 modified |
| Build | `next build` exit 0 (19/19 pages, `/app/match` prerendered ○, TS clean) |
| Commit | `17f3a77` (`feat(70): video-session matching page`) → pushed `1e086ef..17f3a77` → Vercel |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: stage many clips, content thumbnails, no upload | **Pass (build) / UAT-pending (interactive)** | Static prerender of the client component succeeded (no render-time crash). Canvas frame-grab + multi-file staging need a real browser + clips — human UAT. |
| AC-2: assign a clip to a chosen session (uploads via POST /videos) | **UAT-pending** | Upload path is `apiUpload` → `POST /sessions/{id}/videos` (proven by AddVideoModal / Phase 69). Needs live auth + a real ≤50 MB clip to exercise. |
| AC-3: metadata soft-hint only; 413/409 errors clear | **Pass (code) / UAT-pending (errors)** | No sort/rank/auto-select by metadata; hints are plain text. 413/409 mapping mirrors AddVideoModal. Error paths need a live upload to trigger. |
| AC-4: reachable, loading/empty states, URL revocation | **Pass** | "Match videos" nav entry added; loading + empty states present; object URLs revoked on Remove and on unmount (clipsRef cleanup effect). Build green. |

## Accomplishments

- **`/app/match`** — multi-file staging held entirely client-side; per-clip **canvas thumbnail** + duration from an offscreen `<video>` (same-origin object URL, no taint); soft hints (duration · size · file date) that never auto-decide; per-clip native session `<select>` (labelled `sessionLabel(s,{withStroke})`, narrowed by a top athlete filter); **Assign** → `POST /videos` with per-clip status + 413/409 messaging; **Assign all matched** (sequential, per-clip error attribution).
- **Nav:** "Match videos" between Sessions and Compare.
- **Zero backend/schema/mobile:** matching = assign-by-upload on the existing Phase-69 endpoint; the assigned external then appears on the session via Phase 71's unified reader.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| T1 page: staging + thumbnails + soft-hint grid + nav | `17f3a77` | feat | part of the single phase commit |
| T2 session picker + assign via POST /videos + status | `17f3a77` | feat | " |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/match/page.js` | Created | The batch matching surface (staging, thumbnails, picker, assign) |
| `web/app/app/layout.js` | Modified | "Match videos" nav entry |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Web-only core, QR deferred | User-chosen; Phase 69 built the backend, iOS never touches external footage | Phase 70 committed scope = this plan; QR slate is a future mobile-gated phase |
| Client-side thumbnails | Server-light, no schema, works pre-upload | No api.py/Supabase change |
| Native `<select>` + athlete filter | Dependency-free, matches existing UI | If a coach routinely scrolls dozens of sessions, a search box is a cheap later upgrade |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | Plan executed as written |

**Total impact:** None — executed as specified. (Optional coverage endpoint offered pre-plan was declined; not built.)

## Issues Encountered

None. The page is auth-gated, so interactive verification (staging/thumbnail/upload) is impossible in the sandbox (no login/clips) — the same "built blind" ceiling as Phases 69/71. Automated gate (build + static prerender + route presence) is green.

## Next Phase Readiness

**Ready:** Phase 70 committed core is shipped. Foundation for the QR slate follow-on (web decode) is the same `/app/match` surface.

**Concerns:**
- Interactive UAT owed (see human steps): stage real clips → thumbnails render; assign → external appears on the session.
- Thumbnail frame-grab across odd codecs (HEVC/off-brand) may fail → falls back to "No preview" (non-blocking) — confirm on real GoPro/DJI footage.

**Blockers:** None.

---
*Phase: 70-video-session-matching, Plan: 01 — committed core complete; QR slate deferred. Code shipped `17f3a77`. `.paul` docs kept local; ROADMAP table untouched.*
*Completed: 2026-08-19*
