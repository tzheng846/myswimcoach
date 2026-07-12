"use client";

import { PHASE_META, phaseLabel } from "./AnnotationChart";

// Presentational editor panel: tool palette + current marks + save controls.
// All annotation state lives in the page (single source of truth).
export default function AnnotationEditor({
  strokeType,
  activeTool,
  setActiveTool,
  phases,
  strokeMarks,
  onClearPhase,
  onRemoveMark,
  onClearAllMarks,
  dirty,
  saving,
  errors,
  savedMsg,
  onSave,
  onReset,
  seekEnabled,
}) {
  const tools = [
    ...PHASE_META.map((m) => ({
      key: m.key,
      label: phaseLabel(m, strokeType),
      color: m.color,
    })),
    { key: "stroke", label: "+ Stroke mark", color: "#94a3b8" },
    { key: "seek", label: "Seek video", color: "#f59e0b", disabled: !seekEnabled },
  ];

  return (
    <div className="space-y-3">
      {/* Tool palette */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Click tool
        </p>
        <p className="mb-3 text-xs leading-relaxed text-muted">
          Pick a tool, then click the velocity trace to place it.
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
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Phases
        </p>
        <div className="space-y-1.5">
          {PHASE_META.map((m) => (
            <div key={m.key} className="flex items-center gap-2 text-sm">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: m.color }}
              />
              <span className="w-24 text-ink">{phaseLabel(m, strokeType)}</span>
              <span className="flex-1 font-mono text-xs text-subtle">
                {phases[m.key] != null ? `${phases[m.key].toFixed(2)} s` : "—"}
              </span>
              {phases[m.key] != null && (
                <button
                  onClick={() => onClearPhase(m.key)}
                  className="px-1 text-xs text-muted hover:text-danger"
                  title={`Clear ${phaseLabel(m, strokeType)}`}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stroke marks */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <div className="mb-2 flex items-center justify-between">
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

      {/* Save / reset */}
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        {errors.length > 0 && (
          <ul className="mb-3 space-y-1 text-xs text-danger">
            {errors.map((e, i) => (
              <li key={i}>• {e}</li>
            ))}
          </ul>
        )}
        <div className="flex items-center gap-2">
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
            onClick={onReset}
            className="rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm font-semibold text-subtle hover:text-ink"
            title="Restore the auto-segmenter draft"
          >
            Reset to auto
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
      </div>
    </div>
  );
}
