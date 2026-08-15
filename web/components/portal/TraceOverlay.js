"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";

// Rolling velocity strip drawn over the video (Phase 64 D6/D7).
//
// ⚠ THIS IS DELIBERATELY NOT `VelocityChart`. recharts re-renders its whole point set on every
// state change; following a playhead at animation-frame rate through React would re-render
// ~2000 points 60×/s and stutter — which is the exact thing this phase exists to remove.
// Here the polyline is built ONCE in DATA coordinates (x = seconds, y = m/s) and the window is a
// `viewBox` pan applied imperatively. No React state participates in the animation.
//
// ⚠ `preserveAspectRatio="none"` stretches the viewBox to the element box, which scales x and y
// by different factors. Every stroked element therefore needs `vector-effect="non-scaling-stroke"`
// or lines render as wedges.
//
// ⚠ It is PERMANENT — no `dimmed` prop (item 1, 2026-08-14). Only the control bar below it hides
// on idle; the trace never does. Positioning + scrim are the parent column's job, not this
// component's.

const MAX_POINTS = 4000; // ~undecimated up to a 45 s swim at 89.5 Hz
const Y_PAD_FRAC = 0.08;

// Stroke-mark colour = the trace colour, noticeably darker (user request 2026-08-14). Kept in RGB
// so it works for any hex the picker sets.
function darken(hex, f = 0.66) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  const r = Math.round(((n >> 16) & 255) * f);
  const g = Math.round(((n >> 8) & 255) * f);
  const b = Math.round((n & 255) * f);
  return `rgb(${r}, ${g}, ${b})`;
}

export default function TraceOverlay({
  velocity = [],
  fsHz = 100,
  cycles = [],
  videoElRef, // ref to the <video> element — read directly, never through React state
  originS, // effective sync origin; null until known, in which case the loop idles
  onSeek, // (sessionTimeS) => void
  windowS = 2, // seconds; null = show the whole swim (no follow)
  lineColor = "#ff453a", // user-chosen trace colour (PlaybackControls swatches)
}) {
  const svgRef = useRef(null);
  const playheadRef = useRef(null);
  const readoutRef = useRef(null);
  // Stroke-mark triangles live in an HTML layer over the svg, NOT inside it: preserveAspectRatio=
  // "none" would stretch an in-svg polygon into a wedge. Positioned per frame from the same window.
  const markLayerRef = useRef(null);
  // The window's current left edge, in seconds. Held in a ref because click-to-seek needs the
  // value the last animation frame wrote, and that frame never touched React.
  const windowStartRef = useRef(0);

  const geom = useMemo(() => {
    const n = velocity.length;
    const durationS = n > 1 ? (n - 1) / fsHz : 0;

    let lo = Infinity;
    let hi = -Infinity;
    for (let i = 0; i < n; i++) {
      const v = velocity[i];
      if (v == null || Number.isNaN(v)) continue;
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi === lo) {
      lo = 0;
      hi = 1;
    }
    const pad = (hi - lo) * Y_PAD_FRAC;
    const yTop = hi + pad;
    const yBot = lo - pad;
    const ySpan = yTop - yBot;

    // SVG y grows downward, so flip: plotY = yTop − v.
    const step = Math.max(1, Math.ceil(n / MAX_POINTS));
    const parts = [];
    let pen = "M";
    for (let i = 0; i < n; i += step) {
      const v = velocity[i];
      if (v == null || Number.isNaN(v)) {
        pen = "M"; // gap — lift the pen rather than bridging a dropout
        continue;
      }
      parts.push(`${pen}${(i / fsHz).toFixed(4)},${(yTop - v).toFixed(4)}`);
      pen = "L";
    }

    return { durationS, yTop, yBot, ySpan, pathD: parts.join(" ") };
  }, [velocity, fsHz]);

  const { durationS, yTop, yBot, ySpan, pathD } = geom;

  // `null` window = the whole swim, static (playhead moves across a fixed viewBox). Otherwise a
  // following window clamped to the trace.
  const span = windowS == null ? durationS || 1 : Math.min(windowS, durationS || windowS);
  const follow = windowS != null && durationS > span;

  // Same derivation as VelocityChart.js:50-56 — cycle bounds are sample indices.
  const boundaries = useMemo(
    () =>
      (cycles ?? [])
        .map((c) => (c.start_idx != null ? c.start_idx / fsHz : null))
        .filter((t) => t != null),
    [cycles, fsHz]
  );

  const zeroInRange = 0 <= yTop && 0 >= yBot;
  const markColor = darken(lineColor);

  useEffect(() => {
    if (!(durationS > 0)) return undefined;
    const maxStart = Math.max(0, durationS - span);
    // Static window: pin the left edge at 0 once so click-to-seek maps correctly.
    if (!follow) windowStartRef.current = 0;
    let raf = 0;

    const frame = () => {
      raf = requestAnimationFrame(frame);
      const v = videoElRef?.current;
      const svg = svgRef.current;
      if (!v || !svg || originS == null) return;

      const sessionT = originS + v.currentTime;
      const x0 = follow ? Math.min(Math.max(sessionT - span / 2, 0), maxStart) : 0;
      if (x0 !== windowStartRef.current || follow === false) {
        windowStartRef.current = x0;
        svg.setAttribute("viewBox", `${x0} 0 ${span} ${ySpan}`);
      }

      // The playhead lives INSIDE the panned viewBox, in data coordinates — that keeps it correct
      // at the trace ends, where the window clamps and the playhead is no longer centred.
      const ph = playheadRef.current;
      if (ph) {
        const xs = sessionT.toFixed(4);
        ph.setAttribute("x1", xs);
        ph.setAttribute("x2", xs);
      }

      const ro = readoutRef.current;
      if (ro) {
        const i = Math.round(sessionT * fsHz);
        const val = i >= 0 && i < velocity.length ? velocity[i] : null;
        ro.textContent =
          val == null || Number.isNaN(val) ? "—" : `${val.toFixed(2)} m/s`;
      }

      // Stroke-mark triangles: same x-mapping as the trace, read from the DOM so a changed cycle
      // set needs no effect restart. Only those inside the current window show.
      const layer = markLayerRef.current;
      if (layer) {
        for (const el of layer.children) {
          const bt = Number(el.dataset.bt);
          const frac = (bt - x0) / span;
          if (frac < -0.02 || frac > 1.02) {
            el.style.opacity = "0";
          } else {
            el.style.opacity = "1";
            el.style.left = `${(frac * 100).toFixed(3)}%`;
          }
        }
      }
    };

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [durationS, span, follow, ySpan, originS, videoElRef, velocity, fsHz]);

  const handleClick = useCallback(
    (e) => {
      const svg = svgRef.current;
      if (!svg || !onSeek) return;
      const r = svg.getBoundingClientRect();
      if (r.width <= 0) return;
      const frac = Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1);
      onSeek(windowStartRef.current + frac * span);
    },
    [onSeek, span]
  );

  if (!(durationS > 0)) return null;

  return (
    <div className="px-3 pt-1">
      <div className="mb-0.5 flex items-baseline gap-2">
        <span
          ref={readoutRef}
          className="font-mono text-base font-semibold tabular-nums text-ink"
        >
          —
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-subtle">
          m/s
        </span>
      </div>

      {/* Compact by design (2026-08-14): a tall strip covered the swimmer both inline and
          fullscreen. Small fixed band, clamped so it neither vanishes nor dominates. */}
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${span} ${ySpan}`}
          preserveAspectRatio="none"
          onClick={handleClick}
          className="block h-[clamp(56px,9vh,96px)] w-full cursor-crosshair"
        >
          {zeroInRange && (
            <line
              x1={0}
              x2={durationS}
              y1={yTop}
              y2={yTop}
              stroke="#7f8c8d"
              strokeOpacity={0.35}
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
          )}

          {/* RED default, picker-driven — a blue trace on blue water is invisible (user report,
              2026-08-14). The static VelocityChart below stays blue: it sits on the dark surface
              card, not over video, so it has no legibility problem there. */}
          <path
            d={pathD}
            fill="none"
            stroke={lineColor}
            strokeWidth={2.2}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          <line
            ref={playheadRef}
            x1={0}
            x2={0}
            y1={0}
            y2={ySpan}
            stroke="#f59e0b"
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
          />
        </svg>

        {/* Stroke marks — a downward triangle per cycle start, at the top of the strip, in a
            darker shade of the trace colour (replaced the white dashed lines, 2026-08-14). HTML,
            not SVG, so preserveAspectRatio="none" cannot skew them; positioned per frame. */}
        <div
          ref={markLayerRef}
          className="pointer-events-none absolute inset-x-0 top-0 z-10"
          aria-hidden="true"
        >
          {boundaries.map((t, i) => (
            <span
              key={i}
              data-bt={t}
              className="absolute top-0 -translate-x-1/2"
              style={{
                width: 0,
                height: 0,
                opacity: 0,
                borderLeft: "5px solid transparent",
                borderRight: "5px solid transparent",
                borderTop: `9px solid ${markColor}`,
                filter: "drop-shadow(0 0 1px rgba(0,0,0,0.55))",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
