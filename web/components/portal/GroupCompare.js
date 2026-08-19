"use client";

// Phase 73 — Group Comparison (A/B experiments). Two labeled groups of ONE athlete's SAME-stroke
// swims, compared per metric: each swim a dot, group means, the delta, and an honest clear/overlapping
// cue. Metrics only (no traces), no p-values (n is tiny — CONTEXT D4). Web-only; reuses the Compare
// supabase-read + client-stats pattern.

import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
import { COLOR_A, COLOR_B } from "@/components/portal/CompareChart";
import { REPORT_METRICS, formatValue } from "@/lib/reportMetrics";
import { metricComparison } from "@/lib/groupStats";
import { sessionLabel } from "@/lib/sessionName";

const STROKE_LABELS = {
  freestyle: "Freestyle",
  backstroke: "Backstroke",
  breaststroke: "Breaststroke",
  butterfly: "Butterfly",
  im: "Individual Medley",
  udk: "Underwater Dolphin Kick",
};

// Compact SVG strip plot: group-A swims as dots above a shared axis, group-B below, means as ticks.
function StripPlot({ valuesA, valuesB, meanA, meanB }) {
  const W = 300, H = 46, PAD = 10, midY = H / 2;
  const all = [...valuesA, ...valuesB];
  if (all.length === 0) return null;
  let lo = Math.min(...all), hi = Math.max(...all);
  if (lo === hi) { lo -= 1; hi += 1; } // avoid zero-width domain for a single distinct value
  const x = (v) => PAD + ((v - lo) / (hi - lo)) * (W - 2 * PAD);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" style={{ maxHeight: H }}>
      <line x1={PAD} y1={midY} x2={W - PAD} y2={midY} stroke="currentColor" strokeOpacity="0.15" />
      {meanA != null && (
        <line x1={x(meanA)} y1={midY - 15} x2={x(meanA)} y2={midY} stroke={COLOR_A} strokeWidth="2" />
      )}
      {meanB != null && (
        <line x1={x(meanB)} y1={midY} x2={x(meanB)} y2={midY + 15} stroke={COLOR_B} strokeWidth="2" />
      )}
      {valuesA.map((v, i) => (
        <circle key={`a${i}`} cx={x(v)} cy={midY - 8} r="3.5" fill={COLOR_A} fillOpacity="0.85" />
      ))}
      {valuesB.map((v, i) => (
        <circle key={`b${i}`} cx={x(v)} cy={midY + 8} r="3.5" fill={COLOR_B} fillOpacity="0.85" />
      ))}
    </svg>
  );
}

function CueBadge({ separation }) {
  const map = {
    clear: { text: "Clear difference", cls: "border-accent text-accent" },
    overlapping: { text: "Overlapping — likely noise", cls: "border-surface-3 text-muted" },
    insufficient: { text: "Add ≥2 swims per group", cls: "border-surface-3 text-muted" },
  };
  const { text, cls } = map[separation] ?? map.insufficient;
  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>{text}</span>;
}

function GroupMetricRow({ metric, valuesA, valuesB, labelA, labelB }) {
  const cmp = metricComparison(metric, valuesA, valuesB);
  const { a, b, deltaAbs, deltaPct, betterSide, separation } = cmp;
  const deltaColor =
    betterSide === "B" ? "text-[#3ecf8e]" : betterSide === "A" ? "text-[#ff5252]" : "text-subtle";
  return (
    <div className="rounded-xl border border-surface-3 bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{metric.label}</p>
        <CueBadge separation={separation} />
      </div>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
        <span style={{ color: COLOR_A }} className="font-medium">
          {labelA}: {a.mean == null ? "--" : formatValue(metric, a.mean)}{" "}
          <span className="text-xs text-muted">(n={a.n})</span>
        </span>
        <span style={{ color: COLOR_B }} className="font-medium">
          {labelB}: {b.mean == null ? "--" : formatValue(metric, b.mean)}{" "}
          <span className="text-xs text-muted">(n={b.n})</span>
        </span>
        {deltaAbs != null && (
          <span className={`ml-auto font-mono text-xs ${deltaColor}`}>
            Δ {deltaAbs >= 0 ? "+" : ""}{formatValue(metric, deltaAbs)}
            {deltaPct != null ? ` (${deltaPct >= 0 ? "+" : ""}${deltaPct.toFixed(1)}%)` : ""}
          </span>
        )}
      </div>
      <StripPlot valuesA={valuesA} valuesB={valuesB} meanA={a.mean} meanB={b.mean} />
    </div>
  );
}

export default function GroupCompare({ athletes }) {
  const [athleteId, setAthleteId] = useState("");
  const [stroke, setStroke] = useState("");
  const [allSessions, setAllSessions] = useState([]);
  const [assignment, setAssignment] = useState({}); // { sessionId: 'A' | 'B' }
  const [labelA, setLabelA] = useState("Group A");
  const [labelB, setLabelB] = useState("Group B");

  // Switching athlete resets the dependent selections (done in the handler, not an effect, to avoid
  // cascading-render churn), then the effect below fetches that athlete's sessions.
  const selectAthlete = (v) => {
    setAthleteId(v);
    setStroke("");
    setAssignment({});
    if (!v) setAllSessions([]);
  };

  // One query per athlete: all their sessions with the scalar metrics we compare on.
  useEffect(() => {
    if (!athleteId) return;
    let cancelled = false;
    supabase
      .from("sessions")
      .select("id, created_at, name, stroke_type, session:metrics_json->session")
      .eq("athlete_id", athleteId)
      .order("created_at", { ascending: false })
      .then(({ data }) => { if (!cancelled) setAllSessions(data ?? []); });
    return () => { cancelled = true; };
  }, [athleteId]);

  const strokeOptions = useMemo(
    () => [...new Set(allSessions.map((s) => s.stroke_type).filter(Boolean))],
    [allSessions]
  );

  // Same stroke only (D6): assignment resets when the stroke changes.
  const sessions = useMemo(
    () => (stroke ? allSessions.filter((s) => s.stroke_type === stroke) : []),
    [allSessions, stroke]
  );

  const toggle = (id, group) =>
    setAssignment((prev) => {
      const next = { ...prev };
      if (next[id] === group) delete next[id]; // clicking the active group unassigns
      else next[id] = group; // moves out of the other group by construction (single map)
      return next;
    });

  const groupA = sessions.filter((s) => assignment[s.id] === "A");
  const groupB = sessions.filter((s) => assignment[s.id] === "B");
  const valuesFor = (grp, key) => grp.map((s) => s.session?.[key]);
  const ready = groupA.length >= 1 && groupB.length >= 1;

  return (
    <div className="mt-5 space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row">
        <select
          value={athleteId}
          onChange={(e) => selectAthlete(e.target.value)}
          className="rounded-lg border border-surface-3 bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
        >
          <option value="">Select athlete…</option>
          {athletes.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <select
          value={stroke}
          onChange={(e) => { setStroke(e.target.value); setAssignment({}); }}
          disabled={!athleteId}
          className="rounded-lg border border-surface-3 bg-surface px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-50"
        >
          <option value="">Select stroke…</option>
          {strokeOptions.map((s) => (
            <option key={s} value={s}>{STROKE_LABELS[s] ?? s}</option>
          ))}
        </select>
      </div>

      {stroke && (
        <>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              value={labelA}
              onChange={(e) => setLabelA(e.target.value)}
              className="flex-1 rounded-lg border-l-4 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
              style={{ borderLeftColor: COLOR_A }}
            />
            <input
              value={labelB}
              onChange={(e) => setLabelB(e.target.value)}
              className="flex-1 rounded-lg border-l-4 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
              style={{ borderLeftColor: COLOR_B }}
            />
          </div>

          {sessions.length === 0 ? (
            <p className="text-sm text-muted">No {STROKE_LABELS[stroke] ?? stroke} sessions for this athlete.</p>
          ) : (
            <div className="space-y-1.5">
              <p className="text-xs text-muted">
                Assign each swim to {labelA || "Group A"} or {labelB || "Group B"} (a swim can be in one group).
              </p>
              {sessions.map((s) => {
                const g = assignment[s.id];
                return (
                  <div
                    key={s.id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-surface-3 bg-surface px-3 py-2"
                    style={g ? { borderColor: g === "A" ? COLOR_A : COLOR_B } : undefined}
                  >
                    <span className="min-w-0 truncate text-sm text-subtle">
                      {sessionLabel(s, { withStroke: false })}
                    </span>
                    <div className="flex shrink-0 gap-1">
                      {["A", "B"].map((grp) => {
                        const active = g === grp;
                        const color = grp === "A" ? COLOR_A : COLOR_B;
                        return (
                          <button
                            key={grp}
                            onClick={() => toggle(s.id, grp)}
                            className="rounded-md border px-2.5 py-1 text-xs font-semibold"
                            style={
                              active
                                ? { backgroundColor: color, borderColor: color, color: "#fff" }
                                : { borderColor: "var(--surface-3, #333)", color: color }
                            }
                          >
                            {grp === "A" ? labelA || "A" : labelB || "B"}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {ready ? (
        <div className="space-y-3">
          <p className="text-sm text-muted">
            {labelA} (n={groupA.length}) vs {labelB} (n={groupB.length}) — each dot is one swim; the cue
            flags whether the groups clearly separate.
          </p>
          {REPORT_METRICS.map((metric) => (
            <GroupMetricRow
              key={metric.key}
              metric={metric}
              valuesA={valuesFor(groupA, metric.key)}
              valuesB={valuesFor(groupB, metric.key)}
              labelA={labelA || "Group A"}
              labelB={labelB || "Group B"}
            />
          ))}
        </div>
      ) : (
        stroke && sessions.length > 0 && (
          <p className="text-center text-sm text-muted">Assign at least one swim to each group to compare.</p>
        )
      )}
    </div>
  );
}
