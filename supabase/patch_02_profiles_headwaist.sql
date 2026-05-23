-- Patch 02: add full session profiles + athlete anthropometrics
-- Run in Supabase SQL Editor (Settings → SQL Editor → New query)

ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS velocity_profile JSONB,
  ADD COLUMN IF NOT EXISTS distance_profile JSONB;

ALTER TABLE athletes
  ADD COLUMN IF NOT EXISTS head_waist_m FLOAT;
