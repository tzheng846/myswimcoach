---
phase: 75-report-card-phase-model
plan: 06
subsystem: metrics
tags: [phase-metrics, race-phase, report-card, annotations, backfill, nextjs, pytest]

requires:
  - phase: 75-01
    provides: MetricSpec registry + metrics_json.phases jsonb + compute_phases engine
  - phase: 75-05
    provides: RangeStrip / phaseBaseline / DIRECTION_OF_GOOD rendering seam
  - phase: 75-07
    provides: PhaseReportCard as the primary /app/sessions/[id] body
provides:
  - 23 implemented Swim + Whole registry metrics (registry 37 -> 47 specs)
  - PhaseContext.cycles + segmentation_reliable (the per-cycle annotations-first seam)
  - per-metric `provisional` flag (schema_version 2 -> 3)
  - PUT /annotations no longer destroys metrics_json.phases
  - four complete phase sections on the report card
affects: [75-08, 75-09, 80-stroke-cycle-segmentation, iOS report card]

tech-stack:
  added: []
  patterns:
    - "Vector metrics register as N scalar specs, never list-valued (baseline lookup is by key across history)"
    - "needs_cycles on MetricSpec -> emitted `provisional` -> valence forced neutral in the UI"
    - "Every PhaseContext construction site must thread cycles; there are THREE, not two"

key-files:
  created: []
  modified:
    - phase_metrics.py
    - api.py
    - tools/backfill_phases.py
    - web/components/portal/phases/PhaseReportCard.js
    - web/lib/phaseValence.js
    - tests/test_phase_metrics.py
    - tests/test_annotations.py
    - PIPELINE.md
    - .paul/PROJECT.md

key-decisions:
  - "D7: vector metrics -> N scalar registry specs (list indices would misalign across a session's history)"
  - "D8: provisional flag suppresses valence rather than hiding the metric"
  - "D11: breathing_dip DELETED, not deferred — the encoder cannot observe breaths"
  - "PUT /annotations rebuilds phases unconditionally, so a boundaries-only annotation still promotes its marks to manual"

patterns-established:
  - "A metric that reads ctx.cycles declares needs_cycles=True and inherits provenance reporting for free"
  - "Backfill tooling reports per-family coverage so a silent zero is visible in its own output"

duration: ~1 session
completed: 2026-08-28
---

# Phase 75 Plan 06: Swim + Whole Metrics Summary

**The race-phase registry is complete: 23 Swim and Whole metrics implemented, rendered as the report card's last two sections, computed from the coach's annotated stroke cycles where they exist and the auto segmenter's where they don't — verified across the stored library at 43 trusted / 44 provisional.**

## Performance

| Metric | Value |
|--------|-------|
| Tasks | 3 auto + 2 checkpoints (1 approved by action, 1 not run) |
| Test suite | 447 → **485** (+38) |
| Registry specs | 37 → **47** |
| Files modified | 9 (4 code, 2 test, 3 doc) |
| Library backfilled | **99 sessions**, all `schema_version: 3`, 0 stale keys |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Swim + Whole compute from stored profiles | **Pass** | 97/99 stored sessions carry `ivv`/`breakout_vel`/`accel_asymmetry`; unavailable inputs yield `null`, never NaN or a raise |
| AC-2: Per-cycle metrics prefer annotated cycles | **Pass** | Stored audit: `dead_spot_timing` = **43 TRUSTED (coach cycles) / 44 provisional**, exactly matching the 43 sessions with `segmentation_reliable=True` |
| AC-3: Annotating no longer destroys phase metrics | **Pass** | `TestPhasesSurviveAnnotation` (4 tests): `go_signal_s` + `phases` survive, boundaries rebuild as `manual`, provisional clears, rebuild failure never loses the annotation |
| AC-4: Four complete phase sections | **Pass (build)** / **owed (visual)** | `grep ComingSoon` → 0 matches; build clean. Visual confirmation is AC-7, not run |
| AC-5: Provenance + provisional in hover | **Pass (code)** / **owed (visual)** | `windowSourceNote` + `PROVISIONAL_NOTE` wired into `metricExplain`; verdict forced neutral when provisional |
| AC-6: No regression | **Pass** | 485 tests green; `npm run build` compiles clean, 19 routes, zero warnings |
| AC-7: Coach-visible verification | **NOT RUN** | Portal is Supabase-auth-gated; user moved to UNIFY without it. **Owed** — same posture as 81-01 |
| AC-8: Stored library carries the metrics | **Pass** | Two backfill runs; final audit below |

## What shipped

**Backend — `phase_metrics.py`**
- `PhaseContext` gained `cycles` + `segmentation_reliable`; `MetricSpec` gained `needs_cycles`.
- 23 compute functions across two new sections. Swim: `ivv`, `breakout_vel`, `breakout_vel_loss`,
  `breakout_vs_steady`, `splits_{5,10,15,20,25}m`, `accel_asymmetry`, `sr_dps_coupling`,
  `dead_spot_timing`. Whole: `phase_{time,dist}_budget_{start,underwater,swim}`,
  `vel_envelope_{start,underwater,swim,overall}`, `jerk_smoothness`.
- `compute_phases` emits `provisional` per metric; `SCHEMA_VERSION` 2 → 3.
- `breathing_dip` removed with a comment recording why it is unbuildable, not deferred.

**Backend — `api.py`**
- Cycles threaded at `/process` and `_rebuild_phases`.
- `PUT /annotations` merges onto the stored `metrics_json` instead of replacing it, then rebuilds
  `phases` — closing the defect where annotating a session erased its entire phase object.

**Frontend**
- `SECTIONS` gained `swim` (strips above `CycleCharts`) and `whole` (full-trace inset).
- 23 `DISPLAY` entries authored; `DIRECTION_OF_GOOD` updated to the per-element keys.
- Hover overlay now states window provenance and provisional status. No standing chrome added.

## Stored-library audit (post-backfill)

| Group | Coverage / 99 | Note |
|---|---|---|
| Start (closes the never-run 75-04 backfill) | 95–97 | `streamline_drag` 0 (planned), `reaction_time` 0 |
| Swim window metrics | 97 | |
| `splits_5m` → `splits_20m` | 93 → 56 | Declines with swim length, as expected |
| `splits_25m` | **2** | Waist-tether geometry — see Discoveries |
| `sr_dps_coupling` / `dead_spot_timing` | 77 / 87 | Of 90 sessions that have stored cycles |
| Whole race | 84–98 | Underwater-dependent members sit at 84 |

Boundary sources: `dive_start_s` manual 44 / detected 25 / auto 30; `underwater_start_s` manual 43 /
detected 54 / none 2. Manual precedence confirmed on real data.

## Deviations from plan

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 4 | Essential; two were silent data-loss bugs |
| Scope additions | 2 | User-requested mid-apply (domain docs) |
| Deferred | 4 | Listed below |

### Auto-fixed

**1. `tools/backfill_phases.py` was a THIRD `PhaseContext` construction site.**
Found by auditing the stored data after the user's first backfill run: `sr_dps_coupling` and
`dead_spot_timing` were **0/99** despite computing correctly in tests. The plan said "thread cycles
through both call sites", meaning `api.py`'s two — but the backfill tool builds its own context and
is the one that populates the library. Fixed; re-run gave 77/99 and 87/99. **The lesson is in the
patterns block above: there are three sites, not two.** Also added a per-cycle coverage line to the
tool's summary so a zero like this is visible in its own output rather than needing a separate audit.

**2. Same tool hardcoded `go_signal_s=None`,** which would null `reaction_time` on any session with a
GO time stored. Zero sessions have one today, so nothing was lost; it now reads the stored value like
`_rebuild_phases` does.

**3. `acceleration_profile` was missing from `put_annotations`' column select.**
`_rebuild_phases` treats a missing profile as "pre-Phase-64 session", so without adding it every
annotated session would have silently nulled its `max_accel`, `accel_asymmetry` and `jerk_smoothness`.

**4. `jerk_smoothness` unit corrected** from the 75-01 placeholder `"ratio"` to `"m/s³"`. The UI
overrides units for display, but the stored value is read by other consumers.

### Behavior change beyond the plan

`PUT /annotations` now rebuilds `phases` **unconditionally**, not only when a cycle recompute fires.
Rationale: a boundaries-only annotation (marks placed, too few for cycles) must still promote those
boundaries to `source: "manual"`. This overturned an existing assertion
(`test_too_few_boundaries_saves_without_recompute` asserted no write happened at all); that test was
updated to the new contract, and two others were switched from `update.call_args` to a positional
helper because the endpoint now issues two writes.

### Scope additions (user-requested, 2026-08-28)

Two apparatus facts were recorded in `.paul/PROJECT.md` (Constraints) and `PIPELINE.md`
(sensor intro + `finish_s` callout), plus a memory entry:
- **The tether is waist-mounted**, so `dist_m` runs ~1 m short of wall-to-wall; a 25-yard lap records
  only ~21.9 m of travel. This is geometry, not miscalibration.
- **`finish_s` correctly precedes zero velocity** — swimmers drift into the wall after touching.

The first directly explains `splits_25m` at 2/99 and retro-justifies the tail-trimming in
`breakout_vs_steady`. `splits_25m`'s hover text now explains the geometry instead of showing a dash.

### Tests placed differently

Plan said `tests/test_api.py`; the annotation-endpoint tests live in `tests/test_annotations.py`, so
they went there.

## Discoveries worth carrying forward

1. **`splits_25m` is structurally unfillable on a 25-yard pool** (2/99). Open question for the user:
   are 5/10/15/20/25 m the right split points for a waist-tethered rig, or should they be four
   splits, or yardage-based? Not changed unilaterally.
2. **~15 sessions have an unresolvable underwater window** (the 84/99 ceiling on every
   underwater-dependent metric). Pre-existing, unrelated to this plan — but it is the reason a coach
   can open a session and find the whole Underwater panel blank with no inset. Candidate for its own pass.
3. **`reaction_time` is 0/99 because no session has a GO signal at all.** The endpoint shipped in
   75-04; the coach GO button never did. The metric cannot fill until it does.
4. **The report card renders stored keys, not registry keys.** Until the backfill ran, the page showed
   the *old* labels ("Split velocities", "Breathing-stroke velocity dip") because it iterates the
   stored `phases` object. Any future registry rename needs a backfill in the same breath.

## Deferred

- **AC-7 human-verify** — owed against a live session; especially the ~23-row panel length judgment.
- **Split distances vs. tether geometry** — user decision (Discovery 1).
- **Unresolvable underwater windows on ~15 sessions** (Discovery 2).
- **`streamline_drag`** — still the only `planned` spec.

## Uncommitted

**Nothing in this plan is committed.** `api.py` and `tests/test_api.py` also carry **Phase 82-01's**
session-delete storage cleanup, which was applied but never committed, so `api.py` now holds two
plans' changes. Splitting them needs hunk-level staging — flagged for the user rather than committing
a mixed history.

## Next Phase Readiness

**Ready:** The registry is complete except `streamline_drag`. The `provisional` flag and
`boundaries.sources` are both live and rendered, giving 75-08's compare-window work a trustworthy
per-metric provenance signal. Phase 80 now has a direct payoff: fixing the cycle count upgrades 44
provisional sessions to trusted without any further code.

**Concerns:** AC-7 unverified. Phase 75 is NOT complete — 75-08 and 75-09 remain (the plan/summary
file counts match only because those plans aren't written yet; do not let that trigger a phase
transition).

**Blockers:** None.

---
*Phase: 75-report-card-phase-model, Plan: 06*
*Completed: 2026-08-28*
