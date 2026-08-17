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
};

export const DEFAULT_VEL_COLOR = "#ff453a"; // red — a blue line on blue water is invisible
export const DEFAULT_ACCEL_COLOR = "#22d3ee"; // cyan — distinct from velocity's red

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

  useEffect(() => {
    try {
      const sv = window.localStorage.getItem(KEYS.showVelocity);
      const sa = window.localStorage.getItem(KEYS.showAcceleration);
      const vc = window.localStorage.getItem(KEYS.velColor);
      const ac = window.localStorage.getItem(KEYS.accelColor);
      if (sv === "0" || sv === "1") setShowVelocity(sv === "1");
      if (sa === "0" || sa === "1") setShowAcceleration(sa === "1");
      if (vc) setVelColor(vc);
      if (ac) setAccelColor(ac);
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

  return {
    showVelocity,
    showAcceleration,
    velColor,
    accelColor,
    setShowVelocity: chooseShowVelocity,
    setShowAcceleration: chooseShowAcceleration,
    setVelColor: chooseVelColor,
    setAccelColor: chooseAccelColor,
  };
}
