-- Patch 13: sessions.recording_token — QR video-session matching (Phase 70 QR slate)
-- Run in Supabase SQL Editor. User-applied. Idempotent. Nothing existing is touched.
--
-- WHY: the phone generates a short token at record start, DISPLAYS it as a QR (filmed by an
-- over-water camera) and sends it to POST /process, which stores it here. On the web /app/match
-- page, jsQR decodes the token from an uploaded clip's early frames and looks up the session with
-- this token (supabase-js, coach-scoped RLS) to PRE-FILL the match. A scrapped swim / no-QR clip
-- matches nothing → it stays on the manual matching path (Phase 70 core, D4).
--
-- SAFE PRE-DEPLOY: /process writes this column ONLY when the phone actually sends a token, so every
-- existing mobile build (which sends none) keeps inserting sessions without it even before this
-- patch runs. Apply this together with the paid EAS build that ships the phone's QR display.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS recording_token text;

CREATE INDEX IF NOT EXISTS sessions_recording_token_idx ON sessions(recording_token);

COMMENT ON COLUMN sessions.recording_token IS
  'Phone-generated QR token (Phase 70). Displayed as a QR at record start, filmed by an external '
  'camera, decoded on /app/match to pre-fill the video-session match. Nullable; NULL = no slate.';
