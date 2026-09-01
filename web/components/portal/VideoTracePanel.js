"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import VideoPane from "@/components/portal/VideoPane";
import TraceOverlay from "@/components/portal/TraceOverlay";

// Phase 64 — the embeddable "video with velocity laid over it" unit.
//
// Lives INLINE on the report card (right above VelocityChart) and expands to FULLSCREEN from a
// button on itself. One component, two sizes: the only differences are the stage's height and
// whether the control bar auto-hides. Owns fullscreen state, the rolling-window preset, and the
// control auto-hide timer; composes VideoPane (the video + sync engine) with TraceOverlay (the
// permanent trace), handing the overlay to VideoPane as a prop so VideoPane keeps sole ownership
// of the playback handlers the bar calls — no duplicated origin logic (58-04 / D9).
//
// ⚠ The stage div IS the fullscreen target: it must be an ancestor of the <video>, and the
// <video> must never move in the DOM or playback position and the signed URL are lost (D1).

const IDLE_MS = 2000;

export default function VideoTracePanel({
  sessionId,
  velocity = [],
  acceleration = [], // Phase 64-03 — signed acceleration series (sessions.acceleration_profile)
  fsHz = 100,
  cycles = [],
  sessionDurationS = null,
  video, // {path, origin_s} | null — controlled by the page
  onVideoChange, // ({path, origin_s}) => void
  onPlayhead, // optional (sessionTimeS | null) => void — moves the page's VelocityChart marker
  seekRef: externalSeekRef, // optional ref; if given, the page can also seek (e.g. a static chart)
  // Phase 64-03 — trace visibility + colours are OWNED BY THE PAGE (so the overlay and the static
  // charts stay in sync) and passed down; only the rolling-window span stays local to the panel.
  showVelocity = true,
  showAcceleration = false,
  velColor = "#ff453a",
  accelColor = "#22d3ee",
  onToggleVelocity, // (bool) => void
  onToggleAcceleration, // (bool) => void
  onVelColor, // (hex) => void
  onAccelColor, // (hex) => void
  // Display units (2026-09-01) — forwarded untouched to TraceOverlay's readouts. The panel itself
  // shows no numbers, so it neither converts nor labels anything.
  unitFactor = 1,
  velUnit = "m/s",
  accelUnit = "m/s²",
  readOnly = false, // watch-only (report card): video + trace + playback, but no manual sync controls
}) {
  const stageRef = useRef(null);
  const videoElRef = useRef(null);
  const playToggleRef = useRef(null);
  const frameStepRef = useRef(null);
  const internalSeekRef = useRef(null);
  const seekRef = externalSeekRef || internalSeekRef;

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [canFullscreen, setCanFullscreen] = useState(false);
  const [idle, setIdle] = useState(false);
  const [windowSpanS, setWindowSpanS] = useState(null); // null = whole swim (All), the default
  const [overlayOriginS, setOverlayOriginS] = useState(null);

  const hasVideo = !!(video?.url || video?.path);

  // Trace colour + visibility are now page-owned (persisted via useTracePrefs) so both the overlay
  // and the static charts move together — this panel no longer holds that state.

  // Track fullscreen from the EVENT, not the click handler — Esc and browser chrome change it too.
  useEffect(() => {
    const onChange = () =>
      setIsFullscreen(document.fullscreenElement === stageRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  // AC-8: iOS Safari only fullscreens the <video> element itself, so a stage-level request is
  // unavailable there. Detect once video is present (the stage only renders then).
  useEffect(() => {
    setCanFullscreen(
      typeof stageRef.current?.requestFullscreen === "function" &&
        !!document.fullscreenEnabled
    );
  }, [hasVideo]);

  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    else stageRef.current?.requestFullscreen?.().catch(() => {});
  }, []);

  const onOverlaySeek = useCallback(
    (t) => {
      seekRef.current?.(t);
    },
    [seekRef]
  );

  // Auto-hide the CONTROL BAR after ~2 s idle in fullscreen (item 1: the trace never hides).
  useEffect(() => {
    if (!isFullscreen) return undefined;
    let t = setTimeout(() => setIdle(true), IDLE_MS);
    const wake = () => {
      setIdle(false);
      clearTimeout(t);
      t = setTimeout(() => setIdle(true), IDLE_MS);
    };
    document.addEventListener("mousemove", wake);
    document.addEventListener("keydown", wake);
    return () => {
      clearTimeout(t);
      document.removeEventListener("mousemove", wake);
      document.removeEventListener("keydown", wake);
      setIdle(false); // reset on the way OUT — a body setState here would cascade-render
    };
  }, [isFullscreen]);

  // Keyboard while fullscreen. Escape is the browser's own exit — deliberately not intercepted.
  useEffect(() => {
    if (!isFullscreen) return undefined;
    const onKey = (e) => {
      if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        playToggleRef.current?.();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        frameStepRef.current?.(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        frameStepRef.current?.(1);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isFullscreen]);

  // No video → the slim attach card (VideoPane's own no-video branch). No stage, no empty box.
  if (!hasVideo) {
    return (
      <VideoPane
        sessionId={sessionId}
        video={video}
        onVideoChange={onVideoChange}
        sessionDurationS={sessionDurationS}
      />
    );
  }

  return (
    <div
      ref={stageRef}
      className={
        isFullscreen
          ? "relative h-full w-full bg-black"
          : "relative w-full overflow-hidden rounded-xl border border-navy/50 bg-black h-[clamp(360px,60vh,720px)]"
      }
    >
      <VideoPane
        sessionId={sessionId}
        video={video}
        onVideoChange={onVideoChange}
        sessionDurationS={sessionDurationS}
        onPlayhead={onPlayhead}
        seekRef={seekRef}
        frameStepRef={frameStepRef}
        playToggleRef={playToggleRef}
        videoElRef={videoElRef}
        onOriginChange={setOverlayOriginS}
        panel
        readOnly={readOnly}
        isFullscreen={isFullscreen}
        onToggleFullscreen={canFullscreen ? toggleFullscreen : undefined}
        windowSpanS={windowSpanS}
        onWindowSpanS={setWindowSpanS}
        lineColor={velColor}
        onLineColor={onVelColor}
        showVelocity={showVelocity}
        showAcceleration={showAcceleration}
        onToggleVelocity={onToggleVelocity}
        onToggleAcceleration={onToggleAcceleration}
        accelColor={accelColor}
        onAccelColor={onAccelColor}
        dimmed={isFullscreen && idle}
        overlay={
          <TraceOverlay
            velocity={velocity}
            acceleration={acceleration}
            fsHz={fsHz}
            cycles={cycles}
            videoElRef={videoElRef}
            originS={overlayOriginS}
            onSeek={onOverlaySeek}
            windowS={windowSpanS}
            lineColor={velColor}
            accelColor={accelColor}
            showVelocity={showVelocity}
            showAcceleration={showAcceleration}
            unitFactor={unitFactor}
            velUnit={velUnit}
            accelUnit={accelUnit}
          />
        }
      />
    </div>
  );
}
