"use client";

import { useEffect, useMemo, useState } from "react";
import { buildBins, measureWindow, toggleBin } from "@/lib/splitWindow";

// Segment splits (Phase 88-04) — reported defect 1: the coach could only read the five fixed 5 m
// grid rows, never 0–10 or 5–15. This card offers one chip per COMPLETE 5 m (5 yd in imperial)
// segment; clicking selects a contiguous run and reads back that window's average velocity and
// elapsed time.
//
// What it is AGAINST the Swimming grid's split rows: those are fixed bins carrying usual-range
// history and a flag. This is an ad-hoc window for THIS swim only — no baseline, no band, no
// flag, no dismiss (CONTEXT D4 declined all of it deliberately, in exchange for being small and
// instant). A single-chip selection reproduces the matching grid row exactly (splitWindow D4).
//
// D1 — it does NOT use `onMarkerChange`. It gets its own `spanS` prop on the two charts. Two cards
// writing one marker is a live conflict (TimeToX's marker effect re-fired on every dependency
// change and would have stomped this one), and a *window* is not a *point*.
// ⚠ That conflict is now historical: the user removed the Time-to-Distance card at the 88-04
// verify as redundant against this one. `spanS` stays a separate prop from `markerTimeS` anyway —
// the window/point distinction is the durable half of D1, and TimeToX.js survives as dead code.
export default function SplitPicker({
  timeArr,
  distArr,
  anchorS,
  finishS,
  fsHz = 100,
  unit = "metric",
  onSpanChange,
}) {
  const imp = unit === "imperial";
  const unitSuffix = imp ? "yd" : "m";
  const velSuffix = imp ? "yd/s" : "m/s";

  const bins = useMemo(
    () =>
      buildBins({
        dist: distArr,
        time: timeArr,
        anchorS,
        finishS,
        fsHz,
        imperial: imp,
      }),
    [distArr, timeArr, anchorS, finishS, fsHz, imp]
  );

  // D3 — no default selection, so the shared velocity chart is unshaded on page load for every
  // coach who never touches this card.
  const [rawSel, setSel] = useState(null);

  // The bin grid changes width when the unit toggles, so a stored {lo, hi} can outlive the bins it
  // indexed. Clamped by DERIVING it during render rather than resetting it in an effect: there is
  // then no frame in which the chips are lit against a selection the readout has already dropped,
  // and no react-hooks/set-state-in-effect.
  const sel = rawSel && rawSel.hi < bins.length ? rawSel : null;

  const win = useMemo(
    () => measureWindow(bins, sel, distArr, timeArr),
    [bins, sel, distArr, timeArr]
  );

  const label = win ? `${win.fromU}–${win.toU} ${unitSuffix}` : "";

  useEffect(() => {
    onSpanChange?.(win ? [timeArr[win.i0], timeArr[win.i1]] : null, label);
  }, [win, label, timeArr, onSpanChange]);

  if (bins.length === 0) {
    return (
      <p className="text-sm text-muted">
        Not enough distance recorded to measure segments.
      </p>
    );
  }

  return (
    <div className="flex flex-col items-center">
      {win && win.avgVelMs != null ? (
        <>
          <p className="font-mono text-4xl font-bold text-ink">
            {(win.avgVelMs * (imp ? 1.09361 : 1)).toFixed(2)} {velSuffix}
          </p>
          <p className="mt-1 text-sm text-muted">
            {label} · {win.elapsedS.toFixed(2)} s
          </p>
        </>
      ) : (
        <p className="mt-1 text-sm text-muted">Tap segments to measure a window.</p>
      )}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {bins.map((b) => {
          const on = sel != null && b.k >= sel.lo && b.k <= sel.hi;
          return (
            <button
              key={b.k}
              onClick={() => setSel(toggleBin(sel, b.k))}
              className={`rounded-lg border px-3.5 py-2 text-sm font-semibold transition-colors ${
                on
                  ? "border-accent bg-accent text-white"
                  : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
              }`}
            >
              {b.fromU}–{b.toU}
              {unitSuffix}
            </button>
          );
        })}
      </div>
      {/* D6 — bins are unit-native, so in yards these windows and the metre-binned split rows in
          the grid below are legitimately DIFFERENT windows. A coach who cannot see the
          disagreement cannot reason about it. */}
      {imp && (
        <p className="mt-3 text-[11px] text-muted">
          Segments here are yards; the split rows below stay metre-binned.
        </p>
      )}
    </div>
  );
}
