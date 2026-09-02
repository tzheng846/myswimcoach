"use client";

// LeaderboardBoard — one metric's ordering, for one stroke (Phase 90-03).
//
// Takes exactly what 90-01's `rankBoard` emits, plus `factor`/`unit` from
// `displayUnit(metric.unit, imperial)`.
//
// ⚠ `factor` is applied at the point of FORMATTING and nowhere else. Entries arrive already ranked
// on SI values; nothing here rescales before sorting, recomputes a rank from a converted number, or
// feeds a converted number back anywhere. That is what makes "the unit toggle reorders nothing"
// structural rather than hoped for (88-03 D2).
//
// ⚠ `expanded` is component-local and is NEVER reset in an effect
// (`react-hooks/set-state-in-effect` is an error in this repo). The call site keys the component on
// the stroke, so switching tabs remounts it and the board collapses.
//
// No colour coding and no good/bad thresholds (CONTEXT F8; 87-02 D9): the board states an order,
// not a verdict, and there is no validated threshold behind a green row.

import { useState } from "react";

const TOP_N = 5;

export default function LeaderboardBoard({ metric, entries, factor, unit }) {
  const [expanded, setExpanded] = useState(false);

  const ranked = (entries ?? []).filter((e) => e.value != null);
  const unranked = (entries ?? []).filter((e) => e.value == null);
  const visible = expanded ? ranked : ranked.slice(0, TOP_N);
  const decimals = metric.unit === "s" ? 1 : 2;

  return (
    <section className="rounded-xl border border-navy/50 bg-surface p-4">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">{metric.label}</h2>
        <span className="shrink-0 text-[11px] text-muted">
          {metric.direction === "lower" ? "lower is better" : "higher is better"}
        </span>
      </div>

      <ul className="mt-3 space-y-1">
        {visible.map((e) => (
          <li key={e.athleteId} className="flex items-baseline gap-2 text-sm">
            <span className="w-4 shrink-0 text-right font-mono text-xs text-muted">{e.rank}</span>
            <span className="min-w-0 flex-1 truncate text-ink">{e.name}</span>
            <span className="shrink-0 font-mono text-ink">
              {(e.value * factor).toFixed(decimals)}{" "}
              <span className="text-xs font-sans text-muted">{unit}</span>
            </span>
            <span className="w-7 shrink-0 text-right text-xs text-muted">n={e.n}</span>
          </li>
        ))}
        {unranked.map((e) => (
          <li key={e.athleteId} className="flex items-baseline gap-2 text-sm opacity-60">
            <span className="w-4 shrink-0" />
            <span className="min-w-0 flex-1 truncate text-subtle">{e.name}</span>
            <span className="shrink-0 font-mono text-muted">—</span>
            <span className="w-7 shrink-0" />
          </li>
        ))}
      </ul>

      {/* AC-2: rendered only when there is something hidden. N counts RANKED athletes — the
          unranked rows are always visible, so counting them here would promise rows that are
          already on screen. */}
      {ranked.length > TOP_N && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-xs font-semibold text-primary hover:underline"
        >
          {expanded ? `Show top ${TOP_N}` : `Show all ${ranked.length}`}
        </button>
      )}

      {unranked.length > 0 && (
        <p className="mt-2 text-[11px] leading-relaxed text-muted">
          — = no swim with this measurement, not last place.
        </p>
      )}
    </section>
  );
}
