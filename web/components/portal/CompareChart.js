"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

const MAX_POINTS = 2000;

// Session colours. Defined once and exported because the per-cycle overlays key off the same
// pairing — a second copy of these hexes is how the two surfaces drift into disagreeing about
// which session is which.
export const COLOR_A = "#2196f3";
export const COLOR_B = "#f59e0b";

// Two velocity traces, STACKED (61-04 D9). Previously a single overlay with both series on one
// axis; stacking is what makes "do these line up" readable, because two similar shapes drawn on
// top of each other are hardest to separate exactly when the comparison matters.
//
// ⚠ EACH PANEL USES ITS OWN SAMPLE RATE. This file used to build `t: Math.round(i)/100` for BOTH
// series — the last hardcoded rate on the web, after Phase 52 fixed the report card and Phase
// 60-01 fixed mobile. CLAUDE.md described the assumption here as deliberate ("two sessions may
// have two different rates, so there is no single axis to draw them on"); stacked panels give
// each series its own axis, which is exactly the answer, so that note is superseded.
//
// ⚠ Measured 2026-08-11: of 62 stored sessions, 56 are 90.0 Hz and 6 are NULL — none differ from
// each other. So this fixes an ~11% ABSOLUTE error applied equally to both traces, not a visible
// differential skew. The two-rate case is real but does not yet occur in the data.

function downsample(vel, fsHz, offsetS = 0) {
  const n = vel?.length ?? 0;
  if (!n) return [];
  const step = Math.max(1, Math.ceil(n / MAX_POINTS));
  const pts = [];
  for (let i = 0; i < n; i += step) {
    if (vel[i] == null) continue;
    pts.push({
      t: Math.round((i / fsHz + offsetS) * 100) / 100,
      v: Math.round(vel[i] * 1000) / 1000,
    });
  }
  return pts;
}

function TracePanel({ data, color, label, domain, height = 190 }) {
  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No signal data for {label}.
      </div>
    );
  }
  return (
    <div
      className="w-full min-w-0 rounded-xl border-l-2 bg-surface p-3"
      style={{ height, borderLeftColor: color, borderColor: "rgba(30,58,95,0.5)" }}
    >
      <p className="mb-1 px-1 text-[11px] font-semibold" style={{ color }}>
        {label}
      </p>
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 520, height: height - 26 }}
      >
        <LineChart data={data} margin={{ top: 4, right: 12, bottom: 18, left: 0 }}>
          <CartesianGrid stroke="#1e3a5f" strokeOpacity={0.25} />
          <XAxis
            dataKey="t"
            type="number"
            // Shared across both panels so features line up VERTICALLY — the whole point of
            // stacking. Each panel still derives its own `t` from its own rate.
            domain={domain}
            tick={{ fill: "#7f8c8d", fontSize: 10 }}
            stroke="#1e3a5f"
            unit="s"
            tickCount={10}
            allowDataOverflow
          />
          <YAxis
            tick={{ fill: "#7f8c8d", fontSize: 10 }}
            stroke="#1e3a5f"
            width={38}
            tickFormatter={(v) => (typeof v === "number" ? v.toFixed(1) : v)}
          />
          <Tooltip
            cursor={{ stroke: color, strokeWidth: 1 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-md border border-navy bg-surface-2 px-2.5 py-1.5 font-mono text-xs text-ink">
                  {payload[0].payload.t.toFixed(2)} s ·{" "}
                  {payload[0].value?.toFixed(2)} m/s
                </div>
              ) : null
            }
          />
          <ReferenceLine y={0} stroke="#1e3a5f" strokeOpacity={0.6} />
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function CompareChart({
  velA,
  velB,
  fsA = 100,
  fsB = 100,
  labelA,
  labelB,
  offsetS = 0, // shifts B relative to A; in-memory only, never persisted
}) {
  const dataA = useMemo(() => downsample(velA, fsA, 0), [velA, fsA]);
  const dataB = useMemo(() => downsample(velB, fsB, offsetS), [velB, fsB, offsetS]);

  // One time axis for both panels, spanning whichever trace reaches furthest (offset included),
  // so a nudge visibly moves B against a fixed grid instead of rescaling both.
  const domain = useMemo(() => {
    const lo = Math.min(0, offsetS);
    const hiA = dataA.length ? dataA[dataA.length - 1].t : 0;
    const hiB = dataB.length ? dataB[dataB.length - 1].t : 0;
    return [lo, Math.max(hiA, hiB)];
  }, [dataA, dataB, offsetS]);

  return (
    <div className="space-y-2">
      <TracePanel data={dataA} color={COLOR_A} label={labelA} domain={domain} />
      <TracePanel data={dataB} color={COLOR_B} label={labelB} domain={domain} />
    </div>
  );
}
