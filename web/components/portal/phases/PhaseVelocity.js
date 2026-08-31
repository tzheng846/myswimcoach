"use client";

// PhaseVelocity — the report card's velocity line (Phase 75-05). A plain, hand-rolled SVG line
// (NOT the cycle-coupled VelocityChart): every y-axis starts at 0, charts stay line-only.
//   variant="hero"  → whole swim, faint phase tint bands, a Surfaced marker, and phase labels
//                     pinned along the BOTTOM axis (their own row, so they never overlap the trace).
//   variant="inset" → one phase's window (pass `window={[i0,i1]}`), just the slice, no bands.
// Boundary times in seconds; missing boundaries degrade (that band/marker is skipped).
//
// Phase 83-01 added the optional `bands` prop (from `lib/cycleBands`): the trace is drawn once in
// neutral grey and each band overdrawn in alternating blue/purple, so the un-segmented gaps handle
// themselves. Without `bands` the render is exactly what it was — the hero and the Start / Whole
// insets pass nothing and are untouched.
//
// 83-03 gilds the breakout band (decided in `lib/cycleBands`; this file only paints it) and drops
// the old duration-outlier halo entirely.

import { useMemo } from "react";

function niceMax(v) {
  if (!(v > 0)) return 1;
  const step = v <= 1 ? 0.25 : v <= 3 ? 0.5 : 1;
  return Math.max(step, Math.ceil((v * 1.05) / step) * step);
}

function buildPath(velocity, idxToX, yOf, i0, i1) {
  let d = "";
  let pen = false;
  for (let i = i0; i <= i1; i++) {
    const v = velocity[i];
    if (v == null || !Number.isFinite(v)) {
      pen = false;
      continue;
    }
    d += `${pen ? "L" : "M"}${idxToX(i).toFixed(1)} ${yOf(v).toFixed(1)} `;
    pen = true;
  }
  return d;
}

export default function PhaseVelocity({
  velocity = [],
  fsHz = 100,
  boundaries = null,
  window: win = null,
  variant = "hero",
  // Phase 83-01 — all optional; null everywhere except the Swimming inset. Aliased on the way in:
  // `bands` is already taken inside `geom` by the hero's phase-tint rects.
  bands: cycleBands = null,
  highlightN = null,
  onHoverBand = null,
  // Phase 87-02 — the ONLY addition this file takes for that plan, and it is display copy, not
  // geometry: the banded aria-label reads "one band per cycle", which would be wrong in stroke mode
  // for exactly the users who cannot see the colours. Defaults to "cycle"; nothing else reads it.
  itemLabel = "cycle",
}) {
  const geom = useMemo(() => {
    const n = velocity.length;
    if (n < 2 || !(fsHz > 0)) return null;
    const inset = variant === "inset";
    const i0 = win ? Math.max(0, Math.min(n - 1, win[0])) : 0;
    const i1 = win ? Math.max(0, Math.min(n - 1, win[1])) : n - 1;
    if (i1 <= i0) return null;

    const W = 1000;
    const H = inset ? 200 : 320;
    const pl = 44;
    const pr = 16;
    const pt = 16;
    const pb = inset ? 28 : 56;

    const t0 = i0 / fsHz;
    const t1 = i1 / fsHz;
    let vmax = 0;
    for (let i = i0; i <= i1; i++) {
      const v = velocity[i];
      if (v != null && Number.isFinite(v) && v > vmax) vmax = v;
    }
    vmax = niceMax(vmax);

    const xOfT = (t) => pl + ((t - t0) / (t1 - t0 || 1)) * (W - pl - pr);
    const idxToX = (i) => xOfT(i / fsHz);
    const yOf = (v) => H - pb - (v / vmax) * (H - pt - pb);
    const plotBottom = H - pb;

    const d = buildPath(velocity, idxToX, yOf, i0, i1);

    // gridlines at integer m/s
    const grid = [];
    for (let g = 1; g <= vmax + 1e-9; g += vmax <= 3 ? 0.5 : 1) {
      grid.push(Math.round(g * 100) / 100);
    }

    // phase bands + labels (hero only)
    const bands = [];
    const phaseLabels = [];
    if (!inset && boundaries) {
      const b = boundaries;
      const T = t1;
      const segs = [
        ["start", b.dive_start_s, b.underwater_start_s, "DIVE / PUSH-OFF", 0.06],
        ["uw", b.underwater_start_s, b.stroke_start_s, "UNDERWATER", 0.12],
        ["swim", b.stroke_start_s, b.finish_s ?? T, "SWIMMING", 0.04],
      ];
      for (const [key, a, c, label, op] of segs) {
        if (a == null || c == null || !(c > a)) continue;
        const xa = xOfT(a);
        const xc = xOfT(c);
        bands.push({ key, x: xa, w: xc - xa, op });
        let px = (xa + xc) / 2;
        px = Math.max(pl + 46, Math.min(px, W - pr - 46));
        phaseLabels.push({ key, x: px, label });
      }
    }

    // time ticks along the bottom
    const ticks = [];
    const tickCount = inset ? 2 : 4;
    for (let k = 0; k <= tickCount; k++) {
      const t = t0 + ((t1 - t0) * k) / tickCount;
      ticks.push({ x: xOfT(t), label: `${t.toFixed(1)}s` });
    }

    const surfaced =
      !inset && boundaries?.stroke_start_s != null && boundaries.stroke_start_s > t0 && boundaries.stroke_start_s < t1
        ? xOfT(boundaries.stroke_start_s)
        : null;

    // Per-cycle segments (83-01). Re-clamped defensively: `buildBands` already clamps to this same
    // window, but the component must not draw off-plot if a caller ever passes a stale band list.
    // Each segment reuses `buildPath` — one path builder for the whole component.
    const segs = [];
    const edges = [];
    for (const b of cycleBands ?? []) {
      const s0 = Math.max(i0, Math.min(i1, b.startIdx));
      const s1 = Math.max(i0, Math.min(i1, b.endIdx));
      if (!(s1 > s0)) continue;
      const xa = idxToX(s0);
      const xb = idxToX(s1);
      segs.push({
        n: b.n,
        isBreakout: !!b.isBreakout,
        d: buildPath(velocity, idxToX, yOf, s0, s1),
        x: xa,
        w: xb - xa,
      });
      edges.push(xa, xb);
    }
    const segTicks = [...new Set(edges.map((x) => Math.round(x * 10) / 10))];

    return {
      W, H, pl, pr, pt, pb, plotBottom, vmax, xOfT, yOf, idxToX,
      d, grid, bands, phaseLabels, ticks, surfaced, inset,
      segs, segTicks,
    };
  }, [velocity, fsHz, boundaries, win, variant, cycleBands]);

  if (!geom) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No signal data for this session.
      </div>
    );
  }

  const g = geom;
  const banded = g.segs.length > 0;

  return (
    <svg
      viewBox={`0 0 ${g.W} ${g.H}`}
      className="block h-auto w-full"
      role="img"
      aria-label={
        banded
          ? `Speed during this phase, coloured one band per ${itemLabel} (${g.segs.length} bands)`
          : g.inset
            ? "Speed during this phase"
            : "Speed over the whole swim"
      }
      onMouseLeave={onHoverBand ? () => onHoverBand(null) : undefined}
    >
      {/* phase tint bands */}
      {g.bands.map((b) => (
        <rect
          key={b.key}
          x={b.x}
          y={g.pt}
          width={b.w}
          height={g.plotBottom - g.pt}
          fill="var(--color-accent)"
          fillOpacity={b.op}
        />
      ))}

      {/* gridlines + y labels */}
      {g.grid.map((v) => (
        <g key={v}>
          <line
            x1={g.pl}
            y1={g.yOf(v)}
            x2={g.W - g.pr}
            y2={g.yOf(v)}
            stroke="var(--color-navy)"
            strokeOpacity={0.4}
          />
          <text
            x={g.pl - 8}
            y={g.yOf(v) + 4}
            textAnchor="end"
            fill="var(--color-muted)"
            fontSize="11"
            fontFamily="ui-monospace, monospace"
          >
            {v}
          </text>
        </g>
      ))}

      {/* trace — one continuous line, in the idle grey when bands will overdraw it (83-01). Drawing
          the whole window first is what makes "grey everywhere outside a cycle" free: the gaps are
          simply the part nothing paints over. */}
      <path
        d={g.d}
        fill="none"
        stroke={banded ? "var(--color-cycle-idle)" : "var(--color-primary)"}
        strokeWidth="2.4"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* one band per cycle: the breakout in gold, everything else alternating by the cycle's OWN
          number — so pulling the breakout out of the rotation cannot flip the parity after it */}
      {g.segs.map((s) => (
        <path
          key={`seg-${s.n}`}
          d={s.d}
          fill="none"
          stroke={
            s.isBreakout
              ? "var(--color-cycle-breakout)"
              : s.n % 2
                ? "var(--color-cycle-a)"
                : "var(--color-cycle-b)"
          }
          strokeWidth={highlightN === s.n ? 3.8 : 2.4}
          strokeOpacity={highlightN != null && highlightN !== s.n ? 0.45 : 1}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ))}

      {/* boundary ticks — the colourblind mitigation (83 D6), not decoration: blue and purple
          differ mainly in the red channel, so bands must stay countable by structure alone. */}
      {g.segTicks.map((x, i) => (
        <line
          key={`tick-${i}`}
          x1={x}
          y1={g.plotBottom}
          x2={x}
          y2={g.plotBottom - 14}
          stroke="var(--color-navy)"
          strokeWidth="1.4"
        />
      ))}

      {/* Surfaced marker */}
      {g.surfaced != null && (
        <g>
          <line
            x1={g.surfaced}
            y1={g.pt}
            x2={g.surfaced}
            y2={g.plotBottom}
            stroke="var(--color-ink)"
            strokeWidth="1.5"
            strokeDasharray="3 3"
            strokeOpacity={0.55}
          />
          <text
            x={g.surfaced + 5}
            y={g.pt + 11}
            fill="var(--color-muted)"
            fontSize="9.5"
            fontWeight="600"
            letterSpacing="0.06em"
            fontFamily="var(--font-sans)"
          >
            SURFACED
          </text>
        </g>
      )}

      {/* time ticks */}
      {g.ticks.map((t, i) => (
        <text
          key={i}
          x={t.x}
          y={g.plotBottom + 18}
          textAnchor="middle"
          fill="var(--color-muted)"
          fontSize="11"
          fontFamily="ui-monospace, monospace"
        >
          {t.label}
        </text>
      ))}

      {/* phase labels pinned along the BOTTOM (own row beneath the ticks — the overlap fix) */}
      {g.phaseLabels.map((p) => (
        <text
          key={p.key}
          x={p.x}
          y={g.plotBottom + 38}
          textAnchor="middle"
          fill="var(--color-muted)"
          fontSize="10"
          fontWeight="600"
          letterSpacing="0.1em"
          fontFamily="var(--font-sans)"
        >
          {p.label}
        </text>
      ))}

      {/* transparent hit targets, last so they sit above everything. The matching mouseleave is on
          the <svg> itself, so sliding off the chart clears the highlight in one place. */}
      {onHoverBand &&
        g.segs.map((s) => (
          <rect
            key={`hit-${s.n}`}
            x={s.x}
            y={g.pt}
            width={s.w}
            height={g.plotBottom - g.pt}
            fill="transparent"
            pointerEvents="all"
            onMouseEnter={() => onHoverBand(s.n)}
          />
        ))}
    </svg>
  );
}
