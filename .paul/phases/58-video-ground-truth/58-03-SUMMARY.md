---
phase: 58-video-ground-truth
plan: 03
subsystem: ui
tags: [react, nextjs, bfcache, coach-portal, ratings, stroke-gating]

requires:
  - phase: 54-gate-removal
    provides: ratings.py breaststroke-threshold fallback + dropped provisional gate (and the false
              "web has no stroke gate" finding this plan corrects)
  - phase: 47-trial-annotation
    provides: recomputed_from_annotation flag written by PUT /annotations
provides:
  - full analytics for every stroke on the web report card
  - report-card revalidation on pageshow/persisted + window focus (bfcache-safe)
  - visible recompute provenance marker
affects: [53 attention-allocation, 16-06 segmenter tuning, any future stroke-threshold work]

tech-stack:
  added: []
  patterns:
    - "Revalidate client pages on pageshow/persisted + focus, not mount alone — a bfcache restore
       skips mount entirely and router.refresh() cannot reach it"
    - "A refetch must not reassign user-owned editable state, or an alt-tab silently discards edits"

key-files:
  created: []
  modified:
    - web/app/app/sessions/[id]/page.js

key-decisions:
  - "Gate set to true with the old line kept in a comment; all 5 usage sites and the dead branch kept"
  - "No replacement caveat added for non-breaststroke bands — reported to the user instead"
  - "load() takes resetEditable, true only on first load, so revalidation cannot clobber notes"
  - "Provenance marker placed in page.js under the summary, not in DataQualityCard — keeps the
     plan to exactly one file and puts it where the metrics it qualifies actually are"

patterns-established:
  - "When a plan says 'verify X still holds', run it — the answer here was no, and assuming would
     have shipped an unvalidated metric surface with its only warning silently gone"

duration: ~1 session (single sitting, 2026-08-07)
started: 2026-08-07
completed: 2026-08-07
---

# Phase 58 Plan 03: Report-Card Visibility

**Every stroke now shows full analytics on the web report card, the page can no longer serve stale
data by any return route including bfcache, and metrics recomputed from a hand annotation say so —
one file, no backend deploy. The plan's one verification requirement came back negative: the
"Provisional" caveat no longer fires for any stroke.**

## Performance

| Metric | Value |
|--------|-------|
| Date | 2026-08-07 |
| Tasks | 2 auto + 1 checkpoint, all completed |
| Files modified | **1** |
| Backend suite | **237** — unchanged, proving no backend file was touched |
| Web build | exit 0 |
| Browser | route 200 → /login, zero console errors |
| Checkpoint | Approved by user |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Every stroke shows full analytics | **Pass, with a caveat failure** | Gate → `true`; 5 usage sites intact. ⚠ The AC also required the "Provisional" banner to appear — **it does not, for any stroke.** See below. Checkpoint approved with that known. |
| AC-2: Never stale by any route back | **Pass** | `load()` fired from mount, `pageshow`/`persisted`, and window `focus`, with a sequence guard. Checkpoint approved. |
| AC-3: Recompute provenance visible | **Pass** | `metrics.data_quality?.recomputed_from_annotation` renders a marker + "Review marks ›" link; absent when the flag is absent. Checkpoint approved. |

## The verification that came back negative

The plan required checking, not assuming, whether `PillarCards`' *"Provisional — stroke segmentation
is still being validated"* banner still fires. **It does not — for any stroke:**

```
breaststroke   any_provisional=False   per-pillar=[False, False, False, False]
freestyle      any_provisional=False   per-pillar=[False, False, False, False]
backstroke     any_provisional=False   per-pillar=[False, False, False, False]
butterfly      any_provisional=False   per-pillar=[False, False, False, False]
```

Mechanism: `ratings.py:229` always falls back to the breaststroke table, so `thr_table` is never
`None`; `provisional` at `:184` is therefore true only when a pillar's own metric lacks a threshold
entry, which is stroke-independent. Phase 54-01 dropped the `seg_reliable` condition and this was
the collateral — unnoticed at the time because the *web* gate was believed not to exist, so nobody
looked at what the web would show once it was lifted.

**Live consequence:** a freestyle report card now shows pillar bands, scores and verdicts with
nothing on screen indicating they are breaststroke-derived and unvalidated — over segmentation
16-04 measured at 3/8 sessions within ±5 SPM. Freestyle numbers look exactly as authoritative as
breaststroke's.

No replacement caption was added. The plan forbade doing so silently, and whether those bands should
exist at all is Phase 53's question. **The user was shown this at the checkpoint and approved.** It
is an accepted, recorded consequence — not an oversight. It remains open.

## Accomplishments

- **Closed the annotation pipeline's last mile.** Phases 47/57/58-02 built a tool producing
  corrected metrics; until now those corrections were invisible on any non-breaststroke session and
  unlabelled on every session.
- **Corrected a false entry in the project record.** See below.
- **Removed the stale-read class rather than a stale-read instance.** `pageshow`/`persisted` is the
  case nothing React-side can reach.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/sessions/[id]/page.js` | Modified | Gate → `true` (restorable, dead branch kept); mount-only fetch extracted into `load()` with a sequence guard and `resetEditable`; `pageshow`/`focus` revalidation; provenance marker under the session summary. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| No replacement caveat for borrowed bands | Plan boundary; and it is Phase 53's call, not this plan's | Freestyle bands currently ship with no on-screen warning. Recorded as open. |
| `load({resetEditable})` | Reassigning `sessionName`/`notes`/`isStarred` on every focus would silently discard notes typed before an alt-tab | Revalidation touches only `data` and `athlete` |
| Sequence guard (`reqRef`) | `load()` now has three triggers; a slow earlier response must not overwrite a newer one | Cheaper and clearer than an AbortController here |
| Provenance in `page.js`, not `DataQualityCard` | Keeps the plan to exactly one file, and puts the marker beside the metrics it qualifies rather than below the chart | `DataQualityCard` untouched |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Prevented a real regression |
| Scope removals | 1 | Pre-apply, user-directed |

### 1. `resetEditable` guard added (auto-fixed)

- **Found during:** Task 2, while extracting the effect.
- **Issue:** the original effect also assigns `sessionName`, `notes` and `isStarred`. Firing it on
  every window focus would mean: type notes → alt-tab → return → unsaved notes silently replaced by
  the stored value. The plan did not anticipate this.
- **Fix:** `load({ resetEditable })`, true only on the initial load.

### 2. Diagnosis task removed before apply (scope removal, user-directed)

The plan originally opened with a bisect for the reported staleness. The user then observed
annotations updating correctly. Since **58-02 touched nothing on the report-card path**, that could
not be credited to a code change — so rather than chase a bug that was not presenting, the user
chose confirm-and-harden. This also dropped the `api.py` and annotate-page edits, which is what
took the plan to one file, no backend deploy, and `depends_on []`.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Bash tool cwd drifting between repo root and `web/` | Absolute paths |

## Next Phase Readiness

**Ready:**
- Freestyle sessions are now fully inspectable on the web, which is what Phase 53's Track A4 and
  16-06 need in order to judge annotation results.

**Concerns:**
- ⚠ **Borrowed thresholds now display with no caveat on any stroke.** Accepted by the user, but
  live and unmarked. Phase 53 owns the decision.
- ⚠ **Whether the original staleness was ever real is still unknown.** The Back-button observation
  was not reported back. The `pageshow`/`focus` refetch is hardening against an unconfirmed cause —
  it should not be described as a diagnosed bug fix.
- ⚠ **Phase 54's record is wrong and needs correcting in ROADMAP**: it states the web had no stroke
  gate. It did, at `sessions/[id]/page.js:99`, since Phase 23. How it survived: both the web and
  mobile copies use the identifier `isAnalyticsReady`, so a grep would have found it — the miss was
  in the reading, not the search.

**Blockers:** None.

---
*Phase: 58-video-ground-truth, Plan: 03*
*Completed: 2026-08-07*
