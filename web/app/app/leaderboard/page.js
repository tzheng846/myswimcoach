"use client";

// Phase 90-02 — the /app/leaderboard route: the right swims, in the right stroke, with the
// assumptions stated. Phase 90-03 replaced 90-02's placeholder per-metric count with the eight
// real boards and the unit toggle.
//
// ⚠ The toggle reads the STANDING `swimnetics.unit` preference (`useUnitPref`), the same one the
// report card and /video already share — a coach who set yards there sees yards here without
// touching anything. Conversion is `displayUnit` at the last moment; `rankBoard` never sees a
// converted number (88-03 D2), so flipping units cannot reorder a board.

import { useEffect, useMemo, useState } from "react";
import { fetchLeaderboard } from "@/lib/leaderboardData";
import {
  DEFAULT_N,
  LEADERBOARD_METRICS,
  MIN_DIST_M,
  rankBoard,
} from "@/lib/leaderboard";
import { displayUnit } from "@/lib/unitConvert";
import useUnitPref from "@/lib/useUnitPref";
import LeaderboardBoard from "@/components/portal/LeaderboardBoard";
import { STROKE_LABELS } from "@/components/portal/SessionCard";

export default function LeaderboardPage() {
  const [data, setData] = useState(undefined); // undefined = loading, null = error
  const [stroke, setStroke] = useState(null);
  const { unit, setUnit } = useUnitPref();

  useEffect(() => {
    let live = true;
    fetchLeaderboard()
      .then((d) => live && setData(d))
      .catch(() => live && setData(null));
    return () => {
      live = false;
    };
  }, []);

  // One tab per stroke that has at least one eligible swim — so a stroke the guard emptied simply
  // is not offered. Today that removes Underwater Dolphin Kick: all five udk sessions are one
  // athlete's, and every one of them is under the 15 m guard.
  const tabs = useMemo(() => {
    const byStroke = new Map();
    for (const row of data?.rows ?? []) {
      if (!byStroke.has(row.stroke_type)) byStroke.set(row.stroke_type, []);
      byStroke.get(row.stroke_type).push(row);
    }
    return [...byStroke.entries()]
      .map(([key, rows]) => ({
        key,
        label: STROKE_LABELS[key] ?? key,
        rows,
        athletes: new Set(rows.map((r) => r.athlete_id)).size,
        swims: rows.length,
      }))
      .sort((a, b) => b.swims - a.swims || (a.label < b.label ? -1 : 1));
  }, [data]);

  if (data === undefined) return <p className="text-muted">Loading…</p>;
  if (data === null) return <p className="text-muted">Couldn’t load the leaderboard.</p>;

  // The selected tab is DERIVED, never clamped by a state reset in an effect: this repo's eslint
  // treats react-hooks/set-state-in-effect as an error, and 87-02 shipped a defect learning it.
  const active = tabs.find((t) => t.key === stroke) ?? tabs[0] ?? null;

  return (
    <div>
      <h1 className="text-2xl font-bold">Leaderboard</h1>
      <p className="mt-1 text-sm text-muted">
        How your swimmers rank against each other, one stroke at a time.
      </p>

      {!active ? (
        <p className="mt-10 text-center text-sm text-muted">
          {data.total > 0
            ? `Nothing to rank yet — all ${data.total} of your swims cover under ${MIN_DIST_M} m, which is the likeliest reason a swim is missing here.`
            : "Nothing to rank yet — no swims have been uploaded for your athletes."}
        </p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex flex-wrap rounded-lg border border-surface-3 bg-surface p-0.5 text-sm">
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setStroke(t.key)}
                  className={`rounded-md px-3 py-1.5 font-semibold transition-colors ${
                    t.key === active.key
                      ? "bg-primary text-white"
                      : "text-subtle hover:text-ink"
                  }`}
                >
                  {t.label}{" "}
                  <span className="font-normal opacity-80">
                    {t.athletes} athletes · {t.swims} swims
                  </span>
                </button>
              ))}
            </div>

            {/* The same control the report card uses, on the same stored preference. */}
            <div className="flex gap-1.5">
              {["metric", "imperial"].map((u) => (
                <button
                  key={u}
                  onClick={() => setUnit(u)}
                  className={`rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
                    unit === u
                      ? "border-accent bg-accent text-white"
                      : "border-surface-3 bg-surface-2 text-subtle"
                  }`}
                >
                  {u === "metric" ? "m" : "yd"}
                </button>
              ))}
            </div>
          </div>

          {/* Both assumptions, stated once, where a coach reading a rank will see them. */}
          <div className="mt-4 rounded-xl border border-navy/50 bg-surface px-4 py-3 text-xs leading-relaxed text-muted">
            <p>
              Every swim here is compared as a <span className="text-subtle">25 yd effort</span>.
              Nothing in the recorded data confirms the distance — a swim of another length ranks
              as if it were 25 yd.
            </p>
            <p className="mt-1.5">
              <span className="text-subtle">
                {data.excluded} of {data.total} swims
              </span>{" "}
              are excluded for covering under {MIN_DIST_M} m of tether travel, which is too short
              to compare.
            </p>
            <p className="mt-1.5">
              A row is the mean of an athlete’s last {DEFAULT_N} swims of that stroke, newest
              first — ordered by <span className="text-subtle">upload</span> time, which is the
              only timestamp every session has.
            </p>
          </div>

          {/* Eight boards in catalog order. The `key` carries the stroke, so a tab switch
              REMOUNTS every board and its "show all" collapses — no expanded state leaks across
              tabs, and no state is reset in an effect to achieve it. */}
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {LEADERBOARD_METRICS.map((metric) => {
              const { factor, unit: displayed } = displayUnit(metric.unit, unit === "imperial");
              return (
                <LeaderboardBoard
                  key={`${active.key}:${metric.key}`}
                  metric={metric}
                  entries={rankBoard(active.rows, metric, {
                    nameFor: (id) => data.athletes.get(id) ?? String(id),
                  })}
                  factor={factor}
                  unit={displayed}
                />
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
