import Link from "next/link";
import Avatar from "./Avatar";

const VERDICT = { good: "Good", ok: "OK", needs_work: "Needs work", unknown: "No data" };

function bandColor(band, colors) {
  if (band === "good") return colors.good;
  if (band === "ok") return colors.ok;
  if (band === "needs_work") return colors.needs_work;
  return null; // unknown → neutral
}

// One athlete in the team grid: avatar + four pillar band-dots (color from the payload).
export default function RosterBandCard({ athlete, colors }) {
  const { name, stroke_type, last_tested, pillars } = athlete;
  const date = last_tested
    ? new Date(`${last_tested}T00:00:00`).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : null;
  const hasData = pillars && pillars.length > 0;

  return (
    <Link
      href={`/app/sessions?athlete=${athlete.athlete_id}`}
      className={`block rounded-xl border border-navy/50 bg-surface p-5 transition-colors hover:border-navy ${
        hasData ? "" : "opacity-60"
      }`}
    >
      <div className="flex items-center gap-3">
        <Avatar name={name} />
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{name}</p>
          <p className="text-xs capitalize text-muted">
            {stroke_type || "breaststroke"}
            {date ? ` · ${date}` : ""}
          </p>
        </div>
      </div>

      {hasData ? (
        <div className="mt-4 grid grid-cols-2 gap-2">
          {pillars.map((p) => {
            const c = bandColor(p.band, colors);
            return (
              <div
                key={p.key}
                className="flex items-center gap-2"
                title={`${p.label}: ${VERDICT[p.band] || p.band}`}
              >
                <span
                  className={`h-2.5 w-2.5 shrink-0 rounded-full ${c ? "" : "bg-surface-3"}`}
                  style={c ? { background: c } : undefined}
                  aria-label={`${p.label}: ${VERDICT[p.band] || p.band}`}
                />
                <span className="truncate text-[11px] text-subtle">{p.label}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted">No sessions yet</p>
      )}
    </Link>
  );
}
