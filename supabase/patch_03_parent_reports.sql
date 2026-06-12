-- Patch 03: parent contact info + shareable report cards
-- Run in Supabase SQL Editor (Settings → SQL Editor → New query)

-- ── athletes: parent contact ─────────────────────────────────────────────────
ALTER TABLE athletes ADD COLUMN parent_name  TEXT;
ALTER TABLE athletes ADD COLUMN parent_email TEXT;

-- ── reports (parent-facing progress report cards) ────────────────────────────
-- token is the only credential a parent has; public access goes through the
-- service-role API (GET /reports/{token}) — no anon RLS policy on purpose.
CREATE TABLE reports (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  athlete_id  UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  coach_id    UUID REFERENCES coaches(id) ON DELETE SET NULL,
  token       TEXT UNIQUE NOT NULL,
  config_json JSONB NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  sent_at     TIMESTAMPTZ
);
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

CREATE INDEX reports_token_idx ON reports(token);

-- ── RLS ──────────────────────────────────────────────────────────────────────
-- coach manages reports for their team's athletes
-- WITH CHECK ensures INSERT also enforces team ownership (USING alone is ignored for INSERT)
CREATE POLICY "coach manages own reports" ON reports
  FOR ALL
  USING (athlete_id IN (SELECT id FROM athletes WHERE team_id = current_team_id()))
  WITH CHECK (athlete_id IN (SELECT id FROM athletes WHERE team_id = current_team_id()));
