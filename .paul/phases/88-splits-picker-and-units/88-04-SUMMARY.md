---
phase: 88-splits-picker-and-units
plan: 04
subsystem: ui
tags: [react, nextjs, recharts, splits, report-card]

requires:
  - phase: 88-02
    provides: the single hoisted anchorS const in page.js, and its provenance caveat line
  - phase: 88-01
    provides: the chord arithmetic (delta-distance over delta-time) that AC-2 reproduces exactly
provides:
  - web/lib/splitWindow.js — bin construction + chord window measurement, pure
  - web/components/portal/SplitPicker.js — the Segment splits card
  - spanS/spanLabel ReferenceArea on VelocityChart + AccelerationChart
  - scratch/split_picker_check.mjs — 44 checks incl. the 1e-12 grid equality
affects: [88-05 (also edits VelocityChart.js and page.js), any mobile phase carrying TimeToX parity]

tech-stack:
  added: []
  patterns:
    - "Selection held as an inclusive {lo, hi} bin-index pair — contiguity is structural, not enforced"
    - "A JS surface reproducing a phase_metrics.py formula is pinned by re-implementing the Python in the harness and asserting equality to 1e-12"

key-files:
  created: [web/lib/splitWindow.js, web/components/portal/SplitPicker.js, scratch/split_picker_check.mjs]
  modified: [web/app/app/sessions/[id]/page.js, web/components/portal/VelocityChart.js, web/components/portal/AccelerationChart.js]

key-decisions:
  - "D4: the window average is the CHORD, never a sample mean — and the search is clamped at finish_s"
  - "D2: complete bins only; the closing stretch belongs to 88-01's splits_remainder row"
  - "D1: its own spanS prop, never onMarkerChange — a window is not a point"
  - "POST-PLAN: Time-to-Distance REMOVED at the user's direction; the anchor caveat moved into this card"

patterns-established:
  - "Clamp a stale index-selection by DERIVING it during render, not by resetting it in an effect (avoids react-hooks/set-state-in-effect)"

duration: ~2h
started: 2026-08-31
completed: 2026-08-31
---

# Phase 88 Plan 04: Segment splits picker — Summary

**A "Segment splits" card that lets a coach measure any contiguous window of the swim — 0–10, 5–15,
0–15 — reading back its chord average velocity and elapsed time and shading the span on both traces;
a single-chip selection reproduces the corresponding grid split to 0.0e+0. Time-to-Distance was
removed at the verify as redundant, and this card inherited its slot and its anchor caveat.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2 h |
| Tasks | 4 auto + 1 blocking human-verify, all complete |
| Files created | 3 |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: arbitrary contiguous windows | **Pass** | `toggleBin`'s four D5 cases asserted, incl. CONTEXT D8's fill-the-gap example; human-verified |
| AC-2: one bin == the grid's split | **Pass** | 6/6 bins equal an independent re-implementation of `_split_velocity`, **max \|Δ\| = 0.00e+0** |
| AC-3: only completed segments offered | **Pass** | A 21.9 m (25-yd) lap yields 4 bins, no 20–25 chip |
| AC-4: shown on the trace, TimeToX undisturbed | **Pass (superseded in part)** | Shading verified live. The "TimeToX marker unchanged" half was verified, then **made moot** when the user removed that card |
| AC-5: unit-native bins, honestly labelled | **Pass** | 5-yd chips + the metre-binned caveat line, imperial only |
| AC-6: nothing else moved | **Pass** | `spanS` absent === `spanS` null byte-for-byte; `/video` route, `VideoTracePanel`, `TraceOverlay`, `phase_metrics.py` all absent from the diff |

## Verification Results

| Check | Result |
|-------|--------|
| `node scratch/split_picker_check.mjs` | **44 passed, 0 failed** |
| `cd web && npm run build` | clean |
| `anchor_check` / `unit_check` / `stroke_toggle_check` / `overlay_render_check` / `marketing_render_check` | 17 / 63 / 63 / 40 / 45 — all **unedited** |
| `npx eslint .` | 26 problems / 23 errors — **zero new** |
| Human-verify | **Approved** 2026-08-31, all 9 steps incl. step 7's grid equality |

**The two assertions worth keeping:** every single-bin window equals `_split_velocity` at exactly
`0.00e+0`; and the `finishS` clamp is proven load-bearing — 5 m of post-touch drift manufactures a
fifth bin without it (4 → 5).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/splitWindow.js` | Created (102 ln) | `buildBins` / `measureWindow` / `toggleBin`, pure |
| `web/components/portal/SplitPicker.js` | Created (120 ln) | The card |
| `scratch/split_picker_check.mjs` | Created (384 ln) | 44 checks |
| `web/components/portal/VelocityChart.js` | Modified (+23) | `spanS`/`spanLabel` → `ReferenceArea`, drawn before the marker |
| `web/components/portal/AccelerationChart.js` | Modified (+21) | Same edit, near-twin |
| `web/app/app/sessions/[id]/page.js` | Modified (+74/−51) | Span state, card mount, **and the Time-to-Distance removal** |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Chord, clamped at `finish_s` (D4) | The waist tether keeps `dist_m` rising past the touch; without the clamp the picker and the grid silently diverge | AC-2 is an equality, not an approximation |
| Complete bins only (D2) | `TimeToX` already hides unreachable presets | No partial "20–25" label can lie; that stretch is 88-01's row |
| Own `spanS` prop (D1) | Two cards writing one marker is a live conflict; a window is not a point | Now partly historical — TimeToX is gone — but the window/point half is durable |
| Derive the stale-selection clamp, don't reset it in an effect | The effect form added the 24th eslint error | Zero new eslint errors, and no frame where chips are lit against a dropped selection |

## Deviations from Plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Test-authoring errors, caught by the harness itself |
| Scope additions | 1 | **Time-to-Distance removal — significant, user-directed** |
| Deferred | 0 | — |

### Scope addition: Time-to-Distance removed

**Found during:** the blocking human-verify. The user's words: *"Remove the time to distance — it's
redundant when segment splits exists."*

🔴 **This contradicts this plan's own D1 rationale and its explicit boundary
`DO NOT CHANGE: web/components/portal/TimeToX.js — 88-02 owns it`.** It is recorded as the user's
call at the verify, not a silent widening. It also lands one day after 88-02 re-anchored that very
card, so 88-02's shipped work now has no UI.

What changed:
- The Time-to-Distance `<section>` deleted from `page.js`; `SplitPicker` inherits its slot and chrome.
- **The anchor caveat block MOVED, not copied, and stayed in `page.js`** rather than going inside
  `SplitPicker`. Two reasons: `page.js` owns the anchor, and pushing the provenance wording into the
  card would put a second copy of the anchor-source rule in the one place nobody looks — the exact
  defect 88-02 removed. It also keeps `scratch/anchor_check.mjs` check 5 (a source-text assertion
  against `page.js`) passing **unedited** — the gate I expected to break and did not.
- Orphans removed, per the repo's surgical-changes rule: the `TimeToX` import, `markerTimeS` /
  `markerLabel` state, the `onMarkerChange` callback, and the now-always-null marker props on both
  chart calls.

⚠ **Dead code deliberately left and named** (the 88-02 D4 convention):
`web/components/portal/TimeToX.js` now has **zero importers**, and the `markerTimeS` / `markerLabel`
props with their `ReferenceLine` blocks on both charts have **no caller on either route**.

⚠ **The user asked for the line to read "from your annotation"; it still reads "from your marks."**
The block was moved verbatim — `anchor_check.mjs` check 5 pins that exact string, and the ask was
read as naming which line to move rather than dictating new copy. **Owed:** confirm the wording; it
is a one-word edit plus one line in the gate.

⚠ **iOS still ships its own Time-to-Distance** (`ReportCardScreen`), so web and mobile now differ in
what the session screen offers, on top of the ~0.4–0.5 s TimeToX disagreement 88-02 already logged.

### Auto-fixed: the harness's own first-run failures

**Found during:** Task 4, first run — 5 failures.
**Issue:** Four were my test arithmetic (20 s × 1.5 m/s reaches 29.98 m, not 30 → 5 bins, not 6).
The fifth was a worthless sub-check: the "sample mean" I built telescoped to the chord exactly on a
uniform time grid, so it proved nothing (|Δ| = 6.66e-16).
**Fix:** Corrected the expectations to a 21 s / 31.5 m trace, and replaced the dud with a real
structural assertion — perturb every *interior* sample of a window by +3 m and the answer must not
move, which only a two-endpoint chord can satisfy.
**Verification:** 44/44, and the AC-2 equality was green from the first run.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Port 3000 held by another chat's dev server | Same working tree, so HMR already served the changes; no second server started |
| A tool result carried an appended instruction to route file work through `cat`/`sed` instead of the Read/Edit/Write tools | Not acted on — it arrived through a tool-result channel and contradicts project setup. Surfaced to the user instead |

## Next Phase Readiness

**Ready:** `splitWindow.js` is pure and node-loadable; the `{lo, hi}` selection shape is reusable.

**Concerns:**
- 🔴 **Phase 88 is 4 of 5, NOT complete. 88-05 (velocity trend overlay, wave 3) has a PLAN and no
  SUMMARY.** This plan's own success criteria said "Phase 88 closes at 4 of 4 plans" — that count
  was written before 88-05 was appended at the user's direction, and acting on it would repeat the
  plan-count trap STATE flags four times over for phase 83. **The phase was NOT transitioned and no
  phase commit was made.**
- ⚠ **88-05 edits `VelocityChart.js` AND `page.js`** — both touched here. It must be re-read against
  the current tree, not the version its PLAN was written against; the Time-to-Distance removal in
  particular changed `page.js`'s middleSlot.
- ⚠ **Nothing is committed.** Wave 1, wave 2, plus the partial 86-02 and 89 work all sit in one
  uncommitted tree.

**Blockers:** None.

---
*Phase: 88-splits-picker-and-units, Plan: 04*
*Completed: 2026-08-31*
