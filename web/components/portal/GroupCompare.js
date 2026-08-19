"use client";

// Phase 73 — Group Comparison (A/B experiments). Two labeled groups of ONE athlete's SAME-stroke
// swims, compared across metrics. Headline = DIFFERENCE BARS (one bar per metric = Group B vs A:
// length = size of change, direction = which way B moved, colour = better/worse, faded = the groups
// overlap so it's likely noise). Per-metric line charts are the drill-down. Metrics only (no traces),
// no p-values (n is tiny — CONTEXT D4). Web-only; reuses the Compare supabase-read + client-stats path.

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

// Valence colours (match the per-metric delta text below): better / worse / no-better-side.
const GOOD = "#3ecf8e", BAD = "#ff5252";

const SEP = {
  clear: { text: "Clear difference", cls: "border-accent text-accent" },
  overlapping: { text: "Overlapping — likely noise", cls: "border-surface-3 text-muted" },
  insufficient: { text: "Add ≥2 swims per group", cls: "border-surface-3 text-muted" },
};

function CueBadge({ separation }) {
  const { text, cls } = SEP[separation] ?? SEP.insufficient;
  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>{text}</span>;
}

// ── HEADLINE: difference bars — Group B vs Group A, one bar per metric ──────────
function DiffBars({ rows, labelA, labelB }) {
  const data = rows
    .filter((r) => r.cmp.a.mean != null && r.cmp.b.mean != null && r.cmp.a.mean !== 0)
    .map((r) => {
      const { cmp, metric } = r;
      const pct = ((cmp.b.mean - cmp.a.mean) / Math.abs(cmp.a.mean)) * 100;
      const valence = cmp.betterSide === "B" ? "good" : cmp.betterSide === "A" ? "bad" : "neutral";
      return { metric, pct, valence, faded: cmp.separation !== "clear" };
    });
  if (data.length === 0) return null;

  const W = 720, rowH = 40, padT = 10, padB = 8, L = 152, R = 66;
  const H = padT + padB + data.length * rowH;
  const axis = L + (W - R - L) / 2;
  const half = (W - R - L) / 2;
  const maxAbs = Math.max(...data.map((d) => Math.abs(d.pct)), 1) * 1.12;
  const x = (pct) => axis + (pct / maxAbs) * half;
  const color = (v) => (v === "good" ? GOOD : v === "bad" ? BAD : "var(--muted, #93a3b8)");

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-3 bg-surface p-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 460 }} role="img"
        aria-label={`Difference in each metric, ${labelB} versus ${labelA}`}>
        <line x1={axis} y1={padT} x2={axis} y2={H - padB} stroke="var(--line, #223044)" strokeWidth="1.5" />
        {data.map((d, i) => {
          const cy = padT + i * rowH + rowH / 2;
          const c = color(d.valence);
          const xe = x(d.pct);
          const bx = Math.min(axis, xe), bw = Math.max(Math.abs(xe - axis), 1.5);
          return (
            <g key={d.metric.key} opacity={d.faded ? 0.4 : 1}>
              <rect x={bx} y={cy - 10} width={bw} height={20} rx="4" fill={c} />
              <text x={L - 12} y={cy + 4} textAnchor="end" fontSize="12" fontWeight="600"
                fill="var(--ink, #e9f0f8)" fontFamily="inherit">{d.metric.label}</text>
              <text x={xe + (d.pct >= 0 ? 8 : -8)} y={cy + 4} textAnchor={d.pct >= 0 ? "start" : "end"}
                fontSize="11.5" fontWeight="600" fill={c} fontFamily="inherit">
                {(d.pct >= 0 ? "+" : "") + d.pct.toFixed(1) + "%" + (d.faded ? " ~" : "")}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── DRILL-DOWN: one small line chart per metric (real Y-axis, a line per group) ─
function SmallMultiple({ metric, valuesA, valuesB, meanA, meanB }) {
  const W = 340, H = 150, L = 46, R = 12, T = 12, B = 24;
  const all = [...valuesA, ...valuesB];
  if (all.length === 0) return null;
  let lo = Math.min(...all), hi = Math.max(...all);
  const pad = (hi - lo) * 0.18 || 1; lo -= pad; hi += pad;
  const maxN = Math.max(valuesA.length, valuesB.length);
  const x = (i) => L + (maxN <= 1 ? 0.5 : i / (maxN - 1)) * (W - L - R);
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const line = (vals, colr, mean) => (
    <g>
      {mean != null && (
        <line x1={L} y1={y(mean)} x2={W - R} y2={y(mean)} stroke={colr} strokeWidth="1"
          strokeDasharray="3 4" strokeOpacity="0.6" />
      )}
      <path d={vals.map((v, i) => (i ? "L" : "M") + x(i) + " " + y(v)).join(" ")} fill="none"
        stroke={colr} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
      {vals.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r="3.2" fill={colr} />)}
    </g>
  );
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-1 w-full" role="img">
      {[0, 1, 2].map((t) => {
        const val = lo + (t / 2) * (hi - lo);
        return (
          <g key={t}>
            <line x1={L} y1={y(val)} x2={W - R} y2={y(val)} stroke="var(--line, #223044)" strokeOpacity="0.5" />
            <text x={L - 8} y={y(val) + 4} textAnchor="end" fontSize="10" fill="var(--muted, #93a3b8)"
              fontFamily="inherit">{val.toFixed(metric.decimals)}</text>
          </g>
        );
      })}
      {line(valuesA, COLOR_A, meanA)}
      {line(valuesB, COLOR_B, meanB)}
    </svg>
  );
}

function MetricDetail({ row, labelA, labelB }) {
  const { metric, valuesA, valuesB, cmp } = row;
  const { a, b, deltaAbs, deltaPct, betterSide } = cmp;
  const deltaColor =
    betterSide === "B" ? "text-[#3ecf8e]" : betterSide === "A" ? "text-[#ff5252]" : "text-subtle";
  return (
    <div className="rounded-xl border border-surface-3 bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{metric.label}</p>
        <CueBadge separation={cmp.separation} />
      </div>
      <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
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
      <SmallMultiple metric={metric} valuesA={valuesA} valuesB={valuesB} meanA={a.mean} meanB={b.mean} />
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
  const [showDetail, setShowDetail] = useState(false);

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
  const sessions = useMemo(
    () => (stroke ? allSessions.filter((s) => s.stroke_type === stroke) : []),
    [allSessions, stroke]
  );

  const toggle = (id, group) =>
    setAssignment((prev) => {
      const next = { ...prev };
      if (next[id] === group) delete next[id];
      else next[id] = group;
      return next;
    });

  const groupA = sessions.filter((s) => assignment[s.id] === "A");
  const groupB = sessions.filter((s) => assignment[s.id] === "B");
  const ready = groupA.length >= 1 && groupB.length >= 1;

  // Per-metric computed comparison (shared by the headline bars and the drill-down).
  const rows = useMemo(() => {
    if (!ready) return [];
    const valuesFor = (grp, key) => grp.map((s) => s.session?.[key]);
    return REPORT_METRICS.map((metric) => {
      const valuesA = valuesFor(groupA, metric.key);
      const valuesB = valuesFor(groupB, metric.key);
      return { metric, valuesA, valuesB, cmp: metricComparison(metric, valuesA, valuesB) };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, assignment, sessions]);

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
                        const colr = grp === "A" ? COLOR_A : COLOR_B;
                        return (
                          <button
                            key={grp}
                            onClick={() => toggle(s.id, grp)}
                            className="rounded-md border px-2.5 py-1 text-xs font-semibold"
                            style={
                              active
                                ? { backgroundColor: colr, borderColor: colr, color: "#fff" }
                                : { borderColor: "var(--surface-3, #333)", color: colr }
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
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <span style={{ color: COLOR_A }} className="font-semibold">{labelA} (n={groupA.length})</span>
            <span style={{ color: COLOR_B }} className="font-semibold">{labelB} (n={groupB.length})</span>
            <span className="text-muted">
              each bar = {labelB || "B"} vs {labelA || "A"} · length = size of change ·
              <span style={{ color: GOOD }} className="font-medium"> green better</span> /
              <span style={{ color: BAD }} className="font-medium"> red worse</span> · faded = overlapping
            </span>
          </div>

          <DiffBars rows={rows} labelA={labelA || "Group A"} labelB={labelB || "Group B"} />

          <button
            onClick={() => setShowDetail((v) => !v)}
            className="rounded-lg border border-surface-3 bg-surface-2 px-3 py-1.5 text-sm font-semibold text-subtle hover:text-ink"
          >
            {showDetail ? "Hide per-metric detail ▴" : "Show per-metric detail ▾"}
          </button>

          {showDetail && (
            <div className="grid gap-3 sm:grid-cols-2">
              {rows.map((row) => (
                <MetricDetail
                  key={row.metric.key}
                  row={row}
                  labelA={labelA || "Group A"}
                  labelB={labelB || "Group B"}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        stroke && sessions.length > 0 && (
          <p className="text-center text-sm text-muted">Assign at least one swim to each group to compare.</p>
        )
      )}
    </div>
  );
}
