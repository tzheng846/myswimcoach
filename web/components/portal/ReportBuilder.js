"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import Avatar from "./Avatar";
import { REPORT_METRICS } from "@/lib/reportMetrics";

export default function ReportBuilder({ onGenerated }) {
  const [athletes, setAthletes] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [metrics, setMetrics] = useState(new Set(REPORT_METRICS.map((m) => m.key)));
  const [message, setMessage] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    supabase
      .from("athletes")
      .select("id, name, parent_name, parent_email")
      .order("name")
      .then(({ data }) => setAthletes(data ?? []));
  }, []);

  function toggle(set, value, setter) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setter(next);
  }

  const allSelected = athletes.length > 0 && selected.size === athletes.length;

  async function generate() {
    setError(null);
    setGenerating(true);
    try {
      const rows = [...selected].map((athleteId) => ({
        athlete_id: athleteId,
        token: crypto.randomUUID(),
        config_json: {
          start: start ? new Date(start).toISOString() : null,
          end: end ? new Date(`${end}T23:59:59`).toISOString() : null,
          metrics: REPORT_METRICS.map((m) => m.key).filter((k) => metrics.has(k)),
          message: message.trim() || null,
        },
      }));
      const { error } = await supabase.from("reports").insert(rows);
      if (error) throw error;
      setSelected(new Set());
      setMessage("");
      onGenerated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-5">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">
        New Report Cards
      </p>

      {/* Swimmer selection */}
      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-semibold">Swimmers</p>
          <button
            onClick={() =>
              setSelected(allSelected ? new Set() : new Set(athletes.map((a) => a.id)))
            }
            className="text-xs text-primary hover:underline"
          >
            {allSelected ? "Clear all" : "Select all"}
          </button>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {athletes.map((a) => (
            <label
              key={a.id}
              className={`flex cursor-pointer items-center gap-2.5 rounded-lg border p-2.5 transition-colors ${
                selected.has(a.id)
                  ? "border-primary bg-navy/30"
                  : "border-surface-3 bg-surface-2 hover:border-navy"
              }`}
            >
              <input
                type="checkbox"
                checked={selected.has(a.id)}
                onChange={() => toggle(selected, a.id, setSelected)}
                className="accent-[#2196f3]"
              />
              <Avatar name={a.name} size={28} />
              <span className="min-w-0 flex-1 truncate text-sm">{a.name}</span>
              {!a.parent_email && (
                <span className="shrink-0 text-[10px] text-amber">no email</span>
              )}
            </label>
          ))}
          {athletes.length === 0 && (
            <p className="text-sm text-muted">No athletes on roster yet.</p>
          )}
        </div>
      </div>

      {/* Date range */}
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs text-muted">
            From (blank = first session)
          </label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full rounded-md border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none [color-scheme:dark] focus:border-primary"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">
            To (blank = latest session)
          </label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full rounded-md border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none [color-scheme:dark] focus:border-primary"
          />
        </div>
      </div>

      {/* Metric checklist */}
      <div className="mt-5">
        <p className="mb-2 text-sm font-semibold">Metrics to include</p>
        <div className="flex flex-wrap gap-2">
          {REPORT_METRICS.map((m) => (
            <label
              key={m.key}
              className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] transition-colors ${
                metrics.has(m.key)
                  ? "border-primary bg-primary text-white"
                  : "border-surface-3 bg-surface-2 text-subtle"
              }`}
            >
              <input
                type="checkbox"
                checked={metrics.has(m.key)}
                onChange={() => toggle(metrics, m.key, setMetrics)}
                className="hidden"
              />
              {m.label}
            </label>
          ))}
        </div>
      </div>

      {/* Message */}
      <div className="mt-5">
        <label className="mb-1 block text-sm font-semibold">
          Note to parents{" "}
          <span className="font-normal text-muted">
            (optional — included on every selected report)
          </span>
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder="What should parents know about this training block?"
          className="w-full resize-y rounded-md border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-primary"
        />
      </div>

      {error && <p className="mt-3 text-sm text-[#ff5252]">{error}</p>}

      <button
        onClick={generate}
        disabled={generating || selected.size === 0 || metrics.size === 0}
        className="mt-5 rounded-lg bg-primary px-6 py-2.5 font-semibold text-white transition-colors hover:bg-accent disabled:opacity-50"
      >
        {generating
          ? "Generating…"
          : `Generate ${selected.size || ""} report card${selected.size === 1 ? "" : "s"}`}
      </button>
    </div>
  );
}
