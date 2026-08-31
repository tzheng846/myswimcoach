-- Patch 14: absolute session start + its measured error bars (Phase 86-01)
-- Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- WHY: every encoder sample is stamped with micros() — microseconds since the
-- ESP32 booted, which wraps at 71.6 min and means nothing outside that boot.
-- Absolute time existed only as sessionStartPhoneMs, computed on the phone from
-- the META packet, used for the local video overlay, and then discarded. So
-- nothing in the system could answer "what UTC instant was sample #0?" — the one
-- thing any external video system needs to align its frames to our trace.
--
-- BIGINT EPOCH MILLISECONDS, NOT timestamptz, on purpose: this is the number the
-- phone computes and the number an external video system consumes. Converting to
-- timestamptz on write and back on read adds two places to get a timezone wrong
-- and buys nothing — Postgres timestamptz is microsecond-precision, so no
-- accuracy is gained.
--
-- NULL MEANS "UNKNOWN", NEVER "assume recorded_at". recorded_at is UPLOAD time,
-- not swim time (api.py never sets it, so the DB default NOW() fires when the
-- phone finishes uploading, which can be hours or days after the swim).
--
-- NO BACKFILL IS POSSIBLE. Only the phone can produce this, at recording time.
-- Every session recorded before Phase 86 holds NULL permanently — the same
-- reasoning that forbids backfilling a NULL sample_rate_hz with 100 (patch_09):
-- a default would make "genuinely measured" indistinguishable from "never
-- recorded", and here there is no second pass that could ever repair it.
--
-- sync_error_ms is the phone's measured one-way BLE flight time to the encoder;
-- clock_offset_ms is the phone's measured offset from server UTC. Both are
-- DIAGNOSTICS, not corrections — the correction is already baked into
-- session_start_utc_ms. They exist so a suspect alignment can be explained after
-- the fact rather than re-litigated.

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_start_utc_ms BIGINT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS sync_error_ms        DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS clock_offset_ms      DOUBLE PRECISION;
