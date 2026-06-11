"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceDot,
} from "recharts";
import data from "@/src/data/sample-session.json";

// Annotate one representative cycle: the global arm-pull peak and the
// glide trough that follows it.
const peakIdx = data.reduce((m, p, i) => (p.v > data[m].v ? i : m), 0);
let troughIdx = peakIdx;
for (let i = peakIdx; i < data.length && data[i].t < data[peakIdx].t + 2; i++) {
  if (data[i].v < data[troughIdx].v) troughIdx = i;
}
const peak = data[peakIdx];
const trough = data[troughIdx];

export default function SampleChart() {
  return (
    <section className="border-t border-navy/30">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-primary">
          REAL DATA
        </p>
        <h2 className="mt-3 text-3xl font-bold">
          One breaststroke lap, as the encoder sees it
        </h2>
        <p className="mt-4 max-w-[60ch] text-subtle">
          An actual session from the pipeline — every arm pull, every glide.
          The peaks are propulsion; the troughs between them are where the
          coaching conversation starts.
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
              <ReferenceDot
                x={trough.t}
                y={trough.v}
                r={4}
                fill="#7f8c8d"
                stroke="none"
                label={{
                  value: "glide",
                  position: "bottom",
                  fill: "#7f8c8d",
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
