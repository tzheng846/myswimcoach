"use client";

import { useCallback, useMemo, useRef } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Brush,
  ReferenceArea,
  ReferenceLine,
} from "recharts";

const MAX_POINTS = 2000;

// Grab radius for dragging an existing mark, as a fraction of the VISIBLE span —
// so it stays a constant number of pixels however far the view is zoomed in.
const GRAB_FRAC = 0.01;

// Canonical phase order matches annotations.py PHASE_KEYS.
// "underwater" displays as "Pulldown" for breaststroke (display concern only).
// `drivesMetrics` records which markers reach compute_session_metrics via
// annotations.annotation_to_overrides — dive → baseline_end_idx, stroke → ip_end_idx,
// finish → swim_end_idx. UW kick is the only marker that feeds the 16-06 export and
// nothing else (api.py carries initial_phase over from the auto result unchanged on
// recompute).
//
// Breakout was REMOVED in Phase 58 (superseding 57 D5 for that marker). The UW kick span
// now runs through the breakout, and the first stroke cycle contains it. This array is the
// single source: the tool palette, the phase rows, the band tiling and the page's
// normalizePhases all derive from it, so nothing else needed editing.
export const PHASE_META = [
  { key: "dive_start_s", label: "Dive", color: "#fb923c", drivesMetrics: true },
  {
    key: "underwater_start_s",
    label: "UW kick",
    breaststrokeLabel: "Pulldown",
    color: "#c084fc",
    drivesMetrics: false,
  },
  { key: "stroke_start_s", label: "Stroke", color: "#4ade80", drivesMetrics: true },
  { key: "finish_s", label: "Finish", color: "#f87171", drivesMetrics: true },
];

export function phaseLabel(meta, strokeType) {
  return strokeType === "breaststroke" && meta.breaststrokeLabel
    ? meta.breaststrokeLabel
    : meta.label;
}

// Click-to-mark velocity chart for the annotation editor. Modeled on the shared
// VelocityChart (which report card + compare depend on — deliberately not reused).
export default function AnnotationChart({
  time,
  velocity,
  phases = {},
  strokeMarks = [],
  playheadS = null,
  strokeType,
  onChartClick,
  onMarkDrag,
  onMarkSelect,
  selected = null,
  viewRange = null, // [lo, hi] in seconds, or null for the full trace
  // Any CSS length. Default scales with the viewport and is clamped at both ends, so
  // the trace gets the vertical room a tall screen offers without collapsing on a short
  // one. A plain number still works (React appends px) for any caller that passes one.
  height = "clamp(220px,30vh,480px)",
}) {
  const containerRef = useRef(null);
  const dragRef = useRef(null); // {kind, index} while a drag is in flight
  // Set when a press lands on an existing mark. Recharts fires onClick after mouseup,
  // so without this a grab (or a plain click to select) would ALSO place a new mark
  // on top of the one being targeted.
  const suppressClickRef = useRef(false);

  // Fit the view by SLICING the data rather than setting an XAxis domain: the
  // <Brush> below also controls the visible domain and the two fight each other.
  // Slicing also re-spreads the MAX_POINTS decimation budget over the shorter
  // span, which is where the precision gain actually comes from.
  const data = useMemo(() => {
    const n = Math.min(time.length, velocity.length);
    const [lo, hi] = viewRange ?? [-Infinity, Infinity];
    const kept = [];
    for (let i = 0; i < n; i++) {
      if (time[i] < lo || time[i] > hi) continue;
      if (velocity[i] == null) continue;
      kept.push(i);
    }
    const step = Math.max(1, Math.ceil(kept.length / MAX_POINTS));
    const pts = [];
    for (let j = 0; j < kept.length; j += step) {
      const i = kept[j];
      pts.push({
        t: Math.round(time[i] * 100) / 100,
        v: Math.round(velocity[i] * 1000) / 1000,
      });
    }
    return pts;
  }, [time, velocity, viewRange]);

  const span = data.length
    ? data[data.length - 1].t - data[0].t
    : 0;
  const grabTol = Math.max(span * GRAB_FRAC, 1e-3);

  // Every draggable item, flattened, so hit-testing is one pass.
  const targets = useMemo(() => {
    const out = [];
    for (const m of PHASE_META) {
      if (phases[m.key] != null) out.push({ kind: m.key, index: 0, t: phases[m.key] });
    }
    strokeMarks.forEach((t, i) => out.push({ kind: "stroke", index: i, t }));
    return out;
  }, [phases, strokeMarks]);

  const nearest = useCallback(
    (t) => {
      let best = null;
      let bestD = Infinity;
      for (const tgt of targets) {
        const d = Math.abs(tgt.t - t);
        if (d < bestD) {
          bestD = d;
          best = tgt;
        }
      }
      return bestD <= grabTol ? best : null;
    },
    [targets, grabTol]
  );

  const setCursor = (c) => {
    // Mutate the DOM directly instead of holding hover in state — this fires on
    // every mousemove and a re-render per event would stutter the whole chart.
    if (containerRef.current) containerRef.current.style.cursor = c;
  };

  const handleMouseDown = useCallback(
    (state) => {
      if (!state || state.activeLabel == null) return;
      const hit = nearest(Number(state.activeLabel));
      if (hit) {
        dragRef.current = { kind: hit.kind, index: hit.index };
        suppressClickRef.current = true;
        onMarkSelect?.({ kind: hit.kind, index: hit.index });
        setCursor("grabbing");
      }
    },
    [nearest, onMarkSelect]
  );

  const handleMouseMove = useCallback(
    (state) => {
      if (!state || state.activeLabel == null) return;
      const t = Number(state.activeLabel);
      if (dragRef.current) {
        onMarkDrag?.(dragRef.current.kind, dragRef.current.index, t);
        return;
      }
      setCursor(nearest(t) ? "grab" : "crosshair");
    },
    [nearest, onMarkDrag]
  );

  const endDrag = useCallback(() => {
    dragRef.current = null;
    setCursor("crosshair");
  }, []);

  const handleClick = useCallback(
    (state) => {
      // The press landed on an existing mark (select or drag) — do not also place one.
      if (suppressClickRef.current) {
        suppressClickRef.current = false;
        return;
      }
      if (state && state.activeLabel != null) onChartClick?.(Number(state.activeLabel));
    },
    [onChartClick]
  );

  // Consecutive placed markers tile the swim into non-overlapping bands. Shading
  // them is what makes "phases cannot overlap" visible rather than merely enforced
  // by validate_annotation's ordering check.
  const bands = useMemo(() => {
    const placed = PHASE_META.filter((m) => phases[m.key] != null);
    const out = [];
    for (let i = 0; i < placed.length - 1; i++) {
      out.push({
        key: placed[i].key,
        x1: phases[placed[i].key],
        x2: phases[placed[i + 1].key],
        color: placed[i].color,
      });
    }
    return out;
  }, [phases]);

  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No signal data in view.
      </div>
    );
  }

  const isSel = (kind, index) =>
    selected && selected.kind === kind && selected.index === index;

  return (
    <div
      ref={containerRef}
      className="w-full min-w-0 cursor-crosshair rounded-xl border border-navy/50 bg-surface p-3"
      style={{ height }}
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        // Pre-measurement guess only — must stay a NUMBER. `height` is now a CSS length
        // (clamp(...)), which recharts cannot use here; the real height comes from the
        // parent div's style below.
        initialDimension={{ width: 520, height: 320 }}
      >
        <LineChart
          data={data}
          margin={{ top: 18, right: 12, bottom: 0, left: 0 }}
          onClick={handleClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={endDrag}
          onMouseLeave={endDrag}
        >
          <CartesianGrid stroke="#1e3a5f" strokeOpacity={0.25} />
          {/* Phase bands — contiguous by construction, drawn under everything else */}
          {bands.map((b) => (
            <ReferenceArea
              key={`band-${b.key}`}
              x1={b.x1}
              x2={b.x2}
              fill={b.color}
              fillOpacity={0.07}
              stroke="none"
              ifOverflow="hidden"
            />
          ))}
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
            cursor={{ stroke: "#2196f3", strokeWidth: 1 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-md border border-navy bg-surface-2 px-3 py-1.5 font-mono text-xs text-ink">
                  {payload[0].payload.t.toFixed(2)} s ·{" "}
                  {payload[0].payload.v.toFixed(2)} m/s
                </div>
              ) : null
            }
          />
          {/* Individual stroke marks — thin, low-opacity dashed; selected one brightened */}
          {strokeMarks.map((t, i) => (
            <ReferenceLine
              key={`m${i}`}
              x={Math.round(t * 100) / 100}
              stroke={isSel("stroke", i) ? "#e2e8f0" : "#94a3b8"}
              strokeWidth={isSel("stroke", i) ? 2 : 1}
              strokeOpacity={isSel("stroke", i) ? 1 : 0.45}
              strokeDasharray={isSel("stroke", i) ? undefined : "2 4"}
              ifOverflow="hidden"
            />
          ))}
          {/* Phase boundaries — colored + labeled */}
          {PHASE_META.map((meta) =>
            phases[meta.key] != null ? (
              <ReferenceLine
                key={meta.key}
                x={Math.round(phases[meta.key] * 100) / 100}
                stroke={meta.color}
                strokeWidth={isSel(meta.key, 0) ? 3 : 1.5}
                ifOverflow="hidden"
                label={{
                  value: phaseLabel(meta, strokeType),
                  position: "top",
                  fill: meta.color,
                  fontSize: 10,
                }}
              />
            ) : null
          )}
          {/* Video playhead */}
          {playheadS != null && (
            <ReferenceLine
              x={Math.round(playheadS * 100) / 100}
              stroke="#f59e0b"
              strokeWidth={1.5}
              ifOverflow="hidden"
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
