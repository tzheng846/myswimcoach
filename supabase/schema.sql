-- Swimnetics schema
-- Run in Supabase SQL Editor (Settings → SQL Editor → New query)

-- ── teams ────────────────────────────────────────────────────────────────────
CREATE TABLE teams (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name              TEXT NOT NULL,
  subscription_tier TEXT NOT NULL DEFAULT 'starter',
  stripe_customer_id TEXT,
  device_limit      INT NOT NULL DEFAULT 1,
  swimmer_limit     INT NOT NULL DEFAULT 20,
  coach_limit       INT NOT NULL DEFAULT 3,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;

-- ── devices (pre-populated at manufacture; team_id NULL until claimed via QR) ─
CREATE TABLE devices (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  serial_number TEXT UNIQUE NOT NULL,
  mac_address   TEXT,
  team_id       UUID REFERENCES teams(id) ON DELETE SET NULL,
  label         TEXT,
  registered_at TIMESTAMPTZ
);
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;

-- ── athletes ─────────────────────────────────────────────────────────────────
CREATE TABLE athletes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id      UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  dob          DATE,
  stroke_type  TEXT NOT NULL DEFAULT 'breaststroke',
  head_waist_m FLOAT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE athletes ENABLE ROW LEVEL SECURITY;

-- ── coaches (linked to Supabase auth.users) ───────────────────────────────────
CREATE TABLE coaches (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  team_id    UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  email      TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'coach',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);
ALTER TABLE coaches ENABLE ROW LEVEL SECURITY;

-- ── sessions ─────────────────────────────────────────────────────────────────
CREATE TABLE sessions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  athlete_id       UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  device_id        UUID REFERENCES devices(id) ON DELETE SET NULL,
  coach_id         UUID REFERENCES coaches(id) ON DELETE SET NULL,
  recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stroke_type      TEXT NOT NULL DEFAULT 'breaststroke',
  raw_csv_path     TEXT,
  metrics_json     JSONB,
  velocity_profile JSONB,
  distance_profile JSONB,
  upload_status    TEXT NOT NULL DEFAULT 'pending',
  created_at       TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- ── RLS helper ───────────────────────────────────────────────────────────────
-- Returns the team_id for the currently authenticated coach.
CREATE OR REPLACE FUNCTION current_team_id()
RETURNS UUID AS $$
  SELECT team_id FROM coaches WHERE user_id = auth.uid() LIMIT 1;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ── RLS policies ─────────────────────────────────────────────────────────────
-- teams: coach sees only their own team
CREATE POLICY "coach sees own team" ON teams
  FOR SELECT USING (id = current_team_id());

-- athletes: coach sees / manages their team's athletes
-- WITH CHECK ensures INSERT also enforces team ownership (USING alone is ignored for INSERT)
CREATE POLICY "coach manages own athletes" ON athletes
  FOR ALL
  USING (team_id = current_team_id())
  WITH CHECK (team_id = current_team_id());

-- devices: coach sees their team's devices
CREATE POLICY "coach sees own devices" ON devices
  FOR SELECT USING (team_id = current_team_id());

-- sessions: coach sees/writes sessions belonging to their team's athletes
-- WITH CHECK ensures INSERT also enforces team ownership (USING alone is ignored for INSERT)
CREATE POLICY "coach manages own sessions" ON sessions
  FOR ALL
  USING (athlete_id IN (SELECT id FROM athletes WHERE team_id = current_team_id()))
  WITH CHECK (athlete_id IN (SELECT id FROM athletes WHERE team_id = current_team_id()));

-- coaches: coach sees only their own row
CREATE POLICY "coach sees own row" ON coaches
  FOR SELECT USING (user_id = auth.uid());
