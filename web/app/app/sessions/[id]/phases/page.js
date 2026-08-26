"use client";

// /app/sessions/[id]/phases — the race-phase report card route (Phase 75-05, Step 3). Reads the
// session's stored profiles + metrics_json.phases via supabase-js (reads bypass the FastAPI by
// design), fetches the athlete's last-5 same-stroke baseline, and hands both to PhaseReportCard.
// Additive + isolated: the existing report card at ../[id] is untouched beyond one nav link.

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { fetchPhaseBaseline } from "@/lib/phaseBaseline";
import PhaseReportCard from "@/components/portal/phases/PhaseReportCard";

export default function PhasesPage({ params }) {
  const { id: sessionId } = use(params);

  const [data, setData] = useState(null);
  const [athlete, setAthlete] = useState(null);
  const [baseline, setBaseline] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const { data: row, error: err } = await supabase
        .from("sessions")
        .select("metrics_json, velocity_profile, distance_profile, stroke_type, athlete_id, created_at, sample_rate_hz")
        .eq("id", sessionId)
        .single();
      if (!alive) return;
      if (err) {
        setError("Failed to load session.");
        return;
      }
      setData(row);
      // Athlete name + baseline together — the baseline is the athlete's prior same-stroke swims,
      // so both hang off the row we just loaded.
      const [{ data: ath }, base] = await Promise.all([
        row.athlete_id
          ? supabase.from("athletes").select("name").eq("id", row.athlete_id).single()
          : Promise.resolve({ data: null }),
        fetchPhaseBaseline({
          athleteId: row.athlete_id,
          strokeType: row.stroke_type,
          beforeCreatedAt: row.created_at,
        }),
      ]);
      if (!alive) return;
      setAthlete(ath);
      setBaseline(base ?? {});
    })();
    return () => {
      alive = false;
    };
  }, [sessionId]);

  if (error) return <p className="mt-10 text-center text-danger">{error}</p>;
  if (!data) return <p className="text-muted">Loading…</p>;

  const phases = data.metrics_json?.phases ?? null;
  const fsHz = data.sample_rate_hz > 0 ? data.sample_rate_hz : 100;
  const date = new Date(data.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between">
        <Link href={`/app/sessions/${sessionId}`} className="text-sm text-primary">
          ‹ Back to report
        </Link>
        <div className="text-center">
          <p className="font-semibold">{athlete?.name ?? ""}</p>
          <p className="text-xs text-muted">{date}</p>
        </div>
        <span className="w-24" aria-hidden="true" />
      </div>

      <h1 className="mt-3 mb-4 text-lg font-semibold text-ink">Race phases</h1>

      {phases ? (
        <PhaseReportCard
          phases={phases}
          velocity={data.velocity_profile ?? []}
          distProfile={data.distance_profile ?? []}
          fsHz={fsHz}
          baseline={baseline}
          strokeType={data.stroke_type}
          sessionId={sessionId}
        />
      ) : (
        <div className="mt-8 rounded-xl border border-navy/50 bg-surface p-6 text-center">
          <p className="font-semibold text-ink">No race-phase breakdown yet</p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            This session predates the phase model. Re-run its analysis to generate the phase report.
          </p>
        </div>
      )}
    </div>
  );
}
