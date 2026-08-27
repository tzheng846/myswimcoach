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
| 75 | Report Card Revamp (Race-Phase Model: Start / Underwater / Swim) | 🚧 Start (75-04) + UW metrics + Step-3 UI (75-05 /phases) done; report-card CONSOLIDATION cutover shipped (75-07 `040ce0d`) → 75-08 compare-window → 75-09 unified trace next; Swim/Whole metrics owed (75-06) | |
| 76 | Breakout Detection (free/back — kick-band disappearance) | ✅ | 2026-08-20 |
| 77 | Fly Breakout Detection (arm-cycle appearance) | ✅ | 2026-08-20 |
| 78 | Multi-Swimmer Segmentation Diagnostic (pure, no fixes) | ✅ complete (4/~15 swimmers annotated — coverage gap, not "one swimmer") | 2026-08-21 |
| 79 | Redefine dive_start_s (foot of first ≥X m/s surge) | ✅ complete (`e1934ba`; X=2.0, MAE 0.72→0.15 s; backfill applied) | 2026-08-21 |
| 80 | Stroke-Cycle Segmentation (count-centric re-measurement + tuning) | 🚧 CONTEXT done (freestyle-only; measure→re-tune wavelet) | |
| 81 | Annotation Video Marking (play-and-tap + on-video overlay + UW-kick marker) | 🚧 81-01 shipped (`a73db03`) — active camera = stage-fullscreen overlay w/ marker buttons (Dive/UW/Stroke/Finish + stroke-mark) + 4/8/All window presets in the bar; mark in fullscreen without exiting; keys 1/2/4/5+M retained; shared report components untouched. ⚠ human-verify owed. 81-02 (key-3 kick marks + backend recompute) owed | |

_Phase 72 was never used. 56 / 62 / 68 are unscheduled TODOs with no phase directory — live tracking is in [STATE.md](STATE.md)._
