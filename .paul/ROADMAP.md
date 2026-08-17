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
| 54 | Gate Removal (tier enforcement + stroke gating) | ⚠ **RECORD CORRECTED 2026-08-07 (Phase 58-03): this row's claim that "Web has NO stroke gate (already unrestricted); the stroke gate is ratings.py:176 + mobile ReportCardScreen.js:192 only" was FALSE.** `web/app/app/sessions/[id]/page.js:99` carried `isAnalyticsReady = !strokeType \|\| strokeType === "breaststroke"` from Phase 23 until 58-03 removed it, gating five surfaces (view toggle, PillarCards/MetricGrid, TimeToX, per-cycle breakdown, CoachChat). The mobile half shipped in the Phase-55 build; the web stayed breaststroke-only for two more days because the audit said there was nothing to touch. HOW IT SURVIVED: both copies use the SAME identifier `isAnalyticsReady`, so a grep would have found it — the miss was in the reading, not the search. A SECOND consequence surfaced at the same time: dropping `(not seg_reliable)` from `provisional` also silenced the "Provisional — stroke segmentation is still being validated" banner for EVERY stroke (`ratings.py:229` always falls back to the breaststroke table, so `thr_table` is never None and `provisional` became stroke-independent). Borrowed bands now display with no on-screen caveat — accepted by the user 2026-08-07, owned by Phase 53. ✅ **Complete (1/1 plans) 2026-08-05** — backend shipped in `dedac17` (could not be split from 51-02's commit); the mobile half sat uncommitted and unbuilt for two days, was folded into Phase 55-01, and freestyle analytics were VERIFIED ON DEVICE 2026-08-05. `ENFORCE_TIER_LIMITS` default OFF now covers all three limits, superseding 51-02's planned `ENFORCE_ATHLETE_LIMIT`. ⚠ Accepted consequence now LIVE: the team dashboard needs-attention list, inert since Phase 37, populates using breaststroke-derived bands applied to all strokes over segmentation flagged unreliable — Phase 53 decides whether those bands should exist. Prior status: Planning (54-01 created 2026-08-03 — remove every account-level restriction and the breaststroke-only analytics gate, both reversibly. TRIGGER: free-tier `device_limit`=1 blocked a live test, and `monthly_session_limit`=20 would 402 partway through the Phase-53 pool day. (T1) single module-level `ENFORCE_TIER_LIMITS` env kill switch, DEFAULT OFF, gating all three limit sites (session api.py:215, device :242, athlete :1291) so the count queries never run; SUPERSEDES 51-02's `ENFORCE_ATHLETE_LIMIT` — one switch, not two. Billing infrastructure (`_TIER_LIMITS`, Stripe webhook writes, /billing/status, schema columns) explicitly PRESERVED. (T2) ratings.py: bands fall back to the breaststroke table for every stroke + drop `(not seg_reliable)` from `provisional`; 2 contradicted tests INVERTED not deleted. (T3) mobile ReportCardScreen.js:192 `isAnalyticsReady` → true. KNOWN CONSEQUENCE, accepted by user: the team dashboard needs-attention list has been inert since Phase 37 because every pillar was provisional — it now POPULATES, driven by breaststroke-derived bands applied to all strokes over segmentation flagged unreliable. autonomous:false (human-verify after Railway deploy), depends_on 51-02) |
| 53 | Attention Allocation (SPC detection engine) | Planning (53-01 created 2026-08-03 — the instrument before the experiment: Track-A5 repeatability/saturation analyzer + pool-day protocol, requires NO collected data. NEW repeatability.py (pure: sigma_mr = mean(moving_range)/1.128, minimum detectable change, rails DERIVED from metrics._PERIOD_MIN_S/_MAX_S, usability ranking, zero-variance flagged suspect) + tools/analyze_repeatability.py (offline CLI; captures `actual_fs` from run_pipeline so it answers Phase 52's "does fs vary?" without touching Phase-52 files) + tests + COLLECTION-PROTOCOL.md. autonomous:true, depends_on []). Discussed 2026-08-03, CONTEXT.md written. PRODUCT REFRAME: the tool is not a magnifying glass — a head coach cannot track 30 swimmers across a 2-hour practice daily (~90 s attention per athlete per week), so the core value is ALERTING when something goes wrong OR RIGHT. Layer contract: measurement gate → contrast → persistence → co-occurrence → synthesis; HARD BOUNDARY at co-occurrence (no causal claims, no drill prescription). Framing = statistical process control, NOT anomaly detection; LLMs in the phrasing layer ONLY, detection deterministic. Verified: the shipped needs-attention list is INERT (provisional gate) and has been a calendar reminder since Phase 37; `_trend` is ±5% vs one session with no noise model; σ never measured. Roadmap: Track A (blocking) hardware gate → Phase 52 fs contract → collect 10 freestyle sessions in one day with injected perturbations → annotate all (Phase-47 tool) → saturation + repeatability = GO/NO-GO; Track B engine; Track C 90-second surface; Track D real weekly spacing + 16-06 + pilot. Supersedes the Phase-48 "freestyle unlock" (porting breaststroke thresholds is the wrong unlock — within-athlete contrast needs none) |
| 63 | Data Flow Map (DATA-FLOW.md — stores, APIs, callers, field dictionary, diagrams) | Planning — discussed 2026-08-12 via `/paul:discuss`, CONTEXT.md written, 8 decisions D1–D8, zero open questions. **DOC-ONLY**: no product code, no schema, no deploy; findings recorded not fixed. Trigger: the user asked to understand the project's data flow, citing `ramp_up` as something shipped without understanding — and Phase 61-01 had already removed it after measuring it was never ramp-up. Live probe (read-only, 2026-08-12): 62 sessions / 24 annotations / 5 reports; `sample_rate_hz` 6 NULL; ⚠ **5 sessions carry `video_path` with NULL `video_origin_s`** (58-04's data footprint, never backfilled); `metrics_json_auto` 24/62 exactly matching the annotation count; `upload_status` `'complete'` 62/62. Section below |
| 62 | Progress Report Rework (TODO, unscheduled — NOT planned) | Raised 2026-08-11 while reviewing a live parent progress report; user asked to record it, explicitly **not** to plan it. Three problems, one of them already root-caused. **(1) THE TOOLTIP IS INDISTINGUISHABLE ON SAME-DAY SESSIONS** — user: *"on hover it's all the same when it shows otherwise."* `web/components/report/MetricTrend.js:57` renders `payload[0].payload.label`, and `label` is the X-axis key, which is a DATE. Ten sessions recorded on Aug 5 all hover as "Aug 5", so the tooltip cannot be matched to the point under the cursor. ⭐ **This is the SAME defect Phase 61-04 fixed on Compare** (`sessionLabel` needs the TIME, because the date alone is exactly what fails), and `web/lib/sessionName.js` already exports `displayName`/`sessionLabel` — the fix is to reuse them here rather than re-derive. The X-axis tick labels have the same problem (`Aug 5 · Aug 5 · Aug 5 …`). **(2) ALL STROKES ARE AVERAGED TOGETHER** — user: *"progress report should not just average everything together — there needs to be separation by stroke type etc."* A single series mixes freestyle, butterfly and breaststroke, so "distance per stroke" trends across strokes with genuinely different DPS ranges. ⚠ This makes the hero deltas questionable too, not just the charts: the screenshot showed **"−4.4% change in distance per stroke"** and **"+40% faster lap"** computed across a mixed-stroke range, where a change in stroke MIX alone would move both. Needs either per-stroke series/facets or a stroke filter — a product decision, not just a code change. **(3) UNVERIFIED, from the screenshot only:** the Average Speed and Top Speed traces drop to **exactly 0** at two points, which looks like sessions with missing/failed metrics being plotted as 0 rather than skipped. NOT diagnosed — confirm against the data before treating it as a defect. ⚠ A third hero card showed a bare `0.064` with no visible caption; also unconfirmed (may be cropped). Files likely in scope: `web/components/report/MetricTrend.js`, `web/components/report/ImprovementHero.js`, `web/app/report/[token]/page.js`, `web/components/portal/ReportBuilder.js`, and `GET /reports/{token}` in `api.py` if the series is built server-side. |
| 56 | Coach Chat Athlete Scoping (OPEN DEFECT, unscheduled) | Found 2026-08-05 during live use; user chose document-only, no plan. Asking the AI coach "give me info on Sid specifically" returned a DIFFERENT athlete's history under Sid's name — claimed a most-recent swim of Aug 5 when Sid has only two swims, both in May. ROOT CAUSE: `list_athlete_sessions` exposes no athlete parameter (schema is `limit` + `stroke` only, coach.py:141-142) and its executor is bound to the athlete of the session the chat was opened from (api.py:1494, `.eq("athlete_id", athlete_id)` closing over the anchor session). Naming another athlete cannot re-scope the tool, so the model receives the anchor athlete's rows and attributes them to whoever was named; `get_session_metrics` inherits the same anchor scope. This is cross-athlete data attribution, not merely an inaccurate answer. NOT caused by 51-02 (that path filters athlete_id + coach_id, untouched), though 51-02's repair of the team tools makes the chat sound more authoritative while still mis-attributing. Fix direction: either add an athlete_name/athlete_id parameter resolved against the coach's roster, or make the system prompt state that athlete tools are locked to the anchor swimmer so the model declines rather than substitutes |
| 55 | Athlete Flow Fixes (mobile) | ✅ **Complete (1/1 plans) 2026-08-05** — checkpoint approved on the EAS build. All three symptoms traced to ONE fact: `RecordingConfig` is a tab screen that mounts once per app launch and never remounts, so `useEffect(…,[])` ran once ever (frozen roster), `useState()` initializers ran once ever (params ignored), and it sits under `Tabs` not Root (unreachable by bare name). Fixes: `useFocusEffect` roster refetch; nested `navigate('Tabs', {screen, params})` from AthleteDetail; a params effect that applies AND clears (clearing is required — on a never-unmounting screen params persist, so a later plain tab press would inherit the previous athlete). `RootTabs.js:21`'s comment, which had asserted cross-screen navigation "keeps working" and was the assumption that produced the bug, now documents the Root→Tab rule and warns it fails SILENTLY. Phase 54-01's `isAnalyticsReady` one-liner rode the same build → **freestyle analytics verified on device**, clearing 54-01's last outstanding piece. Build also cleared six deferred iOS checks (47-03/41/42/44-03/21-02/34-01). AC-2/3/4 pass; AC-1 partial. ⚠ KNOWN GAP (user: note only, not fixed): deleting the CURRENTLY SELECTED athlete clears them from the dropdown but leaves them in the selection bar — `athlete` state is independent of `athletes` and the focus refetch never revalidates the selection. Matters beyond cosmetics: recording against that stale selection would submit a deleted `athlete_id`. One-line fix recorded in 55-01-SUMMARY.md. Prior status: Planning Found while verifying the 51-02 checkpoint — athlete creation works now, and exercising the unblocked flow surfaced two defects in `swimnetics-mobile`. (B1) A new athlete is missing from the record screen until the app restarts: `RecordingConfigScreen.js:42` fetches the roster in a mount-only `useEffect`, but it is a TAB screen so it mounts once per launch; the three sibling data-bearing tab screens already use `useFocusEffect` and this is the only one missed. (B2) The Record button on the athlete screen is a silent no-op: Phase 38-03 moved `AthleteDetail` to the Root stack (`RootTabs.js:46`) while `RecordingConfig` is a tab child (`:29`), and `navigate()` only bubbles UP to parents — never down into a child navigator — so nothing handles the action; needs `navigate('Tabs', { screen: 'RecordingConfig', params })`. The comment at `RootTabs.js:21-23` asserting cross-screen navigation "keeps working" went stale in the same commit. Verified as the only Root→Tab navigate call in the app — not a bug class. OUT OF SCOPE by user decision: delete-athlete is unchanged (it exists behind a `⋯` glyph at `AthleteDetailScreen.js:96`; user had never noticed it, tested it, judged it fine — the Team list having no delete while sessions have swipe-to-delete is recorded for a later UX pass, along with the fact that athlete delete writes direct via supabase-js on RLS rather than through the API); a dev-time guard for silently-unhandled navigate calls was offered and declined. Mobile repo only. Verification = a new EAS build the user runs right after apply, which should batch the iOS checks deferred from 54-01/47-03/41/42/44/21-02/34-01. UPDATED 2026-08-05 after live use: B1's symptom is broader than first reported — the roster is frozen at app launch in BOTH directions, so a DELETED athlete also stays on the record screen until restart; same cause, one fix. B3 FOLDED IN by user decision: freestyle analytics still blocked on the iPhone, which is NOT a bug — `ratings.py`'s threshold fallback shipped live in `dedac17`, but 54-01's `isAnalyticsReady = true` is uncommitted in the mobile working tree and has never been built (mobile HEAD 1296494 still carries the breaststroke-only gate at ReportCardScreen.js:169). 55-01 commits it so one paid build carries everything; no new code |
| 49 | Security Hardening (backend) | Planning (49-01 created 2026-07-20 — bang-for-buck fixes from a full-surface security review: redact 14 internal-error leaks, CORS `["*"]`→env allowlist, memory-safe upload size caps, athlete-ownership check on /process; api.py+tests only; autonomous:false, human-verify. Deferred: rate limiting, report-token expiry, full dep pinning) |
| 57 | Annotation Workflow (annotate-tool v2) | Planning (57-01 created 2026-08-05 — backend contract + pipeline, awaiting approval; 57-02 web page + 57-03 queue to follow). Discussed 2026-08-05 via /paul:discuss; CONTEXT.md written. TRIGGER: 19 trustworthy sessions collected 2026-08-05 (10 free / 4 br / 4 fly / 1 back) — the first corpus postdating the encoder-integrity fixes, and the blocking input to Phase 53 Track A4 and Phase 16-06. The Phase-47 tool works but was verified at n≈1; 19 in a sitting exposes throughput, precision and semantic gaps. REPO-VERIFIED (contradicts the request's framing): trailing trim ALREADY works via `finish_s`→`swim_end_idx` — what is missing is feedback, not mechanism; non-overlap is ALREADY guaranteed by `validate_annotation`'s ordering check — the UI just never says so, showing a bare "Dive 1.31 s" that reads as a duration. REAL HOLES: stroke marks are not constrained to the swim window (a stray mark in the dead tail becomes a garbage cycle feeding stroke_rate/DPS), `stroke_start_s` and the first mark can silently diverge, only 3 of 5 markers reach the metrics (`initial_phase` is carried over from the auto result at api.py:896), and `v95` (metrics.py:431) is computed over the FULL trace so the dead tail biases every session's dead-spot threshold. DECISIONS (user, AskUserQuestion ×4 rounds): view-fit chart + the swim window made AUTHORITATIVE (out-of-window marks rejected; v95 windowed) with profiles never truncated; the v95 fix applies pipeline-wide, accepting that dead_spot_s/coast_fraction stop being comparable with previously computed sessions; ONE MARK PER ARM ENTRY everywhere, cycles derived by pairing (2 marks/cycle free+back, 1 fly+breast — physiology, not a user choice), pairing factor derived from stroke_type with NO new column; NO PRELOADED MARKS — the editor starts blank (user: "in annotation, it should not have any preloaded"), which is methodologically stronger than what was offered since seeding ground truth from the segmenter being evaluated is circular; no auto-assist; UW kick + Breakout stay ground-truth-only and the UI says so; batch queue + prev/next IN scope. REACTION TIME: `useStartSequence.run()` resolves AT the blare and START is written after it, so t=0 IS cue-anchored (confirmed enabled on all 19) — but the BLE round trip plus the firmware's VARIABLE 150–300 ms warmup discard (ESP_32_V5.ino:383-392) understate true reaction time by 25–50%, differently each trial, and no firmware change can retroactively fix the 19 already collected. So: record `dive_start_s`, caption it a lower bound, ship NO reaction_time_s metric. ACCEPTED RISK: ~500 hand-placed marks on a trace with no video, where each freestyle cycle shows ~2 peaks that cannot be attributed to a specific arm — per-session and per-cycle-only alternatives were offered and declined; the marks record alternation timing, not verified arm identity, and the UI must say so. Context: .paul/phases/57-annotation-workflow/CONTEXT.md |

| 58 | Video Ground Truth (solo capture + annotate-from-video) | ✅ **CLOSED 2026-08-11 (4/5 plans shipped and verified: 58-01, 58-02, 58-03, 58-05).** Closed at user request. ⭐ **WHAT CLOSED IT: 58-01's auto-stop is now DEVICE-VERIFIED** — the phase's one outstanding risk, approved on assumption 2026-08-07 (*"assume 58-01 is working. approve it."*) and never fired against real hardware, with a too-early stop being the failure mode that destroys data rather than merely annoying. It rode the Phase 60-01 build and worked as intended, which also retires the `reset()` latent-bug concern. ✅ **58-04 CLOSED 2026-08-11 by Phase 61-03** (was: never built, carried out, homeless).
  The web now computes an end-anchored `video_origin_s` when none is stored and never overwrites
  one, so `VideoOverlayScreen` is no longer the only writer in the system. A second instance of the
  same defect was found and fixed in `VideoPane.attach()`. Historical description follows.
  ⚠ **58-04 (`VideoPane` end-anchor) WAS NEVER BUILT — carried out, NOT completed.** No plan was ever written; it cannot be called "working as intended" because it does not exist. Live consequence unchanged: `VideoOverlayScreen` on the phone is still the ONLY thing in the system that writes `video_origin_s`, so a record-with-video session never opened there arrives on the web at `origin_s = 0`, silently unsynced. It is WEB work and sits **outside Phase 60's scope** — 60-03 adds a second *mobile* door into Video Overlay, easing the manual workaround without replacing 58-04. **Needs a home in a future phase.** ⚠ **R1 NEVER ANSWERED across five consecutive checkpoints** (57-02, 58-01, 58-02, 58-03, this close-out) — whether ~40 arm-entry marks are placeable from tripod footage, which gates Phase 53 Track A4. Partial evidence says yes (the 08-07 batch, labeled with 58-02's tooling, is the best-covered in the corpus at ~90% vs ~50%). Closing the phase does not close R1. Prior status: Planning — discussed 2026-08-05 via /paul:discuss, CONTEXT.md written. TRIGGER: labeling the 19-session batch proved the Phase-57 tool's core assumption false for alternating strokes — freestyle/backstroke arm entries are not reliably discernible from the velocity trace (3-4 of 10 freestyle sessions unlabelable), while fly/breast trough-labeling is fine. The 19 have ZERO video and none can be added retroactively. Tripod + video test scheduled 2026-08-06, run SOLO (the swimmer is the operator). REPO-VERIFIED, mostly in the user's favour: the camera is already built, shipped and device-verified (RecordScreen.js:473-580 one-tap video + videoUploadQueue background FIFO, 47-03 verified in the Phase-55 build) — the 19 have no video because the mode wasn't used; web annotation ALREADY reaches iOS for metrics (PUT /annotations rewrites metrics_json, ReportCardScreen.js:94 reads it fresh) so item 3 needs no code; chart↔video scrubbing ALREADY works both directions (page.js:128 seek, playheadS marker) — the missing direction is MARKING, since marks land where you click the chart and there is no "mark at the video's current time"; buffer-and-dump makes the swim BLE-free (ESP_32_V5.ino:520-529 explicitly keeps recording through a disconnect; dumpBuffer retains the buffer; buffer-full truncates, never wraps). REAL GAPS: `video_origin_s` only reaches the server from VideoOverlayScreen (the background upload sends the file only) so an unopened session arrives at origin=0, silently unsynced; and a failed `writeCmd('STOP')` is caught non-fatal while the device keeps recording, inflating deviceDuration and therefore the auto-posted end-anchored origin — silent corruption of the same shape as Phases 51/52/57, which auto-stop removes by firing camera-stop and STOP off one timer. DECISIONS: auto-stop default **20 s** (user: "trust me" — confirmed against their own traces, 18.93 s and 16.53 s end to end with velocity back to zero before each recording ended, so 20 s clears both; 15 s would have clipped both finishes), editable with a live countdown since a too-early stop genuinely loses the swim's end; capture via the existing one-tap mode but HELD PROVISIONAL because it structurally pins the tripod near the block (BLE range) = the shallow ~4° rear angle most exposed to glare and occlusion; lab-now/product-later; annotate what's legible and flag the rest; no IMU. OPTICS VERIFIED: distance is NOT the constraint (~70° HFOV → 55 px/m at 1080p / 111 at 4K at 25 m; a 0.4 m splash is 22-44 px, left-vs-right separation 25-50 px) — angle, glare and occlusion are, and they are untested. Context: .paul/phases/58-video-ground-truth/CONTEXT.md |

| 59 | Segmenter Evaluation (ground-truth scoring harness + per-stroke dispatch) | ✅ **COMPLETE (5/5 plans) 2026-08-09.** Built the first ground-truth scoring harness the project has ever had, then used it to fix three real defects and route every stroke to a measured choice. **Butterfly F1 0.317→0.526 · breaststroke 0.232→0.444 · freestyle boundary F1 0.000→0.458 · freestyle rate 1.647→1.00 · swim window ip_end 3.93→1.99 s, finish 3.82→0.82 s.** ⚠ **ALL THREE BUGS WERE INVISIBLE TO `stroke_rate_spm`** — the metric everyone watches: (1) every wavelet boundary counted as a cycle, so freestyle read 1.75× high; (2) the swim window asked "where is MOTION" instead of "where is STROKING"; (3) `_anchors_from_marks`' leading pad put every freestyle cycle half a cycle out of phase, with the rate ratio reading 1.00 either way. ⚠ **THE PHASE'S METHODOLOGICAL LESSON, learned twice:** a gate measured on the tuning subset proves nothing — 59-03's window passed on its 12 tuning sessions and collapsed on 13 of 36; 59-04's `peakpick` won butterfly on F1 and would have shipped phase-drifting cycles. LOSO scoring and `TestCycleRegularityGate` exist because of it. ⚠ OPEN, carried out (none blocking): the trace-vs-video / tether-sag question (decisive experiment = one swim marked twice, NOT done); ground truth redefined to "the TRACE" mid-phase with nothing re-scored; the corpus mixes chart-timed and video-timed labels; 59-03's window regressed butterfly/breaststroke and 17/36 sessions fall back; breaststroke rests on n=2 and backstroke on ZERO; 37 stored sessions out of scale (16 annotation-derived, never to be overwritten); `ratings.py` thresholds now sit on changed inputs. Prior status: Planning — discussed 2026-08-08/09 via /paul:discuss (AskUserQuestion ×3 rounds, 12 questions), CONTEXT.md written. **SUPERSEDES the "16-06 segmenter tuning" slot.** TRIGGER: 23 sessions are now annotated (236 marks: 14 freestyle / 7 butterfly / 2 breaststroke / **0 backstroke**) and the user asked to train a segmenter. MEASURED, not recalled: that corpus is one swimmer on one device and is not a training set, but it IS an evaluation set — and evaluation has never existed, since `segmentation_reliable=False` is a hardcoded constant rather than a measurement. FIRST-EVER SCORE of `segment_cycles_wavelet` against the labels (annotated swim window, greedy 1-to-1 match): vs human CYCLE boundaries recall 0.57 / precision 0.28 at ±0.2 s; vs human ARM ENTRIES, freestyle recall 0.82 / precision 0.67 at ±0.3 s, median timing error 0.06–0.16 s. The ridge tracks the right oscillation and lands within ~0.1 s — it disagrees about what one oscillation MEANS, stroke by stroke. **`marks_per_cycle` ≠ `boundaries_per_cycle`**: freestyle emits 1.15–1.5× the arm-entry count, butterfly a wildly unstable 1.18–2.18× the cycle count (the ridge sometimes locks onto the two-dolphin-kick harmonic), so no single divisor exists and `annotations.MARKS_PER_CYCLE` cannot be reused on the auto path. LIVE DEFECT FOUND: `compute_session_metrics` never receives `stroke_type`, so every wavelet boundary counts as one cycle — on the well-labeled 08-07 freestyle batch the auto `stroke_rate_spm` is **1.48–2.08× (median ~1.75×)** the annotation-recomputed value, i.e. every freestyle session in the app and on the web shows roughly double the true cycle rate. ENABLER: `sessions.velocity_profile` + `sample_rate_hz` are stored per session, so the harness needs no raw-CSV download. DECISIONS (15): harness before any algorithm work; primary gate = per-stroke boundary F1 at ±0.15 s with a tolerance sweep (rate error + MAE reported, not gating); partial labels excluded via a hand-curated list (4 proposed, user to confirm) with excluded sessions still scored for recall; tuning scope free+fly, breast/back scored but never tuned; committed pure module + CLI + checked-in fixture + pytest regression, plus an uncommitted scratch notebook; **per-stroke segmenter dispatch with `metrics.py` owning its own registry** (no import edge to annotations.py — the labeling convention and segmenter behavior are different numbers); the harness ALSO scores the four human phase boundaries, since `detect_phases`/`detect_initial_phase` have never been measured either and `detect_initial_phase` is breaststroke-shaped (dive surge → pulldown peak) while running on all four strokes; a generic named-series scorer so the coming UW-kick segmentation is a caller change, not a rewrite (⚠ the annotation contract has nowhere to store UW kick marks today); backstroke inherits the freestyle implementation, documented as unvalidated; breaststroke scores wavelet AND the never-called trough segmenter, routing decided on the numbers; **refactor first / behavior second** — 59-02 is a pure dispatch refactor whose acceptance is byte-identical harness output, 59-03 changes behavior, because this codebase has a documented history of silent metric drift (51/52/57). Context: .paul/phases/59-segmenter-evaluation/CONTEXT.md |

| 60 | Mobile App Rework (per-cycle analytics + video access + chart windowing) | ✅ **COMPLETE (3/3 plans) 2026-08-11.** The coach's poolside device stopped showing less than the laptop, and stopped showing one number wrong. **Suite 273 throughout — zero Python touched in the entire phase**; export exit 0 at every step. Commit `5e2bde0`; mobile `098f345`/`8c4a4c0`/`a82799d`. 15 decisions (D11 amended, D12–D15 added mid-apply), all user calls. **60-01** real sample rate (**−10.0% → +0.0%**, measured live, 4/4) + four per-cycle charts + Data Quality retired to a dropout strip + `cv_isi` gate → banner. **60-02** brush bar replaces pinch + a controlled window primitive, with the unwindowed polyline proven **byte-identical** against the pre-refactor algorithm transcribed from git. **60-03** video from any saved session + rolling playhead window + origin protected from silent overwrite + a user-dropped START marker. ⭐ **THREE THINGS THIS PHASE GOT RIGHT THAT WERE IN NO PLAN:** 60-01 found a live −10% error nobody asked about; 60-02's byte-identical gate proved a refactor had not drifted; and 60-03's best design change came from the user asking *"why are there different screens?"* at a checkpoint, which **deleted** a parameter, a branch and a concept instead of adding them. ⚠ **NOT VERIFIED ON A DEVICE** — all three plans rest on device-independent evidence plus approvals; **specifically unconfirmed is whether the 2 s rolling window reads well during playback**, the point of the original ask. ⚠ CARRIED OUT: the `currentTime` wobble hypothesis (unmeasured); **58-04 still owed and homeless**; **52-02 better motivated** (most NULL-rate rows are ~90 Hz, not ~100, correcting a Phase 59 generalization); **three unconnected notions of "when the swim starts"** with the user's *"I don't trust auto detect baseline"* as a Phase 53 input; the START marker is in-memory only. Prior status: Planning — discussed 2026-08-10 via /paul:discuss (AskUserQuestion ×3 rounds, 11 questions), CONTEXT.md written, **11 decisions D1–D11, zero open questions**. ⚠ **`swimnetics-mobile` ONLY** — separate, user-owned git repo; the single `myswimcoach` edit in the whole phase is a `CLAUDE.md` documentation correction. No Railway or Vercel deploy. TRIGGER: user asked for five mobile changes; reading the source found a sixth thing they did not ask about, and it is a live wrong number. ⚠⚠ **THE REPORT CARD'S TIME AXIS IS ~11.7% WRONG AND HAS BEEN SINCE PHASE 52.** `89205ca` fixed three web files; **it is a `myswimcoach` commit and the mobile repo was never in its diff.** Web `sessions/[id]/page.js:120` derives `fsHz` from `sample_rate_hz`; mobile `ReportCardScreen.js:170` still hardcodes `i / 100`, and **`sample_rate_hz` appears ZERO times in the entire mobile `src/`**. Four consumers wrong: chart x-axis (47.1 s swim drawn as 42.2 s), cycle overlay, **Time-to-Distance** (7.16 s for a true 8.0 s) and CSV export — and Time-to-Distance carries a **second, compounding** error, since `baseline_end_s` is TRUE seconds compared against the FAKE array at `:536`, so the baseline index is wrong rather than merely scaled. ✅ VERIFIED UNAFFECTED: the `/process` path (server's real `t_dec`) and mobile `CompareScreen` (metrics only). ⚠ `CLAUDE.md` under-describes it, naming only "client-side CSV export". DECISIONS (11, all user choices): D1 full web parity, NULL→100, **no backfill**, + D1c the CLAUDE.md correction; D2 four per-cycle charts (`dist_m`, `coast_fraction`, `duration_s`, `arm_peak_vel`) — ⚠ **THE ASK REQUIRED TRANSLATION**, since "cycle-by-cycle ISI CV" is not a thing: `cv_isi`/`cv_arm_peak_vel` are the *dispersion of* those series, not per-cycle values, so the series is charted and the CV becomes its caption (confirmed with the user); D3 Data Quality card removed; D4 video via signed URL (`GET /sessions/{id}/video-url`), button on the report card; D5 window presets 1/2/5 s/All, default 2 s, playhead-driven; D6 brush bar replaces pinch; D7 **ONE controlled-window primitive, TWO drivers** — the user corrected an earlier framing that bundled asks #4 and #5 as one feature; D8 charts plot ALL cycles with no ramp-up distinction (*"I no longer need that"*), **display-only**; D9 one dropout strip survives, >5% only; D10 the `cv_isi > 0.80` gate becomes a banner instead of blanking Efficiency, **on both screens**; D11 stored origin wins and the read path never auto-writes. ⚠ **`ramp_up` IS LOAD-BEARING:** `metrics.py:841-854` tags cycles and `ss_cycles` (`:892`) then drives **`stroke_count` (which IS the steady count, not the total)**, `stroke_rate_spm`, every `mean_*`/`cv_*` and `fatigue_index_pct` — so D8 is display-only; removing the concept would move every session metric ever recorded, a fourth comparability break after 57's, 59-03's and 59-05's. Two mismatches now knowingly ACCEPTED and not to be "fixed": more dots than `stroke_count`, and a mean line off the dots' visual average. ⚠⚠ **BLOCKING ON ENTRY: 58-01 IS UNCOMMITTED** in the mobile tree — 7 files including **both** `RecordScreen.js` and `VideoOverlayScreen.js`, which Phase 60 edits; it was approved on assumption and its auto-stop has **never fired against real hardware**, so an entangled diff would make any Phase-60 failure unattributable. 60-01 opens with a `checkpoint:human-action` for it. ⚠ **58-04 STILL OWED AND INTERACTS WITH D11** — `VideoOverlayScreen` is currently the ONLY thing in the system that ever writes `video_origin_s`, and Phase 60 adds a SECOND door into it, which is exactly why only one of them may write. ⚠ CORRECTION AT PLAN TIME: `DataQualityCard` renders on **BOTH** screens (`ReportCardScreen.js:492` **and** `RecordScreen.js:954`), so `RecordScreen.js` is in scope for three decisions (D3, D9, D10), not the one D10 named. ⚠ **NO CHART LIBRARY ON MOBILE** — `react-native-svg` + `PanResponder` only; recharts is web-only, so both the `<Brush>` pattern and the per-cycle charts are hand-rolled, and D5 chose presets over a slider because `@react-native-community/slider` is a native module needing a fresh EAS build just to test. Context: .paul/phases/60-mobile-app-rework/CONTEXT.md |

| 61 | Web Portal Rework (report card + video route + Compare redesign + ramp_up removal) | ✅ **COMPLETE (5/5 plans) 2026-08-11.** Delivered all five of the user's asks plus one they did not ask for. **⭐ `ramp_up` was never ramp-up** — measured on two corpora, the split marked the swimmer decelerating into the WALL (median excluded-cycle position 0.91 on the live DB; 0 of 13 `raw/` sessions had a leading run), not accelerating from rest. Removing it made the charts and the numbers describe the same cycles, at the cost of a **fourth comparability break** and a re-anchoring of two `ratings.py` bands. **⭐ 58-04 CLOSED** after being owed and "homeless" since 2026-08-07, plus a second instance of the same `?? 0` defect found in `VideoPane.attach()`. Suite 273 → 274; zero Python outside 61-01. ⚠ CARRIED OUT: **synced playback on Compare is a TODO, deliberately unplanned**; the video chart no longer auto-follows the playhead (D16 withdrawn); generated names are derived, not persisted; mobile D5c comment fix uncommitted. Prior status: Planning (discussed 2026-08-11 via `/paul:discuss`, then GRILLED via `/grilling` with 4 measurement runs; CONTEXT.md written, **15 decisions D1–D15, zero open questions**; 61-01 created, awaiting approval). TRIGGER: user asked for three web changes, then added two more mid-discussion — redesign Compare, and *"rework reports… it feels like the numbers are coming out of nowhere. And also for the graphs the numbers don't reflect what's actually shown on graph."* ⚠⚠ **THAT LAST COMPLAINT IS A REAL DEFECT AND THE GRILLING FOUND ITS CAUSE IS NOT WHAT ANYONE THOUGHT.** `metrics.py:892` computes every `mean_*`/`cv_*` and `stroke_count` over `ss_cycles` (steady only) while the charts plot ALL cycles — so the mean line is a subset's average drawn over the full set, and `stroke_count` is lower than the dot count. Phase 60-01 met both on mobile and recorded them as *"two mismatches knowingly ACCEPTED and not to be fixed."* ⭐⭐ **BUT `ramp_up` IS NOT RAMP-UP.** Measured two ways: on `raw/`, **0 of 13** affected sessions have a leading run and **13/13 are scattered** (`carlos_fr_1`=[9] of 10, `leo1`=[18] of 19, `leo4`=[4,5] of 6); on the live DB, excluded-cycle **median position 0.91**, 59% in the final 20% of the swim. It is a velocity gate (`arm_peak < 0.50 × p75`) that in practice catches **the swimmer decelerating into the wall** — the name has been wrong in `metrics.py`, in Phase 60's record, and in the first draft of Phase 61's CONTEXT.md. CONSEQUENCE: removing it makes the wall-touch a stroke, which lands in `q4` of `fatigue_index_pct=(q1−q4)/q1` and is a low outlier in the arm-peak array, so on the trusted live corpus p90 goes **cv_arm_peak_vel 0.277→0.638** and **fatigue_index_pct 35.4→73.6** (medians barely move — it degrades the ~39% of sessions with excluded cycles, not all). Rating bands flip DOWNWARD only: Consistency 5/11 flip and **11/11 end on `needs_work`**; Endurance 8/11 flip. ⚠ **D5 (remove `ramp_up` entirely) was REAFFIRMED THREE TIMES with those measurements on screen — it is settled, do not re-open.** **D15 (re-anchor the two `ratings.py` bands) is its mandatory mitigation and must ship in the same commit**, or two of four pillars go decorative. DECISIONS (15): D1 new route `/app/sessions/[id]/video`; **D2 the web computes `video_origin_s` itself and never overwrites a stored one — CLOSES 58-04, homeless since 2026-08-07**; D3 `CycleTable` out, `CycleCharts` to 4 panels (mobile parity; Impulse+Trough dropped from the web); D4 Data Quality removal at mobile parity (dropout strip >5%, `cv_isi` blackout→banner); **D5 remove `ramp_up`**; D6 one hierarchy for "when the swim starts" — annotation authoritative → auto fallback → mobile marker a local override that never writes (**retires a Phase-60 carried-out concern; no code change**); D7 report card names its Time-to-Distance start source and links to Annotate when auto-detected; D8 deterministic creative mnemonic session names, **derived at render time, never written to `sessions.name`**; D9 two stacked Compare charts on TRUE per-session sample rates + in-memory nudge (**fixes the last known-wrong time axis in the system**, superseding the CLAUDE.md note calling 100 Hz deliberate there); D10 Compare video right-column, colour-matched to each trace; D11 per-cycle line charts replace `MetricDeltaTable`; D12 prev/next session nav; D13 the video route shows the attach input when no video exists; D14 annotate page otherwise OUT of scope (`VideoPane` backward-compat is an AC); **D15 re-anchor `cv_arm_peak_vel` + `fatigue_index_pct`** from measured post-D5 percentiles. ⭐ **VERIFIED IN THE USER'S FAVOUR AND REMOVED FROM SCOPE: Time-to-Distance is ALREADY annotation-driven on the web** (`dive_start_s`→`annotations.py:187`→`manual["baseline_end_idx"]`→`metrics.py:765`→`baseline_end_s`→`page.js:320`), and mobile already matches the requested model at `ReportCardScreen.js:553`. Nothing to build, nothing broken. DECLINED by the user: CSV export button (`GET /sessions/{id}/export` remains caller-less system-wide), the borrowed-bands caveat (stays Phase 53's), the 57-03 annotation queue, and a web start marker. INCIDENTAL: `fetch_sessions.py:30` still hardcodes `FS = 100.0`; **6 of 67 live sessions have NULL `sample_rate_hz`** (further motivating 52-02). Context: `.paul/phases/61-web-portal-rework/CONTEXT.md` |

| 64 | Fullscreen Video + Velocity Overlay (web) | ✅ **COMPLETE (3/3 plans) 2026-08-16 — unified.** 64-01 fullscreen SVG velocity overlay + drag-to-scrub (`0f63a15` + `fe3b53b` → Vercel); 64-02 `sessions.acceleration_profile` as an exact derivative of velocity, backfill 70/70 (`f133c56` → Railway); 64-03 acceleration on BOTH the overlay (stacked signed band) and a new static `AccelerationChart`, page-synced toggles + colour, `useTracePrefs` (`fe3b53b` → Vercel). ⚠ The stored acceleration is a ~5 Hz reconstruction that reads **choppy** — **Phase 66 replaces it with a Savitzky–Golay derivative** (display-only; metrics.py never consumes acceleration). ⚠ Known limitation: no-video sessions can't toggle acceleration (toggles live in the video bar). Prior status: **64-01 SHIPPED 2026-08-14 (commit `0f63a15` → Vercel).** Delivered end-to-end and iterated live: reusable `VideoTracePanel` (inline on the report card + fullscreen), `FullscreenControls`→`PlaybackControls`, red default trace + colour picker (persisted), compact strip, downward-triangle stroke marks in a darker shade of the trace, all confined to `TraceOverlay`. **Owes UNIFY.** ⚠ **Drag-to-scrub added AFTER the push and is UNCOMMITTED** (window-follow + edge-scroll ≤2s, pause-on-grab, default window All) — first cut was "very buggy" (STUCK-ACTIVE drag froze playback; fixed with window-level pointer listeners, no setPointerCapture, pointercancel teardown for mouse+iPad); awaiting the user's live feel-test before push, so production still has click-to-seek only. **⭐ NEW PLANS 64-02 + 64-03 (Acceleration trace, 2026-08-14, awaiting approval):** **64-02** (backend, `depends_on []`) stores `sessions.acceleration_profile` — accel is a pure derivative of the already-stored velocity (`vel_acc_extraction.py:135-138`) and `api.py:172` already computes it but drops it as `_accel`, so new sessions = ~2-line write + existing rows backfill EXACTLY from `velocity_profile` (no raw-CSV reprocessing); extract `acceleration_from_velocity` (byte-identical test) → patch_10 + /process write → idempotent backfill → human-action checkpoint. **64-03** (web, `depends_on 64-02`) puts acceleration on BOTH the overlay (stacked strip: own signed scale + zero line + own colour + readout, one shared window/scrub/playhead) AND the static chart (new `AccelerationChart` under `VelocityChart`); independent velocity/accel toggles (default velocity-only, persisted) + accel colour picker (cyan); visibility/colour state lifts to the page; `VelocityChart.js` untouched. 7 decisions via AskUserQuestion ×2 (backend+DB not in-browser derive · both surfaces · stacked not overlaid · independent toggles · backfill all existing · default velocity-only · accel own picker). Prior status below. **Planning — 64-01 created 2026-08-13, awaiting approval.** `autonomous:false`, `depends_on []`, wave 1. **4 files: 2 new (`TraceOverlay.js`, `FullscreenControls.js`), 2 edited (`VideoPane.js`, the video route's `page.js`).** 3 auto tasks + 1 `checkpoint:human-verify`. 8 ACs. ⚠ **PLANNED WHILE PHASE 63 IS STILL OPEN** (63-02's checkpoint unrun, phase not unified) — deliberate: 63 is doc-only and 64 is `web/`-only, so `files_modified` cannot collide, but 63 still owes its checkpoint + `/paul:unify`. ARCHITECTURE CALL MADE AT PLAN TIME (CONTEXT left it open, recommending (b)): the fullscreen target is a **page-level stage container** wrapping `<VideoPane>`, not `VideoPane`'s own root — but the control bar lives INSIDE `VideoPane` rather than in the stage, because the bar needs `rate`/`muted`/`effectiveOriginS`/`savedOrigin`/`step`/`nudge`/`saveSync` and lifting all of that out would have meant either an imperative handle or duplicating the origin logic — the one thing D9 forbids. The stage therefore owns only fullscreen state, the idle timer and the keyboard; `VideoPane` gains `fullscreen`/`videoElRef`/`playToggleRef`/`onOriginChange`/`onExitFullscreen`/`dimmed`, **all defaulting to today's behaviour** so the annotate call site (`annotate/[id]/page.js:426-436`, which passes none of them) is untouched. `playToggleRef` follows the file's existing `seekRef`/`frameStepRef` idiom rather than inventing a new one. ⭐ **TraceOverlay runs ZERO React state in its animation loop** — the polyline is built once in DATA coordinates, one rAF loop imperatively sets the svg's `viewBox`, the playhead line's x, and the readout's `textContent`; the playhead lives INSIDE the panned svg so it stays correct when the window clamps at the trace ends and is therefore not centred. `preserveAspectRatio="none"` forces `vector-effect="non-scaling-stroke"` on every stroked element or lines render as wedges. Verification is `npm run build` + `npm run lint` + `git diff --stat` scoped to 4 files + **`pytest tests/ -q` still 274 as a guard that no Python moved**, plus a `git diff` check that `VideoPane`'s non-fullscreen branch is unchanged. Checkpoint asks the user to verify against BOTH a session with a stored origin (24 of 62) and one with a NULL origin (5 of 62, exercising the computed end-anchor), and to report **what the cycle boundaries look like against real footage** — the first time detector output and video share a screen. Prior status: Discussed 2026-08-13 via `/paul:discuss` (4 rounds, 14 questions); CONTEXT.md written, **12 decisions D1–D12, zero open questions**. ⚠ **WEB ONLY** — no Python, no schema, no API, no mobile; Python suite untouched by construction; deploy = Vercel. TRIGGER: *"is it possible to actually overlay the velocity on the video? … the video is extremely small. I want to be able to fullscreen the video and still see the trace."* ⭐ **THE CAUSE IS PRECISE, NOT VAGUE:** 61-03 shipped `/app/sessions/[id]/video` with `<VideoPane>` and `<VelocityChart>` as **DOM siblings** (`page.js:119-143`), so the native fullscreen button promotes the `<video>` element alone into the top layer and the chart is simply not in it. Fix = fullscreen a CONTAINER that already holds both, and drop the native control bar whose fullscreen button would re-create the trap. DECISIONS (12): D1 fullscreen the container, never the `<video>` (the element must not move in the DOM — that would drop playback position and re-fetch the signed URL); D2 custom control bar (play/pause, ±1 frame, 0.25/0.5/1×, mute, exit) — chosen over `controlsList="nofullscreen"`, which is Chrome/Edge-only and leaves the trap open on Safari + Firefox; D3 translucent strip **spanning the FULL screen width** (~2.4× the room of a video-box-width strip for the same span) with a scrim, since a blue trace over sunlit water is low-contrast; D4 `object-contain`, never crop — accepted consequence: portrait 3:4 footage on 16:9 is ~42% of the width, so the strip sits mostly on black bars; D5 **fixed 2 s rolling window that follows the playhead**, no presets (61-03 deleted them as *"redundant"*) — ⚠ this re-introduces the auto-follow 61-03 withdrew (CONTEXT D16), **scoped strictly to fullscreen**; D6 **new hand-rolled SVG overlay, NOT recharts** (viewBox-panned; recharts re-renders ~2000 points/frame and would stutter — the exact thing being asked for); D7 **`requestAnimationFrame`, not `timeupdate`** (~4 Hz, and silent for sub-100 ms seeks — `VideoPane.js:99-101` already documents this); D8 overlay draws trace + centred playhead + cycle boundaries + live velocity readout, ⚠ **requiring the page to start selecting `metrics_json`** (it fetches only `velocity_profile`/`sample_rate_hz`/… today at `page.js:33-36`) — elapsed/total time and saved annotation marks OFFERED AND DECLINED; D9 ±0.1 s nudge + Save reachable IN fullscreen, ⚠ **reusing `VideoPane`'s handlers so it never becomes a second writer of `video_origin_s`** (the invariant 58-04 was closed on); D10 windowed layout unchanged apart from the new button; D11 scope is the video route ONLY — annotate (would need keyboard marking) and Compare (two-video layout + Phase 61's unplanned synced-playback TODO) are OUT; D12 mute toggle only. ASSUMPTIONS: A1 desktop surface — **iOS Safari supports fullscreen only on `<video>` via `webkitEnterFullscreen`, so container fullscreen will not work on an iPhone** and must degrade, not throw; A2 playhead centred, window clamped at the trace ends; A3 Space / ←→ / Esc work regardless of the auto-hidden bar (`VideoPane` already exposes `frameStepRef` for exactly this); A4 bar + strip auto-hide together after ~2 s idle. ⚠ **THIS PHASE WILL REVEAL WRONGNESS, AND THAT IS THE POINT:** it is the first surface where detector output and real footage share one visual field — cycle boundaries come from a segmenter Phase 59 measured at boundary **F1 0.44–0.53** with `segmentation_reliable` still hardcoded `False`, and a bad `video_origin_s` (the end-anchor is inflated by Phase 58's non-fatal `writeCmd('STOP')` failure) becomes obvious once the trace sits on the swimmer — which is why D9 puts the repair where the error is noticed. Also: a 60 Hz rAF playhead is the first thing that would make Phase 60-03's **unmeasured `currentTime` wobble hypothesis** visible. ENABLER: **29 of 62 live sessions have `video_path` and 24 have a stored `video_origin_s`** (DATA-FLOW.md:559-567), so there is plenty to verify against; 5 have video with NULL origin (F-b), fixed on open by 61-03 and NOT backfilled here. OPEN DESIGN CALL LEFT TO `/paul:plan`: whether the fullscreen container is `VideoPane`'s own root (self-contained, but grows it into a chart component) or a page-level wrapper taking a `fullscreen` prop (**recommended** — more surgical; annotate's usage unaffected since it defaults false). `VideoPane` back-compat on `/app/annotate/[id]` is an AC either way, mirroring 61's D14. Context: `.paul/phases/64-video-velocity-overlay/CONTEXT.md` |

| 65 | Underwater Phase Detection (free / back / fly) | **Planning — 65-01 created 2026-08-15, awaiting approval.** `type:research`, `autonomous:false`, `depends_on []`, wave 1. **2 files, both new (`tools/underwater_probe.py`, `65-01-FINDINGS.md`) — measurement only, zero product code.** 2 auto tasks + 1 `checkpoint:decision`. 3 ACs. **3-plan phase:** 65-01 measure → 65-02 fix (`metrics.py` breakout detection + underwater metrics + tests) → 65-03 web reporting. ⚠ **PLANNED WHILE 63 + 64 ARE OPEN** — deliberate and non-colliding: 65-01 is `tools/`-only; 65's web tail (65-03) touches `web/app/app/sessions/[id]/page.js` which 64-01 also edits, so **65-03 sequences after 64 unifies**. TRIGGER: reviewing an auto-segmented butterfly session ("indigo ray"), the user found the segmenter marking the dive peak + the underwater dolphin kicks as stroke cycles — *"it recognized the part of dive as a cycle of stroke… it mistakenly latched onto the dolphin kicks as well"* — and confirmed *"it persists for other strokes as well… fly, free, back are the same in terms of phases — only breaststroke is different."* ⭐ **ROOT CLASS (verified in code):** Part 1 (phase detection) places `ip_end` too early — inside the underwater kicks — so Part 2 (the cycle segmenter, correct on a clean window since 59-05) carves the dive + kicks into "cycles," poisoning every per-cycle average. `ip_end` resolves as `detect_swim_window` primary → `detect_initial_phase` first-trough fallback → manual (`metrics.py:774-793`); both auto sources are weak here. ⭐ **THE "ANNOTATE IT" HALF IS ~80% ALREADY BUILT:** `annotations.py:44-49` already models `dive → underwater → stroke → finish` as a first-class, coach-correctable, exportable phase where `stroke_start_s` IS the breakout (the separate breakout marker was removed in Phase 58 as "not reliably readable", `annotations.py:22-27`); what's broken is only the AUTO seed inheriting the wrong `ip_end` (`build_seed`, `:121-123`). So the phase = fix auto breakout detection (hard) + add underwater duration/distance metrics (cheap) + surface on web (small). DECISIONS (CONTEXT D1–D10): D1 scope = the three dolphin-kick strokes (shared phase anatomy), routed on `stroke_type`; D2 breaststroke EXCLUDED, byte-identical, regression-guarded; **D3 HARDCODED: one lap, no turns**; D4 the bug is a COARSE region error, not sub-second precision (Phase 58 already ruled the surfacing instant unreadable and accepts the first cycle straddling the breakout); D5 fix BOTH ip_end sources; D6 "report + annotate" = fix the seed + ADD underwater metrics, no new phase boundary invented; **D7 MEASUREMENT FIRST (this plan)**; D8 leading hypothesis — kicks LACK an arm-pull surge, and for fly `detect_swim_window` likely fails because the CWT ridge locks to the 2x dolphin-kick harmonic so f_ref = kick rate (`metrics.py:412`); D9 comparability break accepted, fix-forward, backfill deferred (5th such break after 57/59-03/59-05/61-01) — user: *"don't worry about it. the whole point is trying to fix the issue"*; D10 web surfaces it, mobile a separate follow. ⚠ USER-REPORTED across all three strokes OVERRIDES 59-03's freestyle-heavy in-sample numbers (one swimmer, breast n=2, back n=0). Context: `.paul/phases/65-underwater-phase-detection/CONTEXT.md` |

| 66 | Acceleration Derivative (Savitzky–Golay) | ✅ **COMPLETE (1/1 plans) 2026-08-16.** Replaced the choppy ~5 Hz decimate→gradient→linear-interp acceleration with a full-rate **Savitzky–Golay** first derivative (`120908f`) — on a clean sinusoid it tracks the analytic accel to **0.3% RMS** (old 118%) and preserves peaks the old path crushed **~60%** on a real session. Then made the SG window **STROKE-DEPENDENT** (`ee1852c`): free/back 0.50 s, fly/breast 0.25 s, threading `stroke_type` through `run_pipeline` + `/process` + the backfill (freestyle TV 268 vs 740 at the sharp window). Deployed → Railway; re-backfilled **70/70**. **Display-only** (metrics.py never consumes acceleration). Suite 276→277. ⚠ Windows hand-tuned on one swimmer — the principled version sets each from a measured velocity spectrum once a broader corpus exists. Prior status: **Planning — 66-01 created 2026-08-16, awaiting approval.** `type:execute`, `autonomous:false`, `depends_on []`, wave 1. **3 files: `vel_acc_extraction.py`, `tests/test_metrics.py`, `tools/backfill_acceleration.py`.** 3 auto tasks + 1 `checkpoint:human-verify` (deploy + re-backfill). 5 ACs. TRIGGER: reviewing the Phase-64-03 acceleration trace, the user found it *"extremely choppy… definition way too low."* ⭐ **THE DATA IS CHOPPY, NOT THE CHART:** `acceleration_from_velocity` (`vel_acc_extraction.py:102`) decimates velocity to ~5 Hz, `np.gradient`s it, then **LINEARLY** interpolates back to ~89.5 Hz — so the signal carries only ~2.5 Hz of bandwidth reconstructed as straight-line segments 0.2 s apart (plus corners from the forward-only velocity clamp at `:150`). FIX: replace the body with a **Savitzky–Golay first derivative** at full rate (`savgol_filter(vel, ~0.25 s odd window, polyorder=3, deriv=1, delta=1/fs, mode="interp")`) — fits a local cubic and takes its analytic derivative at every sample, smoothing + differentiating in one pass without finite-difference noise blow-up. ⭐ **ONE FUNCTION IS THE SINGLE SOURCE OF TRUTH:** `run_pipeline` (`:153`, the `/process` write) and `tools/backfill_acceleration.py` (`:106`) both call it, so the swap propagates to new sessions AND the re-backfill. ⚠ **DISPLAY-ONLY:** `metrics.py` consumes `vel`, not `accel` (no acceleration in `compute_session_metrics`'s signature or any session-metric key), and velocity is untouched — so ZERO metric changes; only the 64-03 overlay/chart trace changes. Re-backfills the 70 rows 64-02 filled, from their stored `velocity_profile` (a new `--recompute` overwrite mode; no raw-CSV reprocessing) — a comparability break on `acceleration_profile` ALONE. ⚠ `tests/test_metrics.py::test_acceleration_from_velocity_matches_inline` (`:376`) PINS the old decimate→gradient→interp algorithm via `assert_array_equal` and MUST be rewritten to smoothness + ramp-exactness assertions; `tests/test_api.py::test_insert_carries_acceleration_profile` stays green. Context: `.paul/phases/66-acceleration-derivative/66-01-PLAN.md` |

### Phase 63: Data Flow Map — Planning (63-01 created, awaiting approval)

**Plans:** two, sequential — 63-02 appends to the file 63-01 creates.
- [ ] **63-01 PLAN created 2026-08-13, awaiting approval** — the **reference half**.
  `autonomous:false`, `depends_on []`, wave 1. **2 files, both new.** 2 auto tasks +
  1 `checkpoint:human-verify`. 7 ACs.
  Sections 1–6 + 10 + 11: four data stores, full field dictionary (every column of 7 tables
  plus every jsonb payload expanded), all 24 endpoints × real callers as `file:line`, the
  two-doors pattern with every exception, master Mermaid diagram, not-in-product-path list,
  dated snapshot. Plus `tools/dataflow_probe.py` so the snapshot regenerates.
  ⚠ **The probe runs against PRODUCTION with the service-role key, which bypasses RLS.** The
  plan forbids every write call and forbids printing PII.
  ⚠ **The caller inventory is RE-DERIVED, not copied** — `API-AUDIT.md`'s is dated 2026-07-30
  and predates Phases 57–61.
  ⚠ SCOPE ADDITION beyond CONTEXT.md, flagged: the committed probe tool follows the 61-01
  `tools/rampup_impact.py` precedent; strike it if unwanted.
- [ ] **63-02 not yet written** — the **explanatory half**: lifecycle drill-down diagrams
  (record→process→store→display · annotate→recompute→overwrite · video→origin→sync · parent
  report · coach chat), why-each-thing-exists, the findings list, then the stale-stamps in
  `CODEBASE-AUDIT.md` §4 + `API-AUDIT.md`'s inventory + `CLAUDE.md`, and the D7 pointer line in
  `swimnetics-mobile/CLAUDE.md`.

### Phase 63 original goal

**Goal:** one document that answers "where does this byte live, who put it there, and why does
this exist" for the whole product path — because 61 phases have shipped and the system map lives
only in the user's head and two partly-stale audit docs.

⚠ **DOC-ONLY.** No product code, no schema, no deploy. Findings are recorded, not fixed (D8).

Discussed 2026-08-12 via `/paul:discuss` (2 rounds, 8 questions); CONTEXT.md written, **8
decisions D1–D8, zero open questions**. Context: `.paul/phases/63-data-flow-map/CONTEXT.md`.

⭐ **THE TRIGGER'S OWN EXAMPLE IS ALREADY CLOSED, AND THAT IS THE POINT.** The user cited
`ramp_up` as something they shipped without understanding; Phase 61-01 removed it after
measuring that it was never ramp-up but the swimmer **decelerating into the wall** (median
excluded-cycle position 0.91 live). It survived four phases because nothing ever asked what it
selected. This doc exists to make that class of drift visible earlier.

DECISIONS (8): D1 map + rationale, **not** a hunt for the next `ramp_up` (that is a separate
future phase, carried out); D2 new `DATA-FLOW.md` owns data flow, `CODEBASE-AUDIT.md` §4 and
`API-AUDIT.md`'s inventory get stale-stamped to point at it; D3 whole product path, dev and
experimental surfaces named in one line each; D4 repo markdown + Mermaid, layered diagrams;
D5 verify live read-only against Supabase, counts stamped as a dated snapshot; D6 full field
dictionary for every jsonb payload; D7 one pointer line in `swimnetics-mobile/CLAUDE.md` — no
copy, targeting the Phase 60 cross-repo failure mode; D8 document only, findings routed.

VERIFIED THIS SESSION (live, read-only): **62 sessions / 24 annotations / 5 reports / 3 athletes
/ 1 coach / 1 team / 2 devices.** `raw_csv_path` 62/62; `sample_rate_hz` **6 NULL**;
`video_path` 29 but `video_origin_s` 24 → ⚠ **5 sessions have video and no origin — the 58-04
defect's data footprint, which 61-03's forward-looking fix did not backfill**;
`metrics_json_auto` 24/62, exactly matching the annotation count, so every annotated session had
`metrics_json` overwritten by human marks; `name` 10/62 and `notes` 2/62; `upload_status`
`'complete'` on **62/62** — a column that has never discriminated anything. Strokes: free 31,
breast 15, fly 15, **back 1**. TOPOLOGY: **four** data stores, not two (Postgres, Storage,
phone-transient, laptop-dev); **no AsyncStorage session cache on mobile** despite
"offline-safe recording" still unchecked in PROJECT.md; and **two doors into the same data** —
reads mostly direct via supabase-js under RLS (21 web sites / 22 mobile), writes mostly through
the API, with `reports` inserted directly by both clients and mobile deleting athletes directly.

### Phase 61: Web Portal Rework — ✅ COMPLETE (5/5 plans) 2026-08-11

**Outcome:** the coach portal stopped contradicting itself. The numbers and the charts now describe
the same cycles, video has a front door, and two sessions from one morning are tellable apart.

| Plan | What landed |
|---|---|
| 61-01 | `ramp_up` removed from the pipeline; two `ratings.py` bands re-anchored from measured data |
| 61-02 | Report card: 4 per-cycle charts, Data Quality → dropout strip, start provenance, prev/next |
| 61-03 | `/app/sessions/[id]/video` route; **58-04 closed** |
| 61-04 | Compare: mnemonic names, two stacked true-rate traces, alignment, per-cycle overlays |
| 61-05 | Video on Compare (toggleable); portal-wide one-name model |

⚠ **DEFERRED TODO — synced playback on Compare (unplanned, at user request).** Play both videos and
both trace playheads together, driven by the D9 alignment offset. Needs: a play/pause API on
`VideoPane` (it has only `seekRef`/`frameStepRef`), per-panel playhead markers in `CompareChart`, a
master clock, and an explicit decision on **whether the align offset should also shift video B**
(it currently shifts the trace only). Do not start this without that decision.

⚠ **CARRIED OUT:** the video chart no longer auto-follows the playhead (CONTEXT D16 withdrawn at
the 61-03 checkpoint); generated session names are derived, not persisted (persisting is a
`/process` backend change); 61-02's mobile `CycleCharts` comment fix is still uncommitted in
`swimnetics-mobile` and needs an EAS build; and **the fourth comparability break from 61-01 stands**
— stored sessions are on the old cycle scale, with no backfill.

### Phase 61 original goal
**Goal:** make the report card's numbers explainable, give video a front door, make Compare
actually comparable, close 58-04, and remove the steady/ramp split so the numbers and the graphs
describe the same cycles.
**Plans:** four, sequential — 61-02/03/04 all depend on 61-01's semantics.
- [ ] **61-01 PLAN created 2026-08-11, awaiting approval** — D5 + D15. `autonomous:false`,
  `depends_on []`, wave 1. **11 files, all backend/tests/docs — zero web or mobile.** 3 auto tasks
  + 1 `checkpoint:decision` (final band anchors). 5 ACs.
  ⚠ **D5 and D15 MUST NOT be split** — shipping D5 alone leaves two of four pillars reading
  `needs_work` on ~39% of sessions.
  ⚠ Task 1 commits `tools/rampup_impact.py` and captures the BEFORE baseline *before* any change,
  so "old → new" is measured rather than reconstructed — the grilling's measurements live in a
  session scratchpad and are not reproducible as they stand.
  ⚠ `coach.py` reads cycles from STORED `metrics_json`, so pre-change rows still carry `phase`;
  the reader must not depend on the key in either direction.
  ⚠ Boundary: `tests/test_segmenter_eval.py` passing **unchanged** is the proof that Phase 59's
  segmentation did not move. Nothing may be deleted, skipped, or weakened to make the suite green.
  ⚠ Knife-edge noted at plan time: `_band` uses `value <= thr["good"]` and `test_ratings.py:14`
  pins `cv_arm_peak_vel` at exactly `0.08`, so anchors must be rounded AWAY from fixture values.
- [x] **61-02 ✅ COMPLETE 2026-08-11** — all 7 ACs met, checkpoint approved. Build clean at every
  task boundary; **suite 274, zero Python touched**. 4 web files modified, 1 created, **2 deleted**;
  1 mobile file (comments + one display string). **Three of the user's five original asks are now
  on screen.**
  ⭐ **AC-2's vintage predicate was validated against the LIVE corpus, not assumed** — 54 legacy /
  0 new / 8 no-cycles across 62 sessions, exactly as expected while 61-01 is undeployed.
  ⚠ **VERIFICATION HONESTY: every VISUAL criterion rests on the user's approval, not on
  observations I made.** The coach portal is behind Supabase auth and signing in is out of bounds,
  so AC-1/4/5/6 were not independently checked. What WAS checked without a login: build clean,
  route 200 with no console errors, `pytest` 274, no live refs to the deleted components or to
  `warnings.length`, `dropoutWarning` 10/10 in node, and the AC-2 predicate above.
  ⚠ **AC-6's REQUIRED OBSERVATION WAS NOT OBTAINED** — whether the Simple/Advanced and m/yd toggles
  survive prev/next navigation. The checkpoint asked; the reply was "approved" without it. Recorded
  as unknown rather than guessed.
  ⚠ DEVIATIONS (5, none harmful): prettier run on `MetricGrid.js` produced **55/50 lines of
  unrelated churn** for a ~10-line change — prettier is NOT a repo convention (no config, not a
  dependency), so it was reverted and redone by hand at **8/6**; an `rm` issued from a stale `web/`
  cwd failed harmlessly; the mobile edit is comments **plus the one footnote string** D5c named, so
  the plan's "COMMENT-ONLY" boundary was mine and too narrow; AC-6's observation missing; and the
  flagged `SessionCard` addition below.
  ⚠ SCOPE ADDITION, FLAGGED TWICE AND NOT OBJECTED TO: `SessionCard.qualityIssue` now filters the
  segmentation warning as well as the kick one. Before this it put a ⚠ on essentially every card in
  the session list, since `segmentation_reliable` is hardcoded false. Touches the sessions LIST,
  not the report card.
  ⚠ Impulse and Trough left the web with `CycleTable` — intended, not to be reinstated.
  SUMMARY: 61-02-SUMMARY.md. Original scope follows.
- [ ] ~~61-02 PLAN created 2026-08-11, awaiting approval~~ — report card rework (D3, D4, D7, D12).
  `autonomous:false`, `depends_on ["61-01"]`, wave 2. **8 files** (7 web + 1 mobile comment-only).
  3 auto tasks + 1 device-free human-verify. **7 ACs.**
  ⭐ **AC-2 IS THE PLAN'S SUBTLE PART — the mean-line caption must be true for BOTH session
  vintages.** After 61-01 the mean IS the average of the plotted dots, but only for sessions
  computed by the new code; stored rows keep steady-only means. Vintage is detected from the data
  (`cycles.some(c => "phase" in c)` — 61-01 stopped emitting that key), never from dates, and never
  shown unconditionally.
  ⚠ **CARRIES CONTEXT.md's D5c, WHICH 61-01 MISSED.** 61-01's own boundary said "any web or mobile
  file needs no change", which contradicted D5c and won. `swimnetics-mobile`'s `CycleCharts.js`
  header + footnote still state means exclude cycles AND instruct future developers not to fix the
  mismatch — false since 61-01, and actively misleading. Comment-only, no EAS build.
  ⚠⚠ **THE UNCONDITIONAL-WARNING TRAP, verified twice.** `api.py:181` appends the kick warning
  unconditionally and `:193` appends a segmentation warning whenever `segmentation_reliable` is
  false — hardcoded false for every auto session. So `warnings.length > 0` flags everything and
  carries zero information; mobile's `dropoutWarning.js` documents this and the plan forbids it.
  ⚠ SMALL ADDITION FLAGGED FOR REVIEW: `SessionCard.qualityIssue` filters the kick warning but not
  the segmentation one, so it currently puts a ⚠ on essentially every card in the session list.
  Same defect class, different form; fixed here because deleting `DataQualityCard` while leaving
  its surviving sibling broken would be incoherent. Touches the sessions list, not the report card.
  ⚠ Impulse + Trough leave the web with `CycleTable` — intended, recorded, not to be reinstated.
- [x] **61-03 ✅ COMPLETE 2026-08-11** — 6 of 7 ACs met, **AC-4 WITHDRAWN**; user verified
  *"everything works"*. **⭐ 58-04 IS CLOSED** — owed since 2026-08-07 and called "homeless" in both
  the Phase 58 and Phase 60 close-outs. Build clean; suite **274**; **zero Python, zero backend** —
  `GET /video-url` + `POST /video` unchanged since Phase 47. 1 file created, 4 modified.
  ⭐ **A SECOND INSTANCE OF THE 58-04 DEFECT WAS FOUND, unplanned:** `VideoPane.attach()` also did
  `origin_s: r.video_origin_s ?? 0`, so attaching a video *through the web* forced a null origin to
  zero too. Same defect, second site.
  ⚠ **AC-4 AND CONTEXT D16 WERE WITHDRAWN MID-APPLY**, not satisfied. The user removed the
  1s/2s/5s/All presets at the checkpoint — *"redundant when they can manually adjust the window"* —
  so **the video chart no longer auto-follows the playhead**, which was mobile 60-03 parity and
  D16's whole purpose. Accepted knowingly; revisit first if playback reads badly.
  ⭐ That removal **deleted more than four buttons**: nothing supplied `viewRange` afterwards, so
  `brushIdx`, `yDomain` and `showBrush` died with it. `VelocityChart`'s diff went from a
  controlled-window apparatus to **`onClick` only (9 lines)**, the video page 187 → 147 lines, and
  the downsample returned to byte-for-byte the original — making **AC-5 true by construction**
  rather than by measurement.
  ⚠⚠ **THE FIRST CHECKPOINT SUBMISSION WAS NOT WORKING SOFTWARE — six defects across two rounds.**
  R1: the span presets were inert until the video emitted a playhead AND the brush flickered
  (one root cause — `viewRange` gated on `playheadS != null`); the entry point was a header link
  the user called hidden; view/unit did not survive prev/next. R2: unreadable y-axis ticks (an
  explicit `domain` defeats recharts' nice-tick algorithm, so raw floats got clipped by
  `width={42}`) and an over-corrected brush removal. ⚠ The *flat trace* reported alongside was
  **correct** — at playhead 0 the window sits in the pre-swim baseline.
  ⭐ **READING THE LIBRARY BEAT WORKING AROUND IT:** the brush fix initially forced updates with a
  `key` remount; `recharts/lib/cartesian/Brush.js:534` showed 3.8 supports controlled indices
  natively, and `onTimeUpdate` fires ~4 Hz so remounting would have been worse than the bug.
  ⚠ **BOUNDARY VIOLATION, flagged and accepted:** `web/app/app/annotate/[id]/page.js` is on the
  plan's DO-NOT-CHANGE list, but AC-2 requires that page to compute an end-anchored origin, which
  needs a `sessionDurationS` prop. **The plan contradicted itself**; the AC won. One prop, no logic.
  ✅ Also fixed here: 61-02's unanswered question — the toggles did NOT survive prev/next (the route
  remounts per session id), now persisted to `localStorage`.
  SUMMARY: 61-03-SUMMARY.md. Original scope follows.
- [ ] ~~61-03 PLAN created 2026-08-11, awaiting approval~~ — video route + **CLOSES 58-04**
  (D1, D2, D13, **D16**). `autonomous:false`, `depends_on ["61-02"]`, wave 3. **4 files** (3 web
  modified/created + 1 new route). 3 auto tasks + 1 human-verify. **7 ACs.** Zero Python, zero
  backend — `GET /video-url` and `POST /video` have existed since Phase 47 and mobile 60-03 already
  proved this feature needs no server change.
  ⭐ **58-04's ENTIRE DEFECT IS ONE LINE:** `VideoPane.js:27` — `useState(video?.origin_s ?? 0)`.
  Any session whose footage arrived via the mobile background upload queue (which posts the file
  with no origin) lands at **0** and is silently unsynced. Fix mirrors
  `VideoOverlayScreen.js:49-73` exactly: `stored ?? (sessionDuration − videoDuration)`.
  ⚠ **`??` NOT `||`** — a stored origin of exactly 0 is a real value; `||` would reintroduce the
  bug. Called out in the plan as the single most likely regression.
  ⚠ **VideoPane IS SHARED with the annotate page**, which inherits the fix — that is 58-04's whole
  point — so AC-7 makes annotate non-regression an explicit gate rather than an assumption.
  ⚠ **D16 WAS RECORDED LATE.** The rolling playhead window (1/2/5s/All, default 2 s) was chosen by
  the user in the discussion and never written down as a numbered decision; it survived only as a
  passing mention in CONTEXT.md's Constraints. Added at plan time so 61-03 rests on a record rather
  than an inference.
  ⚠ Phase 60's close-out flags the 2 s rolling window as **specifically unverified on a device** —
  the point of the original ask, never confirmed. **The web is its first real read**, and the
  checkpoint asks for a plain yes/no.
  ⚠ AC-5 gate mirrors 60-02's byte-identical discipline: the report card's unwindowed
  `VelocityChart` output must be proven unchanged, with the old algorithm read from
  `git show HEAD:…` rather than from memory.
  ⚠ FLAGGED ADDITION: chart-click → seek. Not one of the four decisions, and CONTEXT D1 says "no
  annotation tools" — but seek is playback, and a chart you cannot scrub is strictly less than the
  annotate page the user is trying to escape. Remove at review if unwanted.
  ⚠ Carries forward 61-02's unanswered question (do view/unit survive prev/next).
- [x] **61-04 ✅ COMPLETE 2026-08-11** — all 5 ACs met, checkpoint approved after one revision.
  Build clean; **suite 274, zero Python**. 2 files created, 3 modified, 1 deleted.
  ⭐ **AC-1 MEASURED ON THE REAL CORPUS, NOT ASSUMED:** the worst case is **19 sessions for one
  athlete on one day** — exactly the user's complaint — and all 19 labels come out distinct;
  62/62 distinct globally; deterministic across calls.
  ⚠ **THE MNEMONIC ALONE COLLIDES 3 TIMES IN 62** (40×32 = 1280 combos; birthday paradox predicts
  ~1.4). **Uniqueness comes from the appended TIME, not the words** — widen the word lists before
  the corpus reaches thousands.
  ⚠ **AC-2 FIXED AN ABSOLUTE ERROR, NOT A VISIBLE SKEW** — 56 of 62 sessions are 90.0 Hz and 6 are
  NULL, so **none differ from each other**. The hardcoded 100 was ~11% wrong on BOTH traces
  equally. It is the last hardcoded rate on the web and CLAUDE.md's "no single axis to draw them
  on" note is superseded by stacked panels — but nothing visibly misaligned was repaired.
  ⚠ **% DELTAS REMOVED ENTIRELY at the checkpoint** (user: *"two graphs of actual value - not
  difference"*). The `A → B +13.4%` strip became 8 paired-bar cards of actual values, and
  `MetricDeltaTable`'s direction convention (`normal`/`inverse`/`off`, ported from `app.py`) went
  with it — **nothing in the portal now says whether a change is good or bad**. Deliberate.
  ⭐ **ASKED INSTEAD OF GUESSING:** "two graphs… two separate lines" was ambiguous, since the four
  per-cycle panels ALREADY drew two lines of actual values — the request could have meant they were
  broken. They were not. Guessing would have produced the wrong work.
  ⚠ **A SHIPPED SURFACE WAS BROKEN AND CAUGHT IN VERIFICATION:** extending `TrendPanel` to
  multi-series changed the REPORT CARD's tooltip to a two-line form (AC-5 violation, on a surface
  this plan must not touch). Single-series output now reproduces the original verbatim. Found by
  reading the diff, not by testing.
  ⚠ Bars scale by `max(|a|,|b|)` — `fatigue_index_pct` goes NEGATIVE (real value −73.9) when a
  swimmer speeds up, and `max(a,b)` renders that zero-width or inverted. Verified over 7 cases,
  plus 7 per-cycle merge shapes with zero throws.
  SUMMARY: 61-04-SUMMARY.md. Original scope follows.
- [ ] ~~61-04 PLAN created 2026-08-11, awaiting approval~~ — Compare redesign, **D8 + D9 + D11**
  (D10 split out). `autonomous:false`, `depends_on ["61-01"]`, wave 4. 5 files. 3 auto tasks +
  1 human-verify. 5 ACs.
  ⚠ **PHASE RESCOPED 4 → 5 PLANS.** All four Compare decisions in one plan was 4 substantial tasks
  on a page that roughly doubles — past the 2–3 guidance, and 61-03 showed that oversized UI plans
  surface defects in bulk at the checkpoint. D10 is purely additive and needs 61-04's layout first.
  ⚠⚠ **MEASURED AT PLAN TIME, AND IT DEFLATES D9's HEADLINE:** of 62 live sessions **56 are 90.0 Hz
  and 6 are NULL — none differ from each other.** So `CompareChart.js:28`'s hardcoded 100 is an
  ~11% error applied EQUALLY to both traces, not the differential skew CLAUDE.md's "two sessions
  may have two rates" note implies. Fixing it removes the last hardcoded rate on the web and is
  still right; the plan forbids writing it up as having fixed a visible misalignment.
  ⚠ D8 names are **derived at render time and NEVER written** — `sessions.name` is coach-editable
  and PATCHable, so generating into it would clobber typed names. Labels must include the TIME:
  the date alone is exactly what fails to separate same-day sessions.
  ⚠ D11 reuses 61-02's `TrendPanel` (currently module-private, to be exported) rather than growing
  a second chart primitive. The two sessions have DIFFERENT cycle counts and must NOT be padded,
  truncated or resampled — that would imply a correspondence between cycle N of two swims that
  does not exist. 8 of 62 live sessions have no cycles and must degrade to a message.
  ⚠ Deleting `MetricDeltaTable` drops the "% change from baseline" convention ported from `app.py`.
  A real loss of information — the plan requires either keeping a compact summary or saying plainly
  in the SUMMARY that deltas were dropped.
- [x] **61-05 ✅ COMPLETE 2026-08-11** — all 4 ACs met (AC-1 amended), checkpoint approved after
  one revision round of 4 items. Build clean; **suite 274, zero Python**. 5 files modified.
  ⭐ **THE PAIRING CHECK EARNED ITS PLACE:** panels order by DATE but video state is keyed to the
  FETCH SLOT, so picking a newer session on the left swaps base/new — the naive wiring would have
  shown one session's video against the other's trace. Verified across both orderings × three
  video-presence combinations: **0 mispaired**.
  ⚠ **AC-1 AMENDED, not merely met:** video is now **toggleable and OFF by default** (user: *"make
  the video togglable instead of permanently there"*), remembered per browser. The right column
  only EXISTS when video is on, so the traces reclaim full width otherwise; when on it is sticky so
  the panes stop trailing below the charts.
  ⭐ This **resolved both accepted-but-unverified costs the plan flagged** — density and width — but
  on neither's own terms: the user changed the question rather than answering it, and that was the
  better answer than the `compact` prop the plan had lined up.
  ⭐ **NAMING BECAME A PORTAL-WIDE MODEL** (user: *"the naming convention was supposed to be for
  actual session names, not just used for compare… generated name to just one name"*).
  `displayName()` = typed name **OR** mnemonic — **one name, never a concatenation** — applied to
  the sessions list, report card, recent activity and Compare. The report card no longer says "Add
  session name…" for an un-renamed session, because such a session is not nameless. Stroke tags
  added to Compare labels (`Amber Albatross · fly · 9:45 AM`). Verified on all 62 real sessions:
  typed names never decorated, none nameless, 62/62 still distinct.
  ⚠ **STILL DERIVED, NEVER WRITTEN to `sessions.name`** — the column keeps meaning "what the coach
  typed". Persisting generated names at record time is a `/process` backend change and a different
  decision; raised, not taken.
  ⚠ **SCOPE GREW PAST THE PLAN:** `files_modified` named ONE file; the naming model reached four
  more. All user-directed, none speculative, but a checkpoint turned a one-file layout plan into a
  cross-surface one.
  ⚠ Removed `formatTime` from `SessionCard.js`, orphaned by the naming change.
  SUMMARY: 61-05-SUMMARY.md. Original scope follows.
- [ ] ~~61-05 PLAN created 2026-08-11, awaiting approval~~ — **D10**: video on Compare.
  `autonomous:false`, `depends_on ["61-04"]`, wave 5. **1 file** (`compare/page.js`) — layout plus
  two query columns. 2 auto tasks + 1 human-verify. 4 ACs. **THE LAST PLAN IN PHASE 61.**
  ⭐ **Inherits 58-04 for free.** `VideoPane` is reused verbatim, so a NULL-origin session
  self-syncs here with no new code — provided `sessionDurationS` is passed, which is a SILENT
  no-op if forgotten.
  ⚠ **THE `?? 0` TRAP, THIRD SITE.** 61-03 found this defect twice inside `VideoPane`
  (initial state and `attach()`); passing `video_origin_s ?? 0` from this page would reintroduce it
  a third time. The verify greps for it.
  ⚠ **TWO ACCEPTED-BUT-UNVERIFIED COSTS, both raised at the checkpoint rather than defended:**
  (1) a right column takes horizontal pixels from the traces, and horizontal resolution is exactly
  what makes two velocity curves comparable — remedy is videos above/below, not beside;
  (2) two full `VideoPane`s carry frame-step, speed, sync-offset and a provenance line each, which
  is a lot of chrome — remedy is a `compact` prop, applied only if asked for.
  ⚠ DELIBERATELY EXCLUDED: **synchronized playback** (playing both videos together is not in D10
  and is the obvious follow-up), and **the D9 alignment offset does not move video B** — it shifts
  trace B only. Whether it should belongs with synced playback.
  ⚠ Data checked at plan time: all three athletes have **8–11 sessions with video**, so both-have-
  video pairs are common and mixed pairs will occur — AC-2 makes the mixed case ordinary, not an
  edge case.

### Phase 60: Mobile App Rework — ✅ COMPLETE (3/3 plans) 2026-08-11
**Outcome:** the phone stopped showing less than the laptop, and stopped showing one number wrong.
Suite **273 throughout — zero Python touched in the entire phase**; export exit 0 at every step;
1091 → 1093 modules. 12 decisions D1–D15 (D11 amended, D12–D15 added during apply), all user calls.

| Plan | What landed |
|---|---|
| 60-01 | Real sample rate (**−10.0% → +0.0%**, measured live, 4/4); four per-cycle charts; Data Quality retired to a dropout strip; `cv_isi` gate → banner |
| 60-02 | Brush bar replaces pinch; controlled window primitive; unwindowed polyline proven **byte-identical** |
| 60-03 | Video from any saved session; rolling playhead window; origin protected from silent overwrite; user-dropped START marker |

⭐ **Three things this phase got right that were not in any plan.** 60-01 found a live −10% error
nobody had asked about. 60-02's byte-identical acceptance test proved a refactor hadn't drifted,
using the old algorithm transcribed from git rather than from memory. And 60-03's best design change
came from the user asking *"why are there different screens?"* at a checkpoint — which **deleted** a
parameter, a branch and a concept rather than adding them.

⚠ **CARRIED OUT** (none blocking): the `currentTime` wobble hypothesis (unmeasured); **58-04 still
owed and still homeless**; **Phase 52-02 is better motivated than its backlog position** — most
NULL-rate rows are ~90 Hz, not ~100, correcting a generalization in the Phase 59 record; **three
unconnected notions of "when the swim starts"** (auto `baseline_end`, the annotation contract's
`dive_start_s`, and 60-03's marker) with the user's *"I don't trust auto detect baseline"* as a
Phase 53 input; and the start marker being in-memory only.

⚠ **VERIFICATION HONESTY:** 60-01 and 60-03 were both approved without itemized on-device
observations. Device-independent evidence is strong throughout; the visual/interactive ACs rest on
those approvals. **Specifically unconfirmed: whether the 2 s rolling window reads well during
playback**, which is the point of the user's original ask.

**Original goal:** Close the gap where the coach's poolside device shows strictly less than the
laptop, and correct the one number on it that is silently wrong. PROJECT.md lists "Per-cycle charts
in iOS app" under Nice to Have marked *"✓ shipped on web portal instead"* — that substitution was
the gap.
**Blocking on entry:** commit Phase 58-01 in `swimnetics-mobile` first (done — `4a03f2c`).
**Plans:** three, sequential — they share `ReportCardScreen.js`, and this repo has documented
history of concurrent-edit contention between PAUL environments (57-03 / 58-02). False parallelism
buys nothing here: one developer, one repo, one paid EAS build.
- [x] **60-01 ✅ COMPLETE 2026-08-11** — all 5 ACs met, checkpoint approved. Suite **273**
  (unchanged, zero `.py` touched); export exit 0; **1091 → 1092 modules (+1)**.
  ⭐ **AC-1 WAS MEASURED AGAINST THE LIVE DB, NOT SIMULATED** — the mobile time axis was **−10.0%**
  on every recorded-rate session and is now **+0.0%**, exact agreement with each session's own
  `lap_time_s`, 4 for 4. NULL-rate rows render byte-identically.
  ⚠ **FINDING THAT OUTLIVES THE PLAN: most NULL-rate rows are ~90 Hz, not ~100.** Two of three
  sampled NULL sessions remain −10.0% off — correctly, since backfilling is forbidden by D1 and by
  CLAUDE.md (writing 100 would erase "genuinely 100" vs "unknown"). **This corrects a generalization
  in the Phase 59 record**, which noted the June NULL sessions "genuinely ran at ~100 Hz": true of
  the two examined, not true in general. **Phase 52-02 is worth more than its backlog position.**
  SHIPPED: `fsHz` at 3 division sites, with Time-to-Distance fixed transitively — and with it the
  *second, compounding* error where `baseline_end_s` in true seconds was compared against the fake
  array, so the baseline index was wrong rather than merely scaled; NEW `CycleCharts.js` (4
  hand-rolled SVG panels, all cycles plotted per D8, with the two expected mismatches documented
  in the component header as **not to be fixed**); `DataQualityCard` DELETED from **both** screens;
  NEW `dropoutWarning.js` firing only above 5%, node-verified across 10 cases including the
  kick-only trap; the `cv_isi > 0.80` gate demoted from blackout to banner on both screens.
  ⚠ DEVIATIONS (3, none blocking): a 6th file (`src/lib/dropoutWarning.js`) — two screens needed one
  threshold and the plan's own verify wanted a node-runnable predicate; **Fatigue kept as a scalar**,
  because `fatigue_index_pct` is a q1-vs-q4 comparison with no per-cycle series and charting it is
  impossible while dropping it would have silently removed a metric; and **this roadmap's 58-01
  module baseline (1075→1076) was STALE** — real baseline 1091, the gap being `expo-media-library`
  added at 58-01's checkpoint after that number was written down (re-measured by stash → export →
  restore, so the +1 delta is real, not inferred).
  ⚠ VERIFICATION HONESTY: the approval covered **item 7** affirmatively (58-01's auto-stop on real
  hardware — see Phase 58). Items 1–6 were approved without itemized on-device observations; AC-1/3/5
  rest on device-independent evidence, AC-2/4 are visual. Recorded because it is the same pattern
  58-01 itself was flagged for.
  ⚠ Mobile changes **UNCOMMITTED**; HEAD `4a03f2c`. SUMMARY: 60-01-SUMMARY.md. Original scope follows.
- [ ] ~~60-01 PLAN created 2026-08-10, awaiting approval~~ — report card correctness + per-cycle
  analytics (D1, D2, D3, D8, D9, D10, D1c). `autonomous:false`, `depends_on []`, wave 1.
  5 files: `ReportCardScreen.js`, `RecordScreen.js`, NEW `CycleCharts.js`, delete
  `DataQualityCard.js`, `CLAUDE.md`. 3 auto tasks + 2 checkpoints (a `human-action` for the 58-01
  commit, and a device human-verify). 5 ACs. The device checkpoint doubles as the **first hardware
  exposure of 58-01's auto-stop**, outstanding since 2026-08-05.
- [x] **60-02 ✅ COMPLETE 2026-08-11** — all 5 ACs met, checkpoint approved. Suite **273**
  (unchanged, zero `.py`); export exit 0; **1092 → 1093 modules (+1)**. **No `myswimcoach` file
  changed at all**, not even a doc.
  ⭐ **AC-2: THE REFACTOR PROVABLY DID NOT DRIFT** — the old algorithm was transcribed **verbatim
  from `git show HEAD:VelocityChart.js`**, not from memory, and run head-to-head on 4 real traces:
  the unwindowed polyline is **BYTE-IDENTICAL**.
  ⚠ **That required a design choice worth keeping:** `resampleWindow` strides with `Math.ceil`, the
  legacy unwindowed path with `Math.floor(n/400)` — on a 4216-sample trace those differ (384 vs 422
  points). The two paths are **deliberately kept separate**, with a code comment saying so.
  Unifying them would silently change the default chart everyone looks at — a legitimate future
  change needing its own before/after, NOT a tidy-up.
  ⚠ **PLAN FIGURE CORRECTED: the "~17 points" came from a hypothetical 47 s trace.** Real sessions
  are 22–27 s, so the old path kept **30–37**; the new one keeps **181**. Still 5–6×, but the plan
  overstated the starting point.
  SHIPPED: NEW `src/lib/chartWindow.js` (pure; node-verified across 7 clamp cases + 11 degenerate
  inputs with no throws and no NaN — it runs 20×/s on the video page, where one NaN blanks the
  trace mid-playback); `clampWindow` takes an **`anchor`** (`span`/`start`/`end`) because panning
  and the two handle drags hold different edges; pinch, pan-when-zoomed and the **dead** double-tap
  reset all removed; brush strip on a **second, dedicated PanResponder** (the old bugs came from
  one responder multiplexing three jobs), handles drawn at 8 pt but hit-tested at 20 pt; plus the
  three perf fixes 60-03 depends on — memoized full-trace downsample (the component had **no
  `useMemo` anywhere**), in-window resampling, and a y-scale pinned to the full trace when windowed
  (otherwise it rescales 20×/s and the trace jitters).
  D12 applied: `brush` on **both** results surfaces. `VideoOverlayScreen.js` untouched — its empty
  `git diff` is AC-5's regression guard.
  ⚠ DEVIATION: Tasks 2 and 3's component edits landed in **one** file write, not two. The plan split
  them per Phase 59's D14; the substance survived (the byte-identical test the split existed to
  enable ran independently and passed, and the brush is purely additive behind a prop defaulting to
  `false`), but the structure deviated. SUMMARY: 60-02-SUMMARY.md. Original scope follows.
- [ ] ~~60-02 PLAN created 2026-08-11, awaiting approval~~ — **windowed chart primitive + brush
  bar** (D6, D7). `autonomous:false`, `depends_on ["60-01"]`, wave 2. **4 files**: NEW
  `src/lib/chartWindow.js`, `VelocityChart.js`, `ReportCardScreen.js`, `RecordScreen.js`. 3 auto
  tasks + 1 device human-verify. 5 ACs.
  ⚠ **NEW DECISION D12 — the brush ships on BOTH results surfaces**, not only the report card the
  user named. `RecordScreen.js:929` renders the same component and would otherwise silently lose
  pinch and get nothing back; this applies 60-01's D10 principle that the two screens must not
  disagree about the same session. One prop per screen. **Flag at review if unwanted.**
  ⚠ `VideoOverlayScreen.js:170` deliberately does NOT get the brush — it receives a *controlled,
  playhead-driven* window in 60-03, and a hand-draggable brush would fight it. Its unchanged
  rendering doubles as 60-02's regression guard (AC-5).
  STRUCTURE follows **Phase 59's D14 lesson**: Task 2 is behaviour-preserving except pinch removal,
  with acceptance = a **byte-identical unwindowed polyline**; Task 3 adds the brush. A refactor
  sharing a diff with a new feature makes unexpected movement unattributable, and this codebase has
  documented silent drift (51/52/57/59).
  ⚠ Removing pinch also deletes a **DEAD** double-tap reset: `onStartShouldSetPanResponder: () =>
  false` (`:46`) means a plain tap never grants the responder, so the reset at `:60-65` only ever
  fired if the user dragged twice. A bug removed, not a feature lost. Original scope follows.
- [ ] ~~60-02 (scoped, not written)~~ — **windowed chart primitive + brush bar** (D6, D7). Files: NEW
  `src/lib/chartWindow.js` (pure, runnable in node — there is no jest on mobile, so 58-01's
  extract-and-run-in-node precedent is the verification path), `VelocityChart.js`, one prop at the
  report-card call site. `depends_on ["60-01"]`, wave 2. Also carries the three performance details
  that decide whether the rolling window feels smooth, all measured at discussion time and all
  invisible until run at 20 Hz on a device: a 2 s window of a 47 s trace currently keeps only
  ~17 points (downsampling happens over the whole trace first, `VelocityChart.js:87-91`); the
  y-axis would rescale 20×/second (`:107-108` takes min/max from the visible slice); and the
  component has **no `useMemo` anywhere**. ⚠ Removing pinch also removes a latent bug —
  `onStartShouldSetPanResponder: () => false` (`:46`) means a plain tap never grants the responder,
  so the double-tap-to-reset at `:60-65` only fires if the user *drags* twice.
- [x] **60-03 ✅ COMPLETE 2026-08-11** — all **8** ACs met (5 planned + 3 from a mid-apply scope
  amendment), decision checkpoint resolved, human-verify approved. Suite **273**; export exit 0;
  1093 modules. 4 files, `RecordScreen.js` untouched.
  ⭐ **THE BEST DESIGN CHANGE CAME FROM A USER QUESTION AT THE CHECKPOINT, NOT FROM THE PLAN.**
  Asked *"why are there different screens… I want a single destination — would that make it
  simpler?"*, which exposed a misconception (there was only ever ONE screen, `VideoOverlayScreen`,
  with two *doors*) and a real simplification (the origin rule need not differ per door). One
  sentence — **"use the stored origin if there is one, otherwise compute it and save it"** — covers
  every case and **DELETED** the planned `allowOriginWrite` param, its branch, and the "which screen
  am I" concept. `RecordScreen` needed no edit at all. **D11 amended** from "the read path never
  auto-writes" to **"never overwrite an existing origin"** — what it was actually protecting; the
  original wording over-reached into a case nobody had examined.
  ⚠ **THE BUG THE PLAN PREDICTED WAS REAL:** the nudge-save was gated on `originSavedOnceRef`, a ref
  set by the auto-post, so skipping the auto-post would have silently swallowed the user's first
  nudge — losing the one repair mechanism D11 exists to preserve. Fixed with a dedicated mount ref.
  SHIPPED: `▶ Video + Velocity` on the report card (signed URL fetched on tap, 404/503/network each
  handled, no navigation on failure) — **no backend work, the endpoint has existed since Phase 47
  with no mobile caller**; a centred rolling playhead window (1/2/5 s/All, default 2 s, no new
  timer); origin precedence + write guard; and a debug line that names which origin is in effect.
  ⚠ **SCOPE AMENDED MID-APPLY at user request** (*"attach one more feature in this phase"*), folded
  in rather than split into a 60-04 so one paid build verifies everything: **D13** a user-dropped
  START marker for Time-to-Distance (*"I don't trust auto detect baseline"* — per session,
  in-memory only, and **no maths changed** since `computeTimeToX` already took the start as a
  parameter); **D14** labelled the two Video Overlay control rows, which were unlabelled
  near-identical pills with the one caption sitting below the second row; **D15** the lattice fix.
  ⚠ **"DANCING" TRACE: ONE CAUSE MEASURED AND FIXED, ONE LEFT OPEN AND NAMED.** `resampleWindow`
  anchored its stride to the *window's* start index, so on a rolling window the lattice slid with
  the window and consecutive frames drew different neighbouring samples — measured at span 5 s as
  **two alternating lattice phases**, now **one, stable**. **But 1 s and 2 s were ALREADY stable**,
  so any remaining jitter at the default 2 s has a different cause. Hypothesis (unverified without
  a device): `player.currentTime` wobbling between polls, moving a playhead-centred window ±2 px at
  20 Hz. Diagnostic recorded; NOT speculatively patched.
  ⚠ VERIFICATION HONESTY: approved with a bare "approved". Device-independent evidence is strong
  (node lattice simulation, pytest, export, regression suites); AC-4/6/7 are visual and rest on the
  approval. **Specifically unconfirmed: whether the 2 s rolling window reads well during playback**
  — the point of the original ask. SUMMARY: 60-03-SUMMARY.md. Original scope follows.
- [ ] ~~60-03 PLAN created 2026-08-11, awaiting approval~~ — **video from any session + rolling
  playhead window** (D4, D5, D11). `autonomous:false`, `depends_on ["60-01","60-02"]`, wave 3.
  **2 files**: `ReportCardScreen.js`, `VideoOverlayScreen.js`. 3 auto tasks + **a decision
  checkpoint** + 1 device human-verify. 5 ACs. **The last plan of Phase 60.**
  NO BACKEND WORK — `GET /sessions/{id}/video-url` returns `{url, origin_s}` in one call, signed
  3600 s, 404 when no video; it has existed since Phase 47 and has **never had a mobile caller**.
  ⚠ **THIS IS THE PLAN WITH A DATA-LOSS HAZARD RATHER THAN A DISPLAY BUG.**
  `VideoOverlayScreen.js:120-125` auto-posts a recomputed `video_origin_s` as soon as it knows one;
  reached from a second entry point that silently overwrites an origin the user had nudged into
  place — the same silent-plausible-corruption shape as Phases 51/52/57/58.
  ⚠ **SUBTLE BUG FOUND AT PLAN TIME:** the debounced nudge-save at `:128-134` is guarded by
  `if (!originSavedOnceRef.current) return`, and that ref is set by the auto-post — which the read
  path skips. A naive write guard therefore swallows the first nudge on the read path.
  ⚠ **NEW: D11a, a case D11 never distinguished** — decision checkpoint in the plan. When the read
  path finds **no** stored origin, may it save the one it computes? A session whose video came from
  the background upload queue has `video_origin_s = null` — precisely **58-04's gap**, never built
  and now carried out of Phase 58 with no home — and writing there cannot overwrite anything.
  `strict` (D11 literally) vs `null-only` (**recommended**: honours D11's intent of protecting a
  *good* value, rather than its literal wording). Original scope follows.
- [ ] ~~60-03 (scoped, not written)~~ — **video from any session + rolling window** (D4, D5, D11).
  Files: `ReportCardScreen.js`, `VideoOverlayScreen.js`. `depends_on ["60-01","60-02"]`, wave 3 —
  it needs the controlled `window` prop from 60-02 **and** D1 from 60-01, because the
  origin-recompute fallback reads `deviceDuration` off the time array and would inherit the ~11.7%
  error. ⚠ The expensive half of D5 is already shipped: `VideoOverlayScreen.js:65-85` already polls
  `player.currentTime` at 20 Hz, with a comment explaining why polling beats `expo-video`'s
  `timeUpdate` event (the event only fires during playback, so scrubbing while paused would freeze
  the marker) — that reasoning transfers to the window unchanged. ⚠ D11's write guard is the real
  risk here: the screen currently auto-posts a recomputed origin at `:120-125`, which on a read path
  would silently overwrite a stored value already carrying a manual nudge.

### Phase 58: Video Ground Truth (solo capture + annotate-from-video) — ✅ CLOSED 2026-08-11
**CLOSED at user request** (*"update 58 to say that everything worked as intended - close the
phase"*). **4 of 5 plans shipped and verified: 58-01, 58-02, 58-03, 58-05.**

⭐ **WHAT CLOSES IT: 58-01's auto-stop is now DEVICE-VERIFIED.** It was the phase's one outstanding
risk — approved on assumption 2026-08-07 (*"assume 58-01 is working. approve it."*), never fired
against real hardware, and with a too-early stop being the failure mode that destroys data rather
than merely annoying. It rode the Phase 60-01 build and worked as intended. This also retires the
`reset()` latent-bug concern recorded against 58-01 (a surviving deadline passing the double-stop
guard and firing a real STOP into an abandoned session).

⚠ **58-04 (`VideoPane` end-anchor) WAS NEVER BUILT — carried out of the phase, not completed.** No
plan was ever written for it, so it cannot be described as "working as intended"; it does not
exist. **The live consequence is unchanged:** `VideoOverlayScreen` on the phone remains the ONLY
thing in the entire system that writes `video_origin_s`, so a record-with-video session never opened
there arrives on the web at `origin_s = 0`, silently unsynced. It is WEB work (`VideoPane` + the
annotate page) and therefore **outside Phase 60's scope entirely** — Phase 60-03 adds a second
*mobile* door into Video Overlay, which eases the manual workaround but does not replace 58-04.
**Needs a home in a future phase.**

⚠ **R1 WAS NEVER ANSWERED — unanswered across five consecutive checkpoints** (57-02, 58-01, 58-02,
58-03, and this close-out). Whether ~40 arm-entry marks are placeable from tripod footage gates
Phase 53 Track A4. **Partial evidence says yes:** the 08-07 batch was labeled with 58-02's video
tooling and is measurably the best-covered in the corpus (~90% vs ~50% for some 08-05 sessions).
Closing the phase does not close R1.

**Original goal:** Make tomorrow's tripod + video test produce usable ground truth, and make the footage
actually usable for annotation once it exists. Four asks, of which two turned out to be already
built: (1) solo capture — the swimmer must not have to swim back to stop the recording; (2) video
sync that lands without a per-session detour and without depending on a promptly delivered STOP;
(3) annotation driven by the footage rather than by the chart; (4) whether a tripod angle is legible
at all, which is the phase's one genuine unknown and is answerable with no encoder, no BLE and no
app — film one 25 from three positions and try to mark entries off it.
**Blocking on entry:** 57-02's human-verify checkpoint is still open and 57-02 is already deployed.
Phase 58 edits the same annotate page; starting first makes any checkpoint defect indistinguishable
from a 58 regression.
**Plans:**
- [x] 58-01 ✅ **COMPLETE 2026-08-07** (applied 2026-08-05). ⚠⚠ **CHECKPOINT APPROVED ON ASSUMPTION,
  NOT ON DEVICE EVIDENCE** — user: *"assume 58-01 is working. approve it."* No on-device
  verification was reported, so every AC rests on static evidence (`npx expo export` exit 0,
  1075→1076 modules; `clampAutoStopS` extracted and run in node; 5/5 cleanup parity by grep) plus
  that approval. **Auto-stop has never fired against real hardware**, and a too-early stop is the
  one failure mode here that destroys data rather than annoying.
  ⚠ **R1 IS NOW UNANSWERED ACROSS THREE CONSECUTIVE CHECKPOINTS** (57-02, 58-02, 58-01) — this
  checkpoint doubled as the tripod legibility test and it was not reported. It gates Phase 53 Track
  A4 and 16-06.
  ⚠ DEVIATION, and a real latent bug: the plan named 4 cleanup sites; there are **5**. `reset()`
  (`RecordScreen.js:626`) was missed and is the worst one — it sets `isStoppingRef.current = false`,
  so a surviving deadline would pass the double-stop guard and fire a real STOP + retrieval into an
  abandoned session. The plan's RULE was right, its COUNT was wrong.
  ⚠ SCOPE ADDED at the checkpoint, user-authorized, crossing 58-01's own "DO NOT CHANGE
  VideoOverlayScreen.js" boundary: **video was viewable in exactly one place, once** — VideoOverlay
  is reachable only from the just-recorded results state, hard-gates on a LOCAL `videoUri`, nothing
  on mobile calls `/video-url`, and `expo-media-library` was not a dependency, so navigating away
  made footage unviewable on the phone forever. Fixed with the library dep + a write-only save, plus
  `aspectRatio: 3/4` → `flex: 1` so portrait footage stops burying the chart. `Info.plist` edited
  DIRECTLY — expo-doctor confirms app.json `plugins` are inert in bare workflow. 7 files, not 3.
  ⚠ MOBILE REPO ONLY, separate user-owned git — NOT in the myswimcoach push, still uncommitted.
  SUMMARY: 58-01-SUMMARY.md. Original scope follows.
- [ ] ~~58-01: iOS auto-stop — PLAN created 2026-08-05, awaiting approval~~. MOBILE REPO ONLY (3 files:
  new `src/lib/autoStopPrefs.js`, `RecordingConfigScreen.js`, `RecordScreen.js`); 3 tasks + 1
  human-verify checkpoint; autonomous:false, depends_on []. Default **20 s**, editable, 0 = disabled,
  with a live countdown. Armed at the two points where the elapsed timer already starts — immediately
  after `writeCmd('START')` resolves, which is the blare in both paths, so the countdown and the
  deadline share one clock; arming earlier (in `beginPlain`/`startVideoRecording`) would include the
  race sequence's deliberately random hold. Fires the right stop per path via a new `stopPlainRef`
  mirroring the existing `stopVideoRef`, because both stop callbacks are defined after their start
  functions. Cleared at all four sites that already clear `elapsedTimerRef`. SECOND-ORDER BENEFIT:
  it repairs the end-anchor's weakest premise — `deviceDuration − videoDuration` assumes camera and
  device stop together, and today a failed STOP is caught non-fatal while the device keeps recording,
  silently inflating the auto-posted origin; one timer firing both stops is exactly that guarantee.
  Setting lives on RecordingConfigScreen next to the race-start toggle (the only other recording pref)
  and rides the existing nav-params channel to RecordScreen. Checkpoint doubles as the CONTEXT-R1
  legibility test, which needs no encoder, no BLE and no app.
- [x] 58-02 ✅ **COMPLETE 2026-08-07** — all 6 ACs pass, checkpoint approved. Suite 236 → **237**,
  web build exit 0, zero console errors. Shipped: Breakout retired from the contract
  (`LEGACY_PHASE_KEYS` tolerated on read, stripped on write) with **no metric moved on any
  session** — `annotation_to_overrides` only ever read dive/stroke/finish, and a new test pins it;
  video height-capped and the whole editor made viewport-responsive (measured at two viewports:
  ~671 px used of 720, ~934 of 1000); frame-step + 0.25×/0.5×/1× playback; mark-at-playhead on `M`
  sharing ONE swim-window guard with chart clicks; arrows modal on selection with `Escape` as the
  exit. ⚠ **LESSON WORTH KEEPING: `npm run build` exited 0 on a file the dev server could not
  parse** — a `//` comment between `return (` and the JSX, reported by SWC at the closing brace
  ~90 lines away. Browser load caught it; the build did not. Web verification is a clean browser
  load, not a clean build. ⚠ **R1 STILL UNANSWERED for the second consecutive plan** (57-02 also
  could not record it) — whether ~40 arm-entry marks are placeable from footage gates Phase 53
  Track A4 and 16-06. ⚠ The `VideoPane` end-anchor was REMOVED from this plan's scope (the D8
  option the user declined bundled it) → future 58 plan; until then every record-with-video session
  still needs one Video Overlay tap on the phone. SUMMARY: 58-02-SUMMARY.md. Original scope follows.
  3 auto tasks + 1 human-verify checkpoint; `autonomous:false`, `depends_on []`.
  6 files: `annotations.py`, `tests/test_annotations.py`, `VideoPane.js`, `AnnotationChart.js`,
  `AnnotationEditor.js`, `annotate/[id]/page.js`. Suite 236 → **237**.
  Mark-at-playhead on the annotate page (scrub the video to an arm entry, keybinding drops a mark at
  `playheadS` — both halves already existed in the page, the wiring did not). Deliberately NOT
  bundled with 58-01: different repo, different deploy path (Vercel push vs. a build on the phone),
  and it is needed when annotating, not when recording. ~~Gated on 57-02's human-verify
  checkpoint~~ — **gate LIFTED 2026-08-05, that checkpoint was approved.**
  ⚠ **The `VideoPane` end-anchor moved OUT to a future 58-03** — the option the user declined at D8
  was precisely the one bundling it. Until 58-03 lands, every record-with-video session must still be
  opened once in Video Overlay on the phone or it arrives at `origin_s = 0`, silently unsynced.
  ⚠ **DISTINGUISHING PROPERTY vs 57-01: nothing recomputes.** `annotation_to_overrides` only ever
  read dive/stroke/finish, so removing Breakout cannot move a metric — no re-baselined assertion, no
  comparability break, no `CLAUDE.md` note owed. If a metric moves during apply, stop and report.
  **SCOPE AMENDED 2026-08-07** (`/paul:discuss`, AskUserQuestion ×7 — see CONTEXT.md "Amendment"),
  after the first real attempt to annotate with video open. Two additions, both web-only:
    • **D6 — the video is unbounded and pushes the chart off-screen.** Verified structural, not a
      style nit: `page.js:337` is `max-w-5xl` split `[1fr_300px]` → a ~700 px chart column, and
      `VideoPane.js:143` renders the `<video>` `w-full` with **no height constraint**, so 16:9
      footage is ~394 px tall and **portrait 9:16 is ~1244 px** (portrait is the expected case —
      58-01 was directed to "assume portrait"), above a fixed 340 px chart. FIX: cap the video at
      ~35 vh with `object-contain` and widen the page to `max-w-7xl`. Side-by-side, sidebar-video and
      a drag-resizable panel were all offered and declined — at ~40 marks per freestyle 25 the
      chart's horizontal pixels ARE the precision budget, so halving its width to seat the video
      beside it would roughly double the error the video exists to reduce.
    • **D7 — Breakout removed from the phase model, SUPERSEDING Phase 57 D5** for that marker (D5
      still holds for UW kick). Small verified surface: `annotations.py:41` PHASE_KEYS,
      `AnnotationChart.js:38` PHASE_META, 3 test assertions, 2 SQL comments — **`api.py` never names
      it and `phases` is free-form JSONB, so NO SQL patch**. Removed from the contract rather than
      hidden. The ONE hazard is `validate_annotation:238-240` rejecting unknown phase keys, so
      already-stored values are **stripped silently on read** (permissive read, strict write;
      accepted cost = that time is lost on the next save). User's framing: "what used to be breakout
      is absorbed into dolphin kick or pulldown for respective strokes" — the UW kick / Pulldown band
      now runs to `stroke_start_s`, covering kick AND breakout, and the UI must say so. **No metric
      moves:** `annotation_to_overrides` only ever read dive/stroke/finish, `stroke_start_s` keeps its
      meaning, and "the first stroke cycle contains breakout" is **documentation only** — flagging the
      breakout cycle in the export, and excluding the first cycle from cycle averages, were both
      offered and declined (the latter would have shifted `mean_dps_m`/`cv_isi`/`mean_coast_fraction`
      on every session, paying the 57-01 comparability cost a second time). So unlike 57-01 this
      amendment recomputes nothing.
    • **D8 — frame-step (~1/30 s) + 0.25×/0.5×/1× speed ship WITH mark-at-playhead, not after.** The
      native HTML5 player has no frame step, so scrubbing lands within ~±0.3 s; mark-at-playhead built
      on that would be *coarser than clicking the chart* — shipping the feature while defeating it.
      ⚠ `page.js:230` already binds ←/→ to nudging the selected mark; the collision needs an explicit
      rule at plan time.
    • **DEPLOY ORDER — CORRECTED 2026-08-07: EITHER ORDER IS SAFE.** `LEGACY_PHASE_KEYS` (D7b) is
      exactly what removes the constraint — a new backend tolerates `breakout_start_s` from a stale
      page, so no 422 is possible. Superseded text follows; it predates the tolerance.
      `page.js:14-18` `normalizePhases` already filters to PHASE_KEYS, so dropping the PHASE_META
      entry stops the client sending the key for free; backend-first would 422 a stale open tab.
    • ⚠ CONTENTION: 57-03 (queue + prev/next) and this plan both edit
      `web/app/app/annotate/[id]/page.js`. Do not apply them concurrently from two PAUL environments.

- [x] 58-03 ✅ **COMPLETE 2026-08-07** — all 3 ACs pass, checkpoint approved. ONE file, no backend
  deploy; suite still 237 (proving no backend file was touched); build exit 0; zero console errors.
  Shipped: the web stroke gate removed (every stroke now renders the toggle, pillar cards,
  Time-to-Distance, per-cycle breakdown and Coach Chat); the mount-only fetch extracted into
  `load()` and also fired on `pageshow`/`persisted` + window `focus`, which is the bfcache case
  `router.refresh()` cannot reach; and `data_quality.recomputed_from_annotation` — set by api.py:899
  since Phase 47 and rendered by nothing — finally surfaced as a provenance marker.
  ⚠ **THE PLAN'S VERIFICATION REQUIREMENT CAME BACK NEGATIVE.** The "Provisional" banner fires for
  **no stroke** (measured: breaststroke/freestyle/backstroke/butterfly all `any_provisional=False`).
  `ratings.py:229` always falls back to the breaststroke table so `thr_table` is never None, making
  `provisional` (:184) stroke-independent. 54-01 dropped the `seg_reliable` condition and this was
  the collateral — unnoticed because the web gate was believed not to exist, so nobody looked at
  what the web would show once it lifted. **Live consequence:** freestyle bands/scores/verdicts now
  display with nothing on screen saying they are breaststroke-derived and unvalidated, over
  segmentation 16-04 measured at 3/8 within ±5 SPM. Shown to the user at the checkpoint and
  **approved** — accepted and recorded, not an oversight. Phase 53 owns whether those bands should
  exist. ⚠ AUTO-FIX: `load({resetEditable})` — a plain refetch on focus would have silently
  replaced notes typed before an alt-tab. ⚠ Whether the original staleness was ever real is STILL
  UNKNOWN; the refetch hardens against an unconfirmed cause. SUMMARY: 58-03-SUMMARY.md.
  Original scope follows.
- [ ] ~~58-03 PLAN created 2026-08-07, awaiting approval~~ — report-card visibility.
  `autonomous:false`, `depends_on []`, **ONE file** (`web/app/app/sessions/[id]/page.js`), no
  backend deploy. 2 tasks + 1 human-verify.
  ⚠ **SCOPE REVISED the same day, before apply.** The plan originally opened with a diagnosis task
  for the user's report that saved annotations were not reflected on the report card. The user then
  observed them updating correctly. Since **58-02 touched nothing on the report-card path** (its six
  files were annotations.py, tests, VideoPane, AnnotationChart, AnnotationEditor and the *annotate*
  page), that improvement CANNOT be attributed to a code change — leaving two readings: the bug is
  cache-dependent and between appearances, or what looked stale was `initial_phase` carried over by
  design (api.py:905). User chose **confirm-and-harden** over a diagnosis campaign: one Back-button
  observation (recorded, non-blocking), then a `pageshow`/`focus` refetch that removes the class
  regardless. Dropping the diagnosis also dropped the `api.py` and annotate-page edits, which is
  what removed the file contention and the dependency on 58-02.
  ⚠ **CORRECTS A FALSE FINDING IN THE PHASE 54 RECORD.** 54-01's verified surface says "Web has NO
  stroke gate (already unrestricted); the stroke gate is ratings.py:176 + mobile
  ReportCardScreen.js:192 only." **False** — `web/app/app/sessions/[id]/page.js:99` has carried
  `isAnalyticsReady = !strokeType || strokeType === "breaststroke"` since Phase 23, gating five
  surfaces (view toggle, PillarCards/MetricGrid, TimeToX, per-cycle breakdown, CoachChat). The
  mobile half shipped in the Phase-55 build; the web half was never touched because the audit said
  there was nothing to touch. Both copies use the SAME identifier, so a grep would have found it —
  the miss was in the reading, not the search.
  T1 = the one-line gate removal (54-01's mobile pattern: restorable, dead branch kept) + **verify
  the "Provisional" banner still fires for freestyle** — 54-01 dropped `(not seg_reliable)` from
  that flag in ratings.py, so it is genuinely unclear whether `PillarCards.js:141` still renders
  the only thing telling a coach those bands are breaststroke-derived. Check, do not assume, and do
  NOT silently substitute a replacement caption if it is gone (that is Phase 53's question).
  T2 = extract the mount-only fetch (`:33-59`) into a `load()` callback and also call it on
  `pageshow`/`persisted` and window `focus`. **The bfcache case is the one `router.refresh()` cannot
  reach** — on a bfcache restore the component never re-runs, so nothing React-side fires at all.
  Plus surface `data_quality.recomputed_from_annotation` (set by api.py:899, rendered by nothing) —
  worth doing on its own merits: without it the coach cannot tell "the annotation did nothing" from
  "it worked and the numbers barely moved", the exact ambiguity that produced the report.
  ORDER IS THE POINT: you cannot verify an annotation reached a **freestyle** report card while the
  freestyle report card renders "coming soon" instead of any metric.

- [ ] 58-04 (owed, not yet written): **`VideoPane` end-anchor** — compute the origin client-side when
  none is stored (the pane has the video element's `duration`; the page has `duration_s` from
  `GET /annotations`), retiring the per-session Video Overlay tap that is currently the ONLY thing
  posting `video_origin_s`. Split out of 58-02 because the D8 option the user declined bundled it.
  **Until this lands, every record-with-video session must be opened once in Video Overlay on the
  phone or it arrives on the web at `origin_s = 0`, silently unsynced.**
- [x] 58-05 ✅ **COMPLETE 2026-08-07** — all 5 ACs pass, checkpoint approved. 2 files, suite still
  237, build exit 0, zero console errors. Cards now carry an auto-generated title
  (`"Freestyle · 8:24 PM"`, display-only), the athlete name, a weekday-or-date, and prominent
  **✎ Annotated** / 🎥 Video / ⚠ Quality chips; the list revalidates on `pageshow`/`focus` so the
  Annotated chip appears without a manual reload.
  ⭐ **The kick trap was VERIFIED, not assumed** — the shipped `qualityIssue` was extracted and run:
  kick-only → `null`, kick+real → the real warning, 6.2% dropout → flagged, 3.0% → null, thresholds
  matching `DataQualityCard`. The ⚠ will not be universal. 7-day boundary exact (6.9 d → `"Sun"`,
  7.1 d → `"08-01-26"`); null/unknown stroke → `"Session · …"`, no crash.
  ⚠ **RECOMMENDATION: DROP 57-03's SEPARATE QUEUE PAGE.** It existed because "a timestamp-only list
  will be unusable"; that constraint is gone. The sessions list already IS a queue — newest-first,
  filterable by stroke + athlete, shows annotated state, revalidates. A second page would duplicate
  it and need syncing forever. What genuinely remains: **prev/next on the annotate page** (the real
  throughput win, still unaddressed) and a **"Not annotated" filter chip** (~10 lines; the annotated
  Set is already in that component's state).
  ⚠ Checkpoint approved without itemised answers to the two questions the plan asked it to report
  (are the 19 distinguishable in practice; is ⚠ informative on real data). SUMMARY: 58-05-SUMMARY.md.
  Original scope follows.
- [ ] ~~58-05 PLAN created 2026-08-07, awaiting approval~~ — session-card legibility. Web only,
  **2 files** (`app/app/sessions/page.js`, `components/portal/SessionCard.js`), no backend, no
  schema, no new dep. 2 tasks + 1 human-verify; `autonomous:false`, `depends_on []`.
  TRIGGER: the card shows a bare date, so the 19-session corpus renders as nineteen rows reading
  "Aug 5, 2026". Adds an auto-generated title (`"{Stroke} · 8:24 PM"`, display-only — `sessions.name`
  is never written, so all 19 are fixed with no backfill and a typed name still wins), the athlete
  name (the card has never shown whose session it is), weekday-within-7-days else MM-DD-YY, and
  prominent **Annotated** / 🎥 video / ⚠ quality indicators.
  ⚠ **THE USER'S DATE RULE HAD TO BE ADJUSTED, with evidence:** 57-01's Supabase read established
  the 19 are **a time block on one evening (19:50–20:59), not a date** — plain day-of-week would
  render all nineteen as "Wed". Time therefore lives in the TITLE and the weekday in the meta line,
  which separates them without duplicating anything.
  ⚠ **TRAP FOUND AT PLAN TIME:** `metrics.py` sets `kick_metrics_reliable = False` on EVERY session,
  so a naive `warnings.length > 0` quality check would put ⚠ on literally every card and the
  indicator would carry zero information. The plan mirrors `DataQualityCard.js:28-31`'s deliberate
  kick-warning exclusion, and the checkpoint explicitly asks the user to report if ⚠ is universal.
  ⚠ **NO BACKEND NEEDED:** `session_annotations` is readable straight from supabase-js — patch_07
  creates a `FOR ALL` team-scoped RLS policy. "Annotated" is one extra key-only query, not an
  endpoint. Its tooltip distinguishes *metrics recomputed* from *marks saved but too few cycle
  boundaries* — conflating those is how a coach concludes an annotation "did nothing".
  Reuses 58-03's `pageshow`/`focus` revalidation so the Annotated marker appears after annotating
  without a manual reload (a marker that lags reads as "not yet done").
  ⚠ **RE-SCOPES 57-03.** That plan's own summary names "a timestamp-only list will be unusable" as
  its blocking constraint; this solves it on the list that already exists. The SUMMARY is required
  to recommend whether a separate queue page is still worth building, or whether prev/next on the
  annotate page is all that remains.
  ⚠ **PHASE 58 IS NOT COMPLETE.** 58-01/02/03 are closed and all three have SUMMARYs, so the
  mechanical "PLAN count == SUMMARY count" rule WOULD fire a phase transition — do NOT. This plan is
  owed, and **CONTEXT R1 is unanswered after three consecutive checkpoints** (57-02, 58-02, 58-01):
  nobody has yet reported whether arm entries are placeable from tripod footage, which is the one
  genuine unknown the whole phase was built around.

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
- [x] 57-02 ✅ **COMPLETE 2026-08-05** — all 7 ACs pass, checkpoint approved on the deployed portal,
  shipped `16c1d92`. Build exit 0; backend suite still 236 (proves no backend file was touched).
  ⭐ The riskiest piece was machine-verified rather than eyeballed: the shipped `deriveCycles` was
  extracted and run in node against `annotation_to_overrides` over 10 cases →
  `[2,4,1,4,0,0,0,3,1,3]` both sides, exact match, including k=2-with-finish-beyond-last-mark and
  its k=1 twin. TWO AUTO-FIXES: recharts fires `onClick` AFTER `mouseup`, so a select-click would
  have placed a stray mark on top of the one being targeted (fixed by suppressing the click on any
  mousedown that hits a mark); and dragging a mark past its neighbour left `stroke_marks_s` unsorted,
  which `validate_annotation` rejects (re-sort once per gesture on window mouseup). ⚠ R1 UNANSWERED:
  whether ~40 arm-entry marks are placeable from the trace alone was not reported at the checkpoint —
  recorded as unknown, and 57-03 must not assume it. SUMMARY: 57-02-SUMMARY.md. Original scope:
  (web only, 3 files;
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
### Phase 59: Segmenter Evaluation (ground-truth scoring harness + per-stroke dispatch)
**Goal:** Build the instrument before running the experiment. Nothing in this repo can currently
answer "is this segmenter better than that one?" — `segmentation_reliable = False` is a hardcoded
constant, not a measurement. With 23 annotated sessions now in hand, build a committed offline
scorer, make segmentation per-stroke (each stroke has different markers — breaststroke has only a
pulldown, the other three have dolphin kick, and cycle definitions differ), and correct the
freestyle stroke rate that currently ships at ~1.75× the truth.
**Not a training exercise:** 23 sessions / 236 marks / one swimmer / one pool / one device / zero
backstroke is an evaluation set, not a training set. No learned model is in scope.
**Supersedes:** the "16-06 segmenter tuning" slot referenced since Phase 16-04. ⚠ Reconciliation is
LIVING DOCS ONLY (CLAUDE.md, PROJECT.md, ROADMAP.md, STATE.md, CODEBASE-AUDIT.md); the ~25
historical PLAN/SUMMARY files that mention 16-06 are a record and must not be rewritten.
**Plans:**
**⚠ PLAN STRUCTURE REVISED 2026-08-09, mid-apply, user-directed — 3 plans became 5.** The user
asked where new segmentation techniques get brainstormed and found a REAL SCOPING GAP: no plan
covered it. The old 59-03 meant "route the best of the three already scored", not "invent better
ones" — and a 20-line peak-pick baseline beating the SHIPPING segmenter 2× on butterfly says the
space is badly under-explored. Exploration became its own research plan, which pushed the ship plan
out by one; separately, the ~1.75× cycle-pairing fix was split out because it is a cycle-DEFINITION
bug, independent of which segmenter wins, and must not wait behind an open-ended search.

- [x] 59-01 ✅ **COMPLETE 2026-08-09** — all 5 ACs pass. Suite 237 → **262**; regression passes with
  Supabase credentials unset; `git diff --stat` on metrics.py/api.py/annotations.py/ratings.py/
  vel_acc_extraction.py is EMPTY. 4 new files, no product path touched. Fixture 113 KB / 9125 samples.
  ⭐ **THE GREEDY PRIORS HELD** — optimal assignment reproduced them almost exactly (freestyle
  @±0.30 s recall 0.82 vs prior 0.82, precision 0.68 vs 0.67), so the CONTEXT figures can be cited.
  ⭐ **THE PHASE DETECTOR IS THE LARGER ERROR SOURCE, and nobody had ever measured it.** The auto
  swim window is wider than the human window on **19 of 22** sessions, median **+7.83 s**
  (`stroke_start_s` 3.9 s early, `finish_s` 3.6 s late). That is why every production-window score
  sits below its annotated-window twin. `detect_initial_phase` hunts a dive surge then a pulldown
  peak — breaststroke's shape — while running on all four strokes.
  ⭐ **THE TROUGH SEGMENTER'S 0.00 IS A MISFEED, NOT A FAILURE — this invalidates D13 as posed.** It
  keys on velocity below `0.20 × v95`, and Phase 57 made the swim window authoritative, deleting the
  dead tail those troughs lived in. Breaststroke routing CANNOT be decided from this run; re-score it
  on the UNTRIMMED trace in 59-04.
  ⭐ Wavelet finds the right events and places them badly: freestyle entries-F1 climbs 0.19 → 0.74
  across ±0.05 → ±0.30 s. **No constant lag to correct** — bias is −0.04/+0.08/+0.13 s against a
  ~0.10 s within-session spread, so 59-05 must not chase a global shift.
  ⭐ The ridge is strikingly window-sensitive: on `4219daea`, a **0.58 s** window shift collapses
  entries-F1 from 0.54 to 0.11. Pinned in the regression deliberately.
  ⚠ DEVIATIONS (2, minor): the CLI had to be made **ASCII-only** (Windows cp1252 raised
  `UnicodeEncodeError` printing the plan's own ⚠/± glyphs, *after* the fetch had succeeded — the run
  died at the report, not the work); and the regression **imports the CLI by path** rather than
  re-implementing candidate invocation, which the plan's import list did not anticipate but which is
  what stops test and tool drifting apart. SUMMARY: 59-01-SUMMARY.md. Original scope follows.
- [ ] ~~59-01: the harness — PLAN created 2026-08-09~~. New files only, no product path touched.
  3 auto tasks + 1 checkpoint:decision (confirm the D4 exclusion list against the printed coverage
  table); `autonomous:false`, `depends_on []`; no new dependency.
  ⚠⚠ THE CIRCULARITY TRAP: phase scoring must seed from `metrics_json_auto`, NOT `metrics_json` —
  `api.py:889` has already overwritten the latter with metrics recomputed FROM the human annotation,
  so seeding from it and scoring against that same annotation manufactures a meaningless near-perfect
  score. ⚠ Optimal assignment (`scipy.optimize.linear_sum_assignment`), not the greedy matcher that
  produced the preliminary numbers. ⚠ The regression pins exact values within 1e-6, not a `>=` floor,
  because 59-02's acceptance is byte-identical output. ⚠ `metrics.py` is read-only here INCLUDING
  anything that looks wrong while reading it. Files —
  `segmenter_eval.py` (pure: named-series matching, P/R/F1, tolerance sweep, coverage statistic),
  `tools/score_segmenter.py` (CLI), `tests/fixtures/segmenter_truth.json`,
  `tests/test_segmenter_eval.py`. Scores wavelet + trough + a peak-pick baseline over cycle
  boundaries AND the four human phase boundaries, on both the annotated window and the production
  `ip_end:swim_end` window (the gap between them measures how much error belongs to phase detection
  rather than segmentation — never separated before). No new dependencies.
- [x] 59-02 ✅ **COMPLETE 2026-08-09** — all 5 ACs pass. Suite 262 → **268**; 5 files; no behavior
  change. ⭐ **INERTNESS PROVEN BY HASH, NOT BY ASSERTION** — the full fixture report (every
  window × candidate × framing) captured BEFORE the first edit and again after all three tasks is
  byte-identical, `sha256 4609a7b0…` both times. `git diff` on `tests/test_segmenter_eval.py` and
  the fixture is EMPTY, so no pinned value was edited to make anything pass.
  Shipped: `SEGMENTER_BY_STROKE` (**empty by design**) + `resolve_segmenter()` +
  `compute_session_metrics(..., stroke_type=None)`; `/process` forwards the stroke it already had.
  ⚠ **FIRST PHASE-59 CHANGE ON THE RAILWAY DEPLOY PATH** (`metrics.py`, `api.py`) — safe, since
  nothing moved, but 59-01 was purely additive by comparison.
  ⚠ **TWO TESTS ARE EXPECTED TO FAIL LATER BY DESIGN**:
  `test_stroke_type_does_not_change_results_yet` fails in 59-05, and the 7 pinned regression values
  move in 59-03 and 59-05. Re-baseline them with the new numbers recorded in that plan's SUMMARY —
  never edit them to make a diff green.
  ⚠ AUTO-FIX worth keeping: the CLAUDE.md note first claimed the ~1.75× defect was "fixed in
  59-03". It is NOT — 59-03 is unwritten. Corrected to "STILL LIVE, owned by 59-03", with the
  consequence spelled out (auto vs annotation-recomputed freestyle metrics are not on the same
  scale). SUMMARY: 59-02-SUMMARY.md. Original scope follows.
- [ ] ~~59-02 PLAN created 2026-08-09~~ — 3 auto tasks, **`autonomous:true`**
  (everything is mechanically verifiable — no checkpoint), `depends_on ["59-01"]` (genuine: 59-01's
  regression IS this plan's acceptance test). 5 files: `metrics.py`, `api.py`, `tests/test_metrics.py`,
  `tests/test_api.py`, `CLAUDE.md`. ⚠ **THE REGISTRY SHIPS EMPTY BY DESIGN** — it is an OVERRIDE
  table, and "no stroke has earned its own segmenter yet" is the literal truth today; pre-populating
  four entries all pointing at the wavelet says nothing and still has to be edited in 59-05.
  ⚠ Task 1 must capture a before-image of the fixture report BEFORE editing — it covers all
  windows × candidates × framings, broader than the 7 pinned assertions, and cannot be reconstructed
  afterwards. ⚠ `tests/test_segmenter_eval.py` and the fixture are BOUNDARIED: editing a pinned value
  to make it pass would destroy the only evidence the refactor is inert. ⚠ The registry CONTRACT is
  written down now — `(t, vel) -> cycles|None`, slice-relative — because `segment_cycles_trough`'s
  extra `T_est` param does NOT match it and 59-05 must wrap it rather than widen the seam. ⚠ AC-2
  requires proving a registered override is actually CALLED, or the refactor is untested plumbing
  wired to nothing. `api.py:888` deliberately untouched (dead by construction — guarded by
  `cycle_bounds`, which bypasses segmentation entirely). Original scope follows.
- [ ] 59-02 (scope): **pure dispatch refactor.** `compute_session_metrics(..., stroke_type=None)`
  plus a stroke→implementation registry inside `metrics.py`; every stroke still routes to the
  wavelet. **Acceptance is byte-identical harness output** — 59-01's regression pins exact values to
  1e-6 precisely so this is provable. `stroke_type=None` reproduces today's path, so all 8 existing
  call sites are unaffected by default. ⚠ `metrics.py` owns its OWN registry — no import edge to
  `annotations.py`, because `MARKS_PER_CYCLE` is the LABELING convention and this is SEGMENTER
  behavior, and 59-01 measured that they are different numbers.
- [x] 59-03 ✅ **COMPLETE 2026-08-09** — all 6 ACs pass. Suite 268 → **269**; 2 files created,
  3 modified. **GATE PASSED: median auto/human stroke-rate ratio 1.647 → 0.973**, median |log ratio|
  0.50 → 0.069. `ip_end` median error **3.93 → 1.99 s**, `finish` **3.82 → 0.82 s**.
  Shipped `detect_swim_window` (CWT-ridge frequency SETTLING — steady-state stroke frequency taken
  from the back 60% of the swim, `ip_end` = where the ridge first settles near it) plus
  `_pair_boundaries` registered for freestyle/backstroke through 59-02's seam.
  ⭐ **THE RESEARCH MATTERED — 3 of 4 candidates failed, instructively.** A and B missed `ip_end` by
  4–8 s and always EARLY (dolphin kicking is rhythmic; B's band filter centred on the kicking
  because its reference was computed over a mask containing it). C nailed `finish` but was WORST on
  `ip_end`. Only the frequency-transition candidate beat the incumbent on both.
  ⚠⚠ **A REGRESSION THE GATE COULD NOT SEE.** The gate measures the 12 fully-labeled sessions —
  exactly the tuning subset. Across all 36, **13 produced a window yielding ≤3 cycles**, a failure
  mode the OLD detector never had. Root cause: the amplitude run latches onto the DIVE transient,
  whose broadband energy inflates the 95th-pct reference until swimming falls below it. **Four
  alternative references were swept; none beat the shipped one, two were far worse.** Resolution
  (user decision, asked because it exceeded the already-answered checkpoint): `_WINDOW_MIN_CYCLES =
  4.0` — disbelieve any window spanning <4 cycles at its own detected frequency and return None, so
  the caller keeps the old boundaries. Flags **13/13** collapsed windows while also disbelieving
  7/23 sound ones; the asymmetry is deliberate (a false positive costs only the improvement, a false
  negative ships a confident wrong answer). **Collapse 13/36 → 1/36.**
  ⚠ **17 of 36 sessions now fall back** — the improvement reaches roughly half the corpus.
  ⚠ **`tools/score_segmenter.py`'s production-window column is STALE** — it still calls the old
  detectors. 59-04 must fix it before trusting that column.
  ⚠ Butterfly/breaststroke are unpaired but the window still moved them: median **1.316**, fly to
  1.92 — the fix removed an error that had been cancelling for them too. Reported, not compensated.
  ⚠ AC-3 verified empirically: `cycles` identical 23/23 across annotation recomputes, `session`
  22/23 (the exception has `finish_s = null`, so there was no human boundary to override with).
  ⚠ AUTO-FIX: my own reordering moved `detect_initial_phase` above the manual `baseline_end_idx`
  override, silently changing dive/pulldown on annotated sessions — caught by reading the diff, not
  by a test. ⚠ `_cwt_ridge` extraction proven inert by the 59-01 fixture hash.
  SUMMARY: 59-03-SUMMARY.md. Original scope follows.
- [ ] ~~59-03 PLAN created 2026-08-09~~ — cycle pairing **+ the swim-window fix**,
  bundled. 4 tasks + 1 checkpoint:decision; `autonomous:false`; `depends_on ["59-01","59-02"]`.
  ⚠⚠ **THIS PLAN'S SCOPE DOUBLED AT PLANNING TIME, AND IT CORRECTS A CLAIM MADE IN 59-01's SUMMARY
  AND IN CONTEXT D7.** Both said the pairing fix was "independent, so it must not wait." It is
  independent of the SEGMENTER but **not of the WINDOW**, and the two errors partially cancel.
  Measured on the 12 fully-labeled freestyle sessions: today **1.647**, pairing only **0.761**
  (a sign flip, not a fix), window only **2.135** (strictly worse), **both 1.010 (10/12 within
  ±15%)**. Neither half is independently shippable, which is why the phase's usual
  one-change-per-plan rule argues FOR bundling here.
  ⚠ **TWO HYPOTHESES ABOUT THE WINDOW WERE TESTED AND BOTH REFUTED — it is not a tuning fix.**
  `ip_end` is not picking the wrong trough (in 12/23 sessions the first trough already IS the
  nearest to the human mark, still 0.6–6.1 s early; several freestyle traces contain exactly ONE
  qualifying trough and it is 5–6 s early — the trough is the wrong FEATURE). `finish` is not
  threshold-sensitive (mean |vel| in the over-run is **0.403 m/s, 8× `_BASELINE_THRESH`** — the
  swimmer really is still moving; it is a SEMANTIC gap).
  ⭐ **REFRAMING:** both boundaries fail the same way — the detectors ask "where does MOTION start
  and stop", the human marked "where does CYCLIC STROKING start and stop". Post-touch drift is fast
  but not rhythmic; underwater kicking is rhythmic at the wrong frequency. The CWT ridge already
  encodes that distinction. This makes the window fix RESEARCH, so the plan opens with a design task
  in `tools/` and a checkpoint where **stopping is an explicit, legitimate option**.
  DECISIONS: full pairing (a cycle becomes 2 boundaries, so per-cycle metrics are computed over real
  cycles — accepted comparability break, and `cv_isi` is expected to get NOISIER since the wavelet
  over-segments 1.15–1.5×); `finish` redefined as end-of-cyclic-stroking; **dry-run backfill report
  only**, no DB write (37 sessions affected, **14 already on the human scale** — the corpus is
  ALREADY mixed, so this changes which axis the inconsistency falls on rather than creating it);
  gate = median ratio in **0.85–1.15** AND median |log ratio| < today's 0.50.
  ⚠ Pairing ships as a WRAPPER in `SEGMENTER_BY_STROKE` — exactly what 59-02's seam was built for —
  and the divisor is NOT imported from `annotations.MARKS_PER_CYCLE` (that is exact physiology for
  human marks; on the auto path 2 works only as an empirical property of the wavelet).
  ⚠ 59-01's 7 regression pins and 59-02's `test_stroke_type_does_not_change_results_yet` BOTH move
  here (59-02 predicted the latter for 59-05; it lands earlier). Re-baseline with every old → new
  recorded; nothing may be loosened or deleted to make the suite green.
  ⚠ `ratings.py` untouched but AFFECTED — halving freestyle stroke rate moves it against the
  breaststroke-derived bands, changing pillar scores and the needs-attention list. Report, do not
  compensate; Phase 53 owns it.
- [x] 59-04 ✅ **COMPLETE 2026-08-09** — all 5 ACs pass. Suite 269; 1 file created, 2 modified,
  **`metrics.py` untouched** (nothing shipped, as designed). Results (annotated window, F1 @±0.15 s):
  | candidate | free | fly | breast |
  |---|---|---|---|
  | wavelet (incumbent) | 0.458 | 0.317 | 0.232 |
  | peakpick | 0.437 | **0.524** | 0.308 |
  | R2 snap→steep rise | **0.485** | 0.233 | 0.239 |
  | L1 learned (LOSO) | 0.375 | **0.591** | **0.359** |
  ⭐ **THE LEARNED MODEL DID NOT OVERFIT — 59-01's PREDICTION WAS WRONG.** LOSO vs in-sample differ
  by ~0.01 (fly 0.591/0.600). Mechanism: logistic regression on 5 features is too LOW-CAPACITY to
  memorise 236 marks. ⚠ This does NOT license a bigger model — a higher-capacity learner would
  behave exactly as 59-01 feared.
  ⭐ **BUTTERFLY: the wavelet is the wrong tool** — beaten ~2× by two unrelated methods.
  ⭐ **FREESTYLE: refinement works but trades events for precision** — R2 wins at every tolerance
  below ±0.30 and LOSES at ±0.30 (0.774 vs 0.836).
  ⭐ **CONTEXT D13 ANSWERED — the trough segmenter does not transfer.** 0.000 on every stroke even
  untrimmed, and VERIFIED not an artifact: 9–33 troughs found per session but **zero inside the swim
  window** on free/fly — during actual stroking velocity never drops below 0.20×v95. Breaststroke
  gets 12 in-window troughs yet still scores 0.000 until ±0.30 — a systematic PHASE OFFSET. Stop
  carrying it.
  ⚠⚠ **GROUND TRUTH REDEFINED MID-PHASE (user): it is now the TRACE, not video.** The product only
  ever has the trace. **This INVERTS 59-01's quality ordering** — the corpus is inhomogeneous
  (58-02 shipped mark-at-playhead on 08-07, so only that batch is video-timed), and the batch 59-01
  called "measurably the best" on coverage is now the LESS appropriate ground truth. **Nothing was
  re-scored on this basis.**
  ⚠ **TETHER SAG investigated (user hypothesis: encoder 0.5 m above water, inextensible free-spool
  line, so the CWT may have been right and the labels wrong).** Error DOES grow within a swim with
  the sign sag predicts (mean |err| 0.150 → 0.235 s across thirds, 13/19 sessions) — but chart-timed
  vs video-timed labels show NO difference (median F1 0.308 vs 0.379), so the ~60 ms drift is an
  order of magnitude too small to explain F1≈0.3. **Not supported at corpus level.** DEFERRED and
  decisive: mark one swim from trace alone AND video alone, measure divergence vs distance.
  ⚠ PLAN SELF-CONTRADICTION resolved: AC-1 required re-baselining the production-window column while
  the boundaries said the 59-01 pins "must not move" — the pins CONTAIN those values. Resolved for
  AC-1; 8 pins updated; the annotated column did NOT move (containment proof).
  ⚠ Boundary-count ratios for 59-05's `k`: wavelet 2.27, peakpick 3.47, L1 2.17, R2 2.25 — a winner
  that is not ~2.27 means `k` must be RE-MEASURED. ⚠ sklearn is `tools/`-only; shipping L1 puts it on
  the Railway path as an EXPLICIT 59-05 decision. SUMMARY: 59-04-SUMMARY.md. Original scope follows.
- [ ] ~~59-04 PLAN created 2026-08-09~~ — 3 tasks, `type: research`,
  `autonomous:true`, `depends_on ["59-01","59-03"]`. **2 files, both in `tools/` — nothing ships to
  `metrics.py`.** ⭐ **The work originally expected when annotation started** —
  `segment_cycles_wavelet` is still exactly as 16-05 shipped it.
  BASELINE RE-MEASURED at plan time (entries F1 @±0.15 s, median/session), because 59-03 changed the
  segmenter's input: freestyle **0.186 → 0.280** (perfect window 0.458), butterfly **0.320 → 0.222**
  (0.317), breaststroke **0.473 → 0.167** (0.232). Production is **0.17–0.28** — about one boundary
  in four lands within 150 ms of a human mark. ~40% of the remaining freestyle gap is STILL window
  quality even after 59-03.
  SIX CANDIDATES across four families: boundary snapping to velocity minimum / steepest rise (the
  F1-vs-tolerance curve climbs 0.19→0.74, i.e. right events, bad placement); per-swimmer matched
  filter; **trough re-fed the UNTRIMMED trace** (answers CONTEXT D13, open since 59-01 — its 0.00
  was a MISFEED, since Phase 57 removed the dead tail it keys on); autocorrelation + constant phase;
  and a small learned boundary detector. Plus both incumbents.
  ⚠⚠ **LEAVE-ONE-SESSION-OUT IS MANDATORY for every tunable candidate** — 59-03's lesson made
  mechanical. Its gate passed on the 12 sessions its constants were tuned against and then collapsed
  on 13 of 36. With a learned model on 236 marks from ONE swimmer, in-sample scoring is actively
  misleading; LOSO and in-sample are reported side by side.
  ⚠ **PRIMARY SCORING USES THE ANNOTATED WINDOW** — the window is out of scope and 59-03's is
  freestyle-tuned, so scoring through it would penalise a butterfly candidate for a defect it did not
  cause. ⚠ **WINDOW IS OUT OF SCOPE (user decision), so the butterfly/breaststroke regression and the
  17/36 fallback rate BOTH STAY LIVE** after this plan — recorded, not fixed.
  ⚠ Task 1 is a prerequisite: `score_segmenter.py`'s production-window column is STALE and no longer
  measures what the pipeline slices. Fixing it re-baselines that column; the annotated column must
  NOT move, which is the proof the change is confined.
  ⚠ A negative result on the learned model is a real deliverable. Original scope follows.
- [ ] 59-04 (scope): **EXPLORE new segmentation techniques** (`type: research`). Candidates
  live in `tools/` or a scratch module and NEVER in `metrics.py`, so a dead end costs nothing;
  deliverable is a scored table plus a recommendation, not production code. Directions the 59-01
  measurements actually point at, rather than a blank page: snap ridge crossings to a local velocity
  feature (the F1-vs-tolerance curve says right events, bad placement); reject the two-dolphin-kick
  harmonic for butterfly; **re-score the trough segmenter on the UNTRIMMED trace** (its 0.00 is a
  misfeed, and this is the only way to answer D13); per-swimmer matched filter / template averaging;
  rate-continuity-constrained DP on the ridge; HMM. Also worth testing whether fixing the +7.8 s
  window raises segmentation scores without touching the segmenter at all.
- [x] 59-05 ✅ **COMPLETE 2026-08-09** — all 4 ACs pass. Suite 269 → **273**; 3 files modified.
  Butterfly + breaststroke moved OFF the wavelet to `_learned_boundaries` with k=2; freestyle
  deliberately unchanged (59-04 measured both challengers worse on freestyle cycle regularity).
  butterfly **F1 0.317→0.526, cv 0.218→0.104, rate 1.31→1.02**; breaststroke **F1 0.232→0.444,
  cv 0.217→0.071, rate 1.66→1.00**.
  ⭐ **NO sklearn IN PRODUCTION** — 5-feature logistic regression, inference is a dot product +
  sigmoid, numpy form verified to reproduce `predict_proba` to **1.1e-16**. Weights are a constant
  block; retrain = re-run `tools/segmenter_candidates.py` and replace two numbers.
  ⭐⭐ **FOUND AND FIXED A PHASE BUG IN 59-03's PAIRING.** `_anchors_from_marks` pads with index 0,
  so pairing `[0,m0,m1,…]` at 0,2,4… selected `[0,m1,m3,…]` — every freestyle cycle **half a cycle
  out of phase**. Boundary F1 **0.000 with the pad, 0.458 without**. It survived 59-03's gate
  because `stroke_rate_spm` is blind to it (mean interval identical, ratio 1.00 either way).
  ⚠ SCOPE ADDITION: that fix touches `_pair_boundaries`, which 59-05's boundaries said not to do —
  justified, but **freestyle per-cycle metrics moved AGAIN**, a second comparability break.
  ⭐ `peakpick` rejected for butterfly despite better F1 (alternation 0.276 vs human 0.056);
  `TestCycleRegularityGate` now guards that permanently. ⚠ Breaststroke rests on n=2.
  SUMMARY: 59-05-SUMMARY.md. Original scope follows.
- [ ] ~~59-05 (scope)~~: **SHIP the winner per stroke.** Fill in 59-02's registry from 59-04's
  table. ⚠ Backstroke inherits freestyle's implementation, documented as unvalidated (CONTEXT D12) —
  it has ZERO labeled sessions. ⚠ Breaststroke rests on 2 sessions plus historical validation, and
  the write-up must say so. ⚠ Do NOT apply a global timing offset: 59-01 measured the error as
  scatter, not lag.

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
