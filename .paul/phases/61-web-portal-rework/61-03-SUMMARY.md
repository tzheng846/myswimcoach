---
phase: 61-web-portal-rework
plan: 03
subsystem: ui
tags: [nextjs, react, recharts, video, supabase, sync]

requires:
  - phase: 47-trial-annotation
    provides: GET /video-url + POST /video, unchanged and sufficient
  - phase: 61-02
    provides: the report card this plan adds an entry point to
provides:
  - /app/sessions/[id]/video — read-only video + velocity route
  - end-anchored video_origin_s computed by the web — CLOSES 58-04
  - click-to-seek from the velocity trace
  - view/unit persistence across prev/next (61-02 carry-over)
affects: [61-04 compare redesign, 58 video ground truth, 53 attention allocation]

tech-stack:
  added: []
  patterns:
    - "Origin precedence: stored ?? end-anchored; never overwrite a stored value"
    - "Check library source before working around it — recharts 3.8 already supported what was being forced"

key-files:
  created: [web/app/app/sessions/[id]/video/page.js]
  modified: [web/components/portal/VideoPane.js, web/components/portal/VelocityChart.js, web/app/app/sessions/[id]/page.js, web/app/app/annotate/[id]/page.js]

key-decisions:
  - "D16 WITHDRAWN mid-apply: span presets removed, brush is the only window control"
  - "Annotate page edited despite DO-NOT-CHANGE — AC-2 required it, boundary was self-contradictory"
  - "Second instance of the 58-04 defect found in attach() and fixed"

patterns-established:
  - "A control must not appear and disappear with state — showBrush entanglement caused a reported bug"

duration: ~55min including two checkpoint repair rounds
started: 2026-08-11
completed: 2026-08-11
---

# 61-03 SUMMARY — Video route + closing 58-04

**Session video has a front door on the web, and the web now computes its own sync origin instead
of silently defaulting to zero. 58-04 is closed — owed and homeless since 2026-08-07.**
User verification: *"everything works."*

## Performance

| Metric | Value |
|---|---|
| Tasks | 3 auto + 1 checkpoint (2 repair rounds) |
| Files | 1 created, 4 modified |
| Python | **0** — suite held at 274 |
| Build | clean at every task boundary |
| Backend | **none** — `GET /video-url` + `POST /video` unchanged since Phase 47 |

## Acceptance criteria

| AC | Status |
|---|---|
| AC-1 route exists, reachable in one click | **Pass** — user-confirmed |
| AC-2 web computes end-anchored origin (58-04) | **Pass** — user-confirmed |
| AC-3 stored origin never overwritten | **Pass** — guarded on `savedOrigin == null` |
| AC-4 chart follows the playhead, 1/2/5s/All | ⚠ **WITHDRAWN — not met, and no longer required** |
| AC-5 `VelocityChart` backward-compatible | **Pass** — byte-identical, then true by construction |
| AC-6 no video is usable, not a dead end | **Pass** — user-confirmed |
| AC-7 annotate page not regressed | **Pass** — user-confirmed |

## ⚠ AC-4 and CONTEXT D16 were WITHDRAWN, not satisfied

At the checkpoint the user removed the 1s/2s/5s/All presets — *"redundant when they can manually
adjust the window. this should make the code more clear and consistent."* The brush is now the
only window control.

**Accepted consequence, stated before implementing:** the chart no longer auto-follows the
playhead. On a 33 s trace with a narrow brush the marker walks off the right edge during playback.
This was mobile 60-03 parity and D16's entire purpose. **Reverse this first if playback ever feels
wrong.**

⭐ The removal deleted far more than four buttons. Nothing supplied `viewRange` afterwards, so
`brushIdx`, `yDomain` and `showBrush` all became dead and went with it:

| | mid-apply | shipped |
|---|---|---|
| `VelocityChart` diff | viewRange, brushIdx, yDomain, showBrush, rounded domain, tick formatter, controlled brush | **`onClick` only — 9 lines** |
| video page | 187 lines | **147** |

The downsample is now byte-for-byte the pre-61-03 original, so **AC-5 holds by construction rather
than by measurement**. Two of my own defects vanished with the code that caused them.

## ⚠ The checkpoint caught six defects across two rounds

Recorded because the pattern matters more than the individual bugs: **the first submission was not
working software.**

**Round 1 — four reports:**
1. + 2. *"slider bar buggy… disappeared"* and *"1s/2s/5s/All doesn't work, only activates after
   working with buggy slider bar"* — **one root cause, mine.** `viewRange` was gated on
   `playheadS != null`, but the playhead stays null until the video emits its first time update.
   On load: no window → presets inert → brush visible; on interaction → window appears → brush
   vanishes.
3. The entry point was a small header link — *"should be front and center right above velocity
   card"*. Fixed to a full-width accent panel. A header link was still hidden, just elsewhere.
4. view/unit did not survive prev/next — **the exact question 61-02 left unanswered.**

**Round 2 — two more:**
5. Unreadable y-axis ticks (`435346`, `126302`…). Supplying an explicit `domain` defeats recharts'
   nice-tick algorithm, so it interpolated raw floats like `-0.1586398248500771`, which
   `width={42}` clipped into digit soup. ⚠ The *flat line* in the same screenshot was **correct** —
   at playhead 0 the window covers the pre-swim baseline where velocity really is zero.
6. *"scroll bar completely gone"* — my round-1 fix over-corrected. The user wanted it **stable**,
   not deleted.

⭐ **Checking the library beat working around it.** The round-2 brush fix initially forced updates
with a `key` remount. Reading `node_modules/recharts/lib/cartesian/Brush.js:534` showed 3.8
supports controlled indices natively via `startIndexControlledFromProps`. The key was dropped —
which mattered, because `onTimeUpdate` fires ~4 Hz and remounting that often would have traded the
reported bug for a worse one. All of this was then deleted anyway by the preset removal.

## Deviations

**1. ⚠ BOUNDARY VIOLATION — the annotate page was edited despite DO-NOT-CHANGE.**
`web/app/app/annotate/[id]/page.js` is on the plan's protected list, but AC-2 requires the annotate
page to compute an end-anchored origin, which is impossible unless it passes `sessionDurationS`.
**The plan contradicted itself**; the AC was chosen over the boundary. One prop, no logic. Flagged
at the checkpoint and not objected to. Without it 58-04 would stay open on the annotate page —
the surface where it actually bites.

**2. ⭐ A SECOND instance of the 58-04 defect, not in the plan.** `VideoPane.attach()` did
`origin_s: r.video_origin_s ?? 0`, so attaching a video *through the web* also forced a null origin
to zero. Same defect, second site. Fixed; shipping the repair at one site and not the other would
have been incoherent.

**3. view/unit persistence was not in this plan.** It was 61-02's unanswered question, reported as
a defect at this checkpoint and fixed here via `localStorage`. Read in an effect rather than a lazy
initializer — `localStorage` does not exist during SSR and reading it in render desyncs hydration.

**4. Two prompt-driven scope reversals mid-apply** — D16 withdrawn (above) and the entry point
relocated. Both user-initiated at the checkpoint.

## Files

| File | Change |
|---|---|
| `web/app/app/sessions/[id]/video/page.js` | **NEW** — 147 lines, read-only video + velocity |
| `web/components/portal/VideoPane.js` | End-anchored origin, write-once guard, provenance line, `?? 0` removed at **two** sites |
| `web/components/portal/VelocityChart.js` | `onClick` only (9 lines) |
| `web/app/app/sessions/[id]/page.js` | Entry point above the velocity card; view/unit persistence |
| `web/app/app/annotate/[id]/page.js` | `sessionDurationS` prop — see Deviation 1 |

## ⭐ 58-04 IS CLOSED

Owed since 2026-08-07, carried through Phase 58's close-out and Phase 60's, described in both as
"homeless". `VideoOverlayScreen` on the phone is **no longer the only thing in the system that
writes `video_origin_s`**. PROJECT.md and the Phase 58 ROADMAP row should stop listing it as owed.

## Next phase readiness

**Ready:** 61-04 (Compare) is unblocked and shares no files with this plan.

**Concerns**
- ⚠ **Not committed, not deployed.** Working tree carries this plan's 5 files.
- ⚠ **The chart no longer follows the playhead** (AC-4 withdrawn) — the first thing to revisit if
  playback reads badly with a narrow brush.
- ⚠ The mobile D5c comment fix from 61-02 is still uncommitted in `swimnetics-mobile` and needs an
  EAS build to reach a device.

**Blockers:** None.

---
*Phase: 61-web-portal-rework, Plan: 03*
*Completed: 2026-08-11*
