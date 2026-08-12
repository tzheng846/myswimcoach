"use client";

import Link from "next/link";
import { DROPOUT_WARN_PCT } from "@/lib/dropoutWarning";

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

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

// "8:24 PM". Lives in the TITLE, while the weekday/date lives in the meta line — the two are
// deliberately split so they don't duplicate each other. Time is what separates recordings made
// in the same session block, which is what a collection day actually produces.
function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

// Weekday inside a week ("Wed"), MM-DD-YY beyond it.
// Safe to read the clock during render: cards only mount after the client-side fetch resolves,
// so they never server-render and cannot cause a hydration mismatch.
function formatWhen(iso) {
  const d = new Date(iso);
  if (Date.now() - d.getTime() < WEEK_MS) {
    return d.toLocaleDateString("en-US", { weekday: "short" });
  }
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())}-${p(d.getFullYear() % 100)}`;
}

// Shares its dropout threshold with lib/dropoutWarning.js so the list and the report card cannot
// disagree. (It used to say "mirrors DataQualityCard"; 61-02 D4 deleted that card.)
//
// ⚠ THE WARNING EXCLUSIONS ARE LOAD-BEARING, NOT TIDINESS. api.py emits two warnings that fire on
// essentially every session, so counting either would put a ⚠ on literally every card and the
// indicator would carry no information at all:
//   - kick: metrics.py sets kick_metrics_reliable = False on EVERY session (api.py:181 appends
//     it unconditionally)
//   - segmentation: api.py:193 appends it whenever segmentation_reliable is false, and that flag
//     is hardcoded false for every auto-segmented session
// ⚠ The segmentation exclusion was ADDED in 61-02. Before it, this indicator did flag every card.
function qualityIssue(dq) {
  if (!dq) return null;
  if ((dq.magnet_dropout_pct ?? 0) > DROPOUT_WARN_PCT)
    return `${dq.magnet_dropout_pct.toFixed(1)}% signal dropout`;
  if ((dq.implausible_cycle_count ?? 0) > 0)
    return `${dq.implausible_cycle_count} implausible cycle${
      dq.implausible_cycle_count === 1 ? "" : "s"
    }`;
  const real = (dq.warnings ?? []).filter((w) => {
    const t = w.toLowerCase();
    return !t.includes("kick") && !t.includes("segmentation");
  });
  return real.length ? real[0] : null;
}

function Chip({ children, title, tone = "muted" }) {
  const tones = {
    muted: "border-surface-3 bg-surface-2 text-muted",
    accent: "border-accent/50 bg-accent/15 text-primary",
    warn: "border-warning/40 bg-warning/10 text-warning-2",
  };
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

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

export default function SessionCard({
  session,
  athleteName,
  isAnnotated,
  onStar,
  onDelete,
}) {
  const s = session.session ?? {};
  const dq = session.dq ?? {};
  const abbr = STROKE_ABBR[session.stroke_type] ?? session.stroke_type;

  // A typed name always wins and is never decorated. Otherwise derive one — display only,
  // sessions.name is never written, so a name entered later simply takes over.
  const title =
    session.name ||
    `${STROKE_LABELS[session.stroke_type] ?? "Session"} · ${formatTime(
      session.created_at
    )}`;

  const issue = qualityIssue(dq);
  // "Annotated" and "recomputed" are different things: an annotation with fewer than two cycle
  // boundaries is saved but rewrites no metrics. Conflating them is how a coach concludes an
  // annotation did nothing.
  const annTitle = dq.recomputed_from_annotation
    ? "Hand-annotated — metrics were recomputed from these marks"
    : "Hand-annotated — marks saved, but too few cycle boundaries to recompute metrics";

  const hasChips = Boolean(isAnnotated || session.video_path || issue);

  return (
    <div className="group relative rounded-xl border border-navy/50 bg-surface transition-colors hover:border-navy">
      <Link href={`/app/sessions/${session.id}`} className="block p-4">
        {/* Spacing below the header depends on whether a chip row follows, so a card with no
            chips keeps exactly the gap it had before this change. */}
        <div
          className={`flex items-start justify-between gap-2 ${
            hasChips ? "mb-2" : "mb-3"
          }`}
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-ink">{title}</p>
            <p className="mt-0.5 truncate text-[11px] text-muted">
              {[athleteName, formatWhen(session.created_at)]
                .filter(Boolean)
                .join(" · ")}
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

        {hasChips && (
          <div className="mb-3 flex flex-wrap items-center gap-1.5">
            {isAnnotated && (
              <Chip tone="accent" title={annTitle}>
                ✎ Annotated
              </Chip>
            )}
            {session.video_path && <Chip title="Session video attached">🎥 Video</Chip>}
            {issue && (
              <Chip tone="warn" title={issue}>
                ⚠ Check quality
              </Chip>
            )}
          </div>
        )}

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
