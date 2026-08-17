---
phase: 65-underwater-phase-detection
plan: 01
subsystem: signal-processing
tags: [segmentation, cwt-ridge, detect_swim_window, diagnosis, probe]
requires:
  - phase: 59-segmenter-evaluation
    provides: detect_swim_window, the CWT ridge, the per-stroke segmenter dispatch
  - phase: 66-acceleration-derivative
    provides: the smooth acceleration signal tested (inconclusively) as a discriminator
provides:
  - tools/underwater_probe.py (repeatable diagnostic, --id targeting)
  - 65-01-FINDINGS.md (root cause + the chosen 65-02 approach)
  - decision: 65-02 repairs detect_swim_window (Option A), not a new detector
affects: [65-02, 65-03]
tech-stack:
  added: []
  patterns: ["measure the real detector behaviour on stored profiles before writing a fix"]
key-files:
  created: [tools/underwater_probe.py, .paul/phases/65-underwater-phase-detection/65-01-FINDINGS.md]
  modified: []
key-decisions:
  - "Option A: repair detect_swim_window (fix the low-railed f_ref), NOT a new arm-pull detector"
  - "The reported bug is a broken f_ref inside detect_swim_window, not the trough fallback or a 2x harmonic"
patterns-established:
  - "underwater_probe.py --id <uuid> reaches sessions by id (generated names aren't stored)"
duration: ~1 session
started: 2026-08-16
completed: 2026-08-16
---

# Phase 65 Plan 01: Underwater Breakout Diagnosis Summary

**Measured why free/back/fly `ip_end` misfires and found the reported "dive + kicks as cycles" bug is
a broken `f_ref` INSIDE `detect_swim_window` (its CWT ridge rails to the low-frequency floor,
collapsing `ip_end` to `b_end`) — so 65-02 repairs `detect_swim_window` (Option A), not a new
detector.** Full detail: [65-01-FINDINGS.md](65-01-FINDINGS.md).

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Per-session boundary measurement | Pass | 12 annotated sessions (8 fly, 4 free, 0 back) + the reported session by `--id`; win result, fallback/final ip, f_ref, ridge, breakout, error all logged |
| AC-2: Root cause per stroke | Pass | THREE modes found; the reported one (Mode C) is `f_ref` railing low; D8 2×-harmonic **refuted** with numbers |
| AC-3: A single recommendation | Pass | Option A — repair `detect_swim_window` (frequency/ridge robustness); Option B refuted |

## Key Findings

- **Mode A (11/12, when `detect_swim_window` fires):** `ip_end` ~2 s LATE (median +2.1 s), 0 spurious
  cycles — the known 59-03 settle residual, not the reported bug.
- **Mode B (1/12, `None` → trough fallback):** early `ip_end`, 1 spurious cycle.
- **⭐ Mode C = the reported bug (indigo ray `6ececa0f`):** `detect_swim_window` fires but `f_ref` rails
  to **0.33 Hz** (real fly ~0.8–1.2 Hz), so `ip_end` collapses to `b_end` and the dive + kicks segment
  as **15 cycles**. The mechanism is a low-railed CWT ridge, not the fallback, not a 2× harmonic.
- **Discriminators:** velocity amplitude equal underwater vs surface (refuted); acceleration surge
  **dive-confounded → inconclusive**; frequency is the lever but must be made robust to the low rail.

## Decision Recorded

**Option A — `repair-swim-window`** (user-selected 2026-08-16). 65-02 will make `f_ref`/`_cwt_ridge`
robust to the low-frequency rail (reject an implausibly-low `f_ref` and re-estimate, or constrain the
ridge's low-band bias), keeping a valid `ip_end` rather than falling back (the trough fallback is
16.6 s on indigo ray — worse). Mode A late-settle + Mode B fallback-early are milder residuals to
address second.

## Deviations from Plan

| Type | Item | Rationale |
|------|------|-----------|
| Added capability | `--id <uuid>` on the probe | "indigo ray" is a generated display name, not a stored `sessions.name`, so it was unreachable by name — the exact gap that led to ROADMAP TODO #67 |
| Premise refuted | The plan assumed `ip_end` lands EARLY | Measured: it's ~2 s LATE when the detector fires; the reported early/kicks mode is Mode C (railed `f_ref`), a third mechanism |
| Inconclusive measurement | The accel-surge discriminator | Confounded by the dive block-push transient; a clean kick-only test needs the breakout we're detecting |
| Ground truth | 0 backstroke measured | Backstroke has no annotations (n=0), as in Phase 59 |

## Files

| File | Change | Purpose |
|------|--------|---------|
| `tools/underwater_probe.py` | Created | Repeatable diagnostic; `--id` targeting; read-only |
| `.paul/phases/65-underwater-phase-detection/65-01-FINDINGS.md` | Created | Root cause + the Option A decision (65-02's input) |

No production code, schema, or stored data touched.

## Next Phase Readiness

**Ready:** 65-02 can be written from FINDINGS without re-measuring — Option A, targeting the low-railed
`f_ref` in `detect_swim_window`.
**Concern:** n is still tiny (12 + 1 sessions, one swimmer, 0 backstroke); the Mode C fix must be
verified not to regress the 11/12 Mode-A sessions that work today.
**Also surfaced:** ROADMAP #68 (persist generated session names) — unrelated product to-do (#67 is
the separately-appearing external-camera-sync phase).

---
*Phase: 65-underwater-phase-detection, Plan: 01 — Completed 2026-08-16*
