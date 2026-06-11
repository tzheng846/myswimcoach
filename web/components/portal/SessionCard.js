"use client";

import Link from "next/link";

export const STROKE_LABELS = {
  breaststroke: "Breaststroke",
  freestyle: "Freestyle",
  backstroke: "Backstroke",
  butterfly: "Butterfly",
  im: "Individual Medley",
  udk: "Underwater Dolphin Kick",
};

const STROKE_ABBR = {
  breaststroke: "Breast",
  freestyle: "Free",
  backstroke: "Back",
  butterfly: "Fly",
  im: "IM",
  udk: "UDK",
};

function Stat({ label, value, unit }) {
  return (
    <div className="flex-1 text-center">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-0.5 font-mono text-lg font-bold text-ink">
        {value ?? "--"}
      </p>
      <p className="text-[10px] text-muted">{unit}</p>
    </div>
  );
}

export default function SessionCard({ session, onStar, onDelete }) {
  const s = session.session ?? {};
  const date = new Date(session.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const abbr = STROKE_ABBR[session.stroke_type] ?? session.stroke_type;

  return (
    <div className="group relative rounded-xl border border-navy/50 bg-surface transition-colors hover:border-navy">
      <Link href={`/app/sessions/${session.id}`} className="block p-4">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="min-w-0">
            {session.name ? (
              <p className="truncate text-sm font-semibold text-ink">
                {session.name}
              </p>
            ) : null}
            <p className={session.name ? "text-[11px] text-muted" : "text-xs text-subtle"}>
              {date}
            </p>
          </div>
          <div className="flex items-center gap-1.5 group-hover:invisible">
            {session.is_starred ? (
              <span className="text-warning">★</span>
            ) : null}
            {abbr ? (
              <span className="rounded bg-navy px-1.5 py-0.5 text-[10px] font-semibold text-[#7faacc]">
                {abbr}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex">
          <Stat label="Rate" value={s.stroke_rate_spm?.toFixed(1)} unit="SPM" />
          <Stat label="Speed" value={s.mean_vel_ms?.toFixed(2)} unit="m/s" />
          <Stat label="Dist" value={s.total_dist_m?.toFixed(1)} unit="m" />
        </div>
      </Link>

      <div className="absolute right-3 top-3 hidden gap-1 group-hover:flex">
        <button
          onClick={onStar}
          title={session.is_starred ? "Unstar" : "Star"}
          className="rounded-md bg-surface-2 px-2 py-1 text-sm text-warning hover:bg-surface-3"
        >
          {session.is_starred ? "★" : "☆"}
        </button>
        <button
          onClick={onDelete}
          title="Delete"
          className="rounded-md bg-surface-2 px-2 py-1 text-sm text-danger hover:bg-surface-3"
        >
          🗑
        </button>
      </div>
    </div>
  );
}
