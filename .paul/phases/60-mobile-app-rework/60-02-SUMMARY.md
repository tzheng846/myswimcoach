---
phase: 60-mobile-app-rework
plan: 02
subsystem: ui
tags: [react-native, ios, react-native-svg, panresponder, charting, brush, refactor]

requires:
  - phase: 60-mobile-app-rework (60-01)
    provides: the corrected time axis the window maps over, and shared ownership of ReportCardScreen
provides:
  - "chartWindow.js — pure windowing maths (clampWindow with anchor, resampleWindow, px<->time)"
  - "VelocityChart controlled `window` prop — the primitive 60-03 drives from the playhead"
  - "Brush strip: two draggable handles plus a draggable body, on a dedicated PanResponder"
  - "Pinch-to-zoom removed, along with its dead double-tap reset"
affects: [60-03]

tech-stack:
  added: []
  patterns:
    - "Controlled/uncontrolled window resolution: windowProp ?? internal ?? full"
    - "One PanResponder per job — the prior bugs came from one multiplexing three"
    - "Byte-identical output as a refactor acceptance test (Phase 59 D14 made mechanical)"

key-files:
  created: [src/lib/chartWindow.js]
  modified: [src/components/VelocityChart.js, src/screens/ReportCardScreen.js, src/screens/RecordScreen.js]

key-decisions:
  - "D6: brush bar replaces pinch entirely"
  - "D7: ONE controlled-window primitive, TWO drivers — not two components"
  - "D12: brush on both results surfaces, so the two screens cannot disagree"
  - "Legacy Math.floor stride kept SEPARATE from resampleWindow's Math.ceil, to keep the default chart byte-identical"

patterns-established:
  - "Transcribe the pre-refactor algorithm from git, not from memory, when pinning behaviour"
  - "Anchor a sampling lattice to absolute index, never to a sliding window start"

started: 2026-08-11
completed: 2026-08-11
---

# 60-02 SUMMARY — Windowed chart primitive + brush bar

**Phase:** 60 — Mobile App Rework
**Plan:** 60-02 · `execute` · wave 2 · `depends_on ["60-01"]` · `autonomous:false`
**Applied + closed:** 2026-08-11 (checkpoint approved)
**Repo:** `swimnetics-mobile` only — **no `myswimcoach` file changed at all**, not even a doc

---

## Result

All 3 auto tasks complete, checkpoint approved, **all 5 ACs met**.

| Check | Result |
|---|---|
| AC-1 windowing math (node, 7 clamp cases + 4 resample + round-trip) | ✓ all PASS |
| AC-1 degenerate input (11 cases) | ✓ no throws, no NaN |
| **AC-2 unwindowed polyline, OLD vs NEW, 4 real traces** | ✓ **BYTE-IDENTICAL** |
| AC-3 in-window resampling | ✓ **~30–37 → 181 points** for a 2 s window |
| px↔time round-trip | ✓ 2.22e-16 s / 0.00 px |
| pinch / `zoomWindow` / "Reset zoom" remnants | ✓ none (comments only) |
| AC-5 VideoOverlayScreen | ✓ `git diff` empty — untouched |
| `npx expo export --platform ios` | ✓ exit 0, **1092 → 1093** (+1) |
| `pytest tests/` | ✓ **273 passed**, zero `.py` changed |

---

## ⭐ AC-2: the refactor provably did not drift

The unwindowed point set is the chart everyone actually looks at, so the plan pinned it. The old
algorithm was transcribed **verbatim from `git show HEAD:src/components/VelocityChart.js`** (not
from memory) and run head-to-head against the shipped code on four real traces:

```
69f33669  n= 2421  chars=  4484  IDENTICAL
c0cdfc25  n= 2035  chars=  4505  IDENTICAL
e166b8fe  n= 2283  chars=  5052  IDENTICAL
d25c578f  n= 1954  chars=  5370  IDENTICAL
```

⚠ **This required a deliberate design choice worth preserving.** `resampleWindow` uses a
`Math.ceil` stride; the legacy unwindowed path uses `Math.floor(n/400)`. On a 4216-sample trace
those differ (384 vs 422 points), so routing the unwindowed view through the new resampler would
have silently changed the default chart. The two paths are therefore **kept separate on purpose**,
with a comment in `VelocityChart.js` saying so. Unifying them is a legitimate future change but it
needs its own before/after comparison — it is not a tidy-up.

## The 17-point problem, measured — and the plan's figure corrected

⚠ **The plan's "~17 points" was from a hypothetical 47 s trace.** Real sessions are 22–27 s, so the
old behaviour actually kept 30–37 points, not 17. The improvement is real but the plan overstated
the starting point:

```
69f33669  26.9s trace  2s window:  old ~30 pts   new 181 pts
c0cdfc25  22.6s trace  2s window:  old ~35 pts   new 181 pts
e166b8fe  25.4s trace  2s window:  old ~32 pts   new 181 pts
d25c578f  21.7s trace  2s window:  old ~37 pts   new 182 pts
```

5–6× more detail, which is what 60-03's rolling window needs to not look like a polygon.

---

## What shipped

### `src/lib/chartWindow.js` — NEW, pure, node-verified
`MIN_SPAN_S` (0.5, carried over from the removed pinch guard so behaviour transfers rather than
changes), `fullRange`, `clampWindow`, `isFullRange`, `resampleWindow`, `timeToPx`, `pxToTime`.

`clampWindow` takes an **`anchor`** because the three gestures want different things — `'span'`
preserves width while panning, `'start'` holds the left edge when the right handle moves, `'end'`
holds the right edge when the left handle moves. A single "clamp" without this would make a
handle drag slide the whole window once it hit the minimum span.

Every function tolerates degenerate input. This matters more than it looks: on the video page these
run ~20×/second, and one NaN blanks the trace mid-playback.

### `src/components/VelocityChart.js` — rebuilt
**Removed:** `pinchRef`, the two-finger branch, `zoomWindow` state, the pan-when-zoomed branch, the
double-tap reset, the "Reset zoom" button.

⚠ **The double-tap reset was already dead code.** `onStartShouldSetPanResponder: () => false` meant
a plain tap never granted the responder, so it only ever fired if the user dragged twice. Removing
it deletes a bug; it is not a capability being taken away.

**Added:** a controlled `window` prop (resolved as `windowProp ?? brushWin ?? full`, the standard
controlled/uncontrolled pattern, so 60-03's call-site change stays small), a `brush` prop, and
`onWindowChange`.

**Brush strip** uses a **second, dedicated PanResponder**. The old bugs came from one responder
multiplexing pinch, pan and cursor; one responder per job is the fix. It hit-tests once on grant
into `left | right | body` and holds that mode for the drag. Handles are drawn at 8 pt but
hit-tested at 20 pt, since 8 pt is not thumb-reachable.

**Three performance fixes**, all prerequisites for 60-03's 20 Hz driver:
1. `useMemo` on the full-trace downsample — the component previously had **no `useMemo` anywhere**.
2. In-window resampling (the numbers above).
3. **Y-scale pinned to the full trace whenever a window is active** — otherwise it rescales
   20×/second and the trace visibly jitters. Unwindowed behaviour unchanged, which AC-2 proves.
4. (Also) `Math.min(...v)` / `Math.max(...v)` spreads replaced with a loop.

### Call sites
`brush` added to `ReportCardScreen.js:481` and `RecordScreen.js:937` (**D12**).
`VideoOverlayScreen.js` deliberately untouched — it gets a *controlled, playhead-driven* window in
60-03, and a hand-draggable brush would fight it. Its unchanged `git diff` is AC-5's guard.

---

## Deviations from the plan

1. **Tasks 2 and 3's component edits landed in one file write**, not two sequential ones. The plan
   split them per Phase 59's D14 lesson (a refactor sharing a diff with a feature makes unexpected
   movement unattributable). **The substance survived**: the acceptance test the split existed to
   enable — byte-identical unwindowed output — ran independently and passed on four real traces,
   and the brush is purely additive behind a prop defaulting to `false`. The risk is covered; the
   structure deviated. Recorded rather than glossed.
2. **The plan's "~17 points" figure was wrong** (see above). ~30–37 on real traces.
3. **`web/components/Footer.js` and `Nav.js` appear in `git status`** — pre-existing Phase 46 blog
   work, dirty since before this session. Not from 60-02.

---

## Files changed

| File | Change |
|---|---|
| `swimnetics-mobile/src/lib/chartWindow.js` | **NEW** — pure windowing math |
| `swimnetics-mobile/src/components/VelocityChart.js` | controlled window, brush strip, pinch removed, memoized |
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | `brush` prop |
| `swimnetics-mobile/src/screens/RecordScreen.js` | `brush` prop |

---

## Carried forward

- **60-03** — the last plan of Phase 60: video reachable from any saved session (D4), rolling
  playhead window (D5), origin precedence + write guard (D11). It consumes this plan's `window`
  prop and 60-01's `fsHz`.
- **Possible future:** unify the legacy unwindowed projection with `resampleWindow`. Deliberately
  not done here — it changes the default chart and needs its own comparison.
