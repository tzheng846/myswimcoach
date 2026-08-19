// Pure group statistics for the A/B experiment comparison (Phase 73). No React/Next imports — this
// runs under plain node, and holds NO p-values by design: n per group is tiny (often 3), so a
// significance test would be fragile and falsely authoritative (CONTEXT D4). We report the honest
// distribution (mean ± SD, individual values) and a band-overlap separation cue instead.

function toNumbers(values) {
  return (values ?? []).filter((v) => v != null && Number.isFinite(v));
}

// Summary of one group's values for a metric. sd is null for n<2 (no spread from a single swim).
export function groupStats(values) {
  const xs = toNumbers(values);
  const n = xs.length;
  if (n === 0) return { n: 0, mean: null, sd: null, min: null, max: null };
  const mean = xs.reduce((s, x) => s + x, 0) / n;
  const sd =
    n < 2 ? null : Math.sqrt(xs.reduce((s, x) => s + (x - mean) ** 2, 0) / (n - 1));
  return { n, mean, sd, min: Math.min(...xs), max: Math.max(...xs) };
}

// Do the two [mean − sd, mean + sd] bands overlap? Only meaningful when both groups have an sd (n≥2);
// a missing sd is treated as "overlapping" (we can't claim separation from a single point).
export function bandsOverlap(a, b) {
  if (a?.sd == null || b?.sd == null) return true;
  const loA = a.mean - a.sd, hiA = a.mean + a.sd;
  const loB = b.mean - b.sd, hiB = b.mean + b.sd;
  return loA <= hiB && loB <= hiA;
}

// Compare one metric across two groups. betterSide uses the metric's direction ("higher"/"lower"
// improvement, "neutral" = no better/worse). separation: 'insufficient' (a group has n<2),
// 'clear' (±SD bands disjoint) or 'overlapping'.
export function metricComparison(metric, valuesA, valuesB) {
  const a = groupStats(valuesA);
  const b = groupStats(valuesB);
  const deltaAbs = a.mean != null && b.mean != null ? b.mean - a.mean : null;
  const deltaPct = a.mean ? (deltaAbs / Math.abs(a.mean)) * 100 : null;

  let betterSide = null; // 'A' | 'B' | null
  if (deltaAbs != null && deltaAbs !== 0 && metric?.direction && metric.direction !== "neutral") {
    const bIsHigher = b.mean > a.mean;
    const higherIsBetter = metric.direction === "higher";
    betterSide = bIsHigher === higherIsBetter ? "B" : "A";
  }

  let separation; // 'clear' | 'overlapping' | 'insufficient'
  if (a.n < 2 || b.n < 2) separation = "insufficient";
  else separation = bandsOverlap(a, b) ? "overlapping" : "clear";

  return { a, b, deltaAbs, deltaPct, betterSide, separation };
}
