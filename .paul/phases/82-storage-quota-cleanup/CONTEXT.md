# Phase Context

**Phase:** 82 — Storage Quota Cleanup
**Generated:** 2026-08-27
**Status:** Ready for planning

## Trigger

Supabase free tier (1 GB file storage) is exceeded — live usage measured at **2.53 GB** (matches
the 2.6 GB the user saw in the dashboard). Confirmed via web search: free-tier overage gets a
grace-period warning, then Supabase **blocks new storage uploads** (no auto-billing) — so new
video uploads may already be at risk of silently failing.

## Measurements (read-only probes, 2026-08-27, scripts in `scratch/`)

- `raw-csvs` bucket: 16.7 MB, 224 files — negligible.
- `videos` bucket: **2,512 MB, 102 files** — effectively the entire problem.
- **37 of those 102 files are orphaned — 716 MB (28% of video storage) — referenced by no live
  row** (cross-checked against every `sessions.video_path` and `session_videos.storage_path`).
- **Two distinct leak sources, both landing in the `videos` bucket, both hit by
  `DELETE /sessions/{id}` ([api.py:709-765](../../../api.py:709)):**
  1. **`video_path`** (the primary/phone video column on `sessions`) — never captured, never
     removed. Only `raw_csv_path` is captured before the delete and cleaned up after
     ([api.py:740](../../../api.py:740), [api.py:761](../../../api.py:761)).
  2. **`session_videos`** (external-camera clips, Phase 69) — `session_id` has
     `ON DELETE CASCADE` ([patch_12_session_videos.sql:17](../../../supabase/patch_12_session_videos.sql:17)),
     and that patch's own comment claims cascade "drops a session's externals when the session is
     deleted" — true for the **Postgres row only**. Cascade never touches the Storage object, and
     once the row is cascade-deleted there is no longer any reference to find the orphaned file by.
     `delete_session_video` ([api.py:1425-1461](../../../api.py:1425), the *manual* per-video
     delete endpoint) does clean up both the object and the row correctly — but nothing runs that
     logic when the *parent session* is deleted instead of one video at a time.
  - **Confirmed exhaustive:** `session_annotations` also has `ON DELETE CASCADE` on `session_id`
    ([patch_07_annotations.sql:19](../../../supabase/patch_07_annotations.sql:19)) but holds no
    storage reference (jsonb only) — cascade fully handles it, no bug there. Cross-checked against
    `supabase/live_schema.json` (the introspected live schema, not the possibly-stale `schema.sql`):
    `session_annotations` and `session_videos` are the **only two tables** with a `session_id`
    column, so these two leak sources are the complete set — nothing else references a session.
  - The 716 MB / 37-file measurement above already reflects **both** leak sources combined (it
    diffed raw bucket contents against every currently-live path regardless of source table), so
    that reclaim number does not change — the fix just needs to close both going forward.
- Also found (out of scope for this phase, noted for later): 6 rows reference a storage path that
  no longer exists in the bucket (broken link the other direction) — pre-existing, not caused by
  this bug, not blocking.
- Growth: first video-attached session was 2026-08-06. 65 of 99 sessions now carry a video,
  averaging 24.4 MB each; the largest recent uploads (47-48 MB) are already brushing the 50 MB
  free-tier per-file cap ([api.py:1136](../../../api.py:1136) `MAX_VIDEO_BYTES`). Roughly
  500 MB–2 GB/month of new legitimate video at the current pace.
- Video bytes **do** pass through the FastAPI server today (`await file.read()` at
  [api.py:1186](../../../api.py:1186) and [api.py:1350](../../../api.py:1350)) before landing in
  storage — so server-side transcoding at upload time is architecturally possible if ever wanted,
  though not in scope here.

## Goals

- **Goal 1 (do regardless of anything else):** Fix `DELETE /sessions/{id}` so it removes **all**
  storage associated with a session before/around the row delete — not just the primary
  `video_path`, but also every `session_videos.storage_path` for that session (captured before
  the row delete triggers the cascade, since the cascade deletes the only record of where those
  files live). Stop the bleed from both leak sources.
- **Goal 2:** Run a one-time cleanup that purges the currently-orphaned files, reclaiming ~716 MB
  for zero cost. Must recompute the orphan set live at run time (bucket contents minus every
  currently-referenced path across **both** `sessions.video_path` and `session_videos.storage_path`),
  not from the static 2026-08-27 snapshot in `scratch/`, since more may accumulate before this ships.
- **Goal 3:** Close the remaining gap (post-cleanup, still ~1.8 GB vs the 1 GB cap) by **upgrading
  to Supabase Pro ($25/mo)** — user's explicit choice over compressing/re-encoding or deleting
  existing videos, given those videos are ground-truth sync footage for the segmenter-tuning arc
  (STATE.md item 9, the current top priority) and re-encoding/deletion risk that value.

## Approach

- Mirror the existing non-fatal storage-removal pattern already used for `raw-csvs`
  ([api.py:761-763](../../../api.py:761)) when adding `videos` removal to
  `DELETE /sessions/{id}` — same try/except-pass-on-failure shape, so a storage hiccup never
  blocks the row delete.
- **Capture order matters for `session_videos`:** query its `storage_path` list for the session
  *before* the `sessions` row delete executes (alongside the existing `raw_csv_path` /
  new `video_path` capture) — once the delete fires, `ON DELETE CASCADE` removes those rows
  immediately, and there is no way to recover which files they pointed to afterward. Batch
  `video_path` + all `session_videos.storage_path` values into one `storage.from_("videos").remove([...])`
  call after the row delete succeeds.
- One-time cleanup as a standalone script under `tools/`, following the existing
  `tools/backfill_phases.py` precedent (manual, user-run, not wired into any endpoint) — read
  live bucket listing + live `sessions.video_path` + `session_videos.storage_path`, diff, confirm,
  delete. Should be read-only/dry-run by default with an explicit `--apply` flag, matching the
  backfill script's safety pattern.
- Pytest coverage for the `DELETE /sessions/{id}` fix, extending the existing mocked-Supabase
  suite in `tests/test_api.py` (443 green per STATE.md) — assert the video storage `.remove()`
  call includes `video_path` when set, includes every `session_videos.storage_path` for that
  session, and is skipped/harmless when there's neither.
- The Pro upgrade itself is a **user-executed, out-of-band action** (Supabase dashboard, payment)
  — not something built or deployed by this phase. When it happens, the three-part checklist
  already written in [supabase/patch_11_video_size.sql](../../../supabase/patch_11_video_size.sql)
  applies together: raise the Supabase dashboard global upload limit to 500 MB, bump
  `MAX_VIDEO_BYTES` in both `api.py` and `web/components/portal/VideoPane.js` to match, and run
  patch_11 (the per-bucket limit patch, currently a no-op on free tier by design).

## Constraints

- Don't touch the standalone `delete_session_video` endpoint
  ([api.py:1425](../../../api.py:1425)) — the manual per-video delete path already cleans up
  correctly. `DELETE /sessions/{id}` needs its own read of `session_videos` (see Approach) since
  it deletes the parent row directly rather than going through that endpoint per-video.
- Cleanup script must never delete a file any live row currently references — recompute the diff
  at execution time, don't trust a cached list.
- Ground-truth video (used for annotation/sync, Phase 47/58/67/81) is not to be deleted or
  re-encoded as part of closing the quota gap — the user chose to pay instead specifically to
  avoid that risk.

## Open Questions

- Should the one-time cleanup script also become a small recurring/periodic check (so a future
  regression of the same bug class doesn't silently reaccumulate), or is a single manual run
  sufficient for now? Leave to `/paul:plan` to scope — lean toward "just the fix + one script,"
  consistent with how `tools/backfill_phases.py` and other one-shot repo tools work.
- The 6 broken-link rows (DB references a path missing from the bucket) are a separate,
  pre-existing inconsistency, not caused by this bug. Out of scope unless the user wants it folded
  in during planning.

## Additional Context

Probe scripts used to gather the numbers above (read-only, no writes) are in `scratch/`:
`storage_size_probe.py`, `storage_growth_probe.py`, `orphan_video_probe.py`. These are throwaway
discovery tools, not the deliverable — the actual cleanup script belongs under `tools/` per repo
convention and should be written fresh during `/paul:apply` (recomputing the orphan set live,
per Goal 2 above) rather than reusing the scratch snapshot.

---

*This file is temporary. It informs planning but is not required.*
*Created by /paul:discuss, consumed by /paul:plan.*
