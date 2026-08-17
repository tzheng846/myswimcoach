-- Patch 11: raise the videos bucket file-size limit (Phase 67-02)
-- ⚠ PRO-TIER ONLY — DO NOT APPLY ON THE FREE TIER. Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- CONTEXT: the `videos` bucket was created (patch_07) with NO file_size_limit, so it inherits the
-- PROJECT GLOBAL upload limit. On the FREE tier that global limit is a hard 50 MB that per-bucket
-- limits CANNOT exceed — so on free tier this patch has no useful effect and must not be applied.
-- The system already matches the 50 MB reality in code: api.py MAX_VIDEO_BYTES and the client
-- MAX_VIDEO_BYTES both reject >50 MB uploads with a "compress it / upgrade to Pro" message.
--
-- WHEN UPGRADING TO SUPABASE PRO, do all three together:
--   1. Dashboard → Project Settings → Storage → raise the global "Upload file size limit" to 500 MB.
--   2. Set api.py MAX_VIDEO_BYTES and web/components/portal/VideoPane.js MAX_VIDEO_BYTES to 500 MB.
--   3. Run this patch.
--
-- 524288000 = 500 MB. A single-swim clip is ~100–300 MB at 1080p; 500 MB gives margin while bounding
-- storage cost. allowed_mime_types is left NULL (accept all): a restrictive list risks rejecting
-- valid GoPro content-types; format guidance is handled client-side (VideoPane onError + hint).

UPDATE storage.buckets
SET file_size_limit = 524288000  -- 500 MB
WHERE id = 'videos';
