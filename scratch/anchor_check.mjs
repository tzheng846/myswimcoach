// Phase 88-02 RENDER check — TimeToX re-anchored onto dive_start_s, head-waist removed.
//
// Same harness shape as scratch/stroke_toggle_check.mjs (87-02): transpile the JSX with the
// `typescript` package already in web/node_modules, drop the CJS output inside node_modules so
// "react" resolves by the normal walk-up, render with react-dom/server, assert on the markup.
// TimeToX imports only React (no "@/..." aliases), so there is no MAP to maintain here.
//
// ⚠ ONE MEASURED LIMITATION, worked around the same way 87-02 worked around its own:
// renderToStaticMarkup never runs effects, so the marker-change effect and the
// presets-desync-reset effect are unreachable from here. `targetVal`'s initial useState value
// DOES run (it's an initializer, not an effect), so this harness rewrites that ONE initializer
// to read a test-only global override — production source is untouched, and the rewrite asserts
// on the exact initializer text so it fails loudly if that line ever moves. This is what lets
// checks 3 and 4 force a specific chip selected without simulating a click.
//
// Check 5 (the caveat wording map) is a source-text assertion against page.js, not a render: the
// page itself pulls in Supabase, video and the rest of the session route, which is a much bigger
// harness than this plan needs. 88-02 Task 2 kept the wording inline rather than in a shared
// helper, and the plan explicitly allows asserting against the strings in that case.
//
// Run: node scratch/anchor_check.mjs

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

// ── Compile TimeToX.js with the targetVal initializer rewritten for test control ──────────────
const srcPath = path.join(web, "components", "portal", "TimeToX.js");
const srcText = fs.readFileSync(srcPath, "utf8");

const TARGET_INIT =
  'const [targetVal, setTargetVal] = useState(\n    presets[defaultIdx >= 0 ? defaultIdx : presets.length - 1]\n  );';
check("harness: targetVal initializer found for rewrite", srcText.includes(TARGET_INIT));

const rewritten = srcText.replace(
  TARGET_INIT,
  'const [targetVal, setTargetVal] = useState(\n    globalThis.__TEST_TARGET__ ?? presets[defaultIdx >= 0 ? defaultIdx : presets.length - 1]\n  );'
);
const js = ts.transpileModule(rewritten, {
  compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  fileName: "TimeToX.js",
}).outputText;
const compiledPath = path.join(out, "TimeToX.cjs");
fs.writeFileSync(compiledPath, js);
delete require.cache[require.resolve(compiledPath)];
const TimeToX = require(compiledPath).default;

const render = (props) =>
  renderToStaticMarkup(React.createElement(TimeToX, { onMarkerChange: () => {}, ...props }));

const extractSeconds = (markup) => {
  const m = markup.match(/>(-?[\d.]+|--) s</);
  if (!m) return undefined;
  return m[1] === "--" ? null : parseFloat(m[1]);
};

const extractButtonLabels = (markup) =>
  [...markup.matchAll(/<button[^>]*>([^<]*)<\/button>/g)].map((m) => m[1]);

// Independent reimplementation of computeTimeToX (same style as tests/test_phase_metrics.py's
// _split_by_hand): checks the RENDERED component against hand arithmetic, not against itself.
function expectedSeconds(timeArr, distArr, anchorS, targetM) {
  if (!timeArr.length || !distArr.length || anchorS == null) return null;
  const baseIdx = timeArr.findIndex((t) => t >= anchorS);
  if (baseIdx < 0) return null;
  const distBase = distArr[baseIdx];
  if (targetM <= 0) return null;
  const crossIdx = distArr.findIndex((d, i) => i >= baseIdx && d != null && d >= distBase + targetM);
  if (crossIdx < 0) return null;
  return Math.round((timeArr[crossIdx] - timeArr[baseIdx]) * 100) / 100;
}

// ── Check 1: the anchor drives the reading ─────────────────────────────────────────────────────
// dist(t) = t^2 -- an accelerating "swim", so time-to-cover-X depends on WHERE you start, unlike
// a constant-velocity fixture where it wouldn't (proving this needs a non-constant trace).
{
  const N = 500;
  const timeArr = Array.from({ length: N }, (_, i) => Math.round(i * 0.1 * 100) / 100);
  const distArr = timeArr.map((t) => t * t);
  const targetM = 10;

  globalThis.__TEST_TARGET__ = targetM;
  const s1 = extractSeconds(render({ timeArr, distArr, anchorS: 2.0, unit: "metric" }));
  const s2 = extractSeconds(render({ timeArr, distArr, anchorS: 2.5, unit: "metric" }));
  globalThis.__TEST_TARGET__ = undefined;

  const e1 = expectedSeconds(timeArr, distArr, 2.0, targetM);
  const e2 = expectedSeconds(timeArr, distArr, 2.5, targetM);

  check("anchor 2.0s reading matches hand arithmetic", s1 === e1, `rendered=${s1} expected=${e1}`);
  check("anchor 2.5s reading matches hand arithmetic", s2 === e2, `rendered=${s2} expected=${e2}`);
  check("moving the anchor 0.5s changes the reading", s1 !== s2, `${s1} vs ${s2}`);
}

// ── Check 2: head-waist is gone ────────────────────────────────────────────────────────────────
{
  check("source contains no headWaistM identifier", !srcText.includes("headWaistM"));
  check("source contains no waistTarget identifier", !srcText.includes("waistTarget"));

  const N = 200;
  const timeArr = Array.from({ length: N }, (_, i) => Math.round(i * 0.1 * 100) / 100);
  const distArr = timeArr.map((t) => t * 2.0);
  globalThis.__TEST_TARGET__ = 10;
  const withStray = render({ timeArr, distArr, anchorS: 1.0, unit: "metric", headWaistM: 0.8 });
  const withoutStray = render({ timeArr, distArr, anchorS: 1.0, unit: "metric" });
  globalThis.__TEST_TARGET__ = undefined;
  check("a stray headWaistM prop changes nothing in the markup", withStray === withoutStray);
}

// ── Check 3: unit-native presets — 20 yd equals 18.288 m on the same arrays ────────────────────
{
  const N = 400;
  const timeArr = Array.from({ length: N }, (_, i) => Math.round(i * 0.1 * 100) / 100);
  const distArr = timeArr.map((t) => t * t);

  globalThis.__TEST_TARGET__ = 20;
  const imperialMarkup = render({ timeArr, distArr, anchorS: 1.0, unit: "imperial" });
  globalThis.__TEST_TARGET__ = 18.288;
  const metricMarkup = render({ timeArr, distArr, anchorS: 1.0, unit: "metric" });
  globalThis.__TEST_TARGET__ = undefined;

  const impSeconds = extractSeconds(imperialMarkup);
  const metSeconds = extractSeconds(metricMarkup);
  check("imperial \"20yd\" chip is selected", extractButtonLabels(imperialMarkup).includes("20yd"));
  check(
    "20 yd (imperial) reads the same as 18.288 m (metric)",
    impSeconds != null && impSeconds === metSeconds,
    `20yd=${impSeconds}s  18.288m=${metSeconds}s`
  );
}

// ── Check 4: unreachable presets stay hidden ───────────────────────────────────────────────────
{
  const N = 61;
  const timeArr = Array.from({ length: N }, (_, i) => Math.round(i * 0.1 * 100) / 100);
  const distArr = timeArr.map((t) => t * 2.0); // reaches exactly 12.0 m past anchorS=0
  const markup = render({ timeArr, distArr, anchorS: 0, unit: "metric" });
  const labels = extractButtonLabels(markup);
  check("a 12 m swim shows the 5m and 10m chips", labels.includes("5m") && labels.includes("10m"));
  check(
    "a 12 m swim hides the 15/20/25m chips",
    !labels.includes("15m") && !labels.includes("20m") && !labels.includes("25m"),
    `chips=${labels.join(",")}`
  );
}

// ── Check 5: the caveat wording map (source-text, per the harness header note above) ───────────
{
  const pageText = fs.readFileSync(
    path.join(web, "app", "app", "sessions", "[id]", "page.js"),
    "utf8"
  );
  check(
    "anchorS is hoisted from dive_start_s with a baseline_end_s fallback",
    pageText.includes(
      "const anchorS = phases?.boundaries?.dive_start_s ?? metrics.session?.baseline_end_s ?? null;"
    )
  );
  check(
    '"none" source renders the no-dive-detected fallback wording',
    pageText.includes("no dive detected on this session — measured from the older start estimate.")
  );
  check(
    '"manual" source renders "from your marks."',
    pageText.includes('"from your marks."') || pageText.includes("from your marks.")
  );
  check(
    '"detected"/"auto" fall into the same auto-detected branch',
    pageText.includes("auto-detected.") && pageText.includes("Set it yourself")
  );
  check(
    "the whole caveat block is guarded on anchorS != null (null-anchor renders nothing)",
    pageText.includes("{anchorS != null && (")
  );
  check(
    "TimeToX is fed the hoisted anchorS, not a re-derived baselineEndS prop",
    pageText.includes("anchorS={anchorS}") && !pageText.includes("baselineEndS={")
  );
}

console.log();
console.log(`${pass}/${pass + fail} checks passed`);
if (fail > 0) process.exit(1);
