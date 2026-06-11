import Link from "next/link";
import Avatar from "./Avatar";

function Stat({ label, value }) {
  return (
    <div>
      <p className="font-mono text-lg font-semibold text-ink">{value}</p>
      <p className="mt-0.5 text-[11px] uppercase tracking-wider text-muted">
        {label}
      </p>
    </div>
  );
}

export default function AthleteCard({ athlete, lastSession }) {
  const m = lastSession?.metrics_json?.session;
  const date = lastSession
    ? new Date(lastSession.created_at).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <Link
      href={`/app/sessions?athlete=${athlete.id}`}
      className="block rounded-xl border border-navy/50 bg-surface p-5 transition-colors hover:border-navy"
    >
      <div className="flex items-center gap-3">
        <Avatar name={athlete.name} />
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{athlete.name}</p>
          <p className="text-xs capitalize text-muted">
            {athlete.stroke_type || "breaststroke"}
            {date ? ` · ${date}` : ""}
          </p>
        </div>
      </div>

      {m ? (
        <div className="mt-4 grid grid-cols-3 gap-2">
          <Stat label="Mean vel" value={`${m.mean_vel_ms?.toFixed(2) ?? "–"}`} />
          <Stat label="SPM" value={`${m.stroke_rate_spm?.toFixed(1) ?? "–"}`} />
          <Stat label="DPS" value={`${m.mean_dps_m?.toFixed(2) ?? "–"}`} />
        </div>
      ) : (
        <p className="mt-4 text-sm text-muted">No sessions yet</p>
      )}
    </Link>
  );
}
