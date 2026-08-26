"use client";

// RangeStrip — one metric row in the race-phase report card (Phase 75-05): a dotted label that
// opens the hover-explain overlay, a 1D usual-range strip (faint 0-based scale, shaded usual band,
// median tick, today dot), and the value + status on the right. Ported 1:1 from the v3 concept
// mockup. Three states: full (band known), baseline-building (n<2, no band → today dot only), and
// not-measured (value null this swim → a pill, never a fake zero strip).

import { ExplainTrigger } from "./HoverExplain";
import { statusWord } from "@/lib/phaseValence";

function pct(x, domain) {
  const [lo, hi] = domain;
  if (!(hi > lo)) return 0;
  return Math.max(0, Math.min(100, ((x - lo) / (hi - lo)) * 100));
}

function fmt(v) {
  if (v == null || !Number.isFinite(v)) return "—";
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}

function valenceText(valence) {
  return valence === "good"
    ? "text-good"
    : valence === "bad"
      ? "text-bad"
      : valence === "neutral"
        ? "text-neutral"
        : "text-muted";
}

function valenceDot(valence) {
  return valence === "good"
    ? "bg-good"
    : valence === "bad"
      ? "bg-bad"
      : valence === "neutral"
        ? "bg-neutral"
        : "bg-subtle";
}

export default function RangeStrip({
  label,
  unit = "",
  value,
  baseline, // { median, band, n } | undefined
  domain,
  verdict, // { flagged, direction, valence }
  dismissed = false,
  onDismiss,
  onRestore,
  explain, // { title, tag, body } for the label hover
  emptyNote = "not measured this swim",
}) {
  const unitEl = unit ? <span className="text-[10.5px] font-normal text-muted"> {unit}</span> : null;

  const labelEl = explain ? (
    <ExplainTrigger
      title={explain.title}
      tag={explain.tag}
      body={explain.body}
      className="cursor-help border-b border-dotted border-muted text-[12.5px] leading-tight text-ink outline-none focus-visible:border-solid focus-visible:border-accent"
    >
      {label}
      <span className="ml-0.5 align-super text-[9px] text-muted">ⓘ</span>
    </ExplainTrigger>
  ) : (
    <span className="text-[12.5px] leading-tight text-ink">{label}</span>
  );

  // ── not measured this swim ────────────────────────────────────────────────
  if (value == null || !Number.isFinite(value)) {
    return (
      <div className="grid grid-cols-[minmax(104px,1.15fr)_minmax(88px,1.35fr)_auto] items-center gap-3 border-b border-navy/25 px-1.5 py-2 opacity-70">
        <div className="min-w-0">{labelEl}</div>
        <div className="flex items-center">
          <span className="rounded-full border border-dashed border-usual px-2 py-0.5 text-[10px] text-muted">
            {emptyNote}
          </span>
        </div>
        <div className="text-right text-[13px] text-muted">—</div>
      </div>
    );
  }

  const band = baseline?.band ?? null;
  const median = baseline?.median ?? null;
  const n = baseline?.n ?? 0;
  const flagged = !!verdict?.flagged && !dismissed;
  const valence = flagged ? verdict.valence : null;

  // ── baseline building (n < 2, no band) ────────────────────────────────────
  if (!band) {
    return (
      <div className="grid grid-cols-[minmax(104px,1.15fr)_minmax(88px,1.35fr)_auto] items-center gap-3 border-b border-navy/25 px-1.5 py-2">
        <div className="min-w-0">{labelEl}</div>
        <div className="relative h-5">
          <div className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 rounded bg-white/10" />
          <div
            className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-subtle"
            style={{ left: `${pct(value, domain)}%`, boxShadow: "0 0 0 2px var(--color-surface)" }}
          />
        </div>
        <div className="whitespace-nowrap text-right">
          <div className="font-mono text-[13px] font-medium text-ink">
            {fmt(value)}
            {unitEl}
          </div>
          <div className="mt-0.5 text-[11px] text-muted">baseline building ({n}/5)</div>
        </div>
      </div>
    );
  }

  // ── full strip ────────────────────────────────────────────────────────────
  const L = pct(band[0], domain);
  const R = pct(band[1], domain);
  const rowTint = flagged
    ? valence === "bad"
      ? "bg-bad/5"
      : valence === "good"
        ? "bg-good/5"
        : ""
    : "";

  return (
    <div
      className={`grid grid-cols-[minmax(104px,1.15fr)_minmax(88px,1.35fr)_auto] items-center gap-3 rounded-md border-b border-navy/25 px-1.5 py-2 ${rowTint} ${dismissed ? "opacity-55" : ""}`}
    >
      <div className="min-w-0">{labelEl}</div>

      {/* 1D strip: faint 0-based scale, shaded usual band, median tick, today dot */}
      <div className="relative h-5 overflow-visible">
        <div className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 rounded bg-white/10" />
        <div
          className="absolute top-1/2 h-2 -translate-y-1/2 rounded-[5px] bg-usual/60"
          style={{ left: `${L}%`, width: `${Math.max(0, R - L)}%` }}
        />
        {median != null && (
          <div
            className="absolute top-1/2 h-3 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded bg-ink/40"
            style={{ left: `${pct(median, domain)}%` }}
          />
        )}
        <div
          className={`absolute top-1/2 h-[13px] w-[13px] -translate-x-1/2 -translate-y-1/2 rounded-full ${valenceDot(valence)}`}
          style={{ left: `${pct(value, domain)}%`, boxShadow: "0 0 0 2px var(--color-surface)" }}
        />
      </div>

      {/* value + status */}
      <div className="whitespace-nowrap text-right">
        <div className="font-mono text-[13px] font-medium text-ink">
          {fmt(value)}
          {unitEl}
        </div>
        {flagged ? (
          <div className={`mt-0.5 flex items-center justify-end gap-1.5 text-[11px] font-medium ${valenceText(valence)}`}>
            {statusWord(verdict.direction, verdict.valence)}
            <button
              onClick={onDismiss}
              title="Dismiss this flag"
              aria-label="Dismiss this flag"
              className="inline-flex h-[18px] w-[18px] items-center justify-center rounded-md border border-navy bg-surface text-xs leading-none text-muted hover:border-usual hover:text-ink"
            >
              ×
            </button>
          </div>
        ) : dismissed ? (
          <div className="mt-0.5 text-[10.5px] text-muted">
            dismissed
            <button
              onClick={onRestore}
              className="ml-1 text-accent underline"
            >
              undo
            </button>
          </div>
        ) : (
          <div className="mt-0.5 text-[11px] text-muted">in range</div>
        )}
      </div>
    </div>
  );
}
