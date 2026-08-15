# Phase Context

**Phase:** 64 — Fullscreen Video + Velocity Overlay (web)
**Discussed:** 2026-08-13 (`/paul:discuss`, 4 rounds, 14 questions)
**Status:** Ready for `/paul:plan`
**Decisions:** 12 (D1–D12) + 4 stated assumptions. **Zero open blocking questions.**

⚠ **WEB ONLY.** `web/` — no Python, no schema, no API change, no mobile. Deploy target is Vercel.
The Python suite (274) is untouched by construction.

---

## Why now

The user asked, verbatim:

> *"is it possible to actually overlay the velocity on the video? On web. currently the video and
> the velocity are separated, and it's difficult to see the video along with velocity because the
> video is extremely small. I want to be able to fullscreen the video and still see the trace."*

**Yes — and the reason it doesn't work today is precise, not vague.** Phase 61-03 shipped
`/app/sessions/[id]/video` as a stacked layout: a `<video controls>` capped at
`clamp(140px, 26vh, 420px)` above a full-width recharts `VelocityChart`
(`web/app/app/sessions/[id]/video/page.js:119-143`). Pressing the native fullscreen button
fullscreens **the `<video>` element itself**, and the chart — a DOM sibling — is not in the top
layer, so it vanishes. The two are not "separated" by layout choice; they are separated by which
element the browser promotes.

Fix: fullscreen a **container** that already holds both, and stop using the native control bar
(whose fullscreen button would re-create the trap).

⚠ **This is the first surface in the system where detector output and real footage share one
visual field.** Cycle boundaries (D8) come from a segmenter Phase 59 measured at boundary F1
**0.44–0.53**, and `video_origin_s` sync has a known live gap (5 of 62 sessions had video with no
origin — DATA-FLOW.md F-b). Expect this phase to *reveal* wrongness rather than only display
rightness. That is the point, not a defect of the plan.

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Fullscreen the CONTAINER, never the `<video>`.** `Element.requestFullscreen()` on a wrapper that already contains the video element, the trace overlay and the control bar. The video element itself must not move in the DOM — moving it would drop playback position and force a second signed-URL fetch. |
| **D2** | **Custom control bar replaces the native one in fullscreen.** Play/pause, ±1 frame, speed `0.25 / 0.5 / 1` (reuse `VideoPane`'s existing `RATES` + `step()`), mute toggle, exit. Chosen over `controlsList="nofullscreen"`, which is Chrome/Edge-only and leaves the trap open on Safari and Firefox. |
| **D3** | **Trace is a translucent strip over the picture, spanning the FULL screen width**, pinned to the bottom. Full width buys ~2.4× the horizontal room of a video-box-width strip for the same 2 s span, which is the difference between reading individual velocity features and not. Needs a dark scrim gradient behind it — a blue trace over sunlit water is otherwise low-contrast. |
| **D4** | **`object-contain` — never crop the frame.** A swimmer near the frame edge must not be cut off. Consequence, accepted knowingly: portrait 3:4 footage on a 16:9 screen occupies ~42% of the width with ~29% black bar each side, so the full-width strip (D3) sits mostly on black and overlays only the video's lower ~42%. |
| **D5** | **Rolling 2 s window that follows the playhead**, playhead centred. Fixed span — **no presets.** Phase 61-03 removed the 1/2/5s/All presets from this page as *"redundant when they can manually adjust the window"*; they are not coming back. ⚠ This does re-introduce auto-follow, which 61-03 withdrew (CONTEXT D16) — **scoped strictly to fullscreen**; the windowed chart keeps its manual brush and does not follow. |
| **D6** | **New hand-rolled SVG overlay component, NOT recharts.** Precompute the polyline once from `velocity_profile`, then pan it by mutating the SVG `viewBox`. recharts re-renders ~2000 points per frame and will visibly stutter at 60 Hz — the exact thing being asked for. Same technique the mobile app already uses. Cost: a second chart component to keep visually in step with `VelocityChart`. |
| **D7** | **`requestAnimationFrame` drives the playhead, not `timeupdate`.** `timeupdate` fires at ~4 Hz and does not fire at all for sub-100 ms seeks — `VideoPane.js:99-101` already documents this. At a 2 s span, 4 Hz is four visible jumps per second. |
| **D8** | **Overlay draws: trace + centred playhead + cycle boundary lines + live velocity readout.** ⚠ The page must now also select `metrics_json` — it currently fetches only `velocity_profile, sample_rate_hz, name, created_at, athlete_id, video_path, video_origin_s` (`page.js:33-36`). **Not** in scope: elapsed/total time, saved annotation marks (both offered, both declined). |
| **D9** | **Sync nudge (±0.1 s) + Save available IN fullscreen.** A wrong origin is far more visible with the trace sitting on the swimmer, so the repair must be reachable where it is noticed. ⚠ **Must reuse `VideoPane`'s existing `nudge`/`saveSync` handlers — it must not become a second writer of `video_origin_s`.** 58-04 was closed on exactly that invariant, and `VideoPane.js:136-153` guards the auto-post on `savedOrigin == null` for the same reason. |
| **D10** | **The windowed layout is unchanged.** The only addition below fullscreen is a button to enter it. The 26vh cap stays; the stacked chart stays; the brush stays. |
| **D11** | **Scope: `/app/sessions/[id]/video` only.** The annotate page and Compare are explicitly OUT. Annotate would raise "can you place marks while fullscreen", which needs keyboard-driven marking and is a real second feature; Compare is a two-video layout problem with a synced-playback TODO already carried out of Phase 61. |
| **D12** | **Audio: mute toggle only.** No volume slider — pool audio is ambient; you want it on or off. |

### Stated assumptions (user did not object)

- **A1 — desktop/laptop surface.** iOS Safari historically supports fullscreen only on `<video>`
  via `webkitEnterFullscreen`, so **container fullscreen will not work on an iPhone**. The coach
  portal is a laptop surface (the phone has its own app). Behaviour there must degrade to today's
  page, not throw.
- **A2 — playhead centred in the window**, window clamped at the trace's start and end so it does
  not scroll past the data.
- **A3 — keyboard works regardless of the auto-hidden bar:** Space play/pause, ←/→ frame step,
  Esc exit. `VideoPane` already exposes `frameStepRef` for precisely this ("the keyboard shortcut
  must work when the `<video>` element does not have focus", `VideoPane.js:114-115`).
- **A4 — control bar and strip auto-hide together after ~2 s idle**, reappearing on mouse move.

---

## What was verified this session (repo, 2026-08-13)

| Claim | Evidence |
|---|---|
| Native fullscreen drops the chart | `page.js:119-143` — `<VideoPane>` and `<VelocityChart>` are DOM siblings; `VideoPane.js:239-247` sets `controls` on the `<video>` |
| Video is small by design | `VideoPane.js:247` — `max-h-[clamp(140px,26vh,420px)] object-contain` |
| Sync contract | `sessionTime = origin_s + video.currentTime` (44-03 end-anchor), `VideoPane.js:86-96` |
| Click-to-seek already wired | `page.js:79-82` → `seekRef.current` → `VideoPane.js:86-92`. The overlay inherits it free |
| Chart is recharts | `web/components/portal/VelocityChart.js:4-14`, `recharts ^3.8.1` in `web/package.json` |
| Sample rate is per-session, never 100 | `page.js:69` — `row.sample_rate_hz > 0 ? … : 100`. The overlay must derive its x-axis identically |
| Cycle boundaries exist and are index-based | `VelocityChart.js:50-56` — `c.start_idx / fsHz` from `metrics_json.cycles` |
| Speed + frame step already built | `VideoPane.js:102-112` (`step`), `:12` (`RATES`) — the fullscreen bar reuses, does not reimplement |
| Video corpus is large enough to verify against | DATA-FLOW.md:559-567 — **29 of 62 sessions have `video_path`; 24 have `video_origin_s`; 5 have video with NULL origin** |
| Footage is portrait | User-confirmed (tripod, phone upright); consistent with `RecordScreen.js:1172` `aspectRatio: 3/4` |

---

## Risks and things this will expose

- **R1 — bad sync origins become obvious.** The end-anchor assumes recording and filming stop
  together; Phase 58 found that a failed `writeCmd('STOP')` is caught non-fatally while the device
  keeps recording, inflating device duration and therefore the computed origin. Today that error is
  invisible; against a fullscreen trace it will not be. D9 exists so it can be fixed in place.
- **R2 — cycle boundaries will be visibly wrong on some sessions.** Phase 59 measured boundary F1
  at 0.44–0.53 per stroke and left `segmentation_reliable` hardcoded `False`. Drawing them beside
  real footage is arguably the most valuable thing in this phase and the most likely to prompt
  follow-up work. It is **not** a reason to hide them.
- **R3 — the `currentTime` wobble hypothesis is still unmeasured** (carried out of Phase 60-03). A
  60 Hz rAF playhead is the first thing in the system that would make such wobble visible. If the
  playhead jitters while the video plays smoothly, that is the cause, not the overlay.
- **R4 — two chart components can drift visually.** `VelocityChart` (recharts, windowed) and the new
  SVG overlay must agree on colour, stroke width and y-scale, or the same swim will look like two
  different swims on one page.
- **R5 — iOS Safari (A1).** Needs a real fallback path, not an unhandled promise rejection.

---

## For `/paul:plan` — the one open design call

**Where does the fullscreen container live?** The target must be an ancestor of the `<video>`
element (D1), which forces a choice:

- **(a)** `VideoPane`'s root div becomes the target; the overlay renders inside `VideoPane`; the
  page passes `time` / `velocity` / `cycles` / `fsHz` down. Self-contained, but `VideoPane` grows
  from "video player" into "video player + chart" and the annotate page inherits props it ignores.
- **(b) [recommended]** The page wraps `<VideoPane>` and the overlay in a container and fullscreens
  that; `VideoPane` takes one `fullscreen` boolean so it can hide its own chrome (upload label,
  meta line) and swap native `controls` for the custom bar. More surgical per `.claude/CLAUDE.md`
  §3; the annotate page's usage is unaffected because the prop defaults false.

Either way `VideoPane`'s backward compatibility on `/app/annotate/[id]` is an acceptance criterion —
the same invariant Phase 61 used (D14).

---

## Files in scope

| File | Change |
|---|---|
| `web/app/app/sessions/[id]/video/page.js` | Add `metrics_json` to the select (D8); render the fullscreen container; wire the enter/exit button |
| `web/components/portal/VideoPane.js` | `fullscreen` prop: hide chrome, drop native `controls`, expose play/pause + mute to the bar; reuse `nudge`/`saveSync` unchanged (D9) |
| `web/components/portal/TraceOverlay.js` | **NEW** — hand-rolled SVG, viewBox-panned 2 s window, rAF playhead, boundaries, readout (D5–D8) |
| `web/components/portal/FullscreenControls.js` | **NEW (or folded into the page)** — custom bar, auto-hide, keyboard (D2, A3, A4) |

Untouched: all Python, `supabase/`, `api.py`, the mobile repo, `VelocityChart.js`
(unless R4 forces a shared colour constant).

---

## Carried out (recorded, not scoped here)

- Fullscreen overlay on the **annotate** page, incl. marking from fullscreen (D11).
- Fullscreen on **Compare**, which still has Phase 61's unplanned synced-playback TODO (D11).
- Backfilling the 5 sessions with `video_path` and NULL `video_origin_s` (DATA-FLOW.md F-b) —
  61-03's web-side computation fixes them on open, so this stays a data-hygiene item.
- `requestVideoFrameCallback` for true frame-accurate stepping; `FRAME_S = 1/30` stays assumed
  (`VideoPane.js:6-10`).

---

## Success criteria

- [ ] A fullscreen button on `/app/sessions/[id]/video` fills the screen with video **and** trace.
- [ ] The native control bar's fullscreen trap is gone (custom bar, all browsers).
- [ ] Trace strip: full screen width, translucent, scrimmed, legible over sunlit water.
- [ ] Video frame is never cropped (`object-contain`).
- [ ] 2 s rolling window follows the playhead smoothly — no visible stutter at 60 Hz.
- [ ] Live velocity readout and cycle boundaries render on the overlay.
- [ ] Clicking the trace seeks; ±0.1 s nudge + Save work in fullscreen and write via the existing
      single `video_origin_s` path.
- [ ] Controls + strip auto-hide after ~2 s idle; Space / ←→ / Esc work throughout.
- [ ] The windowed layout is byte-for-byte the same as before, apart from the new button.
- [ ] `/app/annotate/[id]` still renders and behaves identically (`VideoPane` back-compat).
- [ ] Verified against a real session that has both `video_path` and a stored `video_origin_s`.
