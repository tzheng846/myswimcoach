"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";

// Rolling velocity/acceleration strip drawn over the video (Phase 64 D6/D7; stacked bands 64-03).
//
// ⚠ THIS IS DELIBERATELY NOT `VelocityChart`. recharts re-renders its whole point set on every
// state change; following a playhead at animation-frame rate through React would re-render
// ~2000 points 60×/s and stutter — which is the exact thing this phase exists to remove.
// Here each polyline is built ONCE in DATA coordinates (x = seconds, y = value) and the window is a
// `viewBox` pan applied imperatively. No React state participates in the animation.
//
// ⚠ 64-03: velocity and acceleration render as SEPARATE stacked bands, each with its own y-scale
// and (for the signed acceleration) a zero line, but sharing ONE window / x0 / scrub / playhead —
// one rAF loop drives every visible band. Velocity alone (the default) behaves exactly as 64-01.
//
// ⚠ `preserveAspectRatio="none"` stretches the viewBox to the element box, which scales x and y
// by different factors. Every stroked element therefore needs `vector-effect="non-scaling-stroke"`
// or lines render as wedges.
//
// ⚠ It is PERMANENT — no `dimmed` prop. Only the control bar below it hides on idle; the trace
// never does. Positioning + scrim are the parent column's job, not this component's.

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

// Once-computed polyline + y-domain for one trace, in DATA coords (x = seconds, y = value). SVG y
// grows downward, so the path stores `yTop − v`. `symmetric` centres the domain on 0 for a signed
// signal (acceleration), putting the zero line in the middle at the same scale either side.
function computeGeom(values, fsHz, symmetric) {
  const n = values.length;
  const durationS = n > 1 ? (n - 1) / fsHz : 0;

  let lo = Infinity;
  let hi = -Infinity;
  for (let i = 0; i < n; i++) {
    const v = values[i];
    if (v == null || Number.isNaN(v)) continue;
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi === lo) {
    if (symmetric) {
      lo = -1;
      hi = 1;
    } else {
      lo = 0;
      hi = 1;
    }
  }

  let yTop;
  let yBot;
  if (symmetric) {
    const a = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
    const pad = a * Y_PAD_FRAC;
    yTop = a + pad;
    yBot = -a - pad;
  } else {
    const pad = (hi - lo) * Y_PAD_FRAC;
    yTop = hi + pad;
    yBot = lo - pad;
  }
  const ySpan = yTop - yBot;

  const step = Math.max(1, Math.ceil(n / MAX_POINTS));
  const parts = [];
  let pen = "M";
  for (let i = 0; i < n; i += step) {
    const v = values[i];
    if (v == null || Number.isNaN(v)) {
      pen = "M"; // gap — lift the pen rather than bridging a dropout
      continue;
    }
    parts.push(`${pen}${(i / fsHz).toFixed(4)},${(yTop - v).toFixed(4)}`);
    pen = "L";
  }

  return { durationS, yTop, yBot, ySpan, pathD: parts.join(" "), hasData: n > 1 };
}

export default function TraceOverlay({
  velocity = [],
  acceleration = [],
  fsHz = 100,
  cycles = [],
  videoElRef, // ref to the <video> element — read directly, never through React state
  originS, // effective sync origin; null until known, in which case the loop idles
  onSeek, // (sessionTimeS) => void
  windowS = 2, // seconds; null = show the whole swim (no follow)
  lineColor = "#ff453a", // velocity trace colour (PlaybackControls swatches)
  accelColor = "#22d3ee", // acceleration trace colour
  showVelocity = true,
  showAcceleration = false,
}) {
  // Per-band DOM handles, populated by callback refs. A ref (not state) because the rAF loop writes
  // to them every frame and must never trigger React; keyed by band so a dynamic 1-or-2 band set
  // needs no conditional hooks.
  const bandDom = useRef({ vel: {}, accel: {} });
  // The window's current left edge, in seconds. Held in a ref because click/scrub-to-seek needs the
  // value the last animation frame wrote, and that frame never touched React.
  const windowStartRef = useRef(0);
  // Active drag-scrub (2026-08-14). While `active`, the rAF loop drives the video from the pointer
  // instead of the video driving the trace. `clientX` is updated by the window pointermove.
  const scrubRef = useRef({ active: false, clientX: 0 });
  // Last time we seeked to, so a still hold doesn't hammer video.currentTime every frame.
  const lastSeekRef = useRef(null);

  const geomV = useMemo(() => computeGeom(velocity, fsHz, false), [velocity, fsHz]);
  const geomA = useMemo(() => computeGeom(acceleration, fsHz, true), [acceleration, fsHz]);

  // Both traces share one x-axis (same fsHz, matched lengths). Duration is whichever exists.
  const durationS = Math.max(geomV.durationS, geomA.durationS);

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

  // A band renders only when toggled on AND it has data (a NULL acceleration_profile just doesn't
  // draw — AC-5; no error).
  const showVel = showVelocity && geomV.hasData;
  const showAccel = showAcceleration && geomA.hasData;

  useEffect(() => {
    if (!(durationS > 0)) return undefined;
    const maxStart = Math.max(0, durationS - span);
    // Static window: pin the left edge at 0 once so click-to-seek maps correctly.
    if (!follow) windowStartRef.current = 0;
    // Edge band + pan rate for scrubbing: while dragging near an edge, the window pans that way so
    // one drag can cross the whole swim. Rate scales with how far into the edge the pointer is.
    const EDGE = 0.1;
    const PAN_PER_FRAME = span * 0.045;
    let raf = 0;

    // Fresh each frame: a band's refs (un)mount when it is toggled. Both bands share the x-geometry,
    // so any visible band's svg gives the same client rect for the scrub fraction.
    const visibleBands = () => {
      const list = [];
      if (bandDom.current.vel.svg)
        list.push({ dom: bandDom.current.vel, geom: geomV, values: velocity, unit: "m/s" });
      if (bandDom.current.accel.svg)
        list.push({ dom: bandDom.current.accel, geom: geomA, values: acceleration, unit: "m/s²" });
      return list;
    };

    const frame = () => {
      raf = requestAnimationFrame(frame);
      const v = videoElRef?.current;
      if (!v || originS == null) return;
      const bands = visibleBands();
      if (bands.length === 0) return;
      const refSvg = bands[0].dom.svg;

      const scrub = scrubRef.current;
      let x0;
      let drawT; // session time to draw the playhead / read out

      if (scrub.active) {
        // POINTER drives the video. The window is frozen at its current left edge except when the
        // pointer is in an edge band, where it pans — so holding mid-strip is stable and holding
        // at an edge jogs through the rest of the swim.
        const r = refSvg.getBoundingClientRect();
        let frac = r.width > 0 ? (scrub.clientX - r.left) / r.width : 0;
        let ws = windowStartRef.current;
        if (maxStart > 0) {
          if (frac < EDGE) {
            ws = Math.max(0, ws - Math.min((EDGE - frac) / EDGE, 1.5) * PAN_PER_FRAME);
          } else if (frac > 1 - EDGE) {
            ws = Math.min(maxStart, ws + Math.min((frac - (1 - EDGE)) / EDGE, 1.5) * PAN_PER_FRAME);
          }
        }
        frac = Math.min(Math.max(frac, 0), 1);
        windowStartRef.current = ws;
        x0 = ws;
        drawT = ws + frac * span;
        // Seek only when the target actually moved — re-seeking to the same time every frame
        // fights the decoder and makes a held scrub feel janky.
        if (lastSeekRef.current == null || Math.abs(drawT - lastSeekRef.current) > 0.004) {
          onSeek?.(drawT);
          lastSeekRef.current = drawT;
        }
      } else {
        // VIDEO drives the trace (playback / normal follow).
        const sessionT = originS + v.currentTime;
        x0 = follow ? Math.min(Math.max(sessionT - span / 2, 0), maxStart) : 0;
        windowStartRef.current = x0;
        drawT = sessionT;
      }

      // Apply the shared window / playhead / readouts / marks to every visible band. Each band has
      // its own y-span (viewBox height), readout unit and value series.
      for (const b of bands) {
        b.dom.svg.setAttribute("viewBox", `${x0} 0 ${span} ${b.geom.ySpan}`);

        // The playhead lives INSIDE the panned viewBox, in data coordinates — that keeps it correct
        // at the trace ends, where the window clamps and the playhead is no longer centred.
        const ph = b.dom.playhead;
        if (ph) {
          const xs = drawT.toFixed(4);
          ph.setAttribute("x1", xs);
          ph.setAttribute("x2", xs);
        }

        const ro = b.dom.readout;
        if (ro) {
          const i = Math.round(drawT * fsHz);
          const val = i >= 0 && i < b.values.length ? b.values[i] : null;
          ro.textContent =
            val == null || Number.isNaN(val) ? "—" : `${val.toFixed(2)} ${b.unit}`;
        }

        // Stroke-mark triangles: same x-mapping as the trace, read from the DOM so a changed cycle
        // set needs no effect restart. Only those inside the current window show.
        const layer = b.dom.marks;
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
      }
    };

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [
    durationS,
    span,
    follow,
    originS,
    videoElRef,
    velocity,
    acceleration,
    fsHz,
    onSeek,
    geomV,
    geomA,
  ]);

  // Drag-scrub: press and slide to move the video continuously (2026-08-14). A plain click is just
  // a zero-length drag, so this subsumes click-to-seek. Pause on grab (user choice). The same
  // handler is attached to every band's svg — both bands scrub the one shared window.
  //
  // ⚠ Move/up are WINDOW listeners, and there is deliberately NO setPointerCapture. The first cut
  // used capture + svg-local up, and the drag got STUCK ACTIVE whenever the up landed off the strip
  // or a touch was interrupted — the loop then re-seeked forever and playback froze / Play went
  // dead. Capture is also flaky on iPadOS and could swallow taps on the Play button. Window
  // pointerup + pointercancel always fire, so the scrub always ends. Works the same for mouse and
  // touch; `touch-action:none` on the svg stops a finger-drag from scrolling the page.
  //
  // The listeners are a local closure whose teardown is stashed in a ref — a self-referential
  // useCallback trips the compiler's use-before-declare rule.
  const teardownRef = useRef(null);

  const onPointerDown = useCallback(
    (e) => {
      if (e.button != null && e.button > 0) return; // primary button / touch only
      teardownRef.current?.(); // defensive: never leave a prior drag attached
      scrubRef.current.active = true;
      scrubRef.current.clientX = e.clientX;
      lastSeekRef.current = null;
      videoElRef?.current?.pause(); // pause on grab

      const move = (ev) => {
        if (scrubRef.current.active) scrubRef.current.clientX = ev.clientX;
      };
      const end = () => {
        scrubRef.current.active = false;
        lastSeekRef.current = null;
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", end);
        window.removeEventListener("pointercancel", end);
        teardownRef.current = null;
      };
      teardownRef.current = end;
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", end);
      window.addEventListener("pointercancel", end);
      e.preventDefault();
    },
    [videoElRef]
  );

  // If we unmount mid-drag (fullscreen toggle, navigation), tear the listeners down.
  useEffect(() => () => teardownRef.current?.(), []);

  if (!(durationS > 0)) return null;
  if (!showVel && !showAccel) return null;

  // One band block: readout header + panned svg + HTML stroke-mark layer. `symmetric` bands
  // (acceleration) always draw the zero line; velocity draws it only if 0 falls in range.
  const renderBand = (key, geom, color, unit, symmetric) => {
    const dom = bandDom.current[key];
    const markColor = darken(color);
    const zeroInRange = symmetric || (0 <= geom.yTop && 0 >= geom.yBot);
    return (
      <div key={key} className="px-3 pt-1">
        <div className="mb-0.5 flex items-baseline gap-2">
          <span
            ref={(el) => {
              dom.readout = el;
            }}
            className="font-mono text-base font-semibold tabular-nums text-ink"
          >
            —
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-subtle">
            {unit}
          </span>
        </div>

        {/* Compact by design (2026-08-14): a tall strip covered the swimmer. Small fixed band,
            clamped so it neither vanishes nor dominates — and two of them still fit the frame. */}
        <div className="relative">
          <svg
            ref={(el) => {
              dom.svg = el;
            }}
            viewBox={`0 0 ${span} ${geom.ySpan}`}
            preserveAspectRatio="none"
            onPointerDown={onPointerDown}
            // touch-none so a finger-drag scrubs instead of scrolling the page (move/up are on
            // window). select-none stops the drag from selecting text on desktop.
            className="block h-[clamp(56px,9vh,96px)] w-full cursor-ew-resize touch-none select-none"
          >
            {zeroInRange && (
              <line
                x1={0}
                x2={durationS}
                y1={geom.yTop}
                y2={geom.yTop}
                stroke="#7f8c8d"
                strokeOpacity={symmetric ? 0.5 : 0.35}
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
              />
            )}

            <path
              d={geom.pathD}
              fill="none"
              stroke={color}
              strokeWidth={2.2}
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />

            <line
              ref={(el) => {
                dom.playhead = el;
              }}
              x1={0}
              x2={0}
              y1={0}
              y2={geom.ySpan}
              stroke="#f59e0b"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
          </svg>

          {/* Stroke marks — a downward triangle per cycle start, at the top of the strip, in a
              darker shade of the band's trace colour. HTML, not SVG, so preserveAspectRatio="none"
              cannot skew them; positioned per frame. */}
          <div
            ref={(el) => {
              dom.marks = el;
            }}
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
  };

  return (
    <>
      {showVel && renderBand("vel", geomV, lineColor, "m/s", false)}
      {showAccel && renderBand("accel", geomA, accelColor, "m/s²", true)}
    </>
  );
}
