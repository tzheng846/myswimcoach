"use client";

// PhaseReportCard — the body of the primary session report (Phase 75-07; the phase model was built
// beside the classic card in 75-05 and became the page itself in 75-07). Reads the stored
// `metrics_json.phases` object plus the athlete's last-5 same-stroke baseline, and renders: the
// deterministic valence-broken-down alert line, the phase timeline, then `middleSlot` (the page's
// velocity / Time-to-Distance / video cards, threaded in the merged order), then one section per
// phase — inset chart on top, metrics in two columns, each a 1D usual-range strip colored by
// direction-of-good. Every description + comparison lives in the hover-explain overlay; nothing here
// asserts a verdict in prose. Legacy sessions with no `phases` show an empty state but still render
// the universal middleSlot + per-cycle. The interim velocity hero and the standalone legend were
// retired in the merge (unified trace = 75-09).
//
// Phase 75-06 completed the four sections: Swimming gained the registry strips ABOVE its per-cycle
// charts, and Whole race replaced its coming-soon stub. Two things arrived with them — the hover
// overlay now says where each phase window came from (`boundaries.sources`), and metrics derived
// from AUTO stroke cycles render with valence suppressed so a provisional number never looks
// confident. Both are hover-only; the card gained no standing chrome.

import { useEffect, useMemo, useState } from "react";
import { flagVerdict, directionOfGood } from "@/lib/phaseValence";
import { BASELINE_LIMIT } from "@/lib/phaseBaseline";
import { buildBands } from "@/lib/cycleBands";
import { deriveMeans, armBalance } from "@/lib/strokeStats";
import { STROKE_LABELS } from "@/components/portal/SessionCard";
import CycleCharts from "@/components/portal/CycleCharts";
import { HoverExplainProvider } from "./HoverExplain";
import RangeStrip from "./RangeStrip";
import PhaseVelocity from "./PhaseVelocity";
import CycleOverlay from "./CycleOverlay";
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
  // Swim (Phase 75-06)
  ivv: { label: "Speed wobble", unit: "", desc: "How much his speed rose and fell across the swim. Lower is smoother (better)." },
  breakout_vel: { label: "Breakout speed", unit: "m/s", desc: "Speed over the first half-second of surface swimming. Higher is better." },
  breakout_vel_loss: { label: "Speed lost surfacing", unit: "m/s", desc: "Speed given up between the underwater and the first strokes. Lower is better." },
  breakout_vs_steady: { label: "Breakout vs cruise", unit: "×", desc: "Breakout speed against the speed he settled into. Above 1× means he came out hot — whether that's right is a race-plan call." },
  splits_5m: { label: "Split 0–5 m", unit: "m/s", desc: "Average speed over the first 5 m from the dive — mostly start and underwater. Higher is better." },
  splits_10m: { label: "Split 5–10 m", unit: "m/s", desc: "Average speed across the second 5 m. Higher is better." },
  splits_15m: { label: "Split 10–15 m", unit: "m/s", desc: "Average speed across the third 5 m. Higher is better." },
  splits_20m: { label: "Split 15–20 m", unit: "m/s", desc: "Average speed across the fourth 5 m. Higher is better." },
  // The tether is on the waist, so a 25-yard lap (22.86 m) records only ~21.9 m of travel — the
  // missing metre is his arm plus torso at the touch. This split is therefore blank on any
  // 25-yard swim by geometry, not by failure, and the note says so rather than showing a bare dash.
  splits_25m: { label: "Split 20–25 m", unit: "m/s", desc: "Average speed across the fifth 5 m. Higher is better. The tether sits on his waist, so a 25-yard lap only records about 21.9 m — this split fills on longer swims.", emptyNote: "beyond this swim's distance" },
  accel_asymmetry: { label: "Speeding up vs slowing", unit: "×", desc: "Time spent accelerating against time spent decelerating. Near 1× is balanced; which way is better depends on the stroke." },
  sr_dps_coupling: { label: "Tempo vs distance", unit: "", desc: "Whether quicker strokes cost him distance. Strongly negative means tempo is being bought with reach — a coaching call, not a fault." },
  dead_spot_timing: { label: "Dead spot", unit: "s", desc: "How far into each stroke his speed bottoms out. Where it sits is a technique read rather than better or worse." },
  // Whole race (Phase 75-06)
  phase_time_budget_start: { label: "Start — time share", unit: "%", desc: "Share of the race spent on the start. How the budget should split is a race-plan call." },
  phase_time_budget_underwater: { label: "Underwater — time share", unit: "%", desc: "Share of the race spent underwater. A race-plan call." },
  phase_time_budget_swim: { label: "Swimming — time share", unit: "%", desc: "Share of the race spent surface swimming. A race-plan call." },
  phase_dist_budget_start: { label: "Start — distance share", unit: "%", desc: "Share of the distance covered on the start. A race-plan call." },
  phase_dist_budget_underwater: { label: "Underwater — distance share", unit: "%", desc: "Share of the distance covered underwater. A race-plan call." },
  phase_dist_budget_swim: { label: "Swimming — distance share", unit: "%", desc: "Share of the distance covered surface swimming. A race-plan call." },
  vel_envelope_start: { label: "Peak speed — start", unit: "m/s", desc: "Fastest instant during the start. Higher is better." },
  vel_envelope_underwater: { label: "Peak speed — underwater", unit: "m/s", desc: "Fastest instant underwater. Higher is better." },
  vel_envelope_swim: { label: "Peak speed — swimming", unit: "m/s", desc: "Fastest instant while swimming. Higher is better." },
  vel_envelope_overall: { label: "Peak speed — whole race", unit: "m/s", desc: "Fastest instant anywhere in the swim. Higher is better." },
  jerk_smoothness: { label: "Stroke smoothness", unit: "m/s³", desc: "How abruptly his speed changed across the swim. Lower is smoother (better). This one is noise-sensitive — read it against his own past swims, never as an absolute number." },
};

// The implemented phases render as real strip sections; each names its inset window (boundary keys).
// `whole` has no window of its own, so it insets the ENTIRE race (dive to finish) — which keeps it
// consistent with the other three panels rather than special-casing it out of the layout (75-06 D5).
// `cycleCharts` marks the section that also carries the per-cycle line charts, beneath its strips.
const SECTIONS = [
  { phase: "start", title: "Dive / Push-off", caption: "Push off, coast, then the first kick.", win: ["dive_start_s", "underwater_start_s"] },
  { phase: "underwater", title: "Underwater", caption: "Speed across the underwater — each bump is a kick.", win: ["underwater_start_s", "stroke_start_s"] },
  { phase: "swim", title: "Swimming", note: "stroke-by-stroke", caption: "Speed across the surface swim — each bump is a stroke.", win: ["stroke_start_s", "finish_s"], cycleCharts: true },
  { phase: "whole", title: "Whole race", caption: "The complete swim, dive to finish.", win: ["dive_start_s", "finish_s"] },
];

// The Swimming inset's window, read off the section model rather than restated, so the bands can
// never be built against a different window than the chart they are drawn on (83-01).
const SWIM_WIN = SECTIONS.find((s) => s.phase === "swim").win;
const UW_WIN = SECTIONS.find((s) => s.phase === "underwater").win;

// Where a phase's window came from, for the hover overlay (75-06 D3). `boundaries.sources` has been
// stored since 75-02 but was never surfaced, so a coach could not tell a hand-marked window from a
// detected one. Hover-only by design — the v3 language keeps standing chrome off the card.
function windowSourceNote(boundaries, win) {
  const src = boundaries?.sources ?? {};
  const vals = win.map((k) => src[k]).filter(Boolean);
  if (!vals.length) return null;
  if (vals.every((v) => v === "manual")) return "Window taken from your marks on the annotate page.";
  if (vals.some((v) => v === "manual")) return "Window partly from your marks, partly auto-detected.";
  return "Window auto-detected — this session has no coach marks.";
}

// Shown on the two per-cycle metrics whenever the stroke cycles behind them were found by the
// segmenter rather than marked by a coach. Their valence is also forced neutral in that case, so a
// provisional number can never render as a confident green or red.
const PROVISIONAL_NOTE =
  "Based on auto-detected stroke cycles, which miscount more often than they mistime. Annotate this session to make it exact.";

// seconds → sample index at THIS session's rate (never assume 100 Hz). Module-level so the band
// memo can call it without taking a new closure as a dependency on every render.
const toIdx = (tS, fsHz) => (tS == null || !(fsHz > 0) ? null : Math.round(tS * fsHz));

// Global, not per-session (87-02 D2).
const GRANULARITY_KEY = "swimnetics.swimGranularity";

const fmt = (v) => (v == null || !Number.isFinite(v) ? "—" : Number.isInteger(v) ? String(v) : v.toFixed(2));

// The hovered band's own stored numbers (83-01 AC-3) — read off `metrics_json.cycles`, never
// recomputed from the trace, so the readout and the four charts below can never disagree.
function cycleReadout(c, n, unit, noun = "Cycle") {
  const imp = unit === "imperial";
  const k = imp ? 1.09361 : 1;
  const d = (v) => (Number.isFinite(v) ? (v * k).toFixed(2) : "—");
  return `${noun} ${n} · ${fmt(c.duration_s)} s · ${d(c.dist_m)} ${imp ? "yd" : "m"}/stroke · peak ${d(
    c.arm_peak_vel
  )} ${imp ? "yd/s" : "m/s"}`;
}

// The A/B definition (87-01 D3), and the scope statement 87-01 D4 makes necessary. Both are always
// visible in stroke mode: the readout is unreadable without the first, and a coach who has just
// switched the whole section to strokes would otherwise reasonably read the usual-range bands below
// as stroke-level. Neither is a warning — 87-01 D2 shipped the auto-path number marked only by the
// existing `auto` chip, and softening that with chrome the user declined is not this plan's call.
const AB_DEFINITION =
  "A and B are the two alternating arms — a single-axis encoder cannot tell which is left.";
const STRIP_SCOPE_NOTE = "Usual-range comparisons below stay per cycle.";

const pctFmt = (v) => (Number.isFinite(v) ? `${Math.abs(v).toFixed(1)}% apart` : "—");
const cvFmt = (v) => (Number.isFinite(v) ? `${(v * 100).toFixed(0)}%` : "—");

// The two side tokens, written as the same real `var(--color-…)` strings the bands and the pack
// use, so the chip that NAMES a side is painted by the colour that DRAWS it (AC-4).
const SIDE_COLOR = { A: "var(--color-cycle-a)", B: "var(--color-cycle-b)" };

// The breakout band (83-03) has no row in `metrics_json.cycles` — it is the span between the coach's
// streamline-break mark and their first stroke mark, so the only number it owns is its own length.
// Saying what it spans is what keeps it from reading as a mystery gold stripe.
function breakoutReadout(band) {
  return `Breakout · ${fmt(band.duration)} s · streamline break to his first stroke mark`;
}

// The hovered kick band's numbers (83-02). Peak velocity is read off the trace at the band's stored
// `peak_idx` rather than persisted separately, and there is no per-kick distance to show — so this is
// three fields where cycleReadout has four, not the same function with a blank.
function kickReadout(row, n, unit, velocity) {
  const imp = unit === "imperial";
  const pv = velocity?.[row?.peak_idx];
  const v = Number.isFinite(pv) ? (pv * (imp ? 1.09361 : 1)).toFixed(2) : "—";
  return `Kick ${n} · ${fmt(row.duration_s)} s · peak ${v} ${imp ? "yd/s" : "m/s"}`;
}

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
function metricExplain(disp, value, base, verdict, unit, notes = []) {
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
        {notes.filter(Boolean).map((n, i) => (
          <span key={i} className="mt-2 block text-subtle">
            {n}
          </span>
        ))}
      </>
    ),
  };
}

// Arm balance (87-02) — the three signed asymmetry percentages and the four per-side CVs that
// 87-01 stored, rendered and never recomputed. States magnitude and direction and passes NO verdict:
// no "even" threshold, no good/bad colour, no flag, no dismiss control. 83-03 is the precedent for
// not shipping an unmeasured cutoff, and there is no usual-range baseline for these seven keys.
//
// ⚠ UNIT-INVARIANT. Asymmetry is a percentage and the four CVs are ratios, so `unit` is deliberately
// not threaded in here — nothing in this block may ever be multiplied by 1.09361.
function ArmBalance({ session }) {
  const model = armBalance(session);
  return (
    <div className="mb-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">Arm balance</p>
      {model ? (
        <>
          <div className="grid gap-1.5 sm:grid-cols-3">
            {model.rows.map((r) => (
              <div key={r.key} className="rounded-lg border border-navy/50 bg-surface-2 px-3 py-2">
                <p className="text-[11px] text-muted">{r.label}</p>
                <p className="mt-0.5 font-mono text-sm tabular-nums text-ink">{pctFmt(r.pct)}</p>
                <p className="mt-0.5 flex items-center gap-1.5 text-[11.5px] text-subtle">
                  <span
                    aria-hidden="true"
                    className="inline-block h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: SIDE_COLOR[r.leader] }}
                  />
                  {r.phrase}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-2 space-y-0.5">
            {model.cvs.map((c) => (
              <p key={c.label} className="text-[11.5px] text-muted">
                {c.label} — <span className="font-mono tabular-nums">A {cvFmt(c.a)}</span> ·{" "}
                <span className="font-mono tabular-nums">B {cvFmt(c.b)}</span>
              </p>
            ))}
          </div>
        </>
      ) : (
        <p className="text-[11.5px] leading-relaxed text-muted">
          Not enough strokes on each side to compare the two arms on this swim.
        </p>
      )}
      <p className="mt-2 text-[11px] leading-relaxed text-subtle">{AB_DEFINITION}</p>
      <p className="text-[11px] leading-relaxed text-subtle">{STRIP_SCOPE_NOTE}</p>
    </div>
  );
}

export default function PhaseReportCard({
  phases,
  velocity = [],
  distProfile = [],
  fsHz = 100,
  baseline = {},
  strokeType,
  sessionId,
  middleSlot = null, // page-owned velocity / Time-to-Distance / video cards, threaded after the timeline
  cycles, // per-cycle rows for the Swimming section
  // Phase 87-02 — `metrics_json.strokes`, the single-arm half-cycles. null for butterfly /
  // breaststroke / im / udk and absent on every session predating 87-01's backfill, which is what
  // makes `hasStrokes` the gate for the entire strokes mode rather than a stroke-type check here.
  strokes = null,
  session, // metrics_json.session — CycleCharts means/CVs
  // data_quality.segmentation_reliable, passed EXPLICITLY by the page (83-01 AC-2). It flips true
  // only when metrics were recomputed from a coach's marks, so it is the one honest source for the
  // band badge's annotated-vs-auto — never infer provenance from an annotation row existing.
  segmentationReliable = false,
  unit = "metric",
}) {
  const storageKey = `phaseDismiss:${sessionId}`;
  const [dismissed, setDismissed] = useState(() => new Set());

  // Swimming-section granularity (87-02). Local to this card and deliberately NOT lifted into
  // `useTracePrefs`: that hook is page-owned and shared with the /video route so trace colours stay
  // in step across surfaces, and granularity has no meaning there. Persisted GLOBALLY rather than
  // per-session — a coach who thinks in strokes should stay in strokes on the next swim.
  const [granularity, setGranularity] = useState("cycle");
  const hasStrokes = Array.isArray(strokes) && strokes.length > 0;
  // The effective mode. A session with no strokes renders exactly today's card even with "stroke"
  // stored, and that fallback is NEVER written back — opening a butterfly swim must not silently
  // reset the preference.
  const mode = hasStrokes ? granularity : "cycle";
  const strokeMode = mode === "stroke";
  const itemLabel = strokeMode ? "stroke" : "cycle";
  const swimItems = strokeMode ? strokes : cycles;

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

  // Same rule as above: read localStorage in an effect, never in a lazy initializer — the server
  // has none and reading it during render desyncs hydration.
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(GRANULARITY_KEY);
      if (raw === "stroke" || raw === "cycle") setGranularity(raw);
    } catch {
      /* private mode — the card just opens on cycles */
    }
  }, []);

  const chooseGranularity = (next) => {
    setGranularity(next);
    // The two keyspaces must never mix: cycle 3 pinned and cycle 5 hovered say nothing about
    // strokes 3 and 5 (AC-7). Cleared HERE rather than in an effect on `mode` — this is the only
    // way the mode ever changes under a coach's hand, and an effect would be a cascading render.
    // The kick hover/pin is a separate keyspace and stays put.
    setHoverCycle(null);
    setPinnedCycle(null);
    try {
      window.localStorage.setItem(GRANULARITY_KEY, next);
    } catch {
      /* non-fatal */
    }
  };

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

  const idxOf = (tS) => toIdx(tS, fsHz);

  // Build the per-section row model once. Each row carries everything RangeStrip needs plus the
  // verdict, so the alert line and timeline can read the same flags without recomputing.
  const model = useMemo(() => {
    const sections = SECTIONS.map((s) => {
      const phaseObj = phases?.[s.phase] ?? {};
      const sourceNote = windowSourceNote(phases?.boundaries, s.win);
      const rows = [];
      for (const [key, m] of Object.entries(phaseObj)) {
        if (key.startsWith("pulldown_") && strokeType !== "breaststroke") continue;
        const disp = DISPLAY[key] ?? { label: m.label, unit: m.unit ?? "", desc: "" };
        const id = `${s.phase}.${key}`;
        const value = m?.value;
        const base = baseline[id];
        const good = directionOfGood(key);
        // A provisional metric (auto stroke cycles, 75-06 D8) is still FLAGGED when it moves
        // outside his usual range — the coach should see that it moved — but it is never
        // colored good/bad, because the number it moved from may itself be a miscount.
        const provisional = m?.provisional === true;
        const verdict = flagVerdict(value, base?.band ?? null, provisional ? "neutral" : good);
        const notes = [sourceNote, provisional ? PROVISIONAL_NOTE : null];
        rows.push({ id, key, phase: s.phase, disp, value, base, verdict, provisional, notes });
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

  // `whole` flags count toward the alert line like any other, but they describe the race as a
  // whole and so map to no single timeline segment — PhaseTimeline simply never reads that key.
  const flagsByPhase = useMemo(() => {
    const g = { start: [], underwater: [], swim: [], whole: [] };
    for (const f of activeFlags) (g[f.phase] ??= []).push(f);
    return g;
  }, [activeFlags]);

  // Per-cycle bands for the Swimming inset (83-01). Annotation-first needs no precedence code here:
  // `PUT /annotations` replaces `metrics_json.cycles` with the coach's own, so reading the stored
  // array IS the precedence — `segmentationReliable` only says which one arrived.
  //
  // 83-03 gilds the breakout, but ONLY on coach-marked cycles. Measured across the library: on the
  // 43 annotated sessions cycle 1 starts a median 1.04 s after `stroke_start_s` and never before it,
  // so the gold genuinely spans the breakout pull. On auto-segmented sessions 28 of 47 have cycle 1
  // starting BEFORE the breakout (worst −12.9 s), where the same gold would be a lie.
  const swimBands = useMemo(
    () =>
      buildBands(swimItems, {
        fsHz,
        i0: toIdx(boundaries?.[SWIM_WIN[0]], fsHz),
        i1: toIdx(boundaries?.[SWIM_WIN[1]], fsHz),
        numberKey: strokeMode ? "stroke_num" : "cycle_num",
        // Unchanged by the mode. In stroke mode the gold band's semantics only get BETTER: the
        // breakout genuinely is one stroke sitting among strokes rather than among cycles.
        breakoutFirst: segmentationReliable,
      }),
    [swimItems, strokeMode, fsHz, boundaries, segmentationReliable]
  );

  // One hover, two surfaces: the inset band and the point in all four CycleCharts panels. Lifted
  // here because neither child may own it (83 D8); both get it as a plain optional prop.
  const [hoverCycle, setHoverCycle] = useState(null);
  // 83-05 D9: a pin is a SECOND, longer-lived channel. `setHoverCycle` still only ever writes the
  // hover half, so a mouseleave clears the preview and leaves the pin standing.
  const [pinnedCycle, setPinnedCycle] = useState(null);
  const numberKey = strokeMode ? "stroke_num" : "cycle_num";
  const hoverRow = useMemo(() => {
    if (hoverCycle == null || !swimItems?.length) return null;
    return (
      swimItems.find((c, i) => (Number.isFinite(c?.[numberKey]) ? c[numberKey] + 1 : i + 1) === hoverCycle) ?? null
    );
  }, [swimItems, numberKey, hoverCycle]);
  // The badge counts CYCLES (or strokes), so it must exclude the synthetic breakout band — it is a stroke, but
  // it is not one of the coach's marked cycles and the four charts below have no row for it.
  const swimCycleCount = useMemo(() => swimBands.filter((b) => !b.isBreakout).length, [swimBands]);

  const hoverBand = useMemo(
    () => (hoverCycle == null ? null : swimBands.find((b) => b.n === hoverCycle) ?? null),
    [swimBands, hoverCycle]
  );

  // Per-kick bands for the Underwater inset (83-02). Unlike cycles these are derived, not stored
  // segmentation: `phases.kick_bands` is emitted by compute_phases, so it is re-derived with the
  // boundaries and rides the same schema_version. Already [] for breaststroke and for sessions
  // stored before schema 4, so no gate is needed here. `duration_s` means buildBands' DEFAULT
  // durationKey applies — the 83-01 lib is reused with zero configuration.
  const kickSource = phases?.kick_bands;
  const kickBands = useMemo(
    () =>
      buildBands(kickSource, {
        fsHz,
        i0: toIdx(boundaries?.[UW_WIN[0]], fsHz),
        i1: toIdx(boundaries?.[UW_WIN[1]], fsHz),
      }),
    [kickSource, fsHz, boundaries]
  );

  // Its OWN hover state, deliberately not shared with hoverCycle: the two insets must not highlight
  // each other, and there is no CycleCharts partner under Underwater, so this stays inset-local.
  const [hoverKick, setHoverKick] = useState(null);
  const [pinnedKick, setPinnedKick] = useState(null);
  const hoverKickRow = useMemo(() => {
    // Kick bands carry `kick_num`, not `cycle_num`, so buildBands numbers them by array position
    // (+1) — which makes n-1 an index straight back into the stored array.
    if (hoverKick == null) return null;
    return kickSource?.[hoverKick - 1] ?? null;
  }, [kickSource, hoverKick]);

  // The one resolution rule (83-05 D9). Hover PREVIEWS over a pin without clearing it; releasing
  // the hover falls back to whatever is pinned. Everything that highlights reads this, never the
  // raw hover — except the inset's readout line, which stays hover-only so a pin does not park a
  // caption over the section's own copy.
  const activeCycle = hoverCycle ?? pinnedCycle;
  const activeKick = hoverKick ?? pinnedKick;

  const strokeLabel = STROKE_LABELS[strokeType];
  const baselineNote = strokeLabel
    ? `vs his last ${BASELINE_LIMIT} ${strokeLabel.toLowerCase()} swims`
    : `vs his last ${BASELINE_LIMIT} swims`;

  return (
    <HoverExplainProvider>
      {phases ? (
        <>
          <AlertSummary flags={activeFlags} dismissedCount={dismissed.size} onRestore={restoreAll} baselineNote={baselineNote} />
          <PhaseTimeline boundaries={boundaries} distProfile={distProfile} velocity={velocity} fsHz={fsHz} flagsByPhase={flagsByPhase} />
        </>
      ) : (
        <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-6 text-center shadow-sm">
          <p className="font-semibold text-ink">No race-phase breakdown yet</p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            This session predates the phase model — re-run its analysis to generate the phase report.
            The velocity, splits, per-cycle, and video below still apply.
          </p>
        </section>
      )}

      {/* Universal, non-phase cards (velocity / Time-to-Distance / video) — page-owned, threaded
          between the timeline and the phase strip sections in the merged order. */}
      {middleSlot}

      {/* one section per implemented phase: inset chart on top, then metrics in two columns */}
      {phases &&
        model.map((s) => {
        const i0 = idxOf(boundaries?.[s.win[0]]);
        const i1 = idxOf(boundaries?.[s.win[1]]);
        const showInset = i0 != null && i1 != null && i1 > i0;
        // Underwater is the second band consumer (83-02). Breaststroke's underwater is the
        // pulldown, not dolphin kicks, so it stays single-colour — the backend already emits []
        // there, which makes this the label rather than the gate.
        const isUW = s.phase === "underwater";
        const isPulldown = isUW && strokeType === "breaststroke";
        return (
          <section key={s.phase} className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
            <h2
              className={`mb-3.5 font-semibold text-ink${
                s.cycleCharts && hasStrokes ? " flex items-center justify-between gap-3" : ""
              }`}
            >
              {s.cycleCharts && hasStrokes ? (
                <>
                  <span>
                    {s.title}
                    <span className="ml-2 text-[11.5px] font-normal text-muted">
                      {strokeMode ? "arm-by-arm" : s.note}
                    </span>
                  </span>
                  {/* Same control styling as CycleOverlay's own x-axis toggle, so the card does not
                      grow a second visual language for the same gesture. */}
                  <span
                    className="flex shrink-0 overflow-hidden rounded-md border border-navy/60"
                    role="group"
                    aria-label="Swimming detail granularity"
                  >
                    {[
                      ["cycle", "cycles"],
                      ["stroke", "strokes"],
                    ].map(([key, text]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => chooseGranularity(key)}
                        aria-pressed={mode === key}
                        className={`px-2 py-0.5 text-[10.5px] font-medium transition-colors ${
                          mode === key ? "bg-navy/60 text-ink" : "text-muted hover:text-subtle"
                        }`}
                      >
                        {text}
                      </button>
                    ))}
                  </span>
                </>
              ) : (
                <>
                  {s.title}
                  {s.note && <span className="ml-2 text-[11.5px] font-normal text-muted">{s.note}</span>}
                </>
              )}
            </h2>
            {showInset && (
              <div className="mb-4 rounded-xl border border-navy/50 bg-surface-2 px-3.5 py-3">
                <PhaseVelocity
                  variant="inset"
                  velocity={velocity}
                  fsHz={fsHz}
                  window={[i0, i1]}
                  {...(s.cycleCharts && swimBands.length
                    ? { bands: swimBands, highlightN: activeCycle, onHoverBand: setHoverCycle, itemLabel }
                    : isUW && kickBands.length
                    ? { bands: kickBands, highlightN: activeKick, onHoverBand: setHoverKick }
                    : null)}
                />
                {/* The hover readout REPLACES the caption rather than sitting under it: the four
                    charts below highlight on the same hover, and a line appearing here would shove
                    them down mid-gesture. */}
                <div className="mt-2 flex items-baseline justify-between gap-3 px-0.5">
                  <p className="text-[11.5px] text-muted">
                    {hoverBand?.isBreakout && s.cycleCharts
                      ? breakoutReadout(hoverBand)
                      : hoverRow && s.cycleCharts
                      ? cycleReadout(hoverRow, hoverCycle, unit, strokeMode ? "Stroke" : "Cycle")
                      : hoverKickRow && isUW
                      ? kickReadout(hoverKickRow, hoverKick, unit, velocity)
                      : s.caption}
                  </p>
                  {s.cycleCharts && swimCycleCount > 0 && (
                    <p className="shrink-0 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                      {swimCycleCount} {swimCycleCount === 1 ? itemLabel : `${itemLabel}s`} ·{" "}
                      {segmentationReliable ? "annotated" : "auto"}
                    </p>
                  )}
                  {/* No reliability half: kicks are auto-only until 81-02 ships a coach
                      kick-marking path, so reading segmentationReliable here would claim a
                      provenance that does not exist yet. */}
                  {isPulldown ? (
                    <p className="shrink-0 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                      pulldown · not kicks
                    </p>
                  ) : (
                    isUW &&
                    kickBands.length > 0 && (
                      <p className="shrink-0 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                        {kickBands.length} {kickBands.length === 1 ? "kick" : "kicks"} · auto
                      </p>
                    )
                  )}
                </div>
                {/* 83-05: the overlay lives INSIDE the same bordered box, below the inset and its
                    badge row (D2) — it is the same picture read a second way, not a new section.
                    Both panels self-gate: CycleOverlay returns null below two drawable traces, so
                    breaststroke (whose kick_bands the backend already emits as []) needs no gate
                    here, and neither does a session with a single cycle. */}
                {s.cycleCharts && (
                  <CycleOverlay
                    items={swimItems}
                    velocity={velocity}
                    fsHz={fsHz}
                    window={[i0, i1]}
                    label={itemLabel}
                    numberKey={numberKey}
                    colorByParity={strokeMode}
                    activeN={activeCycle}
                    onHoverN={setHoverCycle}
                    pinnedN={pinnedCycle}
                    onPinN={setPinnedCycle}
                    excludeBreakout={swimBands.some((b) => b.isBreakout)}
                  />
                )}
                {/* ⚠ Kick bands TILE their window (STATE item 18): band 1 is the push-off glide and
                    band N the breakout transition, not kicks. So ~2 of ~5 underwater traces will
                    always sit outside the pack for a reason that has nothing to do with the swimmer.
                    83-05 D8 ships this KNOWINGLY — no filter, no heuristic here. The fix is upstream
                    in `segment_kick_bands` and costs a SCHEMA_VERSION bump plus a backfill. */}
                {isUW && (
                  <CycleOverlay
                    items={kickSource}
                    velocity={velocity}
                    fsHz={fsHz}
                    window={[i0, i1]}
                    label="kick"
                    activeN={activeKick}
                    onHoverN={setHoverKick}
                    pinnedN={pinnedKick}
                    onPinN={setPinnedKick}
                  />
                )}
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
                  explain={metricExplain(r.disp, r.value, r.base, r.verdict, r.disp.unit, r.notes)}
                />
              ))}
            </div>
            {/* Per-cycle line charts sit BENEATH the Swimming section's strips (75-06 D10): the
                registry metrics are the phase model's content, the charts are the detail under it. */}
            {s.cycleCharts && (
              <div className="mt-5 border-t border-navy/40 pt-4">
                {strokeMode && <ArmBalance session={session} />}
                {swimItems?.length ? (
                  <CycleCharts
                    cycles={swimItems}
                    /* Stroke-level means, re-derived from the plotted items — the stored
                       session.mean_* keys are CYCLE-level and a cycle is two strokes, so the dashed
                       reference line would sit clean off the top of the dots (87-02 D4). Not merged
                       with `session`: one leftover cycle-level key under stroke dots is exactly the
                       failure this guards. */
                    session={strokeMode ? deriveMeans(strokes) : session}
                    unit={unit}
                    itemLabel={itemLabel}
                    highlightN={activeCycle}
                    onHoverN={setHoverCycle}
                  />
                ) : (
                  <p className="text-sm leading-relaxed text-muted">No stroke cycles detected for this swim.</p>
                )}
              </div>
            )}
          </section>
        );
      })}

      {/* Legacy sessions carry no `phases`, so the section loop above never runs — the per-cycle
          charts are still theirs to show, and were the whole Swimming section before 75-06. */}
      {!phases && (
        <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
          <h2 className="mb-3.5 font-semibold text-ink">
            Swimming
            <span className="ml-2 text-[11.5px] font-normal text-muted">stroke-by-stroke</span>
          </h2>
          {cycles?.length ? (
            <CycleCharts cycles={cycles} session={session} unit={unit} />
          ) : (
            <p className="text-sm leading-relaxed text-muted">No stroke cycles detected for this swim.</p>
          )}
        </section>
      )}
    </HoverExplainProvider>
  );
}
