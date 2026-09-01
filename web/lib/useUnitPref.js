"use client";

import { useCallback, useEffect, useState } from "react";
import { M_TO_YD } from "@/lib/unitConvert";

// The standing metric/imperial preference, lifted out of sessions/[id]/page.js so the /video route
// reads the SAME choice (2026-09-01). Before this, `swimnetics.unit` was hydrated only on the
// report card: flipping to yards there left the video overlay's readout — and every chart on
// /video — still printing m/s, which looked like the toggle was broken.
//
// ⚠ Read in an effect, NEVER a lazy initializer: localStorage is absent during SSR and reading it
// in render desyncs hydration. Same rule useTracePrefs follows.

const KEY = "swimnetics.unit";

export default function useUnitPref() {
  const [unit, setUnitState] = useState("metric");

  useEffect(() => {
    try {
      const u = window.localStorage.getItem(KEY);
      if (u === "metric" || u === "imperial") setUnitState(u);
    } catch {
      // Private mode / storage disabled — the default is fine.
    }
  }, []);

  const setUnit = useCallback((u) => {
    setUnitState(u);
    try {
      window.localStorage.setItem(KEY, u);
    } catch {
      // Non-fatal: the toggle still works for this page view.
    }
  }, []);

  const imperial = unit === "imperial";
  return {
    unit,
    setUnit,
    unitFactor: imperial ? M_TO_YD : 1,
    velUnit: imperial ? "yd/s" : "m/s",
    accelUnit: imperial ? "yd/s²" : "m/s²",
  };
}
