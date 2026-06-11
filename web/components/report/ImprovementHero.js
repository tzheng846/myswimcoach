"use client";

import { useEffect, useRef, useState } from "react";
import { computeImprovement, formatValue, metricByKey } from "@/lib/reportMetrics";

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

function CountUp({ value, decimals = 0, prefix = "", suffix = "" }) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(reduced ? value : 0);
  const raf = useRef(null);

  useEffect(() => {
    if (reduced) {
      setDisplay(value);
      return;
    }
    const duration = 1200;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(value * eased);
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [value, reduced]);

  return (
    <span>
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}

function HeroCard({ metric, first, latest }) {
  const imp = computeImprovement(metric, first, latest);

  if (!imp) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-5">
        <p className="text-xs uppercase tracking-wider text-muted">{metric.label}</p>
        <p className="mt-2 font-mono text-3xl font-bold">{formatValue(metric, latest)}</p>
      </div>
    );
  }

  const positive = imp.improved === true;
  const neutral = imp.improved === null;

  return (
    <div
      className={`rounded-xl border p-5 ${
        positive
          ? "border-primary/60 bg-navy/30 shadow-[0_0_30px_rgba(33,150,243,0.10)]"
          : "border-navy/50 bg-surface"
      }`}
    >
      <p className="text-xs uppercase tracking-wider text-muted">{metric.label}</p>
      <p
        className={`mt-2 font-mono text-4xl font-bold ${
          positive ? "text-primary" : neutral ? "text-ink" : "text-subtle"
        }`}
      >
        <CountUp
          value={Math.abs(imp.pct)}
          decimals={Math.abs(imp.pct) < 10 ? 1 : 0}
          prefix={imp.pct >= 0 ? "+" : "−"}
          suffix="%"
        />
      </p>
      <p className="mt-1 text-sm text-subtle">
        {positive ? imp.phrase : neutral ? imp.phrase : `change in ${metric.label.toLowerCase()}`}
      </p>
      <p className="mt-3 text-xs text-muted">
        now {formatValue(metric, latest)}{" "}
        <span className="text-muted/70">(was {formatValue(metric, first)})</span>
      </p>
    </div>
  );
}

export default function ImprovementHero({ metricKeys, sessions }) {
  const metrics = metricKeys.map(metricByKey).filter(Boolean);
  const first = sessions[0];
  const latest = sessions[sessions.length - 1];
  const single = sessions.length < 2;

  return (
    <div>
      {single && (
        <p className="mb-3 text-sm text-subtle">
          First benchmark — here&apos;s where the journey starts. Future reports
          will show progress against these numbers.
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((m) => (
          <HeroCard
            key={m.key}
            metric={m}
            first={single ? null : first?.values?.[m.key]}
            latest={latest?.values?.[m.key]}
          />
        ))}
      </div>
    </div>
  );
}
