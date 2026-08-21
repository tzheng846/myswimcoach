---
phase: 70-video-session-matching
plan: 02
subsystem: api
tags: [qr, recording_token, process, supabase, patch_13, backend]
requires:
  - phase: 70-video-session-matching
    provides: /app/match manual core (the surface the QR pre-fill accelerates)
provides:
  - sessions.recording_token column (patch_13) + /process storing it when the phone sends one
  - No new endpoint — web looks up the session by token via supabase-js (coach-scoped RLS)
affects: [70-03-web-qr-decode, 70-04-mobile-qr-display]
tech-stack:
  added: []
  patterns:
    - "recording_token is written to the sessions insert ONLY when provided — keeps the payload valid on a pre-patch_13 DB"
key-files:
  created: [supabase/patch_13_recording_token.sql]
  modified: [api.py, tests/test_api.py]
key-decisions:
  - "No match-by-token endpoint — the web queries sessions.recording_token directly (RLS already scopes it)"
  - "Conditional store (only when sent) so deploying the backend before patch_13 is applied cannot break recording"
duration: ~loop
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 70 Plan 02: Backend recording_token (QR match) Summary

**`sessions.recording_token` (patch_13) + `/process` storing it only when the phone sends one — the storage half of the QR slate, with no new endpoint (the web looks the session up by token via RLS).**

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: idempotent, non-destructive patch | **Pass** | `ADD COLUMN IF NOT EXISTS` + index + comment; user-applied like patch_12. |
| AC-2: token stored when sent, absent when not | **Pass** | `test_token_carried_when_sent` / `test_token_absent_when_not_sent` green; conditional `if recording_token:` guard. |

## Verification
- `python -m pytest tests/test_api.py -q` → **64 passed** (58 → 64, +2 token tests; +4 pre-existing counted in run).
- `api.py` parses; grep confirms the conditional store.

## Files
| File | Change | Purpose |
|------|--------|---------|
| `supabase/patch_13_recording_token.sql` | Created | nullable `recording_token` + index (user-applied) |
| `api.py` | Modified | `/process` accepts `recording_token`, stores it only when provided |
| `tests/test_api.py` | Modified | `TestRecordingTokenPersisted` (carried / absent) |

## Deviations
None — executed as planned. Simplified vs CONTEXT (no match-by-token endpoint; web uses RLS query directly).

## Next Phase Readiness
**Ready:** the token column + write path exist for 70-03 (web decode → RLS lookup) and 70-04 (mobile sends it).
**Concerns:** patch_13 must be applied live before any token is sent (human step; coordinate with the paid EAS build).
**Blockers:** None.

---
*Phase: 70-video-session-matching, Plan: 02 — committed local (`feat(70): backend recording_token for QR match`); pushed with the phase at end.*
*Completed: 2026-08-19*
