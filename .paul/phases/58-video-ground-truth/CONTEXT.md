# Phase Context

**Phase:** 58 — Video Ground Truth (solo capture + annotate-from-video)
**Generated:** 2026-08-05
**Status:** Ready for planning
**Predecessor:** Phase 57 (Annotation Workflow) — 57-01 closed, 57-02 applied + deployed, **checkpoint still open**

---

## Why now

Phase 57 shipped an annotation tool that assumes the coach can read stroke boundaries off the
velocity trace. **Labeling the 19-session batch proved that assumption false for alternating
strokes.** User, 2026-08-05:

> "Butterfly and breaststroke is easy enough — label the troughs. But freestyle and backstroke —
> it's almost impossible to discern when does one stroke start and ends… for 3-4 of the freestyle
> swims, it's extremely jumbled together."

Some freestyle traces are cleanly periodic and some are mush. Both were supplied as screenshots and
both are real sessions. The 19 collected sessions have **zero video** (verified 2026-08-05 by
read-only Supabase query — the only video in the last 30 rows is a 2026-07-20 session), so nothing
can be recovered retroactively.

A tripod + video test is scheduled for **2026-08-06**. This phase prepares for it.

**Operator model — this drives everything.** The user is testing **solo**: the swimmer *is* the
operator. Phone goes on a tripod, they start, dive, swim 25 m — and today they must swim back to
press stop, appending 20–30 s of dead tail to both the velocity trace and the video.

---

## Repo-verified starting conditions

Checked against the code, not assumed. Several contradict the framing of the request — in the
user's favour.

1. **The camera is already built, shipped, and device-verified.** `RecordScreen.js:473-580` is a
   complete one-tap "Record with Video": `expo-camera` mounts, the race-start cue plays over the
   live preview, `writeCmd('START')` fires on the blare, `videoStartPhoneMs` is stamped at the
   `recordAsync()` call. `src/lib/videoUploadQueue.js` uploads in the background (FIFO, 2 retries,
   survives screen unmount and app backgrounding). Backend `POST /sessions/{id}/video` +
   `GET /video-url` exist. **47-03 was device-verified in the Phase-55 EAS build 2026-08-05.**
   The 19 have no video because video mode was not used that day.

2. **Web annotation already reaches iOS — for metrics.** `PUT /annotations` recomputes and rewrites
   `sessions.metrics_json` (47-04); `ReportCardScreen.js:94-95` selects `metrics_json` fresh from
   Supabase on every open. **No work required.** What does *not* cross over is the marks themselves —
   iOS renders numbers, never boundaries. Out of scope unless asked.

3. **Chart↔video scrubbing already works in both directions.** Chart click → `seekRef.current?.(tt)`
   seeks the video (`web/app/app/annotate/[id]/page.js:128`, gated by `seekEnabled={!!video?.path}`);
   video playback/scrub → `onPlayhead` → `playheadS` → chart marker. **The missing direction is
   marking:** marks land where you click the *chart*. There is no "place a mark at the video's
   current time", which is the only interaction that matters when reading arm entries off footage.
   Both halves already exist in the page — `playheadS` at `:48` and the mark-placing function — so
   this is wiring, not new machinery.

4. **`video_origin_s` only reaches the server from the Video Overlay screen.**
   `VideoOverlayScreen.js:92-125` computes the end-anchored origin
   (`deviceDuration − videoDuration`) and auto-POSTs it once the video duration loads. The
   background upload queue **sends the file only**. So a record-with-video session that is never
   opened in Video Overlay arrives on the web with `origin_s = 0` — unsynced, silently.

5. **The end-anchor is sound but has one silent failure mode.** Its premise (stated in its own
   comment) is that camera and device stop on the same tap. `stopVideoRecording` does
   `cameraRef.stopRecording()` then `await writeCmd('STOP')`, and **a failed STOP is caught as
   non-fatal** — correct for the data, but the device keeps recording. `deviceDuration` inflates by
   however long reconnection takes, and the origin is wrong by exactly that much — then auto-posted.
   Same silent-plausible-corruption shape as Phases 51/52/57. **Auto-stop removes this**: both the
   camera and the STOP write fire off one timer, which is precisely the premise the anchor needs.

6. **Buffer-and-dump makes the swim BLE-free — user's recollection confirmed.**
   `ESP_32_V5.ino:520-529` `onDisconnect` cancels pending meta/dump/status, restarts advertising,
   and deliberately leaves `recording` alone: *"Recording is independent of the connection in buffer
   mode — keep going."* `dumpBuffer` aborts on disconnect but **retains** the buffer (`:474-480`).
   BLE is required at exactly two moments — START, and STOP + dump.

7. **Buffer-full truncates, never wraps** (`:759-766`): sampling stops, `dataReady = true`, error
   LED, data kept. You lose the tail, never the start.

8. **No BLE auto-reconnect.** `BleContext.js:94-98` registers `onDisconnected` and sets status to
   `'disconnected'`. No retry, no rescan — reconnection is manual.

9. **`expo-dev-client` is installed; `expo-updates` is not.** A development build loads JS changes
   off the Metro dev server with no EAS build. A TestFlight build would need a paid EAS build plus
   queue time. **Which build is on the phone decides whether the iOS work lands before the pool.**

10. **Optics: distance is not the constraint.** iPhone main ≈ 70° HFOV → frame width ≈ 1.4 × distance.
    At 25 m that is ~35 m wide: 55 px/m at 1080p, 111 px/m at 4K. A 0.4 m hand-entry splash is
    22–44 px and left-vs-right entry separation (~0.45 m) is 25–50 px. Adequate. The real risks are
    **angle, glare and occlusion** — a deck tripod at the block sits ~1.8 m above the water, so the
    depression angle at 25 m is ~4°, which maximises specular glare and puts the head, bow wave and
    kick plume between camera and entry point. **Untested. This is the phase's one genuine unknown.**

---

## Goals

1. **Make solo capture viable** — the swimmer must not have to swim back to stop the recording.
2. **Make video sync land without a per-session detour**, and without depending on a promptly
   delivered STOP.
3. **Make annotation driven by the footage** — scrub the video to an arm entry, mark it there.
4. **Answer whether a tripod angle is legible at all**, before any of this is treated as settled.

---

## Decisions (user, 2026-08-05)

### D1 — Auto-stop, default **20 s**
User: *"auto stop with 20 second default - trust me."* Confirmed against their own data rather than
taken on faith: the two supplied traces run **18.93 s** and **16.53 s** end to end, and in both the
velocity has returned to zero *before* the recording ends (~18 s, ~16 s). 20 s clears both with ~1 s
and ~3.5 s of margin. A 15 s default would have clipped both finishes; 30 s was over-cautious.

Must be **editable** and must show a **live countdown** on the record screen — unlike buffer-full
(which truncates safely and keeps what it has), a too-early auto-stop genuinely loses the end of
the swim.

### D2 — Capture path: existing one-tap video mode
Chosen 2026-08-05 (AskUserQuestion). The phone is both camera and BLE recorder, so the origin is
computed exactly and no manual alignment is needed. **Held provisional**: it structurally pins the
tripod near the block (BLE range to the block-mounted encoder), which is the shallow rear angle and
the one most exposed to glare and occlusion. If the legibility test fails, the capture decision
reopens — a second camera on a tripod already works with zero code via `VideoPane`'s file input +
±0.1 s nudge, eye-synced to the dive spike.

### D3 — Purpose: lab now, product later
Video is an instrument for 16-06 ground truth and the Phase-53 GO/NO-GO first. The capture protocol
should not foreclose a product version, but product-grade capture UX is not this phase.
**Named cost:** with the phone as camera, a coach holds it for every trial — a real operator burden
against Phase 53's 30-swimmers-in-an-hour target, and the most likely reason the product version
later moves to a tripod.

### D4 — The 19: annotate what's legible, flag the rest
Mark the clean sessions; record the 3–4 jumbled freestyle as *not annotatable* rather than guessing.
Requires vocabulary that does not exist — today, absence of an annotation conflates *not yet done*
with *cannot be done*, the same failure mode 57's CONTEXT identified for null markers. Must be
exportable so 16-06 can exclude or downweight it.

### D5 — No IMU or on-swimmer sensor
User's own assessment, confirmed: second wireless device, second clock, sync protocol, waterproof
enclosure, attachment — and it contradicts PROJECT.md's *"swimmer just swims."* A camera touches
nothing.

---

## Risks accepted

**R1 — Tripod legibility is unverified.** Pixels are sufficient; angle, glare and occlusion are not
characterised. Cheapest possible resolution, and it needs **no encoder, no BLE, no app**: film one
freestyle 25 from three positions (block, far end, highest seat available) on any phone and try to
mark entries off the footage on a laptop. That also reveals whether the good angle is somewhere BLE
cannot reach — which is the fact that would retire D2.

**R2 — Arm identity may not survive the rear angle.** Acceptable without changing the contract:
Phase 57's CONTEXT (R1) already states the marks record **alternation timing, not verified arm
identity**. Footage only has to establish *that* an entry happened and *when*.

**R3 — Auto-stop cuts a slow swim.** Mitigated by editability + countdown, not eliminated.

---

## Approach notes

- **iOS** (`swimnetics-mobile`, separate repo): auto-stop preference mirroring
  `src/lib/startSequencePrefs.js` (SecureStore get/set pair), a timer armed at START, wired into
  **both** stop paths (`stopRecording` and `stopVideoRecording`), Settings field, countdown on the
  record screen. Pure JS — no native module, so a dev build needs no EAS round trip.
- **Web** (`web/`): `VideoPane` computes the end-anchor itself when no origin is stored (it already
  has the video element's `duration`, and the page already has `duration_s` from `GET /annotations`),
  removing the per-session Video Overlay tap; annotate page gains mark-at-playhead + keybinding.
- **Deploy asymmetry drives sequencing.** Web is a Vercel push. iOS needs a build on the phone.
  The iOS half is the only thing that must exist before the pool; the web half is needed when
  annotating, which is after.
- **Keep the two halves in separate plans** — different repos, different urgency, different deploy
  paths. Consistent with how 57 was split.

---

## Out of scope

- IMU or any on-swimmer sensor (D5).
- Retroactive video for the 19 — impossible, no footage exists.
- Rendering annotation marks on iOS (metrics already cross over; boundaries are a real build with
  no stated consumer).
- Product-grade capture UX — mounts, framing guides, throughput for 30 swimmers (D3).
- Pose estimation or auto-labeling from footage. Also excluded by 57's D7 (no auto-assist), and
  seeding from a detector is the circularity D6 exists to prevent.
- Multi-angle / multi-camera capture.
- BLE auto-reconnect (finding 8) — real, but not triggered by the solo tripod setup, where the
  phone and the encoder are both stationary and adjacent.
- Firmware changes of any kind.

---

## Open questions for planning

1. **Which build is on the phone** — dev client or TestFlight? Decides whether auto-stop ships
   before the pool session or after. Blocking for scheduling only, not for design.
2. Does auto-stop count from START (the blare) or from first buffered sample? START is the obvious
   anchor; the firmware's 150–300 ms variable warmup means they are not identical.
3. Should a failed `writeCmd('STOP')` mark the resulting `video_origin_s` untrustworthy, or is
   auto-stop sufficient mitigation on its own? (Finding 5.)
4. Where does D4's "not annotatable" flag live — the annotation doc (`annotations.py` contract +
   validate + export) or a session column (needs a hand-applied SQL patch)?
5. Sequencing against 57-03 (the annotation queue) — both touch the annotate page.

---

## Blocking on entry

**57-02's human-verify checkpoint is still open, and 57-02 is already deployed.** Phase 58 edits the
same annotate page. If 58 starts first, any defect found at that checkpoint becomes indistinguishable
from a 58 regression. Verify 57-02 before the web half of this phase begins — it is one browser
session.

> **RESOLVED 2026-08-07** — 57-02's checkpoint was approved on the deployed portal (all 7 ACs pass;
> see `57-02-SUMMARY.md`). The gate on the web half is lifted. What remains open from 57-02 is **R1**
> — whether ~40 arm-entry marks are placeable from the trace alone was never reported — and the
> amendment below is the direct consequence of trying: they are not, which is why the video has to be
> readable at the same time as the chart.

---

# Amendment — 2026-08-07: annotate-page usability + Breakout removed

Raised after the first real attempt to annotate with video open. Two changes, both landing in the web
half (58-02). Discussed via `/paul:discuss`, AskUserQuestion ×7.

> "I want to improve the annotation process. Right now the video is too big — meaning I can't view
> both the graph and the video at the same time."
>
> "Also I think I'll just remove the 'breakout' aspect. I'll simply say that the first stroke cycle
> will be special because it contains breakout."

## Why these two, and why now

Goal 3 of this phase is *"make annotation driven by the footage."* Neither request is polish against
that goal — the first is a hard blocker (you cannot mark an arm entry off footage you cannot see next
to the trace you are marking), and the second removes a marker the user has already stopped placing
in practice.

## Repo-verified, not assumed

1. **The video overflow is structural, not a style nit.** `page.js:337` sets `max-w-5xl` (1024 px) and
   `:361` splits it `[1fr_300px]`, so the chart column is ~700 px. `VideoPane.js:143` renders the
   `<video>` at `className="w-full …"` with **no height constraint of any kind**. 16:9 footage in that
   column is ~394 px tall; **portrait 9:16 is ~1244 px**. `AnnotationChart`'s default `height` is 340.
   Nothing bounds the sum, so on any normal viewport the chart is pushed off-screen. Portrait is the
   expected case: 58-01's mobile fix was explicitly directed to *"assume portrait."*

2. **`breakout_start_s` is a genuinely small surface.** `annotations.py` :11 + :20 (docstring), **:41
   (PHASE_KEYS)**, :90 (build_seed doc); `AnnotationChart.js:38` (PHASE_META);
   `tests/test_annotations.py` :98, :138, :239; `supabase/patch_07_annotations.sql` :5 + :11 (comments
   only). **`api.py` never names it**, and the `phases` column is free-form JSONB — **no SQL patch, no
   hand-applied migration.**

3. **Exactly one hazard in removing it.** `validate_annotation` (`annotations.py:238-240`) rejects any
   phase key not in `PHASE_KEYS`, so an annotation already stored with `breakout_start_s` would start
   422-ing. That is the whole compatibility problem — see D7b.

4. **The web side strips it for free.** `page.js:14-18` `normalizePhases` copies only keys present in
   `PHASE_KEYS`/`PHASE_META`, so dropping the entry from `PHASE_META` means the page stops sending it
   without any further change. Web-first is therefore the **safe** deploy order (backend keeps
   tolerating a key the client no longer sends); backend-first would 422 a stale tab.

5. **No metric moves.** `annotation_to_overrides` reads only `dive_start_s` → `baseline_end_idx`,
   `stroke_start_s` → `ip_end_idx`, `finish_s` → `swim_end_idx`. `breakout_start_s` was never one of
   them (this is Phase 57's own D5 finding). Removing it cannot change a number on any session.

6. **The user has already adopted the new convention.** The supplied screenshot shows Dive, Pulldown,
   Stroke and Finish placed with **no cyan Breakout line** — the marker was being skipped in practice
   before it was removed in code.

## Decisions (user, 2026-08-07)

### D6 — Cap the video height, keep the stacked layout, widen the page
Video letterboxed into a fixed maximum height (~35 vh) with `object-contain`, and the page widened
from `max-w-5xl` to `max-w-7xl`. Chosen over side-by-side, sidebar-video, and a drag-resizable panel.

**Why this one and not side-by-side:** the chart keeps every horizontal pixel. At ~40 marks on a
freestyle 25, horizontal resolution *is* the precision budget — halving the chart width to seat the
video beside it would roughly double the placement error the video is being introduced to reduce.
Widening the page pays into the same budget.

Letterboxing is deliberate: portrait footage wastes horizontal space inside its own box rather than
dictating the height of the page.

### D7 — Breakout removed from the phase model
**Supersedes Phase 57 D5** (*"UW kick + Breakout stay ground-truth-only, and the UI says so"*) for
Breakout specifically. D5 continues to hold for UW kick.

- **D7a — removed from the contract, not merely hidden.** `PHASE_KEYS`, `PHASE_META`, `build_seed`,
  the docstrings and the tests all lose it. Hiding it in the UI was offered and declined: a nullable
  key nobody places would survive in the 16-06 export and the docs indefinitely.
- **D7b — legacy values are stripped silently on read.** `validate_annotation` tolerates-and-ignores
  `breakout_start_s` instead of 422-ing it; the page never renders it; the next save drops it from the
  row. Permissive read, strict write. **Accepted cost:** the stored breakout time is lost on that
  save. User's framing of where it goes conceptually: *"what used to be breakout is absorbed into
  dolphin kick or pulldown for respective strokes"* — so the UW kick / Pulldown band now runs from
  `underwater_start_s` all the way to `stroke_start_s`, covering kick **and** breakout. The UI must
  say that, not leave it inferred.
- **D7c — UW kick / Pulldown stays.** Only Breakout was asked for. It remains the sole `drivesMetrics:
  false` marker, so the "record only" badge and its tooltip survive.
- **D7d — `stroke_start_s` does not move.** It still means *first arm entry after surfacing*. You
  simply stop placing a separate Breakout mark. `ip_end_idx` is untouched, so **no session recomputes
  and nothing becomes incomparable** — unlike the v95 change in 57-01. Retiring the Stroke marker in
  favour of deriving it from the first stroke mark was offered and declined.
- **D7e — "the first stroke cycle contains breakout" is documentation only.** No metrics.py change, no
  per-cycle flag in the annotation contract. It gets stated in the annotate UI and in the
  `annotations.py` docstring so the 16-06 consumer reads it where the data is defined. Flagging the
  breakout cycle in the export, and excluding the first cycle from cycle averages, were both offered
  and declined — the latter would have shifted `mean_dps_m` / `cv_isi` / `mean_coast_fraction` on
  every session, paying the comparability cost a second time.

### D8 — Frame-accurate playback ships with mark-at-playhead
`←`/`→` frame stepping (~1/30 s) and a 0.25× / 0.5× / 1× speed control on `VideoPane`, in the same
plan as mark-at-playhead rather than after it.

**Reasoning that made this non-optional:** the native HTML5 player has no frame step, so scrubbing
lands within roughly ±0.3 s. Mark-at-playhead built on top of that would be *coarser than clicking
the chart* — it would ship the feature while defeating its purpose. The full-workflow option (also
folding in the `VideoPane` end-anchor) was offered and declined in favour of this middle scope.

⚠ **Keybinding collision to resolve at plan time:** `page.js:230` already binds `ArrowLeft`/
`ArrowRight` to nudging the selected mark. Frame-step wants the same keys. Needs an explicit rule —
focus-scoped, modifier-distinguished, or different keys for one of them.

## Revised 58-02 scope

**⚠ The `VideoPane` end-anchor moved OUT of 58-02.** The declined option in the D8 question was the
one bundling it ("layout + frame-step + slow-mo + mark-at-playhead + the VideoPane end-anchor, all in
one plan"), so honouring that choice means 58-02 stops at mark-at-playhead. The end-anchor — and with
it the retirement of the per-session Video Overlay tap — becomes **58-03**. Consequence to keep in
view: until 58-03 lands, every record-with-video session must still be opened once in Video Overlay
on the phone or it arrives at `origin_s = 0`, silently unsynced (finding 4).

58-02, three tasks, `myswimcoach` repo:

1. **Breakout removal, end to end** — `annotations.py` (drop from `PHASE_KEYS`, add
   `LEGACY_PHASE_KEYS` tolerated on read, rewrite the docstring's phase model + the first-cycle
   note), `tests/test_annotations.py` (3 assertions updated, 1 added → 237), `AnnotationChart.js`
   (drop the `PHASE_META` entry — every consumer is derived from it), `AnnotationEditor.js` (UW kick
   caption + first-cycle convention). `api.py:857` rebuilds `phases` from `PHASE_KEYS`, so the
   endpoint follows with **no edit**.
2. **`VideoPane`** — `max-h-[34vh]` + `object-contain`; frame-step (`FRAME_S = 1/30`, pause before
   seeking, call `onPlayhead` explicitly because `timeupdate` is throttled below ~100 ms); 0.25× /
   0.5× / 1× applied in an effect **and** `onLoadedMetadata` (a new `src` resets `playbackRate`);
   `frameStepRef` mirroring the existing `seekRef` contract.
3. **`page.js`** — `max-w-7xl`; extract `placeStrokeMark(t)` so the swim-window guard exists once and
   cannot drift from the 57-01 server rule; arrow keys step frames when nothing is selected and nudge
   when something is (`preventDefault()` is load-bearing — a focused `<video controls>` seeks ±5 s on
   those keys in Chrome); `Escape` deselects; `M` marks at the playhead **without selecting the new
   mark**, or the step-mark-step loop breaks on its second iteration.

**Deploy order — CORRECTED 2026-08-07 after implementation: either order is safe.** This section
originally read *"web before backend, or together; never backend first."* That was derived before
D7b's `LEGACY_PHASE_KEYS` tolerance was written and was not re-derived once it existed. With the
tolerance, a new backend accepts `breakout_start_s` from a stale page (`validate_annotation` skips
retired keys; `api.py:857` drops it on write), so the 422 the rule guarded against cannot occur.
Backend-first's only effect is that a Breakout mark placed on a stale tab silently fails to persist
— cosmetic, on a marker being abandoned. Web-first is also fine: the client stops sending the key
and an old backend simply writes it as null.

## What this amendment does NOT change

- No metric on any session changes. No recompute, no re-baseline, no comparability break (D7d, D7e).
- No SQL patch and no hand-applied migration (finding 2).
- No iOS work. 58-01 is unaffected.
- `metrics.py` is untouched.
- UW kick / Pulldown survives (D7c), and with it the record-only concept.

## Contention to sequence

**Three pending changes now target `web/app/app/annotate/[id]/page.js`:** 57-03 (annotation queue +
prev/next), this amended 58-02, and any 57-02 follow-up. 57-02's checkpoint is closed, so the gate is
gone, but 57-03 and 58-02 must not be applied concurrently from two PAUL environments — the hazard
STATE.md already flags for `.paul/` applies to this file with real code at stake.
