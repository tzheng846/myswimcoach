# Project: Swimnetics

## Description

B2B swim coaching tool. AS5600 magnetic encoder wheel clamps to a diving block and captures tethered swim velocity at ~270 Hz. Signal pipeline extracts stroke-level biomechanical metrics. AI coaching layer interprets them for the coach. No competitors at this price point or form factor.

## Core Value

Coaches get objective biomechanical data on every swimmer in their lane — no laptop required at poolside.

## Customers

Swim academies and competitive programs. Coach or operator runs the device; swimmer just swims.

## Requirements

### Must Have
- ✓ iOS app: BLE recording, athlete select, velocity chart — no laptop at poolside — Phase 5
- ✓ FastAPI backend: wraps existing Python signal pipeline; all processing server-side — Phase 4
- ✓ Supabase: auth, athlete profiles, session history per athlete — Phase 6–9
- ✓ Breaststroke metrics: stroke rate, DPS, fatigue index, glide time, consistency — Phase 7–8
- Offline-safe recording: local CSV buffer, upload queues and retries
- Supabase: device registration (deferred → v0.3 Phase 10)

### Should Have
- Stripe billing backend: Starter/Enterprise tiers wired (Phase 15). Internal pricing model (NOT shown publicly): **$300 one-time device (basic stroke metrics) + $20/swimmer/month optional cloud tier (video storage, long-term tracking, history, parent reports)** — Phase 29 decision (2026-06-14). As of Phase 40 (2026-06-22) public pricing is REMOVED from the website — the marketing site routes to a "Request a quote" contact form (Web3Forms → tzheng846@gmail.com) instead of publishing prices; checkout still not exposed on web.
- ✓ Website: marketing site + coach web portal (dashboard, athletes, history, report card, compare, per-cycle analytics) — Phase 23. **Coach portal reworked in Phase 61 (2026-08-11):** report card rebuilt around four per-cycle charts (numeric table and Data Quality card retired), Time-to-Distance now states where its start came from, prev/next navigation between an athlete's sessions, a read-only `/app/sessions/[id]/video` route, and Compare rebuilt as two stacked traces on their own true sample rates with alignment, per-cycle overlays, paired value bars and optional video. Every session now carries a name — a coach-typed one or a generated mnemonic — derived, never written to `sessions.name`. **Marketing site redesigned in Phase 40 (2026-06-22)** to the iOS app's light-purple "Template B" immersive-gradient theme on shadcn/ui + Tailwind v4 (plain JS); pricing replaced by a Request-a-quote ContactDialog; coach portal intentionally left on the original dark theme (future phase if a matching portal redesign is wanted). **Marketing home page refreshed in Phase 85 (2026-08-29)** — the page had not moved since Phase 40 while ten weeks of product work went unshown. It now leads with the **race-phase report card** (one real coach-marked lap with the Start / Underwater / Swimming windows tinted in place, plus a radar per phase), then the within-athlete usual-range comparison, the per-cycle trace pack, multi-camera video and the device; the flat six-card metric grid is retired. The **Swimnetics mark** enters the web surface for the first time (nav + footer lockup, `app/icon.png` / `app/apple-icon.png`). Chart geometry is **baked at author time** into `web/lib/marketingGeom.js`, so a public page makes no Supabase call; trace shapes are real but every printable value is perturbed, which is why nothing on the site may claim measured data. Copy rules (no dashes in either form, no material names, no brand names) are now enforced by `scratch/marketing_render_check.mjs` rather than by eye.
- ✓ Marketing **build-log blog** — public `/blog` index + statically-generated `/blog/[slug]` post pages (Next 16 `generateStaticParams` + `notFound`), linked from Nav + Footer, on the light marketing theme. Seeded with 5 thematic founder-journal posts (lightly-polished candid voice; covers current state, past struggles, upcoming ideas). Posts live in a plain JS data file (`web/lib/blog.js`) — no CMS; adding a post = append one object — Phase 46 (2026-06-23).
- ✓ Parent report cards: coach-curated progress reports (range + metric picks + note), tokenized public pages with animated improvement deltas + trend charts, mass dispatch via mailto/copy-link — Phase 24. Email provider (Resend) deliberately deferred.
- ✓ **Team leaderboards** — coach-only `/app/leaderboard`, **the product's first between-athlete surface** (everything before it compares a swimmer to their own usual range) — Phase 90 (2026-09-02). Eight detector-independent metrics — average speed, top speed, lap time, underwater speed, and the four 5 m splits — ranked within team and partitioned by stroke, top five per board with the full order one click away, every swimmer on every board for a stroke they have swum. **Nothing is stored:** ranks are computed on read from data already loaded, so a board is never stale and no backfill exists. Load-bearing caveats are stated on the page rather than hidden — all swims are assumed 25 yd (unverifiable in the data, and the premise under every lap-time and split comparison), swims covering under 15 m of tether travel are excluded with the count shown, and a row is the mean of the athlete's last 5 swims ordered by **upload** time. Values convert with the standing `swimnetics.unit` preference; ranking runs on SI so the toggle provably reorders nothing. ⚠ Deliberately **excludes the four cycle-derived metrics first asked for** — freestyle segmentation detects a median of 5 strokes on a 25 that should be 12–18, so ranking them would publish segmenter failures as swimmer standings by name. Gender and age-group partitioning are deferred (neither field exists in the DB); athlete and family visibility is deferred to Phase 89.
- Device pairing via QR code (serial number → team account claim)
- ✓ **Segmenter measured and tuned against ground truth — Phase 59 (2026-08-09).** The project's
  first scoring harness (`segmenter_eval.py` + `tools/score_segmenter.py` + a committed fixture
  regression), then per-stroke segmenter dispatch. Butterfly F1 0.317→0.526, breaststroke
  0.232→0.444, freestyle boundary F1 0.000→0.458; the swim window is now rhythm-based
  (`ip_end` 3.93→1.99 s, `finish` 3.82→0.82 s); freestyle stroke rate corrected from **1.65× the
  true value to 1.00**. ⚠ Three defects fixed, **all invisible to `stroke_rate_spm`** — the metric
  a coach actually reads. ⚠ Still true: one swimmer, 23 annotated sessions, breaststroke n=2,
  backstroke n=0, and `segmentation_reliable` remains hardcoded `False`. **SUPERSEDES the long-
  referenced "16-06" slot.**
- Freestyle support (Phase 16 — wavelet/CWT ridge segmenter SHIPPED for all strokes at placeholder
  quality, 16-05; `segmentation_reliable=False`; accuracy tuning → Phase 59, done).
  **UI unlock shipped end-to-end 2026-08-05** (Phase 54-01 backend, deployed in `dedac17`; Phase 55-01
  carried the mobile half into an EAS build and it was verified on device): `ratings.py` falls back to
  the breaststroke threshold table for every stroke, `provisional` no longer keys off
  `segmentation_reliable`, and the app's `isAnalyticsReady` gate is off. ⚠ What this does NOT mean:
  the bands are **breaststroke-derived and unvalidated for other strokes**, applied over segmentation
  still flagged unreliable (16-04: 3/8 breaststroke sessions within ±5 SPM). Freestyle numbers now
  *display*; they are not yet *trusted*. Phase 53 decides whether absolute bands should exist at all —
  its within-athlete-contrast reframe needs no thresholds.
- AI coaching chat proxied through FastAPI (Anthropic key server-side)
- ✓ Trial annotation tool: coach hand-corrects auto-segmented swim phases/strokes on the web
  portal with synced video (`/app/annotate/[id]`); corrections both produce a ground-truth
  export for future 16-06 segmenter tuning AND recompute the session's own metrics through
  the real pipeline. iOS auto-uploads Record-with-Video footage in the background (FIFO
  queue, in-app toast, survives backgrounding) and persists the end-anchored sync origin so
  video is pre-aligned when the coach opens the annotate page — Phase 47 (2026-07-12).
  Backend contract + web GUI + recompute committed and deployed (e7f72f4, 627419c); iOS side
  code-complete, device-verify rides the next EAS build (mobile repo local-only, user-owned git).

- ✓ **External-camera video sync (Phase 67, 2026-08-17):** coaches attach GoPro / waterproof-cam
  footage on the web annotate page and sync it to the velocity trace with a one-tap **push-off
  align** (scrub the clip to the dive frame → one click sets `video_origin_s = diveSessionTime −
  videoTime`; the dive is auto-detected on the encoder, so **no computer vision** and zero marks
  required). Upload is memory-safe (413 before buffering + streamed to Storage, never `file.read()`
  into RAM). ⚠ **Free-tier 50 MB cap:** external clips must be compressed to <50 MB (HandBrake /
  GoPro Quik) until a Supabase Pro upgrade — a documented one-flip (raise the global limit + bump the
  two `MAX_VIDEO_BYTES` + apply `patch_11`). V1 = one clip per session; the one-long-take → many-
  sessions workflow is a deferred shared-asset phase. ⚠ Real-clip UAT owed.

- ✓ **Multi-camera video (Phase 69, 2026-08-17):** a session can carry up to 4 synced camera angles
  (phone + 3 external) on a dedicated `/app/sessions/[id]/videos` page — a synced player where ONE
  master timeline drives every camera and the velocity trace together (each seeks to `sessionTime −
  its origin`; the focused camera carries audio, the others are drift-corrected), plus per-camera
  push-off sync, editable labels, and delete. The report card is decluttered (the inline video panel
  became a compact "Videos" link). The data model is **additive** — externals live in a new
  `session_videos` table while the phone/primary stays in the legacy columns, so nothing existing
  broke and mobile is untouched. ⚠ patch_12 (the table) must be applied live, and real-video UAT is
  owed (the 4-video synced playback was built without live data — highest-risk piece). ⚠ Free-tier
  50 MB/clip; the long-take → many-sessions workflow is still deferred.

- ✓ **Arm-by-arm view — the individual stroke as a first-class unit (Phase 87, 2026-08-31).** A
  freestyle or backstroke cycle is TWO arm strokes, and every stored number described the pair, so a
  cycle's own left/right contrast was structurally zero. The backend now segments and stores single
  arm strokes (`metrics_json.strokes` beside `cycles`) plus three signed asymmetry percentages
  (tempo / distance / peak velocity) and four per-side consistency CVs; the coach portal's Swimming
  section carries a **cycles / strokes** toggle that rebuilds the inset bands, count badge, trace
  pack and all four trend panels at stroke scale, with the two arms drawn in different colours and
  an **Arm balance** readout naming the magnitude and direction of each split. Backfilled to 47 of
  101 stored sessions. **The signal is real and it separates:** 6.1% median tempo contrast across 23
  annotated freestyle sessions, 0.4% on the evenest swim and 29.4% on the most lopsided.
  ⚠ **Two limits that are product facts, not bugs.** The sides are **A and B, never left and right**
  — a single-axis encoder cannot observe which arm is which. And on **auto-segmented** sessions the
  asymmetry is *uncorrelated with coach-mark truth* (r = −0.06): one extra or missing boundary flips
  the A/B side of every later stroke. It ships anyway, marked only by the existing `auto` chip
  (explicit user decision, 87-01 D2) — so on an unannotated session the number is a prompt to
  annotate, not a finding. Backstroke rides freestyle's code path and has **0 annotated sessions**,
  so nothing about it is validated.

- ✓ **A coach can pick their own split, read every number in their own units, and see the lap-scale
  trend (Phase 88, 2026-09-01).** Two reported defects, and two larger ones found while fixing them.
  (1) **Splits are selectable**: the report card's five fixed 5 m rows are joined by a chip picker
  that reads back average velocity and elapsed time over any **contiguous** run of complete 5 m /
  5 yd segments on this swim — only complete bins are offered, so no label can describe a stretch it
  does not cover. The structurally-dead `splits_25m` row (a waist tether tops out at ~21.9 m on a
  25 yd lap, so it filled on 2 of 99 sessions) is retired for `splits_remainder`, 20 m → the finish.
  ⚠ Its span varies ~10× — median 0.87 m on a 25 yd lap — so it reads closer to *closing speed* than
  to a fifth 5 m split, directly beneath four true ones.
  (2) **The unit toggle now converts everything.** 23 of 47 registry metrics never converted; the
  fix is keyed on the **unit string** rather than a metric list, and 🔴 **the verdict is computed on
  SI and never on converted values** — so switching units structurally *cannot* invent or erase a
  flag, rather than merely being expected not to.
  (3) **NOT REPORTED and larger than what was: the page held THREE different origins for "0 m."**
  Probed live, they differ by more than 0.1 s on **27 of 99 stored sessions**, tail 12.39 s. Every
  distance-anchored number now measures from one anchor (raw `dive_start_s`), stated once on the
  page along with where that boundary came from. ⚠ This **moved numbers a coach had already read**
  (~0.4–0.5 s on the 37 sessions of the one athlete with a head-waist offset), and **iOS still
  carries the old head-waist-adjusted Time-to-Distance**, so the two surfaces disagree until a
  mobile phase carries it across.
  (4) A **velocity trend overlay** — a grey dotted rolling mean on an adjustable 0–3 s window — was
  added at the user's direction outside the phase's charter. A ~90 Hz butterfly trace is a sawtooth
  of real surge-and-glide peaks that must not be smoothed away, but raw it hides the lap-scale story
  the coach is reading for. It stores nothing and adds no metric: it is a second rendering of the
  velocity profile.
  ⚠ **The unit conversion is this page only** — the same metric still shows unconverted on compare,
  group and parent-report surfaces (accepted, R7). ⚠ **Time-to-Distance was deleted** mid-phase as
  redundant against the new picker, one day after it had been re-anchored.

### Nice to Have
- PDF report generation (server-side, emailed to coach)
- Session compare in iOS app (✓ shipped on web portal instead — Phase 23)
- ✓ **Per-cycle charts in iOS app — actually shipped on iOS in Phase 60-01 (2026-08-11)**, no longer
  substituted by the web. Four hand-rolled SVG panels (distance per stroke, coast, cycle duration,
  arm peak velocity), each captioned with the mean or CV it summarizes. The phase also fixed a live
  **−10% time-axis error** on the mobile report card that Phase 52 had corrected on the web and
  never carried across (`89205ca` is a `myswimcoach` commit; the mobile repo was never in its diff),
  replaced pinch-to-zoom with a scrubbable window bar, and made session video reachable from any
  saved session rather than only in the moments after recording.

## Constraints

- No Mac: iOS builds via Expo EAS Build (cloud Mac infra)
- No video: encoder is the permanent primary sensor
- **The tether measures the WAIST, not the fingertips (2026-08-28).** The line is strapped to the
  swimmer's waist, so recorded distance is always **~1 m short of the wall-to-wall distance** — the
  gap is the swimmer's outstretched arm plus torso. A 25-yard trial (22.86 m) therefore tops out
  near **21.9 m of tether travel**, and every distance-anchored metric is offset by that constant.
  Two consequences that are easy to misread as bugs: a "25 m" split can essentially never fill on a
  25-yard swim, and total distance will always undershoot the nominal lap. This is a property of the
  apparatus, not a calibration error — do not "fix" it by scaling distance.
- **`finish_s` legitimately precedes velocity reaching zero (2026-08-28).** After the hand touches
  the wall the swimmer keeps drifting into it — bending the elbows, coasting the last body-length —
  so the tether keeps paying out after the race is over. The finish mark belongs at the touch, not
  at the end of motion. Any detector or annotation convention that waits for stillness will land
  late by design; the trailing drift is real signal that is not part of the swim.
- Python backend must be preserved: vel_acc_extraction.py + metrics.py + coach.py are not rewritten
- ~~Breaststroke only for V1~~ — **relaxed 2026-08-05** (Phases 54-01 + 55-01). All four strokes now
  render analytics in the app and on the web. Breaststroke remains the only stroke with data behind
  its thresholds; the others borrow that table deliberately and visibly. The constraint has moved
  from "the UI hides other strokes" to "the other strokes are not yet validated" — a data problem
  Phase 53 exists to address, not a product gate.
  ⚠ **The public site no longer discloses this (Phase 85, D6/R3, 2026-08-29).** The FAQ's
  "Which strokes are supported?" answer, live since 2026-06-15, was removed at the user's explicit
  direction. The underlying fact is unchanged: the non-breaststroke strokes borrow the breaststroke
  threshold table and `segmentation_reliable` is still hardcoded `False`. A coach with a fly-heavy or
  backstroke squad now has nowhere on the site to learn that.
- Swimmers 13+ for now (Phase 29, 2026-06-14): privacy policy sets a 13-or-older floor to avoid COPPA's under-13 regime during test demos; club is the customer and collects verifiable parental consent at registration for minors (13–17). Revisit if younger age groups are needed.

## Architecture

```
iOS App  (React Native + Expo bare + EAS Build)
FastAPI on Railway  (Python — reuses existing code)
Supabase  (auth + Postgres + file storage)
Website  (Next.js 16 in web/, Vercel target — marketing + coach portal; Phase 23)
Streamlit app  (existing — deep analysis, desktop/tablet; portal now covers its features)
```

See STRATEGY.md for full architecture and data model. CODEBASE-AUDIT.md (repo root,
2026-06-12) is the verified cross-system map: connection matrix, folder roles, and
known drift (Railway pre-Phase-24, committed SQL ≠ live DB, git coverage gaps).

## Success Criteria

- Coach records a session on iPhone with no laptop present
- Session auto-processed and visible in app within 30 seconds of stopping
- First paying customer (swim academy) using the system

---
*Requirements & product intent above are the durable spec. **Current status / in-flight work: see
[STATE.md](STATE.md).** The per-phase change log was archived 2026-08-21 →
[.paul/archive/PROJECT-changelog-2026-08-20.md](archive/PROJECT-changelog-2026-08-20.md).*
*Created: 2026-05-17 · Docs restructured 2026-08-21 · Last updated 2026-09-02 after Phase 90.*
