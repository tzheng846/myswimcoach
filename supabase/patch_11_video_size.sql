-- Patch 11: raise the videos bucket file-size limit (Phase 67-02)
-- Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- WHY: the `videos` bucket was created (patch_07) with NO file_size_limit, so it
-- inherits the PROJECT GLOBAL upload limit — Supabase's ~50 MB default. External
-- cameras (GoPro / waterproof) produce clips far larger than 50 MB even for a single
-- swim (1080p30 ~45 Mbps ≈ 170 MB for 30 s), so real footage is rejected at the
-- Storage layer today. Phase 67 (external-camera push-off sync) needs real clips to
-- upload, so the per-bucket cap is raised here.
--
-- 524288000 = 500 MB. This MUST match api.py MAX_VIDEO_BYTES and the client
-- MAX_VIDEO_BYTES in web/components/portal/VideoPane.js. A single-swim clip is
-- ~100–300 MB at 1080p; 500 MB gives margin while bounding storage cost.
--
-- ⚠ The PROJECT GLOBAL upload limit still caps this and is a SEPARATE dashboard
-- setting: Project Settings → Storage → "Upload file size limit". Raise it to
-- ≥ 500 MB there as well, or this per-bucket value has no effect. On plans whose
-- global ceiling is below 500 MB (e.g. the free tier), this approach does not apply
-- and the upload path needs client-side compression / resumable upload instead.
--
-- allowed_mime_types is intentionally left NULL (accept all): a restrictive list
-- risks rejecting valid GoPro content-types. Format guidance is handled client-side
-- (VideoPane onError + a recommended-format hint).

UPDATE storage.buckets
SET file_size_limit = 524288000  -- 500 MB
WHERE id = 'videos';
