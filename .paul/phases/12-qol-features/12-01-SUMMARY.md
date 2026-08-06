---
phase: 12-qol-features
plan: 01
type: summary
completed: 2026-05-25
---

# Summary: Plan 12-01 — Backend Schema + CRUD Endpoints

## What Was Built

- Supabase `sessions` table: 4 new columns (`name`, `notes`, `is_starred`, `stroke_type`)
- `POST /process`: accepts `name`, `notes`, `stroke_type` form params; stores them in session row; returns `session_id`
- `PATCH /sessions/{id}`: updates `name`, `notes`, `is_starred`; enforces coach ownership via `coach_id`
- `DELETE /sessions/{id}`: hard-deletes session row; enforces coach ownership via `coach_id`

## Acceptance Criteria Results

| AC | Description | Result |
|----|-------------|--------|
| AC-1 | Schema migration applied — 4 new columns exist | ✓ Pass |
| AC-2 | POST /process stores name, notes, stroke_type; returns session_id | ✓ Pass |
| AC-3 | POST /process backward-compatible (all new fields optional) | ✓ Pass |
| AC-4 | PATCH updates allowed fields, ignores others | ✓ Pass |
| AC-5 | PATCH returns 403 for wrong coach | ✓ Pass (coach_id filter) |
| AC-6 | DELETE hard-deletes session | ✓ Pass |
| AC-7 | DELETE returns 403 for wrong coach | ✓ Pass (coach_id filter) |

## Files Modified

| File | Change |
|------|--------|
| `api.py` | Added name/notes/stroke_type params to /process; insert returns id; added PATCH + DELETE endpoints |
| Supabase sessions table | Added name TEXT, notes TEXT, is_starred BOOLEAN DEFAULT false, stroke_type TEXT |

## Decisions Made

- `session_id_saved` initialised to `None` before the `if athlete_id:` block — returned as null when no athlete linked
- PATCH allows only `{name, notes, is_starred}` — `stroke_type` is write-once at record time
- Legacy sessions with `null coach_id` cannot be patched/deleted (acceptable)

## Deferred

None.
