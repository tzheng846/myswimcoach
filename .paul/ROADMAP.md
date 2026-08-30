# Roadmap: Swimnetics

> **Historical phase index (Phases 1–77).** For what's in flight right now use
> [STATE.md](STATE.md), not this file. Per-phase detail (PLAN / SUMMARY / CONTEXT) lives in
> `.paul/phases/<n>-*/`. The pre-trim long-form roadmap is archived at
> `.paul/archive/ROADMAP-full-2026-08-21.md`.
>
> Status key: ✅ complete · 🚧 in progress · 📋 planned (scoped, not built) · ⏸ unscheduled TODO.
> A blank date means the completion date wasn't captured here — see the phase dir.

## Overview
End-to-end velocity-tracking and stroke-analysis pipeline for swimming. Answers questions like
"how does my technique vary throughout my swim?"

---

## Milestone: v0.1 Initial Release ✅

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 1 | Segmentation Refactor | ✅ | 2026-05-17 |
| 2 | Metric Explanations | ✅ | 2026-05-17 |
| 3 | BLE Record View | ✅ | 2026-05-20 |

## Milestone: v0.2 Coach Demo ✅
**Goal:** Live demo-ready iOS app — full analytical breakdown, multi-swimmer dashboard, dive/pulldown detection, per-athlete history.

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 4 | FastAPI Backend | ✅ | 2026-05-20 |
| 5 | iOS App — TestFlight | ✅ | 2026-05-22 |
| 6 | Auth + Athlete Profiles | ✅ | 2026-05-23 |
| 7 | Algorithm + Backend | ✅ | 2026-05-23 |
| 8 | iOS Full Analytics | ✅ | 2026-05-24 |
| 9 | iOS Dashboard + History | ✅ | 2026-05-24 |

## Milestone: v0.3 Metrics Quality ✅
**Goal:** Coach-facing data-quality signals — cycle plausibility, magnet dropout, outlier counts, kick-reliability flags.

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 10 | Metrics Quality | ✅ | 2026-05-25 |

## Milestone: v0.3.5 Pipeline Tests ✅
**Goal:** Pytest suite over the signal pipeline so metric/API changes don't silently regress.

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 11 | Pipeline Tests | ✅ | 2026-05-25 |

## Milestone: v0.4 Coach Experience ✅
**Goal:** Coach QoL — session naming, notes, starring, deletion, stroke filter, pre-recording config.

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 12 | QoL Features | ✅ | 2026-05-25 |

## Milestone: v0.4.5 Graph Enhancements ✅
**Goal:** Interactive velocity chart — time markers, touch cursor, pinch-zoom, m/yd toggle, live recording graph.

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 13 | Graph Enhancements | ✅ | 2026-05-25 |

---

## Milestone: v0.5 Commercial Foundation 🚧
**Goal:** Billing, device management, website + parent reports, video ground truth, and the race-phase
report-card model — everything needed for paying customers. This is the active milestone; the
segmentation / phase-metrics work (Phases 75–77) is the current frontier.

| Phase | Name | Status | Completed |
|-------|------|--------|-----------|
| 14 | Device Registration | ✅ | 2026-06-08 |
| 15 | Billing + Tier Enforcement | ✅ | |
| 16 | Freestyle Support | ✅ shipped (placeholder quality; tuning deferred) | 2026-06-12 |
| 17 | UX Polish | ✅ | |
| 18 | Design Refresh | ✅ | |
| 19 | Bug Fixes | ✅ | |
| 20 | Device Management | ✅ | |
| 21 | BLE Persistence | ✅ | |
| 22 | Video Overlay Validation | 🚧 at device checkpoint | |
| 23 | Website | ✅ | 2026-06-11 |
| 24 | Parent Report Cards | ✅ | 2026-06-11 |
| 25 | Codebase Audit | ✅ | 2026-06-12 |
| 26 | In-App Video Overlay | 🚧 at EAS-build checkpoint | |
| 27 | Device Model (3D hero) | ✅ | 2026-06-12 |
| 28 | Privacy Policy | ✅ | 2026-06-13 |
| 29 | Marketing Content | ✅ | 2026-06-14 |
| 30 | Website Copy Polish | ✅ | 2026-06-15 |
| 31 | AI Coaching Chat | 📋 superseded by Phase 33 | |
| 32 | SoCal Coach Outreach Research | ✅ | 2026-06-16 |
| 33 | AI Coaching Chat v2 | ✅ | 2026-06-16 |
| 34 | Device Diagnostics | ✅ code (on-device verify deferred) | |
| 35 | Feature Verification & Doc Reconciliation | ✅ | 2026-06-18 |
| 36 | Coach-Friendly Metric Ratings | ✅ | 2026-06-17 |
| 37 | Team Coach Dashboard | ✅ | 2026-06-18 |
| 38 | Mobile UI/UX Redesign | ✅ | 2026-06-19 |
| 39 | Redesign Fixes & UX Iteration | ✅ | 2026-06-19 |
| 40 | Website Redesign (iOS match) | ✅ | 2026-06-22 |
| 41 | Race-Start Sequence (iOS) | ✅ | 2026-06-22 |
| 42 | Core-Flow Failsafes (iOS) | ✅ | 2026-06-22 |
| 43 | Demo Readiness (runbook) | 📋 doc, planning | |
| 44 | Encoder Data Integrity | 🚧 44-03 owed (warmup floor + overlay sync) | |
| 45 | Cloud Session Save (device_id UUID→TEXT) | ✅ | 2026-07-30 |
| 46 | Marketing Blog (build log) | ✅ | 2026-06-23 |
| 47 | Trial Annotation (review + ground truth) | ✅ | 2026-07-20 |
| 48 | Athlete-Create Fix | ✅ | 2026-07-30 |
| 49 | Security Hardening (backend) | 📋 planned | |
| 50 | Demo Team & Synthetic History | ✅ | |
| 51 | API Correctness & Audit | ✅ | |
| 52 | Sample-Rate Contract | ✅ | |
| 53 | Attention Allocation (SPC detection engine) | 📋 direction/planning | |
| 54 | Gate Removal (tier + stroke gating) | ✅ | |
| 55 | Athlete Flow Fixes (mobile) | ✅ | |
| 56 | Coach Chat Athlete Scoping | ⏸ open defect, unscheduled | |
| 57 | Annotation Workflow (annotate-tool v2) | ✅ | |
| 58 | Video Ground Truth (solo capture + annotate-from-video) | ✅ | |
| 59 | Segmenter Evaluation (ground-truth scoring harness) | ✅ | |
| 60 | Mobile App Rework (per-cycle analytics + video + chart windowing) | ✅ | |
| 61 | Web Portal Rework (report card + video + Compare) | ✅ | |
| 62 | Progress Report Rework | ⏸ unscheduled | |
| 63 | Data Flow Map (DATA-FLOW.md) | ✅ | 2026-08-13 |
| 64 | Fullscreen Video + Velocity Overlay (web) | ✅ | |
| 65 | Underwater Phase Detection (free / back / fly) | ✅ | |
| 66 | Acceleration Derivative (Savitzky–Golay) | ✅ | |
| 67 | External Camera Sync (GoPro / waterproof cam) | ✅ | |
| 68 | Persist Generated Session Names | ⏸ unscheduled | |
| 69 | Multi-Camera Video (up to 4 synced angles) | ✅ | |
| 70 | Video Session Matching | ✅ | |
| 71 | Video Surface Rework | ✅ | |
| 73 | Group Comparison | ✅ | |
| 74 | BLE Dump Reliability | 📋 planned (74-01 plan only) | |
| 75 | Report Card Revamp (Race-Phase Model: Start / Underwater / Swim) | 🚧 Start (75-04) + UW metrics + Step-3 UI (75-05 /phases) done; report-card CONSOLIDATION cutover shipped (75-07 `040ce0d`); **75-06 Swim+Whole metrics CLOSED 2026-08-28 — registry complete 46/47, 23 scalar specs, annotations-first per-cycle (43 trusted/44 provisional live), `PUT /annotations` phases-drop repair, library backfilled; ⚠ uncommitted (shares `api.py` with 82-01), AC-7 human-verify owed**; 75-08 compare-window → 75-09 unified trace still next | |
| 76 | Breakout Detection (free/back — kick-band disappearance) | ✅ | 2026-08-20 |
| 77 | Fly Breakout Detection (arm-cycle appearance) | ✅ | 2026-08-20 |
| 78 | Multi-Swimmer Segmentation Diagnostic (pure, no fixes) | ✅ complete (4/~15 swimmers annotated — coverage gap, not "one swimmer") | 2026-08-21 |
| 79 | Redefine dive_start_s (foot of first ≥X m/s surge) | ✅ complete (`e1934ba`; X=2.0, MAE 0.72→0.15 s; backfill applied) | 2026-08-21 |
| 80 | Stroke-Cycle Segmentation (count-centric re-measurement + tuning) | 🚧 CONTEXT done (freestyle-only; measure→re-tune wavelet) | |
| 81 | Annotation Video Marking (play-and-tap + on-video overlay + UW-kick marker) | 🚧 81-01 shipped (`a73db03`) — active camera = stage-fullscreen overlay w/ marker buttons (Dive/UW/Stroke/Finish + stroke-mark) + 4/8/All window presets in the bar; mark in fullscreen without exiting; keys 1/2/4/5+M retained; shared report components untouched. ⚠ human-verify owed. 81-02 (key-3 kick marks + backend recompute) owed | |
| 82 | Storage Quota Cleanup (session-delete storage leaks + Supabase Pro upgrade) | 🚧 planning — 82-01-PLAN.md created; free tier over quota (2.53 GB vs 1 GB); 716 MB orphaned from two leak sources in `DELETE /sessions/{id}`: `video_path` never removed, and `session_videos` cascade-deletes rows without removing their storage objects | |
| 83 | Per-Cycle / Per-Kick Trace Coloring (phase-section insets) | 🚧 **83-01 CLOSED 2026-08-28** (cycles half shipped + AC-7 approved — Swimming inset bands, ticks, amber outlier, annotated-vs-auto badge, hover readout, bidirectional highlight; new pure `web/lib/cycleBands.js`, reusable for kicks). **83-02 CLOSED 2026-08-28** (kicks half shipped, apply outcome approved — `metrics.segment_kick_bands` trough-to-trough with no new constant, `phases.kick_bands` persisted, schema 3→4, Underwater inset via 83-01's lib unmodified, breaststroke gated off, 63/81 non-breaststroke backfilled; **CONTEXT D5 REVERSED** — bands ride inside `phases`, not top-level `metrics_json.kicks`, so all three `PhaseContext` write sites get them from one change and they cannot go stale against an annotated window; peak dot removed everywhere at user direction, so AC-5's zero-diff on `PhaseVelocity.js` failed by the letter). **83-03 CLOSED 2026-08-29** (AC-8 approved on the SECOND attempt, first verify retracted) = breakout GOLD shipped as a synthetic `n: 0` band on annotated sessions only (the coach's streamline-break mark → their first stroke mark; measured positive on all 43 annotated, median 1.04 s). ⚠ **The plan's central feature — the k=3.0 MAD anomaly flag — was MEASURED AND CUT**: at a median 7 cycles a lap it fired on 75% of sessions at k=3.0 and still 39% at k=8.0, so no threshold separates clean from ragged. `web/lib/cycleShape.js` kept but PARKED and unwired; the fix needs a cross-session baseline (STATE item 17). **83-05 CLOSED 2026-08-29** (AC-8 approved after two live corrections) = cycle/kick OVERLAY panel — the replacement for the cut classifier: every cycle (Swimming) / kick (Underwater) laid on one shared axis beneath the inset, all-grey pack, left number gutter with hover-preview + click-to-pin, three-way cross-highlight, seconds axis with a normalized % toggle that adds a pointwise median; breakout excluded from the pack but shown as a `0 · breakout` gutter row. Frontend only, no schema, no backfill; suite still 497; the three protected components stayed byte-identical. Partially un-parks `cycleShape.js` (resample + median wired, MAD gate stays parked, item 17 stays open); ships the item-18 kick-tiling artifact knowingly. ⚠ **Two live corrections at the verify:** the gutter now WRAPS at 10 rows (a 15-dolphin-kick underwater outgrew the chart), and **AC-3 was OVERRIDDEN** — the breakout gutter row is no longer inert, it highlights the gold `n: 0` band on hover. ⚠ Two boundary widenings forced by contradictions inside the PLAN: `cycleShape.js` gained two `export` keywords, and `niceMax` is duplicated from the DO-NOT-CHANGE `PhaseVelocity.js` (guarded by a byte-equality check). ✅ New reusable **headless render-check harness** (`scratch/overlay_render_check.mjs`, 40 checks) that needs no auth — the concrete answer to 83-01's "build and lint are blind to this". Peak-alignment surfaced as a better axis mode and was DECLINED → STATE item 19. **83-04 owed** = inset window framing (context padding + minimum span), dropped out of 83-03, independent of 83-05. Phase stays 🚧 — plan/summary counts now match at **4/4**, the exact heuristic that has falsely signalled "done" at 83-01, 83-02 AND 83-03; **83-04 is scoped in STATE but still has no PLAN**. Original scope: alternating blue/purple bands per stroke cycle (Swimming inset) + per downkick (Underwater inset), grey outside, boundary ticks; new `metrics_json.kicks` persist; count badge w/ human-vs-auto provenance, per-band hover readout, bidirectional cross-highlight with CycleCharts, amber outlier outline. Stacks on uncommitted 75-06, shares its backfill | |
| 84 | Mobile App User Feedback (icon, upload failures, camera, orientation, indicators, brush gesture) | 🚧 CONTEXT done 2026-08-29 (`/paul:discuss`) — 6 user-reported items in the **separate `swimnetics-mobile` repo**; 4 root-caused during discuss, item 2 rescoped to a diagnostic. Native/JS split drives sequencing: **only 1 (AppIcon.appiconset, iOS-only per D1) and 4 (`Info.plist` `UISupportedInterfaceOrientations` still lists both landscape values — `app.json`'s `"orientation": "portrait"` is inert in a bare workflow) need a new EAS build**; 2/3/5/6 are JS. Item 2's premise was FALSE (both the video-file enqueue and the sync-origin save already auto-fire) → rescoped to "find out why uploads sometimes fail", with 6 code-grounded hypotheses, chief among them the 50 MB `MAX_VIDEO_BYTES` 413 against an unset `videoQuality`, the **Phase 82 over-quota bucket** (a possible hard prerequisite), and the **in-memory queue that dies on app restart with no error surfaced**. Item 5 is larger than reported — **three** indicator vocabularies, not two (dashboard 0–100 score excluding provisional / athlete-detail hardcoded `BAND_COLOR` ignoring both `rating_colors` and provisional / `PillarCards`' third inline derivation), so a provisional pillar is invisible, trusted, and warned-about depending on the screen; D3 makes band+`rating_colors` canonical across all three. Item 6 root cause = the brush `PanResponder` never sets `onPanResponderTerminationRequest`, which **defaults to `true`**, so the parent ScrollView steals the drag on any vertical drift. No PLAN yet | |
| 85 | Marketing Home Page Refresh (mark + race-phase repositioning + copy rewrite) | ✅ **COMPLETE 2026-08-29 (1/1 plans, `a75c373`, pushed to `main` so it is live).** CONTEXT done over **4 discuss rounds**; **85-01 APPLIED 2026-08-29, AC-8 approved on the live local site; loop CLOSED.** Shipped as planned with four deviations worth carrying: the copy check is scoped to the MARKETING surface, not all of `web/components` (the portal legitimately says "GoPro" and holds `changed (unclear)` in the `AlertSummary.js` that D27 forbids touching, plus ~285 comment dashes); the build now emits **20** static pages, not AC-7's 19 (measured: +2 icon routes, -1 favicon); the three phase cards align their radars with a per-card CSS **grid row** rather than the mockup's reserved `min-height`, which held at 1280 but broke at 880 where the underwater blurb wraps to a fifth line; and `Brand` uses `next/image` because `no-img-element` is enabled here. Marketing site untouched since `17086cb` (2026-06-22, Phase 40), so ten weeks of product work is invisible: race-phase report card, usual-range comparison, per-cycle bands, multi-camera video. Approved design = `scratch/website-home-mockup.html` (re-runnable build chain in `scratch/`). Page becomes hero → report card → usual range → cycle pack → video → device → how it works → quote; `Features.js` + `SampleChart.js` retired; the Swimnetics mark enters the site for the first time (nav + footer lockup + favicon). **Charts are drawn from ONE real coach-marked session** (Chantee "100%", butterfly, `85b18b3f`, all four boundaries `manual`) — trace geometry real and unmodified, every printable value deterministically perturbed, no athlete name, so **the page may never claim "real data"**. Baked to a static `web/lib/marketingGeom.js` at author time; no Supabase call on a public page. **D24 (alert semantics) drove a correction that matters beyond the site:** an alert fires ONLY outside the usual range, in-range is "Normal" and uncounted — ⚠ but the round-4 code read established the portal's `flagVerdict` **already implements exactly that**, so the earlier claim that the portal was wrong is RETRACTED; the only real gap is the out-of-range-ambiguous chip label ("changed (unclear)" → "to review"), deferred to a follow-up phase (D27, marketing-only scope). Also corrected: the em-dash inventory was wrong — the FAQ is **10 `&mdash;` entities to 2 literal characters**, so a character-only check reads clean while the page is not, and `app/layout.js` (2, inside `metadata`) was missed entirely. ⚠ `web/` auto-deploys to Vercel on push to `main` (R4), and the plan removes the FAQ's stroke-validation answer (D6/R3) and publishes a breakaway-magnet safety claim (D25/D29, user-confirmed real) |2026-08-29 |

_Phase 72 was never used. 56 / 62 / 68 are unscheduled TODOs with no phase directory — live tracking is in [STATE.md](STATE.md)._
