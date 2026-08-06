-- Patch 06: sessions.device_id  UUID  →  TEXT (chip id)
--
-- WHY: api.py /process writes the device's chip-id STRING (e.g. "64CD4D", derived from
-- the BLE name "SwimLogger-64CD4D") into sessions.device_id. The live column is still the
-- original schema.sql UUID FK shape, so every insert with a paired device fails:
--     invalid input syntax for type uuid: "64CD4D"   (Postgres 22P02)
-- Because the save is non-fatal in api.py, the swimmer sees the report and then a
-- "⚠ Save failed" line — and the session is never stored. Confirmed on-device 2026-06-22.
--
-- This completes the Phase-14 intent that patch_04_backfill.sql:31-42 documented but that
-- was never actually run against the live DB (the 22P02 error proves the column is still
-- uuid). The FK target devices(id) is itself stale — Phase 14 reshaped `devices` to a
-- chip-id primary key with no `id` column — so device_id must be plain TEXT (the chip id),
-- NOT a UUID FK. No application code changes: api.py is already correct against a TEXT column.
--
-- Idempotent: the data_type guard + DROP CONSTRAINT IF EXISTS make a second run a no-op.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'sessions'
      AND column_name = 'device_id'
      AND data_type = 'uuid'
  ) THEN
    -- Defensive: the live DB has NO sessions_device_id_fkey (the original UUID FK was
    -- already dropped when devices was reshaped to a chip-id PK), so this is a no-op here;
    -- IF EXISTS keeps it safe in any environment that still carries the old constraint.
    ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_device_id_fkey;
    -- Widen uuid → text. USING device_id::text converts existing values (uuid → its text
    -- form; NULLs stay NULL) — Postgres does not implicitly coerce uuid to text here.
    ALTER TABLE sessions ALTER COLUMN device_id TYPE TEXT USING device_id::text;
  END IF;
END $$;
