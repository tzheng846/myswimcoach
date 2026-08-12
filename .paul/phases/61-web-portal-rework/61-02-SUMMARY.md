---
phase: 61-web-portal-rework
plan: 02
subsystem: ui
tags: [nextjs, react, recharts, tailwind, supabase, coach-portal]

requires:
  - phase: 61-01
    provides: removal of the steady/ramp_up split — the semantics AC-2's caption logic keys on
  - phase: 60-01
    provides: the mobile 4-panel layout, dropoutWarning helper and cv_isi banner this mirrors
provides:
  - CycleCharts at 4 panels with a vintage-aware caption and unit passthrough
  - web/lib/dropoutWarning.js — the single surviving data-quality signal
  - Time-to-Distance start provenance + Annotate link
  - prev/next navigation across an athlete's sessions
  - D5c fulfilled — mobile's stale CycleCharts comment corrected
affects: [61-03 video route, 61-04 compare redesign, 53 attention allocation]

tech-stack:
  added: []
  patterns:
    - "Detect session vintage from the DATA (`'phase' in cycle`), never from dates"
    - "Never gate display on `warnings.length` — two api.py warnings fire on every session"

key-files:
  created: [web/lib/dropoutWarning.js]
  modified: [web/app/app/sessions/[id]/page.js, web/components/portal/CycleCharts.js, web/components/portal/MetricGrid.js, web/components/portal/SessionCard.js, ../swimnetics-mobile/src/components/CycleCharts.js]
  deleted: [web/components/portal/CycleTable.js, web/components/portal/DataQualityCard.js]

key-decisions:
  - "Vintage-aware caption: legacy sessions keep the caveat, new ones drop it"
  - "SessionCard segmentation-warning filter included as a flagged scope addition"
  - "Prettier reverted — not a repo convention, it produced 50 lines of unrelated churn"

patterns-established:
  - "Sibling-session fetch lives inside load() to inherit its reqRef sequence guard"

duration: ~35min (approximate — no per-task timestamps captured)
started: 2026-08-11
completed: 2026-08-11
---

# 61-02 SUMMARY — Report card rework (D3, D4, D7, D12 + D5c)

**Three of the user's five original asks are now on screen: the per-cycle table is four charts, the
Data Quality card is one dropout strip, and Time-to-Distance says where its start came from.**

## Performance

| Metric | Value |
|---|---|
| Tasks | 3 auto + 1 checkpoint, all completed |
| Web files | 4 modified, 1 created, 2 deleted |
| Mobile files | 1 (comments + one display string) |
| Python files | **0** — suite held at 274 |
| Build | `npm run build` clean at every task boundary |

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 four panels, no table | **Pass (visual, user-approved)** | `CycleTable.js` deleted; no live references remain |
| AC-2 caption true for both vintages | **Pass (mechanism) / partly unverifiable (visual)** | Vintage predicate validated against the live DB: **54 legacy / 0 new / 8 no-cycles**. The *new* branch cannot be seen until 61-01 deploys — see Concerns |
| AC-3 one honest data-quality signal | **Pass** | `DataQualityCard.js` deleted; `dropoutWarning` node-verified 10/10 incl. NaN, string, null, boundary; zero live `warnings.length` gates |
| AC-4 Efficiency banded not blanked | **Pass (visual, user-approved)** | `MetricGrid` ternary → `&&`, diff 8/6 |
| AC-5 start provenance + Annotate link | **Pass (visual, user-approved)** | Both branches implemented off the existing `recomputed_from_annotation` flag |
| AC-6 prev/next across one athlete | **Pass (visual, user-approved)** — ⚠ **one required observation NOT obtained** | See Deviations #4 |
| AC-7 clean build + mobile comment | **Pass** | Build compiled; mobile diff is 1 file |

## What I verified myself, and what I could not

**Verified without a login:** `npm run build` clean; `/app/sessions/[id]` returns 200 with no
compile or console errors; `pytest` 274 (Python untouched); no live references to the deleted
components or to `warnings.length`; `dropoutWarning` 10/10 in node; the AC-2 vintage predicate run
against all 62 live sessions.

**Could NOT verify:** every visual criterion. The coach portal is behind Supabase auth and signing
in requires entering credentials, which is out of bounds for me. **AC-1, AC-4, AC-5 and AC-6 rest
on the user's approval, not on itemized observations I made.** Recorded plainly because Phase 60
was flagged for exactly this pattern.

## Deviations

| # | Type | Impact |
|---|---|---|
| 1 | Self-inflicted, caught and reverted | None |
| 2 | Self-inflicted, caught before damage | None |
| 3 | Boundary too narrow | Minor, intended by D5c |
| 4 | Required observation not obtained | **Carries forward** |
| 5 | Flagged scope addition | Approved implicitly |

**1. Prettier churn introduced and reverted.** I ran `npx prettier` on `MetricGrid.js`, which
reformatted the whole file — 55 insertions / 50 deletions for a ~10-line change. Prettier is **not
a repo convention** (no config, not a dependency), so this was unrelated churn against the
"don't reformat adjacent code" rule. Reverted with `git checkout` and redone by hand: final diff
**8 insertions / 6 deletions**.

**2. `rm` executed from the wrong working directory.** The Bash tool's cwd persisted as `web/`
after the build step, so `rm web/components/portal/DataQualityCard.js` resolved to
`web/web/...` and failed. Nothing was wrongly deleted; absolute paths used thereafter.

**3. The mobile change is comments PLUS one user-visible string.** The plan's boundary said
"COMMENT-ONLY", but the only non-comment line changed is the footnote — which is exactly what
CONTEXT.md's D5c named (line 139). The boundary wording was mine and too narrow; D5c always
intended the footnote. No logic changed. ⚠ The corrected footnote does not reach users until the
next EAS build.

**4. ⚠ AC-6's required observation was NOT obtained.** The plan's output section demanded
recording "whether view/unit survive prev/next navigation (observed, not assumed)". The checkpoint
asked for it; the reply was "approved" without the answer. **It remains unknown and is not
recorded here as a guess.** It is cheap to settle: open a session, switch to Advanced + yd, press
the arrow, see whether both stick.

**5. `SessionCard` segmentation-warning filter — flagged scope addition.** Beyond the four
decisions, and it touches the sessions *list* rather than the report card. Included because
`qualityIssue` filtered the kick warning but not the segmentation one, and
`segmentation_reliable` is hardcoded false — so the ⚠ chip appeared on essentially every card.
Deleting `DataQualityCard` while leaving its surviving sibling broken would have been incoherent.
Flagged at plan time and at the checkpoint; not objected to.

## Files

| File | Change | Purpose |
|---|---|---|
| `web/components/portal/CycleCharts.js` | Modified | 2 → 4 panels, captions, unit passthrough, vintage-aware footnote |
| `web/components/portal/CycleTable.js` | **Deleted** | ⚠ Impulse and Trough leave the web with it — intended, not to be reinstated |
| `web/components/portal/DataQualityCard.js` | **Deleted** | Replaced by one dropout strip |
| `web/lib/dropoutWarning.js` | **Created** | Mirrors the mobile helper incl. its documented trap |
| `web/components/portal/MetricGrid.js` | Modified | `cv_isi` blackout → banner |
| `web/components/portal/SessionCard.js` | Modified | Comment repointed; segmentation warning filtered |
| `web/app/app/sessions/[id]/page.js` | Modified | Wiring, dropout strip, start provenance, prev/next |
| `../swimnetics-mobile/src/components/CycleCharts.js` | Modified | D5c — comments + footnote |

Skill audit: no `.paul/SPECIAL-FLOWS.md` — step skipped.

## Next phase readiness

**Ready**
- 61-03 (video route + 58-04) and 61-04 (Compare) are unblocked. Neither touches the files here.
- `web/lib/dropoutWarning.js` is available if Compare wants the same signal.

**Concerns**
- ⚠ **AC-2's "new" branch is unobservable until 61-01 deploys to Railway.** Every stored session
  reads "legacy" today, correctly. Until then the caption is provably right in one direction only.
- ⚠ **Nothing from 61-01 or 61-02 is committed or deployed.** The web changes are Vercel-bound and
  61-01's are Railway-bound; the two must land together or the portal will render new charts over
  old metrics.
- ⚠ AC-6's view/unit-persistence question is open (Deviation 4).
- ⚠ The mobile footnote fix needs an EAS build to reach a device.

**Blockers:** None for 61-03 or 61-04.

---
*Phase: 61-web-portal-rework, Plan: 02*
*Completed: 2026-08-11*
