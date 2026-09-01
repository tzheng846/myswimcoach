// rollingMean.js — null-aware centred moving average over a sampled profile (Phase 88-05).
// Pure: no React, no recharts, no DOM — node-loadable like web/lib/splitWindow.js.
//
// D3 — THE ONE WAY THIS CAN BE QUIETLY WRONG. VelocityChart caps its chart at MAX_POINTS = 2000
// and strides `step = ceil(n / MAX_POINTS)`. This function MUST be called on the FULL-RATE array
// and the RESULT strided — never the other way round. Smoothing a strided array with the same
// `fsHz` widens the real window by exactly `step` seconds while the on-screen label still reads
// "1.00 s". The trap does not reproduce on a 20 s swim (1799 points at 89.99 Hz ⇒ step === 1),
// which is why scratch/rolling_mean_check.mjs pins it with a synthetic 4000-point profile.
//
// The window is CENTRED, not trailing: a trailing mean shifts every feature later in time by half
// the window and would misplace the breakout against the raw trace drawn beneath it.

// values: Array<number|null>, fsHz: number, windowS: number -> Array<number|null>
export function rollingMean(values, fsHz, windowS) {
  const src = values ?? [];
  // `!(windowS > 0)` rather than `windowS <= 0` so NaN/undefined fall through here too.
  if (!(windowS > 0)) return src.slice();

  // A NULL/0/NaN rate is "unknown", not "100" (CLAUDE.md) — but a display transform has to draw
  // something, so it falls back to annotations.FS_HZ the same way every other reader does.
  const fs = Number.isFinite(fsHz) && fsHz > 0 ? fsHz : 100;

  const n = Math.max(1, Math.round(windowS * fs));
  if (n <= 1) return src.slice();

  // Half-width. An even `n` yields a span of n-1 samples: a centred window cannot have even
  // width, and rounding down is what keeps it symmetric about j.
  const h = (n - 1) >> 1;
  const len = src.length;

  // Prefix sums of value and of COUNT, so the mean is O(1) per point regardless of window size.
  // A gap contributes 0 to both, so it is skipped rather than counted as a zero.
  const sum = new Float64Array(len + 1);
  const cnt = new Int32Array(len + 1);
  for (let i = 0; i < len; i++) {
    const v = src[i];
    const ok = v != null && Number.isFinite(v);
    sum[i + 1] = sum[i] + (ok ? v : 0);
    cnt[i + 1] = cnt[i] + (ok ? 1 : 0);
  }

  const out = new Array(len);
  for (let j = 0; j < len; j++) {
    const lo = j - h < 0 ? 0 : j - h;
    const hi = j + h > len - 1 ? len - 1 : j + h;
    const c = cnt[hi + 1] - cnt[lo];
    out[j] = c === 0 ? null : (sum[hi + 1] - sum[lo]) / c;
  }
  return out;
}

export default rollingMean;
