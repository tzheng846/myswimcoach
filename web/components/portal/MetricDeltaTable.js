// Ports app.py _build_compare_metrics conventions:
// delta = % change from baseline (older session); direction per metric —
// "normal" higher-is-better, "inverse" lower-is-better, "off" neutral.
const SPECS = [
  { label: "Avg Speed", key: "mean_vel_ms", fmt: (v) => `${v.toFixed(2)} m/s`, dir: "normal" },
  { label: "Max Speed", key: "max_vel_ms", fmt: (v) => `${v.toFixed(2)} m/s`, dir: "normal" },
  { label: "Stroke Rate", key: "stroke_rate_spm", fmt: (v) => `${v.toFixed(1)} spm`, dir: "off" },
  { label: "Dist per Stroke", key: "mean_dps_m", fmt: (v) => `${v.toFixed(2)} m`, dir: "normal" },
  { label: "Stroke Consistency (CV)", key: "cv_arm_peak_vel", fmt: (v) => v.toFixed(3), dir: "inverse" },
  { label: "Timing Consistency (ISI CV)", key: "cv_isi", fmt: (v) => v.toFixed(3), dir: "inverse" },
  { label: "Glide Time", key: "mean_coast_fraction", fmt: (v) => `${(v * 100).toFixed(0)}%`, dir: "off" },
  { label: "Fatigue Index", key: "fatigue_index_pct", fmt: (v) => `${v.toFixed(1)}%`, dir: "inverse" },
];

function deltaColor(pct, dir) {
  if (dir === "off" || pct === 0) return "text-muted";
  const improved = dir === "normal" ? pct > 0 : pct < 0;
  return improved ? "text-success" : "text-danger";
}

export default function MetricDeltaTable({ baseline, newer, labelBase, labelNew }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-navy/50 bg-surface">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-navy/40 text-left text-[11px] uppercase tracking-wider text-muted">
            <th className="px-4 py-3 font-semibold">Metric</th>
            <th className="px-4 py-3 font-semibold">{labelBase} (baseline)</th>
            <th className="px-4 py-3 font-semibold">{labelNew}</th>
            <th className="px-4 py-3 font-semibold">Δ</th>
          </tr>
        </thead>
        <tbody>
          {SPECS.map(({ label, key, fmt, dir }) => {
            const bVal = baseline?.[key];
            const nVal = newer?.[key];
            if (bVal == null && nVal == null) return null;
            const pct =
              bVal != null && nVal != null && bVal !== 0
                ? ((nVal - bVal) / Math.abs(bVal)) * 100
                : null;
            return (
              <tr key={key} className="border-b border-navy/20 last:border-0">
                <td className="px-4 py-2.5 text-subtle">{label}</td>
                <td className="px-4 py-2.5 font-mono">
                  {bVal != null ? fmt(bVal) : "--"}
                </td>
                <td className="px-4 py-2.5 font-mono">
                  {nVal != null ? fmt(nVal) : "--"}
                </td>
                <td
                  className={`px-4 py-2.5 font-mono font-semibold ${
                    pct != null ? deltaColor(pct, dir) : "text-muted"
                  }`}
                >
                  {pct != null ? `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%` : "--"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
