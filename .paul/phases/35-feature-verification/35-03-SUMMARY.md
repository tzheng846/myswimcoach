---
phase: 35-feature-verification
plan: 03
subsystem: docs
tags: [docs, reconciliation, codebase-audit, claude-md]
requires:
  - phase: 35-01
    provides: web verification findings
  - phase: 35-02
    provides: iOS verification findings + ratings UI
provides:
  - CLAUDE.md + CODEBASE-AUDIT.md reconciled to Phases 33–36 + iOS 35-02 reality
  - Feature Status Ledger (WORKING / DEFERRED / DRAFT) in CODEBASE-AUDIT.md
affects: []
tech-stack:
  added: []
  patterns: ["docs track live reality; one ledger answers what works/deferred/draft"]
key-files:
  created: []
  modified: [CLAUDE.md, CODEBASE-AUDIT.md]
key-decisions:
  - "Refreshed the audit (matrix + drift + ledger), not a full re-audit — per plan scope"
duration: ~45m
completed: 2026-06-18
---

# Phase 35 Plan 03: Doc Reconciliation Summary

**Made the orientation docs tell the truth after Phases 33–36 + the 35-02 iOS work, and
added one Feature Status Ledger so a cold reader sees what works / what's deferred / what's
draft at a glance. Docs-only — zero behavior change.**

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| AC-1 CLAUDE.md is true | ✅ PASS | coach.py "only app.py" claim corrected; `/coach/chat` + `/sessions/{id}/ratings` added to the endpoint list; ratings.py + drills.py + roster_metrics.py added to key-files; RATINGS-SPEC.md pointer; audit-date ref bumped |
| AC-2 CODEBASE-AUDIT reflects 33–36 + iOS | ✅ PASS | Provenance refresh note; §2 production modules added + coach.py/web/tests/ESP statuses fixed; §3 iOS ratings UI + Diagnostics/Video/PillarCards + iPhone-first; §4.2 + /coach/chat + /ratings rows, /reports flipped ✅; §5.1 + §4.5 + §8 deploy-drift marked RESOLVED |
| AC-3 one finished-vs-deferred ledger | ✅ PASS | Feature Status Ledger (14 rows) near the top of CODEBASE-AUDIT.md — WORKING / DEFERRED / DRAFT / DE-SCOPED / NOT-BUILT per surface |
| AC-4 no false comments; nothing over-written | ✅ PASS | Grep for the known-false claims across *.py/*.js → **0 hits** (staleness was doc-only); legal/marketing copy + decision log untouched; `git diff --stat` = CLAUDE.md + CODEBASE-AUDIT.md only |

## Accomplishments
- **CLAUDE.md** — surgical fixes (coach.py coupling, two new endpoints, three new key-files, spec pointer, audit date).
- **CODEBASE-AUDIT.md** — refreshed connection matrix + drift sections for Phases 33–36 + iOS 35-02; flipped the 2026-06-12 Railway/Vercel deploy-drift rows to RESOLVED (35-01 verified prod live); **added the Feature Status Ledger**.
- Confirmed via grep that no *source* comments carried the false claims — they were confined to the two docs.

## Verification
- `git diff --stat` → only `CLAUDE.md` + `CODEBASE-AUDIT.md` changed (docs-only; no code touched).
- Grep `only by app.py|live velocity graph|pre-Phase-24|supportsTablet|not yet deployed` across *.py/*.js → 0 hits.

## Deviations from Plan
None. Scope held to the two orientation docs + comment sweep (no full re-audit, as planned).

## Phase 35 — COMPLETE (transition)
3/3 plans shipped + closed:
- **35-01 (web)** ✅ — all web features WORKING; chat config gap (ANTHROPIC_API_KEY) user-fixed.
- **35-02 (iOS)** ✅ — ratings UI + iPad de-scope verified on device; 2 device bugs fixed; recording checks deferred.
- **35-03 (docs)** ✅ — orientation docs reconciled + Feature Status Ledger.

**Remaining (tracked deferrals, not blockers):**
- Post-resolder iOS device re-verify (4 recording checks + 2 fix re-verifies) — one build, no rebuild cost.
- Coach review of DRAFT breaststroke rating thresholds before customer-facing.
- iOS↔web parity gaps (AI chat + advanced per-cycle graphs) — candidate future "iOS parity" phase.

## Next Phase Readiness
Phase 35 closes the verification milestone goal. Open product threads (user-owned / future phases):
the post-resolder re-verify, the threshold coach review, the iOS parity phase, and 16-06 wavelet
segmentation tuning (flips `segmentation_reliable` → ratings become non-provisional).

---
*Phase: 35-feature-verification, Plan: 03*
*Completed: 2026-06-18*
