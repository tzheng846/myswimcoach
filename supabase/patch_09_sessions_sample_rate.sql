-- Patch 09: per-session true sample rate (Phase 52-01)
-- Run in Supabase SQL Editor. User-applied. Idempotent.
--
-- WHY: vel_acc_extraction.decimate_signal decimates by an INTEGER factor
-- (round(268.5 / 100) = 3 → 89.5 Hz), so the requested TARGET_FS_HZ = 100 is
-- never actually achieved — and api.py discarded the actual_fs the pipeline
-- returned. Every consumer then assumed 100 Hz, which made the annotate page
-- show a 47.1 s swim as 42.2 s and shifted every time-derived metric by ~11.7%
-- when metrics were recomputed from a saved annotation (API-AUDIT.md F2 + F3).
--
-- NULLABLE ON PURPOSE, and deliberately NO DEFAULT: rows written before this
-- patch have no recorded rate, and readers fall back to 100 for them so their
-- behavior is unchanged. A DEFAULT of 100 would make "genuinely 100 Hz"
-- indistinguishable from "never recorded" — exactly the distinction the 52-02
-- backfill needs in order to know which rows to repair.

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS sample_rate_hz DOUBLE PRECISION;
