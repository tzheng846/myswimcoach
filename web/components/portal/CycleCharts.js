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

// Per-cycle trends — the shape of a swim, not four averages of it.
//
// Four panels, matching what mobile shipped in Phase 60-01 (swimnetics-mobile
// src/components/CycleCharts.js). Mobile hand-rolls its SVG because it has no chart library;
// the web has recharts, so this stays on recharts.
//
// ⚠ THE MEAN LINE MEANS DIFFERENT THINGS ON DIFFERENT SESSION VINTAGES — see `legacy` below.
// Phase 61-01 removed the steady/ramp_up cycle split, so for anything computed after it the
// session mean IS the average of the plotted dots. Sessions stored before it keep steady-only
// means and will not line up. The caveat is shown per-session, never unconditionally.

function TrendPanel({ title, caption, data, dataKey, unit, mean, decimals = 2 }) {
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
                    Cycle {payload[0].payload.n}:{" "}
                    {payload[0].value?.toFixed(decimals)} {unit}
                  </div>
                ) : null
              }
            />
            {mean != null && Number.isFinite(mean) && (
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
      {caption && (
        <p className="mt-1.5 px-1 text-[11px] leading-relaxed text-muted">{caption}</p>
      )}
    </div>
  );
}

const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const fmt = (v, d = 2) => (num(v) != null ? v.toFixed(d) : "--");
const pct = (v) => (num(v) != null ? `${(v * 100).toFixed(0)}%` : "--");

export default function CycleCharts({ cycles, session, unit = "metric" }) {
  if (!cycles?.length) return null;

  const s = session ?? {};
  const imp = unit === "imperial";
  const factor = imp ? 1.09361 : 1;
  const distUnit = imp ? "yd" : "m";
  const velUnit = imp ? "yd/s" : "m/s";
  const scale = (v) => (num(v) != null ? v * factor : null);

  // Session vintage, decided from the DATA rather than a date. Phase 61-01 stopped emitting
  // `phase` on cycle dicts, so its presence means the stored metrics were computed by the old
  // code — whose means and CVs covered steady cycles only.
  const legacy = cycles.some((c) => c && "phase" in c);

  const data = cycles.map((c, i) => ({
    n: i + 1,
    dps: scale(c.dist_m),
    coast: num(c.coast_fraction) != null ? c.coast_fraction * 100 : null,
    dur: num(c.duration_s),
    arm: scale(c.arm_peak_vel),
  }));

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <TrendPanel
          title="Distance per Stroke"
          data={data}
          dataKey="dps"
          unit={distUnit}
          mean={scale(s.mean_dps_m)}
          caption={`mean ${fmt(scale(s.mean_dps_m))} ${distUnit}`}
        />
        <TrendPanel
          title="Coast"
          data={data}
          dataKey="coast"
          unit="%"
          mean={num(s.mean_coast_fraction) != null ? s.mean_coast_fraction * 100 : null}
          decimals={0}
          caption={`mean ${pct(s.mean_coast_fraction)} of each cycle spent gliding`}
        />
        <TrendPanel
          title="Cycle Duration"
          data={data}
          dataKey="dur"
          unit="s"
          mean={num(s.mean_isi_s)}
          caption={`mean ${fmt(s.mean_isi_s)} s · rhythm consistency (CV) ${pct(s.cv_isi)}`}
        />
        <TrendPanel
          title="Arm Peak Velocity"
          data={data}
          dataKey="arm"
          unit={velUnit}
          mean={scale(s.mean_arm_peak_vel_ms)}
          caption={`mean ${fmt(scale(s.mean_arm_peak_vel_ms))} ${velUnit} · power consistency (CV) ${pct(s.cv_arm_peak_vel)}`}
        />
      </div>
      <p className="px-1 text-[11px] leading-relaxed text-muted">
        One point per detected cycle.
        {legacy
          ? " This session was processed before the cycle-counting fix, so its means and CVs cover" +
            " only steady-state cycles — the dashed line may not sit at the visual average of the dots."
          : " Means and CVs cover every cycle shown, so the dashed line is the average of the dots."}
      </p>
    </>
  );
}
