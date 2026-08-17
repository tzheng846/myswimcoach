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
- ✓ Website: marketing site + coach web portal (dashboard, athletes, history, report card, compare, per-cycle analytics) — Phase 23. **Coach portal reworked in Phase 61 (2026-08-11):** report card rebuilt around four per-cycle charts (numeric table and Data Quality card retired), Time-to-Distance now states where its start came from, prev/next navigation between an athlete's sessions, a read-only `/app/sessions/[id]/video` route, and Compare rebuilt as two stacked traces on their own true sample rates with alignment, per-cycle overlays, paired value bars and optional video. Every session now carries a name — a coach-typed one or a generated mnemonic — derived, never written to `sessions.name`. **Marketing site redesigned in Phase 40 (2026-06-22)** to the iOS app's light-purple "Template B" immersive-gradient theme on shadcn/ui + Tailwind v4 (plain JS); pricing replaced by a Request-a-quote ContactDialog; coach portal intentionally left on the original dark theme (future phase if a matching portal redesign is wanted).
- ✓ Marketing **build-log blog** — public `/blog` index + statically-generated `/blog/[slug]` post pages (Next 16 `generateStaticParams` + `notFound`), linked from Nav + Footer, on the light marketing theme. Seeded with 5 thematic founder-journal posts (lightly-polished candid voice; covers current state, past struggles, upcoming ideas). Posts live in a plain JS data file (`web/lib/blog.js`) — no CMS; adding a post = append one object — Phase 46 (2026-06-23).
- ✓ Parent report cards: coach-curated progress reports (range + metric picks + note), tokenized public pages with animated improvement deltas + trend charts, mass dispatch via mailto/copy-link — Phase 24. Email provider (Resend) deliberately deferred.
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
- Python backend must be preserved: vel_acc_extraction.py + metrics.py + coach.py are not rewritten
- ~~Breaststroke only for V1~~ — **relaxed 2026-08-05** (Phases 54-01 + 55-01). All four strokes now
  render analytics in the app and on the web. Breaststroke remains the only stroke with data behind
  its thresholds; the others borrow that table deliberately and visibly. The constraint has moved
  from "the UI hides other strokes" to "the other strokes are not yet validated" — a data problem
  Phase 53 exists to address, not a product gate.
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
*Updated: 2026-08-16 after Phase 66 — Acceleration Derivative (1/1 plan). Replaced the ~5 Hz
decimate→gradient→linear-interp acceleration with a full-rate Savitzky–Golay derivative, then made
its smoothing window stroke-dependent (free/back 0.50 s, fly/breast 0.25 s) after the user observed
alternating-arm strokes read noisier than fly. Display-only — `metrics.py` never consumes
acceleration; velocity and every metric are untouched. Deployed to Railway; 70 rows re-backfilled.
⚠ The windows are hand-tuned on one swimmer's data; the principled version sets each from a measured
velocity spectrum once a broader corpus exists.*
*Updated: 2026-08-16 after Phase 64 — Fullscreen Video + Velocity Overlay (3/3 plans, web). A
fullscreen video stage with a hand-rolled SVG velocity trace (rAF, zero React state) + drag-to-scrub
(64-01, `0f63a15`+`fe3b53b`); `sessions.acceleration_profile` stored as an EXACT derivative of the
already-stored velocity with a 70/70 backfill, no raw-CSV reprocessing (64-02, `f133c56` → Railway);
and acceleration on BOTH the overlay (a stacked signed band sharing one window/scrub/playhead) and a
new static `AccelerationChart`, with page-owned, persisted, cross-surface-synced toggles + colour via
`useTracePrefs` (64-03, `fe3b53b` → Vercel). ⚠ The stored acceleration is a ~5 Hz decimate→gradient→
linear-interp reconstruction that reads **choppy** on screen — **Phase 66 replaces the derivation with
a Savitzky–Golay first derivative + re-backfill**, which is **display-only** (`metrics.py` consumes
velocity, never acceleration, so no metric moves). ⚠ Known limitation: the accel toggle lives in the
video control bar, so a no-video session can't turn acceleration on (it follows the persisted pref).*
*Updated: 2026-08-11 after Phase 61 — Web Portal Rework (5/5 plans). Delivered all five things the
user asked for, and one they did not. **⭐ The one they did not: `ramp_up` was never ramp-up.** The
steady/ramp_up cycle split — which every `mean_*`, `cv_*` and `stroke_count` was computed over —
gated on `arm_peak < 0.50 × p75`, a VELOCITY test. Measured on two corpora, it overwhelmingly marked
**the swimmer decelerating into the wall**, not accelerating from rest: 0 of 13 affected `raw/`
sessions had a leading run, and on the live DB the median excluded-cycle position was **0.91**, with
59% in the final 20% of the swim. Removing it (61-01, user's call, reaffirmed three times with the
measurements on screen) made the charts and the numbers describe the same cycles — the user's report
that *"the numbers don't reflect what's actually shown on graph"* was literally true — at the cost of
a **fourth comparability break** and a re-anchoring of two `ratings.py` bands, since the 0–100 score
floored out for a third of sessions once the wall-touch counted. ⭐ **58-04 CLOSED**, owed and
"homeless" since 2026-08-07: the web computes its own end-anchored `video_origin_s`, so the phone's
`VideoOverlayScreen` is no longer the only writer in the system — and a SECOND instance of the same
`?? 0` defect was found in `VideoPane.attach()`. Also shipped: the last hardcoded sample rate on the
web is gone, and per-session generated names so three sessions from one morning are no longer
indistinguishable. Suite 273 → 274. ⚠ CARRIED OUT: **synced playback on Compare** (recorded as a
TODO, deliberately unplanned — needs a `VideoPane` play/pause API it does not have); the video
chart no longer auto-follows the playhead (CONTEXT D16 withdrawn at the user's request); generated
names are derived, not persisted; and the mobile D5c comment fix remains uncommitted.*
*Updated: 2026-08-11 after Phase 60 — Mobile App Rework (3/3 plans). The coach's poolside device no
longer shows less than the laptop, and no longer shows one number wrong. **A live −10% time-axis
error** on the mobile report card was found and fixed: Phase 52 corrected it on the web, but
`89205ca` is a `myswimcoach` commit and the separately-owned mobile repo was never in its diff, so
four consumers stayed wrong for two months (chart axis, cycle overlay, Time-to-Distance, CSV) —
measured against the live DB at **−10.0% → +0.0%**, 4 sessions of 4. Also shipped: four per-cycle
charts (the "Per-cycle charts in iOS app" nice-to-have, previously substituted by the web), a
scrubbable window bar replacing pinch-to-zoom, session video reachable from any saved session rather
than only just after recording, and a user-dropped start marker for Time-to-Distance. Zero Python
touched; suite held at 273 throughout. ⚠ Two things carried out: **58-04 is still owed and homeless**
(the web annotate page still cannot compute a video origin of its own) — ✅ **CLOSED by Phase 61-03
on 2026-08-11** — and **Phase 52-02 gained motivation** — most NULL-rate sessions are ~90 Hz, not
~100, correcting a generalization in the Phase 59 record.*
*Updated: 2026-08-05 after Phase 55 — athlete flow repaired end-to-end. Phase 51-02 fixed the phantom
`athletes.coach_id` that made `POST /athletes` 500 (shipped `dedac17`); Phase 55-01 then fixed the two
defects that failure had been hiding, both consequences of `RecordingConfig` being a tab screen that
never remounts: a roster frozen at app launch, and a Record button whose `navigate()` silently went
unhandled from the Root stack. Freestyle analytics reached a device build for the first time — the
"breaststroke only" constraint is now a data-validation question, not a UI gate.*
*Created: 2026-05-17*
*Updated: 2026-07-20 after Phase 47 — trial annotation tool shipped end-to-end: annotation
contract + web GUI + recompute-on-save (deployed) plus iOS background video upload + synced
playback origin (code-complete, device-verify pending).*
*Updated: 2026-06-23 after Phase 46 — added a public build-log blog to the marketing site (/blog index + /blog/[slug] SSG posts; web/lib/blog.js data file; Nav+Footer links; 5 founder-journal posts).*
*Updated: 2026-06-22 after Phase 40 — marketing site redesigned to the iOS light-purple theme (shadcn/Tailwind v4); public pricing removed sitewide in favor of a Request-a-quote contact form (Web3Forms).*
*Updated: 2026-06-12 after Phase 25 — codebase audit shipped (CODEBASE-AUDIT.md): all cross-system contracts verified, 7 findings documented incl. Railway deploy drift and version-control coverage gaps in both repos*
