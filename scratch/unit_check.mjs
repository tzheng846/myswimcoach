// Phase 88-03 RENDER check — the yd/m toggle actually converting the phase-metric grid.
//
// Same harness shape as scratch/stroke_toggle_check.mjs (87-02): transpile the JSX with the
// `typescript` package already in web/node_modules, drop the CJS output inside node_modules so
// `react` resolves by the normal walk-up, render with react-dom/server, assert on the markup.
//
// ⚠ ONE NEW HARNESS TRICK, beyond what 87-02 needed: `RangeStrip`'s hover-explain sentence and
// `PhaseTimeline`'s flag-list body are both passed to `ExplainTrigger` as the `title`/`body` props,
// and `ExplainTrigger` (web/components/portal/phases/HoverExplain.js) NEVER renders them into the
// DOM directly — it only hands them to context's `show()` on a real mouse/focus event, which
// `renderToStaticMarkup` never fires. So AC-3 and AC-4 (both about that hover text) are unreachable
// through the real component. `HoverExplainStub.cjs` below replaces `./HoverExplain` for this
// harness ONLY (production source untouched) with a version that still renders `children` (the
// visible trigger) but ALSO dumps `title`/`body` into a hidden sibling div, so the sentence text
// becomes assertable. This is the same kind of harness-only substitution `sessionCardStub.cjs`
// already does for `SessionCard`.
//
// ⚠ MEASURED LIMITATION inherited from 87-02: recharts renders an EMPTY wrapper under
// renderToStaticMarkup, so CycleCharts (which already converts, out of this plan's scope) is not
// assertable here.
//
// Run: node scratch/unit_check.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, "..", "web");
const require = createRequire(path.join(web, "package.json"));
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

const out = path.join(web, "node_modules", ".render-check");
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

let pass = 0;
let fail = 0;
const check = (name, ok, extra = "") => {
  if (ok) {
    pass++;
    console.log(`  PASS  ${name}${extra ? "  " + extra : ""}`);
  } else {
    fail++;
    console.log(`  FAIL  ${name}${extra ? "  " + extra : ""}`);
  }
};

const MAP = {
  "@/lib/phaseValence": "./phaseValence.cjs",
  "@/lib/phaseBaseline": "./phaseBaseline.cjs",
  "@/lib/cycleBands": "./cycleBands.cjs",
  "@/lib/cycleTraces": "./cycleTraces.cjs",
  "@/lib/strokeStats": "./strokeStats.cjs",
  "@/lib/unitConvert": "./unitConvert.cjs",
  "./cycleShape": "./cycleShape.cjs",
  "@/components/portal/SessionCard": "./sessionCardStub.cjs",
  "@/components/portal/CycleCharts": "./CycleCharts.cjs",
  "./HoverExplain": "./HoverExplainStub.cjs", // see header — swaps the whole module for this harness
  "./RangeStrip": "./RangeStrip.cjs",
  "./PhaseVelocity": "./PhaseVelocity.cjs",
  "./CycleOverlay": "./CycleOverlay.cjs",
  "./PhaseTimeline": "./PhaseTimeline.cjs",
  "./AlertSummary": "./AlertSummary.cjs",
};

const compile = (src, name) => {
  let code = fs.readFileSync(src, "utf8");
  for (const [from, to] of Object.entries(MAP)) code = code.split(`"${from}"`).join(`"${to}"`);
  const js = ts.transpileModule(code, {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    fileName: name,
  }).outputText;
  fs.writeFileSync(path.join(out, name.replace(/\.js$/, ".cjs")), js);
};

fs.writeFileSync(
  path.join(out, "sessionCardStub.cjs"),
  "exports.STROKE_LABELS={freestyle:'Freestyle',backstroke:'Backstroke',butterfly:'Butterfly',breaststroke:'Breaststroke'};\n"
);

fs.writeFileSync(
  path.join(out, "HoverExplainStub.cjs"),
  `const React = require("react");
exports.HoverExplainProvider = ({ children }) => children;
exports.ExplainTrigger = ({ title, tag, body, as, className, style, children }) =>
  React.createElement(
    as || "span",
    { className, style },
    children,
    React.createElement("div", { "data-explain": "1", style: { display: "none" } }, title, body)
  );
`
);

for (const f of ["phaseValence", "phaseBaseline", "cycleShape", "cycleBands", "cycleTraces", "strokeStats", "unitConvert"])
  compile(path.join(web, "lib", `${f}.js`), `${f}.js`);
compile(path.join(web, "components", "portal", "CycleCharts.js"), "CycleCharts.js");
for (const f of ["RangeStrip", "PhaseVelocity", "CycleOverlay", "PhaseTimeline", "AlertSummary", "PhaseReportCard"])
  compile(path.join(web, "components", "portal", "phases", `${f}.js`), `${f}.js`);

const PhaseReportCard = require(path.join(out, "PhaseReportCard.cjs")).default;
const { displayUnit, scaleBaseline, M_TO_YD } = require(path.join(out, "unitConvert.cjs"));

const fmt = (v) => (v == null || !Number.isFinite(v) ? "—" : Number.isInteger(v) ? String(v) : v.toFixed(2));
const yd = (v) => v * M_TO_YD;
const stripComments = (html) => html.replace(/<!-- -->/g, "");

// ── 1. unit-module arithmetic, direct ─────────────────────────────────────────
console.log("\nunitConvert arithmetic");
{
  check("M_TO_YD is the page's shared constant", M_TO_YD === 1.09361);
  const m = displayUnit("m", true);
  check("m -> yd, imperial", m.factor === M_TO_YD && m.unit === "yd");
  const ms = displayUnit("m/s", true);
  check("m/s -> yd/s, imperial", ms.factor === M_TO_YD && ms.unit === "yd/s");
  const ms2 = displayUnit("m/s²", true);
  check("m/s² -> yd/s², imperial", ms2.factor === M_TO_YD && ms2.unit === "yd/s²");
  const ms3 = displayUnit("m/s³", true);
  check("m/s³ -> yd/s³, imperial", ms3.factor === M_TO_YD && ms3.unit === "yd/s³");
  const mMetric = displayUnit("m", false);
  check("metric mode is always identity, even for a length unit", mMetric.factor === 1 && mMetric.unit === "m");
  for (const u of ["s", "%", "×", "/s", ""]) {
    const r = displayUnit(u, true);
    check(`"${u}" stays invariant even under imperial`, r.factor === 1 && r.unit === u);
  }
  check("scaleBaseline(null, k) === null", scaleBaseline(null, M_TO_YD) === null);
  check("scaleBaseline(undefined, k) === undefined", scaleBaseline(undefined, M_TO_YD) === undefined);
  const base = { median: 2, band: [1, 3], mean: 2, sd: 0.5, mad: 0.4, sMAD: 0.6, n: 5 };
  check("scaleBaseline(base, 1) returns the SAME reference", scaleBaseline(base, 1) === base);
  const scaled = scaleBaseline(base, M_TO_YD);
  check(
    "scaleBaseline scales median/band/mean/sd/mad/sMAD",
    Math.abs(scaled.median - 2 * M_TO_YD) < 1e-9 &&
      Math.abs(scaled.band[0] - 1 * M_TO_YD) < 1e-9 &&
      Math.abs(scaled.band[1] - 3 * M_TO_YD) < 1e-9 &&
      Math.abs(scaled.mean - 2 * M_TO_YD) < 1e-9 &&
      Math.abs(scaled.sd - 0.5 * M_TO_YD) < 1e-9 &&
      Math.abs(scaled.mad - 0.4 * M_TO_YD) < 1e-9 &&
      Math.abs(scaled.sMAD - 0.6 * M_TO_YD) < 1e-9
  );
  check("scaleBaseline leaves n untouched", scaled.n === 5);
}

// ── 2. the F6 census — 23 converting / 24 invariant / 47 total ───────────────
console.log("\nDISPLAY table unit census (F6)");
{
  const srcPath = path.join(web, "components", "portal", "phases", "PhaseReportCard.js");
  const src = fs.readFileSync(srcPath, "utf8");
  const start = src.indexOf("const DISPLAY = {");
  const end = src.indexOf("\n};", start) + 3;
  const block = src.slice(start, end);
  const units = [...block.matchAll(/unit:\s*"([^"]*)"/g)].map((m) => m[1]);
  const CONVERTING = new Set(["m", "m/s", "m/s²", "m/s³"]);
  const conv = units.filter((u) => CONVERTING.has(u)).length;
  check("47 total DISPLAY entries", units.length === 47, `${units.length}`);
  check("23 converting-unit entries", conv === 23, `${conv}`);
  check("24 invariant-unit entries", units.length - conv === 24, `${units.length - conv}`);
}

// ── fixture ──────────────────────────────────────────────────────────────────
// One metric of each converting unit (m/s, m/s², m, m/s³), five invariant units (s, /s, ×, "", %),
// one flagged above, one flagged below, one in-range, one baseline-building (no history), one null
// value (not measured this swim — the critical null-guard case: `null * factor` is `0` in JS).
const FS = 89.5;
const N = 900;
const velocity = Array.from({ length: N }, (_, i) => 1.2 + 0.6 * Math.sin(i / 7));
const distProfile = Array.from({ length: N }, (_, i) => (i / FS) * 1.4);

const phases = {
  boundaries: { dive_start_s: 0.05, underwater_start_s: 0.2, stroke_start_s: 1.0, finish_s: 9.0, sources: {} },
  start: {
    peak_vel: { value: 2.45 }, // m/s — FLAGGED ABOVE (good=up -> "good")
    glide_avg_speed: { value: 1.6 }, // m/s — FLAGGED BELOW (good=up -> "bad")
    max_accel: { value: 3.05 }, // m/s² — IN RANGE
    glide_distance: { value: 1.25 }, // m — NO BASELINE (baseline building)
  },
  underwater: {
    dist_per_kick: { value: 0.38 }, // m — IN RANGE
    uw_distance: { value: null }, // m — NULL VALUE (not measured this swim)
    uw_duration: { value: 4.55 }, // s — invariant, IN RANGE
    kick_tempo: { value: 1.85 }, // /s — invariant, IN RANGE
  },
  swim: {
    breakout_vs_steady: { value: 1.08 }, // × — invariant, IN RANGE
    ivv: { value: 0.18 }, // "" — invariant, IN RANGE
  },
  whole: {
    jerk_smoothness: { value: -0.42 }, // m/s³ — IN RANGE
    phase_time_budget_start: { value: 25.5 }, // % — invariant, IN RANGE
  },
  kick_bands: [],
};

// Both flags land in "start" (2 vs 0 elsewhere) so PhaseTimeline's hot-phase tie-break is
// deterministic — a stable sort on equal counts would otherwise make the hot phase ambiguous.
const baseline = {
  "start.peak_vel": { median: 2.05, band: [1.75, 2.35], mean: 2.05, sd: 0.12, mad: 0.1, sMAD: 0.148, n: 5 },
  "start.glide_avg_speed": { median: 2.1, band: [1.8, 2.4], mean: 2.1, sd: 0.1, mad: 0.1, sMAD: 0.148, n: 5 },
  "start.max_accel": { median: 3.05, band: [2.55, 3.55], mean: 3.05, sd: 0.15, mad: 0.13, sMAD: 0.193, n: 5 },
  // start.glide_distance: intentionally ABSENT — this is the baseline-building row.
  "underwater.dist_per_kick": { median: 0.38, band: [0.33, 0.43], mean: 0.38, sd: 0.02, mad: 0.02, sMAD: 0.03, n: 5 },
  "underwater.uw_distance": { median: 2.55, band: [2.05, 3.05], mean: 2.55, sd: 0.2, mad: 0.17, sMAD: 0.25, n: 5 },
  "underwater.uw_duration": { median: 4.55, band: [4.05, 5.05], mean: 4.55, sd: 0.2, mad: 0.17, sMAD: 0.25, n: 5 },
  "underwater.kick_tempo": { median: 1.85, band: [1.55, 2.15], mean: 1.85, sd: 0.12, mad: 0.1, sMAD: 0.148, n: 5 },
  "swim.breakout_vs_steady": { median: 1.08, band: [0.93, 1.23], mean: 1.08, sd: 0.06, mad: 0.05, sMAD: 0.074, n: 5 },
  "swim.ivv": { median: 0.18, band: [0.1, 0.26], mean: 0.18, sd: 0.03, mad: 0.03, sMAD: 0.044, n: 5 },
  "whole.jerk_smoothness": { median: -0.42, band: [-0.57, -0.27], mean: -0.42, sd: 0.06, mad: 0.05, sMAD: 0.074, n: 5 },
  "whole.phase_time_budget_start": { median: 25.5, band: [20.5, 30.5], mean: 25.5, sd: 2, mad: 1.7, sMAD: 2.52, n: 5 },
};

const render = (unit) =>
  stripComments(
    renderToStaticMarkup(
      React.createElement(PhaseReportCard, {
        phases,
        velocity,
        distProfile,
        fsHz: FS,
        baseline,
        strokeType: "freestyle",
        sessionId: "fixture",
        cycles: [],
        strokes: null,
        session: {},
        segmentationReliable: true,
        unit,
      })
    )
  );

const htmlMetric = render("metric");
const htmlImperial = render("imperial");

// Row labels in FIXTURE / document order — bounds each row's window at the NEXT row's label so
// geometry percentages and explain text from one row can never bleed into a neighbour's assertions.
const ROW_LABELS = [
  "Top speed off dive", // start.peak_vel
  "Coast speed", // start.glide_avg_speed
  "Push off the block", // start.max_accel
  "Coast distance", // start.glide_distance
  "Distance per kick", // underwater.dist_per_kick
  "Distance underwater", // underwater.uw_distance
  "Time underwater", // underwater.uw_duration
  "Kick rate", // underwater.kick_tempo
  "Breakout vs cruise", // swim.breakout_vs_steady
  "Speed wobble", // swim.ivv
  "Stroke smoothness", // whole.jerk_smoothness
  "Start — time share", // whole.phase_time_budget_start
];
// PhaseTimeline's hot-phase flag list (surfaced by HoverExplainStub, needed for the AC-4 checks
// below) renders BOTH flagged labels too, ahead of the real grid — so a bare label search matches
// there first. `GRID_MARKER` is the metric-grid row container's own class, unique to it and first
// occurring at the very start of the "start" section's rows, after both AlertSummary and
// PhaseTimeline are fully behind it — anchoring every row search past that content entirely.
const GRID_MARKER = 'class="grid grid-cols-1 gap-x-6 sm:grid-cols-2"';
function rowWindow(html, label) {
  const gridStart = html.indexOf(GRID_MARKER);
  const searchFrom = gridStart >= 0 ? gridStart : 0;
  const idx = ROW_LABELS.indexOf(label);
  const i = html.indexOf(`>${label}<`, searchFrom);
  if (i < 0) return "";
  const next = ROW_LABELS[idx + 1];
  const j = next ? html.indexOf(`>${next}<`, i + 1) : -1;
  return j > 0 ? html.slice(i, j) : html.slice(i, i + 4000);
}
const percents = (html) => [...html.matchAll(/(?:left|width):\s*([\d.]+)%/g)].map((m) => parseFloat(m[1]));

// ── 3. converted rows changed correctly, including the null-guard case ───────
console.log("\nconverted rows (AC-1)");
{
  let w = rowWindow(htmlImperial, "Top speed off dive");
  check("peak_vel value converts (m/s)", w.includes(fmt(yd(2.45))));
  check("peak_vel median converts", w.includes(fmt(yd(2.05))));
  check("peak_vel band converts", w.includes(fmt(yd(1.75))) && w.includes(fmt(yd(2.35))));
  check("peak_vel relabels yd/s", w.includes("yd/s"));
  let wm = rowWindow(htmlMetric, "Top speed off dive");
  check("peak_vel stays m/s in metric, never yd", wm.includes("m/s") && !wm.includes("yd"));

  w = rowWindow(htmlImperial, "Coast speed");
  check("glide_avg_speed value converts (flagged below)", w.includes(fmt(yd(1.6))));
  check("glide_avg_speed median converts", w.includes(fmt(yd(2.1))));

  w = rowWindow(htmlImperial, "Push off the block");
  check("max_accel value converts (m/s²)", w.includes(fmt(yd(3.05))));
  check("max_accel relabels yd/s²", w.includes("yd/s²"));

  w = rowWindow(htmlImperial, "Coast distance");
  check("glide_distance (baseline building) still converts (m)", w.includes(fmt(yd(1.25))));
  check("glide_distance has no band (baseline building)", w.includes("baseline building"));

  w = rowWindow(htmlImperial, "Stroke smoothness");
  check("jerk_smoothness value converts (m/s³)", w.includes(fmt(yd(-0.42))));
  check("jerk_smoothness relabels yd/s³", w.includes("yd/s³"));

  w = rowWindow(htmlImperial, "Distance underwater");
  check("null value stays the not-measured pill in imperial (never a fake 0)", w.includes("not measured this swim"));
  wm = rowWindow(htmlMetric, "Distance underwater");
  check("null value stays the not-measured pill in metric too", wm.includes("not measured this swim"));
}

// ── 4. invariant rows are byte-identical between the two renders ─────────────
console.log("\ninvariant rows unchanged (AC-1)");
{
  for (const label of ["Time underwater", "Kick rate", "Breakout vs cruise", "Speed wobble", "Start — time share"]) {
    const wm = rowWindow(htmlMetric, label);
    const wi = rowWindow(htmlImperial, label);
    check(`${label}: byte-identical metric vs imperial`, wm.length > 0 && wm === wi);
  }
}

// ── 5. THE CENTRAL ASSERTION (AC-2) — geometry ratios survive the unit swap ──
console.log("\nAC-2 — strip geometry (band/median/dot) identical ratios across unit systems");
{
  for (const label of [
    "Top speed off dive",
    "Coast speed",
    "Push off the block",
    "Coast distance",
    "Distance per kick",
    "Time underwater",
    "Kick rate",
    "Breakout vs cruise",
    "Speed wobble",
    "Stroke smoothness",
    "Start — time share",
  ]) {
    const pm = percents(rowWindow(htmlMetric, label));
    const pi = percents(rowWindow(htmlImperial, label));
    const ok = pm.length > 0 && pm.length === pi.length && pm.every((v, i) => Math.abs(v - pi[i]) < 1e-6);
    check(`${label}: band/median/dot % identical`, ok, ok ? `${pm.length} values` : `${JSON.stringify(pm)} vs ${JSON.stringify(pi)}`);
  }
}

// ── 6. flag count + status words identical across the whole card ─────────────
console.log("\nAC-2 — flag count and status words identical across the whole card");
{
  for (const word of ["↑ better", "↓ worse", "in range", "baseline building"]) {
    const cm = htmlMetric.split(word).length - 1;
    const ci = htmlImperial.split(word).length - 1;
    check(`"${word}" occurs the same number of times`, cm === ci, `${cm} vs ${ci}`);
  }
  check("peak_vel: better in both", rowWindow(htmlMetric, "Top speed off dive").includes("↑ better") && rowWindow(htmlImperial, "Top speed off dive").includes("↑ better"));
  check("glide_avg_speed: worse in both", rowWindow(htmlMetric, "Coast speed").includes("↓ worse") && rowWindow(htmlImperial, "Coast speed").includes("↓ worse"));
}

// ── 7. AC-3 — hover-explain sentence, via the HoverExplainStub hidden div ────
console.log("\nAC-3 — hover-explain sentence converts (band + value together)");
{
  const w = rowWindow(htmlImperial, "Top speed off dive");
  check("explain: converted value appears", w.includes(fmt(yd(2.45))));
  check("explain: converted band appears", w.includes(fmt(yd(1.75))) && w.includes(fmt(yd(2.35))));
  const wm = rowWindow(htmlMetric, "Top speed off dive");
  check("explain: metric row never says yd", !wm.includes("yd"));
}

// ── 8. AC-4 — the timeline's flag list converts too ───────────────────────────
console.log("\nAC-4 — timeline flag list (hot phase = start, 2 flags)");
{
  check("metric: peak_vel flag-list entry", htmlMetric.includes(`${fmt(2.45)}m/s vs ${fmt(2.05)}m/s`));
  check("metric: glide_avg_speed flag-list entry", htmlMetric.includes(`${fmt(1.6)}m/s vs ${fmt(2.1)}m/s`));
  check("imperial: peak_vel flag-list entry converts", htmlImperial.includes(`${fmt(yd(2.45))}yd/s vs ${fmt(yd(2.05))}yd/s`));
  check("imperial: glide_avg_speed flag-list entry converts", htmlImperial.includes(`${fmt(yd(1.6))}yd/s vs ${fmt(yd(2.1))}yd/s`));
}

fs.rmSync(out, { recursive: true, force: true });
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
