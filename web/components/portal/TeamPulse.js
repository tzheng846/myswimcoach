// Team-health header: roster counts + per-pillar band distribution.
// Colors come from the /team/overview payload (rating_colors) — never hard-coded.

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-navy/50 bg-surface px-5 py-4">
      <p className="font-mono text-3xl font-semibold text-ink">{value}</p>
      <p className="mt-0.5 text-[11px] uppercase tracking-wider text-muted">{label}</p>
    </div>
  );
}

function DistBar({ p, colors }) {
  const total = p.good + p.ok + p.needs_work + p.unknown;
  const seg = (n, color, cls) =>
    n > 0 ? (
      <div
        className={`h-full ${cls || ""}`}
        style={{ width: `${(n / total) * 100}%`, background: color || undefined }}
      />
    ) : null;

  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-4">
      <p className="text-xs font-semibold text-subtle">{p.label}</p>
      <div className="mt-2 flex h-2.5 overflow-hidden rounded bg-surface-2">
        {total > 0 && (
          <>
            {seg(p.good, colors.good)}
            {seg(p.ok, colors.ok)}
            {seg(p.needs_work, colors.needs_work)}
            {seg(p.unknown, null, "bg-surface-3")}
          </>
        )}
      </div>
      <p className="mt-1.5 text-[11px] text-muted">
        <span style={{ color: colors.good }}>{p.good} good</span>
        {" · "}
        <span style={{ color: colors.ok }}>{p.ok} ok</span>
        {" · "}
        <span style={{ color: colors.needs_work }}>{p.needs_work} low</span>
      </p>
    </div>
  );
}

export default function TeamPulse({ athleteCount, testedThisWeek, pillars, colors }) {
  return (
    <section className="space-y-4">
      <div className="grid grid-cols-2 gap-4 sm:max-w-md">
        <Stat label="Athletes" value={athleteCount} />
        <Stat label="Tested this week" value={testedThisWeek} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {pillars.map((p) => (
          <DistBar key={p.key} p={p} colors={colors} />
        ))}
      </div>
    </section>
  );
}
