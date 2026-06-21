-- Patch 05: allow a coach to UPDATE their own team row (team name).
-- Run in Supabase SQL Editor (Settings → SQL Editor → New query). User-applied.
--
-- WHY: the `teams` table only had a SELECT policy ("coach sees own team"), so the iOS
-- Settings screen's `supabase.from('teams').update({ name }).eq('id', teamId)` was silently
-- blocked by RLS (0 rows updated, no error) — the edited team name never persisted.
-- WITH CHECK ensures the coach can't repoint a row to a team they don't own.

CREATE POLICY "coach updates own team" ON teams
  FOR UPDATE
  USING (id = current_team_id())
  WITH CHECK (id = current_team_id());
