---
phase: 84-mobile-user-feedback
plan: 04
subsystem: mobile
tags: [react-native, panresponder, gestures, scrollview, velocity-chart]

requires:
  - phase: 60-mobile-app-rework
    provides: the brush strip itself — Phase 60 removed pinch-to-zoom, making the brush the
      ONLY way to zoom the velocity trace, which is why losing it mid-drag is severe
provides:
  - both VelocityChart pan responders refuse to hand an in-progress drag to a parent ScrollView
  - scratch/gesture_check.mjs — an AST guard with a mutant self-test
affects: [ReportCardScreen, RecordScreen results chart — both repaired without being edited]

tech-stack:
  added: []
  patterns:
    - "Fix gesture ownership in the COMPONENT, not per-consumer — one edit repaired a surface
       nobody reported and kept the plan out of another plan's file"

key-files:
  created:
    - scratch/gesture_check.mjs
  modified:
    - ../swimnetics-mobile/src/components/VelocityChart.js

key-decisions:
  - "No decision checkpoint by design: the cost (two dead zones) is a device-feel judgement
     nobody can make from a chair, so it goes to the verify with the fallback pre-specified"
  - "onShouldBlockNativeResponder deliberately NOT added — it already defaults true in RN 0.85.3"
  - "The strip is NOT enlarged — a responder does not lose a gesture by leaving bounds"

patterns-established:
  - "Source-level AST guards must state what they do NOT prove; this one's banner says
     configuration only, never gesture behaviour"

duration: ~1 session
started: 2026-08-30
completed: 2026-08-31
---

# Phase 84 Plan 04: Brush-Bar Gesture Summary

**One property on each of two pan responders, in one component, repairs three screens.**
`onPanResponderTerminationRequest: () => false` stops the parent `ScrollView` stealing a brush drag
the moment the finger drifts off the 30 pt strip. **+11 lines, one file.**

## Root cause, confirmed in RN's own source

`node_modules/react-native/Libraries/Interaction/PanResponder.js:520-522` defaults
`onPanResponderTerminationRequest` to **`true`** — so both responders were answering *"yes, take it"*
to every request, including the parent ScrollView's. CONTEXT's root cause held without amendment.

**The bug was worse on a surface CONTEXT never examined (G33):** `RecordScreen.js:994` renders the
post-recording results chart with `brush` and **no `onInteractionStart`/`End`** inside a `ScrollView` —
it had no scroll lock at all, where the report card at least sets `scrollEnabled = false`. Fixing in
the component repairs it **without touching `RecordScreen.js`**, which 84-02 and 84-05 both modify.

**Open question 6 answered NO, twice over (G34):** `VideoOverlayScreen` passes neither `interactive`
nor `brush` — both responders are gated on exactly those props — and its container has no `ScrollView`.

## Acceptance Criteria Results

| AC | Result | Evidence |
|----|--------|----------|
| AC-1: Both responders refuse to hand over a drag | **Pass** | Present at `:75` (body) and `:104` (brush), each with its own reason comment — the two reasons differ and both are written down. No other callback added, removed or reordered |
| AC-2: Component-level — no consumer touched | **Pass** | `ReportCardScreen.js`, `VideoOverlayScreen.js`, `chartWindow.js` all byte-identical to HEAD (empty diff). `RecordScreen.js` untouched *by this plan* |
| AC-3: The guard actually guards | **Pass** | `node scratch/gesture_check.mjs` → **7/7, exit 0**, including the mutant self-test that strips the property from an in-memory copy and asserts the checks FAIL |
| AC-4: The symptom is gone on a device | **Deferred** | Owed |
| AC-5: The two dead zones are judged | **Deferred** | Owed — a judgement, not pass/fail |

Re-run at close 2026-08-31: **7/7, exit 0.**

## Deviations

1. **AC-2's baseline was stale by apply time.** It names four pre-existing mobile files; 84-01/84-02/
   84-03 had since landed, so the real baseline was 14 modified + 2 untracked. The *substance* of the
   clause — this plan adds exactly one file to the diff — holds.
2. **The plan said this lane needs no EAS build.** True: it is pure JS and Metro would prove it today.
   The user chose to fold it into the build batch anyway so the whole phase is judged in one sitting.

## Deferred

**AC-4 + AC-5, both owed → STATE item 23.**

- **AC-4:** a sideways brush drag survives vertical drift on the report card **and** on the results chart.
- **AC-5:** a *judgement* — the accepted cost is two thin dead zones where a drag starting on the 30 pt
  strip, or horizontally on the chart body, can no longer scroll the page until the finger lifts.

If AC-5 reads wrong, the fallback needs no re-plan:
`onPanResponderTerminationRequest: (evt, g) => Math.abs(g.dy) > Math.abs(g.dx) * 2` in each config —
restores page-scroll-from-the-strip at the cost of reintroducing the original bug for a near-vertical drag.

⚠ `scratch/gesture_check.mjs` proves the **configuration** only. Its banner says so. A green run is not
evidence for AC-4 or AC-5.

## Next Phase Readiness

No blockers. The one Phase-84 lane touching none of `RecordScreen.js` / `BleContext.js` / `CycleCharts.js`.
