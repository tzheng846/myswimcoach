"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";
import PlaybackControls from "@/components/portal/PlaybackControls";

// One frame, assumed. HTML5 video exposes no frame rate — requestVideoFrameCallback
// would, and is deliberately not used: reading true frame timing is a bigger change than
// stepping needs. At 60 fps footage this steps two frames, which is still far finer than
// the ~±0.3 s a scrub lands within.
const FRAME_S = 1 / 30;

const RATES = [0.25, 0.5, 1];

// Session video: signed-URL playback synced to the velocity trace.
// sessionTime = originS + videoTime (44-03 end-anchor convention).
// No video attached → an upload input (velocity-only annotation stays fully usable).
export default function VideoPane({
  sessionId,
  video, // {path, origin_s} | null — origin_s null means NEVER STORED, not zero
  onPlayhead, // (sessionTimeS | null) => void
  seekRef, // ref; pane assigns seekRef.current = (sessionTimeS) => void
  frameStepRef, // ref; pane assigns frameStepRef.current = (frames) => void
  onVideoChange, // ({path, origin_s}) => void
  sessionDurationS = null, // encoder-trace duration; drives the end-anchored origin (58-04)
  // Phase 64 — panel mode, used ONLY by VideoTracePanel. ALL of these default to the pre-64
  // behaviour, so the annotate page (which passes none of them) hits the unchanged windowed card.
  panel = false, // render a fill-video + PlaybackControls instead of the card + native controls
  overlay = null, // node (a <TraceOverlay/>) laid out above the controls in panel mode
  isFullscreen = false, // is the enclosing stage currently fullscreen (label + auto-hide)
  onToggleFullscreen, // () => void — enter/exit, owned by VideoTracePanel
  windowSpanS = 2, // rolling-window preset, threaded through to PlaybackControls
  onWindowSpanS, // (number|null) => void
  lineColor, // trace colour, threaded through to PlaybackControls' swatches
  onLineColor, // (hex) => void
  // ⚠ NO `= null` defaults on the ref props below. `react-hooks/immutability` treats a
  // destructured prop that has a default as a LOCAL VARIABLE, and then flags assigning to its
  // `.current` as mutating a local after render — which is why seekRef/frameStepRef have no
  // defaults either. `undefined` guards identically (`if (!ref) return`).
  videoElRef, // ref; pane assigns the <video> DOM node so TraceOverlay can read currentTime
  playToggleRef, // ref; pane assigns playToggleRef.current = () => void (Space key)
  onOriginChange, // (effectiveOriginS | null) => void — the overlay needs the live origin
  dimmed = false, // auto-hide: fade the CONTROL BAR only (the trace above it never dims, item 1)
}) {
  const videoRef = useRef(null);
  const [url, setUrl] = useState(null);
  // ⚠ 58-04: this used to be `useState(video?.origin_s ?? 0)`. A session whose video arrived via
  // the mobile background upload queue has NO stored origin — that queue posts the file only —
  // so it defaulted to 0 and the video sat silently out of sync by the whole pre-roll. null now
  // means "never stored", and the end-anchored value below is computed instead.
  // ⚠ `??` NOT `||`: a stored origin of exactly 0 is a real, deliberate value.
  const [originS, setOriginS] = useState(video?.origin_s ?? null);
  const [savedOrigin, setSavedOrigin] = useState(video?.origin_s ?? null);
  const [videoDurationS, setVideoDurationS] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [rate, setRate] = useState(1);
  // Phase 64: the custom bar has no native control to read from, so play state and mute are
  // tracked here. Both mirror the element rather than driving it — `muted` is never bound as a
  // React prop, or the native controls in windowed mode would fight it.
  const [isPlaying, setIsPlaying] = useState(false);
  const [muted, setMuted] = useState(false);

  // Callback ref: keeps the internal `videoRef` (every existing consumer) AND hands the node to
  // the stage so TraceOverlay can read `currentTime` at animation-frame rate without React.
  const setVideoEl = useCallback(
    (el) => {
      videoRef.current = el;
      if (videoElRef) videoElRef.current = el;
    },
    [videoElRef]
  );

  // End-anchored convention (44-03): recording and filming stop together, so the video's FIRST
  // frame sits at (sessionDuration − videoDuration) on the session clock. Mirrors
  // swimnetics-mobile VideoOverlayScreen.js:69.
  const endAnchoredOriginS =
    sessionDurationS != null && videoDurationS != null
      ? sessionDurationS - videoDurationS
      : null;

  // The origin actually in effect. Stored ALWAYS wins (Phase 60-03 D11 as amended: never
  // overwrite an existing origin); otherwise fall back to the computed one. Stays null until
  // video metadata arrives — deliberately NOT 0, or the trace would jump when it loads.
  const effectiveOriginS = originS ?? endAnchoredOriginS;

  // Separate refs on purpose. Phase 60-03 hit a real bug by sharing one: the manual-nudge save
  // was gated on the ref the auto-post set, so skipping the auto-post silently swallowed the
  // user's first nudge — losing the only way to repair a bad origin by hand.
  const autoSavedRef = useRef(false);

  // Signed URL expires (3600 s) — always refetched on mount, never persisted.
  useEffect(() => {
    if (!video?.path) {
      setUrl(null);
      return;
    }
    let alive = true;
    (async () => {
      try {
        const r = await apiFetch(`/sessions/${sessionId}/video-url`);
        if (!alive) return;
        setUrl(r.url);
        if (r.origin_s != null) {
          setOriginS(r.origin_s);
          setSavedOrigin(r.origin_s);
        }
      } catch (e) {
        if (alive) setMsg(`Could not load video: ${e.message}`);
      }
    })();
    return () => {
      alive = false;
    };
  }, [sessionId, video?.path]);

  // Expose seek to the page (Seek tool routes chart clicks here).
  useEffect(() => {
    if (!seekRef) return;
    seekRef.current = (sessionT) => {
      const v = videoRef.current;
      if (!v || effectiveOriginS == null) return; // no origin yet — a seek would land at NaN
      const dur = Number.isFinite(v.duration) ? v.duration : 0;
      v.currentTime = Math.min(Math.max(sessionT - effectiveOriginS, 0), dur);
      onPlayhead?.(effectiveOriginS + v.currentTime);
    };
    return () => {
      seekRef.current = null;
    };
  }, [seekRef, effectiveOriginS, url, onPlayhead]);

  // Frame step. Pause FIRST — stepping while playing fights the playhead — and push the
  // new time to the chart explicitly: `timeupdate` is throttled to ~4 Hz and does not
  // fire for a sub-100 ms seek, which would leave the chart marker stale exactly when
  // precision matters.
  const step = useCallback(
    (frames) => {
      const v = videoRef.current;
      if (!v) return;
      v.pause();
      const dur = Number.isFinite(v.duration) ? v.duration : 0;
      v.currentTime = Math.min(Math.max(v.currentTime + frames * FRAME_S, 0), dur);
      if (effectiveOriginS != null) onPlayhead?.(effectiveOriginS + v.currentTime);
    },
    [effectiveOriginS, onPlayhead]
  );

  // Expose frame stepping to the page, mirroring the seekRef contract above — the
  // keyboard shortcut must work when the <video> element does not have focus.
  useEffect(() => {
    if (!frameStepRef) return;
    frameStepRef.current = step;
    return () => {
      frameStepRef.current = null;
    };
  }, [frameStepRef, step]);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play().catch(() => {});
    else v.pause();
  }, []);

  // Same idiom as seekRef/frameStepRef above: Space must work when the <video> has no focus,
  // and in fullscreen there is no native control to fall back on. The bar calls `togglePlay`
  // directly rather than going through this ref — the button must work whether or not the page
  // wired one up.
  useEffect(() => {
    if (!playToggleRef) return;
    playToggleRef.current = togglePlay;
    return () => {
      playToggleRef.current = null;
    };
  }, [playToggleRef, togglePlay]);

  // The overlay draws at `originS + currentTime`, so it needs whichever origin is in effect —
  // stored or computed. Reported, never owned: this pane remains the only writer (D9).
  useEffect(() => {
    onOriginChange?.(effectiveOriginS);
  }, [effectiveOriginS, onOriginChange]);

  // Loading a new src resets playbackRate to 1, so setting it once on click would
  // silently revert. Applied here AND in onLoadedMetadata.
  useEffect(() => {
    const v = videoRef.current;
    if (v) v.playbackRate = rate;
  }, [url, rate]);

  // 58-04: persist the computed origin ONCE, and only when nothing was stored. This is what
  // stops a phone-uploaded video from arriving at 0 forever — mobile's VideoOverlayScreen has
  // been the only writer of video_origin_s in the whole system until now.
  // ⚠ Guarded on `savedOrigin == null`, so a stored origin (including a stored 0) is never
  // overwritten. Uses its own ref, never the manual-save path's.
  useEffect(() => {
    if (autoSavedRef.current) return;
    if (savedOrigin != null) return; // already stored — never clobber
    if (endAnchoredOriginS == null || !video?.path) return; // metadata not in yet
    autoSavedRef.current = true;
    (async () => {
      try {
        const fd = new FormData();
        fd.append("video_origin_s", String(endAnchoredOriginS));
        await apiUpload(`/sessions/${sessionId}/video`, fd);
        setSavedOrigin(endAnchoredOriginS);
        onVideoChange?.({ path: video.path, origin_s: endAnchoredOriginS });
      } catch {
        // Non-fatal: playback still works off the computed value; only persistence failed.
        autoSavedRef.current = false;
      }
    })();
  }, [endAnchoredOriginS, savedOrigin, sessionId, video?.path, onVideoChange]);

  // Nudging a COMPUTED origin promotes it to an explicit one — that is the repair path for a
  // bad end-anchor, and it must keep working whether or not the auto-save has run.
  const nudge = (d) => {
    if (effectiveOriginS == null) return;
    const next = Math.round((effectiveOriginS + d) * 100) / 100;
    setOriginS(next);
    const v = videoRef.current;
    if (v) onPlayhead?.(next + v.currentTime);
  };

  // Mute is driven imperatively, not bound as a React prop — binding it would let React fight
  // the native control bar in windowed mode. `onVolumeChange` on the element keeps state honest.
  const toggleMute = () => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
  };

  const saveSync = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("video_origin_s", String(effectiveOriginS));
      await apiUpload(`/sessions/${sessionId}/video`, fd);
      setSavedOrigin(effectiveOriginS);
      setOriginS(effectiveOriginS);
      onVideoChange?.({ path: video.path, origin_s: effectiveOriginS });
      setMsg("Sync saved.");
    } catch (e) {
      setMsg(`Save failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const attach = async (file) => {
    if (!file) return;
    setBusy(true);
    setMsg("Uploading video…");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await apiUpload(`/sessions/${sessionId}/video`, fd);
      setMsg(null);
      onVideoChange?.({
        path: r.video_path,
        // ⚠ was `?? 0` — the same 58-04 defect at a second site. A freshly attached video has
        // no origin, and forcing 0 here would defeat the end-anchor computation entirely.
        origin_s: r.video_origin_s ?? null,
      });
      setOriginS(r.video_origin_s ?? null);
      setSavedOrigin(r.video_origin_s ?? null);
      autoSavedRef.current = false; // a new file needs a fresh end-anchor
    } catch (e) {
      setMsg(`Upload failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  if (!video?.path) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Video
        </p>
        <p className="mb-3 text-xs leading-relaxed text-muted">
          No video attached — annotation works on the velocity trace alone.
          Attach one to review side-by-side.
        </p>
        <label className="inline-block cursor-pointer rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm font-semibold text-subtle hover:text-ink">
          {busy ? "Uploading…" : "Attach video"}
          <input
            type="file"
            accept="video/*"
            className="hidden"
            disabled={busy}
            onChange={(e) => attach(e.target.files?.[0])}
          />
        </label>
        {msg && <p className="mt-2 text-xs text-warning">{msg}</p>}
      </div>
    );
  }

  // Video metadata handlers, shared by both render modes so the <video> element is byte-identical
  // between them (playbackRate restore, end-anchor duration, playhead push, play/mute mirrors).
  const onLoadedMetadata = () => {
    const v = videoRef.current;
    if (!v) return;
    v.playbackRate = rate;
    // The end-anchored origin is unknowable until this fires (58-04).
    if (Number.isFinite(v.duration)) setVideoDurationS(v.duration);
  };
  const onTimeUpdate = () => {
    const v = videoRef.current;
    if (v && effectiveOriginS != null) onPlayhead?.(effectiveOriginS + v.currentTime);
  };

  // PANEL MODE (Phase 64) — a fill-video stage placed inside VideoTracePanel's positioned
  // container, used both inline on the report card and in fullscreen. object-contain never crops
  // (D4). The bottom column stacks the PERMANENT trace (item 1) above the auto-hiding controls.
  if (panel) {
    return (
      <>
        {url ? (
          <video
            ref={setVideoEl}
            src={url}
            playsInline
            className="absolute inset-0 h-full w-full bg-black object-contain"
            onLoadedMetadata={onLoadedMetadata}
            onTimeUpdate={onTimeUpdate}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onVolumeChange={() => setMuted(!!videoRef.current?.muted)}
          />
        ) : (
          <div className="absolute inset-0 grid place-items-center text-xs text-muted">
            Loading video…
          </div>
        )}
        {/* Light scrim, NO blur (2026-08-14): the blurred glass covered too much of the swim, so
            the video now shows through. Legibility comes from the high-saturation trace colour
            (user-chosen) plus a modest bottom gradient that fades to transparent up the frame. */}
        <div className="absolute inset-x-0 bottom-0 z-20 flex flex-col bg-gradient-to-t from-black/80 via-black/40 to-transparent pt-4">
          {overlay}
          <PlaybackControls
            isPlaying={isPlaying}
            onTogglePlay={togglePlay}
            onStep={step}
            rates={RATES}
            rate={rate}
            onRate={setRate}
            muted={muted}
            onToggleMute={toggleMute}
            originS={effectiveOriginS}
            savedOrigin={savedOrigin}
            onNudge={nudge}
            onSave={saveSync}
            busy={busy}
            windowSpanS={windowSpanS}
            onWindowSpanS={onWindowSpanS}
            lineColor={lineColor}
            onLineColor={onLineColor}
            isFullscreen={isFullscreen}
            onToggleFullscreen={onToggleFullscreen}
            dimmed={dimmed}
          />
        </div>
        {msg && (
          <p className="absolute left-4 top-4 z-40 rounded-md bg-black/70 px-2 py-1 text-xs text-ink">
            {msg}
          </p>
        )}
      </>
    );
  }

  // WINDOWED CARD — the pre-64 layout, used by the annotate page. Unchanged in behaviour.
  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Video
      </p>
      {url ? (
        <video
          ref={setVideoEl}
          src={url}
          controls
          playsInline
          // Height scales with the viewport instead of being a fixed cap, clamped so it
          // neither collapses on a short laptop nor eats a tall monitor. object-contain
          // is what letterboxes portrait footage inside that box — without it, it crops.
          className="w-full max-h-[clamp(140px,26vh,420px)] rounded-lg bg-black object-contain"
          onLoadedMetadata={onLoadedMetadata}
          onTimeUpdate={onTimeUpdate}
        />
      ) : (
        <p className="py-6 text-center text-xs text-muted">Loading video…</p>
      )}
      {/* Frame step + playback speed — reading an arm entry needs both */}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <button
          onClick={() => step(-1)}
          className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
          title="Back one frame (← with nothing selected)"
        >
          −1 frame
        </button>
        <button
          onClick={() => step(1)}
          className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
          title="Forward one frame (→ with nothing selected)"
        >
          +1 frame
        </button>
        <span className="ml-1 text-muted">Speed</span>
        {RATES.map((r) => (
          <button
            key={r}
            onClick={() => setRate(r)}
            className={`rounded-md border px-2 py-1 font-semibold ${
              rate === r
                ? "border-accent bg-accent text-white"
                : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
            }`}
          >
            {r}×
          </button>
        ))}
      </div>
      {/* Sync: sessionTime = origin + videoTime */}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted">Sync offset</span>
        <button
          onClick={() => nudge(-0.1)}
          className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
        >
          −0.1s
        </button>
        <span className="w-16 text-center font-mono text-ink">
          {effectiveOriginS != null ? `${effectiveOriginS.toFixed(2)} s` : "—"}
        </span>
        <button
          onClick={() => nudge(0.1)}
          className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
        >
          +0.1s
        </button>
        <button
          onClick={saveSync}
          disabled={busy || effectiveOriginS == null || effectiveOriginS === savedOrigin}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            effectiveOriginS != null && effectiveOriginS !== savedOrigin
              ? "bg-accent text-white"
              : "bg-surface-2 text-muted"
          }`}
        >
          {busy ? "…" : "Save sync"}
        </button>
      </div>
      {/* Which origin is in effect. With two possible sources — stored vs end-anchored — this
          is the only way to tell a saved sync from a computed one when a video looks wrong.
          Mobile added the same line in Phase 60-03 for the same reason. */}
      <p className="mt-2 font-mono text-[10px] text-muted">
        {savedOrigin != null ? "stored" : "computed (end-anchored)"}
        {" · session "}
        {sessionDurationS != null ? `${sessionDurationS.toFixed(1)} s` : "—"}
        {" · video "}
        {videoDurationS != null ? `${videoDurationS.toFixed(1)} s` : "—"}
      </p>
      {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
    </div>
  );
}
