"use client";

import { useEffect, useMemo, useState } from "react";

// Ports the iOS ReportCardScreen TimeToX — splits to a target distance, measured from anchorS
// (dive_start_s — see 88-02 D6/D7). The head-waist offset was retired in computation here: the
// backend path (metrics.time_to_distance) was already dead when this was written, and only this
// component ever applied it. The athlete field, the POST /athletes field and the athletes-page
// editor deliberately remain writable (CONTEXT D7) — do not wire this back to them.
const ALL_PRESETS = [5, 10, 15, 20, 25];
const YARD_TO_M = 0.9144;

function computeTimeToX(timeArr, distArr, anchorS, targetM) {
  if (!timeArr?.length || !distArr?.length || anchorS == null) return null;
  const baseIdx = timeArr.findIndex((t) => t >= anchorS);
  if (baseIdx < 0) return null;
  const distBase = distArr[baseIdx];
  if (targetM <= 0) return null;
  const crossIdx = distArr.findIndex(
    (d, i) => i >= baseIdx && d != null && d >= distBase + targetM
  );
  if (crossIdx < 0) return null;
  return parseFloat((timeArr[crossIdx] - timeArr[baseIdx]).toFixed(2));
}

export default function TimeToX({
  timeArr,
  distArr,
  anchorS,
  onMarkerChange,
  unit = "metric",
}) {
  const imp = unit === "imperial";
  const unitSuffix = imp ? "yd" : "m";

  const { presets, maxReachableM } = useMemo(() => {
    if (!timeArr?.length || !distArr?.length || anchorS == null) {
      return { presets: ALL_PRESETS, maxReachableM: null };
    }
    const baseIdx = timeArr.findIndex((t) => t >= anchorS);
    if (baseIdx < 0) return { presets: ALL_PRESETS, maxReachableM: null };
    const distBase = distArr[baseIdx] ?? 0;
    const distMax = distArr[distArr.length - 1] ?? 0;
    const maxM = Math.max(0, distMax - distBase);
    const maxInUnit = imp ? maxM / YARD_TO_M : maxM;
    const visible = ALL_PRESETS.filter((p) => p <= Math.ceil(maxInUnit) + 1);
    return {
      presets: visible.length > 0 ? visible : ALL_PRESETS,
      maxReachableM: maxM,
    };
  }, [timeArr, distArr, anchorS, imp]);

  const defaultIdx = presets.findIndex((p) => p >= 10);
  const [targetVal, setTargetVal] = useState(
    presets[defaultIdx >= 0 ? defaultIdx : presets.length - 1]
  );

  useEffect(() => {
    if (!presets.includes(targetVal)) setTargetVal(presets[presets.length - 1]);
  }, [presets, targetVal]);

  const targetMeters = imp ? targetVal * YARD_TO_M : targetVal;

  const timeToX = useMemo(
    () => computeTimeToX(timeArr, distArr, anchorS, targetMeters),
    [timeArr, distArr, anchorS, targetMeters]
  );

  const markerAbsoluteTimeS = useMemo(() => {
    if (!timeArr?.length || !distArr?.length || anchorS == null) return null;
    const baseIdx = timeArr.findIndex((t) => t >= anchorS);
    if (baseIdx < 0) return null;
    const distBase = distArr[baseIdx];
    if (targetMeters <= 0) return null;
    const crossIdx = distArr.findIndex(
      (d, i) => i >= baseIdx && d != null && d >= distBase + targetMeters
    );
    if (crossIdx < 0) return null;
    return timeArr[crossIdx];
  }, [timeArr, distArr, anchorS, targetMeters]);

  useEffect(() => {
    onMarkerChange?.(markerAbsoluteTimeS, `${targetVal}${unitSuffix}`);
  }, [markerAbsoluteTimeS, targetVal, unitSuffix, onMarkerChange]);

  const maxDisplay =
    maxReachableM != null
      ? imp
        ? `${(maxReachableM / YARD_TO_M).toFixed(1)} yd`
        : `${maxReachableM.toFixed(1)} m`
      : null;

  return (
    <div className="flex flex-col items-center">
      <p className="font-mono text-4xl font-bold text-ink">
        {timeToX != null ? `${timeToX} s` : "--"}
      </p>
      <p className="mt-1 text-sm text-muted">
        to {targetVal} {unitSuffix}
      </p>
      {maxDisplay != null && (
        <p className="mt-1 text-[11px] text-muted">Max from start: {maxDisplay}</p>
      )}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {presets.map((p) => (
          <button
            key={p}
            onClick={() => setTargetVal(p)}
            className={`rounded-lg border px-3.5 py-2 text-sm font-semibold transition-colors ${
              targetVal === p
                ? "border-accent bg-accent text-white"
                : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
            }`}
          >
            {p}
            {unitSuffix}
          </button>
        ))}
      </div>
    </div>
  );
}
