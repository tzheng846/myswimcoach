function Stat({ label, value, warn }) {
  return (
    <div className="flex-1 text-center">
      <p className="text-[11px] uppercase tracking-wider text-muted">{label}</p>
      <p
        className={`mt-0.5 font-mono text-lg font-bold ${
          warn ? "text-warning-2" : "text-ink"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

// Ports the iOS DataQualityCard — quality stats + warnings from metrics_json.data_quality.
export default function DataQualityCard({ dataQuality }) {
  if (!dataQuality) return null;

  const {
    warnings = [],
    total_cycles_raw = 0,
    outlier_cycle_count = 0,
    implausible_cycle_count = 0,
    magnet_dropout_pct = 0,
  } = dataQuality;

  const kickWarning = warnings.find((w) => w.toLowerCase().includes("kick"));
  const sessionWarnings = warnings.filter(
    (w) => !w.toLowerCase().includes("kick")
  );
  const hasIssues = sessionWarnings.length > 0;

  return (
    <div
      className={`rounded-xl border border-navy/50 bg-surface p-4 ${
        hasIssues ? "border-l-2 border-l-warning" : ""
      }`}
    >
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Data Quality
      </p>
      <div className="flex">
        <Stat label="Cycles" value={String(total_cycles_raw)} />
        <Stat
          label="Outliers"
          value={String(outlier_cycle_count)}
          warn={outlier_cycle_count > 0}
        />
        <Stat
          label="Implausible"
          value={String(implausible_cycle_count)}
          warn={implausible_cycle_count > 0}
        />
        <Stat
          label="Dropout"
          value={magnet_dropout_pct > 0 ? `${magnet_dropout_pct.toFixed(1)}%` : "0%"}
          warn={magnet_dropout_pct > 5}
        />
      </div>
      {sessionWarnings.map((w, i) => (
        <p
          key={i}
          className="mt-2 rounded-md bg-warning/10 px-3 py-2 text-xs leading-relaxed text-warning-2"
        >
          ⚠ {w}
        </p>
      ))}
      {kickWarning ? (
        <p className="mt-2 text-[11px] leading-relaxed text-subtle/70">
          {kickWarning}
        </p>
      ) : null}
    </div>
  );
}
