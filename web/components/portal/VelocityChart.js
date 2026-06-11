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

export default function VelocityChart({
  time,
  velocity,
  unitFactor = 1,
  unitLabel = "m/s",
  markerTimeS = null,
  markerLabel = "",
  cycles = [],
  height = 320,
}) {
  const data = useMemo(() => {
    const n = Math.min(time.length, velocity.length);
    const step = Math.max(1, Math.ceil(n / MAX_POINTS));
    const pts = [];
    for (let i = 0; i < n; i += step) {
      if (velocity[i] == null) continue;
      pts.push({
        t: Math.round(time[i] * 100) / 100,
        v: Math.round(velocity[i] * unitFactor * 1000) / 1000,
      });
    }
    return pts;
  }, [time, velocity, unitFactor]);

  // Cycle boundary times (glide-phase troughs from metrics_json.cycles)
  const boundaries = useMemo(
    () =>
      (cycles ?? [])
        .map((c) => (c.start_idx != null ? c.start_idx / 100 : null))
        .filter((t) => t != null),
    [cycles]
  );

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No signal data for this session.
      </div>
    );
  }

  return (
    <div
      className="w-full min-w-0 rounded-xl border border-navy/50 bg-surface p-3"
      style={{ height }}
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 520, height }}
      >
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
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
              value: unitLabel,
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
                  {payload[0].payload.v.toFixed(2)} {unitLabel}
                </div>
              ) : null
            }
          />
          {boundaries.map((t, i) => (
            <ReferenceLine
              key={i}
              x={Math.round(t * 100) / 100}
              stroke="#1e3a5f"
              strokeOpacity={0.7}
              strokeDasharray="3 3"
            />
          ))}
          {markerTimeS != null && (
            <ReferenceLine
              x={Math.round(markerTimeS * 100) / 100}
              stroke="#f59e0b"
              strokeWidth={1.5}
              label={{
                value: markerLabel,
                position: "top",
                fill: "#f59e0b",
                fontSize: 11,
              }}
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
