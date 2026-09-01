"use client";

import { useCallback, useEffect, useState } from "react";

// Standing display preferences for the velocity/acceleration traces (Phase 64-03). Owned at the
// PAGE level and shared by the report card and the /video route, so a toggle or colour set on one
// surface carries to the other and both stay in step (AC-2, AC-4).
//
// ⚠ Read in an effect, NEVER a lazy initializer: localStorage is absent during SSR and reading it
// in render desyncs hydration. Same rule the report card's view/unit prefs already follow.

const KEYS = {
  showVelocity: "swimnetics.showVelocity",
  showAcceleration: "swimnetics.showAcceleration",
  // Pre-existing key — carry the user's already-chosen trace colour over unchanged (was owned by
  // VideoTracePanel before ownership lifted to the page).
  velColor: "swimnetics.traceColor",
  accelColor: "swimnetics.accelColor",
  // Phase 88-05: the velocity trend overlay's averaging window, in seconds. Lives here rather
  // than in the page so it carries across sessions and reloads (AC-4).
  smoothWindowS: "swimnetics.smoothWindowS",
  // 2026-09-01: the trend line's on/off switch, separate from its window. Dragging the slider to
  // 0.00 s still turns it off, but that DISCARDS the window the coach picked — a switch has to be
  // able to come back on at 1.40 s, not at the default.
  showTrend: "swimnetics.showTrend",
};

export const DEFAULT_VEL_COLOR = "#ff453a"; // red — a blue line on blue water is invisible
export const DEFAULT_ACCEL_COLOR = "#22d3ee"; // cyan — distinct from velocity's red
export const DEFAULT_SMOOTH_WINDOW_S = 1.0; // 88-05 D2 — default-on; 0 is a reachable "off"
export const MAX_SMOOTH_WINDOW_S = 3.0;
export const DEFAULT_SHOW_TREND = true; // unchanged behaviour for anyone who never touches it

// Module-level so it needs no dependency in the callbacks below.
function persist(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // storage disabled — non-fatal, the toggle still works for this view
  }
}

export default function useTracePrefs() {
  const [showVelocity, setShowVelocity] = useState(true); // default velocity-only (AC-2)
  const [showAcceleration, setShowAcceleration] = useState(false);
  const [velColor, setVelColor] = useState(DEFAULT_VEL_COLOR);
  const [accelColor, setAccelColor] = useState(DEFAULT_ACCEL_COLOR);
  const [smoothWindowS, setSmoothWindowS] = useState(DEFAULT_SMOOTH_WINDOW_S);
  const [showTrend, setShowTrend] = useState(DEFAULT_SHOW_TREND);

  useEffect(() => {
    try {
      const sv = window.localStorage.getItem(KEYS.showVelocity);
      const sa = window.localStorage.getItem(KEYS.showAcceleration);
      const vc = window.localStorage.getItem(KEYS.velColor);
      const ac = window.localStorage.getItem(KEYS.accelColor);
      const sw = Number.parseFloat(window.localStorage.getItem(KEYS.smoothWindowS));
      const st = window.localStorage.getItem(KEYS.showTrend);
      if (sv === "0" || sv === "1") setShowVelocity(sv === "1");
      if (sa === "0" || sa === "1") setShowAcceleration(sa === "1");
      if (vc) setVelColor(vc);
      if (ac) setAccelColor(ac);
      // Anything out of range or unparseable leaves the default in place (AC-4).
      if (Number.isFinite(sw) && sw >= 0 && sw <= MAX_SMOOTH_WINDOW_S) setSmoothWindowS(sw);
      if (st === "0" || st === "1") setShowTrend(st === "1");
    } catch {
      // private mode / storage disabled — defaults are fine
    }
  }, []);

  const chooseShowVelocity = useCallback((b) => {
    setShowVelocity(b);
    persist(KEYS.showVelocity, b ? "1" : "0");
  }, []);
  const chooseShowAcceleration = useCallback((b) => {
    setShowAcceleration(b);
    persist(KEYS.showAcceleration, b ? "1" : "0");
  }, []);
  const chooseVelColor = useCallback((c) => {
    setVelColor(c);
    persist(KEYS.velColor, c);
  }, []);
  const chooseAccelColor = useCallback((c) => {
    setAccelColor(c);
    persist(KEYS.accelColor, c);
  }, []);
  const chooseShowTrend = useCallback((b) => {
    setShowTrend(b);
    persist(KEYS.showTrend, b ? "1" : "0");
  }, []);
  const chooseSmoothWindowS = useCallback((s) => {
    setSmoothWindowS(s);
    persist(KEYS.smoothWindowS, String(s));
  }, []);

  return {
    showVelocity,
    showAcceleration,
    velColor,
    accelColor,
    smoothWindowS,
    showTrend,
    setShowVelocity: chooseShowVelocity,
    setShowAcceleration: chooseShowAcceleration,
    setVelColor: chooseVelColor,
    setAccelColor: chooseAccelColor,
    setSmoothWindowS: chooseSmoothWindowS,
    setShowTrend: chooseShowTrend,
  };
}
