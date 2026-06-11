"use client";

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

function TrendPanel({ title, data, dataKey, unit, mean }) {
  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-3">
      <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-widest text-muted">
        {title}
      </p>
      <div className="h-44">
        <ResponsiveContainer
          width="100%"
          height="100%"
          initialDimension={{ width: 260, height: 176 }}
        >
          <LineChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: -8 }}>
            <CartesianGrid stroke="#1e3a5f" strokeOpacity={0.25} />
            <XAxis
              dataKey="n"
              tick={{ fill: "#7f8c8d", fontSize: 10 }}
              stroke="#1e3a5f"
            />
            <YAxis
              tick={{ fill: "#7f8c8d", fontSize: 10 }}
              stroke="#1e3a5f"
              domain={["auto", "auto"]}
            />
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="rounded-md border border-navy bg-surface-2 px-2.5 py-1.5 font-mono text-xs text-ink">
                    Cycle {payload[0].payload.n}: {payload[0].value?.toFixed(2)} {unit}
                  </div>
                ) : null
              }
            />
            {mean != null && (
              <ReferenceLine
                y={mean}
                stroke="#7f8c8d"
                strokeDasharray="4 4"
                label={{
                  value: "mean",
                  position: "right",
                  fill: "#7f8c8d",
                  fontSize: 10,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke="#2196f3"
              strokeWidth={2}
              dot={{ r: 3, fill: "#2196f3" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Cycle-by-cycle trends — the fatigue story made visible.
export default function CycleCharts({ cycles, session }) {
  if (!cycles?.length) return null;
  const data = cycles.map((c, i) => ({
    n: i + 1,
    arm: c.arm_peak_vel,
    dps: c.dist_m,
  }));

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TrendPanel
        title="Arm Peak Velocity per Cycle"
        data={data}
        dataKey="arm"
        unit="m/s"
        mean={session?.mean_arm_peak_vel_ms}
      />
      <TrendPanel
        title="Distance per Stroke per Cycle"
        data={data}
        dataKey="dps"
        unit="m"
        mean={session?.mean_dps_m}
      />
    </div>
  );
}
