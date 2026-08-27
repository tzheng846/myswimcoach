"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";
import TraceOverlay from "./TraceOverlay";

const FRAME_S = 1 / 30;
const RATES = [0.25, 0.5, 1];

// In-stage control-bar buttons (light on the video's bottom gradient, so they read in fullscreen).
const BAR_BTN =
  "rounded-md border border-white/30 bg-black/40 px-2 py-1 font-semibold text-white/80 hover:text-white";
const BAR_BTN_ON = "rounded-md border border-accent bg-accent px-2 py-1 font-semibold text-white";

// Rolling-window presets for the on-tile strip (mirrors the report overlay). null = whole swim.
const STRIP_WINDOWS = [
  { label: "4s", v: 4 },
  { label: "8s", v: 8 },
  { label: "All", v: null },
];

// One camera on the annotate multi-cam hub (Phase 71). A single <video> with frame-step, speed,
// MANUAL two-point align ("Set sync" → click the trace at the same moment), ±0.1 s nudge, and an
// explicit Save. When `active`, it drives the trace playhead / seek / frame-step for mark placing.
// Externals persist via PATCH /videos/{id}; the phone/primary via the legacy POST /video.
// ⚠ No push-off / dive detection anywhere (removed 71-02, D10) — alignment is coach-controlled.
export default function CameraTile({
  sessionId,
  video,
  active = false,
  aligning = false,
  alignClick, // { time, seq } — bumped by the parent when the coach clicks the trace in align mode
  onArmAlign, // () => void — "Set sync": arm this camera for the next trace click
  onAlignConsumed, // () => void — this camera used the trace click; parent clears align mode
  onMakeActive, // () => void
  onPlayhead, // (sessionTimeS) => void — called only while active
  // ⚠ NO `= null` defaults on the ref props (react-hooks/immutability treats a defaulted prop as a
  // local and flags assigning to `.current`). `undefined` guards identically (`if (!ref) return`).
  seekRef, // ref; assigned only while active
  frameStepRef, // ref; assigned only while active
  onChanged, // () => void — refetch the list after delete (NOT after save/label — avoids url churn)
  velocity = [], // session velocity_profile — feeds the active tile's context strip (81-01)
  fsHz = 100, // sample rate for that strip's x-axis
  phaseTools = [], // [{key,label,color}] — boundary marker buttons on the active tile (81-01)
  marks = [], // placed mark times (s) — drawn as ticks on the strip for in-fullscreen confirmation
  onPlaceBoundary, // (phaseKey, sessionT) => void — place/move a boundary at the current frame
  onPlaceStrokeMark, // (sessionT) => void — append a stroke mark at the current frame
}) {
  const videoRef = useRef(null);
  const [label, setLabel] = useState(video.label ?? "");
  const [origin, setOrigin] = useState(video.origin_s ?? null); // pending origin
  const [savedOrigin, setSavedOrigin] = useState(video.origin_s ?? null);
  const [rate, setRate] = useState(1);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  // Stage-fullscreen (active tile only): fullscreen the STAGE div, not the <video>, so the marker
  // bar + trace stay on screen and the coach marks without exiting (Phase 81 fullscreen-marking).
  const stageRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [canFullscreen, setCanFullscreen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [windowS, setWindowS] = useState(4); // strip rolling window (s); null = whole swim (All)

  const isPrimary = video.role === "phone";
  const dirty = origin != null && origin !== savedOrigin;
  const effectiveOrigin = origin ?? savedOrigin;
  // Overlay/marking mode: the active camera turns into the fullscreen marking stage only once it's
  // SYNCED (an origin is needed to map video time ↔ session time, and to draw the strip). Until then
  // it keeps native controls so the coach can scrub freely to the landmark frame for "Set sync".
  const overlayMode = active && effectiveOrigin != null;

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = rate;
  }, [rate, video.url]);

  // sessionTime = origin + videoTime — reported to the parent only while this is the active camera.
  const reportPlayhead = useCallback(() => {
    const v = videoRef.current;
    if (active && v && effectiveOrigin != null) onPlayhead?.(effectiveOrigin + v.currentTime);
  }, [active, effectiveOrigin, onPlayhead]);

  const step = useCallback(
    (frames) => {
      const v = videoRef.current;
      if (!v) return;
      v.pause();
      const d = Number.isFinite(v.duration) ? v.duration : 0;
      const next = v.currentTime + frames * FRAME_S;
      v.currentTime = Math.min(Math.max(next, 0), d || Math.max(next, 0));
      reportPlayhead();
    },
    [reportPlayhead]
  );

  // Seek this camera to a SESSION time (inverse of origin + videoTime), clamped to the clip. Shared
  // by the chart's Seek tool / keyboard (via seekRef) and the on-tile trace strip's drag-scrub
  // (TraceOverlay onSeek) so the clamp lives in exactly one place.
  const seekTo = useCallback(
    (sessionT) => {
      const v = videoRef.current;
      if (!v || effectiveOrigin == null) return;
      const d = Number.isFinite(v.duration) ? v.duration : 0;
      v.currentTime = Math.min(Math.max(sessionT - effectiveOrigin, 0), d);
      reportPlayhead();
    },
    [effectiveOrigin, reportPlayhead]
  );

  // This tile's CURRENT session time (origin + video time), read off the element at click — fresher
  // than the page's onTimeUpdate playhead, so a marker button always lands on the frame on screen.
  const currentSessionT = useCallback(() => {
    const v = videoRef.current;
    if (!v || effectiveOrigin == null) return null;
    return effectiveOrigin + v.currentTime;
  }, [effectiveOrigin]);

  // Placed marks as pseudo-cycles so the strip shows a tick where each landed — the in-fullscreen
  // confirmation a tap registered (the AnnotationChart is off-screen there). Uses TraceOverlay as-is.
  const markCycles = useMemo(
    () => marks.map((t) => ({ start_idx: Math.round(t * fsHz) })),
    [marks, fsHz]
  );

  // Track fullscreen from the EVENT (Esc + browser chrome change it too), not the click handler.
  useEffect(() => {
    const onChange = () => setIsFullscreen(document.fullscreenElement === stageRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);
  // Some engines (iOS Safari) can't fullscreen an arbitrary element — hide the button rather than
  // ship a dead one. The stage only exists once the video is present.
  useEffect(() => {
    setCanFullscreen(
      typeof stageRef.current?.requestFullscreen === "function" && !!document.fullscreenEnabled
    );
  }, [active, video.url]);
  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    else stageRef.current?.requestFullscreen?.().catch(() => {});
  }, []);
  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play().catch(() => {});
    else v.pause();
  }, []);

  // Marking wiring: while active, this camera answers the chart's Seek tool and keyboard frame-step.
  // No cleanup-null: only the active tile assigns, so the shared ref holds the newest active fn —
  // nulling in cleanup would race across tiles when the active camera switches.
  useEffect(() => {
    if (!active || !seekRef) return;
    seekRef.current = seekTo;
  }, [active, seekRef, seekTo]);

  useEffect(() => {
    if (!active || !frameStepRef) return;
    frameStepRef.current = step;
  }, [active, frameStepRef, step]);

  // Two-point align: when armed (aligning) and the coach clicks the trace, the parent bumps
  // alignClick.seq; map the CURRENT video frame to that trace time → origin = traceTime − videoTime.
  const lastAlignSeq = useRef(0);
  useEffect(() => {
    if (!aligning || !alignClick || alignClick.time == null) return;
    if (alignClick.seq === lastAlignSeq.current) return;
    lastAlignSeq.current = alignClick.seq;
    const v = videoRef.current;
    if (!v) return;
    setOrigin(Math.round((alignClick.time - v.currentTime) * 100) / 100);
    onAlignConsumed?.();
  }, [aligning, alignClick, onAlignConsumed]);

  const nudge = (d) => {
    const base = origin ?? savedOrigin;
    if (base == null) return;
    setOrigin(Math.round((base + d) * 100) / 100);
  };

  const saveSync = async () => {
    if (origin == null) return;
    setBusy(true);
    setMsg(null);
    try {
      if (isPrimary) {
        const fd = new FormData();
        fd.append("video_origin_s", String(origin));
        await apiUpload(`/sessions/${sessionId}/video`, fd);
      } else {
        await apiFetch(`/sessions/${sessionId}/videos/${video.id}`, {
          method: "PATCH",
          body: JSON.stringify({ origin_s: origin }),
        });
      }
      setSavedOrigin(origin);
      setMsg("Saved ✓");
    } catch (e) {
      setMsg(`Save failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const saveLabel = async () => {
    if (isPrimary || label === (video.label ?? "")) return;
    setBusy(true);
    try {
      await apiFetch(`/sessions/${sessionId}/videos/${video.id}`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      });
    } catch (e) {
      setMsg(`Rename failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (isPrimary) return;
    setBusy(true);
    try {
      await apiFetch(`/sessions/${sessionId}/videos/${video.id}`, { method: "DELETE" });
      onChanged?.();
    } catch (e) {
      setMsg(`Delete failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`rounded-xl border ${active ? "border-accent" : "border-navy/50"} bg-surface p-3`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        {isPrimary ? (
          <span className="text-sm font-semibold text-ink">Phone</span>
        ) : (
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={saveLabel}
            placeholder="Label (e.g. Underwater front)"
            className="min-w-0 flex-1 rounded-md border border-surface-3 bg-surface-2 px-2 py-1 text-sm text-ink placeholder:text-muted"
          />
        )}
        {active ? (
          <span className="shrink-0 rounded-md bg-accent px-2 py-0.5 text-[11px] font-semibold text-white">
            ● Marking
          </span>
        ) : (
          <button
            onClick={onMakeActive}
            className="shrink-0 rounded-md border border-surface-3 bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-subtle hover:text-ink"
          >
            Mark from this
          </button>
        )}
      </div>

      {video.url ? (
        <div
          ref={stageRef}
          className={
            isFullscreen
              ? "relative flex h-full w-full flex-col bg-black"
              : overlayMode
              ? "relative h-[clamp(180px,34vh,440px)] w-full overflow-hidden rounded-lg bg-black"
              : "relative w-full overflow-hidden rounded-lg bg-black"
          }
        >
          <video
            ref={videoRef}
            src={video.url}
            controls={!overlayMode}
            playsInline
            preload="metadata"
            onTimeUpdate={reportPlayhead}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            className={
              overlayMode
                ? "absolute inset-0 h-full w-full bg-black object-contain"
                : "block max-h-[clamp(140px,26vh,360px)] w-full bg-black object-contain"
            }
          />

          {/* Active = the marking camera. The velocity strip + a control bar live INSIDE the stage,
              so both stay on screen in fullscreen and the coach marks the frame they see without
              exiting (Phase 81 — the fullscreen-marking ask). The bottom gradient keeps them legible
              over the water; the <video> never leaves this div, so playback + the signed URL survive.
              cycles={[]} — placed marks stay on the AnnotationChart below. */}
          {overlayMode && (
            <div className="absolute inset-x-0 bottom-0 z-20 flex flex-col bg-gradient-to-t from-black/85 via-black/45 to-transparent pt-4">
              <TraceOverlay
                velocity={velocity}
                fsHz={fsHz}
                cycles={markCycles}
                videoElRef={videoRef}
                originS={effectiveOrigin}
                onSeek={seekTo}
                windowS={windowS}
              />
              <div className="flex flex-wrap items-center gap-1.5 px-3 pb-2 pt-1 text-xs">
                <button onClick={togglePlay} className={BAR_BTN} title="Play / pause">
                  {isPlaying ? "❚❚" : "▶"}
                </button>
                <button onClick={() => step(-1)} className={BAR_BTN} title="Back one frame">
                  −1
                </button>
                <button onClick={() => step(1)} className={BAR_BTN} title="Forward one frame">
                  +1
                </button>
                {RATES.map((r) => (
                  <button key={r} onClick={() => setRate(r)} className={rate === r ? BAR_BTN_ON : BAR_BTN}>
                    {r}×
                  </button>
                ))}

                <span className="ml-1 text-[10px] font-semibold uppercase tracking-wide text-white/55">
                  Window
                </span>
                {STRIP_WINDOWS.map((w) => (
                  <button
                    key={w.label}
                    onClick={() => setWindowS(w.v)}
                    className={windowS === w.v ? BAR_BTN_ON : BAR_BTN}
                  >
                    {w.label}
                  </button>
                ))}

                <span className="ml-1 text-[10px] font-semibold uppercase tracking-wide text-white/55">
                  Mark
                </span>
                {phaseTools.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => {
                      const st = currentSessionT();
                      if (st != null) onPlaceBoundary?.(t.key, st);
                    }}
                    className="rounded-md border bg-black/40 px-2 py-1 font-semibold hover:brightness-110"
                    style={{ borderColor: t.color, color: t.color }}
                    title={`Mark ${t.label} at the current frame`}
                  >
                    {t.label}
                  </button>
                ))}
                <button
                  onClick={() => {
                    const st = currentSessionT();
                    if (st != null) onPlaceStrokeMark?.(st);
                  }}
                  className="rounded-md border border-white/30 bg-black/40 px-2 py-1 font-semibold text-white/80 hover:text-white"
                  title="Append a stroke mark at the current frame"
                >
                  + mark
                </button>

                {canFullscreen && (
                  <button
                    onClick={toggleFullscreen}
                    className="ml-auto rounded-md border border-white/30 bg-black/40 px-2 py-1 font-semibold text-white/80 hover:text-white"
                    title={isFullscreen ? "Exit fullscreen (Esc)" : "Fullscreen"}
                  >
                    {isFullscreen ? "Exit ⛶" : "⛶"}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="py-6 text-center text-xs text-muted">Video unavailable.</p>
      )}

      {/* Frame step + speed + sync status — shown unless the tile is in marking mode (active AND
          synced), which carries these in its in-stage bar so they survive fullscreen. An unsynced
          active tile keeps this row for scrubbing to the landmark frame during Set sync. */}
      {!overlayMode && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          <button onClick={() => step(-1)} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">−1 frame</button>
          <button onClick={() => step(1)} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">+1 frame</button>
          <span className="ml-1 text-muted">Speed</span>
          {RATES.map((r) => (
            <button
              key={r}
              onClick={() => setRate(r)}
              className={`rounded-md border px-2 py-1 font-semibold ${
                rate === r ? "border-accent bg-accent text-white" : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
              }`}
            >
              {r}×
            </button>
          ))}
          <span className={`ml-auto text-[11px] ${savedOrigin != null ? "text-success" : "text-warning"}`}>
            {savedOrigin != null ? "synced" : "needs sync"}
          </span>
        </div>
      )}

      {/* Manual two-point align + nudge + save (no push-off, no dive detection — D10/D11) */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <button
          onClick={onArmAlign}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            aligning ? "border border-accent bg-accent text-white" : "border border-accent text-primary"
          }`}
          title="Scrub to a landmark frame, click this, then click the trace at the same moment"
        >
          {aligning ? "Click the trace…" : "Set sync"}
        </button>
        <button onClick={() => nudge(-0.1)} disabled={effectiveOrigin == null} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">−0.1s</button>
        <span className="w-14 text-center font-mono text-ink">{effectiveOrigin != null ? `${effectiveOrigin.toFixed(2)} s` : "—"}</span>
        <button onClick={() => nudge(0.1)} disabled={effectiveOrigin == null} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">+0.1s</button>
        <button
          onClick={saveSync}
          disabled={busy || !dirty}
          className={`rounded-md px-2.5 py-1 font-semibold ${dirty ? "bg-accent text-white" : "bg-surface-2 text-muted"}`}
        >
          {busy ? "…" : "Save"}
        </button>
      </div>

      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-[11px] text-muted">
          {aligning
            ? "Now click the trace at the same moment shown in this video."
            : "Scrub to a landmark, click Set sync, then click the trace at that instant."}
        </p>
        {!isPrimary && (
          <button onClick={remove} disabled={busy} className="shrink-0 text-[11px] font-semibold text-subtle hover:text-danger">
            Delete
          </button>
        )}
      </div>
      {msg && (
        <p className={`mt-1 text-[11px] ${/fail/i.test(msg) ? "text-danger" : "text-success"}`}>{msg}</p>
      )}
    </div>
  );
}
