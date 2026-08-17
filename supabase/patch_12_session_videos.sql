-- Patch 12: session_videos — external camera videos (Phase 69-01)
-- Run in Supabase SQL Editor. User-applied. Idempotent. Nothing existing is touched.
--
-- WHY: Phase 69 lets a session carry up to 4 synced camera angles. The phone/primary video STAYS in
-- sessions.video_path / video_origin_s (unchanged — 5 web readers + mobile depend on it). This table
-- holds ONLY the ≤3 EXTERNAL videos, additively: no data is migrated, no existing reader changes.
--
-- Each row: one external clip in the private `videos` bucket at {session_id}/{id}.mp4, its own
-- origin_s (per-camera push-off sync offset, Phase 67-01 mechanic), and a coach label.
--
-- SECURITY: RLS enabled with NO policies = the anon key is denied. All access is through the API with
-- the service role (same model as the videos bucket + the sessions video endpoints). ON DELETE
-- CASCADE drops a session's externals when the session is deleted.

CREATE TABLE IF NOT EXISTS session_videos (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  storage_path text NOT NULL,
  origin_s     double precision,
  label        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS session_videos_session_id_idx ON session_videos(session_id);

ALTER TABLE session_videos ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE session_videos IS
  'External camera videos (<=3 per session, Phase 69). Phone/primary stays in sessions.video_path/'
  'video_origin_s. Private videos bucket at {session_id}/{id}.mp4; API/service-role access only.';
