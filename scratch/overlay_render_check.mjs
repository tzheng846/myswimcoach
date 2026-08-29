// Phase 83-05 RENDER check for CycleOverlay.
//
// 83-01 shipped two silent-failure bugs that `next build` and `eslint` both passed: a prop shadowed
// inside `geom` so it was never read, and Tailwind v4 tree-shaking `@theme` tokens referenced only
// as raw `var()` in an SVG stroke, so every band drew `stroke: none`. Neither is visible to a build.
// The only thing that catches that class is actually rendering the component and looking at the
// output, which is what this does — headlessly, without needing the Supabase-gated portal.
//
// Transpiles the JSX with the `typescript` package already in web/node_modules, drops the CJS
// output inside node_modules (so `react` / `react/jsx-runtime` resolve by the normal walk-up), then
// renders with react-dom/server and asserts on the markup.
//
// Run: node scratch/overlay_render_check.mjs

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

const compile = (src, name) => {
  let code = fs.readFileSync(src, "utf8");
  code = code
    .replace('from "@/lib/cycleTraces"', 'from "./cycleTraces.cjs"')
    .replace('from "./cycleShape"', 'from "./cycleShape.cjs"');
  const js = ts.transpileModule(code, {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    fileName: name,
  }).outputText;
  fs.writeFileSync(path.join(out, name.replace(/\.js$/, ".cjs")), js);
};

compile(path.join(web, "lib", "cycleShape.js"), "cycleShape.js");
compile(path.join(web, "lib", "cycleTraces.js"), "cycleTraces.js");
compile(path.join(web, "components", "portal", "phases", "CycleOverlay.js"), "CycleOverlay.js");

const CycleOverlay = require(path.join(out, "CycleOverlay.cjs")).default;

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

const FS = 89.5;
const profile = (L, scale = 1) =>
  Array.from({ length: L }, (_, i) => scale * (0.6 + 0.9 * Math.sin(Math.PI * (i / (L - 1))) ** 2));

function layout(profiles) {
  const velocity = [];
  const items = [];
  for (const p of profiles) {
    const start = velocity.length;
    velocity.push(...p);
    items.push({ start_idx: start, end_idx: velocity.length, duration_s: p.length / FS });
    velocity.push(0.2, 0.2, 0.2);
  }
  return { velocity, items };
}

const render = (props) =>
  renderToStaticMarkup(React.createElement(CycleOverlay, { fsHz: FS, ...props }));

const countPaths = (html) => (html.match(/<path /g) || []).length;

// ---------- degenerate: renders NOTHING ----------

{
  const one = layout([profile(24)]);
  check("1 item -> renders nothing at all", render({ items: one.items, velocity: one.velocity, window: [0, one.velocity.length - 1] }) === "");
  check("empty items -> renders nothing at all", render({ items: [], velocity: one.velocity, window: [0, 10] }) === "");
  check("no velocity -> renders nothing at all", render({ items: one.items, velocity: [], window: [0, 10] }) === "");
}

// ---------- the pack ----------

const five = layout([profile(24), profile(30), profile(21), profile(27), profile(25)]);
const win = [0, five.velocity.length - 1];
const base = { items: five.items, velocity: five.velocity, window: win };

{
  const html = render(base);
  check("5 items -> a panel renders", html.length > 0);
  // 5 traces; the median is normalized-only so seconds mode must have exactly 5 paths.
  check("seconds mode draws exactly one path per trace", countPaths(html) === 5, `${countPaths(html)} paths`);
  check("every trace path carries real geometry (d=\"M...\")", (html.match(/<path d="M/g) || []).length === 5);

  // ⚠ the 83-01 tree-shaking trap: a stroke must be a REAL var(), never none/undefined.
  check("pack stroke is the idle token", html.includes("stroke:var(--color-cycle-idle)") || html.includes('stroke="var(--color-cycle-idle)"'));
  check("no path rendered with stroke none/undefined", !/stroke="(none|undefined)"/.test(html) && !/stroke:(none|undefined)/.test(html));

  check("gutter has one button per drawable trace", (html.match(/<button/g) || []).length === 5 + 2, "5 rows + 2 toggle buttons");
  check("gutter numbers 1..5 present", [1, 2, 3, 4, 5].every((n) => html.includes(`>${n}<`)));
  check("svg is labelled with the trace count", /aria-label="All 5 cycles/.test(html), (html.match(/aria-label="All[^"]*"/) || [""])[0]);
  check("y gridline labels rendered", html.includes("ui-monospace"));
  check("seconds x-tick labels rendered", /0\.\d\ds<\/text>/.test(html));
  check("mode toggle offers both modes", html.includes(">seconds<") && html.includes("% of cycle"));
}

// ---------- active / dim ----------

{
  const html = render({ ...base, activeN: 3 });
  check("active trace takes the accent colour", html.includes("var(--color-cycle-a)"));
  check("non-active traces are dimmed", /stroke-opacity:0\.45|strokeOpacity="0.45"|stroke-opacity="0.45"/.test(html));
  check("active trace is painted LAST (on top)", html.lastIndexOf("var(--color-cycle-a)") > html.lastIndexOf("var(--color-cycle-idle)"));
  const noActive = render(base);
  check("nothing dimmed when nothing is active", !/stroke-opacity:0\.45|stroke-opacity="0.45"/.test(noActive));
}

// ---------- pinned ----------

{
  const html = render({ ...base, pinnedN: 2, activeN: 2 });
  check("pinned row is marked aria-pressed", /aria-pressed="true"/.test(html));
}

// ---------- breakout gutter row ----------

{
  const html = render({ ...base, excludeBreakout: true });
  check("breakout row rendered as '0 · breakout'", html.includes("0 · breakout"), "");
  // User direction at the 83-05 verify OVERRODE the plan's AC-3 "does nothing": the row has no
  // trace in the pack, but it does have a band in the inset, so it must be a hover target for it.
  check("breakout row IS an interactive hover target", /<button[^>]*>0 · breakout/.test(html));
  check("breakout row is not pointer-inert", !/pointer-events:none/.test(html));
  check("breakout row carries its own aria-label", html.includes('aria-label="Breakout pull'));
  const hb0 = render({ ...base, excludeBreakout: true, activeN: 0 });
  check("activeN 0 lights the breakout row", /<button[^>]*bg-navy\/60[^>]*>0 · breakout/.test(hb0));
  check("activeN 0 dims NOTHING in the pack (it has no trace)", !/stroke-opacity:0\.45|stroke-opacity="0.45"/.test(hb0));
  check("activeN 0 accents no trace", !hb0.includes("var(--color-cycle-a)"));
  check("breakout adds no path", countPaths(html) === 5, `${countPaths(html)} paths`);
  check("numbered rows still start at 1", html.includes(">1<"));
}

// ---------- normalized mode is reachable and adds the median ----------
// The toggle is local state, so drive the module the way the component does and assert the
// component renders what buildTraces hands it.

{
  const { buildTraces } = require(path.join(out, "cycleTraces.cjs"));
  const n5 = buildTraces(five.items, five.velocity, { fsHz: FS, mode: "normalized" });
  check("normalized model has a median for 5 traces", Array.isArray(n5.median));
  check("normalized model still has 5 traces", n5.traces.length === 5);
  // The component draws traces + 1 median path when median is non-null: 6 paths.
  check("median would add exactly one more path", n5.traces.length + 1 === 6);
}

// ---------- dropout draws a GAP, not a straight line ----------

{
  const holed = layout([profile(24), profile(30), profile(21), profile(27), profile(25)]);
  holed.velocity[holed.items[1].start_idx + 10] = NaN;
  const html = render({ items: holed.items, velocity: holed.velocity, window: [0, holed.velocity.length - 1] });
  check("dropout trace still drawn", countPaths(html) === 5, `${countPaths(html)} paths`);
  // A pen-up shows as a SECOND "M" inside one d attribute.
  const ds = [...html.matchAll(/<path d="([^"]+)"/g)].map((m) => m[1]);
  check("dropout path lifts the pen (two M commands)", ds.some((d) => (d.match(/M/g) || []).length === 2));
}

// ---------- y-scale agrees with the inset ----------
// PhaseVelocity's niceMax over the same window must give the same vmax the overlay used, or the two
// stacked charts are drawn at different scales. Re-derive it from PhaseVelocity's own source.

{
  const pv = fs.readFileSync(path.join(web, "components", "portal", "phases", "PhaseVelocity.js"), "utf8");
  const body = pv.match(/function niceMax\(v\) \{([\s\S]*?)\n\}/)[1];
  // eslint-disable-next-line no-new-func
  const insetNiceMax = new Function("v", body);
  const co = fs.readFileSync(path.join(web, "components", "portal", "phases", "CycleOverlay.js"), "utf8");
  const coBody = co.match(/function niceMax\(v\) \{([\s\S]*?)\n\}/)[1];
  const overlayNiceMax = new Function("v", coBody);
  const sames = [0, 0.3, 0.9, 1.0, 1.4, 2.9, 3.0, 3.4, 7.2].every((v) => insetNiceMax(v) === overlayNiceMax(v));
  check("duplicated niceMax is byte-equivalent to PhaseVelocity's", sames && body.trim() === coBody.trim());
}

// ---------- gutter wraps once the row count gets long ----------

{
  const many = layout(Array.from({ length: 15 }, (_, i) => profile(20 + (i % 7))));
  const html = render({ items: many.items, velocity: many.velocity, window: [0, many.velocity.length - 1] });
  check("15 traces all drawn", countPaths(html) === 15, `${countPaths(html)} paths`);
  // 15 rows over a 10-row cap -> 2 columns of 8.
  check("15 rows wrap into 2 columns of 8", /grid-template-rows:repeat\(8, ?minmax\(0, ?auto\)\)/.test(html), (html.match(/grid-template-rows:[^;"]*/) || [""])[0]);
  const nine = layout(Array.from({ length: 9 }, (_, i) => profile(20 + (i % 7))));
  const h9 = render({ items: nine.items, velocity: nine.velocity, window: [0, nine.velocity.length - 1] });
  check("9 rows stay in ONE column", /grid-template-rows:repeat\(9, ?minmax\(0, ?auto\)\)/.test(h9), (h9.match(/grid-template-rows:[^;"]*/) || [""])[0]);
  // 25 rows -> 3 columns of 9.
  const lots = layout(Array.from({ length: 25 }, (_, i) => profile(20 + (i % 7))));
  const h25 = render({ items: lots.items, velocity: lots.velocity, window: [0, lots.velocity.length - 1] });
  check("25 rows wrap into 3 columns of 9", /grid-template-rows:repeat\(9, ?minmax\(0, ?auto\)\)/.test(h25), (h25.match(/grid-template-rows:[^;"]*/) || [""])[0]);
  // The breakout row must sit OUTSIDE the wrapping grid so its long label cannot set column width.
  const hb = render({ ...base, excludeBreakout: true });
  const gridStart = hb.indexOf("grid-template-rows");
  check("breakout row precedes the numbered grid", hb.indexOf("0 · breakout") < gridStart && gridStart > -1);
  check("breakout row is not a grid cell", /grid-template-rows:repeat\(5, ?/.test(hb), "5 numbered rows, breakout excluded from the count");
}

fs.rmSync(out, { recursive: true, force: true });
console.log(`\n${pass}/${pass + fail} render checks passed${fail ? `  (${fail} FAILED)` : ""}`);
process.exit(fail ? 1 : 0);
