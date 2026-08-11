---
phase: 60-mobile-app-rework
plan: 03
subsystem: ui
tags: [react-native, ios, expo-video, signed-url, video-sync, video-origin, rolling-window]

requires:
  - phase: 60-mobile-app-rework (60-01)
    provides: fsHz — the origin-recompute fallback reads deviceDuration off the time array
  - phase: 60-mobile-app-rework (60-02)
    provides: the controlled `window` prop, in-window resampling, and the pinned y-scale
  - phase: 47-trial-annotation
    provides: GET /sessions/{id}/video-url — built then, first called by a mobile client now
provides:
  - "Video reachable from any saved session via a signed URL, on any device"
  - "Rolling playhead window (1/2/5 s/All, default 2 s), centred, no new timer"
  - "video_origin_s protected from silent overwrite by a second entry point"
  - "User-dropped START marker overriding baseline_end_s for Time-to-Distance (in-memory)"
affects: [58-04, 53-attention-allocation, 52-02]

tech-stack:
  added: []
  patterns:
    - "One rule over per-caller flags: 'use the stored value if there is one, else compute and save'"
    - "A read path that may create but never overwrite"

key-files:
  created: []
  modified:
    - src/screens/ReportCardScreen.js
    - src/screens/VideoOverlayScreen.js
    - src/components/VelocityChart.js
    - src/lib/chartWindow.js

key-decisions:
  - "D11 AMENDED: 'never overwrite an existing origin', replacing 'the read path never auto-writes'"
  - "D13: start marker is per-session and in-memory only; DB-persisted and per-athlete both declined"
  - "D14: label the two Video Overlay control rows"
  - "D15: anchor the resampling lattice to absolute index — fixes shimmer at span 5 s and above"

patterns-established:
  - "Prefer deleting a branch to adding a flag when one rule covers every case"
  - "Measure a reported visual defect before patching it; name the unmeasured remainder"

started: 2026-08-11
completed: 2026-08-11
---

# 60-03 SUMMARY — Video from any session + rolling window + start marker

**Phase:** 60 — Mobile App Rework
**Plan:** 60-03 · `execute` · wave 3 · `depends_on ["60-01","60-02"]` · `autonomous:false`
**Applied + closed:** 2026-08-11 (decision checkpoint resolved, human-verify approved)
**Repo:** `swimnetics-mobile` only — **no `myswimcoach` code changed**

---

## Result

4 tasks (3 planned + 1 amended), both checkpoints cleared, **all 8 ACs met**.

| Check | Result |
|---|---|
| `npx expo export --platform ios` | ✓ exit 0, **1093 modules** (no net new files) |
| `pytest tests/` | ✓ **273 passed**, zero `.py` changed |
| Rolling-window lattice, spans 1/2/5 s | ✓ **one phase at every span** (5 s was two, alternating) |
| chartWindow suite (7 clamp + 11 degenerate) | ✓ no regression |
| AC-2 byte-identical unwindowed polyline | ✓ still identical after the lattice change |
| `RecordScreen.js` | ✓ untouched — `git diff` empty |
| Stale `videoOriginS` / `allowOriginWrite` | ✓ none |

---

## ⭐ The decision checkpoint changed the design for the better

D11 was recorded as *"the read path never auto-writes"*. Presenting that at the checkpoint, the user
asked the more useful question — *"I'm confused why there's different screens from right after
recording and session report. I think I want a single destination, so there should be only one view
video. would that make it simpler?"*

Two things came out of that:

1. **A misconception worth having cleared up:** there was never a second screen. `VideoOverlayScreen`
   is one destination with two *doors*. What differs is the video source (local `file://` right after
   recording, signed URL later) — and that difference is justified, since collapsing it would mean
   waiting for a background upload to review a swim you just filmed.
2. **A real simplification.** The origin rule did *not* have to differ per door. One sentence covers
   every case:

   > **Use the stored origin if there is one. Otherwise compute it and save it.**

   | Entry point | stored | behaviour |
   |---|---|---|
   | Record screen | always null | compute, save — unchanged from today |
   | Report card, previously synced | exists | use it, never write |
   | Report card, never synced | null | compute, save — closes 58-04's symptom |
   | Nudge, either door | — | always saves |

**This deleted code rather than adding it**: the planned `allowOriginWrite` param, its branch, and
the "which screen am I" concept are all gone. `VideoOverlayScreen` took **one** new param
(`storedOriginS`) and `RecordScreen` needed **no edit at all**, because a fresh recording never has
a stored origin and the old behaviour falls straight out of the new rule.

D11 amended in CONTEXT from "the read path never auto-writes" to **"never overwrite an existing
origin"** — which is what it was actually protecting; the original wording over-reached into a case
nobody had examined.

## ⚠ The bug the plan predicted was real

The nudge-save at `:128-134` was gated on `originSavedOnceRef`, a ref set by the **auto-post**.
Skipping the auto-post would have made that guard silently swallow the user's first nudge — losing
the one repair mechanism D11 exists to preserve. Replaced with a dedicated `nudgeMountRef` that only
skips the initial mount, decoupling "the user nudged" from "the auto-post ran".

---

## What shipped

**Task 1 — video from any saved session (D4).** `video_path` added to the report card's select;
`▶ Video + Velocity` renders only when it is set, styled as the sibling of "Compare to previous"
(both are "take this session elsewhere"). Taps `GET /sessions/{id}/video-url` via the existing
`apiFetch`, which already throws with `.status`. Spinner in-button, double-tap guarded, 404/503/
network each get a readable alert and **no navigation**. The signed URL is fetched on tap, never at
page load, because it expires in 3600 s. **No backend work** — the endpoint has existed since Phase
47 with no mobile caller.

**Task 2 — rolling playhead window (D5).** Presets 1 s / 2 s / 5 s / **All**, default 2 s, derived
from the marker the existing 20 Hz poll already produces — **no new timer**. Centred on the
playhead, so the coach sees the approach and the follow-through; `clampWindow`'s `'span'` anchor
gives the end behaviour for free (near t=0 the window becomes `[0, span]`, preserving width rather
than shrinking). "All" passes `null`, which is exactly the pre-60-03 view.

**Task 3 — origin precedence and the write guard (D11, amended).** Above. The debug line now names
its source and shows what the end-anchor *would* have been — with two possible origins, a systematic
offset is only diagnosable if you know which produced it.

**Task 4 — added mid-apply at the user's request.**
- **D13 start marker.** *"I don't trust auto detect baseline."* Scrub the chart, tap
  `Start at 3.10 s`, and Time to Distance re-measures from there; a green START line marks it;
  "Use auto" reverts. Per session, **in-memory only** (DB-persisted and per-athlete both declined).
  **No maths changed** — `computeTimeToX` already took the start as a parameter. The non-obvious
  part: the parent's copy of the scrub time must outlive the chart cursor's 2-second fade, or the
  control dies before the user can reach it.
- **D14 control labels.** The window presets and sync nudges were two unlabelled rows of
  near-identical pills, with the single caption *below the second row* so it read as belonging to
  both. Each row now carries a left-hand label at no vertical cost.
- **D15 lattice fix.** Measured, not guessed — see below.

---

## The "dancing" trace: one cause fixed, one left open and named

Measured by simulating the 20 Hz playhead walk against a real trace:

```
BEFORE   span  1s  stride 1  lattice phases 1  STABLE
         span  2s  stride 1  lattice phases 1  STABLE
         span  5s  stride 2  lattice phases 2  ** SLIDES → shimmer **

AFTER    span  5s  stride 2  lattice phases 1  STABLE
```

`resampleWindow` anchored its stride to the *window's* start index, so once a window held more than
400 samples the lattice slid with the window and consecutive frames drew different neighbouring
samples — the line shimmering against itself. Now anchored to absolute index 0, so a slide only adds
and removes points at the edges.

⚠ **NOT FIXED, and deliberately so.** Spans 1 s and 2 s were *already* stable, so if the trace still
dances at the default 2 s the lattice was never the cause. Leading hypothesis, unverified without a
device: `player.currentTime` wobbling between polls, which moves a playhead-centred window ±2 px at
20 Hz. **Diagnostic:** log successive `currentTime` deltas at `VideoOverlayScreen.js:103`; if they
are not a steady ~0.05 s, that is it, and the fix is to advance the window on a monotonic clock.
Recorded rather than speculatively patched.

---

## ⚠ Verification honesty note

Approved with a bare *"approved"*, no itemized on-device observations. Device-independent evidence
is strong for AC-3 (node lattice simulation), AC-5 and AC-8 (export, pytest, regression suites) and
the code paths for AC-1/2. **AC-4, AC-6 and AC-7 are visual/interactive and rest on the approval.**
Same caveat as 60-01, recorded for the same reason: 58-01 was approved on assumption and that
ambiguity cost real diagnostic time later.

Specifically unconfirmed: whether the 2 s rolling window reads well during playback — which is the
entire point of the user's original ask — and whether the trace still dances.

---

## Files changed

| File | Change |
|---|---|
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | video button + signed-URL fetch; start-marker state and controls |
| `swimnetics-mobile/src/screens/VideoOverlayScreen.js` | remote source, origin precedence, write guard, rolling window, labelled controls |
| `swimnetics-mobile/src/components/VelocityChart.js` | `onCursorChange`, `startMarkerTimeS` (green START line) |
| `swimnetics-mobile/src/lib/chartWindow.js` | lattice anchored to absolute index (D15) |

⚠ Uncommitted at time of writing. Prior phase commits: `4a03f2c` (58-01), `098f345` (60-01),
`8c4a4c0` (60-02).

---

## Carried out of Phase 60

- **The `currentTime` wobble hypothesis** — unmeasured; diagnostic recorded above.
- **58-04 (`VideoPane` end-anchor)** — still owed, still homeless. Web work; D11a eased the symptom
  from the mobile side but the annotate page still cannot compute an origin of its own.
- **Phase 52-02 (measure + backfill NULL sample rates)** — better motivated than its backlog
  position suggests: 60-01 found most NULL-rate rows are ~90 Hz, not ~100.
- **Three unconnected notions of "when the swim starts"** — `detect_phases`' auto `baseline_end`,
  the annotation contract's human `dive_start_s`, and now D13's marker. The user's stated distrust
  of auto-detection is an input to Phase 53.
- **The start marker is in-memory only** — lost on leaving the screen, by choice. Persisting it is a
  schema change.
