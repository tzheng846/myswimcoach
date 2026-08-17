"use client";

// Playback + sync control bar for VideoTracePanel (Phase 64, renamed from FullscreenControls).
//
// ⚠ Renamed because it now renders INLINE on the report card, not only in fullscreen — the old
// name was a lie once the panel became embeddable.
//
// It exists because the NATIVE <video> control bar carries its own fullscreen button, which would
// promote the video element alone into the top layer and strand the trace. `controlsList=
// "nofullscreen"` was rejected: Chrome/Edge only.
//
// Presentational only — it holds no video state and never talks to the API. The sync buttons call
// VideoPane's `nudge`/`saveSync`, keeping ONE writer of `video_origin_s` (58-04's invariant, D9).
// Positioning is NOT its job either: VideoTracePanel's bottom column places it; `dimmed` only
// fades it (fullscreen auto-hide), and the trace above it is never dimmed (item 1).

const BTN =
  "rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink";

// Rolling-window presets. `null` = show the whole swim (no follow). 1 s was dropped as too narrow
// to read a stroke (2026-08-16).
const WINDOWS = [
  { label: "2s", v: 2 },
  { label: "4s", v: 4 },
  { label: "8s", v: 8 },
  { label: "All", v: null },
];

// Trace colours — high saturation so the line reads over pool water without a frosted backdrop.
// Red default (a blue line on blue water is invisible — user report 2026-08-14).
export const TRACE_COLORS = [
  { label: "Red", v: "#ff453a" },
  { label: "Green", v: "#00e676" },
  { label: "Yellow", v: "#ffea00" },
  { label: "Blue", v: "#2979ff" },
];

// Acceleration palette (Phase 64-03) — a distinct set from the velocity swatches so the two traces
// never share a colour by accident. Cyan default.
export const ACCEL_COLORS = [
  { label: "Cyan", v: "#22d3ee" },
  { label: "Orange", v: "#ff9f0a" },
  { label: "Magenta", v: "#ff2d95" },
  { label: "Lime", v: "#a3e635" },
];

export default function PlaybackControls({
  isPlaying,
  onTogglePlay,
  onStep,
  rates = [],
  rate,
  onRate,
  muted,
  onToggleMute,
  originS,
  savedOrigin,
  onNudge,
  onSave,
  busy,
  windowSpanS, // number | null (null = All)
  onWindowSpanS,
  lineColor, // velocity trace colour
  onLineColor,
  // Phase 64-03 — trace visibility + acceleration colour. Page-owned, so a toggle here also
  // shows/hides the static chart below (AC-4). The accel swatch row only appears when accel is on.
  showVelocity = true,
  showAcceleration = false,
  onToggleVelocity,
  onToggleAcceleration,
  accelColor,
  onAccelColor,
  isFullscreen,
  onToggleFullscreen,
  dimmed = false,
}) {
  const dirty = originS != null && originS !== savedOrigin;
  const chip = (active) =>
    `rounded-md border px-2 py-1 font-semibold ${
      active
        ? "border-accent bg-accent text-white"
        : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
    }`;

  return (
    <div
      className={`px-3 pb-2 pt-1 text-xs transition-opacity duration-300 ${
        dimmed ? "pointer-events-none opacity-0" : "opacity-100"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={onTogglePlay} className={BTN} title="Play / pause (Space)">
          {isPlaying ? "❚❚ Pause" : "▶ Play"}
        </button>
        <button onClick={() => onStep(-1)} className={BTN} title="Back one frame (←)">
          −1 frame
        </button>
        <button onClick={() => onStep(1)} className={BTN} title="Forward one frame (→)">
          +1 frame
        </button>

        <span className="ml-1 text-muted">Speed</span>
        {rates.map((r) => (
          <button
            key={r}
            onClick={() => onRate(r)}
            className={`rounded-md border px-2 py-1 font-semibold ${
              rate === r
                ? "border-accent bg-accent text-white"
                : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
            }`}
          >
            {r}×
          </button>
        ))}

        <button onClick={onToggleMute} className={BTN} title="Mute / unmute">
          {muted ? "🔇 Muted" : "🔊 Sound"}
        </button>

        {/* Absent where the stage can't fullscreen (e.g. iOS Safari), rather than a dead button. */}
        {onToggleFullscreen && (
          <button
            onClick={onToggleFullscreen}
            className="ml-auto rounded-md border border-surface-3 bg-surface-2 px-2.5 py-1 font-semibold text-subtle hover:text-ink"
            title={isFullscreen ? "Exit fullscreen (Esc)" : "Fullscreen"}
          >
            {isFullscreen ? "Exit fullscreen" : "⛶ Fullscreen"}
          </button>
        )}
      </div>

      {/* Phase 64-03 — which traces to show (velocity default on, acceleration off). Toggling
          here also shows/hides the matching static chart below the panel (page-level state). */}
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <span className="text-muted">Show</span>
        <button onClick={() => onToggleVelocity?.(!showVelocity)} className={chip(showVelocity)}>
          Velocity
        </button>
        <button
          onClick={() => onToggleAcceleration?.(!showAcceleration)}
          className={chip(showAcceleration)}
        >
          Acceleration
        </button>

        {showAcceleration && (
          <>
            <span className="ml-2 text-muted">Accel colour</span>
            {ACCEL_COLORS.map((c) => (
              <button
                key={c.v}
                onClick={() => onAccelColor?.(c.v)}
                title={c.label}
                aria-label={`Acceleration colour ${c.label}`}
                style={{ backgroundColor: c.v }}
                className={`h-5 w-5 rounded-full transition ${
                  accelColor === c.v
                    ? "ring-2 ring-white ring-offset-1 ring-offset-black"
                    : "ring-1 ring-black/40 hover:ring-white/60"
                }`}
              />
            ))}
          </>
        )}
      </div>

      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <span className="text-muted">Window</span>
        {WINDOWS.map((w) => (
          <button
            key={w.label}
            onClick={() => onWindowSpanS(w.v)}
            className={`rounded-md border px-2 py-1 font-semibold ${
              windowSpanS === w.v
                ? "border-accent bg-accent text-white"
                : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
            }`}
          >
            {w.label}
          </button>
        ))}

        <span className="ml-2 text-muted">Colour</span>
        {TRACE_COLORS.map((c) => (
          <button
            key={c.v}
            onClick={() => onLineColor(c.v)}
            title={c.label}
            aria-label={`Trace colour ${c.label}`}
            style={{ backgroundColor: c.v }}
            className={`h-5 w-5 rounded-full transition ${
              lineColor === c.v
                ? "ring-2 ring-white ring-offset-1 ring-offset-black"
                : "ring-1 ring-black/40 hover:ring-white/60"
            }`}
          />
        ))}

        <span className="ml-2 text-muted">Sync</span>
        <button onClick={() => onNudge(-0.1)} className={BTN}>
          −0.1s
        </button>
        <span className="w-16 text-center font-mono text-ink">
          {originS != null ? `${originS.toFixed(2)} s` : "—"}
        </span>
        <button onClick={() => onNudge(0.1)} className={BTN}>
          +0.1s
        </button>
        <button
          onClick={onSave}
          disabled={busy || !dirty}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            dirty ? "bg-accent text-white" : "bg-surface-2 text-muted"
          }`}
        >
          {busy ? "…" : "Save sync"}
        </button>
        {/* stored vs computed — the only cue that a synced origin is real vs end-anchored. */}
        <span className="font-mono text-[10px] text-muted">
          {savedOrigin != null ? "stored" : "computed"}
        </span>
      </div>
    </div>
  );
}
