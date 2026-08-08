---
phase: 57-annotation-workflow
plan: 02
subsystem: ui
tags: [react, recharts, nextjs, annotation, coach-portal]

requires:
  - phase: 57-annotation-workflow (57-01)
    provides: marks_per_cycle on GET, cycles_derived on PUT, the 422 out-of-window error shape
  - phase: 47-trial-annotation
    provides: the annotate page, AnnotationChart/AnnotationEditor split, VideoPane
provides:
  - blank-start annotation editor (no segmenter seed applied)
  - swim-window-fitted chart with full-trace toggle and shaded phase bands
  - drag-to-move, arrow-key nudge, undo stack
  - phase rows as intervals with metric-impact tags
  - live marks→cycles readout verified equivalent to the Python
  - discard-saved-annotation wiring
affects: [57-03 annotation queue, 53 attention-allocation, 16-06 segmenter tuning]

tech-stack:
  added: []
  patterns:
    - "Fit a recharts view by SLICING the data, not by setting an XAxis domain — a <Brush> in the
       same chart also controls the domain and the two fight"
    - "Cross-language logic parity proven by extracting the SHIPPED function and diffing its output
       against the reference implementation, rather than re-reading both by eye"

key-files:
  created: []
  modified:
    - web/app/app/annotate/[id]/page.js
    - web/components/portal/AnnotationChart.js
    - web/components/portal/AnnotationEditor.js

key-decisions:
  - "Fit range is [0, finish+margin] — lower bound never stroke_start, the front is reaction time"
  - "Undo stack in a ref, not state — state would re-render the chart on every one of ~500 clicks"
  - "A mousedown that hits an existing mark suppresses the following click entirely"
  - "Deployed before the checkpoint at user direction, against recommendation"

patterns-established:
  - "Client-side mirrors of a Python contract get an equivalence test, not a careful reading"

duration: ~1 session (single sitting, 2026-08-05)
started: 2026-08-05
completed: 2026-08-05
---

# Phase 57 Plan 02: Annotate Page v2 Summary

**The annotate page now starts blank, fits the view to the annotated swim while keeping the
reaction-time region on screen, states each phase as an interval and whether it moves a number, and
shows live how many cycles the marks will actually produce — verified equivalent to the Python that
will build them.**

## Performance

| Metric | Value |
|--------|-------|
| Date | 2026-08-05 |
| Tasks | 3 auto + 1 checkpoint, all completed |
| Files modified | 3 (web only) |
| Build | `npm run build` exit 0, 18 routes |
| Backend suite | 236 (unchanged — proves no backend file was touched) |
| Checkpoint | Approved by user on the deployed portal |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Editor starts blank | **Pass** | Code: load path is `annRes.annotation` only; `seed` still read from the response but never applied. Confirmed at checkpoint. |
| AC-2: Dead tail trimmed, front kept | **Pass** | `viewRange = [0, finish + max(1, 0.05×finish)]`; null (full trace) when `finish_s` is unset. Confirmed at checkpoint. |
| AC-3: Phases read as intervals with impact stated | **Pass** | `drivesMetrics` on `PHASE_META`; rows render span + duration + "record only" tag; Dive carries the lower-bound caption. Confirmed at checkpoint. |
| AC-4: Marks correctable without hunting | **Pass** | Drag via chart hit-test, arrow/shift-arrow nudge, Backspace delete, Ctrl+Z. Confirmed at checkpoint. |
| AC-5: Mark→cycle relationship visible | **Pass** | **Machine-verified** — see Verification Results. Also confirmed at checkpoint. |
| AC-6: Out-of-window marks prevented | **Pass** | Client guard in `handleChartClick` mirrors the server rule; server 422 strings still render. Confirmed at checkpoint. |
| AC-7: Saved annotation discardable | **Pass** | `DELETE /annotations` wired with confirm step; reports `metrics_restored`. Confirmed at checkpoint. |

## Accomplishments

- **Removed the circularity from the ground truth.** The editor no longer preloads segmenter output,
  so the marks that will be used to *evaluate* the segmenter are no longer anchored by it.
- **Made non-overlap visible instead of merely enforced.** `ReferenceArea` bands between consecutive
  markers tile the axis with no gaps and no overlaps by construction — the invariant
  `validate_annotation` has always held, now drawn.
- **Proved the client readout cannot lie.** The JS cycle derivation was extracted from the shipped
  file and diffed against `annotation_to_overrides` over 10 cases — exact match, including the two
  that were most likely to drift.
- **Made ~500 marks survivable**: undo, drag, keyboard nudge, and a fitted view that roughly doubles
  horizontal resolution on a trace with a 45% dead tail.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/portal/AnnotationChart.js` | Modified | `viewRange` slicing, `ReferenceArea` phase bands, drag hit-test + `onMarkSelect`, selected-mark highlight, direct-DOM cursor affordance. `PHASE_META` gained `drivesMetrics`. |
| `web/components/portal/AnnotationEditor.js` | Modified | `deriveCycles` (Python mirror), interval rows with spans/durations/impact tags, Dive lower-bound caption, view toggle, Undo, Discard. "Reset to auto" removed. |
| `web/app/app/annotate/[id]/page.js` | Modified | Blank start, undo stack in a ref, keyboard handling, drag commit + re-sort, out-of-window guard, discard, `cycles_derived` in the saved message. |

## Verification Results

**Cross-language equivalence (the plan's flagged risk).** The client readout must agree with what
the server will build; a drift would make it lie. Rather than reading both implementations, the
shipped `deriveCycles` was extracted into an `.mjs` and run in node against the same 10 cases passed
through `annotations.annotation_to_overrides`:

```
python: [2, 4, 1, 4, 0, 0, 0, 3, 1, 3]
js    : [2, 4, 1, 4, 0, 0, 0, 3, 1, 3]   MATCH
```

Cases included k=2 with `finish` beyond the last mark (1 cycle — *not* appended), its k=1 twin
(4 cycles — appended), empty marks, and a pair 0.01 s apart that both sides drop under the
2-sample span filter.

**Build + runtime.** `npm run build` exit 0. Dev server served `/app/annotate/[id]` 200 then
redirected to `/login` (auth guard intact); zero console errors, zero compile errors.

**Boundaries.** `git status` showed exactly the three planned web files. `pytest tests/ -q` still
236 — no backend file touched.

**Skill audit:** no `.paul/SPECIAL-FLOWS.md` in this repo — not applicable.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Fit range `[0, finish+margin]`, never starting at `stroke_start` | The leading region is the reaction-time measurement (D4). Trimming the front would delete the one thing the user explicitly asked to keep. | Blank start means no `finish_s` initially → the view opens full-trace and collapses when Finish is placed. |
| Undo stack in a ref, depth counter in state | ~40 marks × 19 sessions; snapshotting into state would re-render the 2000-point chart on every click. | Undo does not participate in React reconciliation. |
| Fit by slicing data, not `XAxis domain` | The `<Brush>` in the same chart also controls the domain; setting both makes them fight. | Also re-spreads `MAX_POINTS` over the shorter span — the actual precision gain. |
| Deploy before the checkpoint | User direction, after the recommendation to verify locally first was stated and declined. | Prod briefly carried an unexercised page. Checkpoint then passed, so no harm realised. |
| Hold the blog back from "deploy everything" | Committing `web/app/blog/` + `web/lib/blog.js` + the Footer/Nav links publishes founder-journal posts to the public marketing site — outward-facing publication, not internal tooling, and not part of anything requested this session. | Still uncommitted. Needs an explicit yes. |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 2 | Both necessary; neither changes plan scope |
| Process | 1 | Deploy ordering, user-directed |
| Scope additions | 0 | — |

### 1. Click-after-mouseup conflict (auto-fixed)

- **Found during:** Task 3 wiring, affecting Task 1.
- **Issue:** The plan said selection is "set by clicking an existing mark." But recharts fires
  `onClick` *after* `mouseup`, so a select-click would also place a **new** mark on top of the one
  being targeted — and every drag would end by placing a stray mark.
- **Fix:** `suppressClickRef` is set on any `mousedown` that hits a mark (not only on movement), so
  a press on an existing mark selects or drags it and never places. Renamed from the originally
  planned `didDragRef`, which only covered the moved case.

### 2. Mark re-sort after drag (auto-fixed)

- **Issue:** Dragging a mark past its neighbour leaves `stroke_marks_s` unsorted, which
  `validate_annotation` rejects as "out of order."
- **Fix:** A window-level `mouseup` listener re-sorts once per gesture. Snapshotting for undo also
  happens once per gesture rather than per mouse event, which would otherwise flood the stack.

### 3. Deployed before the checkpoint (process, user-directed)

Plan ordering implied verify-then-ship. The user directed pushing 57-01 first (necessary — the dev
server targets the production API, so a pre-57-01 backend would have made a freestyle session read
"18 marks → 17 cycles" and verified the exact bug this phase prevents), then directed committing and
deploying 57-02 before the checkpoint ran. Recommendation to verify locally was given and declined.
Recorded, not re-litigated. Checkpoint subsequently passed.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| First 57-02 commit message mangled — PowerShell here-string (`@'…'@`) used in the Bash tool left a stray `@` as the subject line | Amended with a proper heredoc before pushing; history is clean (`16c1d92`) |
| No unauthenticated way to confirm the Railway deploy had landed | Used checkpoint step 5 as the deploy check — a freestyle readout of N/2 proves `marks_per_cycle` arrived |

## Next Phase Readiness

**Ready:**
- 57-03 (queue + prev/next) can build on a page that no longer needs per-session hand-holding.
- Four constraints for the queue were established by the Supabase read at 57-01's close: the 19 are
  a **time block (19:50:50–20:59:25), not a date** — a date filter pulls 22; **no video** on any of
  them; **no session has a name**, so a timestamp-only list will be unusable; and the 20:24
  freestyle needs discarding before re-annotation (now possible from the page).

**Concerns:**
- **R1 is still unanswered.** The plan asked this summary to record whether ~40 arm-entry marks are
  genuinely placeable from the velocity trace alone. The checkpoint was approved without a report on
  that specific point, so **it remains unknown** — it is not being recorded as settled. Annotating
  one real freestyle session end to end is what answers it, and 57-03's queue design should not
  assume the answer.
- The blog remains uncommitted (see Decisions).

**Blockers:** None.

---
*Phase: 57-annotation-workflow, Plan: 02*
*Completed: 2026-08-05*
