// Phase 85-01 checks for the marketing home page. Two of them, because the two failure
// modes found while building the mockup are invisible to `next build` and to eslint.
//
// 1. COPY HYGIENE. Dashes are counted in BOTH forms: the literal characters and the
//    &mdash; / &ndash; entities. The FAQ was 10 entities to 2 literals before this phase,
//    so a character-only grep reports it as nearly clean while the rendered page is full
//    of em dashes. Also flags the banned strings.
//
// 2. RENDER. Follows the pattern 83-05 established in scratch/overlay_render_check.mjs,
//    which exists because "build and lint are blind to this": transpile the components,
//    server-render them, assert on the markup. Targets the two silent failure classes,
//    an SVG collapsed to zero height inside a flex item and a stroke tree-shaken down to
//    `none`, plus the usual-range coherence rule (a coloured strip sits OUTSIDE its band,
//    a grey one INSIDE it), which caught a real defect in the round-2 mockup.
//
// Needs no auth and no dev server, so it runs anywhere.
//
// Run: node scratch/marketing_render_check.mjs

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

// ============================================================ 1. copy hygiene
//
// SCOPE. The marketing surface only: the home page, the root metadata, the FAQ, the
// shared chrome components and everything under components/marketing, plus the baked
// geometry module. Deliberately NOT all of web/app or all of web/components:
//   - /privacy (9 dashes) and lib/blog.js (24) are out of scope by D5 and D27
//   - the coach portal is out of scope for this phase, carries ~285 dashes in comments,
//     and legitimately says "GoPro" in its video upload help and "changed (unclear)" in
//     AlertSummary.js, which this plan is explicitly forbidden to touch
// A check that is permanently red is a check nobody reads.

const COPY_FILES = [
  "app/page.js",
  "app/layout.js",
  "lib/marketingGeom.js",
  ...fs.readdirSync(path.join(web, "app", "faq")).filter((f) => f.endsWith(".js"))
    .map((f) => `app/faq/${f}`),
  ...fs.readdirSync(path.join(web, "components")).filter((f) => f.endsWith(".js"))
    .map((f) => `components/${f}`),
  ...fs.readdirSync(path.join(web, "components", "marketing"))
    .filter((f) => f.endsWith(".js")).map((f) => `components/marketing/${f}`),
];

const DASHES = [
  ["em dash", "—"],
  ["en dash", "–"],
  ["&mdash;", "&mdash;"],
  ["&ndash;", "&ndash;"],
];
const BANNED = ["GoPro", "PETG", "UHMWPE", "REAL DATA", "changed (unclear)", "Chantee"];

const copyHits = [];
for (const rel of COPY_FILES) {
  const src = fs.readFileSync(path.join(web, rel), "utf8");
  for (const [label, needle] of DASHES) {
    const n = src.split(needle).length - 1;
    if (n) copyHits.push(`${rel}: ${n} x ${label}`);
  }
  for (const needle of BANNED) {
    const n = src.toLowerCase().split(needle.toLowerCase()).length - 1;
    if (n) copyHits.push(`${rel}: ${n} x "${needle}"`);
  }
}

console.log(`copy hygiene over ${COPY_FILES.length} files`);
check("no dashes and no banned strings on the marketing surface", copyHits.length === 0,
  copyHits.length ? "\n        " + copyHits.join("\n        ") : "");

// ================================================================= 2. render

const out = path.join(web, "node_modules", ".marketing-render-check");
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

const compile = (src, name) => {
  const code = fs
    .readFileSync(src, "utf8")
    .replace('from "@/lib/marketingGeom"', 'from "./marketingGeom.cjs"')
    .replace('from "./PhaseRadar"', 'from "./PhaseRadar.cjs"');
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

compile(path.join(web, "lib", "marketingGeom.js"), "marketingGeom.js");
for (const name of ["PhaseRadar", "PhaseStory", "UsualRange", "CyclePack", "VideoSync", "Device"]) {
  compile(path.join(web, "components", "marketing", `${name}.js`), `${name}.js`);
}
const load = (name) => require(path.join(out, `${name}.cjs`)).default;

const html = {};
for (const name of ["PhaseStory", "UsualRange", "CyclePack", "VideoSync", "Device"]) {
  html[name] = renderToStaticMarkup(React.createElement(load(name)));
}
const all = Object.values(html).join("\n");

// ---------- the two silent failure classes ----------

console.log("silent failure classes");
check("nothing renders stroke none", !/stroke="none"/.test(all) && !/stroke:\s*none/.test(all));
check("no unresolved var() reaches a paint attribute",
  !/(stroke|fill)="var\(/.test(all));
for (const [name, markup] of Object.entries(html)) {
  check(`${name} renders something`, markup.length > 200, `${markup.length} chars`);
}
const svgs = all.match(/<svg[^>]*>/g) || [];
check("every svg carries a viewBox", svgs.length > 0 && svgs.every((s) => s.includes("viewBox=")),
  `${svgs.length} svg`);
check("no svg is given a fixed zero height", !/height="0"/.test(all));

const emptyGeom = (all.match(/points="\s*"/g) || []).length;
check("every polyline and polygon carries real geometry", emptyGeom === 0);
const points = [...all.matchAll(/points="([^"]*)"/g)].map((m) => m[1]);
check("every points attribute parses as coordinate pairs",
  points.length > 0 && points.every((p) => /^-?\d/.test(p) && p.includes(",")),
  `${points.length} polylines/polygons`);

// ---------- report card ----------

console.log("report card");
const wholePts = points.find((p) => p.split(" ").length > 500);
check("whole lap polyline is the decimated real trace", !!wholePts,
  wholePts ? `${wholePts.split(" ").length} pts` : "missing");
for (const word of ["START", "UNDERWATER", "SWIMMING"]) {
  check(`whole lap chart labels ${word}`, html.PhaseStory.includes(`>${word}<`));
}
check("three phase bands are tinted",
  ["#f2b134", "#2196f3", "#a970ff"].every((c) => html.PhaseStory.includes(`fill="${c}" opacity="0.15"`)));
check("a boundary tick sits at each phase start",
  (html.PhaseStory.match(/<line[^>]*stroke-width="1.2"/g) || []).length === 3);
check("post finish tail is drawn grey",
  html.PhaseStory.includes('fill="#9b8ba6" opacity="0.07"'));

const radarDots = (html.PhaseStory.match(/r="3.4"/g) || []).length;
check("three radars, five axes each, dot per axis", radarDots === 15, `${radarDots} dots`);
const axisLabels = (html.PhaseStory.match(/font-size="10.5"/g) || []).length;
check("all fifteen axis labels render", axisLabels === 15, `${axisLabels} labels`);
check("each radar draws a dashed usual range ring",
  (html.PhaseStory.match(/stroke-dasharray="3 3"/g) || []).length === 3);
check("radar viewBox stays wider than the plot so labels do not clip",
  (html.PhaseStory.match(/viewBox="0 0 300 214"/g) || []).length === 3);
const todayPolys = (html.PhaseStory.match(/stroke-width="2.4"/g) || []).length;
check("three today polygons, one per phase", todayPolys === 3);
check("the three radar shapes differ from each other", (() => {
  const p = [...html.PhaseStory.matchAll(/<polygon points="([^"]*)"[^>]*stroke-width="2.4"/g)]
    .map((m) => m[1]);
  return p.length === 3 && new Set(p).size === 3;
})());

// ---------- usual range coherence ----------

console.log("usual range");
const GREY = "#6e5a78";
const strips = [...html.UsualRange.matchAll(/<svg viewBox="0 0 200 18".*?<\/svg>/gs)].map((m) => m[0]);
check("exactly six strips", strips.length === 6, `${strips.length}`);

let coherent = 0;
for (const s of strips) {
  const band = s.match(/<rect x="([\d.]+)" y="4" width="([\d.]+)"/);
  const dot = s.match(/<circle cx="([\d.]+)" cy="9" r="5.4" fill="([^"]+)"/);
  if (!band || !dot) continue;
  const [lo, w] = [parseFloat(band[1]), parseFloat(band[2])];
  const x = parseFloat(dot[1]);
  const inside = x >= lo && x <= lo + w;
  const grey = dot[2] === GREY;
  // The rule the whole section rests on: an alert is OUTSIDE the usual range, a normal
  // row is inside it. A coloured dot sitting inside its own band is the contradiction.
  if (inside === grey) coherent++;
}
check("every strip agrees with its own colour", coherent === 6, `${coherent}/6 coherent`);

check("alert line counts only out of range rows", html.UsualRange.includes("3 alerts today"));
for (const chip of ["2 worse", "1 better", "3 normal"]) {
  check(`chip "${chip}"`, html.UsualRange.includes(chip));
}
check("legend third entry reads Normal", html.UsualRange.includes(">Normal<"));
check("no changed (unclear) anywhere", !all.includes("changed (unclear)"));

// ---------- cycle pack, video, device ----------

console.log("cycle pack, video, device");
const cycleLines = (html.CyclePack.match(/<polyline/g) || []).length;
check("five cycle traces", cycleLines === 5, `${cycleLines}`);
check("exactly one cycle is picked out",
  (html.CyclePack.match(/stroke="#4e148c"/g) || []).length === 1);
check("the other four are muted",
  (html.CyclePack.match(/stroke="#b9aecf"/g) || []).length === 4);
check("cycle copy names the odd stroke", /Cycle \d runs longer/.test(html.CyclePack));

const panes = (html.VideoSync.match(/aspect-ratio:16 \/ 10|aspect-ratio:16\/10/g) || []).length;
check("four video panes", panes === 4, `${panes}`);
check("video panes carry no camera position labels",
  !/(Above|Side|Under|Deck|End|Front|Rear|Camera \d)/.test(html.VideoSync));
check("video heading still claims four angles",
  html.VideoSync.includes("Up to four angles on one timeline."));

for (const head of ["Built for a wet deck", "Safety built in", "No laptop on deck",
  "Back in about thirty seconds"]) {
  check(`device card "${head}"`, html.Device.includes(head));
}
check("safety card names the breakaway magnet", html.Device.includes("breakaway magnet"));

// ---------- result ----------

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
