# Phase Context

**Phase:** 60 — Mobile App Rework (per-cycle analytics + video access + chart windowing)
**Generated:** 2026-08-10 (`/paul:discuss`, AskUserQuestion ×3 rounds, 11 questions)
**Status:** Ready for planning — **all open questions resolved**
**Predecessor:** Phase 59 (Segmenter Evaluation) — 5/5 plans complete 2026-08-09, pushed and
deployed (`6223a95` is on `origin/main`)
**Entangled with:** Phase 58 (Video Ground Truth) — **58-01 is uncommitted in the mobile tree and
58-04 is still owed.** See "Relationship to Phase 58" below; this is not background, it changes
what Phase 60 may safely do.
**Repo:** ⚠ **`swimnetics-mobile` ONLY** — a separate, user-owned git repo at
`C:\Users\TonyZheng\Desktop\swimnetics-mobile`. No file in `myswimcoach` is edited by this phase
except `CLAUDE.md` (see D1c). Nothing deploys to Railway or Vercel.

---

## Why now

The user opened this session with: *"This session will be dedicated to updating the mobile app."*
The app has had no UI work since Phase 55-01 (2026-08-05), while the web portal has taken Phases 57,
58-02, 58-03 and the whole of 59. The gap now shows in four places the user named, plus one they
did not.

The five asks, and what the code says about each:

| # | Ask | Verdict after reading the source |
|---|---|---|
| 1 | Advanced section → per-cycle line graphs | **Real gap.** `metrics_json.cycles` already stores 8 per-cycle series; mobile renders none of them. Web has `CycleCharts` + `CycleTable`. |
| 2 | Remove Data Quality | **Editorial, not a defect** — see "What I got wrong" below. |
| 3 | View video + velocity from the session card | **Real gap, structural.** Video is reachable exactly once, from the just-recorded state. |
| 4 | Rolling ~2 s window on the video page | **Buildable, no new dependency.** The hard part (playhead clock) already ships. |
| 5 | Replace pinch-zoom with a web-style window bar | **Real.** Must be hand-built — no chart library exists on mobile. |

And the one not asked for:

| P1 | **The report card's time axis is ~11% wrong.** Phase 52 fixed this on web and never touched mobile. |

---

## What was measured (2026-08-10, current source both repos)

### P1 — the sample-rate defect is mobile-only, and it is live

Commit `89205ca` (Phase 52-01, "Persist per-session sample rate") touched
`web/app/app/sessions/[id]/page.js`, `web/app/app/annotate/[id]/page.js` and
`web/components/portal/VelocityChart.js`. **It is a `myswimcoach` commit; the mobile repo was never
in its diff.** The two report-card files are near-mirrors:

```js
// web/app/app/sessions/[id]/page.js:120-123   ← FIXED
const fsHz = data?.sample_rate_hz > 0 ? data.sample_rate_hz : 100;
const time = useMemo(() => Array.from({ length: vel.length }, (_, i) => i / fsHz), [vel.length, fsHz]);

// swimnetics-mobile src/screens/ReportCardScreen.js:170   ← NOT FIXED
const time = Array.from({ length: vel.length }, (_, i) => i / 100);
```

`sample_rate_hz` appears **zero times** in the entire mobile `src/` tree.

The real rate is ~89.5 Hz (`decimate_signal` uses an integer factor: `round(268.5/100) = 3`,
`268.5/3 = 89.5`). Four on-screen consumers of that array, all wrong by the same ~11.7%:

| Consumer | Site | Effect |
|---|---|---|
| Velocity chart x-axis | `:459` | A 47.1 s swim is drawn as 42.2 s |
| Cycle-boundary dashes | `:176` (`idx/100`) | Misplaced against the trace |
| **Time-to-Distance** | `:480`, `:536` | Understated ~11% — 7.16 s shown for a true 8.0 s |
| CSV export | `:219` | Wrong timestamps |

**Time-to-Distance carries a second, compounding error.** `baseline_end_s` comes from
`metrics_json` in *true* seconds and is compared against the *fake* time array at
`ReportCardScreen.js:536` (`timeArr.findIndex(t => t >= baselineEndS)`), so the baseline index is
also wrong — not merely scaled.

**Unaffected, verified:**
- The `/process` path. `RecordScreen` uses `apiResult.time` straight from the server
  (`api.py:337` returns `t_dec.tolist()`), which is correct.
- Mobile `CompareScreen` — it compares metrics only and never touches a velocity profile.
- Web `CompareChart.js:28` still has `/100`, but that is the deliberate documented exception
  (two sessions may have two different rates).

⚠ **`CLAUDE.md` under-describes this.** Its "Sample rate" section records the iOS exception as
"iOS `ReportCardScreen.js` client-side CSV export". The CSV is one of four consumers; the chart,
the cycle overlay and Time-to-Distance are not mentioned. The note is not wrong so much as
incomplete in a way that made the defect look cosmetic.

### Ask #3 — video reachability is structural, not a missing button

- `VideoOverlay` is a Root-stack screen (`RootTabs.js:48`) reached from exactly one call site:
  `RecordScreen.js:960`, inside the `bleState === 'results'` branch.
- That call is gated on `videoUri && videoStartPhoneMs != null && sessionStartPhoneMs != null` —
  `videoUri` is a **local** file path from the camera.
- `VideoOverlayScreen.js:136` hard-returns an error state without it.
- **Nothing in the mobile app calls `GET /sessions/{id}/video-url`.** Nothing selects `video_path`.

So the footage is in the `videos` bucket and is unreachable from the phone the moment the user
navigates away. 58-01 added an `expo-media-library` save-to-camera-roll, which preserves the *file*
but not the *overlay*.

The backend side needs no work: `GET /sessions/{id}/video-url` (`api.py:1028-1054`) returns
`{url, origin_s}` in **one** call — signed for 3600 s, bytes never proxied through the API.

### Asks #4/#5 — no chart library exists, and the playhead clock already does

`package.json` dependencies relevant here: `react-native-svg` 15.15.4, `expo-video` ~56.1.4.
**No recharts (web-only), no victory, no `react-native-gesture-handler`, no slider.** Every chart in
the app is hand-rolled SVG driven by `PanResponder`. The web `<Brush>` cannot be ported; it must be
written.

But the expensive half of #4 is already solved and shipped. `VideoOverlayScreen.js:65-85` polls
`player.currentTime` at 20 Hz on a `setInterval`, with a comment explaining why polling beats
`expo-video`'s `timeUpdate` event — the event only fires during playback, so scrubbing while paused
would leave the marker stale. That reasoning transfers unchanged to a rolling window.

What is missing is a single seam: `VelocityChart` derives its visible range from **internal**
`zoomWindow` state (`:32`, `:105-106`) that no parent can write.

**Three performance details that decide whether #4 feels smooth** (none are blockers; all are
invisible until run at 20 Hz on a device, which is why they belong in the plan and not in apply):

1. **A 2 s window would render ~17 points.** Downsampling to 400 happens over the *whole* trace
   first (`:87-91`), so a 2 s slice of a 47 s trace keeps `400 × 2/47 ≈ 17`. Resample *within* the
   window instead.
2. **The y-axis would jitter 20×/second.** `vMin`/`vMax` are taken from the visible slice
   (`:107-108`). Pin the y-scale to the full trace whenever a window is active.
3. **No memoization anywhere in the component.** It re-walks the full sample array and spreads ~400
   arguments into `Math.min`/`Math.max` on every render. Fine at 1 render; wasteful at 20 Hz.

**Latent gesture bug, relevant to #5:** `onStartShouldSetPanResponder: () => false`
(`VelocityChart.js:46`) means a plain tap never grants the responder, so the double-tap-to-reset-zoom
at `:60-65` only fires if the user *drags* twice. Part of why pinch feels bad. It dies with pinch.

### `ramp_up` is load-bearing, not cosmetic — read this before touching cycle counts

`metrics.py:841-854` tags every cycle `steady` or `ramp_up`:

```python
steady_floor = 0.50 * np.percentile([vel[c["peak_idx"]] for c in cycles], 75)
phases_raw   = [vel[c["peak_idx"]] >= steady_floor for c in cycles]
# then: an isolated ramp_up sandwiched between two steady cycles is promoted to steady
```

Intent: after dive → pulldown → breakout the first strokes are not at pace, and would drag every
average down while inflating every CV.

**The tag drives every session-level number.** `ss_cycles` (`:892`) feeds:

- `stroke_count = n_ss` — ⚠ **the stroke count on the report card is the STEADY count, not the
  total number of cycles in `metrics_json.cycles`**
- `stroke_rate_spm` = 60 ÷ mean steady `duration_s`
- every `mean_*` and `cv_*`, including all four series D2 charts
- `fatigue_index_pct` (its q1/q4 are quarters of the *steady* cycles, `:928-932`)

Vestigial detail that can mislead a reader: `detect_phases` returns `steady_start`, which is just
an alias for `baseline_end` (`metrics.py:57`, `:80`). Ramp-up is decided **per cycle**, never at a
time boundary.

⚠ **D8 removes ramp-up from the DISPLAY only.** Removing the concept from `metrics.py` would move
`stroke_count`, `stroke_rate_spm` and every mean/CV on every session past and future — a fourth
comparability break on top of Phase 57's, 59-03's and 59-05's. It was raised with the user and is
explicitly **out of scope**.

### Relationship to Phase 58

Phase 58 = *Video Ground Truth (solo capture + annotate-from-video)*. Trigger: labeling the
19-session batch proved freestyle/backstroke arm entries are not reliably discernible from the
velocity trace alone (3–4 of 10 freestyle sessions unlabelable), so the swims must be filmed.

| Plan | What | State |
|---|---|---|
| 58-01 | iOS auto-stop (20 s default, editable, countdown) + save-to-camera-roll + `flex:1` video layout | ✅ **approved on assumption, NEVER device-verified** |
| 58-02 | Web annotate: Breakout retired, video height-capped, frame-step + speed control, mark-at-playhead | ✅ |
| 58-03 | Web report card: stroke gate removed, `pageshow`/`focus` refetch, `recomputed_from_annotation` surfaced | ✅ |
| **58-04** | **`VideoPane` end-anchor (compute origin client-side on web)** | ⬜ **OWED** |
| 58-05 | Web session cards: auto-titles + Annotated / 🎥 Video / ⚠ Quality chips | ✅ |

Two consequences Phase 60 must respect:

1. **58-01 is the uncommitted work in the mobile tree** (see "Blocking on entry"). Its auto-stop has
   never fired against real hardware.
2. **58-04 being owed is why D11 matters.** `VideoOverlayScreen` is currently the *only* thing in
   the entire system that ever writes `video_origin_s`; a record-with-video session never opened
   there reaches the web at `origin_s = 0`, silently unsynced. Phase 60 adds a **second** entry
   point to that screen. That makes the manual workaround easier but does **not** substitute for
   58-04 — and it means exactly one of the two entry points may be allowed to write.

58-05 also built and *verified* a `qualityIssue` helper on web (strips the always-present kick
warning; flags dropout > 5%; kick-only → `null`, 6.2% → flagged, 3.0% → `null`). **D9 is the mobile
mirror of that helper, not a new invention.**

### What I got wrong on first read, corrected

- **Data Quality is not reading phantom keys.** I suspected `total_cycles_raw` /
  `implausible_cycle_count` were absent from the contract because `CLAUDE.md`'s documented
  `data_quality` key set omits them. They are genuinely populated — `api.py:199-205` builds a
  **richer** object than the one `metrics.py` returns, and `api.py:897` carries three of those keys
  across annotation recompute. The card works. Removing it is a judgement about usefulness.
- **The warning styling is fine.** `colors.ok` is `#d4860a` — amber, the middle rating band, not
  green. `DataQualityCard`'s warn rows and `ReportCardScreen`'s `unreliableWarn` are correctly
  cautionary.

---

## Goals

1. **Correct the report card's time base** to the session's real sample rate, at full parity with
   what web already does. (D1)
2. **Replace the Advanced section's scalar grid with per-cycle line charts** for the four series
   the user named, correctly translated. (D2)
3. **Remove the Data Quality card**, keeping only a magnet-dropout strip above 5%. (D3, D9)
4. **Make video + velocity reachable from any saved session**, not only from the just-recorded
   state. (D4)
5. **Give the video page a short, adjustable window that follows the playhead.** (D5)
6. **Replace pinch-to-zoom on the report card with a draggable window bar.** (D6)
7. **Stop hiding the Efficiency block** when `cv_isi > 0.80` — banner instead of blackout, on both
   screens that carry the gate. (D10)

Explicitly **not** goals: touching `metrics.py` (D8), adding a provenance/segmentation marker (D9),
or writing `video_origin_s` from the new read path (D11).

---

## Decisions

### D1 — Sample rate: full parity with web
**User choice.** Select `sample_rate_hz` on the report card, derive one `fsHz`, and use it for all
four consumers: the time array, the cycle-boundary overlay, Time-to-Distance and the CSV export.

- `NULL → 100`, matching `web/app/app/sessions/[id]/page.js:120`, `api.py:_session_fs` and
  `annotations.FS_HZ`. **Do not backfill** — NULL means "predates Phase 52", and 100 reproduces
  exactly how those rows have always rendered.
- **D1c:** correct the `CLAUDE.md` "Sample rate" section, which currently names only the CSV export
  as the iOS gap. This is the one `myswimcoach` file this phase touches.

### D2 — Per-cycle charts: DPS, Coast, Duration, Arm peak
**User choice** (multi-select; Trough / Impulse / Dead-spot all declined).

| Chart | Per-cycle key | Caption |
|---|---|---|
| Distance per stroke | `dist_m` | mean = `session.mean_dps_m` |
| Coast | `coast_fraction` | mean = `session.mean_coast_fraction` |
| Cycle duration | `duration_s` | **`cv_isi`** — the dispersion of *this* series |
| Arm peak velocity | `arm_peak_vel` | **`cv_arm_peak_vel`** — the dispersion of *this* series |

⚠ **The translation matters and was explicitly confirmed with the user.** The ask named "isi cv"
and (implicitly) arm-peak CV as chartable series. **They are not per-cycle quantities** — there is
no "ISI CV of cycle 4". They are the coefficient of variation *of* `duration_s` and `arm_peak_vel`
across cycles. Charting the underlying series and captioning it with the CV shows the scatter the
number summarizes. Do not invent a per-cycle CV.

All four keys are already in `metrics_json.cycles` — **no backend work, no new endpoint, no schema
change.** Charts plot **all** cycles, not just steady ones — see D8.

### D3 — Remove the Data Quality card
**User choice**, reason given: "outdated". Delete the `<DataQualityCard>` usage from
`ReportCardScreen`. One piece survives — see D9.

Why "outdated" is accurate: three of the card's four stats are segmentation-derived and Phase 59
replaced the segmenter for every stroke. The `implausible_cycle_count` rails are `0.5 < duration <
4.0 s`, whose own comment reads *"physically reasonable **breaststroke** range"* (`metrics.py:961`) —
written in Phase 10 (2026-05-25), never revisited for the freestyle-heavy corpus now being recorded.

### D4 — Video from the report card, via signed URL
**User choice** (list-row glyph, both-surfaces, and local-file-only all declined).

- Report card selects `video_path` + `video_origin_s`; render a `▶ Video + Velocity` button only
  when `video_path` is present.
- On tap, call `GET /sessions/{id}/video-url` → `{url, origin_s}` and push `VideoOverlay` with the
  remote URL.
- Works from any device for any session — the phone that recorded it need not be the phone viewing
  it. No backend change.

### D5 — Video window: preset buttons, default 2 s, auto-following
**User choice** (slider and pinch-sets-length both declined).

- Presets **1 s / 2 s / 5 s / All**, default 2 s. The trace scrolls through a fixed window as the
  video plays; the playhead drives the window position.
- **No new dependency.** React Native dropped its built-in `Slider` at 0.60, so a continuous slider
  would mean `@react-native-community/slider` — a native module, therefore a new EAS build before it
  could even be tested. Presets also match the idiom already on that page (the ±0.1/±0.5 s nudge row
  at `VideoOverlayScreen.js:180`).

### D6 — Report card: brush bar, pinch removed
**User choice** (keep-pinch-too and snap-to-cycle both declined).

A full-trace strip beneath the chart with two draggable end handles (length) and a draggable body
(position) — the web `<Brush>` pattern, hand-built in SVG. Pinch-to-zoom, its pan-when-zoomed
branch, and the dead double-tap reset are all deleted.

### D7 — One primitive, two drivers
**Derived from the user's correction:** *"4 and 5 are different."* They are. #4 is
**auto-following, length-adjustable, position driven by the video**. #5 is **manual, length- and
position-adjustable by hand**.

They share exactly one thing: "render only `[tStart, tEnd]`". So `VelocityChart` gains a
**controlled** `window` prop, and the two callers drive it differently. Do not build two chart
components, and do not try to make one driver serve both.

### D8 — Charts plot all cycles, with no ramp-up distinction
**User choice** — *"I no longer need that"*, resolved as **display-only** (steady-only plotting and
hollow-dot marking were both offered and declined).

Every cycle in `metrics_json.cycles` is drawn identically. **`metrics.py` is not touched** — the
`steady`/`ramp_up` tag keeps driving every session-level number exactly as it does today.

⚠ **Two mismatches are now accepted, deliberately, and the plan must not "fix" them:**
1. The chart shows **more dots than `stroke_count`** reports, because `stroke_count` is the steady
   count (`metrics.py:906`).
2. A "mean" reference line **will not sit at the visual average of the plotted dots**, because the
   mean is over steady cycles only.

Consider whether the caption should say so in a few words. Do not renumber, filter or hide cycles
to make the numbers line up.

### D9 — One dropout strip survives the Data Quality removal
**User choice** (delete-everything and dropout-plus-`segmentation_reliable` both declined).

Keep a single amber line, rendered **only** when `magnet_dropout_pct > 5`. Everything else in the
card goes.

Rationale: dropout is the one stat that never touches the segmenter. It is computed in
`api.py:150-160` straight from the raw CSV's `magnet_ok` column — the fraction of samples where the
AS5600 failed its I²C read (magnet misaligned, wheel wobbling, connector loose). It is hardware
truth, and the visible product of a real firmware fix: `angle == 4095` used to pass through as valid
data until `readAngle()` began error-checking and flagging `magnet_ok = 0`.

**Mirror 58-05's verified web helper**, including its threshold and its deliberate stripping of the
always-present kick warning (`api.py:180` appends that one unconditionally, so any naive
`warnings.length > 0` check flags every session and carries zero information — a trap 58-05 caught
at plan time).

### D10 — The `cv_isi > 0.80` gate becomes a banner, on BOTH screens
**User choice** (keep-as-is and drop-entirely both declined).

Today `efficiencyUnreliable` (`ReportCardScreen.js:184`) replaces the entire Efficiency block with
*"Stroke detection may be unreliable for this session"* (`:399`). Instead: **always render the
charts, and move the warning to a banner above them.**

Rationale: ISI CV above 0.80 means cycle durations vary by more than 80% of their mean — implausible
for a swimmer holding a stroke, so it is a segmenter-failure detector wearing a swimmer-metric
costume. The per-cycle chart shows *exactly the scatter that made it fire* (durations of 0.9, 1.0,
**0.4**, 1.1, 0.95 s read instantly as one bad cycle); the scalar cannot. The gate was suppressing
the one view that explains itself.

⚠ **The same gate exists twice.** `RecordScreen.js:128` carries an identical
`efficiencyUnreliable` for the just-recorded path. **Apply D10 to both** or the two screens will
disagree about the same session. This is the only reason `RecordScreen.js` is in scope.

### D11 — Never overwrite an existing origin  ⚠ AMENDED 2026-08-11
**Original user choice** (fully-read-only and always-recompute-and-post both declined) was worded
*"the read path never auto-writes"*. **Amended during 60-03 apply, prompted by the user asking why
two entry points behave differently at all** — *"I think I want a single destination… would that
make it simpler?"*

The original wording over-reached. What D11 was protecting is a **good stored value**, not the act
of writing. Restating it as one rule covers every case with no per-screen branch:

> **Use the stored origin if there is one. Otherwise compute it and save it.**

| Entry point | stored origin | behaviour | note |
|---|---|---|---|
| Record screen | always null | compute, save | unchanged from today |
| Report card, previously synced | exists | use it, never write | fixes the overwrite hazard |
| Report card, never synced | null | compute, save | closes 58-04's symptom; nothing to destroy |
| Nudge, either screen | — | always saves | deliberate action; the only phone-side repair |

**What this removed:** the planned `allowOriginWrite` route param, its branch, and the "which screen
am I" concept. `VideoOverlayScreen` takes one new param (`storedOriginS`) and no flag.

⚠ This does **not** retire 58-04 — that is web work on `VideoPane`, and the annotate page still
cannot compute an origin of its own.

- **Playback origin:** use the `origin_s` returned by `GET /sessions/{id}/video-url`; fall back to
  the end-anchored recompute (`deviceDuration − videoDuration`) only when it is null.
- **Writes:** the report-card entry path must **not** auto-post. Guard
  `VideoOverlayScreen.js:120-125`, which currently posts once as soon as origin becomes known.
- **Manual nudges still save** from either path — a nudge is a deliberate user action, and it is
  the only way to repair a bad stored origin from the phone. The debounced re-post at `:128-134`
  stays.

Why this matters: a recompute-and-post on the read path would silently overwrite a stored origin
that already carries a nudge the user dialled in — good data replaced by worse, the same defect
shape Phases 51, 52, 57 and 58 each turned up.

⚠ **Ordering dependency: D1 must land with or before D4.** Before the sample-rate fix,
`deviceDurationS` on the report-card path derives from the `i/100` array, so any recomputed origin
would itself be ~11% short.

---

### D13 — A user-dropped start marker for Time to Distance  ⚠ ADDED 2026-08-11
**User request mid-apply**, with the reason stated plainly: *"Just like how user can scrub the trace
to look at exact velocity at time — add ability to drop a marker as starting time. **I don't trust
auto detect baseline.**"*

Scrub the velocity chart, tap "Start at X.XX s", and Time to Distance measures from there instead of
`baseline_end_s`. A green START line marks it; "Use auto" reverts.

- **Per session, on the report card, IN-MEMORY ONLY** (user choice; DB-persisted and per-athlete
  were both offered and declined). No schema change, no PATCH, nothing sent to the server — so the
  marker is lost on leaving the screen, deliberately.
- **No maths changed.** `computeTimeToX` already takes the start as a parameter; the call site
  passes `startTimeS ?? baseline_end_s`.
- ⚠ The parent's copy of the scrub time must outlive the chart cursor's 2-second fade, or the
  control goes dead before the user can reach it.

⚠ Worth noting for a later phase: this is the *third* place a human start time exists, alongside
`detect_phases`' auto `baseline_end` and the annotation contract's human `dive_start_s`. They are
not connected, and the user's stated distrust of auto-detection is an input to Phase 53.

### D14 — Label the Video Overlay controls  ⚠ ADDED 2026-08-11
The window presets and the sync nudges were two unlabelled rows of near-identical pills, and the one
caption sat *below the second row*, so it read as belonging to both. Each row now carries a
left-hand label (`WINDOW` / `SYNC`) — no vertical cost, since the video is `flex: 1` — and the
readout says what it shifts.

### D15 — Fix rolling-window shimmer  ⚠ ADDED 2026-08-11
`resampleWindow` anchored its stride to the *window's* start index, so on a rolling window the
sampled lattice slid with the window and consecutive frames drew different neighbouring samples.
Measured at span 5 s: **two lattice phases alternating**. Anchored to absolute index 0 → **one,
stable**. Spans 1 s and 2 s were already stable (stride 1), which matters — see below.

⚠ **A second cause of the reported "dancing" is diagnosed but NOT fixed.** Since 1 s and 2 s
resample provably stably, any remaining jitter at the default 2 s has a different cause. Leading
hypothesis, unverified without a device: `player.currentTime` wobbling between polls, which moves a
playhead-centred window ±2 px at 20 Hz. Diagnostic recorded in 60-03-PLAN; the fix would be to
advance the window on a monotonic clock. Not speculatively changed, because it has not been measured.

## Constraints and risks

### ⚠ BLOCKING ON ENTRY — the mobile working tree is dirty with unverified Phase 58-01 work

```
 M ios/mobile/Info.plist
 M package-lock.json
 M package.json
 M src/screens/RecordScreen.js
 M src/screens/RecordingConfigScreen.js
 M src/screens/VideoOverlayScreen.js
?? src/lib/autoStopPrefs.js
```

`RecordScreen.js` and `VideoOverlayScreen.js` are both files Phase 60 will edit. Two problems:

1. The diff becomes unreadable — 58-01's changes and 60's would be indistinguishable.
2. **58-01 was approved on assumption, not on device evidence** (ROADMAP: *"assume 58-01 is
   working. approve it."*). Its auto-stop has never fired against real hardware. If the Phase-60
   EAS build misbehaves, the cause is ambiguous between the two phases.

**Commit 58-01 before starting 60.** This is a git action for the user — it is their repo.

### EAS build economics
Builds are paid and there is no Mac. **Everything in this phase must land in one build.** This is
the main argument for bundling D1 with the UI work rather than shipping it as its own phase (an
option the user was offered and declined for exactly this reason).

### No test infrastructure on mobile
`package.json` has no `jest`, no `test` script. Verification precedent from 58-01: `npx expo export`
exit code + running extracted pure helpers in `node` + a device build.

**Therefore: extract the windowing math as pure functions** (window clamping, in-window resampling,
brush-handle → time mapping) so they can be executed in node without a device. 58-01 set this
precedent with `clampAutoStopS`.

### Per-cycle charts will expose the segmentation transition
37 stored sessions carry pre-Phase-59 segmentation; 16 of those are annotation-derived and must
never be overwritten. The charts will faithfully render whatever is stored, so old and new sessions
will visibly differ in cycle count and per-cycle shape for the first time. **This is not a bug and
must not be "fixed."**

⚠ Do not resolve this by adding a provenance marker. The user was offered
`segmentation_reliable` alongside the dropout strip and **declined it** (D9). If the transition
needs acknowledging at all, a caption is the ceiling.

### Chart width is not rotation-aware
`VelocityChart.js:26` computes `W = Dimensions.get('window').width - 48` at render with no dimension
listener. Pre-existing; the brush bar inherits it. Out of scope unless it becomes a problem.

---

## Open questions

**None.** The four carried out of the first discussion round were all resolved by the user on
2026-08-10: OQ-1 → **D9**, OQ-2 → **D8**, OQ-3 → **D10**, OQ-4 → **D11**. Each was decided against
a stated recommendation and the alternatives were explicitly declined; see those decisions for what
was rejected and why, so the plan does not relitigate them.

Two things the plan should *notice* rather than decide:

- D8 knowingly accepts two visible mismatches (dot count vs `stroke_count`; mean line vs visual
  average). Wording the caption is a plan-time detail, not a reopened question.
- D10 touches `RecordScreen.js`, a file 58-01 has uncommitted changes in. That is a sequencing
  constraint, not an open choice — see "Blocking on entry".

---

## Metric definitions (user asked; recorded here so the UI copy is right)

All three read **steady-state cycles only** (`metrics.py:892`).

**Coast** — `coast_fraction`, `metrics.py:877-880`. Fraction of each cycle spent below **50% of
that cycle's own `arm_peak_vel`**. Self-normalizing, so it is comparable across swimmers, speeds and
sessions — and, unlike `dead_spot_s`, it did **not** move in Phase 57's v95 change or 59-03's window
change. Reads as "share of the stroke not near your own top speed". The name oversells it: it
measures *not accelerating*, not *gliding well*.

**ISI CV** — `cv_isi`, `metrics.py:922`. ISI = one cycle's `duration_s`; CV = std ÷ mean across
steady cycles. **Rhythm consistency**: 0% metronomic, higher = ragged tempo. Dimensionless, so a
sprint and a 200 pace compare directly. ⚠ Above 0.80 the app currently hides the whole Efficiency
block — at that level it is as likely to be a segmenter failure as a swimmer failure.

**Arm Peak CV** — `cv_arm_peak_vel`, `metrics.py:920`. std ÷ mean of each cycle's peak pull
velocity. **Power consistency.** Distinct from `fatigue_index_pct`, which is *directional* (first
quarter vs last quarter, `:928`); Arm Peak CV is *undirected scatter*, so a swimmer alternating
strong and weak pulls scores badly here and clean on fatigue.

---

## Files in scope

**`swimnetics-mobile` (the only repo that ships):**

| File | Change |
|---|---|
| `src/screens/ReportCardScreen.js` | D1 (fsHz ×4 consumers), D2+D8 (charts replace scalars), D3+D9 (card out, dropout strip in), D4 (video button), D10 (gate → banner) |
| `src/components/VelocityChart.js` | D6 (brush bar, pinch removed), D7 (controlled `window` prop), perf fixes |
| `src/screens/VideoOverlayScreen.js` | D5 (window presets, playhead-driven), D4 (accept remote URL), D11 (origin precedence + auto-post guard) |
| `src/screens/RecordScreen.js` | **D3 + D9 + D10** — see the correction below. ⚠ 58-01 has uncommitted changes in this file |
| `src/components/CycleCharts.js` | **NEW** — four small SVG line charts |
| `src/components/DataQualityCard.js` | D3 — delete the component; **two** import sites, not one |

⚠ **CORRECTION found at plan time — `DataQualityCard` is rendered on BOTH screens**, not just the
report card: `ReportCardScreen.js:9`/`:492` **and** `RecordScreen.js:17`/`:954`. Deleting the
component without touching `RecordScreen` would break the just-recorded results view. So
`RecordScreen.js` is in scope for **three** decisions (D3 removal, D9 dropout strip, D10 banner),
not the one D10 originally named. Both screens must end up showing the same thing.
| `src/lib/chartWindow.js` | **NEW** — pure windowing math, runnable in node |

**`myswimcoach`:** `CLAUDE.md` only (D1c).

---

## Success criteria

- Report card time axis, cycle overlay, Time-to-Distance and CSV all use the session's real rate;
  a pre-Phase-52 (NULL) session renders byte-identically to today.
- Advanced shows four per-cycle line charts, all cycles plotted, each stating its mean or CV.
- Data Quality card gone; a dropout strip appears **only** above 5% and is verified against both
  sides of that threshold plus the kick-only case.
- A session with `cv_isi > 0.80` shows charts **plus** a warning banner — on the report card *and*
  the record screen, agreeing with each other.
- A saved session with video shows a working `▶ Video + Velocity` button that streams from the
  signed URL, plays at the **stored** origin, and leaves `video_origin_s` unchanged in the DB
  unless the user nudges it.
- Video page shows a following window, default 2 s, switchable to 1/5/All.
- Report card chart has a draggable window bar; pinch is gone.
- `metrics.py` untouched; `stroke_count`, `stroke_rate_spm` and every mean/CV are byte-identical
  before and after.
- `npx expo export` exits 0; pure helpers pass in node; one EAS build verifies on device.

---
*Discussed 2026-08-10 via `/paul:discuss`. AskUserQuestion ×3 rounds (11 questions). All eleven
decisions D1–D11 are user choices; no open questions remain.*
