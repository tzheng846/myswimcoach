import Link from "next/link";
import Avatar from "./Avatar";

// Reason object → display chip. needs_work/declined use the needs_work color; the rest are neutral.
function reasonChip(r, colors) {
  if (r.type === "needs_work") return { text: r.pillar, color: colors.needs_work };
  if (r.type === "declined") return { text: `${r.pillar} ↓`, color: colors.needs_work };
  if (r.type === "stale") return { text: `${r.days}d since test`, color: null };
  if (r.type === "never_tested") return { text: "Never tested", color: null };
  return { text: r.type, color: null };
}

// Athletes the coach should look at — a needs-work band, a declined trend, or a stale/no test.
export default function NeedsAttention({ items, colors }) {
  return (
    <section>
      <h2 className="text-sm uppercase tracking-wider text-muted">Needs attention</h2>
      {!items || items.length === 0 ? (
        <p className="mt-3 text-sm text-muted">Everyone’s on track.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {items.map((a) => (
            <Link
              key={a.athlete_id}
              href={`/app/sessions?athlete=${a.athlete_id}`}
              className="flex items-center gap-3 rounded-xl border border-navy/50 bg-surface p-3 transition-colors hover:border-navy"
            >
              <Avatar name={a.name} size={32} />
              <span className="font-semibold text-ink">{a.name}</span>
              <div className="ml-auto flex flex-wrap justify-end gap-1.5">
                {a.reasons.map((r, i) => {
                  const c = reasonChip(r, colors);
                  return (
                    <span
                      key={i}
                      className="rounded-md bg-surface-2 px-2 py-0.5 text-xs font-semibold text-muted"
                      style={c.color ? { color: c.color } : undefined}
                    >
                      {c.text}
                    </span>
                  );
                })}
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
