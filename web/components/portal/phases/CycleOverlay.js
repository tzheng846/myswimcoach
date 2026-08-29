"use client";

// CycleOverlay — the per-cycle OVERLAY panel (Phase 83-05). Sits inside the same bordered box as
// the phase inset, directly beneath it: every stroke cycle (or downkick) drawn on ONE shared axis,
// all starting at x = 0, so the pack is visible and the stroke that leaves it is visible with it.
//
// This is the honest replacement for 83-03's cut shape classifier. That plan tried to ASSERT which
// stroke was odd and was measured out: at a median of 7 cycles a lap the MAD gate fired on 75% of
// sessions at k=3.0 and still 39% at k=8.0. Nothing here asserts anything — it lays the strokes on
// top of each other and lets the coach's eye do the work, which is also what makes every number in
// CycleCharts auditable against the shape it came from.
//
// CONTROLLED component: it renders `activeN` and owns none of that state. The parent computes
// `hovered ?? pinned` (83-05 D9) so a hover can preview without dropping a pin, and a mouseleave
// cannot clobber one. The only state here is the seconds/normalized toggle, which is deliberately
// local and NOT persisted — every session opens in seconds.

import { useMemo, useState } from "react";
import { buildTraces } from "@/lib/cycleTraces";

// ⚠ DUPLICATED from PhaseVelocity.js on purpose. `niceMax` is a local there and is not exported,
// and 83-05's boundaries forbid editing that file — 83-01 lost a verify cycle to a shadowed prop
// inside its `geom`, and 83-02 broke a zero-diff AC by touching it. This panel's y-axis MUST land
// on the same rounded maximum as the inset stacked above it, or two charts sharing a box would be
// drawn at two different scales. If PhaseVelocity ever exports this, delete the copy.
function niceMax(v) {
  if (!(v > 0)) return 1;
  const step = v <= 1 ? 0.25 : v <= 3 ? 0.5 : 1;
  return Math.max(step, Math.ceil((v * 1.05) / step) * step);
}

const REASON_NOTE = {
  breakout: "The breakout pull — its own stroke, with no cycle row to compare against.",
  dropout: "Signal dropout inside this span; it cannot be resampled onto a shared grid.",
  "too-short": "Too few samples to draw.",
};

// Above this many numbered rows the gutter wraps into a second (third, …) column instead of
// running past the bottom of the plot. A 15-dolphin-kick underwater is not unusual and a single
// 15-row column stands taller than the chart it labels.
const MAX_GUTTER_ROWS = 10;

const W = 1000;
const H = 200;
const PL = 44;
const PR = 16;
const PT = 14;
const PB = 26;
const PLOT_BOTTOM = H - PB;

export default function CycleOverlay({
  items,
  velocity = [],
  fsHz = 100,
  window: win = null,
  activeN = null,
  onHoverN = null,
  onPinN = null,
  pinnedN = null,
  excludeBreakout = false,
  label = "cycle",
}) {
  const [mode, setMode] = useState("seconds");
  const normalized = mode === "normalized";

  const model = useMemo(
    () => buildTraces(items, velocity, { fsHz, mode, excludeBreakout }),
    [items, velocity, fsHz, mode, excludeBreakout]
  );

  // Scale over the INSET'S window, not over the traces — the two charts must agree even when a
  // cycle is dropped from the pack, and even when the phase window holds signal no cycle covers.
  const vmax = useMemo(() => {
    const n = velocity.length;
    if (!n) return 1;
    const i0 = win ? Math.max(0, Math.min(n - 1, win[0])) : 0;
    const i1 = win ? Math.max(0, Math.min(n - 1, win[1])) : n - 1;
    let m = 0;
    for (let i = i0; i <= i1; i++) {
      const v = velocity[i];
      if (v != null && Number.isFinite(v) && v > m) m = v;
    }
    return niceMax(m);
  }, [velocity, win]);

  const { rows, traces, median, maxDuration } = model;

  // Fewer than two traces is not a pack. Render nothing at all — no empty box, no bare axis.
  if (traces.length < 2) return null;

  const span = normalized ? 1 : maxDuration || 1;
  const xOf = (x) => PL + (x / span) * (W - PL - PR);
  const yOf = (v) => PLOT_BOTTOM - (v / vmax) * (PLOT_BOTTOM - PT);

  // One path builder, shared with the median line. `null` in a point list is a pen-up marker, so a
  // dropout draws a gap instead of a straight line across missing signal.
  const pathOf = (points) => {
    let d = "";
    let pen = false;
    for (const p of points) {
      if (p === null) {
        pen = false;
        continue;
      }
      d += `${pen ? "L" : "M"}${xOf(p[0]).toFixed(1)} ${yOf(p[1]).toFixed(1)} `;
      pen = true;
    }
    return d;
  };

  const grid = [];
  for (let g = 1; g <= vmax + 1e-9; g += vmax <= 3 ? 0.5 : 1) grid.push(Math.round(g * 100) / 100);

  const ticks = normalized
    ? [0, 0.5, 1].map((f) => ({ x: xOf(f), label: `${Math.round(f * 100)}%` }))
    : [0, 0.5, 1].map((f) => ({ x: xOf(f * span), label: `${(f * span).toFixed(2)}s` }));

  // Active last so it paints ON TOP of the pack rather than under whichever trace follows it.
  const ordered = [...traces].sort((a, b) => (a.n === activeN ? 1 : 0) - (b.n === activeN ? 1 : 0));
  const dimOthers = activeN != null && traces.some((t) => t.n === activeN);

  // The breakout is not part of the numbered sequence — it sits on its own full-width row ABOVE
  // them (AC-3), which also keeps its long label from setting the width of every wrapped column.
  const breakoutRow = rows.find((r) => r.reason === "breakout") ?? null;
  const numbered = rows.filter((r) => r.reason !== "breakout");
  const gutterCols = Math.max(1, Math.ceil(numbered.length / MAX_GUTTER_ROWS));
  const perCol = Math.ceil(numbered.length / gutterCols);

  const hover = (n) => onHoverN?.(n);
  const pin = (n) => onPinN?.(n === pinnedN ? null : n);

  return (
    <div className="mt-3 border-t border-navy/40 pt-3" onMouseLeave={() => hover(null)}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-subtle">
          every {label} on one axis
        </p>
        <div
          className="flex shrink-0 overflow-hidden rounded-md border border-navy/60"
          role="group"
          aria-label={`${label} overlay x-axis mode`}
        >
          {[
            ["seconds", "seconds"],
            ["normalized", `% of ${label}`],
          ].map(([key, text]) => (
            <button
              key={key}
              type="button"
              onClick={() => setMode(key)}
              aria-pressed={mode === key}
              className={`px-2 py-0.5 text-[10.5px] font-medium transition-colors ${
                mode === key ? "bg-navy/60 text-ink" : "text-muted hover:text-subtle"
              }`}
            >
              {text}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-stretch gap-2.5">
        {/* Gutter. HTML rather than SVG text: these are real hit targets that must be keyboard
            reachable, and a <button> gets Enter/Space activation and focus rings for free. The rows
            are a legend, not an axis — the traces are stacked, so nothing here aligns to a y. */}
        <div className="shrink-0 pt-0.5">
          {/* The breakout has no trace in the pack — it is one stroke, not a cycle — but it DOES
              have a band in the inset above, so hovering this row highlights `n: 0` there. It stays
              visually dim because there is nothing of it to accent down here, and nothing in
              CycleCharts reacts because 0 is outside that component's keyspace. */}
          {breakoutRow && (
            <button
              type="button"
              onMouseEnter={() => hover(0)}
              onFocus={() => hover(0)}
              onBlur={() => hover(null)}
              onClick={() => pin(0)}
              aria-pressed={pinnedN === 0}
              aria-label="Breakout pull — highlight it on the chart above"
              title={REASON_NOTE.breakout}
              className={`mb-0.5 block w-full rounded px-1.5 py-0.5 text-left font-mono text-[11px] tabular-nums transition-colors ${
                activeN === 0 ? "bg-navy/60 text-subtle" : "text-subtle/45 hover:text-subtle/70"
              }`}
            >
              0 · breakout
              {pinnedN === 0 && <span aria-hidden="true"> •</span>}
            </button>
          )}
          {/* Fill DOWN the first column, then wrap to the next — `grid-flow: column` over a fixed
              row count. Deterministic, unlike flex-wrap, which needs a guessed container height. */}
          <div
            className="grid gap-x-1 gap-y-px"
            style={{ gridAutoFlow: "column", gridTemplateRows: `repeat(${perCol}, minmax(0, auto))` }}
          >
            {numbered.map((r) =>
              r.available ? (
                <button
                  key={r.n}
                  type="button"
                  onMouseEnter={() => hover(r.n)}
                  onFocus={() => hover(r.n)}
                  onBlur={() => hover(null)}
                  onClick={() => pin(r.n)}
                  aria-pressed={pinnedN === r.n}
                  aria-label={`${label} ${r.n}${r.duration != null ? `, ${r.duration.toFixed(2)} seconds` : ""}`}
                  className={`min-w-[2rem] rounded px-1.5 py-0.5 text-left font-mono text-[11px] tabular-nums transition-colors ${
                    activeN === r.n ? "bg-navy/60 text-ink" : "text-muted hover:text-subtle"
                  }`}
                >
                  {r.n}
                  {pinnedN === r.n && <span aria-hidden="true"> •</span>}
                </button>
              ) : (
                <span
                  key={r.n}
                  style={{ pointerEvents: "none" }}
                  className="min-w-[2rem] rounded px-1.5 py-0.5 font-mono text-[11px] tabular-nums text-subtle/45"
                  title={REASON_NOTE[r.reason] ?? undefined}
                >
                  {r.n}
                </span>
              )
            )}
          </div>
        </div>

        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block h-auto w-full min-w-0 flex-1"
          role="img"
          aria-label={`All ${traces.length} ${label}s of this phase drawn on one shared axis${
            median ? ", with a median reference line" : ""
          }`}
        >
          {grid.map((v) => (
            <g key={v}>
              <line x1={PL} y1={yOf(v)} x2={W - PR} y2={yOf(v)} stroke="var(--color-navy)" strokeOpacity={0.4} />
              <text
                x={PL - 8}
                y={yOf(v) + 4}
                textAnchor="end"
                fill="var(--color-muted)"
                fontSize="11"
                fontFamily="ui-monospace, monospace"
              >
                {v}
              </text>
            </g>
          ))}

          {/* Median BENEATH the pack: it is a reference, not a member of it. Normalized only —
              a pointwise median needs a common x-grid and seconds mode has none. */}
          {median && (
            <path
              d={pathOf(median)}
              fill="none"
              stroke="var(--color-muted)"
              strokeWidth="6"
              strokeOpacity={0.3}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}

          {ordered.map((t) => {
            const isActive = t.n === activeN;
            return (
              <path
                key={t.n}
                d={pathOf(t.points)}
                fill="none"
                stroke={isActive ? "var(--color-cycle-a)" : "var(--color-cycle-idle)"}
                strokeWidth={isActive ? 3.2 : 1.8}
                strokeOpacity={dimOthers && !isActive ? 0.45 : 1}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            );
          })}

          {ticks.map((t, i) => (
            <text
              key={i}
              x={t.x}
              y={PLOT_BOTTOM + 17}
              textAnchor="middle"
              fill="var(--color-muted)"
              fontSize="11"
              fontFamily="ui-monospace, monospace"
            >
              {t.label}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}
