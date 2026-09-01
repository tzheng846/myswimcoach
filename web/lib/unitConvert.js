// unitConvert.js — display-only unit conversion for the race-phase report card's metric grid
// (Phase 88-03).
//
// Fixes CONTEXT F6: `unit` already drives the traces, the cycle/kick hover readouts, CycleCharts
// and TimeToX, but stops dead at PhaseReportCard's metric grid — 23 of 47 registry metrics never
// converted.
//
// D1 — keyed off the UNIT STRING, not a per-metric list. Only `m`, `m/s`, `m/s²` and `m/s³` carry
// a length power; every other unit in DISPLAY is dimensionless or pure time. This is correct only
// while no unit carries a length power other than 1 (no `m²`, no `s/m`) — scratch/unit_check.mjs
// pins the 23/24/47 split so a metric added outside this table fails loudly instead of silently
// not converting.
//
// D2 — a DISPLAY transform, applied at the last moment. `flagVerdict` and `computeDomain` both run
// upstream on SI values; nothing here feeds back into a verdict. Scaling the value and the baseline
// by the same factor preserves every comparison, so toggling units cannot create or clear a flag.

export const M_TO_YD = 1.09361; // same constant as PhaseReportCard.js, CycleCharts.js, page.js

const LENGTH_UNITS = { "m": "yd", "m/s": "yd/s", "m/s²": "yd/s²", "m/s³": "yd/s³" };

// unit string + imperial flag -> { factor, unit }. Metric, or a unit outside LENGTH_UNITS, returns
// factor 1 and the SAME string — so an invariant row's markup is provably untouched.
export function displayUnit(unit, imperial) {
  if (!imperial || !(unit in LENGTH_UNITS)) return { factor: 1, unit };
  return { factor: M_TO_YD, unit: LENGTH_UNITS[unit] };
}

// baseline ({ median, band, mean, sd, mad, sMAD, n } | null/undefined) scaled by `factor`. `n` is a
// count and is carried through untouched. factor === 1 or no baseline returns the input unchanged
// (no allocation, so `===` still holds).
export function scaleBaseline(base, factor) {
  if (factor === 1 || base == null) return base;
  const scale = (v) => (typeof v === "number" && Number.isFinite(v) ? v * factor : v);
  return {
    ...base,
    median: scale(base.median),
    band: base.band ? [scale(base.band[0]), scale(base.band[1])] : base.band,
    mean: scale(base.mean),
    sd: scale(base.sd),
    mad: scale(base.mad),
    sMAD: scale(base.sMAD),
  };
}
