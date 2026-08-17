"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// Synced multi-cam player (Phase 69-03). ONE master timeline (the session clock) drives every
// camera and the velocity trace together — each video seeks to `sessionTime − its origin_s`, the
// same way the stacked traces share an x-axis. The focused camera is the timing master (its
// currentTime sets sessionTime) and the only one with audio; the others play muted and are
// drift-corrected each frame rather than hard-seeked per frame (the perf model, CONTEXT D6). This
// is the "side by side on one view window" the coach asked for.
export default function MultiCamPlayer({ videos, velocity, fsHz, sessionDurationS }) {
  const playable = useMemo(() => (videos || []).filter((v) => v.url), [videos]);

  const elsRef = useRef({}); // id -> <video> element (written by ref callbacks, read in effects only)
  const [focusedId, setFocusedId] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);

  const focused = focusedId ?? playable[0]?.id ?? null;
  const dur = sessionDurationS && sessionDurationS > 0 ? sessionDurationS : 0;

  // Stable ref callback per camera id, memoized on the list — created outside render execution, so
  // no ref access during render and no per-render detach/reattach churn.
  const refCallbacks = useMemo(() => {
    const m = {};
    for (const v of playable) {
      m[v.id] = (el) => {
        if (el) elsRef.current[v.id] = el;
        else delete elsRef.current[v.id];
      };
    }
    return m;
  }, [playable]);

  const seekAll = useCallback(
    (t) => {
      for (const v of playable) {
        const el = elsRef.current[v.id];
        if (!el) continue;
        const target = t - (v.origin_s != null ? v.origin_s : 0);
        const d = Number.isFinite(el.duration) ? el.duration : 0;
        el.currentTime = Math.min(Math.max(target, 0), d || Math.max(target, 0));
      }
    },
    [playable]
  );

  // Latest values for the rAF loop, without stale closures.
  const stateRef = useRef({ playable, focused });
  useEffect(() => {
    stateRef.current = { playable, focused };
  }, [playable, focused]);

  // The synced loop runs only while playing. The focused camera's clock sets sessionTime; the others
  // are drift-corrected only when they slip >0.2 s, so they aren't re-seeked every frame.
  useEffect(() => {
    if (!isPlaying) return undefined;
    let raf = 0;
    const loop = () => {
      const { playable: ps, focused: f } = stateRef.current;
      const fv = ps.find((v) => v.id === f);
      const fel = fv && elsRef.current[fv.id];
      if (fel) {
        const t = (fv.origin_s != null ? fv.origin_s : 0) + fel.currentTime;
        setSessionTime(t);
        for (const v of ps) {
          if (v.id === fv.id) continue;
          const el = elsRef.current[v.id];
          if (!el) continue;
          const target = t - (v.origin_s != null ? v.origin_s : 0);
          if (Math.abs(el.currentTime - target) > 0.2) {
            const d = Number.isFinite(el.duration) ? el.duration : 0;
            el.currentTime = Math.min(Math.max(target, 0), d || Math.max(target, 0));
          }
        }
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [isPlaying]);

  const play = () => {
    seekAll(sessionTime);
    for (const v of playable) elsRef.current[v.id]?.play().catch(() => {});
    setIsPlaying(true);
  };
  const pause = () => {
    for (const v of playable) elsRef.current[v.id]?.pause();
    setIsPlaying(false);
  };
  const onScrub = (e) => {
    const t = Number(e.target.value);
    setSessionTime(t);
    seekAll(t);
  };

  const cols = playable.length <= 1 ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2";

  // Velocity trace polyline (downsampled to ~640 px) + a playhead at sessionTime.
  const tracePts = useMemo(() => {
    const n = velocity?.length ?? 0;
    if (!n || !dur) return "";
    const W = 640, H = 48;
    const step = Math.max(1, Math.floor(n / W));
    let max = 0.001;
    for (let i = 0; i < n; i += step) max = Math.max(max, Math.abs(velocity[i]));
    const pts = [];
    for (let i = 0; i < n; i += step) {
      const x = ((i / fsHz) / dur) * W;
      const y = H - (Math.abs(velocity[i]) / max) * (H - 4) - 2;
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return pts.join(" ");
  }, [velocity, fsHz, dur]);
  const playX = dur ? Math.min(Math.max(sessionTime / dur, 0), 1) * 640 : 0;

  if (!playable.length) return null;

  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-3">
      <div className={`grid gap-2 ${cols}`}>
        {playable.map((v) => (
          <button
            key={v.id}
            type="button"
            onClick={() => setFocusedId(v.id)}
            className={`relative block overflow-hidden rounded-lg bg-black text-left ${
              v.id === focused ? "ring-2 ring-accent" : ""
            }`}
          >
            <video
              ref={refCallbacks[v.id]}
              src={v.url}
              playsInline
              preload="metadata"
              muted={v.id !== focused}
              className="aspect-video w-full bg-black object-contain"
            />
            <span className="absolute left-2 top-2 rounded-full bg-surface/80 px-2 py-0.5 text-[11px] text-subtle">
              {v.label || (v.role === "phone" ? "Phone" : "Camera")}
            </span>
            {v.origin_s == null && (
              <span className="absolute right-2 top-2 rounded-full bg-surface/80 px-2 py-0.5 text-[11px] text-warning">
                not synced
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="mt-2 rounded-md border border-navy/50 bg-surface-2 p-1">
        <svg viewBox="0 0 640 48" width="100%" height="44" preserveAspectRatio="none" aria-hidden="true">
          <polyline
            points={tracePts}
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
          <line
            x1={playX}
            y1="0"
            x2={playX}
            y2="48"
            stroke="var(--color-ink)"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      </div>

      <div className="mt-2 flex items-center gap-3 text-xs">
        <button
          onClick={isPlaying ? pause : play}
          className="rounded-md border border-surface-3 bg-surface-2 px-2.5 py-1 font-semibold text-subtle hover:text-ink"
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
        <span className="w-12 text-right font-mono text-muted">{sessionTime.toFixed(1)}s</span>
        <input
          type="range"
          min="0"
          max={dur || 0}
          step="0.05"
          value={Math.min(sessionTime, dur || 0)}
          onChange={onScrub}
          className="flex-1"
        />
        <span className="w-12 font-mono text-muted">{(dur || 0).toFixed(1)}s</span>
      </div>
      <p className="mt-1 text-[11px] text-muted">
        One timeline drives all cameras and the trace. Click a camera to focus its audio.
      </p>
    </div>
  );
}
