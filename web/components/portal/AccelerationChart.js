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

// Signed companion to VelocityChart (Phase 64-03), stacked directly beneath it. Acceleration is a
// derivative of the same velocity_profile, so it swings through zero — the y-axis is symmetric
// around 0 with a zero reference line, which VelocityChart's positive-only axis is not.
//
// ⚠ This is a SEPARATE sibling, NOT an edit to VelocityChart (a hard boundary of this plan). It
// mirrors VelocityChart's decimation, cycle boundaries, fsHz and optional click-to-seek so the two
// charts read on the same time basis; it deliberately omits the Brush (a second, unsynced range
// slider next to VelocityChart's own would let the two charts drift out of x-alignment).
export default function AccelerationChart({
  time,
  acceleration,
  unitFactor = 1,
  unitLabel = "m/s²",
  markerTimeS = null,
  markerLabel = "",
  cycles = [],
  fsHz = 100,
  height = 220,
  color = "#22d3ee",
  // Optional recharts click handler — the video page seeks playback from the trace; the report
  // card omits it, so behaviour there is a static chart.
  onClick = undefined,
}) {
  const data = useMemo(() => {
    const n = Math.min(time.length, acceleration.length);
    const step = Math.max(1, Math.ceil(n / MAX_POINTS));
    const pts = [];
    for (let i = 0; i < n; i += step) {
      if (acceleration[i] == null) continue;
      pts.push({
        t: Math.round(time[i] * 100) / 100,
        a: Math.round(acceleration[i] * unitFactor * 1000) / 1000,
      });
    }
    return pts;
  }, [time, acceleration, unitFactor]);

  // Symmetric domain so 0 sits in the middle and +/- read at the same scale.
  const yMax = useMemo(() => {
    let m = 0;
    for (const p of data) {
      const abs = Math.abs(p.a);
      if (abs > m) m = abs;
    }
    return m > 0 ? Math.round(m * 1.08 * 1000) / 1000 : 1;
  }, [data]);

  // Same derivation as VelocityChart.js:50-56 — cycle bounds are sample indices.
  const boundaries = useMemo(
    () =>
      (cycles ?? [])
        .map((c) => (c.start_idx != null ? c.start_idx / fsHz : null))
        .filter((t) => t != null),
    [cycles, fsHz]
  );

  // AC-5: a NULL acceleration_profile degrades cleanly rather than erroring.
  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No acceleration data for this session.
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
        <LineChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
          onClick={onClick}
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
            domain={[-yMax, yMax]}
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
                  {payload[0].payload.a.toFixed(2)} {unitLabel}
                </div>
              ) : null
            }
          />
          {/* Signed signal → the zero line is the reference the trace is read against. */}
          <ReferenceLine y={0} stroke="#7f8c8d" strokeOpacity={0.5} />
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
            dataKey="a"
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
