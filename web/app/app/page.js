"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import AthleteCard from "@/components/portal/AthleteCard";

export default function DashboardPage() {
  const [athletes, setAthletes] = useState(null);
  const [lastSessions, setLastSessions] = useState({});

  useEffect(() => {
    (async () => {
      const { data: athletes } = await supabase
        .from("athletes")
        .select("id, name, stroke_type, head_waist_m")
        .order("name");
      setAthletes(athletes ?? []);

      const ids = (athletes ?? []).map((a) => a.id);
      if (ids.length > 0) {
        const { data: sessions } = await supabase
          .from("sessions")
          .select("athlete_id, created_at, metrics_json")
          .in("athlete_id", ids)
          .order("created_at", { ascending: false });
        const latest = {};
        for (const s of sessions ?? []) {
          if (!latest[s.athlete_id]) latest[s.athlete_id] = s;
        }
        setLastSessions(latest);
      }
    })();
  }, []);

  if (athletes === null) return <p className="text-muted">Loading…</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-1 text-sm text-muted">
        Latest session at a glance, per athlete.
      </p>

      {athletes.length === 0 ? (
        <p className="mt-10 text-center text-muted">
          No athletes yet — add your roster on the Athletes page.
        </p>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {athletes.map((a) => (
            <AthleteCard key={a.id} athlete={a} lastSession={lastSessions[a.id]} />
          ))}
        </div>
      )}
    </div>
  );
}
