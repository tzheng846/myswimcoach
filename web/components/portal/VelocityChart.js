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
  ReferenceArea,
} from "recharts";
import { rollingMean } from "@/lib/rollingMean";

const MAX_POINTS = 2000;

export default function VelocityChart({
  time,
  velocity,
  unitFactor = 1,
  unitLabel = "m/s",
  markerTimeS = null,
  markerLabel = "",
  // 88-04: the Segment splits picker's selected window, as a [t0, t1] pair. Defaults to null so
  // the /video route — which passes neither prop — renders byte-unchanged (AC-6). Deliberately
  // separate from markerTimeS: a window is not a point, and two cards writing one marker would
  // conflict (88-04 D1).
  spanS = null,
  spanLabel = "",
  // 88-05: averaging window for the grey dotted trend line, in SECONDS. Defaults to 0 ("off") so
  // the /video route — which passes nothing — renders byte-identically to before this plan (D5).
  // The slider that sets it lives on the report card, not in this component.
  smoothWindowS = 0,
  cycles = [],
  // The session's true sample rate (sessions.sample_rate_hz). Cycle bounds are stored
  // as sample indices, so converting them to seconds needs it. Defaults to 100 for
  // sessions recorded before Phase 52, which have no recorded rate.
  fsHz = 100,
  height = 320,
  // Optional recharts click handler (61-03). Absent on the report card, so its behaviour there
  // is unchanged; the video page uses it to seek playback from the trace.
  onClick = undefined,
}) {
  const data = useMemo(() => {
    const n = Math.min(time.length, velocity.length);
    const step = Math.max(1, Math.ceil(n / MAX_POINTS));
    // 88-05 D3: the mean is taken at the NATIVE rate and the result strided below — never the
    // other way round, which would widen the real window by `step` while the slider still read
    // "1.00 s". scratch/rolling_mean_check.mjs §5 pins the two orderings apart.
    const sm = smoothWindowS > 0 ? rollingMean(velocity, fsHz, smoothWindowS) : null;
    const pts = [];
    for (let i = 0; i < n; i += step) {
      if (velocity[i] == null) continue;
      pts.push({
        t: Math.round(time[i] * 100) / 100,
        v: Math.round(velocity[i] * unitFactor * 1000) / 1000,
        // Same factor and same precision as `v`, so a unit toggle moves both lines together
        // (AC-5). `undefined` rather than null where the window held only dropouts.
        m:
          sm && sm[i] != null
            ? Math.round(sm[i] * unitFactor * 1000) / 1000
            : undefined,
      });
    }
    return pts;
  }, [time, velocity, unitFactor, fsHz, smoothWindowS]);

  // Cycle boundary times (glide-phase troughs from metrics_json.cycles)
  const boundaries = useMemo(
    () =>
      (cycles ?? [])
        .map((c) => (c.start_idx != null ? c.start_idx / fsHz : null))
        .filter((t) => t != null),
    [cycles, fsHz]
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
                  {/* Second row only when a trend is drawn — with no trend the tooltip is the
                      single text row it has always been. */}
                  {payload[0].payload.m != null && (
                    <div className="text-[#9aa6b2]">
                      trend {payload[0].payload.m.toFixed(2)} {unitLabel}
                    </div>
                  )}
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
          {/* Drawn BEFORE the marker so Time-to-Distance's line stays on top of the shading. */}
          {spanS && (
            <ReferenceArea
              x1={Math.round(spanS[0] * 100) / 100}
              x2={Math.round(spanS[1] * 100) / 100}
              fill="#f59e0b"
              fillOpacity={0.12}
              stroke="none"
              label={{
                value: spanLabel,
                position: "insideTop",
                fill: "#f59e0b",
                fontSize: 11,
              }}
            />
          )}
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
          {/* 88-05 D4: grey, and a coarser dash than the cycle boundaries (#1e3a5f "3 3") and the
              amber TimeToX marker, so the trend reads as neither. Deliberately NOT #7f8c8d — a
              data line must not share a colour with the axis chrome. Drawn after the raw trace so
              it sits on top of it, and omitted entirely at 0.00 s (D2/AC-3) rather than degenerating
              into a duplicate of the line beneath it. */}
          {smoothWindowS > 0 && (
            <Line
              type="monotone"
              dataKey="m"
              stroke="#9aa6b2"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              isAnimationActive={false}
              connectNulls={false}
            />
          )}
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
