"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

const VERDICT = { good: "Good", ok: "OK", needs_work: "Needs work" };
const TREND = {
  improved: { label: "Improved", icon: "↑" },
  declined: { label: "Declined", icon: "↓" },
  steady: { label: "Steady", icon: "→" },
  first_session: { label: "First session", icon: "•" },
};

function fmt(v) {
  if (v == null) return "--";
  return typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(2)) : v;
}

function TrendChip({ trend, colors }) {
  const t = TREND[trend] || TREND.first_session;
  const fg =
    trend === "improved" ? colors.good : trend === "declined" ? colors.needs_work : null;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md bg-surface-2 px-2 py-0.5 text-xs font-semibold text-muted"
      style={fg ? { color: fg } : undefined}
    >
      <span aria-hidden="true">{t.icon}</span>
      {t.label}
    </span>
  );
}

function Band({ score, colors }) {
  const pos = Math.max(0, Math.min(100, score ?? 0));
  return (
    <div className="relative my-2.5 h-2.5">
      <div className="absolute inset-0 flex gap-[3px]">
        <div className="flex-1 rounded-l" style={{ background: colors.needs_work }} />
        <div className="flex-1" style={{ background: colors.ok }} />
        <div className="flex-1 rounded-r" style={{ background: colors.good }} />
      </div>
      <div
        className="absolute -top-1 h-[18px] w-[3px] rounded bg-ink"
        style={{ left: `${pos}%`, transform: "translateX(-50%)" }}
      />
    </div>
  );
}

function PillarCard({ p, colors }) {
  const [open, setOpen] = useState(false);
  const unknown = p.band === "unknown";
  const verdictColor =
    p.band === "good" ? colors.good : p.band === "ok" ? colors.ok : colors.needs_work;
  const detail = [p.primary, ...(p.metrics || [])].filter((m) => m && m.value != null);

  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-4">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={`pillar-detail-${p.key}`}
        className="w-full text-left"
      >
        <div className="flex items-center justify-between">
          <span className="font-semibold text-ink">{p.label}</span>
          <TrendChip trend={p.trend} colors={colors} />
        </div>

        {unknown ? (
          <p className="mt-2 text-sm text-muted">Not enough data</p>
        ) : (
          <>
            <Band score={p.score} colors={colors} />
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold" style={{ color: verdictColor }}>
                {VERDICT[p.band]}
              </span>
              <span className="text-xs text-muted" aria-hidden="true">
                {open ? "▲" : "▼"}
              </span>
            </div>
          </>
        )}
      </button>

      {open && (
        <div id={`pillar-detail-${p.key}`} className="mt-3 border-t border-navy/50 pt-3">
          <p className="text-sm leading-relaxed text-muted">{p.explanation}</p>
          {detail.length > 0 && (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {detail.map((m) => (
                <div key={m.key} className="rounded-lg bg-surface-2 p-2.5">
                  <p className="text-[11px] text-muted">{m.label}</p>
                  <p className="mt-0.5 font-mono text-lg text-ink">
                    {fmt(m.value)}
                    {m.unit ? <span className="text-[11px] text-muted"> {m.unit}</span> : null}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Glanceable good/ok/needs-work read for the four headline pillars.
// Reads GET /sessions/{id}/ratings (ratings.py is the shared source of truth).
export default function PillarCards({ sessionId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let live = true;
    setData(null);
    setError(false);
    apiFetch(`/sessions/${sessionId}/ratings`)
      .then((d) => live && setData(d))
      .catch(() => live && setError(true));
    return () => {
      live = false;
    };
  }, [sessionId]);

  if (error)
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-4 text-sm text-muted">
        Couldn’t load the rating summary.
      </div>
    );
  if (!data)
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-4 text-sm text-muted">
        Loading ratings…
      </div>
    );

  const provisional = data.pillars.some((p) => p.provisional);

  return (
    <div className="space-y-3">
      {provisional && (
        <div className="flex items-center gap-1.5 text-[11px] text-warning">
          <span aria-hidden="true">⚠</span>
          Provisional — stroke segmentation is still being validated.
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        {data.pillars.map((p) => (
          <PillarCard key={p.key} p={p} colors={data.rating_colors} />
        ))}
      </div>
    </div>
  );
}
