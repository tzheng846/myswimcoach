---
phase: 70-video-session-matching
plan: 03
subsystem: ui
tags: [qr, jsqr, match, next.js, supabase, web]
requires:
  - phase: 70-video-session-matching
    provides: recording_token column (70-02) + /app/match manual core (70-01)
provides:
  - Client-side QR decode of staged clips (jsQR) → RLS lookup by recording_token → pre-filled, overridable match with a "Matched by QR" badge
affects: [70-04-mobile-qr-display]
tech-stack:
  added: [jsqr@^1.4.0]
  patterns:
    - "QR is an accelerator layered on the manual flow — any failure (no QR / unknown token / column absent) silently falls back to manual"
key-files:
  created: []
  modified: [web/app/app/match/page.js, web/package.json]
key-decisions:
  - "Token→session lookup is a supabase-js RLS read (no API endpoint); wrapped so a pre-patch_13 DB returns null, not an error"
  - "Pre-fill only when the coach hasn't already picked; the selection stays overridable (D4)"
duration: ~loop
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 70 Plan 03: Web QR decode + match pre-fill Summary

**On `/app/match`, jsQR scans each staged clip's early frames for a token, looks up the session by `recording_token` (supabase RLS), and pre-selects that clip's picker with a "Matched by QR" badge — degrading silently to manual on any miss.**

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: slated clip pre-fills its match, overridable | **Build-verified / UAT-pending** | `decodeQrToken` (6 early frames, jsQR) → `lookupSessionByToken` → `patchClip(sessionId: c.sessionId \|\| s.id)`; badge shown; select stays editable. Needs a real slated clip. |
| AC-2: clean degradation (no QR / unknown / no patch_13) | **Pass** | Decode + lookup both resolve null on failure; `error` from the RLS query returns null (unknown column pre-patch). Build green; manual path unchanged. |

## Verification
- `npm --prefix web run build` → exit 0, `/app/match` prerendered (client module imports jsQR cleanly). Interactive QR decode needs a real QR-bearing clip → UAT.

## Files
| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/match/page.js` | Modified | `decodeQrToken` + `seekTo` + `lookupSessionByToken`; QR fields on staged clips; pre-fill + badge; options include the matched session |
| `web/package.json` (+lock) | Modified | jsqr@^1.4.0 |

## Decisions
| Decision | Rationale | Impact |
|----------|-----------|--------|
| supabase RLS lookup, no endpoint | sessions is already coach-scoped readable | No api.py change |
| Silent fallback everywhere | QR is an accelerator (D4) | Un-slated clips behave exactly like 70-01 |

## Deviations
None.

## Next Phase Readiness
**Ready:** web decode consumes tokens; 70-04 (mobile) produces them (display QR + send to /process).
**Concerns:** end-to-end QR match is only exercisable once the mobile slate exists AND a camera films it (paid build + camera UAT). Per-clip decode seeks ~6 frames — acceptable client-side; note if a large batch feels slow.
**Blockers:** None (build-buildable; value gated on 70-04 + patch_13).

---
*Phase: 70-video-session-matching, Plan: 03 — committed local (`feat(70): web QR decode + match pre-fill`); pushed with the phase at end.*
*Completed: 2026-08-19*
