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

export default function SampleChart() {
  return (
    <section className="border-t border-navy/30">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-primary">
          REAL DATA
        </p>
        <h2 className="mt-3 text-3xl font-bold">
          One real breaststroke lap, stroke by stroke
        </h2>
        <p className="mt-4 max-w-[60ch] text-subtle">
          A swimmer&apos;s actual speed through the lap. Each peak is a stroke
          driving forward; the dips between them are where the coaching
          conversation starts.
        </p>

        <div className="mt-10 h-72 w-full rounded-xl border border-navy/50 bg-surface p-4 sm:h-80">
          <ResponsiveContainer
            width="100%"
            height="100%"
            initialDimension={{ width: 520, height: 300 }}
          >
            <LineChart
              data={data}
              margin={{ top: 24, right: 16, bottom: 8, left: 0 }}
            >
              <CartesianGrid stroke="#1e3a5f" strokeOpacity={0.3} />
              <XAxis
                dataKey="t"
                type="number"
                domain={["dataMin", "dataMax"]}
                tick={{ fill: "#7f8c8d", fontSize: 12 }}
                stroke="#1e3a5f"
                unit="s"
                tickCount={8}
              />
              <YAxis
                tick={{ fill: "#7f8c8d", fontSize: 12 }}
                stroke="#1e3a5f"
                width={44}
                label={{
                  value: "m/s",
                  angle: -90,
                  position: "insideLeft",
                  fill: "#7f8c8d",
                  fontSize: 12,
                }}
              />
              <Tooltip
                cursor={{ stroke: "#1e3a5f", strokeWidth: 1 }}
                contentStyle={{
                  background: "#0f1b2d",
                  border: "1px solid #1e3a5f",
                  borderRadius: 8,
                  color: "#e6edf3",
                  fontSize: 12,
                }}
                labelFormatter={(t) => `${Number(t).toFixed(2)} s`}
                formatter={(v) => [`${Number(v).toFixed(2)} m/s`, "Speed"]}
              />
              <Line
                type="monotone"
                dataKey="v"
                stroke="#2196f3"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <ReferenceDot
                x={peak.t}
                y={peak.v}
                r={4}
                fill="#f59e0b"
                stroke="none"
                label={{
                  value: "arm pull",
                  position: "top",
                  fill: "#f59e0b",
                  fontSize: 12,
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
