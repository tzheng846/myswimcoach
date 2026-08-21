# PROJECT.md change log (archived 2026-08-21)

---
*Updated: 2026-08-19 — Phase 73-04 metric scoping. Added a **Scope selector** to the Groups view (Full swim
/ Stroking / Underwater / a distance range in metres from push-off) that **recomputes the 6 metrics over the
chosen window entirely client-side** from each session's stored velocity/distance profile + per-cycle data.
Fixes the audited inconsistency that speed spans the whole swim (dive included — top speed is usually the
dive) while stroke metrics span only the stroking, which diluted A/B speed contrast. New pure
`web/lib/windowMetrics.js` (**node-verified 17/17**); "Full swim" (default) uses STORED scalars verbatim so
nothing regresses; Distance/Stroking use WHOLE cycles for stroke metrics, Underwater blanks them. No
backend/schema/mobile; DiffBars headline + line drill-down + two-swim mode untouched. Shipped `2f17a1a` →
Vercel. Interactive UAT owed. (Headline is now difference bars — 73-03 `69e0dfa`.)*
*Updated: 2026-08-19 — Phase 73-02 chart rework. UAT found the per-metric strip plots "hard to read /
scale-less"; after showing 3 line-chart options as a published artifact, replaced them with a **mean-profile
headline** (one axis per metric, two group-mean lines + **±1 SD ribbons**, up=better, axis labels tinted
when groups clearly separate — where the ribbons clear each other the difference is real) plus **per-metric
small-multiple line charts** (real labelled Y-axis) as a collapsible drill-down. Only `GroupCompare.js`'s
render changed; build green, shipped `3964139` → Vercel. Interactive UAT still owed.*
*Updated: 2026-08-19 after Phase 73 — Group Comparison (1/1 plan, web-only). Added a **"Groups" mode** to
Compare that turns it into an A/B experiment tool: pick one athlete + stroke, assign that athlete's
same-stroke swims to two labeled groups, and per metric (`REPORT_METRICS`) see both group means, **each
swim as a dot** on an SVG strip plot, the direction-aware delta, and an honest **clear-separation /
overlapping** cue — answering "does breathing matter?" (3 no-breath vs 3 breath) at a glance. ⭐ **No
p-values** — with n≈3 a significance test is fragile/false-authority, so the cue is a ±SD band-overlap
read (suppressed for n<2); Claude pushed back on stats theater and the user agreed. Metrics-only (no
traces — the user's "6 traces = noise" steer); one athlete, same stroke; 2 groups modeled as an array so
≤5 is a later flip; ephemeral + coach-labeled (no schema). Web-only, reuses the Compare supabase-read +
client-stats pattern; the pure `web/lib/groupStats.js` was **node-verified 17/17** (no JS test runner
added). Shipped `d66734a` → Vercel; two-swim Compare untouched. ⚠ Interactive UAT owed (auth-gated). V2s:
group-average traces, >2 groups, saved experiments, an LLM one-liner summary.*
*Updated: 2026-08-19 after Phase 70 QR slate — built END-TO-END across all three surfaces (user chose
"build all 3 halves now" rather than defer). The QR accelerator: the phone mints a `recording_token` at
plain record start and shows it as a **QR** (react-native-qrcode-svg) for an external over-water camera to
film (mobile `e5e814e`); `/process` stores it on the session via `patch_13`'s nullable
`sessions.recording_token` — written ONLY when sent, so pre-patch DBs and current mobile builds are
unaffected (backend `e010eee`); and `/app/match` decodes the token from an uploaded clip's early frames
with **jsQR** and pre-fills the match via a coach-scoped RLS lookup, always **overridable** and degrading
silently to manual when absent (web `59411ab`). No match-by-token endpoint (RLS read suffices). Backend+web
→ Railway+Vercel; suite 64 (test_api) green; web build 19/19. ⚠ **Inert until three HUMAN steps:** apply
`patch_13` (Supabase SQL editor), a **paid EAS build** of the mobile app, and a real external-camera film
test — until then matching stays manual (Phase 70 core), which is the safe default (D4). ⚠ `expo-doctor`
flags PRE-EXISTING SDK drift (not this change) — reconcile before the paid build.*
*Updated: 2026-08-19 after Phase 70 — Video↔Session Matching, manual core (1/1 committed plan; QR slate
deferred). New `/app/match` page: the coach dumps many opaque external clips, sees a **client-side content
thumbnail** of each (recognize the swim — GoPro/off-brand filenames + timestamps are untrusted, D2), and
assigns each to a session by reusing Phase-69 `POST /sessions/{id}/videos`. The assigned external then
appears on that session via Phase-71's unified reader. **Web-only by design** (user-chosen): Phase 69 already
built the upload path and iOS never handles external footage, so there is NO backend/schema/mobile change —
only the QR accelerator would touch those, and it is a deferred mobile-gated follow-on (jsQR web decode +
`sessions.recording_token` + phone QR display, useless until all three ship together, D4–D9). Metadata is a
display-only soft hint (never sorts/auto-selects). Thumbnails are canvas frame-grabs from same-origin object
URLs (no server, no schema). Shipped `17f3a77` → Vercel; `next build` green (19/19, +1 page). ⚠ Auth-gated
page → interactive UAT owed (stage real clips → thumbnails render; assign → external shows on the session);
odd codecs (HEVC/off-brand) may fail thumbnail grab → non-blocking "No preview" fallback. ⚠ V1 = one clip →
one session (the long-take → many-sessions shared-asset model stays deferred).*
*Updated: 2026-08-19 after Phase 71 — Video Surface Rework (2/2 plans). Fixed the Phase-69 UAT bug where
a web-uploaded external video was invisible on the report card AND annotate page: both read the legacy
`sessions.video_path` while web uploads land in `session_videos`. **Reader-side fix, no schema change /
no migration** — every video surface now reads the unified `GET /videos`, so the orphaned external
reappears. Also: "Add video" is a report-card MODAL (no page nav); the report card plays one angle inline
with the velocity overlay; the **annotate page became the single video hub** (all cameras as tiles, one
active camera drives marking, per-camera manual **two-point align** — "Set sync": scrub camera → click
the trace at the same instant → `origin = traceTime − videoTime` + ±nudge); the distrusted **auto
push-off/dive alignment was removed entirely** (user: doesn't trust the encoder can detect push-off);
and the standalone `/app/sessions/[id]/videos` page/route was deleted. Shipped 71-01+71-02 as one commit
`1e086ef` → Vercel. User UAT confirmed "Set sync" works. ⚠ Phone end-anchor not re-added to the web tile
— a never-opened phone record-with-video shows unsynced until manually aligned (accepted; the user's
clips are externals). ⚠ Follow-on captured, NOT built: tablet-responsive layout for the now-denser
annotate hub (candidate Phase 72). No mobile / pipeline / metrics change.*
*Updated: 2026-08-17 after Phase 69 — Multi-Camera Video (3/3 plans). Up to 4 synced camera angles
per session on a new `/app/sessions/[id]/videos` page with a one-timeline player (focused camera
drives the clock + audio; others drift-corrected); report card decluttered (video panel → compact
link). Data model is ADDITIVE — a new `session_videos` table holds the ≤3 externals while the
phone/primary stays in the legacy columns, so no migration, no reader breaks, mobile untouched.
Refined from the CONTEXT's "replace the 1:1 columns" once the repo showed 5 web sites read them
directly. Ran as an auto-loop (plan→apply→unify ×3): 69-01 API `ca73421`, 69-02 Videos page
`57d06c9`, 69-03 synced player + declutter `f03c4fd`; suite 58→61. ⚠ Built blind (no live
data/videos/auth in the sandbox) — patch_12 apply + synced-playback UAT are owed; the synced player
is the highest-risk piece. ⚠ Free-tier 50 MB/clip; long-take → many-sessions still deferred.*
*Updated: 2026-08-17 after Phase 67 — External Camera Sync (2/2 plans). Added GoPro/external-camera
support to the web annotate page: 67-01 a one-tap **push-off visual align** (coach scrubs the clip to
the dive frame, one click snaps it to the encoder-detected dive on the trace — no CV; `2aa58ca` →
Vercel), 67-02 **memory-safe uploads** (413 before buffering + streamed to Storage instead of
`await file.read()`) with a **free-tier 50 MB cap** and actionable compress/upgrade messaging
(`030f6f9`, `e3ce464`). ⭐ Repo-verified the phase was smaller than assumed — `VideoPane` already had
upload/nudge/save/end-anchor, so 67-01 was ~50 additive lines. ⚠ Mid-phase pivot: the user is on the
Supabase FREE tier (hard 50 MB), so the "raise the cap to 500 MB" premise was invalidated — pivoted
(user-chosen) to guide manual compression + defer real >50 MB footage to a Pro upgrade, rather than
build throwaway in-browser transcoding; `patch_11` + a two-line cap bump are the documented Pro flip.
V1 = one clip per session; the long-take → many-sessions (shared-asset) workflow is deferred. Suite
58 green (test_api.py); zero regressions. ⚠ Real-clip UAT (align feel + <50 MB upload) owed. Not
committed to `.paul` (project keeps planning docs local); code shipped in 3 commits.*
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
