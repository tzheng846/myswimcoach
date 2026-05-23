-- Patch 01: Add WITH CHECK to athletes and sessions RLS policies.
-- USING alone is silently ignored for INSERT in PostgreSQL.
-- Run in Supabase SQL Editor.

-- athletes
DROP POLICY IF EXISTS "coach manages own athletes" ON athletes;
CREATE POLICY "coach manages own athletes" ON athletes
  FOR ALL
  USING (team_id = current_team_id())
  WITH CHECK (team_id = current_team_id());

-- sessions
DROP POLICY IF EXISTS "coach manages own sessions" ON sessions;
CREATE POLICY "coach manages own sessions" ON sessions
  FOR ALL
  USING (athlete_id IN (SELECT id FROM athletes WHERE team_id = current_team_id()))
  WITH CHECK (athlete_id IN (SELECT id FROM athletes WHERE team_id = current_team_id()));
