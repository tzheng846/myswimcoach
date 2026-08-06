---
phase: 25-codebase-audit
plan: 01
subsystem: infra
tags: [audit, documentation, fastapi, supabase, ble, esp32, nextjs, gitignore]

requires:
  - phase: 23-website
    provides: web/ portal whose contracts were cross-referenced
  - phase: 24-parent-reports
    provides: /reports endpoint + reports table whose deploy drift was probed
provides:
  - CODEBASE-AUDIT.md — verified cross-system map (connection matrix, folder maps, findings §5.1–5.7)
  - Refreshed AI-context files in both repos (CLAUDE.md ×2, AGENTS.md ×2)
  - Live confirmation Railway runs pre-Phase-24 api.py
  - Discovery: .gitignore excludes production files from git in BOTH repos
affects: [any future phase — audit is the orientation doc; consider-issues routing of §5 findings]

tech-stack:
  added: []
  patterns: ["read-only live probing to detect deploy drift (compare 404 body shapes)"]

key-files:
  created: [CODEBASE-AUDIT.md]
  modified: [CLAUDE.md, web/AGENTS.md, ../swimnetics-mobile/CLAUDE.md, ../swimnetics-mobile/AGENTS.md]

key-decisions:
  - "Documentation-only: all findings recorded in audit §5, none fixed"
  - "Live probes strictly GET; .env values never read (key names only)"

patterns-established:
  - "CODEBASE-AUDIT.md is the cold-start orientation doc; STATE.md stays the decision log"

duration: ~45min
started: 2026-06-12T08:50:00Z
completed: 2026-06-12T09:35:00Z
---

# Phase 25 Plan 01: Codebase Audit Summary

**Full-surface audit shipped: CODEBASE-AUDIT.md with an evidence-backed connection
matrix across firmware/iOS/backend/Supabase/web, 7 findings (2 critical), and surgical
refreshes of all four AI-context files — pytest 30/30, web build clean, Railway drift
confirmed live.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Tasks | 3 of 3 completed |
| Files created | 1 (CODEBASE-AUDIT.md) |
| Files modified | 4 (CLAUDE.md, web/AGENTS.md, mobile CLAUDE.md + AGENTS.md) |
| Production code modified | 0 (by design) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Cross-system contracts verified | ✅ Pass | Matrix in audit §4 — BLE protocol, endpoints↔callers, schema columns, constants, URLs; every row rated with file:line evidence |
| AC-2: Tests and builds run | ✅ Pass | pytest 30/30 (7.9 s); `npm run build` clean (Next.js 16.2.9, 10 routes) — outputs in audit §4.5 |
| AC-3: Live deploy drift detected | ✅ Pass | /health 200; /reports/<dummy> returns generic `Not Found` (≠ local `Report not found`) → route absent on Railway |
| AC-4: CODEBASE-AUDIT.md complete | ✅ Pass | All required sections, zero placeholders |
| AC-5: AI-context files refreshed surgically | ✅ Pass | Factual corrections only; each edit traceable to a Task 1 finding |

## Accomplishments

- **CODEBASE-AUDIT.md** at repo root: system diagram, annotated folder maps (both
  repos, every top-level item tagged production/legacy/experimental), connection
  matrix (§4), findings (§5), working/unverified/deploy-state (§6–8), cold-start
  guide (§9).
- **Critical finding #1 (confirmed live):** Railway runs pre-Phase-24 api.py — parent
  report links 404 in production until api.py is pushed (§5.1).
- **Critical finding #2 (new):** `.gitignore` excludes production files from version
  control in both repos — ESP_32_V5 firmware, tests/, supabase patch_03, all *.md in
  myswimcoach; most of `src/` untracked in swimnetics-mobile (§5.3). Verified via
  `git ls-files` + `git check-ignore`.
- **Schema drift documented (§5.2):** committed supabase SQL cannot rebuild the live
  DB — Phase 12/14/15 migrations were SQL-editor-only.
- All four AI-context files corrected (stale wheel-constant claim, wrong PATCH fields,
  pre-buffer-and-dump BLE protocol docs, missing endpoint/folder inventory).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `CODEBASE-AUDIT.md` | Created | The audit deliverable |
| `CLAUDE.md` | Modified | 6 factual fixes: audit pointer, web/reports in system map, key-files rows, wheel-constant claim, full endpoint list (PATCH fields, DELETE storage-orphan), deps line |
| `web/AGENTS.md` | Modified | Added project-context block (data-flow + audit pointer) |
| `../swimnetics-mobile/CLAUDE.md` | Modified | Buffer-and-dump protocol, BleContext/DevicesScreen in structure, retrieval state machine, live-graph removal, firmware_version gap |
| `../swimnetics-mobile/AGENTS.md` | Modified | Locked-protocol block updated to fw 1.1.0 spec; expo-secure-store added to approved libs |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Probe deploy drift by comparing 404 body shapes | Generic `{"detail":"Not Found"}` vs route-specific `"Report not found"` distinguishes missing route from missing row, unauthenticated | Reusable read-only drift check |
| Audit findings NOT auto-fixed | Plan boundary (documentation-only); each §5 row is a consider-issues candidate | Clean separation of audit vs remediation |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 2 | Both documentation additions within audit intent |
| Auto-fixed | 0 | — |
| Deferred | 7 | Audit §5 findings, for /paul:consider-issues |

**1. §5.3 git-coverage finding** — discovered during Task 3 verification (`git status`
came back impossibly clean). Investigated via `check-ignore`/`ls-files`, added as a new
critical finding + folder-map annotations + memory note. Not in the planned contract
list but squarely within "make sure it's well connected."

**2. DELETE-orphans-CSV finding (§5.7)** — root CLAUDE.md claimed `DELETE /sessions`
removes the raw CSV from storage; api.py only deletes the row. Found while fixing the
endpoint list; documented in audit + corrected in CLAUDE.md.

## Issues Encountered

None — no task failures, no blocked verifications.

## Next Phase Readiness

**Ready:** Future sessions orient from CODEBASE-AUDIT.md; AI-context files now truthful.

**Concerns (the §5 findings, user-owned or routable):**
- Push api.py to Railway (parent links broken in prod) — already on user follow-ups
- Fix .gitignore / force-add + commit in both repos (single-machine loss risk)
- Commit live Supabase schema (dump or backfilled patches)
- Optional wiring: firmware_version pass-through, export endpoint (use or remove),
  billing UI, raw-CSV deletion on session delete

**Blockers:** None.

---
*Phase: 25-codebase-audit, Plan: 01*
*Completed: 2026-06-12*
