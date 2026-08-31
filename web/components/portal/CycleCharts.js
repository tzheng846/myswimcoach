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

// Exported for CompareCycleCharts (61-04 D11), which renders the same panel with two series.
// One chart primitive, two callers — a second copy is how the report card and Compare drift into
// looking like different products.
export function TrendPanel({
  title,
  caption,
  data,
  dataKey,
  unit,
  mean,
  decimals = 2,
  // Optional multi-series form: [{ dataKey, color, name }]. Omitted → the original single blue
  // line, so the report card's rendering is unchanged.
  series = null,
  // Phase 83-01 cross-highlight, both optional. Absent → this panel behaves exactly as before,
  // which is what keeps CompareCycleCharts (the other caller of this export) un-regressed.
  highlightN = null,
  onHoverN = null,
  // Phase 87-02 — the noun this panel calls one plotted item. Defaults to today's exact strings,
  // which is what keeps CompareCycleCharts (the other caller of this export) un-regressed.
  itemLabel = "cycle",
}) {
  const lines = series ?? [{ dataKey, color: "#2196f3", name: undefined }];
  const Item = itemLabel.charAt(0).toUpperCase() + itemLabel.slice(1);
  // activeLabel is the x-category, which recharts may hand back as a string — coerce, so the
  // number the inset compares against is always a number.
  const reportHover = (state) => {
    const v = Number(state?.activeLabel);
    onHoverN(Number.isFinite(v) ? v : null);
  };
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
          <LineChart
            data={data}
            margin={{ top: 6, right: 10, bottom: 0, left: -8 }}
            onMouseMove={onHoverN ? reportHover : undefined}
            onMouseLeave={onHoverN ? () => onHoverN(null) : undefined}
          >
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
                    {/* ⚠ The single-series form is preserved EXACTLY as 61-02 shipped it. The
                        report card renders this component, and quietly restyling its tooltip
                        while adding a Compare feature would be an unannounced change to a
                        surface this plan is not supposed to touch (AC-5). */}
                    {series ? (
                      <>
                        <p className="text-muted">
                          {Item} {payload[0].payload.n}
                        </p>
                        {payload.map((pl) => (
                          <p key={pl.dataKey} style={{ color: pl.stroke }}>
                            {pl.name ? `${pl.name}: ` : ""}
                            {pl.value?.toFixed(decimals)} {unit}
                          </p>
                        ))}
                      </>
                    ) : (
                      <>
                        {Item} {payload[0].payload.n}:{" "}
                        {payload[0].value?.toFixed(decimals)} {unit}
                      </>
                    )}
                  </div>
                ) : null
              }
            />
            {/* the band the coach is hovering on the inset — solid, so it never reads as a second
                mean line (83-01) */}
            {highlightN != null && (
              <ReferenceLine x={highlightN} stroke="#f0f2f5" strokeOpacity={0.5} strokeWidth={1.5} />
            )}
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
            {lines.map((ln) => (
              <Line
                key={ln.dataKey}
                type="monotone"
                dataKey={ln.dataKey}
                name={ln.name}
                stroke={ln.color}
                strokeWidth={2}
                dot={{ r: 3, fill: ln.color }}
                isAnimationActive={false}
                // Two sessions have DIFFERENT cycle counts; the shorter series must simply end
                // rather than be bridged across missing cycles it never had.
                connectNulls={false}
              />
            ))}
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

// ⚠ The `cycles` prop is handed STROKES in the report card's stroke mode (87-02 D5). The name is
// kept deliberately: renaming it to `items` would ripple into CompareCycleCharts and the legacy
// no-phases branch, both out of that plan's scope. `itemLabel` is what tells this component which
// of the two it is drawing — the same shape-agnostic posture buildBands has had since 83-02.
export default function CycleCharts({
  cycles,
  session,
  unit = "metric",
  itemLabel = "cycle",
  // Phase 83-01 — shared with the Swimming inset. The parent owns the state; absent (the legacy
  // no-phases branch, where there is no inset partner) the charts behave exactly as before.
  highlightN = null,
  onHoverN = null,
}) {
  const imp = unit === "imperial";
  const factor = imp ? 1.09361 : 1;

  // Memoized so a hover-driven re-render does not rebuild four recharts datasets (83 R4).
  const data = useMemo(
    () =>
      (cycles ?? []).map((c, i) => ({
        n: i + 1,
        dps: num(c.dist_m) != null ? c.dist_m * factor : null,
        coast: num(c.coast_fraction) != null ? c.coast_fraction * 100 : null,
        dur: num(c.duration_s),
        arm: num(c.arm_peak_vel) != null ? c.arm_peak_vel * factor : null,
      })),
    [cycles, factor]
  );

  if (!cycles?.length) return null;

  const s = session ?? {};
  const distUnit = imp ? "yd" : "m";
  const velUnit = imp ? "yd/s" : "m/s";
  const scale = (v) => (num(v) != null ? v * factor : null);

  // Session vintage, decided from the DATA rather than a date. Phase 61-01 stopped emitting
  // `phase` on cycle dicts, so its presence means the stored metrics were computed by the old
  // code — whose means and CVs covered steady cycles only.
  const legacy = cycles.some((c) => c && "phase" in c);
  const isStroke = itemLabel === "stroke";

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <TrendPanel
          highlightN={highlightN}
          onHoverN={onHoverN}
          itemLabel={itemLabel}
          title={isStroke ? "Distance per Arm Stroke" : "Distance per Stroke"}
          data={data}
          dataKey="dps"
          unit={distUnit}
          mean={scale(s.mean_dps_m)}
          caption={`mean ${fmt(scale(s.mean_dps_m))} ${distUnit}`}
        />
        <TrendPanel
          highlightN={highlightN}
          onHoverN={onHoverN}
          itemLabel={itemLabel}
          title="Coast"
          data={data}
          dataKey="coast"
          unit="%"
          mean={num(s.mean_coast_fraction) != null ? s.mean_coast_fraction * 100 : null}
          decimals={0}
          caption={`mean ${pct(s.mean_coast_fraction)} of each ${itemLabel} spent gliding`}
        />
        <TrendPanel
          highlightN={highlightN}
          onHoverN={onHoverN}
          itemLabel={itemLabel}
          title={isStroke ? "Stroke Duration" : "Cycle Duration"}
          data={data}
          dataKey="dur"
          unit="s"
          mean={num(s.mean_isi_s)}
          caption={`mean ${fmt(s.mean_isi_s)} s · rhythm consistency (CV) ${pct(s.cv_isi)}`}
        />
        <TrendPanel
          highlightN={highlightN}
          onHoverN={onHoverN}
          itemLabel={itemLabel}
          title="Arm Peak Velocity"
          data={data}
          dataKey="arm"
          unit={velUnit}
          mean={scale(s.mean_arm_peak_vel_ms)}
          caption={`mean ${fmt(scale(s.mean_arm_peak_vel_ms))} ${velUnit} · power consistency (CV) ${pct(s.cv_arm_peak_vel)}`}
        />
      </div>
      <p className="px-1 text-[11px] leading-relaxed text-muted">
        One point per detected {itemLabel}.
        {legacy
          ? " This session was processed before the cycle-counting fix, so its means and CVs cover" +
            " only steady-state cycles — the dashed line may not sit at the visual average of the dots."
          : ` Means and CVs cover every ${itemLabel} shown, so the dashed line is the average of the dots.`}
      </p>
    </>
  );
}
