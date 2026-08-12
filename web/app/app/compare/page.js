"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import CompareChart from "@/components/portal/CompareChart";
import CompareCycleCharts from "@/components/portal/CompareCycleCharts";
import { sessionLabel, sessionDate } from "@/lib/sessionName";

function SessionPicker({ side, athletes, value, onChange }) {
  const [athleteId, setAthleteId] = useState("");
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    if (!athleteId) {
      setSessions([]);
      return;
    }
    supabase
      .from("sessions")
      .select("id, created_at, name, athlete_id")
      .eq("athlete_id", athleteId)
      .order("created_at", { ascending: false })
      .then(({ data }) => setSessions(data ?? []));
  }, [athleteId]);

  return (
    <div className="flex-1 rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Session {side}
      </p>
      <select
        value={athleteId}
        onChange={(e) => {
          setAthleteId(e.target.value);
          onChange(null);
        }}
        className="w-full rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
      >
        <option value="">Select athlete…</option>
        {athletes.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={!athleteId}
        className="mt-2 w-full rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-50"
      >
        <option value="">Select session…</option>
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {sessionLabel(s)}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function ComparePage() {
  const [athletes, setAthletes] = useState([]);
  const [idA, setIdA] = useState(null);
  const [idB, setIdB] = useState(null);
  const [rowA, setRowA] = useState(null);
  const [rowB, setRowB] = useState(null);

  useEffect(() => {
    supabase
      .from("athletes")
      .select("id, name")
      .order("name")
      .then(({ data }) => setAthletes(data ?? []));
  }, []);

  useEffect(() => {
    if (!idA) {
      setRowA(null);
      return;
    }
    supabase
      .from("sessions")
      .select(
        "id, created_at, name, velocity_profile, sample_rate_hz, session:metrics_json->session, cycles:metrics_json->cycles"
      )
      .eq("id", idA)
      .single()
      .then(({ data }) => setRowA(data));
  }, [idA]);

  useEffect(() => {
    if (!idB) {
      setRowB(null);
      return;
    }
    supabase
      .from("sessions")
      .select(
        "id, created_at, name, velocity_profile, sample_rate_hz, session:metrics_json->session, cycles:metrics_json->cycles"
      )
      .eq("id", idB)
      .single()
      .then(({ data }) => setRowB(data));
  }, [idB]);

  // Alignment nudge (D9). Shifts B relative to A so the coach can line the two swims up by eye.
  // ⚠ IN-MEMORY ONLY — never persisted, matching the mobile start-marker precedent. It is a
  // viewing aid, not a property of either session.
  const [offsetS, setOffsetS] = useState(0);

  const ready = rowA && rowB;
  // Baseline = older session (app.py convention: delta = % change from baseline)
  let baseRow = rowA;
  let newRow = rowB;
  if (ready && new Date(rowA.created_at) > new Date(rowB.created_at)) {
    baseRow = rowB;
    newRow = rowA;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Compare</h1>
      <p className="mt-1 text-sm text-muted">
        Pick two sessions — each trace is drawn on its own recorded sample rate, and deltas are
        % change from the older (baseline) session.
      </p>

      <div className="mt-5 flex flex-col gap-4 sm:flex-row">
        <SessionPicker side="A" athletes={athletes} value={idA} onChange={setIdA} />
        <SessionPicker side="B" athletes={athletes} value={idB} onChange={setIdB} />
      </div>

      {ready ? (
        <div className="mt-5 space-y-4">
          <CompareChart
            velA={baseRow.velocity_profile}
            velB={newRow.velocity_profile}
            // Never hardcode 100 — read each session's own recorded rate, falling back only when
            // it is NULL (pre-Phase-52 rows), exactly as sessions/[id]/page.js does.
            fsA={baseRow.sample_rate_hz > 0 ? baseRow.sample_rate_hz : 100}
            fsB={newRow.sample_rate_hz > 0 ? newRow.sample_rate_hz : 100}
            labelA={`${sessionLabel(baseRow)} (baseline)`}
            labelB={sessionLabel(newRow)}
            offsetS={offsetS}
          />

          <div className="flex flex-wrap items-center justify-center gap-2 rounded-xl border border-navy/50 bg-surface px-3 py-2 text-xs">
            <span className="text-muted">Align second trace</span>
            {[-1, -0.1].map((d) => (
              <button
                key={d}
                onClick={() => setOffsetS((o) => Math.round((o + d) * 100) / 100)}
                className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
              >
                {d}s
              </button>
            ))}
            <span className="w-16 text-center font-mono text-ink">
              {offsetS >= 0 ? "+" : ""}
              {offsetS.toFixed(2)} s
            </span>
            {[0.1, 1].map((d) => (
              <button
                key={d}
                onClick={() => setOffsetS((o) => Math.round((o + d) * 100) / 100)}
                className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
              >
                +{d}s
              </button>
            ))}
            <button
              onClick={() => setOffsetS(0)}
              disabled={offsetS === 0}
              className={`rounded-md px-2.5 py-1 font-semibold ${
                offsetS !== 0 ? "bg-accent text-white" : "bg-surface-2 text-muted"
              }`}
            >
              Reset
            </button>
            <span className="text-muted">not saved</span>
          </div>

          <CompareCycleCharts
            cyclesA={baseRow.cycles}
            cyclesB={newRow.cycles}
            sessionA={baseRow.session}
            sessionB={newRow.session}
            labelA={sessionLabel(baseRow)}
            labelB={sessionLabel(newRow)}
          />
        </div>
      ) : (
        <p className="mt-10 text-center text-sm text-muted">
          Select two sessions to compare.
        </p>
      )}
    </div>
  );
}
