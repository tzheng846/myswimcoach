// Throwaway feasibility probe: can PhaseReportCard be rendered headlessly the 83-05 way?
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

const out = path.join(web, "node_modules", ".prc-probe");
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

const MAP = {
  '@/lib/phaseValence': './phaseValence.cjs',
  '@/lib/phaseBaseline': './phaseBaseline.cjs',
  '@/lib/cycleBands': './cycleBands.cjs',
  '@/lib/cycleTraces': './cycleTraces.cjs',
  './cycleShape': './cycleShape.cjs',
  '@/components/portal/SessionCard': './sessionCardStub.cjs',
  '@/components/portal/CycleCharts': './CycleCharts.cjs',
  './HoverExplain': './HoverExplain.cjs',
  './RangeStrip': './RangeStrip.cjs',
  './PhaseVelocity': './PhaseVelocity.cjs',
  './CycleOverlay': './CycleOverlay.cjs',
  './PhaseTimeline': './PhaseTimeline.cjs',
  './AlertSummary': './AlertSummary.cjs',
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

fs.writeFileSync(path.join(out, "sessionCardStub.cjs"),
  "exports.STROKE_LABELS={freestyle:'Freestyle',backstroke:'Backstroke',butterfly:'Butterfly',breaststroke:'Breaststroke'};\n");

for (const f of ["phaseValence", "phaseBaseline", "cycleShape", "cycleBands", "cycleTraces"])
  compile(path.join(web, "lib", `${f}.js`), `${f}.js`);
compile(path.join(web, "components", "portal", "CycleCharts.js"), "CycleCharts.js");
for (const f of ["HoverExplain", "RangeStrip", "PhaseVelocity", "CycleOverlay", "PhaseTimeline", "AlertSummary", "PhaseReportCard"])
  compile(path.join(web, "components", "portal", "phases", `${f}.js`), `${f}.js`);

const PhaseReportCard = require(path.join(out, "PhaseReportCard.cjs")).default;

const FS = 89.5;
const N = 900;
const velocity = Array.from({ length: N }, (_, i) => 1.2 + 0.6 * Math.sin(i / 7));
const dist = Array.from({ length: N }, (_, i) => (i / FS) * 1.4);
const mkItems = (count, key) => {
  const w = Math.floor((N - 100) / count);
  return Array.from({ length: count }, (_, i) => ({
    [key]: i, start_idx: 100 + i * w, end_idx: 100 + (i + 1) * w,
    duration_s: w / FS, dist_m: 2 + 0.1 * i, coast_fraction: 0.3, arm_peak_vel: 2.1 + 0.05 * i,
  }));
};
const phases = {
  boundaries: { dive_start_s: 0.1, ip_end_s: 0.5, stroke_start_s: 1.0, finish_s: 9.0, sources: {} },
  start: {}, underwater: {}, swim: { stroke_rate_spm: { value: 40, label: "Tempo", unit: "spm" } }, whole: {},
  kick_bands: [],
};
try {
  const html = renderToStaticMarkup(React.createElement(PhaseReportCard, {
    phases, velocity, distProfile: dist, fsHz: FS, baseline: {}, strokeType: "freestyle",
    sessionId: "abc", cycles: mkItems(7, "cycle_num"), session: { mean_dps_m: 2.3, mean_isi_s: 1.1, cv_isi: 0.08, mean_arm_peak_vel_ms: 2.2, cv_arm_peak_vel: 0.06, mean_coast_fraction: 0.3 },
    segmentationReliable: true, unit: "metric",
  }));
  console.log("RENDER OK, length:", html.length);
  console.log("has Swimming:", html.includes("Swimming"));
  console.log("has cycles badge:", /\d+ cycles? ·/.test(html), (html.match(/\d+ cycles? · \w+/) || [""])[0]);
  console.log("has recharts svg:", (html.match(/<svg/g) || []).length, "svgs");
  console.log("has 'every cycle on one axis':", html.includes("every cycle on one axis"));
  console.log("has 'One point per detected cycle':", html.includes("One point per detected cycle"));
  for (const t of ["Distance per Stroke","Cycle Duration","Arm Peak Velocity","Coast"]) console.log("title", JSON.stringify(t), html.includes(t));
  console.log("captions:", JSON.stringify((html.match(/mean [0-9.]+[^<]*/g)||[]).slice(0,6)));
  console.log("tooltip text 'Cycle ' present:", html.includes("Cycle "));
  console.log("readout caption line:", JSON.stringify((html.match(/<p class="text-\[11\.5px\] text-muted">[^<]*/g)||[]).slice(0,4)));
  console.log("recharts container html sample:", JSON.stringify(html.slice(html.indexOf("Distance per Stroke"), html.indexOf("Distance per Stroke")+700)));
} catch (e) {
  console.log("RENDER FAILED:", e.message);
  console.log(e.stack.split("\n").slice(0, 6).join("\n"));
}
fs.rmSync(out, { recursive: true, force: true });
