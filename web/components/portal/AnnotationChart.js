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
  Brush,
  ReferenceLine,
} from "recharts";

const MAX_POINTS = 2000;

// Canonical phase order matches annotations.py PHASE_KEYS.
// "underwater" displays as "Pulldown" for breaststroke (display concern only).
export const PHASE_META = [
  { key: "dive_start_s", label: "Dive", color: "#fb923c" },
  {
    key: "underwater_start_s",
    label: "UW kick",
    breaststrokeLabel: "Pulldown",
    color: "#c084fc",
  },
  { key: "breakout_start_s", label: "Breakout", color: "#22d3ee" },
  { key: "stroke_start_s", label: "Stroke", color: "#4ade80" },
  { key: "finish_s", label: "Finish", color: "#f87171" },
];

export function phaseLabel(meta, strokeType) {
  return strokeType === "breaststroke" && meta.breaststrokeLabel
    ? meta.breaststrokeLabel
    : meta.label;
}

// Click-to-mark velocity chart for the annotation editor. Modeled on the shared
// VelocityChart (which report card + compare depend on — deliberately not reused).
export default function AnnotationChart({
  time,
  velocity,
  phases = {},
  strokeMarks = [],
  playheadS = null,
  strokeType,
  onChartClick,
  height = 340,
}) {
  const data = useMemo(() => {
    const n = Math.min(time.length, velocity.length);
    const step = Math.max(1, Math.ceil(n / MAX_POINTS));
    const pts = [];
    for (let i = 0; i < n; i += step) {
      if (velocity[i] == null) continue;
      pts.push({
        t: Math.round(time[i] * 100) / 100,
        v: Math.round(velocity[i] * 1000) / 1000,
      });
    }
    return pts;
  }, [time, velocity]);

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No signal data for this session.
      </div>
    );
  }

  return (
    <div
      className="w-full min-w-0 cursor-crosshair rounded-xl border border-navy/50 bg-surface p-3"
      style={{ height }}
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 520, height }}
      >
        <LineChart
          data={data}
          margin={{ top: 18, right: 12, bottom: 0, left: 0 }}
          onClick={(state) => {
            if (state && state.activeLabel != null && onChartClick) {
              onChartClick(Number(state.activeLabel));
            }
          }}
        >
          <CartesianGrid stroke="#1e3a5f" strokeOpacity={0.25} />
          <XAxis
            dataKey="t"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={{ fill: "#7f8c8d", fontSize: 11 }}
            stroke="#1e3a5f"
            unit="s"
            tickCount={10}
          />
          <YAxis
            tick={{ fill: "#7f8c8d", fontSize: 11 }}
            stroke="#1e3a5f"
            width={42}
            label={{
              value: "m/s",
              angle: -90,
              position: "insideLeft",
              fill: "#7f8c8d",
              fontSize: 11,
            }}
          />
          <Tooltip
            cursor={{ stroke: "#2196f3", strokeWidth: 1 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-md border border-navy bg-surface-2 px-3 py-1.5 font-mono text-xs text-ink">
                  {payload[0].payload.t.toFixed(2)} s ·{" "}
                  {payload[0].payload.v.toFixed(2)} m/s
                </div>
              ) : null
            }
          />
          {/* Individual stroke marks — thin, low-opacity dashed */}
          {strokeMarks.map((t, i) => (
            <ReferenceLine
              key={`m${i}`}
              x={Math.round(t * 100) / 100}
              stroke="#94a3b8"
              strokeOpacity={0.45}
              strokeDasharray="2 4"
            />
          ))}
          {/* Phase boundaries — colored + labeled */}
          {PHASE_META.map((meta) =>
            phases[meta.key] != null ? (
              <ReferenceLine
                key={meta.key}
                x={Math.round(phases[meta.key] * 100) / 100}
                stroke={meta.color}
                strokeWidth={1.5}
                label={{
                  value: phaseLabel(meta, strokeType),
                  position: "top",
                  fill: meta.color,
                  fontSize: 10,
                }}
              />
            ) : null
          )}
          {/* Video playhead */}
          {playheadS != null && (
            <ReferenceLine
              x={Math.round(playheadS * 100) / 100}
              stroke="#f59e0b"
              strokeWidth={1.5}
            />
          )}
          <Line
            type="monotone"
            dataKey="v"
            stroke="#2196f3"
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
          />
          <Brush
            dataKey="t"
            height={26}
            stroke="#1e3a5f"
            fill="#1a1a1a"
            travellerWidth={8}
            tickFormatter={(t) => `${t}s`}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
