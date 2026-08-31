// strokeStats — the pure stroke-level layer behind the Swimming section's strokes mode (Phase 87-02).
//
// 87-01 stores `metrics_json.strokes` (one entry per single ARM stroke, freestyle/backstroke only)
// and seven session keys off it. Two things are missing for rendering, and both live here:
//   1. stroke-level MEANS. `metrics_json.session` carries `mean_isi_s` / `mean_dps_m` etc. at CYCLE
//      level, and a cycle is two strokes — so the stored mean is ~2x the stroke value and would
//      draw a dashed reference line clean off the top of the dots. `deriveMeans` recomputes them
//      from the plotted items, which also makes CycleCharts' "means cover every item shown" true.
//   2. a display model for the asymmetry numbers. `armBalance` only SHAPES what 87-01 measured; it
//      never recomputes it. Two implementations of asymmetry is how the readout and the backfill
//      start disagreeing.
//
// ⚠ MEASURED CAVEAT, carried verbatim from 87-01. On the AUTO path the asymmetry is uncorrelated
// with coach-mark truth: Pearson r = -0.06, median error 10.2 percentage points against a 6.1%
// median signal, measured 2026-08-31 on 23 annotated freestyle sessions. The cause is a parity
// flip — one extra or missing stroke boundary swaps the A/B side of every stroke after it. And A
// and B are NEVER left and right: a 1-D axial encoder cannot observe which arm is which.
//
// Pure: no React, no formatting of units. Asymmetry is a percentage and the four CVs are ratios, so
// the whole block is UNIT-INVARIANT — nothing here may ever be multiplied by 1.09361.

const fin = (v) => typeof v === "number" && Number.isFinite(v);

// Population standard deviation (ddof = 0), matching numpy's `.std()` in metrics.py — otherwise the
// same caption would read a different CV in cycle mode and stroke mode for no reason a coach could
// ever discover.
function meanCv(vals) {
  if (vals.length < 2) return { mean: vals.length === 1 ? vals[0] : null, cv: null };
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const variance = vals.reduce((a, b) => a + (b - mean) * (b - mean), 0) / vals.length;
  return { mean, cv: mean === 0 ? null : Math.sqrt(variance) / mean };
}

const pluck = (items, key) => items.map((c) => c?.[key]).filter(fin);

// items → the same six keys CycleCharts reads off its `session` prop, so the result can be handed
// straight in. Nulls, never NaN, when a field has fewer than two usable values.
export function deriveMeans(items) {
  const list = Array.isArray(items) ? items : [];
  const dps = meanCv(pluck(list, "dist_m"));
  const coast = meanCv(pluck(list, "coast_fraction"));
  const dur = meanCv(pluck(list, "duration_s"));
  const arm = meanCv(pluck(list, "arm_peak_vel"));
  return {
    mean_dps_m: dps.mean,
    mean_coast_fraction: coast.mean,
    mean_isi_s: dur.mean,
    cv_isi: dur.cv,
    mean_arm_peak_vel_ms: arm.mean,
    cv_arm_peak_vel: arm.cv,
  };
}

// The three signed asymmetry percentages, in 87-01's own order. `(mean_A - mean_B) / mean * 100`,
// so a POSITIVE value means side A's mean is the larger one.
//
// ⚠ The `phrase` mapping is the one error here that would produce a confident, plausible, WRONG
// coaching statement: a longer duration is the SLOWER side, a larger distance is the FURTHER side,
// a larger arm peak is the FASTER side. Read it twice before changing it.
const ASYM = [
  { key: "arm_asym_tempo_pct", label: "Tempo", larger: "slower" },
  { key: "arm_asym_dps_pct", label: "Distance per stroke", larger: "further" },
  { key: "arm_asym_peak_vel_pct", label: "Arm peak speed", larger: "faster" },
];

const CV_KEYS = ["cv_stroke_interval_a", "cv_stroke_interval_b", "cv_stroke_dps_a", "cv_stroke_dps_b"];

// session (metrics_json.session) → display model, or null when ANY of the seven 87-01 keys is
// missing or non-finite. They are all-or-nothing by construction: `_arm_asymmetry` gates every one
// of them on both sides carrying at least three finite samples, so a partial block would be a
// partial truth. No threshold, no verdict, no good/bad — there is no usual-range baseline for these
// keys, and 83-03 is the precedent for not shipping an unmeasured cutoff.
export function armBalance(session) {
  const s = session ?? {};
  if (ASYM.some((a) => !fin(s[a.key]))) return null;
  if (CV_KEYS.some((k) => !fin(s[k]))) return null;

  return {
    rows: ASYM.map((a) => {
      const pct = s[a.key];
      const leader = pct >= 0 ? "A" : "B";
      return { key: a.key, label: a.label, pct, leader, phrase: `${leader} ${a.larger}` };
    }),
    cvs: [
      { label: "Tempo consistency", a: s.cv_stroke_interval_a, b: s.cv_stroke_interval_b },
      { label: "Distance consistency", a: s.cv_stroke_dps_a, b: s.cv_stroke_dps_b },
    ],
  };
}

export default deriveMeans;
