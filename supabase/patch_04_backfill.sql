-- Patch 04: BACKFILL — documents migrations ALREADY APPLIED to the live DB
-- via the Supabase SQL editor during Phases 12-01, 14-01, and 15-01, which
-- were never committed (CODEBASE-AUDIT.md §5.2).
--
-- Purpose: make `supabase/` reproduce the live schema for disaster recovery /
-- new environments. Reconstructed from code evidence (api.py + iOS/web reads),
-- not from a dump — VERIFY against the dashboard (Table Editor) before
-- trusting column types/defaults exactly.
--
-- Running this against the CURRENT live DB should be a no-op (IF NOT EXISTS /
-- guarded blocks), but it is written primarily as documentation.

-- ── Phase 12-01: session metadata ─────────────────────────────────────────────
-- Evidence: api.py /process inserts name/notes/stroke_type; PATCH allows
-- name/notes/is_starred; iOS/web session cards read all three.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS name       TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS notes      TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE;

-- ── Phase 14-01: devices reshape + sessions.device_id as TEXT chip id ─────────
-- Evidence: api.py upserts devices on chip_id (on_conflict="chip_id") with
-- coach_id / firmware_version / last_seen_at / name; /process writes
-- sessions.device_id = chip id string. The original schema.sql shape
-- (serial_number / mac_address / team_id / label, sessions.device_id UUID FK)
-- was replaced in the live DB.
--
-- NOTE: devices.coach_id deliberately has NO foreign key — the FK failed in
-- the SQL editor at the time; ownership is enforced at the application layer
-- (STATE.md Phase 14-01 decision).

-- sessions.device_id: UUID FK → plain TEXT chip id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'sessions' AND column_name = 'device_id'
      AND data_type = 'uuid'
  ) THEN
    ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_device_id_fkey;
    ALTER TABLE sessions ALTER COLUMN device_id TYPE TEXT;
  END IF;
END $$;

-- devices: replace manufacture-time shape with chip-id auto-registration shape
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'devices' AND column_name = 'chip_id'
  ) THEN
    DROP TABLE IF EXISTS devices;
    CREATE TABLE devices (
      chip_id          TEXT PRIMARY KEY,          -- upsert conflict target
      coach_id         UUID,                      -- no FK by decision (Phase 14-01)
      name             TEXT,
      firmware_version TEXT,
      last_seen_at     TIMESTAMPTZ,
      created_at       TIMESTAMPTZ DEFAULT NOW()
    );
    ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
    -- No anon/coach RLS policy required: all device reads/writes go through
    -- api.py with the service role (iOS DevicesScreen → GET/PATCH/DELETE /devices).
  END IF;
END $$;

-- ── Phase 15-01: coaches billing columns ──────────────────────────────────────
-- Evidence: api.py _get_coach_row selects these; /billing/webhook updates them;
-- defaults = free tier (_TIER_LIMITS["free"]).
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS stripe_customer_id    TEXT;
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS subscription_tier     TEXT DEFAULT 'free';
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS subscription_status   TEXT DEFAULT 'active';
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS athlete_limit         INT  DEFAULT 3;
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS device_limit          INT  DEFAULT 1;
ALTER TABLE coaches ADD COLUMN IF NOT EXISTS monthly_session_limit INT  DEFAULT 20;

-- ── athletes.coach_id (added somewhere in Phases 6–15; exact phase unrecorded) ─
-- Evidence: api.py POST /athletes inserts coach_id and athlete-limit counts
-- filter on it; web/iOS rosters scope by RLS team policy, API by coach_id.
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS coach_id UUID;
