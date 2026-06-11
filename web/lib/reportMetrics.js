// Single source of truth for parent report card metrics.
// direction: "higher" = increase is improvement, "lower" = decrease is
// improvement (lap time, consistency CV), "neutral" = change shown without
// good/bad framing.
export const REPORT_METRICS = [
  {
    key: "mean_vel_ms",
    label: "Average Speed",
    unit: "m/s",
    direction: "higher",
    improvePhrase: "faster on average",
    decimals: 2,
  },
  {
    key: "max_vel_ms",
    label: "Top Speed",
    unit: "m/s",
    direction: "higher",
    improvePhrase: "higher top speed",
    decimals: 2,
  },
  {
    key: "stroke_rate_spm",
    label: "Stroke Rate",
    unit: "spm",
    direction: "neutral",
    improvePhrase: "change in stroke rate",
    decimals: 1,
  },
  {
    key: "mean_dps_m",
    label: "Distance per Stroke",
    unit: "m",
    direction: "higher",
    improvePhrase: "farther per stroke",
    decimals: 2,
  },
  {
    key: "lap_time_s",
    label: "Lap Time",
    unit: "s",
    direction: "lower",
    improvePhrase: "faster lap",
    decimals: 1,
  },
  {
    key: "cv_arm_peak_vel",
    label: "Stroke Consistency",
    unit: "",
    direction: "lower",
    improvePhrase: "more consistent",
    decimals: 3,
  },
];

export function metricByKey(key) {
  return REPORT_METRICS.find((m) => m.key === key);
}

export function formatValue(metric, v) {
  if (v == null) return "--";
  const num = v.toFixed(metric.decimals);
  return metric.unit ? `${num} ${metric.unit}` : num;
}

// Direction-aware improvement between the first and latest session in range.
// "lower" metrics invert: a decrease reads as positive improvement
// ("8% faster lap", "12% more consistent"). Returns null when not computable.
export function computeImprovement(metric, first, latest) {
  if (first == null || latest == null || first === 0) return null;
  const rawPct = ((latest - first) / Math.abs(first)) * 100;
  if (metric.direction === "neutral") {
    return { pct: rawPct, improved: null, phrase: metric.improvePhrase };
  }
  const signedTowardBetter = metric.direction === "lower" ? -rawPct : rawPct;
  return {
    pct: signedTowardBetter,
    improved: signedTowardBetter > 0,
    phrase: metric.improvePhrase,
  };
}
