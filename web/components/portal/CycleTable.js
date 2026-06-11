// Per-cycle breakdown from metrics_json.cycles (keys set in metrics.py
// compute_session_metrics). Outlier flag mirrors metrics.py: duration < 0.8 × median.
const COLS = [
  { label: "#", get: (c, i) => i + 1 },
  { label: "Duration", unit: "s", get: (c) => c.duration_s?.toFixed(2) },
  { label: "Arm Peak", unit: "m/s", get: (c) => c.arm_peak_vel?.toFixed(2) },
  { label: "Trough", unit: "m/s", get: (c) => c.trough_vel_ms?.toFixed(2) },
  { label: "DPS", unit: "m", get: (c) => c.dist_m?.toFixed(2) },
  { label: "Impulse", unit: "m", get: (c) => c.impulse_m?.toFixed(2) },
  {
    label: "Coast",
    unit: "%",
    get: (c) =>
      c.coast_fraction != null ? (c.coast_fraction * 100).toFixed(0) : null,
  },
];

export function outlierDurations(cycles) {
  const durs = cycles.map((c) => c.duration_s).filter((d) => d != null);
  if (durs.length === 0) return new Set();
  const sorted = [...durs].sort((a, b) => a - b);
  const med = sorted[Math.floor(sorted.length / 2)];
  return new Set(
    cycles.filter((c) => c.duration_s != null && c.duration_s < 0.8 * med)
  );
}

export default function CycleTable({ cycles }) {
  if (!cycles?.length) return null;
  const outliers = outlierDurations(cycles);

  return (
    <div className="overflow-x-auto rounded-xl border border-navy/50 bg-surface">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-navy/40 text-left text-[11px] uppercase tracking-wider text-muted">
            {COLS.map((c) => (
              <th key={c.label} className="px-3 py-2.5 font-semibold">
                {c.label}
                {c.unit ? (
                  <span className="ml-1 font-normal normal-case">({c.unit})</span>
                ) : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-mono">
          {cycles.map((c, i) => (
            <tr
              key={i}
              className={`border-b border-navy/20 last:border-0 ${
                outliers.has(c) ? "bg-warning/10" : ""
              }`}
            >
              {COLS.map((col) => (
                <td key={col.label} className="px-3 py-2">
                  {col.get(c, i) ?? "--"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {outliers.size > 0 && (
        <p className="border-t border-navy/20 px-3 py-2 text-[11px] text-warning-2">
          Highlighted cycles are duration outliers (&lt; 80% of median) —
          possible segmentation artifacts.
        </p>
      )}
    </div>
  );
}
