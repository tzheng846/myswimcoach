---
phase: 67-external-camera-sync
plan: 02
subsystem: api
tags: [fastapi, supabase-storage, upload, size-limit, streaming, video, gopro, free-tier]

requires:
  - phase: 67-external-camera-sync
    provides: 67-01 push-off align (the sync mechanic these caps protect)
provides:
  - memory-safe video upload size guard (413 before buffering) + streamed Storage upload
  - free-tier 50 MB cap enforced on server + client with actionable compress/upgrade messaging
  - patch_11 (Pro-tier cap raise artifact, not applied on free tier)
affects: [pro-tier upgrade, phase-49 security-hardening upload caps]

tech-stack:
  added: []
  patterns:
    - "Upload size cap is a single constant mirrored server (api.py) + client (VideoPane) + patch_11; it tracks the ACTIVE Supabase global limit."
    - "Stream multipart uploads to storage3 from the spooled temp file (storage3 accepts a file object) instead of await file.read() — no full-file RAM copy."

key-files:
  created:
    - supabase/patch_11_video_size.sql
  modified:
    - api.py
    - tests/test_api.py
    - web/components/portal/VideoPane.js

key-decisions:
  - "Free tier caps uploads at a hard 50 MB — guide manual compression + defer real >50 MB to Pro rather than build throwaway in-browser transcoding."
  - "Cap = 50 MB now (matches free-tier global ceiling); patch_11 (500 MB) + code bump documented as the Pro-upgrade step."
  - "Size guard placed BEFORE _get_supabase_admin() so it 413s memory-safely and is testable without a Storage mock."

patterns-established:
  - "In-browser video compression was explicitly rejected as throwaway-on-Pro; the honest free-tier path is a clear cap + compress/upgrade guidance."

duration: ~50min
started: 2026-08-17T00:20:00Z
completed: 2026-08-17T01:10:00Z
---

# Phase 67 Plan 02: Production-Size Robustness Summary

**Made the external-video upload path safe and honest on the free tier: a memory-safe 413 guard that
rejects oversized clips before buffering, a streamed Storage upload (no full-file RAM copy), and a
50 MB cap on both server and client with an actionable "compress it / upgrade to Pro" message. The
real >50 MB path is deferred to a Pro upgrade (patch_11 + a one-line cap bump already written), after
the free-tier 50 MB hard ceiling ruled out raising the cap.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~50 min (incl. the mid-plan free-tier pivot) |
| Completed | 2026-08-17 |
| Tasks | 3 auto completed; 1 human-action checkpoint DISSOLVED (see deviations) |
| Files modified | 4 |
| Commits | `030f6f9` (code), `e3ce464` (free-tier 50 MB pivot) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Oversized rejected memory-safely | Pass | 413 fires BEFORE `_get_supabase_admin()` and before any read; `TestVideoUploadSizeGuard` green. |
| AC-2: Accepted uploads stream (no full-file RAM copy) | Pass (code) | Uploads `file.file` (spooled temp) to storage3, which accepts a file object; response shape unchanged. ⚠ Live streaming confirmation rides the real-clip UAT. |
| AC-3: Bucket accepts real GoPro-size clips | **Deferred → Pro** | Free tier's 50 MB global ceiling cannot be raised; real GoPro clips must be compressed to <50 MB first (user decision). Free-tier equivalent — accepts ≤50 MB clips — pending UAT with a compressed clip. `patch_11` + the 500 MB bump are the documented Pro-upgrade flip. |
| AC-4: Clear client-side guidance | Pass | Too-large → "compress (HandBrake / GoPro Quik) to under 50 MB, or upgrade to Pro"; `onError` → H.264 .mp4 hint; attach-card format nudge. |

## Verification Results

- `python -c "import api"` clean; `api.MAX_VIDEO_BYTES == 52428800` (50 MB).
- `pytest tests/test_api.py -q` → **58 passed** (incl. the new 413 test) — both before and after the pivot.
- `cd web && npm run build` → **Compiled successfully, exit 0** — both before and after the pivot.
- Railway `/health` → HTTP 200 after deploy.

## Accomplishments

- The server can no longer be OOM'd by a large upload: an oversized clip is refused with a 413 before
  a single byte is buffered, and accepted clips stream to Storage rather than being read whole into RAM.
- The 50 MB reality is now honest end-to-end — the coach gets an instant, actionable message instead
  of a late, opaque Storage rejection.
- The Pro upgrade is a documented three-line flip (raise the Supabase global limit, bump two
  `MAX_VIDEO_BYTES` constants, apply `patch_11`) with zero rework.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| T1: patch_11 (bucket cap) | `030f6f9` → `e3ce464` | infra | Written at 500 MB, then reframed as the Pro-tier-only artifact. |
| T2: api.py guard + test | `030f6f9` → `e3ce464` | feat | Size guard (413, pre-buffer) + streamed upload; `TestVideoUploadSizeGuard`; cap 500→50 MB. |
| T3: VideoPane client guards | `030f6f9` → `e3ce464` | feat | Pre-upload size reject + `onError` + format hint; cap 500→50 MB + compress/upgrade message. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Guide manual compression + defer >50 MB to Pro | User is on the free tier (hard 50 MB); in-browser transcoding (ffmpeg.wasm) is heavy AND throwaway the moment they go Pro | No throwaway work; feature usable today with a <50 MB (compressed) clip |
| Cap = 50 MB now, 500 MB documented for Pro | Match the active Supabase global limit exactly so the guard's message is truthful | Guard rejects >50 MB cleanly instead of letting Supabase fail at 50 MB |
| Stream from the spooled temp file | storage3 accepts a file object (verified); avoids a 50–500 MB RAM copy regardless of Railway instance size | Memory-safe upload; also partially satisfies Phase 49-01's intent |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Scope pivot | 1 | Free-tier discovery → cap 500→50 MB + defer to Pro |
| Checkpoint dissolved | 1 | The blocking Supabase human-action became a no-op on free tier |
| Deferred | 1 | Real >50 MB upload → Pro upgrade (documented) |

**Total impact:** The plan's "raise the cap to 500 MB" premise was invalidated mid-flight by the
user's free-tier 50 MB ceiling. Pivoted to the no-throwaway path (user-chosen via AskUserQuestion).
No scope creep; the memory-safe guard + streaming (the load-bearing robustness) shipped unchanged.

### Deferred Items

- Real >50 MB external footage: needs a Supabase Pro upgrade (raise global limit + bump the two
  `MAX_VIDEO_BYTES` + apply `patch_11`). Fully documented in `patch_11_video_size.sql` and the code.
- In-browser auto-compression (ffmpeg.wasm / MediaRecorder): explicitly rejected as throwaway-on-Pro.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| The originally-shipped 500 MB cap (`030f6f9`) was wrong for the free tier — it let 51–499 MB files reach Supabase, which rejects them at 50 MB with an opaque error | Corrected both caps to 50 MB (`e3ce464`) so the clean client/server message fires first |
| Blocking human-action checkpoint (raise cap + apply patch_11) had no valid action on free tier | Dissolved it: on free tier nothing is applied; patch_11 reframed as the Pro-only artifact |

## Next Phase Readiness

**Ready:**
- Phase 67 is code-complete: external clips (≤50 MB, compressed) attach, sync via push-off align, and
  play. The upload path is memory-safe.

**Concerns:**
- ⚠ On the free tier the feature is usable ONLY with a compressed <50 MB clip — full GoPro footage
  awaits Pro.
- ⚠ **Real-clip UAT is owed** (67-01 align "feel" + 67-02 <50 MB upload/play) — needs the user with a
  compressed clip. Streaming upload has not been exercised against live Supabase yet.

**Blockers:**
- None for closing Phase 67. Pro upgrade is an optional future flip, not a blocker.

---
*Phase: 67-external-camera-sync, Plan: 02*
*Completed: 2026-08-17*
