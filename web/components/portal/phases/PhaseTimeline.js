"use client";

// PhaseTimeline — the segmented "Race phases" bar (Phase 75-05): Dive/Push-off | Underwater |
// Swimming, each segment's width = its distance (or time) share, with a thin "Surfaced" divider at
// the breakout (stroke_start_s). The phase carrying the most active flags gets a NEUTRAL attention
// outline (a phase is never good/bad) and a hover-explain payload listing what changed. Ported from
// the v3 concept mockup (report-card-concept-v3.html). Boundaries in seconds; a missing boundary
// degrades that one segment rather than crashing the bar.

import { useMemo, useState } from "react";
import { ExplainTrigger } from "./HoverExplain";

const PHASE_META = [
  { key: "start", label: "Dive / Push-off", from: "dive_start_s", to: "underwater_start_s" },
  { key: "underwater", label: "Underwater", from: "underwater_start_s", to: "stroke_start_s" },
  { key: "swim", label: "Swimming", from: "stroke_start_s", to: "finish_s" },
];

const fmt = (v) => (v == null || !Number.isFinite(v) ? "—" : Number.isInteger(v) ? String(v) : v.toFixed(2));
const fmt1 = (v) => (v == null || !Number.isFinite(v) ? "—" : v.toFixed(1));

function valenceText(valence) {
  return valence === "good"
    ? "text-good"
    : valence === "bad"
      ? "text-bad"
      : valence === "neutral"
        ? "text-neutral"
        : "text-subtle";
}

export default function PhaseTimeline({
  boundaries,
  distProfile = [],
  velocity = [],
  fsHz = 100,
  flagsByPhase = {}, // { start:[{label,value,median,unit,valence}], underwater:[...], swim:[...] }
}) {
  const [mode, setMode] = useState("dist");

  const model = useMemo(() => {
    if (!boundaries) return null;
    const n = velocity.length || distProfile.length;
    const idxOf = (t) =>
      t == null || !(fsHz > 0) || n === 0 ? null : Math.max(0, Math.min(n - 1, Math.round(t * fsHz)));
    const distAt = (t) => {
      const i = idxOf(t);
      return i == null || !Number.isFinite(distProfile[i]) ? null : distProfile[i];
    };
    const finishS = boundaries.finish_s ?? (n > 0 && fsHz > 0 ? (n - 1) / fsHz : null);

    const segs = PHASE_META.map((p) => {
      const aS = boundaries[p.from];
      const bS = p.to === "finish_s" ? finishS : boundaries[p.to];
      if (aS == null || bS == null || !(bS > aS)) return { ...p, ok: false };
      const da = distAt(aS);
      const db = distAt(bS);
      return {
        ...p,
        ok: true,
        aS,
        bS,
        timeShare: bS - aS,
        distShare: da != null && db != null ? Math.max(0, db - da) : null,
      };
    });

    const usable = segs.filter((s) => s.ok);
    return {
      segs,
      totalTime: usable.reduce((a, s) => a + s.timeShare, 0),
      totalDist: usable.reduce((a, s) => a + (s.distShare ?? 0), 0),
      strokeStartS: boundaries.stroke_start_s,
    };
  }, [boundaries, distProfile, velocity.length, fsHz]);

  if (!model) return null;

  const useDist = mode === "dist" && model.totalDist > 0;
  const total = useDist ? model.totalDist : model.totalTime;

  const counts = {};
  for (const p of PHASE_META) counts[p.key] = flagsByPhase[p.key]?.length || 0;
  const hot =
    PHASE_META.map((p) => p.key)
      .filter((k) => counts[k] > 0)
      .sort((a, b) => counts[b] - counts[a])[0] || null;

  const segInner = (s, isHot) => {
    const share = useDist ? s.distShare : s.timeShare;
    const valTxt =
      !s.ok || share == null
        ? "—"
        : `${fmt1(share)} ${useDist ? "m" : "s"}${total > 0 ? ` · ${Math.round((share / total) * 100)}%` : ""}`;
    return (
      <>
        <span className="truncate text-xs font-semibold text-ink">
          {s.label}
          {isHot && <span className="ml-1 align-middle text-[8px] text-accent">●</span>}
        </span>
        <span className="mt-0.5 font-mono text-[11px] text-subtle">{valTxt}</span>
      </>
    );
  };

  return (
    <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
      <div className="mb-3.5 flex items-center justify-between gap-3">
        <h2 className="font-semibold text-ink">
          Race phases
          <span className="ml-2 text-[11.5px] font-normal text-muted">start → finish</span>
        </h2>
        <div className="inline-flex overflow-hidden rounded-lg border border-surface-3 bg-surface-2">
          {[
            ["dist", "By distance"],
            ["time", "By time"],
          ].map(([m, label]) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              className={`px-3 py-1.5 text-xs transition-colors ${
                mode === m ? "bg-accent text-white" : "text-subtle hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex h-14 overflow-hidden rounded-xl border border-navy/50 bg-surface-2">
        {model.segs.map((s, i) => {
          const isHot = s.ok && s.key === hot;
          const grow = s.ok ? (useDist ? s.distShare ?? s.timeShare : s.timeShare) || 0.001 : 1;
          const tint =
            s.key === "underwater" ? "bg-accent/15" : s.key === "swim" ? "bg-accent/[0.06]" : "bg-accent/10";
          const divider = i < model.segs.length - 1 ? "border-r-2 border-surface" : "";
          const segClass = `relative flex min-w-0 flex-col justify-center ${divider} px-3.5 ${tint} ${
            isHot ? "!bg-accent/25 cursor-help ring-2 ring-inset ring-accent" : ""
          }`;
          const flags = flagsByPhase[s.key] ?? [];

          const child = isHot ? (
            <ExplainTrigger
              as="div"
              title={`${s.label} — what changed`}
              tag={null}
              body={
                <>
                  <b>{counts[s.key]}</b> metric{counts[s.key] > 1 ? "s" : ""} here differ from usual:
                  <br />
                  <br />
                  {flags.map((f, k) => (
                    <span key={k}>
                      <span className={valenceText(f.valence)}>{f.label}</span> ({fmt(f.value)}
                      {f.unit} vs {fmt(f.median)}
                      {f.unit})
                      <br />
                    </span>
                  ))}
                </>
              }
              className={`${segClass} outline-none`}
              style={{ flexGrow: grow, flexBasis: 0 }}
            >
              {segInner(s, true)}
            </ExplainTrigger>
          ) : (
            <div key={s.key} className={segClass} style={{ flexGrow: grow, flexBasis: 0 }}>
              {segInner(s, false)}
            </div>
          );

          // The breakout divider sits between Underwater and Swimming (at stroke_start_s).
          const showSurfaced = s.key === "underwater" && model.strokeStartS != null;
          return (
            <div key={s.key} className="contents">
              {child}
              {showSurfaced && (
                <div className="relative w-0 flex-none overflow-visible" aria-hidden>
                  <span className="absolute top-0 left-[-1px] h-14 w-0.5 bg-ink/50" />
                  <b className="absolute top-[-15px] left-[-20px] whitespace-nowrap text-[9px] font-semibold uppercase tracking-wider text-muted">
                    Surfaced
                  </b>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
