"use client";

// PhaseVelocity — the report card's velocity line (Phase 75-05). A plain, hand-rolled SVG line
// (NOT the cycle-coupled VelocityChart): every y-axis starts at 0, charts stay line-only.
//   variant="hero"  → whole swim, faint phase tint bands, a Surfaced marker, and phase labels
//                     pinned along the BOTTOM axis (their own row, so they never overlap the trace).
//   variant="inset" → one phase's window (pass `window={[i0,i1]}`), just the slice + peak, no bands.
// Boundary times in seconds; missing boundaries degrade (that band/marker is skipped).

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

function argmax(velocity, i0, i1) {
  let bi = -1;
  let bv = -Infinity;
  for (let i = i0; i <= i1; i++) {
    const v = velocity[i];
    if (v != null && Number.isFinite(v) && v > bv) {
      bv = v;
      bi = i;
    }
  }
  return bi;
}

export default function PhaseVelocity({
  velocity = [],
  fsHz = 100,
  boundaries = null,
  window: win = null,
  variant = "hero",
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
    const peakIdx = argmax(velocity, i0, i1);

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

    return {
      W, H, pl, pr, pt, pb, plotBottom, vmax, xOfT, yOf, idxToX,
      d, peakIdx, grid, bands, phaseLabels, ticks, surfaced, inset,
    };
  }, [velocity, fsHz, boundaries, win, variant]);

  if (!geom) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
        No signal data for this session.
      </div>
    );
  }

  const g = geom;

  return (
    <svg
      viewBox={`0 0 ${g.W} ${g.H}`}
      className="block h-auto w-full"
      role="img"
      aria-label={g.inset ? "Speed during this phase" : "Speed over the whole swim"}
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

      {/* trace */}
      <path
        d={g.d}
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth="2.4"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* peak dot */}
      {g.peakIdx >= 0 && (
        <circle
          cx={g.idxToX(g.peakIdx)}
          cy={g.yOf(velocity[g.peakIdx])}
          r="4"
          fill="var(--color-primary)"
        />
      )}

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
    </svg>
  );
}
