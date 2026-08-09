---
phase: 58-video-ground-truth
plan: 05
subsystem: ui
tags: [react, nextjs, coach-portal, supabase-rls, session-list]

requires:
  - phase: 47-trial-annotation
    provides: session_annotations table + its team-scoped RLS policy (patch_07)
  - phase: 58-video-ground-truth (58-03)
    provides: the pageshow/focus revalidation pattern reused here
provides:
  - auto-generated session titles (display-only) so unnamed sessions are distinguishable
  - athlete name, weekday-or-date, and Annotated / Video / Quality indicators on each card
  - session-list revalidation on return
affects: [57-03 annotation queue (re-scoped by this), 53 attention-allocation, 16-06]

tech-stack:
  added: []
  patterns:
    - "Read session_annotations straight from supabase-js — patch_07's FOR ALL team-scoped policy
       means annotation state needs no API endpoint"
    - "Any derived 'warning' indicator must exclude the kick warning, which is set on every session"

key-files:
  created: []
  modified:
    - web/app/app/sessions/page.js
    - web/components/portal/SessionCard.js

key-decisions:
  - "Auto-name is display-only; sessions.name is never written, so all 19 are fixed with no backfill"
  - "Time in the title, weekday in the meta line — separates same-evening recordings without duplicating"
  - "Annotated chip reads session_annotations; its tooltip reads recomputed_from_annotation, because
     those are different states"
  - "Header bottom margin is conditional so a card with no chips keeps its previous spacing"

patterns-established:
  - "Extract the shipped helpers and run them, rather than eyeballing date/threshold logic"

duration: ~1 session (single sitting, 2026-08-07)
started: 2026-08-07
completed: 2026-08-07
---

# Phase 58 Plan 05: Session-Card Legibility

**Session cards now identify themselves — an auto-generated title carrying the recording time, the
athlete, a weekday, and prominent Annotated / Video / Quality indicators — so a 19-session
collection block stops rendering as nineteen rows reading "Aug 5, 2026". Two web files, no backend,
no schema.**

## Performance

| Metric | Value |
|--------|-------|
| Date | 2026-08-07 |
| Tasks | 2 auto + 1 checkpoint, all completed |
| Files modified | **2** |
| Backend suite | **237** — unchanged, proving no backend file was touched |
| Web build | exit 0 |
| Browser | `/app/sessions` 200 → /login, zero console errors |
| Checkpoint | Approved by user |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Usable title on every card | **Pass** | Extracted-function run: `freestyle → "Freestyle · 1:24 PM"`, `null/bogus → "Session · 1:24 PM"`. Typed names pass through undecorated. |
| AC-2: Athlete + weekday-or-date | **Pass** | 7-day boundary exact — 6.9 d → `"Sun"`, 7.1 d → `"08-01-26"`; zero-padding `"01-09-26"`. Unresolved athlete is omitted, not placeholdered. |
| AC-3: Annotated prominent and honest | **Pass** | Accent-styled chip from `session_annotations`; tooltip switches on `recomputed_from_annotation`. |
| AC-4: Video + quality visible | **Pass** | 🎥 from `video_path`. ⚠ verified against the kick trap — see below. |
| AC-5: List current after annotating | **Pass** | `pageshow`/`persisted` + `focus` refetch, same pattern as 58-03. |

## The verification that mattered

The plan flagged one trap: `metrics.py` sets `kick_metrics_reliable = False` on **every** session, so
a naive `warnings.length > 0` check would put ⚠ on every card and the indicator would carry no
information. The shipped `qualityIssue` was extracted and run:

```
kick warning ONLY -> must be null            null
kick + real -> the real one                  "Signal gap detected"
dropout 6.2%                                 "6.2% signal dropout"
dropout 3.0% -> null                         null
1 implausible cycle                          "1 implausible cycle"
2 implausible cycles                         "2 implausible cycles"
empty dq -> null                             null
undefined dq -> null                         null
```

Thresholds match `DataQualityCard`'s (`>5%` dropout, `>0` implausible), so the two surfaces cannot
disagree about whether a session had a problem.

## Accomplishments

- **Made the collection batch workable.** The list is the entry point to every annotation, and it
  previously could not distinguish one session from another.
- **Adjusted the user's date rule with evidence rather than following it into a known failure.**
  57-01's Supabase read established the 19 are a time block on one evening (19:50–20:59), not a
  date — plain day-of-week would have rendered all nineteen as "Wed". Time moved to the title and
  the weekday stayed in the meta line, satisfying the intent without the collision.
- **Confirmed no backend was needed.** patch_07 gave `session_annotations` a `FOR ALL`, team-scoped
  RLS policy, so annotation state is one key-only supabase-js query.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/app/app/sessions/page.js` | Modified | Select widened (`video_path`, `dq:metrics_json->data_quality`); `session_annotations` fetched in the same `Promise.all` as the sessions so the two cannot disagree; athlete-name Map reusing the existing roster query; `pageshow`/`focus` revalidation. |
| `web/components/portal/SessionCard.js` | Modified | `formatTime` / `formatWhen` / `qualityIssue` helpers; `Chip`; auto-title; athlete + weekday meta line; Annotated / Video / Quality chip row; conditional header margin. |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Auto-name is display-only | Fixes all 19 unnamed sessions with no backfill and no write against production data; a typed name simply takes over | `sessions.name` untouched; nothing to migrate |
| Time in title, weekday in meta | The two would be redundant on one line, and time is what separates a collection block | The user's stated rule survives for older sessions |
| Annotated chip ≠ recomputed | An annotation with <2 cycle boundaries saves but rewrites no metrics | Tooltip distinguishes them; conflating is how a coach concludes an annotation "did nothing" |
| Conditional header margin | A card with no chips must keep the spacing it had | No visual regression on unannotated, video-less, clean sessions |
| Kept Rate / Speed / Dist | Swapping Dist for duration was offered and declined | Stat row unchanged |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Cosmetic regression prevented |
| Scope additions | 0 | — |

### 1. Conditional header margin (auto-fixed)

Inserting the chip row between the header and the stat row would have left cards **without** chips
with a tighter gap than before. The header's bottom margin is now conditional on whether a chip row
follows, so unchipped cards are pixel-identical to their previous state.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Three failed attempts to write the extraction harness — `/tmp` resolving to `\tmp` on Windows, an env-var assignment not expanded within its own command's argument list, and `\\n` escaping through heredoc→python→JS | Used the scratchpad with a literal raw path, and built the harness as a list of lines with no backslash escapes |

## Next Phase Readiness

**Ready:**
- The annotation batch can now be worked from the list: which sessions exist, whose they are, when
  they were recorded, and which are already done.

**Recommendation on 57-03 (required by the plan):**

**Drop the separate queue page; re-scope 57-03 to two smaller pieces.** 57-03 existed because "a
timestamp-only list will be unusable" — that constraint is now gone. The sessions list already *is*
a queue: it is ordered newest-first, filterable by stroke and athlete, shows annotated state, and
revalidates on return. A second page duplicating it would have to be kept in sync with it forever.

What genuinely remains:
1. **Prev/next on the annotate page** — the real throughput win. Bouncing back to the list between
   each of 19 sessions is the remaining friction, and it is not addressed by anything shipped here.
2. **A "Not annotated" filter chip** beside the existing stroke chips — roughly ten lines, since
   the annotated Set is already in that component's state.

**Concerns:**
- The checkpoint was approved without itemised answers to the two questions the plan asked it to
  report: whether the 19 are *in practice* distinguishable, and whether ⚠ is informative or
  near-universal on real data. The mechanisms are proven by the extracted-function run; the
  real-data judgement is not recorded.
- `"Underwater Dolphin Kick · 8:24 PM"` truncates in a narrow card. Cosmetic; the short form
  (`UDK`) was offered and not requested.
- Times render in the browser's local timezone, unchanged from the previous card's behaviour.

**Blockers:** None.

---
*Phase: 58-video-ground-truth, Plan: 05*
*Completed: 2026-08-07*
