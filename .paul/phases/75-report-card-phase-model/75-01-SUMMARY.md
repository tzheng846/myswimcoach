# 75-01 SUMMARY — Report Card Phase Model: Skeleton / Integration

**Plan:** [75-01-PLAN.md](75-01-PLAN.md) · **Status:** Complete · **Date:** 2026-08-19

## What shipped

Step 1 of the CONTEXT's 3-step, backend-first resequencing (D11). Pure "define + provide
space" — **zero metrics implemented**, confirmed by test assertion (`test_all_specs_planned_with_no_compute_fn`).

1. **`phase_metrics.py`** (new, pure module, no I/O) — `MetricSpec` (frozen dataclass,
   validates phase/tier/status/compute-consistency in `__post_init__`), `PhaseContext`
   (the compute-fn seam: t/vel/dist/accel/fs/stroke_type/go_signal_s), a 37-entry
   `REGISTRY` covering the full CONTEXT taxonomy (11 start, 13 underwater, 9 swim,
   4 whole), all `status="planned"`/`compute=None`, and `compute_phases(ctx)` — the
   engine that partitions the registry into the 4 phase buckets, never raises (a
   raising `compute` fn degrades that one metric to `value: None`).
2. **`api.py` `/process`** — additive `phases` object (built via
   `pm.compute_phases(pm.PhaseContext(...))`) written into both the stored
   `metrics_json` and the JSON response. `go_signal_s` stays `None` (no GO button
   yet). Every existing `metrics_json` key (`session`/`cycles`/`initial_phase`/
   `data_quality`) is untouched — same line count, same values.
3. **`api.py` `POST /sessions/{id}/recompute`** (new endpoint, inserted after
   `DELETE /annotations`) — the D16 backfill seam. Reads
   `velocity_profile`/`distance_profile`/`acceleration_profile`/`sample_rate_hz`/
   `stroke_type` via the existing `_owned_session` helper (403/404 for free),
   rebuilds `phases` from the **stored** profiles (no raw-CSV read), merges it into
   `metrics_json` (`{**old_mj, "phases": phases}` — every other key preserved
   verbatim), writes, and returns. 422 on missing/mismatched profiles. Idempotent by
   construction (always derives fresh, never accumulates).

## Interpretation calls made (flagged in the plan, now confirmed by implementation)

- **GO-signal reserved inside `metrics_json.phases.go_signal_s`, not a new column.**
  Read D15 ("no migration") as ruling out a `sessions.go_signal_s` column too — the
  jsonb slot is the migration-free reading. If a future session wants it queryable at
  the SQL level, that's a deliberate `patch_XX` decision, not something this plan
  assumed.
- **Tier assignment (low/medium/high)** for each of the 37 metrics was my judgment call
  from the CONTEXT's ✅/🟡/🔶 tags (✅/🟡 → low/medium, 🔶 → high), not a value re-derived
  from anywhere else. Re-rankable in Step 2 per the plan's own note — getting a tier
  "slightly wrong" here costs nothing since no metric is implemented yet.

## Registry key list (for 75-02 to pick the first metric from)

**start** (11): `peak_vel`, `time_to_peak_vel`, `max_accel`, `dive_duration`,
`glide_duration`, `glide_distance`, `glide_avg_speed`, `glide_decel`,
`streamline_drag`, `break_into_kick_vel`, `reaction_time`

**underwater** (13): `uw_duration`, `uw_distance`, `uw_avg_speed`, `uw_surface_ratio`,
`kick_count`, `dist_per_kick`, `kick_tempo`, `kick_consistency`, `uw_ivv`,
`per_kick_decay`, `first_kick_impulse`, `pulldown_peak_vel`, `pulldown_duration`

**swim** (9): `ivv`, `breakout_vel`, `breakout_vel_loss`, `breakout_vs_steady`,
`splits`, `sr_dps_coupling`, `dead_spot_timing`, `accel_asymmetry`, `breathing_dip`

**whole** (4): `phase_time_budget`, `phase_dist_budget`, `vel_envelope`,
`jerk_smoothness`

Per the CONTEXT's open-call-1, the "cheap, ship first" candidates (boundaries/data
already exist, no new detector) are: `uw_duration`, `uw_distance`, `uw_avg_speed`,
`uw_surface_ratio`, `ivv` (per-cycle slices already exist), `breakout_vel`,
`phase_time_budget`, `phase_dist_budget`, `splits`, `pulldown_peak_vel` /
`pulldown_duration` (already-computed values, just not yet mapped into the registry).

## Verification

- `pytest tests/test_phase_metrics.py tests/test_recompute.py tests/test_api.py -q` →
  17 + 8 + 68 = 93 passed (17 new phase_metrics tests, 8 new recompute tests, 4 new +
  all pre-existing test_api.py assertions).
- `pytest tests/ -q` → **317 passed**, full suite, zero failures.
- `python -c "import phase_metrics, api"` → clean, no circular import.
- Additive-only proof: `test_phases_addition_does_not_disturb_existing_session_dict`
  plus every pre-existing `test_api.py`/`test_annotations.py` assertion still passes
  unchanged.

## Files touched (matches plan `files_modified` exactly)

`phase_metrics.py` (new), `api.py` (+68/-1: import + phases computation + `/process`
wiring + new `/recompute` endpoint), `tests/test_phase_metrics.py` (new, 17 tests),
`tests/test_recompute.py` (new, 8 tests), `tests/test_api.py` (+34: `phases` in
`RESPONSE_TOP_KEYS` + `TestPhaseMetricsScaffold`).

## Boundaries held

No changes to `metrics.py`, `vel_acc_extraction.py`, `annotations.py`, `ratings.py`,
`supabase/`, `web/`, or the mobile repo. No schema migration. **No metric was
implemented** — every `REGISTRY` entry is `status="planned"`, `compute=None`, enforced
by a test. No GO-button UI or clock-sync work.

## Deviations from plan

None. All 3 tasks executed as written; no retries, no scope changes, no checkpoints
(plan was `autonomous: true` with zero checkpoint tasks).

## Next

**75-02** — pick the first metric from the "cheap, ship first" list above, implement
its `compute` fn, flip its `REGISTRY` entry to `status="implemented"`, at the user's
explicit approval (CONTEXT D12 — one metric at a time, never a batch). Run
`/paul:plan 75` to scope it once a metric is chosen.
