// splitWindow.js — bin construction and window measurement for the report card's Segment splits
// picker (Phase 88-04). Pure: no React, no Next, node-loadable like web/lib/windowMetrics.js.
//
// D4 — THE WINDOW'S AVERAGE VELOCITY IS THE CHORD, never a sample mean of `vel`:
//   avgVelMs = (dist[i1] - dist[i0]) / (time[i1] - time[i0])
// This mirrors phase_metrics._split_velocity (phase_metrics.py:797-817) exactly, which is what
// makes AC-2 an EQUALITY and not an approximation — selecting one chip reproduces the matching
// `Split a–b m` grid row to floating-point tolerance, because both compute the same two indices
// from the same anchor by the same rule:
//   - the anchor index is `round(anchorS * fsHz)`, matching phase_metrics._idx (:248-259)
//   - the search is CLAMPED at finishS, matching _dive_relative's `end` (:791-794). Without that
//     clamp a bin could be filled by the swimmer drifting into the wall AFTER the touch (the
//     waist-tether geometry: dist_m keeps rising past finish_s), and the two numbers would
//     silently diverge.
//
// D2 — COMPLETE BINS ONLY. A partial trailing segment is never emitted, so no chip can describe a
// distance the swimmer did not cover. On a 25-yard lap the closing ~0.9 m therefore has no chip;
// that stretch is what 88-01's `splits_remainder` grid row reports instead.

export const YARD_TO_M = 0.9144; // same constant TimeToX.js uses
export const BIN_U = 5; // 5 m in metric, 5 yd in imperial (D6) — bins are unit-native

// { dist, time, anchorS, finishS, fsHz, imperial } -> [{ k, fromU, toU, i0, i1 }], complete bins
// only. Returns [] for any input that cannot yield at least one whole bin — a missing or
// out-of-trace anchor, a non-finite d0, or fewer than two distance boundaries.
export function buildBins({ dist, time, anchorS, finishS, fsHz, imperial = false }) {
  const n = Math.min(dist?.length ?? 0, time?.length ?? 0);
  if (!n || !(fsHz > 0) || anchorS == null) return [];

  const iAnchor = Math.round(anchorS * fsHz);
  if (!(iAnchor >= 0 && iAnchor < n)) return []; // _idx is deliberately unclamped; so is this
  const d0 = dist[iAnchor];
  if (typeof d0 !== "number" || !Number.isFinite(d0)) return [];

  // finishS -> exclusive end, mirroring _dive_relative: an unresolvable finish falls back to the
  // end of the stored trace (D8, _finish_s at phase_metrics.py:671-682).
  let end = n;
  if (finishS != null) {
    const iFin = Math.round(finishS * fsHz);
    if (iFin >= 0 && iFin < n) end = Math.min(n, iFin + 1);
  }

  const step = imperial ? BIN_U * YARD_TO_M : BIN_U;
  if (!(step > 0)) return [];

  // One pass: the first index at which relative distance reaches each successive multiple of
  // `step`. bounds[k] is _split_velocity's `_first_at(k * step)`.
  const bounds = [];
  let k = 0;
  for (let i = iAnchor; i < end; i++) {
    const d = dist[i];
    if (typeof d !== "number" || !Number.isFinite(d)) continue; // dropout nulls, cf. _finite_slice
    const rel = d - d0;
    while (rel >= k * step) {
      bounds[k] = i;
      k++;
    }
  }
  if (bounds.length < 2) return [];

  const bins = [];
  for (let j = 0; j + 1 < bounds.length; j++) {
    // Defensive, and it must TRUNCATE rather than skip: a degenerate bin (both thresholds first
    // hit on the same sample, i.e. >= 5 m covered between two consecutive samples) is what
    // _split_velocity returns None for. Dropping it mid-list would break the contiguity that the
    // {lo, hi} selection shape relies on, so the list ends there instead.
    if (!(bounds[j + 1] > bounds[j])) break;
    bins.push({ k: j, fromU: j * BIN_U, toU: (j + 1) * BIN_U, i0: bounds[j], i1: bounds[j + 1] });
  }
  return bins;
}

// bins + an inclusive { lo, hi } bin-index pair -> the measured window, or null.
export function measureWindow(bins, sel, dist, time) {
  if (!bins?.length || !sel) return null;
  const { lo, hi } = sel;
  if (!(lo >= 0 && hi < bins.length && lo <= hi)) return null;
  const i0 = bins[lo].i0;
  const i1 = bins[hi].i1;
  const elapsedS = time[i1] - time[i0];
  const dd = dist[i1] - dist[i0];
  const ok = Number.isFinite(elapsedS) && Number.isFinite(dd) && elapsedS > 0;
  return {
    fromU: bins[lo].fromU,
    toU: bins[hi].toU,
    i0,
    i1,
    elapsedS: ok ? elapsedS : null,
    avgVelMs: ok ? dd / elapsedS : null, // chord (D4), never mean(vel)
  };
}

// D5 — click extends the contiguous run; clicking inside a multi-bin run collapses to that bin;
// clicking the only selected bin clears. Contiguity is structural in the { lo, hi } shape, so
// there is no invariant to enforce.
export function toggleBin(sel, k) {
  if (!sel) return { lo: k, hi: k };
  const { lo, hi } = sel;
  if (k < lo || k > hi) return { lo: Math.min(lo, k), hi: Math.max(hi, k) };
  if (lo === hi) return null; // the only selected bin, clicked again
  return { lo: k, hi: k }; // inside a multi-bin run -> collapse
}
