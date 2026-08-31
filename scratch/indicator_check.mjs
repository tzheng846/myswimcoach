// Phase 84-03 INDICATOR check for the mobile band vocabulary.
//
// The mobile repo has no test runner and no linter (package.json scripts = start/android/ios/web),
// and this plan is not the place to add one. So the harness lives here, following the 83-05 /
// 85-01 precedent (scratch/overlay_render_check.mjs, scratch/marketing_render_check.mjs).
//
// It is strictly simpler than 83-05's: src/lib/indicators.js is deliberately RN-free with a single
// import specifier, so this rewrites that one specifier to a file URL for src/theme/tokens.js and
// imports the result as a data: module. No transpile, no JSX, no react-dom.
//
// It also prints the specimen matrix the plan's decision checkpoint is judged from — the point
// being that the visual call gets made without paying for an EAS build.
//
// Run: node scratch/indicator_check.mjs        (everything)
//      node scratch/indicator_check.mjs --pure (module behaviour only, skip the static wiring checks)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..");
const mobile = path.resolve(repo, "..", "swimnetics-mobile");
const src = path.join(mobile, "src");
const pureOnly = process.argv.includes("--pure");

let pass = 0;
let fail = 0;
const failed = [];
const check = (name, ok, extra = "") => {
  if (ok) {
    pass++;
    console.log(`  PASS  ${name}${extra ? "  " + extra : ""}`);
  } else {
    fail++;
    failed.push(name);
    console.log(`  FAIL  ${name}${extra ? "  " + extra : ""}`);
  }
};

// ---------- load the pure module under plain node (G29) ----------

const tokensUrl = pathToFileURL(path.join(src, "theme", "tokens.js")).href;
const indicatorsPath = path.join(src, "lib", "indicators.js");
const rawSource = fs.readFileSync(indicatorsPath, "utf8");
const rewritten = rawSource.replace(/(['"])\.\.\/theme\1/, JSON.stringify(tokensUrl));
if (rewritten === rawSource) {
  console.log("  FAIL  indicators.js imports '../theme' exactly once (the harness's one rewrite)");
  process.exit(1);
}
const otherImports = [...rewritten.matchAll(/^import\s.*?from\s+['"](.+?)['"]/gm)]
  .map((m) => m[1])
  .filter((s) => !s.startsWith("file:"));
const M = await import("data:text/javascript;base64," + Buffer.from(rewritten, "utf8").toString("base64"));
const { colors } = await import(tokensUrl);

console.log("\nmodule shape");
check("indicators.js is RN-free (no react / react-native import)", otherImports.length === 0,
  otherImports.length ? otherImports.join(", ") : "0 unresolved specifiers");
check("BAND_KEYS is the canonical four",
  JSON.stringify(M.BAND_KEYS) === JSON.stringify(["good", "ok", "needs_work", "unknown"]), M.BAND_KEYS.join("/"));

// ---------- AC-2: color resolution is server-first and total ----------

// Sentinel hexes, NOT the real ones. ratings.py and tokens.js currently carry byte-identical band
// colors (G21), so asserting against the real payload could not tell server-first from theme-first.
const SERVER = { good: "#111111", ok: "#222222", needs_work: "#333333" };
const SHAPES = [["server payload", SERVER], ["undefined", undefined], ["null", null], ["empty {}", {}]];
const INPUTS = [...M.BAND_KEYS, "not_a_band"];

console.log("\nAC-2  color resolution is server-first and total");
{
  let allDefined = true;
  const bad = [];
  for (const [shapeName, rcv] of SHAPES) {
    for (const band of INPUTS) {
      const c = M.bandColor(band, rcv);
      if (typeof c !== "string" || !c) { allDefined = false; bad.push(`${band} x ${shapeName} -> ${String(c)}`); }
    }
  }
  check("every band x payload-shape returns a defined color string", allDefined,
    `${INPUTS.length * SHAPES.length} combinations` + (bad.length ? " | " + bad.join(", ") : ""));

  const serverFirst = ["good", "ok", "needs_work"].every((b) => M.bandColor(b, SERVER) === SERVER[b]);
  check("the three server bands return the SERVER hex, not the theme's", serverFirst,
    ["good", "ok", "needs_work"].map((b) => `${b}=${M.bandColor(b, SERVER)}`).join(" "));

  const themeFallback =
    M.bandColor("good", undefined) === colors.good &&
    M.bandColor("ok", null) === colors.ok &&
    M.bandColor("needs_work", {}) === colors.needsWork;
  check("absent / null / empty rating_colors falls back to the theme tokens", themeFallback);

  // G24: rating_colors has only three keys, so unknown must be the client's own answer.
  const unknownOwned =
    M.bandColor("unknown", SERVER) === colors.textMuted && M.bandColor("not_a_band", SERVER) === colors.textMuted;
  check("unknown and an unrecognized band resolve to the theme fallback even WITH a payload",
    unknownOwned, M.bandColor("unknown", SERVER));

  // The whole point of totality: no caller needs a trailing `|| colors.textMuted`.
  const neverUndefined = SHAPES.every(([, rcv]) => INPUTS.every((b) => M.bandColor(b, rcv) !== undefined));
  check("no result is ever undefined, so no caller needs its own fallback tail", neverUndefined);
}

// ---------- G21 pin: the server hexes and the theme tokens still agree ----------

console.log("\nG21  server hexes vs theme tokens (drift pin, not a behaviour check)");
{
  const py = fs.readFileSync(path.join(repo, "ratings.py"), "utf8");
  const m = py.match(/RATING_COLORS\s*=\s*\{([^}]*)\}/);
  const server = Object.fromEntries(
    [...(m ? m[1] : "").matchAll(/"(\w+)":\s*"(#[0-9a-fA-F]{6})"/g)].map((x) => [x[1], x[2]]),
  );
  const same = server.good === colors.good && server.ok === colors.ok && server.needs_work === colors.needsWork;
  check("ratings.py RATING_COLORS == tokens.js band tokens", same,
    `${server.good}/${server.ok}/${server.needs_work} vs ${colors.good}/${colors.ok}/${colors.needsWork}`);
  check("RATING_COLORS still has no `unknown` key (G24 — the client owns it)", !("unknown" in server));
}

// ---------- AC-3: unknown and provisional are handled once ----------

console.log("\nAC-3  every (band x provisional) pair resolves");
{
  const rows = [];
  let allDefined = true;
  for (const band of M.BAND_KEYS) {
    for (const prov of [false, true]) {
      const label = M.bandLabel(band, prov);
      const color = M.bandColor(band, SERVER);
      const dot = M.bandDotStyle(band, SERVER, prov);
      const fill = dot.backgroundColor;
      const ring = dot.borderColor ? `${dot.borderWidth}px ${dot.borderColor}` : "none";
      if (!label || !color || fill === undefined || (prov && !dot.borderColor)) allDefined = false;
      rows.push({ band, prov, label, color, fill, ring });
    }
  }
  check("8 rows, every label / color / dot cell defined", allDefined && rows.length === 8, `${rows.length} rows`);
  const hollow = rows.filter((r) => r.prov).every((r) => r.fill === "transparent" && r.ring !== "none");
  check("provisional renders as a hollow ring in the band color", hollow);
  const filled = rows.filter((r) => !r.prov).every((r) => r.fill !== "transparent" && r.ring === "none");
  check("trusted renders as a filled swatch", filled);

  console.log("\n  SPECIMEN MATRIX  (the artifact the decision checkpoint judges — no build needed)");
  console.log("  " + "band".padEnd(12) + "provisional".padEnd(13) + "label".padEnd(24) + "color".padEnd(10) +
    "dot fill".padEnd(14) + "dot ring");
  console.log("  " + "-".repeat(90));
  for (const r of rows) {
    console.log("  " + r.band.padEnd(12) + String(r.prov).padEnd(13) + r.label.padEnd(24) +
      r.color.padEnd(10) + String(r.fill).padEnd(14) + r.ring);
  }
  console.log("  (sentinel payload #111111/#222222/#333333; unknown is the theme's textMuted by design — G24)\n");
}

if (pureOnly) {
  console.log(`--pure: static wiring checks skipped.`);
  console.log(`${pass}/${pass + fail} checks passed${fail ? `  (${fail} FAILED: ${failed.join(", ")})` : ""}`);
  process.exit(fail ? 1 : 0);
}

// ---------- AC-1: exactly one file owns the vocabulary ----------

const SURFACES = {
  "screens/AthletesScreen.js": path.join(src, "screens", "AthletesScreen.js"),
  "screens/AthleteDetailScreen.js": path.join(src, "screens", "AthleteDetailScreen.js"),
  "screens/DashboardScreen.js": path.join(src, "screens", "DashboardScreen.js"),
  "components/PillarCards.js": path.join(src, "components", "PillarCards.js"),
};
const read = Object.fromEntries(Object.entries(SURFACES).map(([k, p]) => [k, fs.readFileSync(p, "utf8")]));

// G30: these target band-keyed MAP LITERALS and band TERNARY CHAINS, never the token names.
// `colors.needsWork` on a network-error message and on a never-tested caption are legitimate
// non-band uses of the band palette and must survive untouched.
const BANNED = {
  "band-keyed map literal": /good\s*:[^,}]+,\s*ok\s*:/,
  "band ternary chain": /band\s*===\s*['"]good['"]\s*\?/,
};
const IMPORT_RE = /from\s+['"][^'"]*lib\/indicators['"]/;

console.log("AC-1  one module owns the vocabulary");
for (const [name, pattern] of Object.entries(BANNED)) {
  const hits = Object.entries(read).filter(([, s]) => pattern.test(s)).map(([k]) => k);
  check(`no ${name} on any surface`, hits.length === 0, hits.length ? hits.join(", ") : "0 matches");
}
check("indicators.js is the one file that DOES carry the band map", BANNED["band-keyed map literal"].test(rawSource));
for (const name of Object.keys(SURFACES)) {
  check(`${name} imports lib/indicators`, IMPORT_RE.test(read[name]));
}
// The two legitimate non-band uses of the band palette must survive (G30).
check("DashboardScreen keeps its needsWork error message",
  /color="needsWork">\{error\}/.test(read["screens/DashboardScreen.js"]));
check("AthletesScreen keeps its needsWork never-tested caption",
  /tested \? 'textMuted' : 'needsWork'/.test(read["screens/AthletesScreen.js"]));

// ---------- AC-4: rating_colors reaches the athlete page ----------

console.log("\nAC-4  the athlete page reads the server's colors");
{
  const nav = read["screens/AthletesScreen.js"].match(/navigate\(\s*['"]AthleteDetail['"][\s\S]{0,160}?\)/);
  check("AthletesScreen's navigate('AthleteDetail') carries a rating-colors param",
    !!nav && /ratingColors/.test(nav[0]), nav ? nav[0].replace(/\s+/g, " ") : "no navigate call found");
  check("AthleteDetailScreen reads ratingColors off route.params",
    /route\.params\?\.ratingColors/.test(read["screens/AthleteDetailScreen.js"]));
  check("AthleteDetailScreen has no local band-to-color map",
    !/BAND_COLOR|BAND_LABEL\s*=/.test(read["screens/AthleteDetailScreen.js"]));
}

// ---------- AC-5: the dashboard leads with the band ----------

console.log("\nAC-5  the dashboard uses the roster's dot and keeps the score");
{
  const d = read["screens/DashboardScreen.js"];
  check("DashboardScreen renders BandDot", /<BandDot/.test(d) && /from\s+['"][^'"]*ui\/BandDot['"]/.test(d));
  check("AthletesScreen renders the SAME BandDot component", /<BandDot/.test(read["screens/AthletesScreen.js"]));
  check("the 0-100 score survives on the card", /\{score\}/.test(d));
  check("overallScore still excludes provisional pillars", /filter\(p\s*=>\s*!p\.provisional/.test(d));
  check("the mixed-vocabulary `rating_colors || colors` fallback is gone (G26)", !/rating_colors\s*\|\|\s*colors\b/.test(d));
}

// ---------- AC-6: the change set is item 5 only ----------

console.log("\nAC-6  scope");
{
  const stray = ["screens/RecordScreen.js", "context/BleContext.js", "components/CycleCharts.js"]
    .filter((f) => IMPORT_RE.test(fs.readFileSync(path.join(src, f), "utf8")));
  check("RecordScreen / BleContext / CycleCharts untouched by this vocabulary", stray.length === 0, stray.join(", "));
}

console.log(`\n${pass}/${pass + fail} indicator checks passed${fail ? `  (${fail} FAILED: ${failed.join(", ")})` : ""}`);
process.exit(fail ? 1 : 0);
