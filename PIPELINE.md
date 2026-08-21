# PIPELINE.md — signal processing, phase model & metrics (current fact)

*Reference doc. Describes how the system **works today**, not its history. Updated 2026-08-20
(through Phase 77). Phase tags in parentheses are for tracing history in `.paul/phases/`, not
narration. Volatile status — what's uncommitted, owed, or in flight — lives in `.paul/STATE.md`,
not here.*

The sensor is one **1-D axial trace**: an AS5600 encoder on a tethered wheel logs angle counts at
~270 Hz. Everything downstream is `velocity(t)`, `distance(t)`, `acceleration(t)` on one axis.
There is no pose, no depth, no per-limb signal — metrics that need those are out of reach and are
not faked.

---

## 1. Signal extraction — `vel_acc_extraction.py`

`run_pipeline()` (the api.py path) processing order:
1. Drop rows where `magnet_ok == 0`.
2. Unwrap angle counts (0↔4095 rollovers).
3. Counts → metres via `WHEEL_DIAMETER_M = 0.06` (circumference / 4096).
4. Resample to a uniform native-rate grid (linear interp).
5. `scipy.signal.decimate` toward `TARGET_FS_HZ = 100` (Chebyshev lowpass — no separate filter).
6. `np.gradient` → velocity.
7. Velocity → ~5 Hz → `np.gradient` → acceleration, interpolated back. *(As of Phase 66 the stored
   `acceleration_profile` is instead a full-rate Savitzky–Golay derivative of the stored velocity;
   display-only — `metrics.py` never consumes acceleration.)*

**No Hampel or post-gradient filter.** Velocity troughs between strokes are real signal.

### Sample rate is per-session — never assume 100 Hz
Decimation is by an **integer** factor, so the requested 100 Hz is essentially never achieved:
`factor = round(268.5/100) = 3 → actual ≈ 89.5 Hz`. `run_pipeline` returns the real rate as its 5th
value. **`sessions.sample_rate_hz` is authoritative per session.** Readers: `api.py:_session_fs(row)`,
web `row.sample_rate_hz`, `annotations.py`/`phase_metrics.py` take it as `fs`. **NULL = pre-rate
session** → every reader falls back to `annotations.FS_HZ` (100), which reproduces old behaviour. Do
**not** backfill NULL with 100 (erases "genuinely 100" vs "unknown"). Most NULL-rate sessions are
actually ~90 Hz.

### Raw / processed columns
- Raw CSV: `timestamp_us`, `angle_counts`, `magnet_ok`.
- Processed: `time_s`, `dist_m`, `vel_ms`, `accel_ms2` at the decimated rate.

---

## 2. The race-phase model (the spine of everything below)

One lap, no turns. Exactly one of each phase per recording. Maps 1:1 onto the annotation contract
(`annotations.py`), so the phase decomposition is **read**, coach-correctable, not reinvented.

| # | Phase | Content by stroke | Boundary that opens it |
|---|-------|-------------------|------------------------|
| 1 | **Start** | dive (free/back/fly) *or* push-off | `dive_start_s` |
| 2 | **Underwater** | dolphin kicks (free/back/fly) *or* pulldown (breast) | `underwater_start_s` |
| 3 | **Swim** | strokes; the **first stroke = breakout** (marked special, still a stroke) | `stroke_start_s` … `finish_s` |

**Boundary resolution** — `phase_metrics.resolve_boundaries(ctx)` resolves the four boundaries once
per session, with per-key provenance in `sources`. Precedence: **coach annotation (`manual`) →
auto-seed (`auto`) → detector (`detected`) → `none`**. A human mark always wins. The seed's legacy
`underwater_start_s` is deliberately ignored (it was the dive-peak derivation the detector replaced).

---

## 3. Boundary detection — the segmentation (Phase 75–77)

Every detector obeys **refuse-to-answer**: return `None` when it doesn't trust its own answer, and
the caller keeps the incumbent boundary rather than shipping a confident wrong one.

| Boundary | Detector | Mechanism | Accuracy (1 swimmer) |
|---|---|---|---|
| `dive_start_s` (start) | `session.baseline_end_s` via `build_seed` | **motion onset** — first point where the rolling mean of \|vel\| holds above `_BASELINE_THRESH` (a low floor) for 0.5 s | ⚠ known defect ↓ |
| `underwater_start_s` ("dolphin-kick start") | **`detect_underwater_start`** (75-02) | from `baseline_end`, the start-surge peak within 4 s, then the **first velocity trough** with prominence ≥ `0.40 × v95` | median **0.13 s** vs 38 marks; answers 102/108 |
| `stroke_start_s` = **breakout** | per-stroke, 3 mechanisms ↓ | | |
| `finish_s` | `detect_swim_window` | rhythm-based (CWT ridge); end of cyclic stroking | inherited (Phase 59/65) |

> ⚠ **`dive_start_s` keys on motion onset, so a low-velocity artifact fires it early.** As the swimmer
> leaves the block they jump and sink, tugging the line below true dive speed; the low baseline
> threshold trips on that. **Intended rule (not yet implemented): the first velocity peak ≥ 2 m/s** —
> the tug never reaches it, a real dive/push-off does. Open caveat for implementation: a weak wall
> push-off may not reach 2 m/s. Tracked as owed in `.paul/STATE.md`.

### The breakout, three different mechanisms
Selected by `stroke_type` in `compute_session_metrics` ([metrics.py:1377](metrics.py:1377) free/back,
[:1393](metrics.py:1393) fly), applied as an `ip_end` override *after* `detect_swim_window`, *before*
the manual override (so a coach still wins).

- **Free / back — DISAPPEARANCE** · `detect_breakout_kickband` (76). A dedicated wide CWT (0.5–5.0 Hz)
  measures energy in the **~1.8–3.2 Hz dolphin-kick band** (`_kick_band_power`). Breakout = where that
  band-power **collapses below 0.35× its run-peak and holds**. Works because underwater is ~2 Hz
  kicking (in-band) while the free/back surface stroke is ~1 Hz arms (below band) + low-amplitude
  flutter → the kick band switches **off**. Guarded by `_breakout_leaves_swim` (refuse if <2 stroke
  cycles remain). **2.07 → 0.42 s** median, 10/16 ≤0.5 s.
- **Fly — APPEARANCE** · `detect_breakout_fly` (77). Band-power **ratio** `P(0.8–1.1 Hz)/P(1.1–1.5 Hz)`
  detected as a **rise after a sustained low** — the arm-cycle fundamental appearing. Disappearance is
  impossible on fly: its surface undulation is *itself* ~2 Hz (2 kicks per arm cycle), so the kick band
  never drops; what changes is that an arm pull is **added**. `_FLY_MIN_CONTRAST = 1.5` supplies the
  refusal (the sustained-low gate alone can't). **2.67 → 0.38 s** median, 12/16 ≤1.0 s.
- **Breaststroke — incumbent, no dedicated detector.** Byte-identical/untouched in 76 & 77. Its
  `stroke_start` still comes from `detect_swim_window` / the pulldown path, because a pulldown is one
  pull+glide+kick, not a kick train — neither disappearance nor arm-appearance applies. **Least-trusted
  breakout of the four.**

### Why one detector can't serve all strokes
The kick-band gate is a **one-band energy meter**, not a waveform detector — `|CWT|²` averaged over
one band discards phase/shape before deciding. In that one band, fly's surface stroke and a dolphin
kick are the same motion, so free's "band goes quiet" signal is absent on fly. Free wins on an
**amplitude** margin (its flutter is low-amplitude in hip/COM velocity), not a frequency one — which
is why the refuse gates are load-bearing, not decoration.

---

## 4. v95 — the threshold scale (Phase 57)
`v95` (95th percentile of `|vel|`) scales every velocity threshold in `metrics.py`. It is taken over
the **swim window** (`_window_v95(vel, start, end)`), not the full trace — a recording keeps running
after the touch, and a long near-zero tail otherwise drags the percentile down (+1.5–12% depending on
tail length). `compute_session_metrics` uses `vel[baseline_end:swim_end]`; `extract_cycle_peaks` uses
the span its cycles cover. `dead_spot_s` computed before vs after this change is not comparable.

---

## 5. Stroke-cycle segmentation (inside the Swim phase)
Separate from the phase boundaries above: this cuts the swim into individual stroke cycles for the
per-cycle metrics. Table-driven per-stroke dispatch (`SEGMENTER_BY_STROKE`, Phase 59):

| stroke | segmenter | pairing k |
|---|---|---|
| freestyle, backstroke | `segment_cycles_wavelet` | 2 |
| butterfly, breaststroke | `_learned_boundaries` (logistic over 5 shape features; **no sklearn in prod** — a dot product + sigmoid) | 2 |
| unknown / im / udk | bare wavelet | 1 |

`k` describes the **detector's** boundary rate, not the stroke's physiology (`annotations.MARKS_PER_CYCLE`
is 1 for fly/breast — do **not** reuse it as the divisor). Cycle *regularity* is a separate gate from
boundary F1 — a segmenter with good F1 but drifting cycle phase is rejected (guarded by
`tests/test_metrics.py::TestCycleRegularityGate`). **`segmentation_reliable` is hardcoded `False`** for
every auto-segmented session; it flips `True` only when metrics are recomputed from human cycle bounds.

---

## 6. Phase-metrics registry — `phase_metrics.py`
The compute engine for per-phase metrics. Pure, no I/O. `metrics_json.phases` (jsonb, no migration)
is the storage; a `MetricSpec` registry is the single source of truth — one entry per metric with
`key / phase / unit / tier / status(planned|implemented) / compute`. A metric is declared once, then
"turned on" by attaching a compute fn. `compute_phases(ctx)` runs every implemented spec, swallowing
any raise to `value=None` (a metric never fails the whole response). Wired at **`POST /process`** and
**`POST /sessions/{id}/recompute`** (the backfill seam — re-derives from stored velocity/distance/accel
arrays, never the raw CSV).

**Registry status (37 slots):**

| Phase bucket | Implemented | Planned (compute=None) |
|---|---|---|
| **Start** (11) | — none | all 11 (peak_vel, time_to_peak, max_accel, dive_duration, glide_*, streamline_drag, break_into_kick_vel, **reaction_time**) |
| **Underwater** (13) | **13** — 4 window (`uw_duration/distance/avg_speed/surface_ratio`) + 2 breast pulldown + **7 kick** (`kick_count/tempo/consistency/dist_per_kick/per_kick_decay/first_kick_impulse/uw_ivv`) | — |
| **Swim** (9) | — none | all 9 (ivv, breakout_vel, breakout_vel_loss, breakout_vs_steady, splits, sr_dps_coupling, dead_spot_timing, accel_asymmetry, breathing_dip) |
| **Whole** (4) | — none | all 4 (phase_time_budget, phase_dist_budget, vel_envelope, jerk_smoothness) |

- Underwater window metrics = Δdist/Δt over `[underwater_start_s, stroke_start_s]`; refuse below
  `_MIN_UW_DURATION_S = 0.5 s`.
- The **7 kick metrics** ride on one detector, `metrics.detect_underwater_kicks` (prominence
  `0.15 × window-v95`, ≤4 Hz spacing). Gated to dolphin-kick strokes; breaststroke → `None` (its
  underwater is the pulldown). Display-only — dolphin kicks have **zero** annotated ground truth.
- `reaction_time` is reserved (`start.reaction_time` + `PhaseContext.go_signal_s`), awaiting the
  coach GO-button + phone↔encoder clock sync.

> ⚠ Kick-metric commit/verify status (uncommitted, eyeball not run) is in `.paul/STATE.md`.

---

## 7. `metrics.py` session metrics (the older, per-cycle layer)
`compute_session_metrics(t, vel, dist, head_waist_m, manual, stroke_type)` →
`{session, cycles, data_quality, initial_phase}`. `manual` applies human-annotation overrides
(boundary indices and/or `cycle_bounds`); `manual=None` reproduces pure auto-detection.

- **Session keys:** `lap_time_s, total_dist_m, baseline_end_s, stroke_rate_spm, stroke_count,
  mean_vel_ms, max_vel_ms, mean_arm_peak_vel_ms, cv_arm_peak_vel, mean_isi_s, cv_isi, mean_dps_m,
  mean_impulse_m, mean_coast_fraction, mean_trough_vel_ms, fatigue_index_pct, pct_cycles_with_kick,
  mean_arm_kick_ratio, mean_arm_kick_delay_s`.
- **Data-quality keys:** `magnet_dropout_pct, cycle_count, outlier_cycle_count, plausible_fraction,
  kick_metrics_reliable, segmentation_reliable`.
- **`kick_metrics_reliable` is always `False`** — arm-pull and kick are hard to resolve as two
  distinct velocity peaks when biomechanically close. (Distinct from the new §6 underwater kicks,
  which are pure kicking with no arm to confuse them.)

---

## 8. Validation reality (read before trusting any number)
- **Annotated corpus spans multiple swimmers** — Tony, Leo, Titus, and *AlexGroup* (a stand-in
  athlete whose session-ids are individual testers' names). Counts by stroke: ~16 free / 17 fly /
  breast n=2 / **back n=0**. ⚠ **Unresolved:** the Phase 76/77 breakout-tuning records call their
  scoring corpus *"one swimmer"* — either that is wrong, or those detectors were fit on a
  single-swimmer subset while more labeled data exists. Being reconciled in a follow-up (see
  `.paul/STATE.md`). Until then treat cross-swimmer generalisation of the breakout constants as
  unproven; the band-edge **jitter grid** is the only in-corpus evidence.
- **No absolute thresholds** for non-breaststroke strokes (display doctrine = within-athlete
  contrast / trend). Breaststroke is the only stroke with data behind its rating bands; the others
  borrow that table, deliberately and visibly.
- **Circularity caveat:** `underwater_start_s` marks were placed while the coach looked at the same
  velocity trace, so 0.13 s is agreement with a human reading the curve, not independent ground truth.
- **Validation is by eyeball on DATABASE traces**, never the local raw CSVs (`tools/plot_kicks.py`,
  `tools/breakout_band_probe.py`, `tools/score_underwater.py`, read-only via service-role key).
