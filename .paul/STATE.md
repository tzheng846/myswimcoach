# Project State

*Lean current-state snapshot — updated as work lands. How the pipeline **works** lives in
[PIPELINE.md](../PIPELINE.md) (repo root); the phase index in [ROADMAP.md](ROADMAP.md); the data map
in [DATA-FLOW.md](../DATA-FLOW.md). The full pre-2026-08-20 running log (4,905 lines) is archived at
[.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md).*

## Current Position

- **Milestone:** v0.5 Commercial Foundation
- **Arc:** Race-phase report-card model (Phases 75–77) — segment the 4 phase boundaries, then compute
  per-phase metrics, then build the UI.
- **Phase 77** (fly breakout) — closed + committed (`d6e00c8`, `0ff29e7`).
- **Phase 76** (free/back breakout) — closed + committed (`046b8d1`).
- **Phase 75-03** (7 underwater kick metrics) — **APPLIED, uncommitted, eyeball checkpoint NOT run.**
- **Phase 75 Step 3** (report-card UI) — not started. Nothing from Phase 75 is visible in any UI yet.
- **Working tree:** `phase_metrics.py` + `tests/test_phase_metrics.py` dirty (= 75-03). `ESP_32_V5.ino`
  + `assets/icon/` also dirty/untracked — **unrelated to this arc; confirm before committing.**

## Segmentation status — the 4 phase boundaries
Mechanisms in [PIPELINE.md §3](../PIPELINE.md).

| Boundary | State |
|---|---|
| `dive_start_s` | ⚠ motion-onset (`baseline_end`) — **known defect + active fix, item 1** |
| `underwater_start_s` | ✅ `detect_underwater_start`, median 0.13 s |
| `stroke_start_s` (breakout) | ✅ free/back 0.42 s · fly 0.38 s · ⚠ **breaststroke = incumbent, untuned** |
| `finish_s` | inherited (`detect_swim_window`) |

## Owed / next actions (priority order)

**1. ⭐ ACTIVE — Redefine `dive_start_s` (first velocity peak ≥ 2 m/s).**
Current: `dive_start_s = session.baseline_end_s` ([annotations.py:119](../annotations.py)); `baseline_end`
([metrics.py:51](../metrics.py) `detect_phases`) is the first point the rolling mean of |vel| holds above
`_BASELINE_THRESH` (a low floor) for 0.5 s = **motion onset**. Defect: at the start the swimmer jumps and
sinks, tugging the line below true dive speed; the low threshold trips on that artifact → `dive_start`
fires early. Intended rule (user, 2026-08-20): **the first velocity peak ≥ 2 m/s** — the tug never
reaches it, a real dive/push-off does. ⚠ Open caveat: a weak wall push-off may not reach 2 m/s → decide
the fallback (null? lower floor for push-off starts?). Changing `dive_start` shifts a stored boundary →
comparability break + backfill. Verify against the multi-swimmer data in item 2.

**2. ⭐ ACTIVE — Reconcile the "one swimmer" validation claim.**
The Phase 76/77 records call their breakout scoring corpus *"one swimmer,"* but labeled data exists for
**Tony, Leo, Titus, and AlexGroup** (a stand-in athlete whose session-ids are individual testers' names).
Resolve which is true: **(a)** the claim is wrong — the ~16 free / 17 fly annotated sessions already span
multiple swimmers (then just delete the caveat); or **(b)** the detectors were fit on a one-swimmer
subset while more labeled data went unused (then re-score against the fuller corpus and re-tune
constants if needed). Method: point `tools/breakout_band_probe.py` / `tools/score_underwater.py` at the
DB (read-only, service-role key) to print distinct athlete_ids per stroke. Update [PIPELINE.md §8](../PIPELINE.md)
with the resolved count.

**3. Close out 75-03.** Run the eyeball checkpoint (AC-4): `python tools/plot_kicks.py` on live DB
sessions → confirm the marked peaks are the kicks a coach would count. Then commit + write
`75-03-SUMMARY.md`. Registry: the 7 kick specs are already flipped to `implemented` in the working tree.

**4. Fix `tools/breakout_band_probe.py` (DEFER-77-A).** The probe plots the exploratory/rejected
detector, not the shipped one — 3 defects, one root cause. Defect (a): `:270` passes `cand_idx` (the
probe's own `_detect_breakout`) to `_plot` instead of `ship_idx`, so even the freestyle plots draw a
detector materially different from production. **This blocks Phase 76's owed AC-4** (item 5). Fix (a)
before item 5, all three before the next breakout human-verify. Detail in
[77-01-SUMMARY.md](phases/77-fly-breakout-detection/77-01-SUMMARY.md) DEFER-77-A.

**5. Run Phase 76's AC-4 eyeball.** Never run — both 76 corrections were found by measurement, not the
checkpoint. Needs item 4(a) first.

**6. Backfills (USER runs — Claude is blocked from prod writes).** 76/77's new `stroke_start` boundaries
and 75-03's kick metrics create comparability breaks vs stored sessions. Re-run
`python tools/backfill_phases.py --apply` after the eyeball approvals. Standing pattern (57 / 59-03 /
61-01 / 65).

**7. Remaining Step-2 metrics — one at a time, approval-gated** ([phase_metrics.REGISTRY](../phase_metrics.py)):
Start (11 — incl. `reaction_time`, which needs the coach GO-button + phone↔encoder clock sync), Swim
(9 — IVV, breakout velocity, splits, dead-spot; mostly cheap), Whole race (4).

**8. Step-3 UI.** Phase-organized web report card (Start / Underwater / Swim, breakout marked in Swim),
then iOS. Display doctrine = within-athlete contrast / trend, **no absolute thresholds**.

## Recent arc (compressed)
- **75-01** skeleton — `MetricSpec` registry (37 specs) + `metrics_json.phases` jsonb + `POST /sessions/{id}/recompute` backfill seam.
- **75-02** — `detect_underwater_start` + 4 underwater window metrics; backfilled all 108 sessions.
- **75-03** (applied) — `detect_underwater_kicks` + 7 kick metrics.
- **76** — free/back breakout by kick-band **disappearance**.
- **77** — fly breakout by arm-cycle **appearance**.

## Pointers
- **How it works:** [PIPELINE.md](../PIPELINE.md) — signal, phase model, detectors, metrics registry
- **Phase index / milestones:** [ROADMAP.md](ROADMAP.md)
- **Data map (stores, endpoints, jsonb):** [DATA-FLOW.md](../DATA-FLOW.md)
- **Requirements / product intent:** [PROJECT.md](PROJECT.md)
- **Full historical log:** [.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md)
