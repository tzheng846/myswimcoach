---
phase: 83-per-cycle-trace-coloring
plan: 02
subsystem: ui
tags: [react, svg, nextjs, tailwind-v4, numpy, supabase, signal-processing]

requires:
  - phase: 83-01
    provides: "web/lib/cycleBands.js (buildBands) + PhaseVelocity's `bands` prop — reused for kicks"
  - phase: 75-03
    provides: "metrics.detect_underwater_kicks + phase_metrics._kick_analysis (the peaks this plan draws)"
provides:
  - "metrics.segment_kick_bands — pure trough-to-trough per-downkick spans"
  - "phases.kick_bands — persisted per-kick segmentation, emitted by compute_phases"
  - "SCHEMA_VERSION 4"
  - "Underwater inset banded, badged and hover-readable in PhaseReportCard"
  - "tools/backfill_phases.py reports a kick-band count"
affects: [81-02, 83-03]

tech-stack:
  added: []
  patterns:
    - "Non-registry session data rides inside `phases` beside `boundaries`, so all three PhaseContext write sites get it from one change and it can never go stale against its own window"

key-files:
  created: []
  modified:
    - metrics.py
    - phase_metrics.py
    - tests/test_phase_metrics.py
    - web/components/portal/phases/PhaseReportCard.js
    - web/components/portal/phases/PhaseVelocity.js
    - tools/backfill_phases.py
    - PIPELINE.md

key-decisions:
  - "D5 REVERSED: kick bands live in `phases.kick_bands`, not top-level `metrics_json.kicks`"
  - "Kicks are auto-only — badge reads `auto` with no reliability flag until 81-02"
  - "Peak dot removed from the hero chart and all four insets (user direction, mid-verify)"

patterns-established:
  - "A new var()-only CSS token must go in `@theme static` — invisible to build and eslint otherwise"
  - "Backfill counters exist so a zero is visible rather than silent (75-06 precedent, extended to kick bands)"

duration: ~1 session
started: 2026-08-28
completed: 2026-08-28
---

# Phase 83 Plan 02: Per-Cycle Trace Coloring — Kicks Half

**Underwater downkicks are now drawn: `compute_phases` emits a persisted `phases.kick_bands` array (trough-to-trough between detected peaks, no new tuning constant), schema 3 → 4, and the Underwater inset renders it through 83-01's `buildBands` and `PhaseVelocity` with alternating bands, ticks, an outlier halo, an `N kicks · auto` badge and a hover readout. 63 of 81 non-breaststroke sessions carry bands library-wide.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 session |
| Completed | 2026-08-28 |
| Tasks | 6 of 6 (4 auto, 1 decision, 1 human-action, 1 human-verify) |
| Files modified | 7 |
| Python suite | 485 → **497 passing** (+12) |
| Web build | clean, 19 pages |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Bands derived trough-to-trough | **Pass** | Plain argmin between consecutive peaks; no new tuning constant. Synthetic 5-kick sine → 5 bands meeting at the minima, peak inside each. |
| AC-2: Degenerate underwaters → no bands | **Pass** | 0 peaks, 1 peak, reversed/empty window, peaks outside window, unsorted peaks, bad `fs`, and any non-finite velocity in the slice all yield `[]`. Never raises. |
| AC-3: Bands reach the browser from every write path | **Pass** | Verified against **stored** Supabase state, not just computed: 99/99 sessions at `schema_version` 4, **0** missing the `kick_bands` key. Riding inside `phases` means `PUT /annotations` re-derives via `_rebuild_phases` rather than carrying stale bands. |
| AC-4: Breaststroke gated off | **Pass (partial verify)** | Backend gate is test-covered (`compute_phases(breaststroke)["kick_bands"] == []`); the UI `pulldown · not kicks` label was **not** individually confirmed on a live breaststroke session. |
| AC-5: Rendered via 83-01 components, unmodified | **FAIL by the letter** | `web/lib/cycleBands.js` is genuinely unchanged and the bands do render through `buildBands`/`PhaseVelocity` with zero configuration. But `PhaseVelocity.js` **was** modified — user directed peak-dot removal mid-verify. Spirit met, letter not. See Deviations. |
| AC-6: Swimming and the rest un-regressed | **Pass** | Swimming bands/badge/hover/cross-highlight untouched; Start and Whole insets stay single-colour; suite 497 green. |
| AC-7: Library backfilled | **Pass** | User-run `--apply`. Verified: **63 of 81** non-breaststroke sessions carry bands (84/99 have a resolvable underwater window — matches STATE item 14's ~15 unresolvable). Non-zero, so not the 75-06 missed-write-site signature. |
| AC-8: Visual approval | **Pass with findings** | User reviewed the live portal and approved the apply outcome. Three findings raised → all routed to 83-03. |

## Accomplishments

- **`metrics.segment_kick_bands`** — pure, never raises, splits trough-to-trough at the plain argmin between consecutive peaks. Reuses `segment_cycles_trough`'s rule minus its prominence gate, which is redundant because the detector already prominence-filters the peaks. **No new tuning constant** (D4). Emits plain `int`/`float` only, because `_clean` is applied by callers *around* `compute_phases`, not inside it.
- **`phases.kick_bands`** emitted from `compute_phases` beside `boundaries`, reusing `_kick_analysis` rather than re-running the detector.
- **Underwater inset rendered** through 83-01's lib with zero configuration — `duration_s` was chosen deliberately so `buildBands`' default `durationKey` applies.
- **Backfill reporting gap closed** — the tool now prints a kick-band count against the non-breaststroke denominator.
- **12 new tests**, including a `json.dumps` round-trip that would catch a numpy leak end to end.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `metrics.py` | Modified | `segment_kick_bands` — pure trough-to-trough band derivation |
| `phase_metrics.py` | Modified | `_kick_bands(ctx)` helper + `kick_bands` in the `compute_phases` header; `SCHEMA_VERSION` 3 → 4 |
| `tests/test_phase_metrics.py` | Modified | 12 tests: segmentation, degenerate inputs, breaststroke gate, numpy/json round-trip, schema pin 3 → 4 |
| `web/components/portal/phases/PhaseReportCard.js` | Modified | `kickBands` memo, `hoverKick` state, `kickReadout`, bands prop, badge, breaststroke pulldown note |
| `web/components/portal/phases/PhaseVelocity.js` | Modified | **Deviation** — peak dot + its orphaned `argmax` helper removed (user direction) |
| `tools/backfill_phases.py` | Modified | **Deviation** — `with_kick_bands` / `kickable` counters so a zero is visible |
| `PIPELINE.md` | Modified | Documents `kick_bands`, schema 4, and why it lives inside `phases` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **CONTEXT D5 REVERSED** — bands live in `phases.kick_bands`, not top-level `metrics_json.kicks` | D5's premise ("`phases` is a pure metrics-registry payload") is factually incomplete: `phases` already carries `schema_version`, `go_signal_s` and `boundaries`. A top-level key needs writes at **all three** `PhaseContext` sites — the exact bug 75-06 shipped — and `PUT /annotations` would carry it forward **stale** against a window the coach just replaced. | One change instead of three; staleness impossible by construction. Cost: kicks are read from `phases.kick_bands` while cycles come from `metrics.cycles`, so the two band sources are addressed differently. 81-02 may want a coach-writable kick array outside the derived object. |
| Kicks are **auto-only**; badge omits any reliability half | No coach kick-marking path exists until 81-02. Reading `segmentationReliable` here would claim a provenance that does not exist. | Badge reads `N kicks · auto`. Do not add a reliability flag before 81-02 ships. |
| Peak dot removed everywhere (hero + all four insets) | User: "I don't see the use in that." | `argmax` deleted as an orphan. AC-5's zero-diff guarantee lost. |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Pre-applied work found | 2.5 tasks | None — verified against the plan and the decision |
| Scope additions | 2 | Both required by ACs the plan under-specified |
| Boundary override | 1 | User-directed |
| Deferred | 1 | Documentation-only, logged below |

**Total impact:** No scope creep. One boundary override, made explicitly by the user, recorded rather than absorbed.

### Pre-applied work

**Tasks 2 and 3 were already present in the working tree** at APPLY time — `segment_kick_bands`, `_kick_bands`, the emit site, `SCHEMA_VERSION = 4`, and all 12 tests — from a prior session that was cut off. They were read and verified to match the `in-phases` decision rather than trusted. **Task 4 was half-applied:** the `kickBands` / `hoverKick` / `hoverKickRow` memos and `kickReadout` existed but **nothing in the render read them** — dead code, so no band was ever drawn. Only the render wiring was written this session.

### Scope additions

**1. [Tooling] `tools/backfill_phases.py` gained a kick-band counter**
- **Found during:** Task 5 (backfill human-action)
- **Issue:** AC-7 requires "the run reports how many sessions got bands, so a zero is visible rather than silent." The tool reported `with_uw` and `with_cycles` but had no kick counter, so the checkpoint's own verification step was unsatisfiable as written.
- **Fix:** Added `with_kick_bands` / `kickable`, mirroring the existing `with_cycles` precedent and its comment. Counted against the **non-breaststroke** denominator, since breaststroke is gated off by design and is not a miss.
- **Note:** Task 3 forbade editing this file, but that prohibition was about *wiring the bands* (the three-write-site problem). A read-only diagnostic counter wires nothing.

**2. [Docs] `PIPELINE.md` updated**
- **Found during:** post-task verification
- **Issue:** listed in `files_modified` but no task body specified the edit; it still documented schema 3 against code at 4.
- **Fix:** Added a `kick_bands` bullet beside the `provisional` one, covering the derivation rule, the `[]` cases, and why the key lives inside `phases`.

### Boundary override

**`PhaseVelocity.js` modified — AC-5 and an explicit DO-NOT-CHANGE boundary.** During the human-verify the user asked for the peak dot to be removed ("I don't see the use in that"), and on a follow-up question chose **remove everywhere** over insets-only. The dot and its `argmax` helper are gone from the hero chart and all four insets. The plan said to stop and raise rather than edit that file; it was raised, and the user's direction superseded it. Recorded here rather than reported as AC-5 met.

### Deferred

- **`web/lib/cycleBands.js:9` carries a now-false comment** — it says 83-02 "passes `metrics_json.kicks` through it unmodified," the D5 shape this plan reversed. Left untouched deliberately: the file is under a DO-NOT-CHANGE boundary and AC-5 checks a zero-line diff on it. **Fix it in 83-03**, which modifies that file anyway.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Backfill tool could not satisfy its own checkpoint verification | Added the counter, then confirmed against **stored** Supabase state rather than trusting the dry run |
| `--apply` was run by the user *before* the counter existed, so its output could not be read back | Queried the live DB directly: 99/99 at schema 4, 0 missing the key, 63/81 with bands |
| Heredoc/CRLF mismatch when editing web files | Files are CRLF; edits made with universal-newline reads and CRLF writes |

## Findings for 83-03 (raised at human-verify)

1. **The gold/amber flag is not an abnormality test.** `buildBands` flags the single furthest-from-median duration with **no threshold**, so exactly one band is always gilded whenever ≥3 exist, however tight the spread. Nothing in the UI explains it.
2. **A single-dolphin-kick underwater stretches ~0.5 s across the full chart width** — unreadable. No minimum span exists.
3. **Every inset hard-clips to its own phase.** The user read the Swimming inset's grey lead-in as out-of-phase context; it is actually the band base trace showing un-segmented time *inside* the window. Context padding is genuinely new behaviour, not a consistency fix.

## Next Phase Readiness

**Ready:**
- Both halves of Phase 83's original scope now render: cycles (83-01) and kicks (83-02).
- `phases.kick_bands` is persisted library-wide and re-derives on annotation, so 83-03 needs no backend.

**Concerns:**
- ⚠ **Still uncommitted.** This stacks on 75-06, which shares `api.py` with 82-01. The next commit must take the whole tree — hunk staging is unavailable in this environment.
- AC-4's UI label and AC-5's letter are the two soft spots above.
- 75-03's known over-detection cases (`udk` alternating peaks, shallow-freestyle ripple) are now *visible*. Any wrong band count is a detector finding, not a rendering bug.

**Blockers:** None.

⚠ **Phase 83 does NOT transition here.** The plan/summary counts are now equal (2/2), which is exactly the heuristic that would wrongly call the phase done — the same trap flagged at 83-01. **83-03 is next** (inset legibility: context padding, minimum span, breakout gold, deviant red, hover explanation). No phase commit.

---
*Phase: 83-per-cycle-trace-coloring, Plan: 02*
*Completed: 2026-08-28*
