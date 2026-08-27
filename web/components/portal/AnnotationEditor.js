"use client";

import { useState } from "react";
import { PHASE_META, phaseLabel } from "./AnnotationChart";

// Mirror of annotations.annotation_to_overrides so the readout tells the truth about
// what the server will actually build. Boundaries are every k-th mark; finish_s closes
// the last cycle ONLY at k === 1 (at k > 1 a boundary is a same-side arm entry and the
// wall touch is not one). Indices, the strictly-increasing filter and the >= 2-sample
// span filter all replicate the Python. If this drifts, the panel starts lying.
function deriveCycles(marks, finishS, k, fsHz) {
  const sorted = [...marks].sort((a, b) => a - b);
  const boundaries = sorted.filter((_, i) => i % k === 0);
  if (
    k === 1 &&
    finishS != null &&
    (boundaries.length === 0 || finishS > boundaries[boundaries.length - 1])
  ) {
    boundaries.push(finishS);
  }
  const idxs = [];
  for (const b of boundaries) {
    const i = Math.round(b * fsHz);
    if (!idxs.length || i > idxs[idxs.length - 1]) idxs.push(i);
  }
  let cycles = 0;
  for (let i = 0; i < idxs.length - 1; i++) {
    if (idxs[i + 1] - idxs[i] >= 2) cycles++;
  }
  // Arm entries past the last boundary open nothing — a real outcome, but silence
  // would read as a lost mark.
  const lastBoundaryIdx = boundaries.length
    ? (Math.ceil(sorted.length / k) - 1) * k
    : -1;
  const unpaired = Math.max(0, sorted.length - 1 - lastBoundaryIdx);
  return { cycles, unpaired };
}

const CONVENTION = {
  2: "1 mark = 1 arm entry · 2 entries per cycle (arms alternate)",
  1: "1 mark = 1 cycle (both arms move together)",
};

// Presentational editor panel: tool palette + current marks + save controls.
// All annotation state lives in the page (single source of truth).
export default function AnnotationEditor({
  strokeType,
  activeTool,
  setActiveTool,
  phases,
  strokeMarks,
  marksPerCycle = 1,
  fsHz = 100,
  onClearPhase,
  onRemoveMark,
  onClearAllMarks,
  onUndo,
  canUndo,
  onDiscard,
  hasSaved,
  dirty,
  saving,
  errors,
  savedMsg,
  hint,
  viewMode,
  setViewMode,
  fitAvailable,
  onSave,
  seekEnabled,
}) {
  const [confirmDiscard, setConfirmDiscard] = useState(false);

  // Number-key each play-and-tap boundary drops (81-01), keyed by phase key — NOT position — so
  // finish_s (no key) and the future key-3 kick marker never shift the 4/5 assignment.
  const DIGIT_BY_KEY = {
    dive_start_s: "1",
    underwater_start_s: "2",
    stroke_start_s: "4",
  };

  const tools = [
    ...PHASE_META.map((m) => ({
      key: m.key,
      label: DIGIT_BY_KEY[m.key]
        ? `${DIGIT_BY_KEY[m.key]} ${phaseLabel(m, strokeType)}`
        : phaseLabel(m, strokeType),
      color: m.color,
    })),
    { key: "stroke", label: "5 Stroke mark", color: "#94a3b8" },
    { key: "seek", label: "Seek video", color: "#f59e0b", disabled: !seekEnabled },
  ];

  // Each marker opens a phase and closes the previous one — so spans tile the swim.
  const placed = PHASE_META.filter((m) => phases[m.key] != null);
  const closerOf = (key) => {
    const i = placed.findIndex((m) => m.key === key);
    return i >= 0 && i < placed.length - 1 ? placed[i + 1] : null;
  };

  const { cycles, unpaired } = deriveCycles(
    strokeMarks,
    phases.finish_s,
    marksPerCycle,
    fsHz
  );

  return (
    <div className="space-y-3">
      {/* View */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
          View
        </p>
        <div className="flex gap-1.5">
          {[
            { k: "fit", label: "Fit to swim" },
            { k: "full", label: "Full trace" },
          ].map((v) => (
            <button
              key={v.k}
              onClick={() => setViewMode(v.k)}
              disabled={v.k === "fit" && !fitAvailable}
              className={`rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
                viewMode === v.k
                  ? "border-accent bg-accent text-white"
                  : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
              } ${v.k === "fit" && !fitAvailable ? "opacity-40" : ""}`}
            >
              {v.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-muted">
          {fitAvailable
            ? "Fit hides the dead time after Finish. The start is always kept — that region is the reaction time."
            : "Mark Finish to trim the dead time after the swim."}
        </p>
      </div>

      {/* Tool palette */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Click tool
        </p>
        <p className="mb-2 text-xs leading-relaxed text-muted">
          Pick a tool, then click the trace to place it. Drag an existing mark to move
          it; click one to select, then ←/→ to nudge (shift = ×10).
        </p>
        {/* The arrows are modal — say so, or the mode switch reads as a bug. */}
        <p className="mb-3 text-[11px] leading-relaxed text-muted">
          <span className="text-subtle">Keys:</span> with nothing selected ←/→ step the
          video one frame (shift = ×10); with a mark selected they nudge it instead, and{" "}
          <span className="text-subtle">Esc</span> deselects.{" "}
          <span className="text-subtle">1 / 2 / 4</span> place or move Dive / UW / Stroke at
          the video playhead; <span className="text-subtle">5</span> (or{" "}
          <span className="text-subtle">M</span>) drops a stroke mark.{" "}
          <span className="text-subtle">Ctrl+Z</span> undoes.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {tools.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTool(t.key)}
              disabled={t.disabled}
              className={`rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
                activeTool === t.key
                  ? "border-accent bg-accent text-white"
                  : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
              } ${t.disabled ? "opacity-40" : ""}`}
            >
              <span
                className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle"
                style={{ background: t.color }}
              />
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Phase boundaries */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Phases
        </p>
        <p className="mb-3 text-[11px] leading-relaxed text-muted">
          Each time is where that phase <span className="text-ink">starts</span> — and
          where the previous one ends. The phases tile the swim in order, so they can
          never overlap.
        </p>
        <div className="space-y-2">
          {PHASE_META.map((m) => {
            const t = phases[m.key];
            const closer = closerOf(m.key);
            const end = closer ? phases[closer.key] : null;
            return (
              <div key={m.key} className="text-sm">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ background: m.color }}
                  />
                  <span className="w-24 text-ink">{phaseLabel(m, strokeType)}</span>
                  <span className="flex-1 font-mono text-xs text-subtle">
                    {t != null ? `starts ${t.toFixed(2)} s` : (
                      <span className="not-italic text-muted">not marked</span>
                    )}
                  </span>
                  {!m.drivesMetrics && (
                    <span
                      className="rounded border border-surface-3 px-1 text-[9px] uppercase tracking-wide text-muted"
                      title="Recorded for the segmenter-tuning export. Does not change any metric."
                    >
                      record only
                    </span>
                  )}
                  {t != null && (
                    <button
                      onClick={() => onClearPhase(m.key)}
                      className="px-1 text-xs text-muted hover:text-danger"
                      title={`Clear ${phaseLabel(m, strokeType)}`}
                    >
                      ✕
                    </button>
                  )}
                </div>
                {t != null && (
                  <p className="ml-[18px] mt-0.5 font-mono text-[10px] text-muted">
                    {end != null
                      ? `→ ${phaseLabel(closer, strokeType)} at ${end.toFixed(2)} s · ${(
                          end - t
                        ).toFixed(2)} s`
                      : m.key === "finish_s"
                      ? "→ end of swim (everything after is excluded)"
                      : "→ open (no later phase marked)"}
                  </p>
                )}
                {m.key === "dive_start_s" && t != null && (
                  <p className="ml-[18px] mt-1 text-[10px] leading-relaxed text-warning/80">
                    Lower bound on reaction time. t=0 is the start blare, but the first
                    recorded sample lags it by an unmeasured 170–400 ms (BLE write +
                    encoder warmup). Not a calibrated measurement.
                  </p>
                )}
                {m.key === "underwater_start_s" && t != null && (
                  <p className="ml-[18px] mt-1 text-[10px] leading-relaxed text-muted">
                    This span runs <span className="text-subtle">through the breakout</span> —
                    there is no separate Breakout marker. Recorded for the tuning export;
                    moves no metric.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Stroke marks */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <div className="mb-1 flex items-center justify-between">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">
            Stroke marks ({strokeMarks.length})
          </p>
          {strokeMarks.length > 0 && (
            <button
              onClick={onClearAllMarks}
              className="text-xs text-muted hover:text-danger"
            >
              Clear all
            </button>
          )}
        </div>
        <p className="text-sm text-ink">
          {strokeMarks.length} mark{strokeMarks.length === 1 ? "" : "s"} →{" "}
          <span className="font-semibold">{cycles} cycle{cycles === 1 ? "" : "s"}</span>
        </p>
        <p className="mt-0.5 text-[11px] leading-relaxed text-muted">
          {CONVENTION[marksPerCycle] ?? CONVENTION[1]}
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-muted">
          The <span className="text-subtle">first cycle contains the breakout</span> and is
          expected to be atypical. Mark it anyway — it is recorded as-is, and no metric
          excludes it.
        </p>
        {unpaired > 0 && (
          <p className="mt-1 text-[11px] text-warning/80">
            Last arm entry is unpaired — it completes no cycle. Kept as ground truth.
          </p>
        )}
        <div className="mt-3">
          {strokeMarks.length === 0 ? (
            <p className="text-xs text-muted">
              No marks — use the "+ Stroke mark" tool.
            </p>
          ) : (
            <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
              {strokeMarks.map((t, i) => (
                <span
                  key={`${t}-${i}`}
                  className="inline-flex items-center gap-1 rounded-md border border-surface-3 bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-subtle"
                >
                  {t.toFixed(2)}s
                  <button
                    onClick={() => onRemoveMark(i)}
                    className="text-muted hover:text-danger"
                    title="Remove mark"
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Save / undo / discard */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        {errors.length > 0 && (
          <ul className="mb-3 space-y-1 text-xs text-danger">
            {errors.map((e, i) => (
              <li key={i}>• {e}</li>
            ))}
          </ul>
        )}
        {hint && <p className="mb-3 text-xs text-warning">{hint}</p>}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={onSave}
            disabled={saving || !dirty}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
              dirty
                ? "bg-accent text-white hover:opacity-90"
                : "bg-surface-2 text-muted"
            }`}
          >
            {saving ? "Saving…" : dirty ? "Save" : "Saved"}
          </button>
          <button
            onClick={onUndo}
            disabled={!canUndo}
            className={`rounded-lg border border-surface-3 px-3 py-2 text-sm font-semibold transition-colors ${
              canUndo
                ? "bg-surface-2 text-subtle hover:text-ink"
                : "bg-surface-2 text-muted opacity-40"
            }`}
            title="Undo the last placement, move or deletion (Ctrl+Z)"
          >
            Undo
          </button>
          {dirty && (
            <span className="text-xs text-warning" title="Unsaved changes">
              ● unsaved
            </span>
          )}
          {!dirty && savedMsg && (
            <span className="text-xs text-muted">{savedMsg}</span>
          )}
        </div>
        {hasSaved && (
          <div className="mt-3 border-t border-surface-3 pt-3">
            {confirmDiscard ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-danger">
                  Delete the saved annotation and restore auto metrics?
                </span>
                <button
                  onClick={() => {
                    setConfirmDiscard(false);
                    onDiscard();
                  }}
                  className="rounded-md bg-danger px-2 py-1 text-xs font-semibold text-white"
                >
                  Discard
                </button>
                <button
                  onClick={() => setConfirmDiscard(false)}
                  className="text-xs text-muted hover:text-ink"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDiscard(true)}
                className="text-xs text-muted hover:text-danger"
              >
                Discard saved annotation
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
