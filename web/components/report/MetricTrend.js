"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { formatValue, metricByKey } from "@/lib/reportMetrics";

function TrendChart({ metric, sessions }) {
  const data = sessions
    .map((s) => ({
      label: new Date(s.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      value: s.values?.[metric.key] ?? null,
    }))
    .filter((d) => d.value != null);

  if (data.length === 0) return null;
  const lastIdx = data.length - 1;

  return (
    <div className="min-w-0 rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
        {metric.label}
      </p>
      <div className="h-44 w-full min-w-0">
        <ResponsiveContainer
          width="100%"
          height="100%"
          initialDimension={{ width: 320, height: 176 }}
        >
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid stroke="#1e3a5f" strokeOpacity={0.25} />
            <XAxis
              dataKey="label"
              tick={{ fill: "#7f8c8d", fontSize: 10 }}
              stroke="#1e3a5f"
            />
            <YAxis
              tick={{ fill: "#7f8c8d", fontSize: 10 }}
              stroke="#1e3a5f"
              domain={["auto", "auto"]}
              width={48}
            />
            <Tooltip
              cursor={{ stroke: "#2196f3", strokeWidth: 1 }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <div className="rounded-md border border-navy bg-surface-2 px-2.5 py-1.5 font-mono text-xs text-ink">
                    {payload[0].payload.label}: {formatValue(metric, payload[0].value)}
                  </div>
                ) : null
              }
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2196f3"
              strokeWidth={2}
              isAnimationActive={false}
              dot={(props) => {
                const { key, cx, cy, index } = props;
                const emphasized = index === 0 || index === lastIdx;
                return (
                  <circle
                    key={key}
                    cx={cx}
                    cy={cy}
                    r={emphasized ? 5 : 3}
                    fill={index === lastIdx ? "#f59e0b" : "#2196f3"}
                    stroke={emphasized ? "#07090e" : "none"}
                    strokeWidth={emphasized ? 1.5 : 0}
                  />
                );
              }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function MetricTrend({ metricKeys, sessions }) {
  if (sessions.length < 2) return null;
  const metrics = metricKeys.map(metricByKey).filter(Boolean);

  return (
    <div>
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Session by Session
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {metrics.map((m) => (
          <TrendChart key={m.key} metric={m} sessions={sessions} />
        ))}
      </div>
    </div>
  );
}
