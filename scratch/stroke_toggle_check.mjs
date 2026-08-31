// Phase 87-02 RENDER check — the cycles/strokes toggle, end to end through the real
// PhaseReportCard.
//
// Same harness shape as `scratch/overlay_render_check.mjs` (83-05): transpile the JSX with the
// `typescript` package already in web/node_modules, drop the CJS output inside node_modules so
// `react` resolves by the normal walk-up, render with react-dom/server, assert on the markup.
// 83-01's lesson is why this exists at all: `next build` and `eslint` are both blind to a prop that
// is never read and to a colour token that tree-shakes to `stroke: none`.
//
// ⚠ TWO MEASURED LIMITATIONS OF THIS HARNESS, both worked around rather than fought:
//
// 1. recharts renders an EMPTY wrapper under renderToStaticMarkup (it has no dimensions
//    server-side), so the dashed mean `ReferenceLine` and the dots are NOT assertable. The panel
//    CAPTIONS carry the same numbers and do render — every mean assertion below reads those.
//
// 2. `renderToStaticMarkup` never runs effects, and the granularity preference is hydrated from
//    localStorage IN AN EFFECT on purpose (87-02 D2: reading it in a lazy initializer desyncs
//    hydration). So stroke mode is unreachable from the outside here. This file rewrites the ONE
//    state initializer to a global while transpiling its private copy — production source is
//    untouched, and the rewrite asserts on the exact initializer so it fails loudly if that line
//    ever moves. What it therefore does NOT cover is the effect itself; that is step 7 of the
//    plan's human-verify (reload, still on strokes).
//
// Run: node scratch/stroke_toggle_check.mjs

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

// Every `@/…` and relative import rewritten to a compiled sibling; SessionCard stubbed because the
// real module pulls in next/link (both tricks proven by scratch/_prc_render_probe.mjs).
const MAP = {
  "@/lib/phaseValence": "./phaseValence.cjs",
  "@/lib/phaseBaseline": "./phaseBaseline.cjs",
  "@/lib/cycleBands": "./cycleBands.cjs",
  "@/lib/cycleTraces": "./cycleTraces.cjs",
  "@/lib/strokeStats": "./strokeStats.cjs",
  "./cycleShape": "./cycleShape.cjs",
  "@/components/portal/SessionCard": "./sessionCardStub.cjs",
  "@/components/portal/CycleCharts": "./CycleCharts.cjs",
  "./HoverExplain": "./HoverExplain.cjs",
  "./RangeStrip": "./RangeStrip.cjs",
  "./PhaseVelocity": "./PhaseVelocity.cjs",
  "./CycleOverlay": "./CycleOverlay.cjs",
  "./PhaseTimeline": "./PhaseTimeline.cjs",
  "./AlertSummary": "./AlertSummary.cjs",
};

const GRANULARITY_INIT = 'const [granularity, setGranularity] = useState("cycle");';

const compile = (src, name) => {
  let code = fs.readFileSync(src, "utf8");
  for (const [from, to] of Object.entries(MAP)) code = code.split(`"${from}"`).join(`"${to}"`);
  if (name === "PhaseReportCard.js") {
    check("harness: granularity initializer found for rewrite", code.includes(GRANULARITY_INIT));
    code = code.replace(
      GRANULARITY_INIT,
      'const [granularity, setGranularity] = useState(globalThis.__TEST_GRANULARITY__ || "cycle");'
    );
  }
  const js = ts.transpileModule(code, {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: name,
  }).outputText;
  fs.writeFileSync(path.join(out, name.replace(/\.js$/, ".cjs")), js);
};

fs.writeFileSync(
  path.join(out, "sessionCardStub.cjs"),
  "exports.STROKE_LABELS={freestyle:'Freestyle',backstroke:'Backstroke',butterfly:'Butterfly',breaststroke:'Breaststroke'};\n"
);

for (const f of ["phaseValence", "phaseBaseline", "cycleShape", "cycleBands", "cycleTraces", "strokeStats"])
  compile(path.join(web, "lib", `${f}.js`), `${f}.js`);
compile(path.join(web, "components", "portal", "CycleCharts.js"), "CycleCharts.js");
for (const f of [
  "HoverExplain",
  "RangeStrip",
  "PhaseVelocity",
  "CycleOverlay",
  "PhaseTimeline",
  "AlertSummary",
  "PhaseReportCard",
])
  compile(path.join(web, "components", "portal", "phases", `${f}.js`), `${f}.js`);

const PhaseReportCard = require(path.join(out, "PhaseReportCard.cjs")).default;
const PhaseVelocity = require(path.join(out, "PhaseVelocity.cjs")).default;
const { buildTraces } = require(path.join(out, "cycleTraces.cjs"));
const { buildBands } = require(path.join(out, "cycleBands.cjs"));

// ── fixture ──────────────────────────────────────────────────────────────────
// A cycle is exactly TWO strokes: same spans, halved durations and distances. That is what makes
// the stroke-level mean assertion below a real test — the stored session means are the cycle ones.
const FS = 89.5;
const N = 900;
const velocity = Array.from({ length: N }, (_, i) => 1.2 + 0.6 * Math.sin(i / 7));
const distProfile = Array.from({ length: N }, (_, i) => (i / FS) * 1.4);

const CYCLE_DUR = 1.1;
const CYCLE_DPS = 2.3;
const cycles = Array.from({ length: 7 }, (_, i) => ({
  cycle_num: i,
  start_idx: 100 + i * 100,
  end_idx: 200 + i * 100,
  duration_s: CYCLE_DUR,
  dist_m: CYCLE_DPS,
  coast_fraction: 0.3,
  arm_peak_vel: 2.2,
}));
const strokes = Array.from({ length: 14 }, (_, i) => ({
  stroke_num: i,
  start_idx: 100 + i * 50,
  end_idx: 150 + i * 50,
  duration_s: CYCLE_DUR / 2,
  dist_m: CYCLE_DPS / 2,
  coast_fraction: 0.3,
  arm_peak_vel: 2.2,
}));

const phases = {
  boundaries: { dive_start_s: 0.05, underwater_start_s: 0.2, stroke_start_s: 1.0, finish_s: 9.0, sources: {} },
  start: {},
  underwater: {},
  swim: {},
  whole: {},
  kick_bands: [
    { kick_num: 0, start_idx: 20, end_idx: 42, duration_s: 0.25 },
    { kick_num: 1, start_idx: 42, end_idx: 64, duration_s: 0.25 },
    { kick_num: 2, start_idx: 64, end_idx: 86, duration_s: 0.25 },
  ],
};

// The stored, CYCLE-level session means — the ones stroke mode must never print.
const session = {
  mean_dps_m: CYCLE_DPS,
  mean_isi_s: CYCLE_DUR,
  cv_isi: 0.08,
  mean_arm_peak_vel_ms: 2.2,
  cv_arm_peak_vel: 0.06,
  mean_coast_fraction: 0.3,
  arm_asym_tempo_pct: 6.2,
  arm_asym_dps_pct: -3.4,
  arm_asym_peak_vel_pct: 1.5,
  cv_stroke_interval_a: 0.08,
  cv_stroke_interval_b: 0.11,
  cv_stroke_dps_a: 0.05,
  cv_stroke_dps_b: 0.07,
};

const render = (props = {}, granularity = "cycle") => {
  globalThis.__TEST_GRANULARITY__ = granularity;
  try {
    return renderToStaticMarkup(
      React.createElement(PhaseReportCard, {
        phases,
        velocity,
        distProfile,
        fsHz: FS,
        baseline: {},
        strokeType: "freestyle",
        sessionId: "fixture",
        cycles,
        session,
        segmentationReliable: true,
        unit: "metric",
        ...props,
      })
    );
  } finally {
    globalThis.__TEST_GRANULARITY__ = undefined;
  }
};

// Colours of the SWIMMING inset's band paths, in document order. `lastIndexOf`, deliberately: the
// Underwater inset is banded too and comes FIRST in the section order, and Whole race carries no
// bands at all — so the last banded aria-label in the document is always the Swimming one.
const bandColors = (html) => {
  const swim = html.lastIndexOf("one band per");
  const end = html.indexOf("</svg>", swim);
  return [...html.slice(swim, end).matchAll(/stroke="var\(--color-cycle-([a-z]+)\)"/g)].map((m) => m[1]);
};

const armBlock = (html) => {
  const i = html.indexOf("Arm balance");
  if (i < 0) return "";
  const j = html.indexOf("stay per cycle", i);
  return html.slice(i, j);
};

// ── 1. cycle mode / no strokes: today's card, unchanged ──────────────────────
console.log("\ncycle mode, session with no strokes");
{
  const html = render({ strokes: null });
  for (const str of [
    "Distance per Stroke",
    "Cycle Duration",
    "every cycle on one axis",
    "One point per detected cycle",
    "cover every cycle shown",
    "stroke-by-stroke",
  ])
    check(`legacy string present: ${str}`, html.includes(str));
  check("badge reads cycles · annotated", html.includes("7 cycles"), (html.match(/7 cycles[^<]*/) || [""])[0]);
  check("cycle-level mean in caption", html.includes("mean 1.10 s"));
  for (const str of [">strokes<", "Arm balance", "arm-by-arm", "% apart", "Stroke Duration"])
    check(`absent without strokes: ${str}`, !html.includes(str));
}

// ── 2. strokes present, still cycle mode ─────────────────────────────────────
console.log("\nstrokes present, cycle mode (the default)");
{
  const html = render({ strokes });
  check("toggle rendered", html.includes('aria-label="Swimming detail granularity"'));
  check("cycles pressed", /aria-pressed="true"[^>]*>cycles</.test(html));
  check("strokes not pressed", /aria-pressed="false"[^>]*>strokes</.test(html));
  check("still the cycle card", html.includes("Cycle Duration") && html.includes("7 cycles"));
  check("no Arm balance in cycle mode", !html.includes("Arm balance"));
  check("no stroke-level mean in cycle mode", html.includes("mean 1.10 s") && !html.includes("mean 0.55 s"));
}

// ── 3. stroke mode: four surfaces switch together ────────────────────────────
console.log("\nstroke mode");
const strokeHtml = render({ strokes }, "stroke");
{
  const html = strokeHtml;
  check("badge reads strokes", html.includes("14 strokes"), (html.match(/14 strokes[^<]*/) || [""])[0]);
  check("badge keeps its provenance chip", /14 strokes ·\s*annotated/.test(html.replace(/<!-- -->/g, "")));
  check("overlay heading", html.includes("every stroke on one axis"));
  check("panel title Stroke Duration", html.includes("Stroke Duration") && !html.includes("Cycle Duration"));
  check("panel title Distance per Arm Stroke", html.includes("Distance per Arm Stroke"));
  check("footer noun", html.includes("One point per detected stroke"));
  check("section note is arm-by-arm", html.includes("arm-by-arm") && !html.includes("stroke-by-stroke"));
  check("strokes pressed", /aria-pressed="true"[^>]*>strokes</.test(html));

  const cycleBandCount = bandColors(render({ strokes })).filter((c) => c === "a" || c === "b").length;
  const strokeBandCount = bandColors(html).filter((c) => c === "a" || c === "b").length;
  check("band count doubles", strokeBandCount === 2 * cycleBandCount, `${cycleBandCount} → ${strokeBandCount}`);
}

// ── 4. means are stroke-level, never the stored cycle-level ones ─────────────
console.log("\nstroke-level means");
{
  check("halved duration in caption", strokeHtml.includes("mean 0.55 s"));
  check("stored cycle mean never printed", !strokeHtml.includes("mean 1.10 s"));
  check("halved distance in caption", strokeHtml.includes("mean 1.15 m"));
  check("stored cycle distance never printed", !strokeHtml.includes("mean 2.30 m"));
  check("CV recomputed, not the stored 8%", strokeHtml.includes("(CV) 0%") && !strokeHtml.includes("(CV) 8%"));
}

// ── 5. A/B colour alignment ──────────────────────────────────────────────────
console.log("\nA / B colour alignment");
{
  const cols = bandColors(strokeHtml);
  check("trace first, then gold breakout", cols[0] === "idle" && cols[1] === "breakout", cols.slice(0, 4).join(","));
  const bands = cols.slice(2);
  check("n = 1 is cycle-a", bands[0] === "a");
  check("n = 2 is cycle-b", bands[1] === "b");
  check("strict alternation after the breakout", bands.every((c, i) => c === (i % 2 ? "b" : "a")), bands.join(""));
  check("A chip painted with cycle-a", armBlock(strokeHtml).includes("background-color:var(--color-cycle-a)"));
  check("no path strokes none/undefined", !/stroke="(none|undefined)"/.test(strokeHtml));
  check("no left/right anywhere", !/\b(left|right) arm\b/i.test(strokeHtml));
}

// ── 6. arm balance ───────────────────────────────────────────────────────────
console.log("\narm balance");
{
  const block = armBlock(strokeHtml);
  check("tempo magnitude", block.includes("6.2% apart"));
  check("tempo direction: A slower", block.includes("A slower"));
  check("distance sign flips the side", block.includes("3.4% apart") && block.includes("B further"));
  check("peak velocity", block.includes("1.5% apart") && block.includes("A faster"));
  check(
    "per-side CVs",
    block.includes("A 8%") && block.includes("B 11%") && block.includes("A 5%") && block.includes("B 7%")
  );
  check("A/B definition always shown", strokeHtml.includes("cannot tell which is left"));
  check("strip scope note shown", strokeHtml.includes("Usual-range comparisons below"));
  check("no verdict word", !/\beven\b/.test(block));

  const flipped = render({ strokes, session: { ...session, arm_asym_tempo_pct: -6.2 } }, "stroke");
  check("negative tempo names B", armBlock(flipped).includes("B slower"));

  const imperial = render({ strokes, unit: "imperial" }, "stroke");
  check("unit-invariant under imperial", armBlock(imperial) === block);

  const nulled = render({ strokes, session: { ...session, cv_stroke_dps_b: null } }, "stroke");
  check("null key degrades to one line", nulled.includes("Not enough strokes on each side"));
  check("…and the rest still renders", nulled.includes("14 strokes") && nulled.includes("Stroke Duration"));
}

// ── 7. per-side medians (driven directly — the overlay opens in seconds mode) ─
console.log("\nper-side medians");
{
  const mk = (count) =>
    Array.from({ length: count }, (_, i) => ({
      stroke_num: i,
      start_idx: 100 + i * 50,
      end_idx: 150 + i * 50,
      duration_s: 0.55,
    }));
  const opt = { fsHz: FS, mode: "normalized", numberKey: "stroke_num", parity: true };
  const ten = buildTraces(mk(10), velocity, opt);
  check("two medians at 5 a side", Array.isArray(ten.medianA) && Array.isArray(ten.medianB));
  const eight = buildTraces(mk(8), velocity, opt);
  check("none at 4 a side", eight.medianA === null && eight.medianB === null);
  const cyc = buildTraces(cycles, velocity, { fsHz: FS, mode: "normalized" });
  check(
    "cycle mode: one combined median, no side medians",
    Array.isArray(cyc.median) && cyc.medianA === null && cyc.medianB === null
  );
  check("sides tagged by parity", ten.traces[0].side === "A" && ten.traces[1].side === "B");
  check("no side tag without parity", cyc.traces[0].side === null);
}

// ── 8. defaults: the libs and PhaseVelocity behave exactly as before ─────────
console.log("\ndefaults unchanged");
{
  const pv = renderToStaticMarkup(
    React.createElement(PhaseVelocity, {
      variant: "inset",
      velocity,
      fsHz: FS,
      window: [89, 805],
      bands: buildBands(cycles, { fsHz: FS, i0: 89, i1: 805 }),
    })
  );
  check("PhaseVelocity default aria noun", pv.includes("coloured one band per cycle"));
  const noOpts = buildBands(cycles, { fsHz: FS, i0: 89, i1: 805 });
  check("buildBands default numbering", noOpts.map((b) => b.n).join(",") === "1,2,3,4,5,6,7");
  const byStroke = buildBands(strokes.slice(0, 6), { fsHz: FS, i0: 89, i1: 805, numberKey: "stroke_num" });
  check("numberKey numbers 1..6", byStroke.map((b) => b.n).join(",") === "1,2,3,4,5,6");
}

// ── 9. no cross-contamination: Underwater is untouched in stroke mode ────────
console.log("\nunderwater untouched");
{
  check("kick badge still kicks · auto", strokeHtml.includes("3 kicks"), (strokeHtml.match(/3 kicks[^<]*/) || [""])[0]);
  check("kick overlay heading unchanged", strokeHtml.includes("every kick on one axis"));
}

fs.rmSync(out, { recursive: true, force: true });
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
