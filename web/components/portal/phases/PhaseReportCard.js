"use client";

// PhaseReportCard — assembles the race-phase report card (Phase 75-05, Step 3). Reads the stored
// `metrics_json.phases` object (Start + Underwater implemented; Swim + Whole still planned) plus the
// athlete's last-5 same-stroke baseline, and renders the v3 visual language: a one-line legend, a
// deterministic valence-broken-down alert line, the phase timeline, a phase-tinted velocity line,
// then one section per implemented phase — inset chart full-width on top, metrics in two columns,
// each a 1D usual-range strip colored by direction-of-good. Every description + comparison lives in
// the hover-explain overlay; nothing here asserts a verdict in prose. Ported 1:1 from
// scratch/report-card-concept-v3.html.

import { useEffect, useMemo, useState } from "react";
import { flagVerdict, directionOfGood } from "@/lib/phaseValence";
import { BASELINE_LIMIT } from "@/lib/phaseBaseline";
import { STROKE_LABELS } from "@/components/portal/SessionCard";
import { HoverExplainProvider } from "./HoverExplain";
import RangeStrip from "./RangeStrip";
import PhaseVelocity from "./PhaseVelocity";
import PhaseTimeline from "./PhaseTimeline";
import AlertSummary from "./AlertSummary";

// Short label + friendly unit + plain description, keyed by phase_metrics REGISTRY key. Wording
// sourced from the v3 mockup. `emptyNote` overrides the "not measured this swim" pill for the two
// metrics that are absent for a knowable reason rather than a failed window.
const DISPLAY = {
  // Start
  peak_vel: { label: "Top speed off dive", unit: "m/s", desc: "His single quickest instant off the block — a peak, not an average. Higher is better." },
  time_to_peak_vel: { label: "Time to top speed", unit: "s", desc: "Block to that fastest instant. Faster (lower) is better." },
  max_accel: { label: "Push off the block", unit: "m/s²", desc: "How hard he accelerated off the wall. Higher is better." },
  dive_duration: { label: "Dive length", unit: "s", desc: "How long the start phase lasted. Neither longer nor shorter is clearly better." },
  glide_duration: { label: "Coast time", unit: "s", desc: "The streamline glide before he kicked. Too long loses speed, too short wastes streamline — a coaching call." },
  glide_distance: { label: "Coast distance", unit: "m", desc: "Distance covered while gliding. Good or bad depends on the glide plan." },
  glide_avg_speed: { label: "Coast speed", unit: "m/s", desc: "Average speed carried through the glide. Higher is better." },
  glide_decel: { label: "Speed lost coasting", unit: "m/s²", desc: "How fast he decelerated during the glide. Lower (less drag) is better." },
  break_into_kick_vel: { label: "Speed at first kick", unit: "m/s", desc: "Speed the instant kicking began. There's an optimum, not simply higher-is-better." },
  streamline_drag: { label: "Streamline drag", unit: "", desc: "", emptyNote: "planned" },
  reaction_time: { label: "Reaction time", unit: "s", desc: "From the coach's GO signal to first movement. Faster (lower) is better.", emptyNote: "needs coach GO signal" },
  // Underwater
  uw_duration: { label: "Time underwater", unit: "s", desc: "Dive until he broke the surface. More or less underwater is a race-plan choice." },
  uw_distance: { label: "Distance underwater", unit: "m", desc: "How far before surfacing. Good or bad depends on the underwater plan." },
  uw_avg_speed: { label: "Underwater speed", unit: "m/s", desc: "Average speed over the whole underwater. Higher is better." },
  uw_surface_ratio: { label: "Underwater vs surface", unit: "×", desc: "Above 1× = he was faster underwater than swimming. Higher is better." },
  kick_count: { label: "Kicks", unit: "", desc: "Dolphin kicks before surfacing. More kicks = more propulsion but slower to surface — genuinely a coaching call." },
  dist_per_kick: { label: "Distance per kick", unit: "m", desc: "How far each kick carried him. Higher is better." },
  kick_tempo: { label: "Kick rate", unit: "/s", desc: "Kicks per second. Faster isn't automatically better — depends on distance per kick." },
  kick_consistency: { label: "Kick evenness", unit: "", desc: "Evenly spaced vs ragged. Lower is more even (better)." },
  uw_ivv: { label: "Underwater wobble", unit: "", desc: "How much speed rose and fell underwater. Lower is smoother (better)." },
  per_kick_decay: { label: "Kick fade", unit: "%", desc: "Last kick's speed vs the first. Less fade (higher / toward 0) is better." },
  first_kick_impulse: { label: "First-kick punch", unit: "m/s", desc: "Speed gained on the very first kick. Higher is better." },
  pulldown_peak_vel: { label: "Pulldown speed", unit: "m/s", desc: "Peak speed of the breaststroke pulldown. Higher is better." },
  pulldown_duration: { label: "Pulldown length", unit: "s", desc: "How long the pulldown took. A race-plan choice." },
};

// The implemented phases render as real strip sections; each names its inset window (boundary keys).
const SECTIONS = [
  { phase: "start", title: "Dive / Push-off", caption: "Push off, coast, then the first kick.", win: ["dive_start_s", "underwater_start_s"] },
  { phase: "underwater", title: "Underwater", caption: "Speed across the underwater — each bump is a kick.", win: ["underwater_start_s", "stroke_start_s"] },
];

const fmt = (v) => (v == null || !Number.isFinite(v) ? "—" : Number.isInteger(v) ? String(v) : v.toFixed(2));

function valenceText(valence) {
  return valence === "good" ? "text-good" : valence === "bad" ? "text-bad" : valence === "neutral" ? "text-neutral" : "text-subtle";
}

// 0-based strip domain that always contains the value, band, and median with a little headroom.
// Signed metrics (e.g. Kick fade %) are allowed to span below zero. Data-driven rather than the
// mockup's hand-tuned synthetic constants, so a real swim never pushes the today-dot off scale.
function computeDomain(value, base) {
  const pts = [];
  if (Number.isFinite(value)) pts.push(value);
  if (base) {
    if (Number.isFinite(base.median)) pts.push(base.median);
    if (base.band) pts.push(base.band[0], base.band[1]);
  }
  if (!pts.length) return [0, 1];
  let lo = Math.min(0, ...pts);
  let hi = Math.max(...pts);
  if (hi <= lo) hi = lo + 1;
  const pad = (hi - lo) * 0.12;
  hi += pad;
  if (lo < 0) lo -= pad;
  return [lo, hi];
}

// The hover-explain payload for one metric: the plain description, this swim vs usual, and the
// comparison sentence colored by valence. This is the ONLY place the numbers appear.
function metricExplain(disp, value, base, verdict, unit) {
  const median = base?.median;
  const band = base?.band ?? null;
  const v = verdict?.valence;
  let cmp;
  if (!band) {
    cmp = "Not enough past swims yet to set his usual range.";
  } else if (!verdict?.flagged) {
    cmp = `Within his usual range (${fmt(band[0])}–${fmt(band[1])}${unit}).`;
  } else {
    const diff = Math.abs(value - median);
    const dir = value < median ? "below" : "above";
    const tail = v === "good" ? " — better" : v === "bad" ? " — worse" : " — unclear if good or bad";
    cmp = (
      <>
        <span className={valenceText(v)}>
          {fmt(diff)}
          {unit} {dir} usual{tail}
        </span>
        . Outside his {fmt(band[0])}–{fmt(band[1])}
        {unit} range.
      </>
    );
  }
  return {
    title: disp.label,
    tag: verdict?.flagged ? v : null,
    body: (
      <>
        {disp.desc}
        {disp.desc && (
          <>
            <br />
            <br />
          </>
        )}
        This swim{" "}
        <b>
          {fmt(value)}
          {unit}
        </b>
        {median != null && (
          <>
            {" "}
            · usual{" "}
            <b>
              {fmt(median)}
              {unit}
            </b>
          </>
        )}
        .<br />
        {cmp}
      </>
    ),
  };
}

function ComingSoon({ title, note }) {
  return (
    <section className="mb-5 rounded-2xl border border-dashed border-navy/50 bg-surface p-5 shadow-sm">
      <h2 className="font-semibold text-ink">{title}</h2>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">{note}</p>
    </section>
  );
}

export default function PhaseReportCard({ phases, velocity = [], distProfile = [], fsHz = 100, baseline = {}, strokeType, sessionId }) {
  const storageKey = `phaseDismiss:${sessionId}`;
  const [dismissed, setDismissed] = useState(() => new Set());

  // Hydrate the dismissed set from localStorage after mount (never during render — the server has
  // no localStorage and reading it in a lazy initializer would desync hydration). Client-only this
  // slice; server persistence is a documented follow-up (see SUMMARY).
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) setDismissed(new Set(JSON.parse(raw)));
    } catch {
      /* private mode — the count just resets on reload */
    }
  }, [storageKey]);

  const persist = (next) => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify([...next]));
    } catch {
      /* non-fatal */
    }
  };
  const dismiss = (id) =>
    setDismissed((prev) => {
      const n = new Set(prev).add(id);
      persist(n);
      return n;
    });
  const restore = (id) =>
    setDismissed((prev) => {
      const n = new Set(prev);
      n.delete(id);
      persist(n);
      return n;
    });
  const restoreAll = () => {
    persist(new Set());
    setDismissed(new Set());
  };

  const boundaries = phases?.boundaries ?? null;

  // Build the per-section row model once. Each row carries everything RangeStrip needs plus the
  // verdict, so the alert line and timeline can read the same flags without recomputing.
  const model = useMemo(() => {
    const sections = SECTIONS.map((s) => {
      const phaseObj = phases?.[s.phase] ?? {};
      const rows = [];
      for (const [key, m] of Object.entries(phaseObj)) {
        if (key.startsWith("pulldown_") && strokeType !== "breaststroke") continue;
        const disp = DISPLAY[key] ?? { label: m.label, unit: m.unit ?? "", desc: "" };
        const id = `${s.phase}.${key}`;
        const value = m?.value;
        const base = baseline[id];
        const good = directionOfGood(key);
        const verdict = flagVerdict(value, base?.band ?? null, good);
        rows.push({ id, key, phase: s.phase, disp, value, base, verdict });
      }
      return { ...s, rows };
    });
    return sections;
  }, [phases, baseline, strokeType]);

  // Active flags (flagged AND not dismissed) drive both the alert line and the timeline hot phase.
  const activeFlags = useMemo(() => {
    const out = [];
    for (const s of model) {
      for (const r of s.rows) {
        if (r.verdict.flagged && !dismissed.has(r.id)) {
          out.push({
            id: r.id,
            phase: r.phase,
            label: r.disp.label,
            value: r.value,
            median: r.base?.median ?? null,
            unit: r.disp.unit,
            valence: r.verdict.valence,
          });
        }
      }
    }
    return out;
  }, [model, dismissed]);

  const flagsByPhase = useMemo(() => {
    const g = { start: [], underwater: [], swim: [] };
    for (const f of activeFlags) (g[f.phase] ??= []).push(f);
    return g;
  }, [activeFlags]);

  const strokeLabel = STROKE_LABELS[strokeType];
  const baselineNote = strokeLabel
    ? `vs his last ${BASELINE_LIMIT} ${strokeLabel.toLowerCase()} swims`
    : `vs his last ${BASELINE_LIMIT} swims`;

  const idxOf = (tS) => (tS == null || !(fsHz > 0) ? null : Math.round(tS * fsHz));

  return (
    <HoverExplainProvider>
      {/* legend — teaches the whole visual language once, so the rows need no words */}
      <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-navy/50 bg-surface px-3.5 py-2.5 text-[11.5px] text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-5 rounded bg-usual" /> his usual range
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-subtle ring-2 ring-usual" /> this swim
        </span>
        <span className="h-3.5 w-px bg-navy/60" />
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-good" /> better
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-bad" /> worse
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-neutral" /> changed — unclear if good/bad
        </span>
        <span className="h-3.5 w-px bg-navy/60" />
        <span>
          hover any <span className="border-b border-dotted border-muted">dotted</span> label for the numbers
        </span>
      </div>

      <AlertSummary flags={activeFlags} dismissedCount={dismissed.size} onRestore={restoreAll} baselineNote={baselineNote} />

      <PhaseTimeline boundaries={boundaries} distProfile={distProfile} velocity={velocity} fsHz={fsHz} flagsByPhase={flagsByPhase} />

      {/* Velocity timeline — the hero, phase-tinted */}
      <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
        <h2 className="mb-3.5 font-semibold text-ink">
          Velocity timeline
          <span className="ml-2 text-[11.5px] font-normal text-muted">speed across the whole swim</span>
        </h2>
        <PhaseVelocity variant="hero" velocity={velocity} fsHz={fsHz} boundaries={boundaries} />
      </section>

      {/* one section per implemented phase: inset chart on top, then metrics in two columns */}
      {model.map((s) => {
        const i0 = idxOf(boundaries?.[s.win[0]]);
        const i1 = idxOf(boundaries?.[s.win[1]]);
        const showInset = i0 != null && i1 != null && i1 > i0;
        return (
          <section key={s.phase} className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
            <h2 className="mb-3.5 font-semibold text-ink">{s.title}</h2>
            {showInset && (
              <div className="mb-4 rounded-xl border border-navy/50 bg-surface-2 px-3.5 py-3">
                <PhaseVelocity variant="inset" velocity={velocity} fsHz={fsHz} window={[i0, i1]} />
                <p className="mt-2 px-0.5 text-[11.5px] text-muted">{s.caption}</p>
              </div>
            )}
            <div className="grid grid-cols-1 gap-x-6 sm:grid-cols-2">
              {s.rows.map((r) => (
                <RangeStrip
                  key={r.id}
                  label={r.disp.label}
                  unit={r.disp.unit}
                  value={r.value}
                  baseline={r.base}
                  domain={computeDomain(r.value, r.base)}
                  verdict={r.verdict}
                  dismissed={dismissed.has(r.id)}
                  onDismiss={() => dismiss(r.id)}
                  onRestore={() => restore(r.id)}
                  emptyNote={r.disp.emptyNote}
                  explain={metricExplain(r.disp, r.value, r.base, r.verdict, r.disp.unit)}
                />
              ))}
            </div>
          </section>
        );
      })}

      <ComingSoon title="Swimming" note="Stroke-phase metrics — breakout speed, cruise, intracyclic variation, splits — are coming soon." />
      <ComingSoon title="Whole race" note="Cross-phase metrics — phase time/distance budget, velocity envelope, whole-swim smoothness — are coming soon." />
    </HoverExplainProvider>
  );
}
