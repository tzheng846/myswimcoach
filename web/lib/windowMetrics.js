// Pure client-side recompute of the group-compare metrics over a chosen window of a swim (Phase 73-04).
// No React/Next imports → node-verifiable. Formulas mirror metrics.py (verified 2026-08-19):
//   mean_vel_ms = mean(vel[i0:i1] where >0); max_vel_ms = max(vel[i0:i1]);
//   stroke_rate_spm = 60/mean(cycle.duration_s); mean_dps_m = mean(cycle.dist_m);
//   cv_arm_peak_vel = std(arm_peak_vel)/mean(arm_peak_vel)  [population std, as np.std];
//   lap_time_s (windowed) = (i1-i0)/fs.
// "full" mode returns the STORED session scalars unchanged — never recomputed, so the default view
// can't drift from the unstored swim_end boundary. cycles[].start_idx/end_idx are full-trace indices
// into velocity_profile/distance_profile (same grid).

const nums = (a) => (a ?? []).filter((v) => v != null && Number.isFinite(v));
const mean = (a) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : null);
// Population std (ddof=0), matching metrics.py's np.std; null for n<2 (a single value has no spread).
const stdPop = (a) => {
  if (a.length < 2) return null;
  const m = mean(a);
  return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / a.length);
};

const KEYS = ["mean_vel_ms", "max_vel_ms", "stroke_rate_spm", "mean_dps_m", "lap_time_s", "cv_arm_peak_vel"];

// session = { sessionScalars, cycles, velocityProfile, distanceProfile, fs }
export function phaseBounds(session) {
  const fs = session.fs > 0 ? session.fs : 100;
  const baselineIdx = Math.max(0, Math.round((session.sessionScalars?.baseline_end_s ?? 0) * fs));
  const cy = session.cycles ?? [];
  const strokeStart = cy.length ? cy[0].start_idx : null;
  const strokeEnd = cy.length ? cy[cy.length - 1].end_idx : null;
  return { baselineIdx, strokeStart, strokeEnd };
}

// Resolve a scope to full-trace [i0, i1] (exclusive end), or null for "full"/empty/degenerate windows.
export function windowFor(scope, session) {
  const { baselineIdx, strokeStart, strokeEnd } = phaseBounds(session);
  const n = session.velocityProfile?.length ?? 0;
  const clamp = (i) => Math.min(Math.max(i, 0), n);
  let i0 = null, i1 = null;
  if (scope.mode === "full") return null;
  if (scope.mode === "stroking") { i0 = strokeStart; i1 = strokeEnd; }
  else if (scope.mode === "underwater") { i0 = baselineIdx; i1 = strokeStart; }
  else if (scope.mode === "distance") {
    const dp = session.distanceProfile ?? [];
    if (!dp.length) return null;
    const base = dp[Math.min(baselineIdx, dp.length - 1)] ?? 0;
    let lo = null, hi = null;
    for (let i = 0; i < dp.length; i++) {
      const d = dp[i] - base;
      if (d >= scope.from && d <= scope.to) { if (lo == null) lo = i; hi = i; }
    }
    if (lo == null) return null;
    i0 = lo; i1 = hi + 1;
  } else return null;
  if (i0 == null || i1 == null) return null;
  i0 = clamp(i0); i1 = clamp(i1);
  return i1 - i0 < 2 ? null : [i0, i1];
}

// The 6 REPORT_METRICS values recomputed over the scope's window, or the stored scalars for "full".
// Uncomputable quantities are null (not 0/NaN) so groupStats drops them.
export function scopedMetrics(scope, session) {
  const win = windowFor(scope, session);
  if (!win) {
    const s = session.sessionScalars ?? {};
    const out = {};
    for (const k of KEYS) out[k] = s[k] ?? null;
    return out;
  }
  const [i0, i1] = win;
  const fs = session.fs > 0 ? session.fs : 100;
  const seg = nums((session.velocityProfile ?? []).slice(i0, i1));
  const pos = seg.filter((v) => v > 0);
  const cyIn = (session.cycles ?? []).filter((c) => c.start_idx >= i0 && c.end_idx <= i1);
  const durs = nums(cyIn.map((c) => c.duration_s));
  const dists = nums(cyIn.map((c) => c.dist_m));
  const arms = nums(cyIn.map((c) => c.arm_peak_vel));
  const meanDur = mean(durs), meanArm = mean(arms), sdArm = stdPop(arms);
  return {
    mean_vel_ms: pos.length ? mean(pos) : null,
    max_vel_ms: seg.length ? Math.max(...seg) : null,
    stroke_rate_spm: meanDur ? 60 / meanDur : null,
    mean_dps_m: dists.length ? mean(dists) : null,
    lap_time_s: (i1 - i0) / fs,
    cv_arm_peak_vel: meanArm && sdArm != null ? sdArm / meanArm : null,
  };
}
