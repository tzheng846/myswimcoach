"use client";

import { useMemo } from "react";
import { TrendPanel } from "@/components/portal/CycleCharts";
import { COLOR_A, COLOR_B } from "@/components/portal/CompareChart";

// Per-cycle comparison (61-04 D11), replacing MetricDeltaTable.
//
// Averages tell you THAT two swims differ; these tell you WHERE in the swim they diverge, which
// is the question a coach is actually asking on this page.
//
// ⚠ THE TWO SESSIONS HAVE DIFFERENT CYCLE COUNTS AND ARE NOT ALIGNED. The x-axis is cycle
// ordinal, and cycle 7 of one swim is NOT the counterpart of cycle 7 of another — different
// swimmers, different tempos, different lap lengths. Deliberately NOT padded, truncated or
// resampled to a common length: any of those would invent a correspondence that does not exist.
// The shorter series simply ends (connectNulls={false} in TrendPanel).

const PANELS = [
  { key: "dps", title: "Distance per Stroke", unit: "m", from: (c) => c.dist_m, decimals: 2 },
  {
    key: "coast",
    title: "Coast",
    unit: "%",
    from: (c) => (typeof c.coast_fraction === "number" ? c.coast_fraction * 100 : null),
    decimals: 0,
  },
  { key: "dur", title: "Cycle Duration", unit: "s", from: (c) => c.duration_s, decimals: 2 },
  { key: "arm", title: "Arm Peak Velocity", unit: "m/s", from: (c) => c.arm_peak_vel, decimals: 2 },
];

// Session-level metrics, carried over from MetricDeltaTable. These are single scalars per
// session — there is no per-cycle series behind mean_vel_ms or fatigue_index_pct — so they are
// drawn as a PAIR OF BARS per metric rather than as lines.
//
// ⚠ ACTUAL VALUES, NOT DIFFERENCES (61-04 checkpoint, user request). The earlier form showed
// "1.42 m → 1.61 m  +13.4%"; the % is deliberately gone. The bars carry the comparison visually,
// which is what the percentage was standing in for.
const METRICS = [
  { label: "Avg speed", key: "mean_vel_ms", fmt: (v) => `${v.toFixed(2)} m/s` },
  { label: "Max speed", key: "max_vel_ms", fmt: (v) => `${v.toFixed(2)} m/s` },
  { label: "Stroke rate", key: "stroke_rate_spm", fmt: (v) => `${v.toFixed(1)} spm` },
  { label: "Dist/stroke", key: "mean_dps_m", fmt: (v) => `${v.toFixed(2)} m` },
  { label: "Power CV", key: "cv_arm_peak_vel", fmt: (v) => v.toFixed(3) },
  { label: "Rhythm CV", key: "cv_isi", fmt: (v) => v.toFixed(3) },
  { label: "Glide", key: "mean_coast_fraction", fmt: (v) => `${(v * 100).toFixed(0)}%` },
  { label: "Fatigue", key: "fatigue_index_pct", fmt: (v) => `${v.toFixed(1)}%` },
];

const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

// One metric: two bars, one per session, both drawn on the SAME scale so their lengths are
// directly comparable.
// ⚠ Bars are scaled by max(|a|, |b|), not by max(a, b) — fatigue_index_pct goes NEGATIVE when a
// swimmer speeds up through the swim, and a naive scale would render that as a zero-width or
// inverted bar. The sign stays visible in the printed value.
function MetricBars({ label, a, bVal, fmt, labelA, labelB }) {
  const scale = Math.max(Math.abs(a ?? 0), Math.abs(bVal ?? 0)) || 1;
  const row = (v, color, name) => (
    <div className="flex items-center gap-2">
      <div className="h-3 flex-1 overflow-hidden rounded-sm bg-surface-2">
        {v != null && (
          <div
            className="h-full rounded-sm"
            style={{
              width: `${Math.max(2, (Math.abs(v) / scale) * 100)}%`,
              backgroundColor: color,
              opacity: v < 0 ? 0.45 : 1,
            }}
            title={name}
          />
        )}
      </div>
      <span
        className="w-20 shrink-0 text-right font-mono text-[11px]"
        style={{ color }}
      >
        {v != null ? fmt(v) : "--"}
      </span>
    </div>
  );
  return (
    <div className="rounded-lg border border-navy/40 bg-surface p-2.5">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
        {label}
      </p>
      <div className="space-y-1">
        {row(a, COLOR_A, labelA)}
        {row(bVal, COLOR_B, labelB)}
      </div>
    </div>
  );
}

function MetricBarGrid({ base, newer, labelA, labelB }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {METRICS.map(({ label, key, fmt }) => {
        const a = num(base?.[key]);
        const bVal = num(newer?.[key]);
        if (a == null && bVal == null) return null;
        return (
          <MetricBars
            key={key}
            label={label}
            a={a}
            bVal={bVal}
            fmt={fmt}
            labelA={labelA}
            labelB={labelB}
          />
        );
      })}
    </div>
  );
}

export default function CompareCycleCharts({
  cyclesA,
  cyclesB,
  sessionA,
  sessionB,
  labelA,
  labelB,
}) {
  const hasA = Array.isArray(cyclesA) && cyclesA.length > 0;
  const hasB = Array.isArray(cyclesB) && cyclesB.length > 0;

  // Per-session vintage. 61-01 stopped emitting `phase` on cycles, so its presence means the
  // stored metrics came from the old steady-only code. The two sessions can differ, so the
  // caveat names WHICH one is affected rather than being stated for both.
  const legacyA = hasA && cyclesA.some((c) => c && "phase" in c);
  const legacyB = hasB && cyclesB.some((c) => c && "phase" in c);

  const data = useMemo(() => {
    const n = Math.max(hasA ? cyclesA.length : 0, hasB ? cyclesB.length : 0);
    const rows = [];
    for (let i = 0; i < n; i++) {
      const ca = hasA ? cyclesA[i] : null;
      const cb = hasB ? cyclesB[i] : null;
      const row = { n: i + 1 };
      for (const p of PANELS) {
        row[`${p.key}A`] = ca ? num(p.from(ca)) : null;
        row[`${p.key}B`] = cb ? num(p.from(cb)) : null;
      }
      rows.push(row);
    }
    return rows;
  }, [cyclesA, cyclesB, hasA, hasB]);

  if (!hasA && !hasB) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        Neither session has per-cycle data — nothing to compare cycle by cycle.
      </div>
    );
  }

  const legacyNote = [legacyA ? labelA : null, legacyB ? labelB : null].filter(Boolean);

  return (
    <div className="space-y-3">
      <MetricBarGrid
        base={sessionA}
        newer={sessionB}
        labelA={labelA}
        labelB={labelB}
      />

      <div className="grid gap-3 sm:grid-cols-2">
        {PANELS.map((p) => (
          <TrendPanel
            key={p.key}
            title={p.title}
            data={data}
            unit={p.unit}
            decimals={p.decimals}
            series={[
              { dataKey: `${p.key}A`, color: COLOR_A, name: labelA },
              { dataKey: `${p.key}B`, color: COLOR_B, name: labelB },
            ]}
          />
        ))}
      </div>

      <p className="px-1 text-[11px] leading-relaxed text-muted">
        One point per detected cycle. The two swims are not aligned — cycle 7 of one is not the
        counterpart of cycle 7 of the other, and the shorter series simply ends.
        {!hasA && ` ${labelA} has no per-cycle data.`}
        {!hasB && ` ${labelB} has no per-cycle data.`}
        {legacyNote.length > 0 &&
          ` Processed before the cycle-counting fix, so means cover steady-state cycles only: ${legacyNote.join(
            ", "
          )}.`}
      </p>
    </div>
  );
}
