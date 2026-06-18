import Link from "next/link";

function relDate(d) {
  if (!d) return "";
  const then = new Date(`${d}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((today - then) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  return then.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Newest sessions team-wide; each row opens that session's report card.
export default function RecentActivity({ items }) {
  return (
    <section>
      <h2 className="text-sm uppercase tracking-wider text-muted">Recent activity</h2>
      {!items || items.length === 0 ? (
        <p className="mt-3 text-sm text-muted">No sessions yet.</p>
      ) : (
        <div className="mt-3 divide-y divide-navy/40 rounded-xl border border-navy/50 bg-surface">
          {items.map((s) => (
            <Link
              key={s.session_id}
              href={`/app/sessions/${s.session_id}`}
              className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-surface-2"
            >
              <span className="font-medium text-ink">{s.name}</span>
              <span className="text-xs capitalize text-muted">
                {(s.stroke_type || "breaststroke")} · {relDate(s.date)}
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
