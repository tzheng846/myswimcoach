// 2026-09-01 follow-ups to Phase 88 — three user-reported items, one gate.
//
//   1. The anchor caveat still read "from your marks." (owed since 88-04's verify).
//   2. The metric/imperial toggle never reached the VIDEO. TraceOverlay hardcoded "m/s" / "m/s²"
//      and printed raw SI in its readout, and the /video route never hydrated `swimnetics.unit`
//      at all — so flipping to yards on the report card left both surfaces in metres.
//   3. The trend line is now a SWITCH with the window behind it, not a slider whose 0.00 s end
//      doubles as "off" (that end forgets the window the coach picked).
//
// Same harness shape as rolling_mean_check.mjs / split_picker_check.mjs: transpile with the
// `typescript` package already in web/node_modules, drop the CJS output inside node_modules so
// `react` resolves by the normal walk-up, require it back.
//
// ⚠ MEASURED LIMITATION: TraceOverlay's readout TEXT is written by the rAF loop against a live
// <video>, never during render — so this asserts the unit LABEL in the markup (which is rendered)
// plus source-text on the conversion in the loop (which is not). The converted number on screen is
// a human check. Stated rather than left as a silent gap.
//
// Run: node scratch/trend_toggle_check.mjs

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

const out = path.join(web, "node_modules", ".trend-toggle-check");
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

const compile = (src, name) => {
  const code = fs.readFileSync(src, "utf8");
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

compile(path.join(web, "components", "portal", "TraceOverlay.js"), "TraceOverlay.js");
const TraceOverlay = require(path.join(out, "TraceOverlay.cjs")).default;

const read = (...p) => fs.readFileSync(path.join(web, ...p), "utf8");
const pageText = read("app", "app", "sessions", "[id]", "page.js");
const videoText = read("app", "app", "sessions", "[id]", "video", "page.js");
const prefsText = read("lib", "useTracePrefs.js");
const unitPrefText = read("lib", "useUnitPref.js");
const overlayText = read("components", "portal", "TraceOverlay.js");
const panelText = read("components", "portal", "VideoTracePanel.js");

// ── 1. The caveat wording (item 1) ───────────────────────────────────────────
console.log("\n1. The anchor caveat says annotation, not marks");
{
  check(
    'the "manual" branch reads "from your annotation."',
    pageText.includes('"from your annotation."')
  );
  check(
    'the old "from your marks." wording is gone from the page',
    !pageText.includes("from your marks.")
  );
  // The other two branches are anchor_check's; pinned here only so a copy-paste fix cannot
  // silently take them with it.
  check(
    "the auto-detected and no-dive branches are untouched",
    pageText.includes("auto-detected.") &&
      pageText.includes("no dive detected on this session")
  );
}

// ── 2. TraceOverlay converts and relabels (item 2) ───────────────────────────
console.log("\n2. The video overlay follows the unit toggle");
{
  const n = 400;
  const fsHz = 100;
  const velocity = Array.from({ length: n }, (_, i) => 1.5 + 0.4 * Math.sin(i / 20));
  const acceleration = Array.from({ length: n }, (_, i) => 0.4 * Math.cos(i / 20));
  const base = { velocity, acceleration, fsHz, videoElRef: { current: null }, originS: 0 };

  const metric = renderToStaticMarkup(React.createElement(TraceOverlay, { ...base }));
  check("a velocity band renders at all", metric.length > 0);
  check("metric velocity band is labelled m/s", metric.includes("m/s"));
  check("metric never says yd", !metric.includes("yd"));

  const imperial = renderToStaticMarkup(
    React.createElement(TraceOverlay, {
      ...base,
      unitFactor: 1.09361,
      velUnit: "yd/s",
      accelUnit: "yd/s²",
    })
  );
  check("imperial velocity band is relabelled yd/s", imperial.includes("yd/s"));
  check("imperial band carries no stale m/s label", !imperial.includes(">m/s<"));

  const bothMetric = renderToStaticMarkup(
    React.createElement(TraceOverlay, { ...base, showAcceleration: true })
  );
  const bothImperial = renderToStaticMarkup(
    React.createElement(TraceOverlay, {
      ...base,
      showAcceleration: true,
      unitFactor: 1.09361,
      velUnit: "yd/s",
      accelUnit: "yd/s²",
    })
  );
  check("both bands render together", bothMetric.includes("m/s²"));
  check("both bands relabel together", bothImperial.includes("yd/s²") && bothImperial.includes("yd/s"));
  // The geometry is scaled to each band's own min/max, so the DRAWN path must be identical in
  // either unit — a converted path would be the same shape computed twice.
  const pathOf = (h) => (h.match(/ d="M[^"]*"/g) || []).join("|");
  check(
    "the drawn path is byte-identical in both units (the factor is readout-only)",
    pathOf(bothMetric) === pathOf(bothImperial) && pathOf(bothMetric).length > 0
  );
  check(
    "defaults are metric, so any caller that passes nothing is unchanged",
    metric === renderToStaticMarkup(React.createElement(TraceOverlay, { ...base, unitFactor: 1 }))
  );

  // Source-text: the rAF readout is not rendered, so this is the only place the conversion can be
  // pinned. Both the multiply and the dependency that re-arms the loop on a unit flip.
  check(
    "the readout multiplies the sampled value by unitFactor",
    /\(val \* unitFactor\)\.toFixed\(2\)/.test(overlayText)
  );
  check(
    "unitFactor is a dependency of the rAF effect (a flip re-arms the loop)",
    /geomA,\s*unitFactor,\s*velUnit,\s*accelUnit,\s*\]/.test(overlayText)
  );
  check(
    "no hardcoded m/s survives in the band wiring",
    !overlayText.includes('unit: "m/s"') && !overlayText.includes('renderBand("vel", geomV, lineColor, "m/s"')
  );
}

// ── 3. The pref reaches both routes (item 2, plumbing) ───────────────────────
console.log("\n3. Both video surfaces read the same persisted unit");
{
  check("useUnitPref owns the swimnetics.unit key", unitPrefText.includes('"swimnetics.unit"'));
  check(
    "useUnitPref hydrates in an effect, never a lazy initializer",
    unitPrefText.includes("useState(\"metric\")") && unitPrefText.includes("useEffect(() => {")
  );
  check("useUnitPref reuses M_TO_YD rather than a fourth copy of 1.09361", unitPrefText.includes("M_TO_YD"));
  check(
    "the report card uses the hook instead of its own localStorage read",
    pageText.includes("useUnitPref()") && !pageText.includes('window.localStorage.getItem("swimnetics.unit")')
  );
  check("the /video route uses it too", videoText.includes("useUnitPref()"));
  check(
    "the report card's video panel is given the factor and both labels",
    /unitFactor=\{unitFactor\}[\s\S]{0,80}velUnit=\{velUnit\}[\s\S]{0,80}accelUnit=\{accelUnit\}/.test(pageText)
  );
  check(
    "/video's panel is given them as well",
    /unitFactor=\{unitFactor\}[\s\S]{0,80}velUnit=\{velUnit\}[\s\S]{0,80}accelUnit=\{accelUnit\}/.test(videoText)
  );
  check(
    "/video's static charts convert too (they never did before)",
    videoText.includes("unitLabel={velUnit}") && videoText.includes("unitLabel={accelUnit}")
  );
  check(
    "VideoTracePanel forwards all three to the overlay",
    /unitFactor=\{unitFactor\}[\s\S]{0,80}velUnit=\{velUnit\}[\s\S]{0,80}accelUnit=\{accelUnit\}/.test(panelText)
  );
  check(
    "VideoTracePanel defaults keep every other caller metric",
    panelText.includes('unitFactor = 1') && panelText.includes('velUnit = "m/s"')
  );
}

// ── 4. The trend is a switch, with the window behind it (item 3) ─────────────
console.log("\n4. The trend toggles independently of its window");
{
  check("showTrend has its own storage key", prefsText.includes('showTrend: "swimnetics.showTrend"'));
  check("it defaults on, so nobody's chart changes", prefsText.includes("DEFAULT_SHOW_TREND = true"));
  check(
    "it hydrates in the EXISTING effect, alongside the other prefs",
    /const st = window\.localStorage\.getItem\(KEYS\.showTrend\)/.test(prefsText) &&
      /if \(st === "0" \|\| st === "1"\) setShowTrend\(st === "1"\)/.test(prefsText)
  );
  check("only 0/1 is accepted — anything else leaves the default", !prefsText.includes("Boolean(st)"));
  check("it persists as 0/1 like the other two toggles", prefsText.includes('persist(KEYS.showTrend, b ? "1" : "0")'));
  check("the hook exposes both the value and its setter", prefsText.includes("setShowTrend: chooseShowTrend"));

  check(
    "the chart is handed 0 when the switch is off",
    /smoothWindowS=\{\s*tracePrefs\.showTrend \? tracePrefs\.smoothWindowS : 0\s*\}/.test(pageText)
  );
  check("there is a Trend button", pageText.includes("tracePrefs.setShowTrend(!tracePrefs.showTrend)"));
  check("it reports its state to assistive tech", pageText.includes("aria-pressed={tracePrefs.showTrend}"));
  check(
    "the slider is hidden while the switch is off",
    /\{tracePrefs\.showTrend && \(\s*<>/.test(pageText)
  );
  check(
    "the window itself is NOT reset by the switch (no setSmoothWindowS in the toggle)",
    !/setShowTrend\([^)]*\)[\s\S]{0,120}setSmoothWindowS/.test(pageText)
  );
  check(
    "the slider still spans 0.00-3.00 s, unchanged",
    pageText.includes('min="0"') && pageText.includes('max="3"') && pageText.includes('step="0.05"')
  );
  check(
    "the whole row still lives inside the showVelocity branch (D5 boundary held)",
    pageText.indexOf("{tracePrefs.showVelocity && (") < pageText.indexOf("tracePrefs.setShowTrend")
  );
  check(
    "the /video route still passes no trend at all (D5)",
    !videoText.includes("smoothWindowS") && !videoText.includes("showTrend")
  );
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
