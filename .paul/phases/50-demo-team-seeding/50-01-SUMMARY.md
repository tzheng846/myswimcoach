---
phase: 50-demo-team-seeding
plan: 01
subsystem: tooling
tags: [demo, seeding, supabase, service-role, pipeline-replay]
requires: []
provides:
  - seed_demo_team.py (demo-team seeder — real CSVs through the real pipeline, backdated)
  - DEMO_ROSTER (12 athletes, 8 breaststroke / 4 freestyle, story-beat trajectories)
  - TIMELINE config (clustered test weeks, consumed by 50-02)
  - time_warp_bytes (invertible warp — the mechanism 50-02 uses to propagate annotations)
affects:
  - 50-02 (generate ~144 sessions + propagate the 12 archetype annotations)
  - 16-06 (the 12 hand-annotations double as segmenter-tuning ground truth)
tech-stack:
  added: [python-dotenv (dev only)]
  patterns: ["replay REAL raw CSVs through vae.run_pipeline + m.compute_session_metrics so rows are
    shape-identical to POST /process output — zero product code changes downstream"]
key-files:
  created: [seed_demo_team.py]
  modified: []
key-decisions:
  - "Backdate created_at explicitly — api.py orders by it in 6 places and the whole portal sorts on it"
  - "Perturb via an INVERTIBLE time warp, so 50-02 can propagate archetype annotations exactly
     instead of requiring ~144 hand-annotations (saves 7-14 h of clicking)"
  - "Service-role writes, every one explicitly scoped to the resolved demo team_id (RLS bypassed)"
duration: unknown (retroactive summary)
completed: PARTIAL — see status below
---

# Phase 50 Plan 01: Demo Team Seeder Summary

**Built the seeder that gives the demo a believable six-month training history: it replays real raw
encoder CSVs from `raw/` through the real production pipeline and writes session rows shaped exactly
like `POST /process` writes them, with backdated `created_at`.**

> ⚠ **This summary was first written retroactively (2026-07-30) by a session that could not see the
> apply run.** It has since been RECONCILED against the actual apply session, which resolves every
> "unknown" below. Two corrections to the original retroactive read:
>
> - **The script is not rogue work.** The user explicitly approved APPLY (STATE's stale
>   "DO NOT APPLY" line predated the approval). T1, T2 and T4's code were built and verified in
>   that approved run.
> - **Stage 1 definitively did NOT run.** Execution stopped at the T3 human gate: no demo coach
>   email was ever supplied, and the apply environment additionally had no network (DNS to the
>   Supabase host failed), so no write could have reached the DB even accidentally.

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| All 4 tasks complete | ◐ **PARTIAL — stopped at the T3 gate** | T1 seeder core ✅ verified, T2 roster + timeline ✅ verified, T4 stage1 **code** ✅ (written early, not run). **T3 OPEN** — user never supplied the demo coach email |
| Demo team contains 12 athletes × 1 archetype session, backdated | ❌ **NOT DONE** | Never ran. No demo account existed and the apply env had no network |
| Seeder re-runnable (`--wipe` then `--stage1`) | ✅ PASS (by inspection) | Both flags implemented plus `--validate` and `--dry-run`. The write paths remain **unexercised against a live DB** |
| No product code, schema, or web changes | ✅ PASS | Single new standalone script + `python-dotenv` → `requirements-dev.txt`. `pytest tests/` = **149 passed**, unchanged |
| The 12 sessions are annotatable at `/app/annotate/[id]` | ❌ **BLOCKED** | Requires Stage 1 to have run. This is 50-02's entry gate |

## Verified during the apply run (offline)
- `--help` exits 0 with all five flags; module parses.
- `--validate` → **24 of 43** raw CSVs usable as archetypes (≥4 cycles, ≤15% dropout). Known-bad
  files fail gracefully with reasons (sub-2 s recordings, 0-cycle traces, 48–68% dropout, two
  `IndexError` empties) rather than crashing the pass.
- Roster invariants: 12 unique names, 8 br / 4 fr, all archetype files exist, no two athletes share
  the same (source, warp) pair. Trajectories = 2 strong_improver / 6 steady_improver /
  1 regression_recovery / 2 needs_attention / 1 plateau.
- Row shape matches the `/process` contract: `metrics_json` has exactly
  `{session, cycles, initial_phase, data_quality}`, `data_quality` has exactly the six keys
  api.py builds, profiles are equal-length, and the payload survives
  `json.dumps(..., allow_nan=False)` — NaN would have made Postgres reject the insert.
- `time_warp_bytes` scales real duration by exactly the warp factor across 4 source files.
- Unreachable-Supabase now exits with one clear line instead of a 40-line traceback.

## Accomplishments (by source inspection)
- **`seed_demo_team.py`** — argparse CLI (`--coach-email`, `--validate`, `--stage1`, `--wipe`,
  `--dry-run`), service-role client, `resolve_demo_target` (scopes every write to the demo team).
- **`process_csv` / `ingest_csv`** — mirror the `/process` path: real pipeline, `_clean` for NaN,
  `_magnet_dropout_pct`, explicit backdated `created_at`, raw CSV uploaded to Storage (keeps
  annotate-recompute and `/export` working).
- **`DEMO_ROSTER`** — 12 athletes: 8 breaststroke + 4 freestyle (revised down from "all four
  strokes" because `raw/` has zero backstroke and only 2 usable fly recordings). Each carries a
  story-beat trajectory: `strong_improver`, `steady_improver`, `regression_recovery`, `plateau`,
  `needs_attention`.
- **`TIMELINE`** — 6 test weeks × 2 sessions = 12 per athlete over 6 months, clustered 21-28 days
  apart with jitter and a 12% skip probability, so "last tested" reads naturally rather than
  metronomically.
- **`time_warp_bytes`** — the invertible perturbation. This is the load-bearing trick: because the
  seeder chooses the warp, 50-02 can map the 12 hand-annotations onto all ~144 derivatives exactly.

## ⚠ Important findings

1. **`seed_demo_team.py` is UNTRACKED in git.** 565 lines of unversioned work, and the only copy.
   Commit it.

2. **The device_id landmine in the plan is now void.** 50-01 was written to force `device_id = NULL`
   because the live column was UUID (Phase-45 22P02). That column is now TEXT, so the constraint no
   longer applies. Harmless as-is — but don't let a future reader treat it as a live restriction.
   **Actioned 2026-07-30:** the stale rationale was corrected in `seed_demo_team.py`, `50-01-PLAN.md`
   and `CONTEXT.md`. The field stays NULL, but now for the honest reason — demo sessions aren't tied
   to a physical encoder, and the roster decision excluded a fake device row.

5. **⚠ NEW — the stored profiles are NOT 100 Hz, and shipped Phase-47 code assumes they are.**
   `run_pipeline` decimates by an *integer* factor: native ~268.5 Hz ÷ 3 = **89.51 Hz**. Metrics are
   computed on the true `t_dec` clock and are correct, but the stored `velocity_profile` is consumed
   as if it were exactly 100 Hz by `annotations.py` (`FS_HZ = 100`) and by api.py's annotation
   recompute (`t_arr = np.arange(size) / annot.FS_HZ`). Consequences on REAL sessions, not just demo
   data: the annotate page displays a 47.1 s swim as 42.2 s, and **recomputing metrics from a saved
   annotation shifts every time-derived metric by ~11.7%** (stroke rate, velocities, lap time).
   Found while mirroring `/process`; NOT fixed here — `annotations.py` and `api.py` are outside this
   plan's boundaries, and per the plan a discrepancy gets reported, not patched. **Deserves its own
   phase, and it should probably precede 50-02.**

6. **A useful corollary of #5 for 50-02.** A pure time warp changes `actual_fs` but *not* the sample
   count (2134 → 2134; occasional ±1). So annotation marks are effectively **identity in index
   space** between an archetype and its warped derivatives — propagation is closer to a copy than a
   remapping. Confirm this still holds once amplitude perturbation is added.

7. **The warp scales velocity amplitude without changing trace shape.** Two athletes sharing a
   source with different warps get visually similar traces. Acceptable for two different athletes'
   baseline sessions, but worth avoiding putting `Jonah Okafor` and `Elena Vargas` (or
   `Marcus Delaney` and `Hana Kirchner`) side by side in Compare during a pitch.

3. **Confirm before planning 50-02.** Whether Stage 1 ran determines whether the next action is
   "run the seeder" or "annotate the 12 archetypes." Check the demo coach account in the portal:
   12 athletes, one session each, dated ~6 months back.

4. **The human gate is the real schedule risk.** 50-02 cannot start until you hand-annotate 12
   archetype sessions at `/app/annotate/[id]` (~1 h). Everything downstream — 144 sessions,
   propagated annotations, and 16-06's ground-truth set — waits on that hour.

## Deviations from Plan
Recovered from the apply session:

1. **Task 4 was coded before the T3 checkpoint, not after.** The plan ordered T3 (signup) → T4
   (implement + run). The code was written first so that resuming needs only one command. No
   behavioural difference; the gate still blocked the run.
2. **`ingest_csv` gained a `warp` parameter and now returns `(session_id, n_cycles)`.** The first
   version ignored the roster's `warp` field entirely and re-ran the whole pipeline a second time
   just to count cycles for the summary table. Both were defects, caught and fixed in-session.
3. **`time_warp_bytes` had to drop unparseable rows.** `leo3.csv` contains 9 rows (of 12,647) with a
   blank `timestamp_us` — real logger corruption. `load_data` silently drops these downstream, so the
   warp now does the same instead of dying on `float('')`.
4. **Added a clean exit when Supabase is unreachable.** Not in the plan; a connection failure
   produced a 40-line traceback from a tool the user runs by hand.
5. **Plan verification command needed adjusting.** `open(...)` for the AST check defaults to cp1252
   on this machine and choked on the file's UTF-8 box characters; the check needs
   `encoding='utf-8'`. The plan's literal command as written fails for an unrelated reason.

## Next Phase Readiness
**50-01 is not finished. The next action is the T3 gate, not 50-02.**

1. Sign up the demo coach account, then run
   `python seed_demo_team.py --coach-email <demo> --stage1` from a machine with network access
   (the apply environment had none). Its write paths have never touched a live DB — expect to
   debug the first run.
2. **Commit `seed_demo_team.py`** — still untracked, still the only copy.
3. Consider fixing finding #5 (the 89.51 Hz vs 100 Hz assumption) BEFORE 50-02, since 50-02's whole
   annotation-propagation mechanism sits on top of that clock.
4. Then hand-annotate the 12 archetypes → 50-02's entry gate.

---
*Phase: 50-demo-team-seeding, Plan: 01*
*Summary written retroactively 2026-07-30 — run status unverified*
