-- Patch 10: per-session acceleration profile (Phase 64-02)
-- Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- WHY: the signal pipeline already computes acceleration (run_pipeline returns
-- it), but api.py discarded it as `_accel` and only ever stored velocity_profile
-- + distance_profile. The web wants an acceleration trace alongside velocity, so
-- it is persisted here rather than re-derived on every page load.
--
-- Acceleration is a PURE, deterministic function of the stored velocity_profile
-- (vel_acc_extraction.acceleration_from_velocity: decimate velocity to 5 Hz,
-- np.gradient, interpolate back). So existing rows can be backfilled EXACTLY from
-- velocity_profile + sample_rate_hz — no raw-CSV reprocessing — by
-- tools/backfill_acceleration.py.
--
-- NULLABLE ON PURPOSE, NO DEFAULT: a NULL acceleration_profile means the row
-- predates this patch and has not been backfilled yet. Readers must treat NULL as
-- "no acceleration available" (draw nothing) rather than as an empty trace.

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS acceleration_profile jsonb;

COMMENT ON COLUMN sessions.acceleration_profile IS
  'Per-sample acceleration (m/s^2) at sample_rate_hz, same length as velocity_profile. '
  'Exact derivative of velocity_profile via vel_acc_extraction.acceleration_from_velocity. '
  'NULL predates Phase 64-02 (backfill with tools/backfill_acceleration.py).';
