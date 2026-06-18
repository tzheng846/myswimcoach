"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import TeamPulse from "@/components/portal/TeamPulse";
import NeedsAttention from "@/components/portal/NeedsAttention";
import RecentActivity from "@/components/portal/RecentActivity";
import RosterBandCard from "@/components/portal/RosterBandCard";

export default function DashboardPage() {
  const [data, setData] = useState(undefined); // undefined = loading, null = error

  useEffect(() => {
    let live = true;
    apiFetch("/team/overview")
      .then((d) => live && setData(d))
      .catch(() => live && setData(null));
    return () => {
      live = false;
    };
  }, []);

  if (data === undefined) return <p className="text-muted">Loading…</p>;
  if (data === null) return <p className="text-muted">Couldn’t load the dashboard.</p>;

  const colors = data.rating_colors;

  return (
    <div>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-1 text-sm text-muted">How your team is doing, at a glance.</p>

      {data.athlete_count === 0 ? (
        <p className="mt-10 text-center text-muted">
          No athletes yet — add your roster on the Athletes page.
        </p>
      ) : (
        <div className="mt-6 space-y-8">
          <TeamPulse
            athleteCount={data.athlete_count}
            testedThisWeek={data.tested_this_week}
            pillars={data.pillars}
            colors={colors}
          />
          <NeedsAttention items={data.needs_attention} colors={colors} />
          <RecentActivity items={data.recent} />
          <section>
            <h2 className="text-sm uppercase tracking-wider text-muted">Team</h2>
            <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.athletes.map((a) => (
                <RosterBandCard key={a.athlete_id} athlete={a} colors={colors} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
