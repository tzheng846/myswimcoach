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
  Legend,
  Brush,
} from "recharts";

const MAX_POINTS = 2000;
const COLOR_A = "#2196f3";
const COLOR_B = "#f59e0b";

// Two velocity profiles overlaid, aligned at t=0 (both stored at 100 Hz).
export default function CompareChart({ velA, velB, labelA, labelB }) {
  const data = useMemo(() => {
    const n = Math.max(velA?.length ?? 0, velB?.length ?? 0);
    const step = Math.max(1, Math.ceil(n / MAX_POINTS));
    const pts = [];
    for (let i = 0; i < n; i += step) {
      pts.push({
        t: Math.round(i) / 100,
        a: velA?.[i] != null ? Math.round(velA[i] * 1000) / 1000 : null,
        b: velB?.[i] != null ? Math.round(velB[i] * 1000) / 1000 : null,
      });
    }
    return pts;
  }, [velA, velB]);

  if (data.length === 0) return null;

  return (
    <div className="h-[340px] w-full min-w-0 rounded-xl border border-navy/50 bg-surface p-3">
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 520, height: 340 }}
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
              value: "m/s",
              angle: -90,
              position: "insideLeft",
              fill: "#7f8c8d",
              fontSize: 11,
            }}
          />
          <Tooltip
            cursor={{ stroke: "#7f8c8d", strokeWidth: 1 }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div className="rounded-md border border-navy bg-surface-2 px-3 py-2 font-mono text-xs text-ink">
                  <p className="mb-1 text-muted">{Number(label).toFixed(2)} s</p>
                  {payload.map((p) =>
                    p.value != null ? (
                      <p key={p.dataKey} style={{ color: p.stroke }}>
                        {p.name}: {p.value.toFixed(2)} m/s
                      </p>
                    ) : null
                  )}
                </div>
              ) : null
            }
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => <span style={{ color: "#b0b8c4" }}>{value}</span>}
          />
          <Line
            type="monotone"
            dataKey="a"
            name={labelA}
            stroke={COLOR_A}
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="b"
            name={labelB}
            stroke={COLOR_B}
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
            connectNulls
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
