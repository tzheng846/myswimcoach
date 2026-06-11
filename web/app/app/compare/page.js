"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import CompareChart from "@/components/portal/CompareChart";
import MetricDeltaTable from "@/components/portal/MetricDeltaTable";

function sessionLabel(s) {
  const date = new Date(s.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return s.name ? `${s.name} — ${date}` : date;
}

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
      .select("id, created_at, name, velocity_profile, session:metrics_json->session")
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
      .select("id, created_at, name, velocity_profile, session:metrics_json->session")
      .eq("id", idB)
      .single()
      .then(({ data }) => setRowB(data));
  }, [idB]);

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
        Pick two sessions — curves align at t=0; deltas are % change from the
        older (baseline) session.
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
            labelA={`${sessionLabel(baseRow)} (baseline)`}
            labelB={sessionLabel(newRow)}
          />
          <MetricDeltaTable
            baseline={baseRow.session}
            newer={newRow.session}
            labelBase={sessionLabel(baseRow)}
            labelNew={sessionLabel(newRow)}
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
