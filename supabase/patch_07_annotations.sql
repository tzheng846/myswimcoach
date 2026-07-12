-- Patch 07: trial annotation storage (Phase 47)
-- Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- WHY: Phase 47 adds a review-and-annotate tool — hand-marked swim phases
-- (dive → underwater kick/pulldown → breakout → stroke → finish, single ordered pass)
-- plus per-stroke boundaries, edited against the velocity trace + session video.
-- Annotations are ground truth for segmenter tuning (16-06) and manual corrections
-- for metric recomputation (47-04).
--
-- 1. session_annotations — one row per session, last write wins.
--    phases         JSONB: {"dive_start_s","underwater_start_s","breakout_start_s",
--                           "stroke_start_s","finish_s"} — any subset, seconds on the
--                           100 Hz session clock. "underwater" is the canonical key;
--                           clients display "pulldown" for breaststroke.
--    stroke_marks_s JSONB: sorted array of individual stroke-boundary times (seconds).
--    Writes go through the API (service role); the RLS policy lets the web portal
--    read via supabase-js like the rest of the schema.
CREATE TABLE IF NOT EXISTS session_annotations (
  session_id     UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
  phases         JSONB NOT NULL DEFAULT '{}',
  stroke_marks_s JSONB NOT NULL DEFAULT '[]',
  source         TEXT  NOT NULL DEFAULT 'manual',
  updated_by     UUID REFERENCES coaches(id) ON DELETE SET NULL,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE session_annotations ENABLE ROW LEVEL SECURITY;

-- Same team-scoping shape as the sessions policy (schema.sql), one hop further out.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'session_annotations'
      AND policyname = 'coach manages own annotations'
  ) THEN
    CREATE POLICY "coach manages own annotations" ON session_annotations
      FOR ALL
      USING (session_id IN (
        SELECT id FROM sessions WHERE athlete_id IN (
          SELECT id FROM athletes WHERE team_id = current_team_id())))
      WITH CHECK (session_id IN (
        SELECT id FROM sessions WHERE athlete_id IN (
          SELECT id FROM athletes WHERE team_id = current_team_id())));
  END IF;
END $$;

-- 2. Video attachment on sessions (first time video reaches the cloud).
--    video_path     — object path inside the private `videos` bucket.
--    video_origin_s — session-clock time (s) at which video t=0 aligns; per the
--                     44-03 end-anchor convention iOS computes
--                     deviceDuration − videoDuration at upload time.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS video_path     TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS video_origin_s DOUBLE PRECISION;

-- 3. Private videos bucket. No storage RLS policies — all storage access goes
--    through the API with the service role (same model as raw-csvs; clients get
--    time-limited signed URLs from GET /sessions/{id}/video-url).
INSERT INTO storage.buckets (id, name, public)
VALUES ('videos', 'videos', false)
ON CONFLICT (id) DO NOTHING;
