// cycleShape — per-band shape anomaly detection for the phase insets.
//
// ⚠ PARTLY WIRED (Phase 83-05). `resample`, `median`, `POINTS` and `MIN_ITEMS` ARE imported — by
// `lib/cycleTraces`, which uses them to draw every cycle on one axis for the overlay panel's
// normalized (% of cycle) mode and its pointwise-median reference line.
//
// ⚠ `analyzeShapes` and its MAD gate below remain PARKED AND UNIMPORTED (Phase 83-03). They are
// kept because the algorithm is correct and covered by `scratch/shape_checks.mjs`, and because the
// follow-up that needs it is a real owed item (STATE item 17) — not because anything renders it.
// Do not wire `analyzeShapes` without first fixing its reference population; see below.
//
// Why the gate was cut: measured across the stored library (90 sessions, 618 cycles), the MAD gate below
// fired on 75% of sessions at k=3.0 and still on 39% at an absurd k=8.0. There is no k where a
// clean swim is quiet and a ragged one is not. The cause is sample size — a lap holds a median of
// 7 cycles, so the MAD is small and unstable, and a within-lap outlier test on n=7 is not a
// abnormality test. Excluding the breakout helps marginally (67% → 55% at k=4.0) and costs 10
// sessions their eligibility.
//
// What would actually work: build the reference profile from the athlete's LAST N same-stroke
// SESSIONS rather than from the single lap — the same within-athlete-contrast baseline
// `lib/phaseBaseline` already uses for every metric strip, and the SPC posture the product doctrine
// asks for. That needs prior sessions' velocity arrays in the browser, which is a backend question,
// not a frontend one.
//
// The algorithm itself is sound and duration-invariant; only its reference population was wrong.
//
// ---------------------------------------------------------------------------------------------
//
// Answers "did this stroke look different?" by resampling every cycle (or kick) to a fixed length,
// taking the pointwise MEDIAN as the reference profile, and measuring each band's RMSE against it.
// Pure data in, pure data out: no React, no SVG, no display copy.
//
// Indices are SAMPLE indices at the session's own `sample_rate_hz` — never assume 100 Hz.

// Resample length. 50 points is well above the ~8-30 samples a real cycle spans at ~89.5 Hz, so
// the interpolation never throws away detail; raising it costs time and buys nothing.
export const POINTS = 50;

// MAD gate width. MAD * 1.4826 ~= sigma, so k = 3.0 is roughly a 2-sigma equivalent (~1 in 20).
// The single number most likely to want a coach's eye: raise it if too much goes red, lower it
// toward 2.5 if an obviously ragged swim shows nothing.
export const K = 3.0;

// Below this many usable bands a within-session median profile is not a reference, it is noise.
export const MIN_ITEMS = 5;

const fin = (v) => typeof v === "number" && Number.isFinite(v);

// Exported for `lib/cycleTraces` (83-05) so the overlay's median line and this file's reference
// profile cannot drift into two different definitions of "median".
export function median(xs) {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// Resample velocity[start..end-1] to exactly `points` values, linearly interpolating between
// neighbouring samples. This is what makes the distance duration-invariant (AC-1).
// Returns null when the span is too short or carries ANY non-finite value: a dropout must exclude
// the band, never be filled. `detect_underwater_kicks` interpolates over dropouts because peak
// SHAPE survives it, but a distance measure would silently score the fill itself.
export function resample(velocity, start, end, points) {
  const a = Math.max(0, Math.trunc(start));
  const b = Math.min(velocity.length, Math.trunc(end));
  const len = b - a;
  if (len < 2) return null;
  for (let i = a; i < b; i++) if (!fin(velocity[i])) return null;

  const out = new Array(points);
  for (let j = 0; j < points; j++) {
    const p = a + (j / (points - 1)) * (len - 1);
    const lo = Math.floor(p);
    const hi = Math.min(b - 1, lo + 1);
    const f = p - lo;
    out[j] = velocity[lo] * (1 - f) + velocity[hi] * f;
  }
  return out;
}

function rmse(x, ref) {
  let s = 0;
  for (let i = 0; i < x.length; i++) {
    const d = x[i] - ref[i];
    s += d * d;
  }
  return Math.sqrt(s / x.length);
}

// items (metrics_json.cycles or phases.kick_bands) + the session's velocity array
//   → { byN, results, reference }
//
// `byN` is the lookup `buildBands({ anomalies })` consumes, keyed by the SAME `n` buildBands
// assigns (`cycle_num + 1` when stored, else array position + 1) so the two libs cannot disagree
// about which band is which.
//
// Per item: `shapeDist` = RMSE in m/s against the reference profile (null when excluded),
// `durationDev` = signed deviation of its duration from the median, in MADs (a hover FACT — it
// never sets `anomaly` on its own), `anomaly` = the gated shape verdict.
export function analyzeShapes(items, velocity, opts = {}) {
  const { points = POINTS, k = K, minItems = MIN_ITEMS, durationKey = "duration_s" } = opts;
  const empty = { byN: {}, results: [], reference: null };
  if (!Array.isArray(items) || !items.length) return empty;
  if (!Array.isArray(velocity) || velocity.length < 2) return empty;

  const results = [];
  items.forEach((c, i) => {
    if (!c) return;
    const n = fin(c.cycle_num) ? c.cycle_num + 1 : i + 1;
    const profile = fin(c.start_idx) && fin(c.end_idx) ? resample(velocity, c.start_idx, c.end_idx, points) : null;
    results.push({
      n,
      profile,
      duration: fin(c[durationKey]) ? c[durationKey] : null,
      shapeDist: null,
      durationDev: null,
      anomaly: false,
    });
  });

  const usable = results.filter((r) => r.profile);

  // Reference = pointwise MEDIAN, not mean: one bad cycle must not drag the thing it is being
  // compared against.
  let reference = null;
  if (usable.length >= minItems) {
    reference = new Array(points);
    for (let j = 0; j < points; j++) reference[j] = median(usable.map((r) => r.profile[j]));

    // Distance = RMSE on raw velocities. Deliberately NOT Pearson correlation: Pearson is scale-
    // and offset-invariant, so it would discard amplitude — and a weak pull with an otherwise
    // normal profile is exactly what should be caught. RMSE also gives the hover a real unit.
    for (const r of usable) r.shapeDist = rmse(r.profile, reference);

    // Gate: within-athlete contrast against this session's own bands, no absolute threshold.
    // ONE-SIDED — a band closer to typical than typical is not an anomaly.
    const dists = usable.map((r) => r.shapeDist);
    const med = median(dists);
    const mad = median(dists.map((d) => Math.abs(d - med)));
    if (mad > 0) {
      for (const r of usable) if (r.shapeDist - med > k * mad) r.anomaly = true;
    }
  }

  // Duration, on the same robust basis but TWO-SIDED (long and short both matter). Returned as a
  // secondary fact for the hover; the primary flag above never reads it.
  const durs = results.filter((r) => r.duration != null);
  if (durs.length >= minItems) {
    const dMed = median(durs.map((r) => r.duration));
    const dMad = median(durs.map((r) => Math.abs(r.duration - dMed)));
    if (dMad > 0) for (const r of durs) r.durationDev = (r.duration - dMed) / dMad;
  }

  const byN = {};
  for (const r of results) {
    delete r.profile;
    byN[r.n] = r;
  }
  return { byN, results, reference };
}

export default analyzeShapes;
