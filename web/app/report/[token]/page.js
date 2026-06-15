"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import ImprovementHero from "@/components/report/ImprovementHero";
import MetricTrend from "@/components/report/MetricTrend";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://swimnetics-api-production.up.railway.app";

function Shell({ children }) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-16 pt-8">
      <div className="flex items-center">
        <span className="text-xs font-bold tracking-[0.3em] text-ink">
          SWIMNETICS
        </span>
      </div>
      {children}
    </main>
  );
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function ReportPage({ params }) {
  const { token } = use(params);
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading"); // loading | ready | notfound

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/reports/${token}`);
        if (!res.ok) {
          setState("notfound");
          return;
        }
        setData(await res.json());
        setState("ready");
      } catch {
        setState("notfound");
      }
    })();
  }, [token]);

  if (state === "loading") {
    return (
      <Shell>
        <div className="mt-16 text-center text-muted">Loading report…</div>
      </Shell>
    );
  }

  if (state === "notfound") {
    return (
      <Shell>
        <div className="mt-16 text-center">
          <p className="text-lg font-semibold">This report isn&apos;t available.</p>
          <p className="mt-2 text-sm text-muted">
            The link may have been removed or mistyped — please check with your
            coach for a fresh one.
          </p>
        </div>
      </Shell>
    );
  }

  const firstName = (data.athlete?.name ?? "Your swimmer").split(" ")[0];
  const sessions = data.sessions ?? [];
  const periodStart = sessions[0]?.date ?? data.period?.start;
  const periodEnd =
    sessions[sessions.length - 1]?.date ?? data.period?.end;

  return (
    <Shell>
      <header className="mt-8">
        <p className="text-xs font-semibold tracking-[0.3em] text-amber">
          PROGRESS REPORT
        </p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
          {firstName}&apos;s Progress Report
        </h1>
        <p className="mt-2 text-sm text-subtle">
          {periodStart && periodEnd
            ? `${fmtDate(periodStart)} — ${fmtDate(periodEnd)}`
            : "Training period"}
          {sessions.length > 0 &&
            ` · ${sessions.length} recorded session${sessions.length === 1 ? "" : "s"}`}
        </p>
      </header>

      <div className="mt-8 space-y-8">
        {sessions.length === 0 ? (
          <p className="rounded-xl border border-navy/50 bg-surface p-6 text-center text-sm text-muted">
            No recorded sessions in this period yet — check back after the next
            test set.
          </p>
        ) : (
          <>
            <ImprovementHero metricKeys={data.metrics ?? []} sessions={sessions} />

            {data.message && (
              <div className="rounded-xl border-l-2 border-l-amber border-y border-r border-y-navy/50 border-r-navy/50 bg-surface p-5">
                <p className="text-xs font-semibold uppercase tracking-widest text-amber">
                  A note from the coach
                </p>
                <p className="mt-2 leading-relaxed text-ink">
                  {data.message}
                </p>
                <p className="mt-2 text-sm text-muted">— Coach</p>
              </div>
            )}

            <MetricTrend metricKeys={data.metrics ?? []} sessions={sessions} />
          </>
        )}
      </div>

      <footer className="mt-12 border-t border-navy/30 pt-6 text-center">
        <p className="text-xs text-muted">
          Measured with Swimnetics velocity tracking — every number comes from
          real in-water motion, recorded at the pool.
        </p>
        <Link
          href="/"
          className="mt-2 inline-block text-xs text-primary hover:underline"
        >
          Learn more at swimnetics.com
        </Link>
      </footer>
    </Shell>
  );
}
