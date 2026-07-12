-- Patch 08: once-only backup of auto-computed metrics (Phase 47-04)
-- Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- WHY: saving a trial annotation with stroke boundaries now RECOMPUTES the
-- session's metrics from the human boundaries and OVERWRITES metrics_json
-- (user decision 2026-07-12: overwrite + backup — every consumer updates with
-- zero client changes). The original auto pipeline result is preserved here
-- the FIRST time a session is recomputed and never overwritten afterwards;
-- DELETE /sessions/{id}/annotations restores metrics_json from it.

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS metrics_json_auto JSONB;
