"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceDot,
  Tooltip,
} from "recharts";
import data from "@/src/data/sample-session.json";

// Annotate one representative cycle: the global arm-pull peak.
const peakIdx = data.reduce((m, p, i) => (p.v > data[m].v ? i : m), 0);
const peak = data[peakIdx];

// Rendered inside the Hero's floating card — no section chrome of its own.
export default function SampleChart() {
  return (
    <div>
      <p className="text-xs font-semibold tracking-[0.3em] text-brand">
        REAL DATA
      </p>
      <h2 className="mt-2 text-xl font-bold text-ink-900 sm:text-2xl">
        One real breaststroke lap, stroke by stroke
      </h2>
      <p className="mt-2 max-w-[60ch] text-sm text-ink-600">
        A swimmer&apos;s actual speed through the lap. Each peak is a stroke
        driving forward; the dips between them are where the coaching
        conversation starts.
      </p>

      <div className="mt-5 h-64 w-full sm:h-72">
        <ResponsiveContainer
          width="100%"
          height="100%"
          initialDimension={{ width: 520, height: 280 }}
        >
          <LineChart data={data} margin={{ top: 24, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="#e8e4f2" />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              tick={{ fill: "#9b8ba6", fontSize: 12 }}
              stroke="#e8e4f2"
              unit="s"
              tickCount={8}
            />
            <YAxis
              tick={{ fill: "#9b8ba6", fontSize: 12 }}
              stroke="#e8e4f2"
              width={44}
              label={{
                value: "m/s",
                angle: -90,
                position: "insideLeft",
                fill: "#9b8ba6",
                fontSize: 12,
              }}
            />
            <Tooltip
              cursor={{ stroke: "#858ae3", strokeWidth: 1 }}
              contentStyle={{
                background: "#ffffff",
                border: "1px solid #e8e4f2",
                borderRadius: 12,
                color: "#2c0735",
                fontSize: 12,
                boxShadow: "0 8px 24px rgba(44,7,53,0.12)",
              }}
              labelFormatter={(t) => `${Number(t).toFixed(2)} s`}
              formatter={(v) => [`${Number(v).toFixed(2)} m/s`, "Speed"]}
            />
            <Line
              type="monotone"
              dataKey="v"
              stroke="#4e148c"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
            <ReferenceDot
              x={peak.t}
              y={peak.v}
              r={4}
              fill="#613dc1"
              stroke="none"
              label={{
                value: "arm pull",
                position: "top",
                fill: "#613dc1",
                fontSize: 12,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
