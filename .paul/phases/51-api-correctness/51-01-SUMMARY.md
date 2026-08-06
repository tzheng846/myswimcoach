---
phase: 51-api-correctness
plan: 01
subsystem: backend
tags: [audit, schema-contract, introspection, ast, api]
requires: []
provides:
  - API-AUDIT.md (11 ranked findings + 24-endpoint inventory + ownership rule)
  - tools/introspect_schema.py (live schema snapshot, read-only)
  - supabase/live_schema.json (authoritative schema — 7 tables, 67 columns)
  - tools/schema_contract.py (AST column-reference checker, ready to promote into a test)
affects:
  - 51-02 (its work list; the extractor becomes a permanent test there)
  - future FS_HZ phase (F2/F3 quantified here)
  - 49-01 (cross-referenced, not duplicated)
tech-stack:
  added: []
  patterns: ["schema truth comes from PostgREST's OpenAPI doc, not committed SQL",
    "AST-scoped column extraction — regex cannot distinguish a column from a response-dict key"]
key-files:
  created: [API-AUDIT.md, tools/introspect_schema.py, tools/schema_contract.py, supabase/live_schema.json]
  modified: []
key-decisions:
  - "api.py left untouched — report-only, per the audit-before-fix decision"
  - "Severity means observable damage today, not effort to fix"
  - "Data reads left out of scope; the one question needing them is documented with its query"
duration: ~50m
completed: 2026-07-30
---

# Phase 51 Plan 01: API Audit Summary

**Audited all 24 endpoints of `api.py` against the real database schema and produced
`API-AUDIT.md`: 11 ranked findings, a full endpoint inventory with callers, and a per-table
ownership rule. No production code was changed.**

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| AC-1 every endpoint accounted for | ✅ PASS | 24 rows; count matches `grep -c "^@app\." api.py` |
| AC-2 schema contract proven both directions | ✅ PASS | 4 violations found, 0 false positives; "live but unreferenced" reported with its limitation stated |
| AC-3 ownership rule stated + deviations listed | ✅ PASS | Rule per table; the only deviations are the four F1 sites |
| AC-4 findings ranked and actionable | ✅ PASS | S1→S4, each with file:line, observable behavior, blast radius, recommended fix |
| AC-5 unambiguous work list for 51-02 | ✅ PASS | 6-item ordered sequence + 2 accept-and-document items |
| AC-6 honest about coverage | ✅ PASS | 6 named gaps incl. both extractor blind spots |

## Accomplishments
- **`tools/introspect_schema.py`** — snapshots the live schema from PostgREST's OpenAPI document.
  Catalog metadata only; no rows read, nothing written; never prints a secret.
- **`supabase/live_schema.json`** — 7 tables, 67 columns. The first authoritative schema record in
  the repo; `schema.sql` and `patch_04` have both been proven wrong.
- **`tools/schema_contract.py`** — AST walker resolving supabase builder chains to their
  `.table("X")` root and checking every column in `.select()`, filters, and insert/update payloads.
- **`API-AUDIT.md`** — the deliverable.

## Findings (full detail in API-AUDIT.md)
**S1 — breaks in production**
- **F1** Phantom `athletes.coach_id` at 4 sites → `POST /athletes` 500s, athlete limit never
  enforced, coach-chat team tools broken since Phase 33-02, `billing/status` always reports 0.
- **F2** Stored profiles are **89.5 Hz**, not 100 Hz (`round(268.5/100) = 3` → `268.5/3`), but
  `annotations.FS_HZ = 100` and three api.py sites assume it → **~11.7% error on every time-derived
  metric recomputed from an annotation**.
- **F3** `api.py:143` discards `_actual_fs` and the `sessions` row has no rate column — so the
  correct value is destroyed at write time, not merely mis-assumed.

**S2 — wrong data, silently**
- **F4** All three tier limits fail open (`except: count = 0` then compare).
- **F5** iOS displays `teams.swimmer_limit`; api.py enforces `coaches.athlete_limit`. **`api.py`
  never reads `teams` at all** — 0 occurrences.
- **F6** 7 of 11 coach lookups mask DB failures as 403; the correct hardened pattern already exists
  at the other 4 (Phase-36) and was never propagated.

**S3/S4** — duplicated billing state across `coaches`/`teams` (F7); 11 inlined coach lookups vs the
existing `_get_coach_row` (F8); `GET /sessions/{id}/export` has zero callers (F9); 4 billing
endpoints have zero client callers (F10); no input-validation layer (F11 — assessed as *not* worth
pydantic, with one caveat).

## Verification
- `python tools/introspect_schema.py` → exits 0, `athletes` has no `coach_id`.
- `python tools/schema_contract.py api.py supabase/live_schema.json` → exactly the 4 known
  violations, no false positives on `sessions`/`devices`/`reports`.
- Extractor self-check: catches injected bad columns in both `select` and `eq`; zero false positives
  on valid chains; **zero false positives on response-dict literals** — the failure mode that made
  the throwaway regex version unusable.
- `pytest tests/ -q` → **149 passed**, unchanged (api.py untouched, as required).
- Route count `grep -c "^@app\."` = 24, matching the inventory.

## Deviations from Plan
Two, both scope reductions I'd flag rather than bury:

1. **Task 5 could not answer "how many stored sessions carry recomputed metrics."** That needs a
   data read, and only read-only *catalog* introspection was approved. The exact SQL is recorded in
   the audit's coverage section for you to run.
2. **The extractor has two blind spots** — column lists passed to helpers as strings, and payload
   dicts built in a variable. Both are documented; the 5 helper call sites were verified by hand
   (all fields exist on `coaches`). The consequence is that "live but never referenced" is a lead
   list, not proof, and the audit says so.

## ⚠ Worth surfacing beyond the findings list
- **F2+F3 together are probably more serious than F1.** F1 is loud — it 500s, you noticed it the
  same day. F2 is silent and corrupts data that looks plausible: every session recomputed from an
  annotation has time-derived metrics off by ~11.7%, and the annotate page has been showing wrong
  durations to whoever used it. It should precede 50-02, since 50-02's whole design is propagating
  annotations across ~144 generated sessions.
- **Segmentation is not corrupted by F2.** The time→index round-trip uses the same wrong constant
  in both directions, so annotation marks land on the sample the coach actually clicked. Only the
  time interpretation is wrong. That makes the fix cheaper than it first appears.
- **The `teams` table is dead weight in this backend** and simultaneously the source of a number the
  iOS app displays. That combination is how F5 will bite again if left alone.

## Next Phase Readiness
`API-AUDIT.md` closes with a 6-item ordered fix sequence. 51-02 is planned and its Task 0 is
triaging exactly this list. Recommended order stands: 51-02 first (unblocks athlete creation), then
the sample-rate phase before 50-02, then 49-01.

---
*Phase: 51-api-correctness, Plan: 01*
*Completed: 2026-07-30*
