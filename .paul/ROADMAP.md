# Roadmap: Swimnetics

## Overview
An end-to-end pipeline with velocity tracking and analysis for stroke analysis for swimming. Answers questions like "how does my technique vary throughout my swim?"

## Milestone: v0.1 Initial Release ✅

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Segmentation Refactor | 1 | Complete | 2026-05-17 |
| 2 | Metric Explanations | 1 | Complete | 2026-05-17 |
| 3 | BLE Record View | 1 | Complete | 2026-05-20 |

### Phase 1: Segmentation Refactor
**Goal:** Clean separation of segmentation and metric calculation; trough-only detection; auto-trim baseline and post-swim regions; remove FFT dependency.
**Plans:**
- [x] 01-01: Segmentation refactor + app.py cleanup

### Phase 2: Metric Explanations
**Goal:** Metric ratings + thresholds; user-facing explanations of coaching metrics.
**Plans:**
- [x] 02-01: Metric ratings + thresholds

### Phase 3: BLE Record View
**Goal:** Add a "Record" mode to app.py. User connects to ESP32 SwimLogger via BLE, records a session, auto-runs vel_acc_extraction + metrics pipeline, and the app auto-switches to Simple view showing the new session's results.
**Plans:**
- [x] 03-01: BLE record view in app.py

---

## Milestone: v0.2 Coach Demo ✅

**Goal:** Live demo-ready iOS app for a swim coach — full analytical breakdown, multi-swimmer dashboard, robust dive/pulldown detection, session history per athlete.

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 4 | FastAPI Backend | 1 | Complete | 2026-05-20 |
| 5 | iOS App — TestFlight | 3 | Complete | 2026-05-22 |
| 6 | Auth + Athlete Profiles | 3 | Complete | 2026-05-23 |
| 7 | Algorithm + Backend | 1 | Complete | 2026-05-23 |
| 8 | iOS Full Analytics | 1 | Complete | 2026-05-24 |
| 9 | iOS Dashboard + History | 1 | Complete | 2026-05-24 |

### Phase 4: FastAPI Backend ✅
**Goal:** Wrap `vel_acc_extraction.py`, `metrics.py`, and `coach.py` in a FastAPI server deployable to Railway. Single endpoint `POST /process` accepts a raw CSV, returns metrics JSON.

### Phase 5: iOS App — TestFlight ✅
**Goal:** React Native + Expo bare workflow app. BLE recording, CSV upload to FastAPI, velocity chart display. Distributed via TestFlight.

### Phase 6: Auth + Athlete Profiles ✅
**Goal:** Supabase auth (coach login), team roster (add athletes), session history per athlete. QR device registration deferred.
**Plans:**
- [x] 06-01: Supabase auth + schema
- [x] 06-02: iOS auth screens + JWT flow
- [x] 06-03: Athlete profiles + /process auth

### Phase 7: Algorithm + Backend ✅
**Goal:** Robust stroke detection for dive-off-block starts. Detect and measure underwater pulldown phase. Time-to-X metric (1–25m, adjusted by head-waist offset). Store full session results (metrics + 100Hz velocity + distance profiles) in Supabase. Raw CSV stored in Supabase Storage.
**Plans:**
- [x] 07-01: Dive/pulldown detection + time-to-X + session storage schema + backend

### Phase 8: iOS Full Analytics ✅
**Goal:** Post-session results screen showing all metrics.py outputs + velocity graph. Time-to-X button presets (1–25m, computed client-side from stored distance profile + athlete head-waist offset). Athlete profile: add/edit `head_waist_m` field. Session auto-stored and retrievable.
**Plans:**
- [x] 08-01: Full analytics results screen + time-to-X + athlete anthropometrics

### Phase 9: iOS Dashboard + History ✅
**Goal:** Multi-swimmer at-a-glance dashboard (latest session key metrics per athlete). Swimmer profile: session history list → tap to view full historical report card. Debug panel removed.
**Plans:**
- [x] 09-01: Dashboard + session history + report card viewer

---

## Milestone: v0.3 Metrics Quality ✅

**Goal:** Coach-facing data quality signals — cycle plausibility validation, magnet dropout reporting, outlier cycle counts, and kick metric reliability flags. Ensures coach knows when to trust (or retake) a session.

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 10 | Metrics Quality | 2 | Complete | 2026-05-25 |

### Phase 10: Metrics Quality ✅
**Goal:** (Plan 01) Backend: cycle quality stats in `metrics.py`, `data_quality` object in `/process` response, magnet dropout %. (Plan 02) iOS: display data quality card in RecordScreen results and ReportCardScreen historical report card.
**Plans:**
- [x] 10-01: Backend — cycle plausibility + outlier count + dropout % + data_quality object
- [x] 10-02: iOS — data quality display in results and report card

---

## Milestone: v0.3.5 Pipeline Tests 🚧

**Goal:** Pytest test suite covering the signal pipeline — no regressions when metrics or API changes are made.

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 11 | Pipeline Tests | 1 | Complete | 2026-05-25 |

### Phase 11: Pipeline Tests
**Goal:** Synthetic-fixture unit tests for `compute_session_metrics` (shape + no-crash, quality keys) and integration tests for `POST /process` (response shape, data_quality, magnet dropout computed correctly).
**Plans:**
- [x] 11-01: tests/conftest.py + test_metrics.py + test_api.py

---

## Milestone: v0.4 Coach Experience ✅

**Goal:** Coach-facing quality-of-life features — session naming, notes, starring, deletion, stroke-type filtering, pre-recording config, and non-breaststroke "coming soon" placeholders.

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 12 | QoL Features | 4 | Complete | 2026-05-25 |

### Phase 12: QoL Features ✅
**Goal:** (Plan 01) Backend schema + PATCH/DELETE endpoints. (Plan 02) Pre-recording config screen. (Plan 03) Session list: stroke filter + swipe-left star/delete. (Plan 04) Report card: editable name/notes/star + Coming Soon for non-breaststroke.
**Plans:**
- [x] 12-01: Backend — schema migration + PATCH/DELETE endpoints + /process metadata params
- [x] 12-02: iOS — RecordingConfigScreen (stroke picker, name, notes) + navigation update
- [x] 12-03: iOS — SessionHistoryScreen: stroke filter chips + swipe-left actions + richer cards
- [x] 12-04: iOS — ReportCardScreen: editable name/star/notes + Coming Soon non-breaststroke

---

## Milestone: v0.4.5 Graph Enhancements ✅

**Goal:** Interactive velocity chart — time markers, touch cursor, pinch-to-zoom, m/yd toggle, and live recording graph.

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 13 | Graph Enhancements | 3 | Complete | 2026-05-25 |

### Phase 13: Graph Enhancements ✅
**Goal:** (Plan 01) Extract shared VelocityChart + time marker line + m/yd unit toggle. (Plan 02) Interactive chart: touch cursor + pinch-to-zoom. (Plan 03) Live velocity graph during BLE recording.
**Plans:**
- [x] 13-01: iOS — shared VelocityChart component + time markers + m/yd toggle
- [x] 13-02: iOS — VelocityChart interactive: touch cursor + pinch-to-zoom + pan-when-zoomed
- [x] 13-03: iOS — live recording graph (on-device velocity approximation)

---

## Milestone: v0.5 Commercial Foundation

**Goal:** Billing, device management, and scaling for paying customers.

| Phase | Name | Status |
|-------|------|--------|
| 14 | Device Registration | Complete | 2026-06-08 |
| 15 | Billing + Tier Enforcement | ✅ Complete (2/2 plans) |
| 16 | Freestyle Support | Wavelet segmenter SHIPPED to production (16-05, placeholder quality, all strokes) 2026-06-12; tuning → future 16-06 |
| 22 | Video Overlay Validation | In progress (22-02 APPLY — Task 1 done; at device checkpoint, pay-per-build) |
| 23 | Website | ✅ Complete (3/3 plans) | 2026-06-11 |
| 24 | Parent Report Cards | ✅ Complete (3/3 plans) | 2026-06-11 |
| 25 | Codebase Audit | ✅ Complete (1/1 plans) | 2026-06-12 |
| 26 | In-App Video Overlay | In progress (26-01 Tasks 1+2 done; at EAS-build checkpoint) |
| 27 | Device Model (3D hero) | ✅ Complete (1/1 plans) | 2026-06-12 |
| 28 | Privacy Policy | ✅ Complete (1/1 plans) | 2026-06-13 |
| 29 | Marketing Content (FAQ + sales email) | ✅ Complete (1/1 plans) | 2026-06-14 |
| 30 | Website Copy Polish | ✅ Complete (1/1 plans) | 2026-06-15 |
| 31 | AI Coaching Chat | Planning (31-01 created — backend + web; iOS → 31-02) |
| 32 | SoCal Coach Outreach Research | ✅ Complete (1/1 plans) | 2026-06-16 |
| 33 | AI Coaching Chat v2 | ✅ Complete (3 plans shipped: 33-01/02/03) 2026-06-16 — semantic RAG / streaming / visual-proof deferred to future |
| 34 | Device Diagnostics | Code complete (34-01 ✅ firmware STATUS command + in-app Diagnostics screen; on-device verify deferred — EAS gate) |
| 35 | Feature Verification & Doc Reconciliation | ✅ Complete (3 plans) 2026-06-18 — 35-01 web (all WORKING) + 35-02 iOS (ratings UI + iPad de-scope verified, 2 bugs fixed, recording checks deferred to a post-resolder build) + 35-03 docs (CLAUDE.md + CODEBASE-AUDIT reconciled, Feature Status Ledger). Deferrals: post-resolder re-verify, threshold coach review, iOS parity phase |
| 36 | Coach-Friendly Metric Ratings | ✅ Backend+web complete (36-01 + 36-02) 2026-06-17; iOS shipped via 35-02 2026-06-18; go-live = user deploy (done — PR #5) |
| 37 | Team Coach Dashboard | ✅ Complete (2/2 plans) — 37-01 backend (GET /team/overview + ratings.summarize_team, suite 103) 2026-06-18; 37-02 web UI shipped 62a6f4f 2026-06-18, live on Vercel (status corrected + SUMMARY written retroactively 2026-07-30). iOS mirror already shipped via Phase 38-02 |
| 38 | Mobile UI/UX Redesign | ✅ Code-complete (6/6 plans, 2026-06-19); device verify → one EAS build |
| 39 | Redesign Fixes & UX Iteration | Planning (39-01 bug fixes created 2026-06-19; 4 bugs located + 7 design updates scoped) |
| 40 | Website Redesign (iOS match) | ✅ Complete (2/2 plans) 2026-06-22 — Template B gradient + shadcn + ContactDialog (landing core) + remaining sections restyled, pricing removed sitewide → Request-a-quote |
| 41 | Race-Start Sequence (iOS) | ✅ Complete (1/1 plan) 2026-06-22 — countdown + "take your marks" + random hold + blare; config toggle; device verify → next EAS build |
| 42 | Core-Flow Failsafes (iOS) | ✅ Complete (1/1 plan) 2026-06-22 — pairing/recording/results hardened; auto-recover or specific reason; device verify → next EAS build |
| 43 | Demo Readiness (runbook) | Planning (43-01 created 2026-06-22 — failure-mode catalog + pre-demo app/hardware checklist; doc only; autonomous:true) |
| 44 | Encoder Data Integrity (pulse + dump reconciliation) | In progress (44-01 diag + 44-02 applied 2026-06-22 — packet loss FIXED via indications ✅; warmup fooled by stable garbage + video overlay desync → 44-03: warmup min-time floor + end-anchored overlay sync) |
| 46 | Marketing Blog (build log) | ✅ Complete (1/1 plan) 2026-06-23 — /blog index + /blog/[slug] SSG posts (5 thematic, founder dev-journal, lightly-polished candid) + Nav/Footer link; build green, verified, checkpoint approved |
| 47 | Trial Annotation (review + ground truth) | ✅ Complete (4/4 plans) 2026-07-20 — 47-01 contract + 47-02 GUI + 47-04 recompute pushed e7f72f4/627419c; 47-03 iOS background video upload code-complete (export green, device-verify → next EAS build) |
| 45 | Cloud Session Save (device_id UUID→TEXT) | ✅ Resolved 2026-07-30 — patch_06 confirmed applied to the live DB (`information_schema` reports `sessions.device_id` = `text`); the 22P02 insert failure is gone and iOS cloud saves are unblocked. No app code was ever required. Follow-ups: commit the untracked patch_06 SQL; on-device save confirm rides the pending EAS build |
| 48 | Athlete-Create Fix | ✅ Applied + deployed 2026-07-30 — `.single()` dropped from the POST /athletes insert chain (api.py:1306-1314), supabase/postgrest==2.30.1 pinned, regression test against the real postgrest builder (tests/test_api.py:1068); suite 149 green; committed + pushed → Railway. Follow-up: human-verify by adding an athlete in the portal |
| 50 | Demo Team & Synthetic History | ⏸ **PAUSED 2026-08-03** (Phase-53 discussion) — the demo now runs on a REAL 10-session series, not the synthetic team. Seeder source CSVs are the pre-fix `raw/` corpus (all dated 2026-05-13→06-10, predating BOTH encoder-integrity fixes of 2026-06-22); user trusts 2-3 of 43, and 50-01's "24/43 usable" was a structural check, not a data-integrity one. NOT cancelled — reseed from clean sessions if a team-scale demo is wanted later (source swap, not a rewrite). ⚠ seed_demo_team.py still UNTRACKED, only copy — commit it. Prior status: Planning (50-01 created 2026-07-27 — demo can't show long-term tracking because no history exists. Replay + perturb real raw CSVs through the real pipeline into a demo coach account: 12 athletes × 12 sessions over 6 months, backdated. NEW seed_demo_team.py only — no product/schema/web changes. 50-01 = seeder core + Stage-1 archetype ingest; 50-02 = generate + propagate annotations + tune) |
| 51 | API Correctness & Audit | ✅ **Complete (2/2 plans) 2026-08-05** — 51-02 shipped `dedac17`: the phantom `athletes.coach_id` is gone from all four sites, `POST /athletes` works in production (AC-1 verified live), and `tests/test_api.py::TestSchemaContract` now fails the suite if any api.py column reference leaves the live schema (mutation-tested). Suite 172→176; schema violations 4→0. Task 2 was STRUCK before apply as superseded by 54-01's `ENFORCE_TIER_LIMITS`. ⚠ AC-3 (team-wide coach chat) + AC-4 (/billing/status athlete_count) UNVERIFIED — exercising AC-3 is what surfaced the wrong-athlete defect in row 56. Prior status: Planning (2026-07-30 — LIVE BUG: phantom `athletes.coach_id` referenced at 4 sites; POST /athletes 500s PGRST204, athlete limits never enforced, coach-chat team tools broken since 33-02, billing athlete_count always 0. AUDIT-FIRST per user 2026-07-30: 51-01 ✅ COMPLETE 2026-07-30 — API-AUDIT.md (11 findings, 24-endpoint inventory, ownership rule) + tools/introspect_schema.py + supabase/live_schema.json + tools/schema_contract.py; api.py untouched, suite 149. Escalations found: the true sample rate is DISCARDED at write time (api.py:143) and `teams` is read by iOS but never by api.py; 51-02 = fixes (four sites → team_id, athlete-limit behind ENFORCE_ATHLETE_LIMIT default OFF, AST schema-contract test), depends_on 51-01) |
| 52 | Sample-Rate Contract | ✅ **Complete (1/1 plans) 2026-08-03, closed 2026-08-05** — shipped `89205ca`, patch_09 applied live; suite 149→170. AC-1 (new session stores ~89 Hz, not 100) and AC-4 (pre-migration NULL-rate rows render byte-identically) verified live. ⚠ AC-2 (annotate-page duration) + AC-3 (recompute plausibility) still UNVERIFIED — both need a swim recorded after the migration. 52-02 (measure + backfill existing rows) remains a future plan. Prior status: Planning (52-01 created 2026-08-03 — API-AUDIT F2+F3. `run_pipeline` decimates by an integer factor so stored profiles are ~89.5 Hz, never 100, and api.py:143 discards the real value; 6 backend + 3 web consumers assume 100 → annotate page shows a 47.1 s swim as 42.2 s and recompute-from-annotation shifts every time-derived metric ~11.7%. FIX (user Option A, 2026-08-03): persist `sessions.sample_rate_hz` (patch_09, nullable, no default) and read it everywhere; NULL → 100 keeps existing rows byte-identical. 52-02 = measure + backfill existing rows. Lands BEFORE 50-02, whose annotation propagation would bake the error into ~144 sessions) |
| 54 | Gate Removal (tier enforcement + stroke gating) | ✅ **Complete (1/1 plans) 2026-08-05** — backend shipped in `dedac17` (could not be split from 51-02's commit); the mobile half sat uncommitted and unbuilt for two days, was folded into Phase 55-01, and freestyle analytics were VERIFIED ON DEVICE 2026-08-05. `ENFORCE_TIER_LIMITS` default OFF now covers all three limits, superseding 51-02's planned `ENFORCE_ATHLETE_LIMIT`. ⚠ Accepted consequence now LIVE: the team dashboard needs-attention list, inert since Phase 37, populates using breaststroke-derived bands applied to all strokes over segmentation flagged unreliable — Phase 53 decides whether those bands should exist. Prior status: Planning (54-01 created 2026-08-03 — remove every account-level restriction and the breaststroke-only analytics gate, both reversibly. TRIGGER: free-tier `device_limit`=1 blocked a live test, and `monthly_session_limit`=20 would 402 partway through the Phase-53 pool day. (T1) single module-level `ENFORCE_TIER_LIMITS` env kill switch, DEFAULT OFF, gating all three limit sites (session api.py:215, device :242, athlete :1291) so the count queries never run; SUPERSEDES 51-02's `ENFORCE_ATHLETE_LIMIT` — one switch, not two. Billing infrastructure (`_TIER_LIMITS`, Stripe webhook writes, /billing/status, schema columns) explicitly PRESERVED. (T2) ratings.py: bands fall back to the breaststroke table for every stroke + drop `(not seg_reliable)` from `provisional`; 2 contradicted tests INVERTED not deleted. (T3) mobile ReportCardScreen.js:192 `isAnalyticsReady` → true. KNOWN CONSEQUENCE, accepted by user: the team dashboard needs-attention list has been inert since Phase 37 because every pillar was provisional — it now POPULATES, driven by breaststroke-derived bands applied to all strokes over segmentation flagged unreliable. autonomous:false (human-verify after Railway deploy), depends_on 51-02) |
| 53 | Attention Allocation (SPC detection engine) | Planning (53-01 created 2026-08-03 — the instrument before the experiment: Track-A5 repeatability/saturation analyzer + pool-day protocol, requires NO collected data. NEW repeatability.py (pure: sigma_mr = mean(moving_range)/1.128, minimum detectable change, rails DERIVED from metrics._PERIOD_MIN_S/_MAX_S, usability ranking, zero-variance flagged suspect) + tools/analyze_repeatability.py (offline CLI; captures `actual_fs` from run_pipeline so it answers Phase 52's "does fs vary?" without touching Phase-52 files) + tests + COLLECTION-PROTOCOL.md. autonomous:true, depends_on []). Discussed 2026-08-03, CONTEXT.md written. PRODUCT REFRAME: the tool is not a magnifying glass — a head coach cannot track 30 swimmers across a 2-hour practice daily (~90 s attention per athlete per week), so the core value is ALERTING when something goes wrong OR RIGHT. Layer contract: measurement gate → contrast → persistence → co-occurrence → synthesis; HARD BOUNDARY at co-occurrence (no causal claims, no drill prescription). Framing = statistical process control, NOT anomaly detection; LLMs in the phrasing layer ONLY, detection deterministic. Verified: the shipped needs-attention list is INERT (provisional gate) and has been a calendar reminder since Phase 37; `_trend` is ±5% vs one session with no noise model; σ never measured. Roadmap: Track A (blocking) hardware gate → Phase 52 fs contract → collect 10 freestyle sessions in one day with injected perturbations → annotate all (Phase-47 tool) → saturation + repeatability = GO/NO-GO; Track B engine; Track C 90-second surface; Track D real weekly spacing + 16-06 + pilot. Supersedes the Phase-48 "freestyle unlock" (porting breaststroke thresholds is the wrong unlock — within-athlete contrast needs none) |
| 56 | Coach Chat Athlete Scoping (OPEN DEFECT, unscheduled) | Found 2026-08-05 during live use; user chose document-only, no plan. Asking the AI coach "give me info on Sid specifically" returned a DIFFERENT athlete's history under Sid's name — claimed a most-recent swim of Aug 5 when Sid has only two swims, both in May. ROOT CAUSE: `list_athlete_sessions` exposes no athlete parameter (schema is `limit` + `stroke` only, coach.py:141-142) and its executor is bound to the athlete of the session the chat was opened from (api.py:1494, `.eq("athlete_id", athlete_id)` closing over the anchor session). Naming another athlete cannot re-scope the tool, so the model receives the anchor athlete's rows and attributes them to whoever was named; `get_session_metrics` inherits the same anchor scope. This is cross-athlete data attribution, not merely an inaccurate answer. NOT caused by 51-02 (that path filters athlete_id + coach_id, untouched), though 51-02's repair of the team tools makes the chat sound more authoritative while still mis-attributing. Fix direction: either add an athlete_name/athlete_id parameter resolved against the coach's roster, or make the system prompt state that athlete tools are locked to the anchor swimmer so the model declines rather than substitutes |
| 55 | Athlete Flow Fixes (mobile) | ✅ **Complete (1/1 plans) 2026-08-05** — checkpoint approved on the EAS build. All three symptoms traced to ONE fact: `RecordingConfig` is a tab screen that mounts once per app launch and never remounts, so `useEffect(…,[])` ran once ever (frozen roster), `useState()` initializers ran once ever (params ignored), and it sits under `Tabs` not Root (unreachable by bare name). Fixes: `useFocusEffect` roster refetch; nested `navigate('Tabs', {screen, params})` from AthleteDetail; a params effect that applies AND clears (clearing is required — on a never-unmounting screen params persist, so a later plain tab press would inherit the previous athlete). `RootTabs.js:21`'s comment, which had asserted cross-screen navigation "keeps working" and was the assumption that produced the bug, now documents the Root→Tab rule and warns it fails SILENTLY. Phase 54-01's `isAnalyticsReady` one-liner rode the same build → **freestyle analytics verified on device**, clearing 54-01's last outstanding piece. Build also cleared six deferred iOS checks (47-03/41/42/44-03/21-02/34-01). AC-2/3/4 pass; AC-1 partial. ⚠ KNOWN GAP (user: note only, not fixed): deleting the CURRENTLY SELECTED athlete clears them from the dropdown but leaves them in the selection bar — `athlete` state is independent of `athletes` and the focus refetch never revalidates the selection. Matters beyond cosmetics: recording against that stale selection would submit a deleted `athlete_id`. One-line fix recorded in 55-01-SUMMARY.md. Prior status: Planning Found while verifying the 51-02 checkpoint — athlete creation works now, and exercising the unblocked flow surfaced two defects in `swimnetics-mobile`. (B1) A new athlete is missing from the record screen until the app restarts: `RecordingConfigScreen.js:42` fetches the roster in a mount-only `useEffect`, but it is a TAB screen so it mounts once per launch; the three sibling data-bearing tab screens already use `useFocusEffect` and this is the only one missed. (B2) The Record button on the athlete screen is a silent no-op: Phase 38-03 moved `AthleteDetail` to the Root stack (`RootTabs.js:46`) while `RecordingConfig` is a tab child (`:29`), and `navigate()` only bubbles UP to parents — never down into a child navigator — so nothing handles the action; needs `navigate('Tabs', { screen: 'RecordingConfig', params })`. The comment at `RootTabs.js:21-23` asserting cross-screen navigation "keeps working" went stale in the same commit. Verified as the only Root→Tab navigate call in the app — not a bug class. OUT OF SCOPE by user decision: delete-athlete is unchanged (it exists behind a `⋯` glyph at `AthleteDetailScreen.js:96`; user had never noticed it, tested it, judged it fine — the Team list having no delete while sessions have swipe-to-delete is recorded for a later UX pass, along with the fact that athlete delete writes direct via supabase-js on RLS rather than through the API); a dev-time guard for silently-unhandled navigate calls was offered and declined. Mobile repo only. Verification = a new EAS build the user runs right after apply, which should batch the iOS checks deferred from 54-01/47-03/41/42/44/21-02/34-01. UPDATED 2026-08-05 after live use: B1's symptom is broader than first reported — the roster is frozen at app launch in BOTH directions, so a DELETED athlete also stays on the record screen until restart; same cause, one fix. B3 FOLDED IN by user decision: freestyle analytics still blocked on the iPhone, which is NOT a bug — `ratings.py`'s threshold fallback shipped live in `dedac17`, but 54-01's `isAnalyticsReady = true` is uncommitted in the mobile working tree and has never been built (mobile HEAD 1296494 still carries the breaststroke-only gate at ReportCardScreen.js:169). 55-01 commits it so one paid build carries everything; no new code |
| 49 | Security Hardening (backend) | Planning (49-01 created 2026-07-20 — bang-for-buck fixes from a full-surface security review: redact 14 internal-error leaks, CORS `["*"]`→env allowlist, memory-safe upload size caps, athlete-ownership check on /process; api.py+tests only; autonomous:false, human-verify. Deferred: rate limiting, report-token expiry, full dep pinning) |
| 57 | Annotation Workflow (annotate-tool v2) | Planning (57-01 created 2026-08-05 — backend contract + pipeline, awaiting approval; 57-02 web page + 57-03 queue to follow). Discussed 2026-08-05 via /paul:discuss; CONTEXT.md written. TRIGGER: 19 trustworthy sessions collected 2026-08-05 (10 free / 4 br / 4 fly / 1 back) — the first corpus postdating the encoder-integrity fixes, and the blocking input to Phase 53 Track A4 and Phase 16-06. The Phase-47 tool works but was verified at n≈1; 19 in a sitting exposes throughput, precision and semantic gaps. REPO-VERIFIED (contradicts the request's framing): trailing trim ALREADY works via `finish_s`→`swim_end_idx` — what is missing is feedback, not mechanism; non-overlap is ALREADY guaranteed by `validate_annotation`'s ordering check — the UI just never says so, showing a bare "Dive 1.31 s" that reads as a duration. REAL HOLES: stroke marks are not constrained to the swim window (a stray mark in the dead tail becomes a garbage cycle feeding stroke_rate/DPS), `stroke_start_s` and the first mark can silently diverge, only 3 of 5 markers reach the metrics (`initial_phase` is carried over from the auto result at api.py:896), and `v95` (metrics.py:431) is computed over the FULL trace so the dead tail biases every session's dead-spot threshold. DECISIONS (user, AskUserQuestion ×4 rounds): view-fit chart + the swim window made AUTHORITATIVE (out-of-window marks rejected; v95 windowed) with profiles never truncated; the v95 fix applies pipeline-wide, accepting that dead_spot_s/coast_fraction stop being comparable with previously computed sessions; ONE MARK PER ARM ENTRY everywhere, cycles derived by pairing (2 marks/cycle free+back, 1 fly+breast — physiology, not a user choice), pairing factor derived from stroke_type with NO new column; NO PRELOADED MARKS — the editor starts blank (user: "in annotation, it should not have any preloaded"), which is methodologically stronger than what was offered since seeding ground truth from the segmenter being evaluated is circular; no auto-assist; UW kick + Breakout stay ground-truth-only and the UI says so; batch queue + prev/next IN scope. REACTION TIME: `useStartSequence.run()` resolves AT the blare and START is written after it, so t=0 IS cue-anchored (confirmed enabled on all 19) — but the BLE round trip plus the firmware's VARIABLE 150–300 ms warmup discard (ESP_32_V5.ino:383-392) understate true reaction time by 25–50%, differently each trial, and no firmware change can retroactively fix the 19 already collected. So: record `dive_start_s`, caption it a lower bound, ship NO reaction_time_s metric. ACCEPTED RISK: ~500 hand-placed marks on a trace with no video, where each freestyle cycle shows ~2 peaks that cannot be attributed to a specific arm — per-session and per-cycle-only alternatives were offered and declined; the marks record alternation timing, not verified arm identity, and the UI must say so. Context: .paul/phases/57-annotation-workflow/CONTEXT.md |

### Phase 57: Annotation Workflow (annotate-tool v2)
**Goal:** Make the Phase-47 annotation tool survive its first real batch — 19 sessions, ~500 marks —
by fixing what n=1 verification could not surface. Three axes: (1) make the swim window **visible and
authoritative** — the chart fits it, and nothing outside it can contaminate a metric; (2) make the
phase model **explicit** — every marker states that it is a *start*, which interval it opens and
closes, and whether it moves any number; (3) make the ground truth **uncontaminated** — the editor
starts blank, because seeding from the segmenter that 16-06 exists to evaluate is circular.
**Plans:**
- [x] 57-01 ✅ **COMPLETE 2026-08-05** — all 5 ACs pass, suite 176 → 236, zero failures, no existing
  assertion re-baselined. Shipped: arm-entry pairing (`MARKS_PER_CYCLE`, k=1 path byte-identical to
  pre-57 and pinned by 28 identity assertions), swim-window rejection of out-of-window marks (422
  before any write), `_window_v95` at both leaking sites, `stroke_type` threaded onto both annotation
  endpoints with `marks_per_cycle` + `cycles_derived` published. ⚠ PLAN CORRECTION found by
  measurement: `coast_fraction` does NOT depend on `v95` (it scales by each cycle's own
  `arm_peak_vel`) — the accepted comparability cost is `dead_spot_s` + peak detection ONLY, narrower
  than planned. Measured with a realistic 45% dead tail: v95 +6.4% to +12.2%, `dead_spot_total_s`
  +1.6% to +3.7%, cycle counts unchanged everywhere. ⚠ OPEN: `stroke_type` correctness on the 19
  collected sessions is unverified and NOT patchable through the API — check before annotating.
  NOT committed. SUMMARY: 57-01-SUMMARY.md. Original scope follows. Deliberately
  first — annotations created against the old contract would have to be redone. `annotations.py` learns
  that one mark is one ARM ENTRY (`MARKS_PER_CYCLE` = 2 for free/back, 1 for everything else including
  `im`/`udk`/unknown, so the default path is byte-identical to today) and rejects stroke marks outside
  `[stroke_start_s, finish_s]`; `metrics.py` computes `v95` over the swim window at both leaking sites
  (`compute_session_metrics` — the statement must MOVE, it currently precedes `detect_phases`; and
  `extract_cycle_peaks`, which drives peak DETECTION thresholds); `api.py` threads `stroke_type` onto
  both annotation selects and publishes `marks_per_cycle` + `cycles_derived` so the pairing rule is
  never duplicated in JS and a wrong (unpatchable) `stroke_type` is visible immediately.
- [ ] 57-02: Annotate page v2 — PLAN created 2026-08-05, awaiting approval (web only, 3 files;
  3 tasks + 1 human-verify checkpoint; autonomous:false, depends_on 57-01). Blank start (D6 — the
  seed is still returned by the API but never applied); view fitted by SLICING the data rather than
  setting an XAxis domain, because the existing `<Brush>` also controls the domain and the two fight
  — slicing additionally re-spreads the 2000-point decimation over the shorter span, which is the
  precision win; fit range is **[0, finish+margin]**, lower bound never `stroke_start`, because the
  leading region is the reaction-time measurement; `ReferenceArea` bands make "phases tile and never
  overlap" visible instead of asserted; phase rows become intervals with a persistent tag saying
  whether each moves a number (UW kick + Breakout do not); Dive captioned as a lower bound; live
  "N marks → M cycles" derived exactly as `annotation_to_overrides` does, k==1-only finish-append
  included; undo stack held in a ref (state would re-render the chart on every one of ~500 clicks);
  drag + arrow-key nudge; client-side out-of-window guard mirroring the server rule; DELETE wiring
  so the old-convention 20:24 annotation can be discarded and redone. "Reset to auto" is REMOVED —
  under D6 it contradicts the point of the phase.
- [ ] 57-03 (next): Annotation queue page + prev/next navigation (D8).

### Phase 52: Sample-Rate Contract
**Goal:** Stop the system from lying about its own clock. `vel_acc_extraction.decimate_signal`
decimates by an **integer** factor (`round(268.5 / 100) = 3` → 89.5 Hz), so the requested 100 Hz is
never achieved, and `api.py:143` throws the returned `actual_fs` away. Nine consumers then assume
exactly 100 — three of them on the annotation path, including the recompute time axis. Real impact
on real sessions: a 47.1 s swim displays as 42.2 s, and recomputing metrics from a saved annotation
shifts stroke rate, lap time and DPS by ~11.7%. Two bounding facts: stored cycle *indices* are not
corrupted (the time→index round trip uses the same wrong constant both ways), and the original auto
metrics are correct (`compute_session_metrics` runs on the true `t_dec` clock inside `/process`) —
so damage is confined to sessions recomputed from an annotation. Found by the Phase-51 audit
(F2 + F3) and escalated there as likely more serious than the F1 500, because it is silent.
**Approach (user decision 2026-08-03, Option A):** persist the true rate per session rather than
correcting a constant — right for every session, and it survives firmware and device changes.
**Plans:**
- [ ] 52-01: `sessions.sample_rate_hz` (patch_09, nullable, no default) + persist on `/process` +
  read it on the annotation / recompute / export paths + the three web time axes + docs. NULL falls
  back to 100 so un-backfilled rows behave exactly as they do today. autonomous:false
  (human-action to apply the SQL, human-verify in the live portal).
- [ ] 52-02 (future): measure how many stored sessions carry annotation-recomputed (corrupted)
  metrics — the SQL is in `API-AUDIT.md` — then decide migration vs. footnote and repair them.

### Phase 14: Device Registration ✅
**Goal:** Auto-register ESP32 devices via chip_id on first session upload. Expose firmware version via BLE characteristic. API endpoints to rename and list devices. Fills `device_id` on sessions.
**Plans:**
- [x] 14-01: Firmware FW_UUID + api.py device endpoints + Supabase schema

### Phase 15: Billing + Tier Enforcement ✅
**Goal:** Stripe subscription management. Two tiers: Starter ($200/mo, 20 athletes, 1 device) and Enterprise ($1,000/mo, 500 athletes, 10 devices). Free tier: 3 athletes, 1 device, 20 sessions/month. Stripe Customer Portal for self-serve management. Limits enforced in api.py on /process and athlete creation.
**Plans:**
- [x] 15-01: Stripe setup + Supabase billing schema + checkout/portal/webhook/status endpoints
- [x] 15-02: Tier enforcement in /process + POST /athletes proxy + iOS 402 error handling

### Phase 17: UX Polish ✅
**Goal:** Fix four confirmed coach-facing bugs: dynamic stroke filter chips (hide strokes with no sessions), swipe-to-star/delete gets stuck, velocity chart scrub causes page scroll, keyboard covers notes field. Code scan surface-finds addressed in same pass.
**Plans:**
- [ ] 17-01: SessionHistoryScreen chips + swipe snap + VelocityChart scroll conflict + ReportCard keyboard

### Phase 18: Design Refresh
**Goal:** Visual redesign of all 6 iOS screens matching the Swimnetics Screens mockup: wave logo on Login, letter avatars on Athletes, 3-column history cards, SESSION summary card on Report.
**Plans:**
- [x] 18-01: Login wave logo + VELOCITY INTELLIGENCE + Athlete letter avatars
- [x] 18-02: History 3-col cards + Report SESSION summary card

### Phase 19: iOS Bug Fixes ✅
**Goal:** Fix three coach-facing bugs confirmed from Phase 17/18: filter chips inconsistent pill shape, swipe-left doesn't always snap open and never closes on tap, ReportCardScreen still light-themed.
**Plans:**
- [x] 19-01: Chips + swipe + ReportCardScreen dark theme + star sync + action button clipping

### Phase 20: Device Management ✅
**Goal:** iOS DevicesScreen accessible from AthletesScreen gear icon. Shows registered encoder(s) with firmware version, last active date, session count. Supports inline rename and deregister. Backend: GET /devices enriched with session_count; new DELETE /devices/{chip_id}.
**Plans:**
- [x] 20-01: Backend session_count + DELETE + iOS DevicesScreen + gear icon entry

### Phase 21: BLE Persistence + Device Pairing UX ✅ (code; on-device UAT deferred — no EAS credits)
**Goal:** Shared BleContext lifts connection state above the navigation stack — connection survives navigating away and app backgrounding. Pairing flow moves to DevicesScreen (scan once, stored via SecureStore). RecordingConfigScreen shows a "pick device" list. RecordScreen drops scan/connect UI and reads device from context.
**Plans:**
- [x] 21-01: BleContext + App.js + DevicesScreen pair flow (2026-06-10)
- [x] 21-02: RecordingConfigScreen device picker + RecordScreen rebuilt on BleContext + buffer-and-dump retrieval (2026-06-10 — code complete; device checkpoint deferred, EAS build credits exhausted)

### Phase 22: Video Overlay Validation
**Goal:** Produce one velocity-overlay demo video using only a phone (business-model
assessment Risk #0 — the "why not TritonWear" proof point). ESP32 firmware moves from
live-streaming to buffer-and-dump: button-only recording into RAM, BLE retrieval
afterward with session-start metadata (META command). Sync via wall-clock offset
(phone retrieves session + records video → one clock), not a visual marker —
camera-agnostic, extends to underwater footage later. `video_sync.py` gains
`--video-origin-s` alongside the existing GoPro sync-frame workflow.
**Plans:**
- [x] 22-01: Firmware buffer-and-dump + META/DUMP, logger_ble.py bench support, video_sync.py --video-origin-s (2026-06-10)
- [ ] 22-02: iOS RecordScreen retrieval flow + sessionStartPhoneMs clock correlation + end-to-end overlay validation (sequence vs. Phase 21 Plan 02 — both touch RecordScreen.js)

### Phase 23: Website
**Goal:** Full Swimnetics website (Next.js in `web/`, Vercel target) replacing the
`landing/index.html` placeholder. Public marketing site — dark tech theme matching the
iOS palette, Three.js 3D device hero (placeholder primitives now, Fusion 360 GLB drop-in
later), features, sample velocity chart, informational pricing at **$15/swimmer/month**
(supersedes $200/$1,000 tier presentation; no Stripe wiring). Plus an authenticated coach
portal with iOS-app parity (dashboard, athletes, session history, full report card) and
Streamlit-demo analytics (compare mode, per-cycle advanced view). Recording stays
iOS-only; device management descoped. Plans applied back-to-back ("one shot").
**Plans:**
- [x] 23-01: Next.js scaffold + design system + marketing site + Three.js device hero (2026-06-10)
- [x] 23-02: Coach portal core — auth, dashboard, athletes, history, report card (2026-06-10; api.py CORS pre-existed)
- [x] 23-03: Compare mode + per-cycle advanced analytics + deploy runbook + visual checkpoint (2026-06-11, approved)

### Phase 24: Parent Report Cards
**Goal:** Web-portal feature: coach generates shareable swimmer progress report cards
for parents. Coach picks date range + metrics (preset: avg/top speed, stroke rate, DPS,
lap time, consistency — parent-friendly labels, no jargon) + personal message; each
report gets a tokenized public URL (`/report/{token}`, no parent account) rendered as a
mobile-first animated page: count-up improvement deltas (direction-aware, declines shown
neutrally), touch trend charts, coach message, brand footer. Mass send = swimmer
multi-select → bulk generate → send list with per-parent **mailto drafts + copy-link**
(real email provider deferred by decision; structure slots Resend in later). Schema:
parent_name/parent_email on athletes + reports table (patch_03, user-applied). Public
payload served by new no-auth `GET /reports/{token}` in api.py (service role).
**Plans:**
- [x] 24-01: patch_03 schema (parent cols + reports table + RLS) + GET /reports/{token} + tests (2026-06-11; user applied patch)
- [x] 24-02: Portal — parent fields on roster, report builder (multi-select/range/metrics/message), send list (mailto/copy, sent tracking) (2026-06-11)
- [x] 24-03: Parent-facing /report/[token] page (animated hero deltas + trend charts) + end-to-end checkpoint (2026-06-11, approved)

### Phase 16: Freestyle Support
**Goal:** Stroke-agnostic cycle segmentation + freestyle metrics. Originally scoped as
"parameterize `metrics.py` thresholds per stroke type" — Plan 16-01's research found the
gap is algorithmic, not parametric: `segment_cycles_trough` anchors on breaststroke's
glide-phase trough, which freestyle/butterfly don't have (continuous/near-simultaneous
propulsion, no near-zero dead spot). Direction: matrix-profile motif-matching (`stumpy`)
as a shape-based, stroke-agnostic segmentation criterion. Stroke type on athlete profile
remains in scope.
**Plans:**
- [x] 16-01: Research spike — single-template motif-matching (CLOSED: regime-locks under drift)
- [x] 16-02: Research spike — chains + Arc Curve/CAC (CLOSED: no better; surfaced dive/pulldown contamination)
- [x] 16-03: Research spike — multi-length PMP heatmap (CLOSED: real structure, no decision rule; shape-matching family parked)
- [x] 16-04: Wavelet/CWT stroke-rate ridge spike — GO verdict 2026-06-12. Ran on the
  11-session set (8 br + 3 free/fly); breaststroke calibration weak (3/8 within ±5 SPM,
  4 sessions rail the 120-SPM ceiling) but the ridge was judged promising on the
  scalograms. Wavelet ridge is now the standing freestyle-segmentation direction (first
  non-"close" verdict after the 3 shape-matching spikes). Implementation — close the
  rate-accuracy/boundary gap, wire into metrics.py — deferred to a future 16-05 plan.
- [x] 16-05: Ship wavelet ridge as the SOLE production segmenter for all 4 strokes
  (segment_cycles_wavelet in metrics.py; trough kept as never-called backup);
  segmentation_reliable=False flag in session + /process data_quality; PyWavelets dep;
  tests re-baselined (2026-06-12). PLACEHOLDER quality — freestyle/fly now segment
  (carlos_fr_1=17, carlos_fl_1=8, lucas_fl=3 cycles); breaststroke regression accepted.
  Tuning (rate accuracy, ceiling-railing) → future 16-06.

### Phase 25: Codebase Audit
**Goal:** Full-surface review of the system — iOS app (swimnetics-mobile), website
(web/), firmware (ESP_32_V5 + motor_logger_esp32; legacy sketches cataloged only),
backend (api.py + pipeline), Supabase schema, deploy targets. Verify every
cross-system contract (BLE protocol, API endpoints vs callers, schema columns,
physical constants), run pytest + web build, probe live Railway read-only for
deploy drift. Output: CODEBASE-AUDIT.md (folder maps, connection matrix,
working/broken/unverified, future-AI pickup guide) + surgical staleness fixes to
CLAUDE.md / AGENTS.md in both repos. Documentation-only — no code fixes.
**Plans:**
- [x] 25-01: Connection audit + CODEBASE-AUDIT.md + AI-context refresh (2026-06-12 —
  7 findings in audit §5; critical: Railway pre-Phase-24 drift confirmed live,
  .gitignore excludes production files from git in both repos)

### Phase 26: In-App Video Overlay
**Goal:** Productize Phase 22's overlay as a phone-native feature. One-tap "Record with
Video": the app writes BLE START + starts the in-app camera together (app-timestamps
`videoStartPhoneMs = Date.now()` at recordAsync — exact, no file metadata), then STOP +
the existing META/DUMP/process pipeline, and opens a playback screen with the velocity
trace synced to the video (`VelocityChart` markerTimeS cursor + m/s readout + ±nudge).
Sync = `sessionStartPhoneMs` (META) − `videoStartPhoneMs`. In-app camera keeps Swimnetics
foreground so BLE survives; buffer-and-dump means BLE isn't needed during the swim anyway.
Reuses RecordScreen's BLE pipeline (no refactor); ESP32 unchanged. Adds expo-camera +
expo-video (native → EAS build). MVP: just-recorded, in-app record, interactive playback.
Supersedes the parked 22-02 manual laptop demo (kept as fallback).
**Plans:**
- [ ] 26-01: expo-camera/expo-video + "Record with Video" mode (BLE START/STOP + in-app
  camera, reusing dump/process) + VideoOverlayScreen synced playback + on-device checkpoint

### Phase 28: Privacy Policy
**Goal:** Publish a Privacy Policy page on the marketing site (`web/app/privacy`)
that accurately describes Swimnetics' real data practices, with a children's-data
(COPPA) section reflecting the B2B club-as-customer consent model, linked from the
footer. Prompted by the 2026-06-13 legal discussion on storing minors' performance
data. Privacy Policy ONLY — the companion ToS (operative parental-consent clause)
and attorney review are deferred follow-ups; no deploy (user-owned). Static content
page; no backend changes.
**Plans:**
- [x] 28-01: web/app/privacy/page.js (10-section policy, dark theme tokens) +
  Footer link + human-verify legal-content checkpoint (2026-06-13, approved).
  Follow-ups: ToS (parental-consent clause) + attorney review before paid pilot
  with minors; living doc — revisit on data-practice changes.

### Phase 27: Device Model (3D hero)
**Goal:** Replace the marketing hero's primitive placeholder with the real
`device_model.glb` (8.24 MB Fusion 360 export). Auto-fit the loaded model
(bounding-box recenter + auto-scale, robust to the export's arbitrary scale/origin/
up-axis), keep the existing auto-rotate + cursor-tilt parallax (no drag, no
compression — user decisions), placeholder retained as error-boundary fallback.
Parallel to Phase 26 (no file overlap — web only).
**Plans:**
- [x] 27-01: Move GLB into web/public/models/, auto-fit loader in DeviceScene.js, visual checkpoint (2026-06-12, approved — angled 3/4 pose)

### Phase 29: Marketing Content (FAQ + sales email)
**Goal:** Publish a website FAQ page (`web/app/faq`) answering the real coach objections
surfaced in the 2026-06-14 sales roleplay (value vs. stopwatch, ease of use, coach-not-
replaced, pool-time/throughput, durability, supported strokes, pricing, data safety),
linked from Nav + Footer. Produce a copy-paste sales-pitch email
(`marketing/sales-pitch-email.md`) for coach outreach. Adopt a NEW pricing model given
2026-06-14 — **$300 one-time device (basic metrics) + $20/swimmer/month cloud tier (video
storage, long-term tracking)** — which supersedes the Phase 23 $15/swimmer/mo and forces
two consistency updates: `Pricing.js` (the model) and `privacy/page.js` (the live policy
promises "no video stored"; the cloud tier stores video — §2/§4/§6 + date). Content-only;
no deploy (user-owned); minors'-video disclosure flagged for attorney review.
**Plans:**
- [x] 29-01: /faq page + Nav/Footer links + Pricing.js + privacy update + sales-pitch
  email + human-verify checkpoint (2026-06-14, approved). New pricing model ($300 device +
  $20/swimmer/mo cloud) adopted; privacy policy updated for cloud video storage.

### Phase 30: Website Copy Polish
**Goal:** Fine-tune the marketing site (`web/`) for buyers, not engineers. Rewrite every
non-legal paragraph shorter + drop build jargon ("encoder", "~270 Hz", "server-side",
"pipeline"); move the interactive velocity chart directly after the Hero; add a hover
tooltip showing the m/s y-value; remove the "glide" marker (keep "arm pull"); show a
sample value on each Features metric card; replace the wave logo with a text-only
"SWIMNETICS" wordmark everywhere (Nav/Footer/login/portal/report — delete WaveMark.js).
Legal pages (/privacy, /faq) untouched. Content/UX polish only; no deploy (user-owned).
**Plans:**
- [x] 30-01: Concise copy rewrite + logo removal sitewide + chart reorder/tooltip/
  glide-removal + sample values on metric cards + human-verify checkpoint (2026-06-15,
  approved). Checkpoint scope adds: new "Stroke-level analysis." Hero + research-grade-lab
  tagline; whole Features block moved directly under the chart. Email → info@swimnetics.com.

### Phase 31: AI Coaching Chat
**Goal:** Add Claude API coaching chat to the product surfaces, proxied through FastAPI
(Anthropic key server-side — PROJECT.md "Should Have"), reusing the Streamlit demo's prompt
convention (`coach.py`). New `POST /coach/chat` endpoint: client sends `{session_id, messages,
simple?}`; backend enforces auth + coach ownership BEFORE any model call, rebuilds the exact
`coach.py` system prompt + per-cycle data block from the stored `metrics_json` (no PII, no
client-injected data), and returns non-streaming `{reply}`. Guardrails (what the AI can/can't
answer) added to `coach._build_system_prompt` (shared with Streamlit): swim-coaching scope only,
redirect off-topic, defer medical/nutrition/mental-health, no fabricated metrics + surface
data-quality caveats, prompt-injection resistance. No usage cap / no tier gate this phase
(user decision); `anthropic` already a dependency. Sequence: backend + web first, iOS later.
**Plans:**
- [ ] 31-01: Guardrails in coach.py + POST /coach/chat proxy + tests + web CoachChat on the
  session report card + human-verify checkpoint (backend + web)
- [ ] 31-02 (future): iOS Coach Chat on the report card screen — reuses the same /coach/chat
  contract; needs a paid EAS build for on-device verification

### Phase 33: AI Coaching Chat v2 ✅ (closed at 3 plans, 2026-06-16)
**Closed:** shipped 33-01 (cross-session), 33-02 (team-wide), 33-03 (drill recommender) — the
chat is now conversational, team-aware, and ends with a grounded drill. Remaining capabilities
(semantic RAG, streaming + saved history + live verify, visual proof) are deferred to future
work, NOT part of this closed phase. Live human-verify (and Phase 31's deferred verify) ride
the future 33-05.
**Goal:** Upgrade the Phase 31 coaching chat from single-session to a genuinely
conversational coaching assistant. Four capabilities (all user-requested): cross-session
trend awareness, self-serve data access, a coaching knowledge base, and better chat UX
(streaming + saved history). DECISION (2026-06-16): NO LangChain — the Anthropic SDK
(native tool-use, streaming) + Supabase (pgvector) cover every goal without burying the
`coach.py` prompt under framework abstractions; tool chosen per-feature. Phase 31's deferred
live human-verify is folded into 33-03 (user: "build on it, verify together at the end").
**Plans:**
- [x] 33-01: Conversational data access — `coach.COACH_TOOLS` (list_athlete_sessions,
  get_session_metrics) + bounded native tool-use loop in `/coach/chat` with athlete+coach-scoped
  executors + tests. Delivers cross-session trends + self-serve access. (2026-06-16; 45 tests;
  PR feat/coach-chat-cross-session.)
- [x] 33-02: Team-wide tools — `roster_metrics.py` (pure) + `coach.TEAM_TOOLS` (rank_athletes,
  rank_progress, team_summary) + coach-scoped executors in the same loop. Answers "who's lagging?",
  "who progressed most?", "how's my team?". Returns athlete names (coach owns roster); kick-ranking
  declined (kick metrics unreliable). `/coach/chat` now also returns structured `data` (visual-proof
  hedge). Backend only, no new dep. (2026-06-16; 54 tests.) Cohort/gender + dashboard UI deferred.
- [x] 33-03: Drill library + metric tag-matching recommender — `drills.py` (8 flagship drills,
  flag taxonomy, `flags_from_session` + `match_drills`) + `coach.DRILL_TOOLS` (recommend_drills) +
  executor in the loop. Grounds the call-to-action: data→drill→why, only-from-library guardrail,
  honest "looks solid" when nothing flagged. No new dep. DRAFT content (coach review owed).
  (2026-06-16; 64 tests.)

**Deferred to future work (not part of the closed phase scope):**
- [ ] 33-04 (future): Semantic drill RAG — embeddings (e.g. Voyage/OpenAI) + in-memory cosine over
  the drill corpus + a `search_drills` tool for free-text drill questions ("breathing drill?").
  The "dip into RAG" piece. NEW dependency + API key + cost (user-owned) — isolated on purpose.
- [ ] 33-05 (future): Streaming (Anthropic SSE) + persisted `chat_messages` table + web UI +
  human-verify checkpoint (also closes Phase 31's deferred live verification).
- [ ] 33-06 (future): Visual proof — render the structured `data` from `/coach/chat` as a small
  comparison table/mini-chart under the answer, and/or deep-link to the existing Phase 23 compare
  view. Front-end-only (backend already returns `data`). Recommended: reuse the compare page.

### Phase 32: SoCal Coach Outreach Research
**Goal:** Turn "cold email some coaches" into a prioritized, evidence-backed target list for
**interest-only** outreach (gauge interest / ask for feedback — not a sales pitch). Two deliverables
in one doc (`marketing/socal-coach-outreach.md`): (Part A) a weighted "ideal target club" qualities
rubric anchored on the real product (encoder-only, 1–2 shared units, periodic testing) and the
user's seeds — mid-sized team, has a national/senior group, open to new tech; (Part B) a scored
shortlist of ≥12 real greater-SoCal clubs (LA, Orange County, San Diego/Imperial, Inland Empire —
weighted evenly) with coach/contact, per-quality scoring, A/B/C tier, and a "why reach out" note.
Marketing-research only — no code/firmware/web changes, no email copy this phase (reuse
`marketing/sales-pitch-email.md` later), no sending. Decisions (user, 2026-06-16): interest-only;
all-SoCal-even geo; rubric + research only.
**Plans:**
- [x] 32-01: marketing/socal-coach-outreach.md — Part A qualities rubric + Part B scored 16-club
  shortlist (OC/LA/SD-Imperial/Inland, balanced) + Part C club social presence + Part D media-presence
  coaches (Dave Salo→Irvine Novaquatics 2026, Mark Schubert; Gary Hall Sr. out-of-region). Parts C+D
  added mid-execution per user follow-ups. Interest-only, no email copy (deferred). marketing/
  gitignored — local-only. (2026-06-16)

### Phase 34: Device Diagnostics
**Goal:** Make hardware failures legible on the phone. Today when a recording fails
the coach gets only "no recording found" with no cause — the firmware already knows
(magnet not detected, encoder not reading, empty buffer) but only logs it over USB
serial, invisible at poolside. Add a firmware `STATUS` BLE command returning a live
15-byte status packet (AS5600 magnet/AGC/raw-angle + recording/buffer state; length
chosen to not collide with the sample/META/end-marker demux) and an in-app
"Diagnostics" screen (reachable from DevicesScreen) that polls it ~2 Hz and renders
plain-English magnet/wiring, recording/buffer, and BLE-link health. Diagnoses the
exact failure the user hit (magnet-not-detected refusal → 10 Hz flash → idle →
"no recording found"). Two repos (firmware here + iOS swimnetics-mobile); on-device
verify rides a paid EAS build.
**Plans:**
- [x] 34-01: Firmware STATUS command + readAgc() + DiagnosticsScreen.js + DevicesScreen
  entry + nav registration (2026-06-16 — code complete; iOS bundle green, firmware by
  structural review). On-device checkpoint (magnet/wiring + record/buffer + link) DEFERRED
  to a later plan per user — needs firmware reflash + paid EAS build. PR creation skipped
  (PR-TICKETS.md retained). SUMMARY: 34-01-SUMMARY.md.

### Phase 35: Feature Verification & Doc Reconciliation
**Goal:** Verify everything Swimnetics claims to support actually works, then make the
docs/comments tell the truth. Three sequenced stages (user request, 2026-06-17): (1) WEB —
marketing site + public report pages + authenticated coach portal + live `/coach/chat`,
local dev first then prod spot-check; (2) iOS — one paid EAS build batching the deferred
on-device checkpoints (34-01 diagnostics, 21-02 buffer-and-dump recording UAT, 26-01 in-app
video overlay, 22-02 laptop overlay demo), with firmware STATUS reflash; hardware on hand;
(3) DOCS — update stale comments/files (CLAUDE.md, CODEBASE-AUDIT.md, STATE/ROADMAP deferred
issues) and clearly mark what is finished vs. deferred, driven by stages 1–2 findings. User
confirmed: verify both local + prod; test coach login + seeded data exist; ANTHROPIC_API_KEY
set on Railway; ESP32 encoder + iPhone available.
**Plans:**
- [ ] 35-01: Web verification — public surfaces + portal + live chat, local then prod;
  35-01-WEB-FINDINGS.md (WORKING/BROKEN/DEFERRED) + in-scope web fixes + human-verify
  checkpoint.
- [x] 35-02: iOS verification — shipped iOS ratings UI (RN PillarCards + Simple/Advanced toggle)
  + iPad de-scope (TARGETED_DEVICE_FAMILY=1) + version-skew fix; verified on a real build/device
  (launch, ratings breaststroke, iPad letterbox, Diagnostics). 2 device bugs fixed (forget/BLE,
  diagnostics verdict). Recording-gated checks (full 34-01, 21-02, 26-01, 22-02) DEFERRED to a
  post-resolder build. SUMMARY: 35-02-SUMMARY.md. (2026-06-18)
- [x] 35-03: Doc/comment reconciliation — CLAUDE.md (coach.py coupling, +2 endpoints, +3 key-files)
  + CODEBASE-AUDIT.md (matrix + drift refreshed for Phases 33–36 + iOS; deploy-drift rows RESOLVED;
  NEW Feature Status Ledger). Grep confirmed no false source comments. SUMMARY: 35-03-SUMMARY.md. (2026-06-18)

### Phase 36: Coach-Friendly Metric Ratings
**Goal:** Replace overwhelming raw metric numbers with a qualitative **good / ok / needs-work**
read across four headline pillars coaches actually reason about — **Speed, Stroke Length,
Consistency, Endurance**. Each pillar = a hybrid verdict: an absolute band ("is it good") + a
trend vs the athlete's own history ("is it improving"); numbers hidden by default, expand a card
to see all contributing metrics + a plain explanation. Logic lives once in the backend (shared by
web, iOS, and the AI chat). Decisions (user, 2026-06-17): hybrid band+trend; 4 headline pillars;
hide-numbers-reveal-on-tap with contributing metrics + explanations; trend vs last session but
coded with a pluggable comparison scope; backend shared source of truth; non-breaststroke =
trend-only + provisional (no validated thresholds, segmentation_reliable=False). Web ships now;
iOS mirrors the same spec in the later iOS phase.
**Plans:**
- [x] 36-01: Backend — `ratings.py` (pure: pillars, draft breaststroke bands seeded from app.py,
  direction-aware trend, data-quality/stroke gating, pluggable baseline) + `GET /sessions/{id}/ratings`
  + `RATINGS-SPEC.md` + tests. (2026-06-17; 93 tests incl. review-hardening — DB errors surface as 5xx.)
- [x] 36-02: Web — pillar cards (band meter + marker@score + verdict + trend chip + expand →
  contributing metrics + explanation) on the session report card, raw grid demoted to Advanced; reads
  the endpoint; a11y. Verified end-to-end vs a local backend (endpoint not yet on Railway). (2026-06-17.)
- [ ] iOS (future, own phase): mirror the pillar UI from RATINGS-SPEC.md against the same endpoint.

### Phase 37: Team Coach Dashboard
**Goal:** Revamp the web coach dashboard from a raw-numbers athlete list
([web/app/app/page.js](web/app/app/page.js)) into a team-health home that answers "how is my
team doing?" at a glance. Four sections (user-chosen): a **team pulse** strip (athlete/tested
counts + per-pillar band-distribution chips), a **needs-attention** list (athletes with a
needs-work band, a declined trend, or a stale/no recent test), a **recent-activity** feed
(newest sessions team-wide), and a **color-banded roster grid** (4 pillar band-dots per athlete
replacing raw numbers). Pillar bands stay computed in `ratings.py` (Phase-36 single source of
truth), so the dashboard reads a new backend rollup. `roster_metrics.py` + `ratings.py` already
exist — this is wiring, not new metric logic. Decisions (user, 2026-06-18): all 4 sections; new
`GET /team/overview` endpoint (vs N per-athlete calls); keep tight — no per-athlete detail page
(athlete card still links to the filtered session list); iOS mirrors later (own phase).
**Plans:**
- [x] 37-01: Backend — `ratings.summarize_team` (band distribution + needs-attention) +
  `GET /team/overview` (auth, coach-scoped; reuses rate_session/select_baseline) + tests
  (suite 103). Locked payload contract in the plan (37-02 + iOS build against it). (2026-06-18)
- [x] 37-02: Web — dashboard rebuilt into the four sections consuming /team/overview (TeamPulse,
  NeedsAttention, RecentActivity, RosterBandCard + page rewrite). SHIPPED — committed as 62a6f4f
  "Add team dashboard UI" and live on Vercel. (Status corrected 2026-07-30: STATE/ROADMAP had
  carried this as "awaiting approval" long after it was built and deployed. SUMMARY never written.)
- [ ] iOS (future, own phase): mirror the team dashboard from the same endpoint.

### Phase 38: Mobile UI/UX Redesign
**Goal:** Full visual + navigation redesign of the iOS app (`swimnetics-mobile`), driven
by the user's wireframe/flow. New bottom-tab nav: Dashboard · Team · History grouped + a
separate **Record "island"** tab, each with a unique icon. Dashboard = team-health home
(reuses `GET /team/overview`); top-right Settings (account/coach name, device mgmt,
diagnostics, units, sign out). Team = roster CRUD + per-athlete pillar overview +
**streamlined per-athlete parent reports** (ported from web). History → session details
(`ReportCardScreen`). **AI coach assistant** made ambient/multi-surface (inline tip cards +
a global collapsed bubble): dashboard "today's focus" (daily-cached, anchored to latest
session via existing `/coach/chat`), session details, and compare. **Compare** = pillar-style
better/no-change/worse deltas (no number dumps), reached from History multi-select AND
"vs previous" on a session. Decisions (user, 2026-06-19, AskUserQuestion ×3): team-health
dashboard; AI = cards + bubble, daily-cached advice; compare from both entry points;
streamlined per-athlete reports; **mobile-repo-only** (no backend changes — team-level AI
context already exists via Phase 33-02 TEAM_TOOLS; reports write via supabase-js + existing
`/report/{token}`); design-system first. Build = 6 vertical slices.
**Plans:**
- [x] 38-01: Design system (theme tokens) + UI primitives + bottom-tab nav skeleton
  (Record island, 4 SVG icons) + Login restyle. CODE-COMPLETE 2026-06-19 (export green;
  device verify deferred to phase end per 38-TEST-PLAN.md).
- [x] 38-02: Dashboard (team-health, `/team/overview`) + Settings + ambient AI (today's-focus
  card daily-cached + floating bubble + CoachChatSheet). CODE-COMPLETE 2026-06-19 (export green;
  build-free; device verify deferred). Deviations: coach email read-only (no coaches.name col);
  team-name persistence pending teams UPDATE RLS; units pref-only.
- [x] 38-03: Team tab — labeled pillar TABLE (icon-header legend; rows = name + last-tested +
  4 band-dots; never-tested flagged) + (+) add athlete + AthleteDetail full-hub (Send report via
  supabase reports + RN Share + /report/{token}; pillar cards; session list → ReportCard; ⋮
  edit/delete). CODE-COMPLETE 2026-06-19 (export green). Added expo-crypto (FIRST native dep →
  forces end build). Fixed snake_case-band vs camelCase-token color bug. Deviations: WEB_BASE
  best-guess; edit = name+head-waist; teams-name still blocked by missing UPDATE RLS.
- [x] 38-04: History tab = TEAM-WIDE feed (stroke filters + swipe star/delete + Compare multi-select)
  + PillarCards→light + ReportCardScreen chrome restyle + session-anchored AiBubble + "compare to
  previous" + SessionSummaryCard/DataQualityCard→light + Compare stub. CODE-COMPLETE 2026-06-19
  (export green). Cross-plan review done — 2 findings folded into 38-06: (A) Settings units pref not
  consumed by Record/ReportCard; (B) Devices/Diagnostics not yet restyled. VelocityChart → 38-06.
- [x] 38-05: Compare — pillar better/no-change/worse from two sessions' ratings (±5 score deadband;
  adaptive labels same-athlete vs cross-athlete; tap-to-expand primary metric A→B). CODE-COMPLETE
  2026-06-19 (export green). Both entry points wired in 38-04.
- [x] 38-06 (FINAL): Record flow. CODE-COMPLETE 2026-06-19 (export green). VelocityChart theme-aware
  (dark prop); Finding A resolved (ReportCard+Record read UnitsContext m/yd); RecordingConfig
  restyled + athlete picker; RecordScreen dark/immersive (BLE/camera logic untouched); VideoOverlay
  restyled; Finding B done (Devices/Diagnostics light). Added dangerOnDark token. Follow-up:
  per-screen StatusBar light on the dark record screen (verify on device). DESIGN LOCKED 2026-06-19: (1)
  RecordingConfigScreen restyle to light + ADD athlete picker (pre-filled when launched from an
  athlete; pick-from-list when cold from the Record island) + keep stroke/device/name + "Record
  with video" toggle; (2) RecordScreen ACTIVE screen = DARK/IMMERSIVE (timer + recording dot +
  optional camera preview + live trace + Stop), returns to light after; (3) VideoOverlayScreen
  restyle; (4) shared VelocityChart restyle (used on active + ReportCard). PLUS cross-plan review:
  (A) wire Settings m/yd UnitsContext into Record + ReportCard + VelocityChart (map m↔metric,
  yd↔imperial; replace the per-screen local toggles); (B) restyle DevicesScreen + DiagnosticsScreen
  to light. Do as ONE focused pass (interdependent: units span Record/ReportCard/Chart; ~950-line
  RecordScreen BLE/camera is fragile). After 38-06 → phase code-complete → one EAS build for all
  deferred device checks.

### Phase 39: Redesign Fixes & UX Iteration
**Goal:** Fix the defects found in on-device testing of the Phase 38 redesign, then apply the
user's design-update backlog. Driven by user testing 2026-06-19. Spans the mobile repo + a small
backend/SQL change.
**BUGS (located 2026-06-19 — see 39-01-PLAN):**
1. Pillar EXPAND view ignores m/yd — `PillarCards.js` shows /ratings values raw (no unit prop, no
   conversion); ReportCardScreen mounts it without `unit`.
2. "declined" chip vs green band — NOT a logic bug: `ratings.py _trend` is correct; band=absolute,
   trend=vs-previous are independent (Phase-36 hybrid). UI conflates them → clarity decision.
3. **CRASH (biggest):** Team → any tested athlete → `AthleteDetailScreen.js:149` references undeclared
   `rc` (removed in the 38-04 self-review; line missed) → ReferenceError rendering pillars. 1-word fix
   (`rc`→`BAND_COLOR`).
4. Team-name edit doesn't persist — `teams` has SELECT-only RLS (schema.sql ~78); the update is
   silently blocked. Needs an UPDATE policy (patch_05, user-applied).
**Plans:**
- [x] 39-01: Bug fixes — CRASH (AthleteDetail rc→BAND_COLOR), pillar-expand units, teams UPDATE RLS
  patch. CLOSED 2026-06-19 (export green; device verify deferred). Bug #2 (band vs trend) =
  correct-by-design → UI clarify folded into 39-03.
- [x] 39-02: History/session UX [DU5] — removed swipe; per-row STAR button; delete ONLY inside a
  session (🗑 next to star + confirm popup → DELETE → back). CODE-COMPLETE 2026-06-19 (export green).
  SessionHistoryScreen + ReportCardScreen.
- [ ] 39-06 (planned, was bundled in 39-02): Flag abnormal sessions in history/lists + "ignore flag"
  option [DU4]. Needs a DESIGN/BACKEND decision first: what defines "abnormal" (data_quality
  warnings / segmentation_reliable=False / low plausible_fraction?) + where "ignore" persists (new
  `sessions` column + PATCH /sessions, vs local). Files: SessionHistoryScreen, AthleteDetailScreen,
  DashboardScreen, api.py + supabase.
- [x] 39-03: Pillar long-press explainer [DU2 — PillarCards Modal] + remove "impulse per stroke" [DU1 —
  ratings.py + ReportCard/Record advanced grids] + athlete-limit display "N / 20" [DU3 — AthletesScreen,
  teams.swimmer_limit ??20] + trend-chip relabel "Up/Down/Same vs last" [bug #2 clarity]. CODE-COMPLETE
  2026-06-19 (iOS export green; ratings 26 passed). DEPLOY: ratings.py → Railway (user push) for the
  pillar-expand impulse removal.
- [x] 39-04: Record tab button redesign [DU6] — TabBar.js rewritten to a frosted lavender pill
  (Dashboard/Team/History) + detached purple circular Record button (no label; solid pill, no
  expo-blur). CODE-COMPLETE 2026-06-19 (export green; mock-confirmed). Nav unchanged.
- [x] 39-05: Advanced — segmentation overlay on the velocity chart (cycle boundaries from
  metrics_json.cycles so the coach sees what the segmenter sees) [DU7 — VelocityChart +
  ReportCardScreen advanced]. CODE-COMPLETE 2026-06-20 (export green; device verify deferred).
  Faint dashed zoom-aware boundary lines under the trace + "segmentation is experimental" caption,
  Advanced view only. Dashed lines (not shading); RecordScreen parity = noted follow-up. self-relabel
  + change analysis scope (e.g. 5–7 s) NOT built — deferred larger future. SUMMARY: 39-05-SUMMARY.md.

### Phase 40: Website Redesign (iOS match)
**Goal:** Redesign the MARKETING website (`web/`) to match the Phase-38 iOS app — the
**immersive purple→periwinkle gradient** direction (Template B), built on shadcn/ui +
Vercel design conventions, in plain JS (Tailwind v4 CSS-first, no TypeScript). Remove
public pricing entirely → a single "Request a quote" contact dialog (name + email +
optional message) that emails leads to tzheng846@gmail.com via Web3Forms (form-to-email;
public access key in `lib/site.js`, no backend). Decisions (user, 2026-06-21,
AskUserQuestion ×5 + 2 mockup artifacts in `web/design-mockups/`): Template B;
marketing-site-only (portal + parent reports stay dark this phase); CTA = form-to-email
(revised from a scheduling link); shadcn-in-JS, keep the stack. Key constraint surfaced
in planning: marketing and the
coach portal SHARE the global `@theme` tokens, so the redesign ADDS a new light-purple
iOS token set and rewrites marketing components onto it while leaving the dark `--color-*`
tokens (portal/report depend on them) untouched. Split into 2 plans.
**Plans:**
- [x] 40-01: Design foundation + landing core — shadcn (hand-authored JSX) + iOS light-purple
  tokens (additive; portal dark tokens preserved) + primitives + `lib/site.js`
  WEB3FORMS_ACCESS_KEY (real key) + reusable ContactDialog ("Request a quote" → Web3Forms
  email, live-tested); immersive gradient Hero + floating SampleChart card; scroll-aware Nav
  (glass→solid); light Footer; page.js. Build green; checkpoint approved. SHIPPED 2026-06-21
  (40-01-SUMMARY.md).
- [x] 40-02: Remaining sections — Features + HowItWorks restyled to light; RequestQuote gradient
  CTA (reuses ContactDialog, id="pricing") replaced Pricing (Pricing.js deleted); login restyle
  (shadcn Input/Button); /faq + /privacy rethemed to light (legal copy untouched; FAQ cost answer
  scrubbed of $300/$20 per the pricing-removal directive). 2 nav-visibility bugs fixed at checkpoint
  (Nav `overHero` prop + homepage `-mt-16` hero overlay). Build green; checkpoint approved. SHIPPED
  2026-06-22 (40-02-SUMMARY.md).

### Phase 41: Race-Start Sequence (iOS)
**Goal:** Add an optional race-start cue to the iOS recording flow (`swimnetics-mobile`): a giant
on-screen **3 → 2 → 1** countdown → spoken **"take your marks"** → **randomized 2–3 s hold** →
**loud blare**, with recording (BLE `START`, and the camera on the video path) beginning *exactly
on the blare* so the buffered session is the race effort, not the setup. A persisted toggle on the
recording-config screen controls it (default **ON**); applies to both plain recording and
Record-with-Video. Decisions (user, 2026-06-21, AskUserQuestion ×3): random (un-anticipatable)
hold; TWO bundled real-starter clips (voice + horn) via **expo-audio**, user-supplied (no TTS);
toggle remembered via **expo-secure-store**. New native dep (expo-audio) → forces the next EAS
build; on-device verify deferred per the Phase 38/39 mobile workflow. Mobile-repo-only — no
backend/web changes; gates only WHEN the existing `START` is written (BLE/camera/sync untouched).
**Plans:**
- [x] 41-01: expo-audio dep + assets/audio + persisted toggle (RecordingConfigScreen) +
  useStartSequence hook + StartSequenceOverlay + RecordScreen wiring (both start paths).
  CODE-COMPLETE 2026-06-22 (export green, 1071 modules; both clips bundled). Checkpoint
  pre-satisfied (user supplied takeyourmarks.mp3 + beep.mp3 before APPLY). Decisions: random
  2–3 s hold; bundled clips (no TTS); secure-store toggle default ON; run() resolves at the blare.
  Device verify (audio/silent-mode/visuals/START-on-blare) DEFERRED → next EAS build (expo-audio =
  new native module). SUMMARY: 41-01-SUMMARY.md.

### Phase 42: Core-Flow Failsafes (iOS)
**Goal:** Harden the three core iOS flows a coach touches every session — **pairing, recording,
checking session results** — so each either auto-recovers or fails gracefully with a *specific,
actionable reason* (never a silent hang or a dead-end), and no session data is ever lost. Driven
by 2026-06-22 user request. Decisions (user, AskUserQuestion ×4): recovery = auto-recover-first,
specific message only on failure; upload failsafe = keep the saved CSV + Retry button + clear
offline/server reason (NO background queue this pass — the PROJECT.md offline-queue Must-Have stays
a later effort); pre-flight guards = Bluetooth-off/permission detection + connect timeout + one
auto-retry + pre-record encoder/magnet STATUS check (warn+override, not a hard block) — network
reachability pre-check NOT chosen; mid-record BLE drop = detect → "data is safe on the device" →
guide reconnect+retrieve (NOT silent auto-reconnect). Mobile-repo-only; no new native deps;
export-green gate; on-device behavior deferred to the next EAS build.
**Plans:**
- [x] 42-01: (T1) Pairing — friendlyError.js mapper + BleContext ensureBleReady + connect
  timeout/retry + DevicesScreen/RecordingConfigScreen specific reasons. (T2) Recording — extract
  parseStatus/magnetVerdict to src/lib/deviceStatus.js (shared with Diagnostics) + pre-record
  checkEncoder (warn+override) + plain-start connection guard (mid-record drop handler already
  existed — reused). (T3) Results — upload Retry on the saved CSV + specific reasons +
  ReportCardScreen load-reason branching + Retry. CODE-COMPLETE 2026-06-22 (export green ×3; no new
  native deps). Device verify (failure paths need hardware/network) DEFERRED → next EAS build.
  SUMMARY: 42-01-SUMMARY.md.

### Phase 43: Demo Readiness (runbook)
**Goal:** Produce a single cross-system demo-readiness runbook (`DEMO-READINESS.md` at repo root)
so a live coach demo doesn't die on a preventable issue. (A) A failure-mode catalog across
Hardware/Encoder + BLE/Connectivity + App(record/results) + Backend/Network/Account — each with the
coach-visible symptom, root cause, the mitigation already in code (Phase 42 failsafes / Phase 34
diagnostics / buffer-and-dump), residual risk, and the manual workaround. (B) An ordered checkbox
pre-demo checklist of app *and* hardware checks (Hardware bench + App + Backend/Account/Venue + a
"T-10 min" quick list; keystone = one record→retrieve→results dry-run; warm up Railway to dodge
cold-start). (C) A mid-demo fallback table mapping the top demo-killers to the on-the-spot fix vs.
falling back to a known-good saved session. Documentation only — no code/firmware changes; cites real
mitigations (no invented capabilities). In-app automated self-test deliberately NOT built this phase
(noted as a possible future option). Driven by 2026-06-22 user request.
**Plans:**
- [ ] 43-01: DEMO-READINESS.md — Part A failure-mode catalog (grounded in RecordScreen/BleContext/
  DiagnosticsScreen/friendlyError/deviceStatus/ESP_32_V5.ino/api.py) + Part B pre-demo checklist
  (app + hardware + T-10) + Part C mid-demo fallback table. Cross-refs the mobile 38/39-TEST-PLANs.
  autonomous:true.

### Phase 45: Cloud Session Save (device_id UUID→TEXT)
**Goal:** Fix the bug where **no iOS session reaches Supabase**. The live `sessions.device_id`
column is still type **UUID** (original schema.sql shape), but `api.py /process` correctly writes
the device's **chip-id string** (e.g. `"64CD4D"`, derived from BLE name `SwimLogger-64CD4D`) into it,
so the row insert fails with `invalid input syntax for type uuid: "64CD4D"` (Postgres 22P02). The
save is non-fatal, so the swimmer sees the full report and then a `⚠ Save failed:` line — nothing
persists. The intended UUID→TEXT migration was documented in `patch_04_backfill.sql:31-42` but never
executed against the live DB; Phase-21's reliable pairing means a chipId is now always present, so
*every* session hits it. This same bug is why the "advanced segmentation view" is gone — 39-05's
dashed cycle overlay only renders on a **saved** session's ReportCard → Advanced, which is
unreachable while saves fail. Fix is a single user-applied migration; `api.py` is already correct
(the devices table is chip-id-keyed). Decisions (user, 2026-06-22/23): video→cloud upload deferred
("discuss first" — undecided); RecordScreen overlay parity an optional follow-up.
**Plans:**
- [ ] 45-01: `supabase/patch_06_sessions_device_id_text.sql` (idempotent guarded UUID→TEXT + drop FK,
  `USING device_id::text`) + human-action (run SQL in Supabase) + human-verify (on-device: session
  saves, appears in history, Advanced segmentation overlay returns). Rides the same EAS build as 44-03.

### Phase 47: Trial Annotation (review + ground truth) ✅
**Goal:** Review-and-annotate tool for recorded trials. Coach (initially the founder) pulls a
trial from storage and hand-marks a SINGLE ORDERED PASS of swim phases — dive → underwater
kick ("pulldown" display label for breaststroke) → breakout → stroke → finish — plus each
individual stroke boundary, by clicking on the velocity trace with the session video playing
alongside (when attached; the tool fully works velocity-only). Marks are PRE-SEEDED from the
existing auto-segmenter (metrics_json cycles + baseline/initial-phase detection) and edited.
Purpose (user, 2026-07-11): (a) ground truth for wavelet segmenter tuning (16-06) and future
HMM sub-phase work; (b) correct the auto-segmentation → recompute session metrics from manual
boundaries. Built as an ESTABLISHED production API (auth, ownership, RLS) because it will later
be exposed to any app user. Video reaches the cloud for the first time this phase: new private
`videos` bucket + sessions.video_path/video_origin_s (44-03 end-anchor convention), iOS
auto-uploads after Record-with-Video (EAS builds no longer treated as a blocker — heads-up only).
Decisions (user, 2026-07-11, AskUserQuestion ×7): web-portal GUI; iOS auto-upload this phase;
ground-truth + correction purposes; pre-seed-then-edit; single-ordered-pass model; recompute
in-phase (final plan); velocity-only must work.
**Plans:**
- [x] 47-01: Backend — patch_07 (session_annotations + RLS, sessions video cols, videos bucket —
  USER-APPLIED, live) + annotations.py (pure seed/validate) + 5 api.py endpoints (annotations
  GET/PUT/DELETE, video POST, signed video-url) + 28 tests (suite 131). Contract LOCKED for
  47-02/03/04. Deviation: seed ordering-drop walks backwards (cycle anchors win). Deploy:
  api.py + annotations.py ride the next user push to Railway. (2026-07-11; 47-01-SUMMARY.md)
- [x] 47-02: Web GUI — /app/annotate/[id] portal page: velocity trace click-to-mark (phase
  palette + stroke marks), synced video pane (signed URL + origin_s + nudge), seed load, save.
  NEW AnnotationChart (shared VelocityChart protected) + AnnotationEditor + VideoPane + additive
  apiUpload in lib/api.js. Checkpoint approved vs local backend; build green (18 routes).
  COMMITTED + PUSHED 2026-07-12: e7f72f4 "Add trial annotation tool (Phase 47, plans 01-02)" →
  origin/main (10 files — Phase 47 only; unrelated pending Phase 44/45/46 changes left untouched).
  (47-02-SUMMARY.md)
- [x] 47-03: iOS — Instagram-style background video upload after Record-with-Video (user:
  non-blocking; AskUserQuestion ×3 — in-app toast / FIFO queue / retry×2 + persistent chip).
  NEW videoUploadQueue singleton (module-singleton FIFO, BACKGROUND FileSystem session,
  survives unmount+backgrounding, retry ×2 w/ backoff then persistent chip) + NEW UploadToast
  global host (mounted once in App.js) + RecordScreen enqueue-on-success (non-awaited;
  videoUriRef stale-closure guard) + VideoOverlayScreen persists the end-anchored
  video_origin_s (origin-only POST, debounced on nudge). CLOSED 2026-07-20 — export green
  (1075 modules, re-verified at UNIFY); NOT committed (mobile repo local-only, user runs git).
  Device verify (real upload/retry/backgrounding, web annotate playback alignment) →
  next EAS build. LAST plan — PHASE 47 COMPLETE (4/4). (47-03-SUMMARY.md)
- [x] 47-04: Recompute — AUTO on annotation save (PUT), not a separate endpoint (user decision
  2026-07-12): metrics.py additive `manual` overrides (phases define windows, marks define
  cycles; wavelet bypassed; segmentation_reliable→True), OVERWRITE metrics_json + once-only
  metrics_json_auto backup (patch_08 APPLIED LIVE; DELETE annotation restores auto), GET
  /annotations/export + fetch_annotations.py for 16-06 ground truth. Suite 148; checkpoint
  approved E2E (save → "metrics recomputed" → report card reflects manual boundaries).
  COMMITTED + PUSHED 2026-07-12: 627419c → origin/main. (47-04-SUMMARY.md)

### Phase 48: Athlete-Create Fix
**Goal:** Fix the live bug blocking athlete creation — `POST /athletes` 500s with
`'SyncQueryRequestBuilder' object has no attribute 'single'`. Root cause (confirmed against
postgrest 2.30.1): `.insert()` returns a mutation builder whose `.select()` stays a mutation
builder with no `.single()` method → AttributeError before any network call. Unpinned
`supabase` in requirements.txt let a Railway redeploy pull a postgrest where the chain is
invalid. Blast radius is ONE endpoint (grep-verified: the only mutation chaining `.single()`;
every other `.single()` is on a valid SELECT chain). First of a user-defined 4-item batch
(2026-07-20): item 0 = this fix; items 1 (iOS video replay), 2 (BLE auto-reconnect), 3
(freestyle unlock) follow as separate phases in order. Decisions (user, AskUserQuestion ×2):
plan item 0 alone now; fix + pin the dependency.
**Plans:**
- [ ] 48-01: api.py POST /athletes — drop `.single()`, return `resp.data[0]` (keep `.select()`,
  proven valid at api.py:293) + pin supabase==2.30.1 & postgrest==2.30.1 in requirements.txt +
  regression test on the REAL postgrest builder (MagicMock can't reproduce the AttributeError).
  Backend-only (mobile sends the correct payload). autonomous:false — human-verify = user
  deploys + adds an athlete live. Created 2026-07-20.

### Phase 49: Security Hardening (backend)
**Goal:** Close the three highest value-to-effort security gaps found in a full-surface review
(2026-07-20), ahead of paid pilots that store minors' data on a shared Railway instance using the
Supabase service-role key (RLS-bypassing — every ownership check is manual in `api.py`).
(1) **Info disclosure** — 14 sites return raw `str(e)` to clients (500 bodies + the `/process`
and annotation response bodies) → generic messages + server-side logging + a catch-all handler.
(2) **Open edge** — `allow_origins=["*"]` → env-driven `ALLOWED_ORIGINS` allowlist; and NO body-size
limit on the two upload endpoints (`await file.read()` buffers the whole upload → one authenticated
caller can OOM the shared instance) → memory-safe `_read_capped` caps on `/process` (10 MB) and
`/sessions/{id}/video` (200 MB) + a `/coach/chat` payload cap. (3) **Cross-tenant write** —
`POST /process` never checks the posted `athlete_id` belongs to the coach's team → add an
`athlete_id ∈ coach.team_id` guard (+ regression tests). Verified NON-issues left alone: Stripe
webhook signature IS verified, report tokens are UUIDv4, no SQLi/XSS, no committed secrets, RLS
`WITH CHECK` present. Deferred with rationale: rate limiting (needs a shared store), report-token
expiry/revocation (schema + product decision), pinning the rest of `requirements.txt`. Backend
only (`api.py` + `tests/`); web/mobile untouched.
**Plans:**
- [ ] 49-01: Redact error-detail leaks + CORS allowlist + memory-safe upload caps + athlete-ownership
  on /process + regression tests. autonomous:false — human-verify = portal + record + add-athlete +
  video-attach all work post-deploy with ALLOWED_ORIGINS set on Railway. Created 2026-07-20.

### Phase 46: Marketing Blog (build log)
**Goal:** Add a public "Build log" blog to the marketing site (`web/`) — a `/blog` index +
`/blog/[slug]` post pages, linked from the Nav + Footer, styled to match the light static
pages (`/faq`, `/privacy`). Seed it with the founder dev-journal turned into **5 thematic
posts** (going battery-powered; the ASP demo & what broke; the string-retraction saga
reel→spring→motor→one-way-bearing; the matrix-profile→wavelet segmentation breakthrough;
current state + video-overlay/auto-tracking-camera roadmap) in a **lightly polished candid**
voice — covering where the product is, the past struggles, and incoming feature ideas.
Decisions (user, 2026-06-23, AskUserQuestion ×4): index + post pages; lightly polished
candor; thematic chunking; Nav + Footer, route `/blog`. Posts live in a plain JS data file
(`web/lib/blog.js`) — no CMS/MDX, no new deps, no fabricated dates. Web-only; independent of
the parked Phase 44/45 loops (no file overlap).
**Plans:**
- [x] 46-01: web/lib/blog.js (5 posts) + /blog index + /blog/[slug] dynamic route
  (generateStaticParams + async params + notFound) + Nav/Footer "Blog" link. SHIPPED 2026-06-23 —
  build green (/blog static, /blog/[slug] SSG all 5 paths prerendered); preview-verified (index
  newest-first, posts 200, bogus slug 404, Nav+Footer links); checkpoint approved. No new deps,
  no fabricated dates. Deviation: plan's ESM verify swapped for build+preview. SUMMARY:
  46-01-SUMMARY.md.

### Phase 50: Demo Team & Synthetic History
**Goal:** Fabricate a believable long-term training history so the demo can actually show off
the product's strongest claim — athlete tracking over time. Today a prospect sees empty trend
chips, an empty team-pulse strip, an empty needs-attention list and an unusable compare view,
because no multi-month history exists.

**Approach — replay + perturb, NOT fabrication.** `raw/` holds ~30 real encoder recordings.
Each demo session is a real raw CSV put through an invertible perturbation (time-warp →
stroke rate, count-scale → velocity/DPS) and then run through the REAL pipeline
(`vae.run_pipeline` → `m.compute_session_metrics`), inserted as a row shaped exactly like
`/process`'s `session_row` with a backdated `created_at`. Because the data is
shape-indistinguishable from real, every downstream surface (pillar ratings, `/team/overview`,
compare, per-cycle advanced, parent reports, AI chat, annotate) works with **zero product code
changes**.

**Annotation propagation is the key cost saver.** The requirement was no visibly-wrong
segmentation anywhere (the wavelet segmenter ships at placeholder quality,
`segmentation_reliable=False`, ridges can rail the 120 SPM ceiling). Hand-annotating ~144
sessions is 7–14 hours. Instead: hand-annotate ~12 archetypes (~1 h) and propagate their marks
through the seeder's own warp into every derivative — exact, because the seeder chose the warp.
Constrains perturbations to time-warp + amplitude scale (no peak-shifting jitter), and forces a
two-stage sequence with a human gate in the middle.

**Decisions (user, 2026-07-27, AskUserQuestion ×3 rounds):** dedicated demo coach account in the
live Supabase project (RLS-isolated); **web coach portal only** (no iOS, no parent-report
seeding); ~12 athletes × ~12 sessions over 6 months; scripted story beats; **breaststroke +
freestyle only** — revised down from the user's initial "all four strokes" because `raw/`
contains ZERO backstroke and only two usable fly recordings; raw CSVs uploaded to Storage (keeps
annotate-recompute and `/export` functional); config-driven and re-runnable; session names +
notes only; obviously-demo naming (it is sample data and must never be presented as a real
club's track record); user signs up the demo account so no credential is handled in the script;
archetypes kept as each athlete's earliest session.

**Routes around, does not fix:** Phase 48 (`POST /athletes` 500s) and Phase 45 (`device_id`
UUID) both sit on API paths the seeder skips by writing direct with the service role.

**Plans:**
- [~] 50-01: Seeder core + Stage-1 archetype ingest. NEW `seed_demo_team.py` (CONFIG block,
  service-role client, `ingest_csv` mirroring `/process`, `--wipe`/`--dry-run`) + archetype
  validation pass + `DEMO_ROSTER`/`TIMELINE` authoring + human-action checkpoint (demo account
  signup) + Stage-1 run = 12 athletes × 1 real backdated session. PLAN created 2026-07-27,
  awaiting approval (autonomous:false).
- [ ] 50-02 (next): Generation + propagation + tuning — perturbation engine, annotation mapping
  into `session_annotations` + `compute_session_metrics(manual=...)`, clustered 6-month
  timeline, plausibility gate (reject/regenerate poor `data_quality`), and the band/trend tuning
  loop. Entry gate = the user has hand-annotated the 12 archetypes from 50-01.

---
*Roadmap created: 2026-05-17*
*Last updated: 2026-07-27 — Phase 50 (Demo Team & Synthetic History) opened: discussed +
50-01 planned. Seeder-only, no product/schema/web changes.*
*Last updated: 2026-07-20 — Phase 47 (Trial Annotation) COMPLETE (4/4 plans): annotation
contract + web GUI + recompute-on-save deployed; iOS background video upload code-complete,
device-verify → next EAS build.*
*Last updated: 2026-06-12 — Phase 16 wavelet segmenter SHIPPED to production (16-05,
placeholder quality, all 4 strokes; segmentation_reliable=False; tuning → future 16-06).
Phase 27 (Device Model) COMPLETE. Phase 26 parked at EAS-build checkpoint. Remaining in
v0.5: Phase 16 tuning (16-06, when freestyle data available), Phase 26 (device checkpoint,
pay-per-build). USER follow-up: commit+push wavelet backend → Railway auto-deploys (pywt
new build dep).*
