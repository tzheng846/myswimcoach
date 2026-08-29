// scratch harness for Phase 83-03's pure libs (cycleShape + cycleBands).
//
// `web/package.json` has no test runner and no `"type": "module"`, so node treats web/lib/*.js as
// CJS and cannot import them despite their ESM syntax. Precedent: 75-05's engine scratch checks.
// This copies each lib to a .mjs beside this file and imports the copy — so the libs themselves
// stay untouched and the checks stay throwaway.
//
// Run: node scratch/shape_checks.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const libDir = path.resolve(here, "..", "web", "lib");
for (const name of ["cycleShape", "cycleBands"]) {
  fs.copyFileSync(path.join(libDir, `${name}.js`), path.join(here, `_${name}.mjs`));
}
const { analyzeShapes, POINTS, K, MIN_ITEMS } = await import("./_cycleShape.mjs");
const { buildBands } = await import("./_cycleBands.mjs");

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

// ---------- fixture helpers ----------

// A plausible stroke profile: one hump, non-zero floor. `scale` changes amplitude, `L` duration.
const profile = (L, scale = 1, shift = 0) =>
  Array.from({ length: L }, (_, i) => {
    const t = i / (L - 1);
    return scale * (0.6 + 0.9 * Math.sin(Math.PI * Math.min(1, Math.max(0, t + shift))) ** 2);
  });

// Exact 2x linear upsample: same continuous shape, twice the samples.
const upsample2x = (a) => {
  const out = [];
  for (let i = 0; i < a.length - 1; i++) out.push(a[i], (a[i] + a[i + 1]) / 2);
  out.push(a[a.length - 1]);
  return out;
};

// Lay profiles end to end into one velocity array + the item rows that index into it.
// A 3-sample gap between items mirrors the real trace, where bands do not abut.
function layout(profiles) {
  const velocity = [];
  const items = [];
  for (const p of profiles) {
    const start = velocity.length;
    velocity.push(...p);
    items.push({ start_idx: start, end_idx: velocity.length, duration_s: p.length / 89.5 });
    velocity.push(0.2, 0.2, 0.2);
  }
  return { velocity, items };
}

console.log(`\ncycleShape — POINTS=${POINTS} K=${K} MIN_ITEMS=${MIN_ITEMS}\n`);

// ---------- AC-1: duration invariance ----------
{
  // A and B share one shape at two durations, and sit OFF the median so the distance is non-zero
  // — a test that both scored 0.0 would prove nothing.
  const base = profile(50, 1.02);
  const { velocity, items } = layout([
    base, // A
    upsample2x(base), // B — same shape, 99 samples
    profile(50, 0.97),
    profile(52, 1.03),
    profile(48, 1.01),
    profile(51, 0.99),
  ]);
  const { byN } = analyzeShapes(items, velocity);
  const dA = byN[1].shapeDist;
  const dB = byN[2].shapeDist;
  check(
    "identical profile at different durations scores the same distance",
    Math.abs(dA - dB) < 1e-9,
    `dA=${dA.toFixed(9)} dB=${dB.toFixed(9)}`
  );
}

// ---------- AC-1: amplitude is NOT normalised away ----------
{
  const { velocity, items } = layout([
    profile(50),
    profile(50, 0.99),
    profile(50, 1.01),
    profile(50, 1.0),
    profile(50, 0.98),
    profile(50, 0.55), // same shape, weak pull
  ]);
  const { byN } = analyzeShapes(items, velocity);
  const weak = byN[6].shapeDist;
  const normal = byN[1].shapeDist;
  check("a same-shape / lower-amplitude cycle scores FURTHER", weak > normal, `weak=${weak.toFixed(3)} normal=${normal.toFixed(3)}`);
}

// ---------- AC-2: a tight session flags nothing ----------
{
  const scales = [0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03, 1.04];
  const { velocity, items } = layout(scales.map((s) => profile(50, s)));
  const { results } = analyzeShapes(items, velocity);
  const flagged = results.filter((r) => r.anomaly);
  check("a tight, metronomic session flags NOTHING", flagged.length === 0, `flagged=${flagged.length}`);
}

// ---------- AC-2: one odd cycle flags exactly itself ----------
{
  const scales = [0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03];
  const { velocity, items } = layout([...scales.map((s) => profile(50, s)), profile(50, 1.0, 0.35)]);
  const { results } = analyzeShapes(items, velocity);
  const flagged = results.filter((r) => r.anomaly).map((r) => r.n);
  check("one injected odd cycle flags exactly itself", flagged.length === 1 && flagged[0] === 8, `flagged=[${flagged}]`);
}

// ---------- AC-2: below minItems, nothing ----------
{
  const { velocity, items } = layout([profile(50), profile(50, 0.99), profile(50, 1.01), profile(50, 0.4)]);
  const { results, reference } = analyzeShapes(items, velocity);
  check(
    `fewer than MIN_ITEMS (${MIN_ITEMS}) flags nothing and builds no reference`,
    results.every((r) => !r.anomaly && r.shapeDist === null) && reference === null
  );
}

// ---------- AC-2: degenerate zero spread ----------
{
  const { velocity, items } = layout(Array.from({ length: 6 }, () => profile(50)));
  const { results } = analyzeShapes(items, velocity);
  check("a zero-MAD (all identical) session flags nothing", results.every((r) => !r.anomaly));
}

// ---------- AC-1: a NaN-bearing item is excluded, not guessed ----------
{
  const scales = [1.0, 0.98, 1.02, 0.99, 1.01, 1.0];
  const { velocity, items } = layout(scales.map((s) => profile(50, s)));
  velocity[items[2].start_idx + 10] = NaN; // dropout inside item 3
  const { byN, results } = analyzeShapes(items, velocity);
  check(
    "a dropout-bearing item is excluded from the reference and left unflagged",
    byN[3].shapeDist === null && byN[3].anomaly === false && results.filter((r) => r.shapeDist !== null).length === 5
  );
}

// ---------- durationDev is a fact, never the flag ----------
{
  // Durations must genuinely vary or the duration MAD is 0 and nothing is measurable — the same
  // degenerate guard the shape gate has.
  const { velocity, items } = layout([
    profile(48),
    profile(49, 0.99),
    profile(50, 1.01),
    profile(51, 1.0),
    profile(52, 0.98),
    profile(110, 1.0), // same shape, wildly long
  ]);
  const { byN } = analyzeShapes(items, velocity);
  check(
    "a duration outlier with a normal shape is NOT flagged, but carries durationDev",
    byN[6].anomaly === false && Math.abs(byN[6].durationDev) > K,
    `durationDev=${byN[6].durationDev.toFixed(1)} MADs`
  );
}

// ============================ cycleBands ============================

console.log("");
console.log("cycleBands - breakout identity");
console.log("");

// Four cycles, the first dropped from the window so `n` starts at 2 - the case that proves the
// breakout is the lowest surviving `n`, not array position 0.
const rows = [
  { cycle_num: 0, start_idx: 0, end_idx: 40, duration_s: 0.45 },
  { cycle_num: 1, start_idx: 110, end_idx: 140, duration_s: 0.45 },
  { cycle_num: 2, start_idx: 140, end_idx: 180, duration_s: 0.45 },
  { cycle_num: 3, start_idx: 180, end_idx: 220, duration_s: 0.45 },
];
const win = { fsHz: 89.5, i0: 100, i1: 220 };

{
  const bands = buildBands(rows, { ...win, breakoutFirst: true });
  const bo = bands.find((b) => b.isBreakout);
  check("exactly one breakout band exists", bands.filter((b) => b.isBreakout).length === 1);
  check(
    "the breakout is its OWN band spanning i0 to the lowest surviving cycle's start",
    bo && bo.n === 0 && bo.startIdx === 100 && bo.endIdx === 110,
    "breakout=[" + bo.startIdx + "," + bo.endIdx + "]"
  );
  check(
    "cycle 1 keeps its own span and is NOT gilded (one stroke gold, not two)",
    bands[1].n === 2 && bands[1].startIdx === 110 && !bands[1].isBreakout
  );
  check("the breakout band carries its own duration in seconds", Math.abs(bo.duration - 10 / 89.5) < 1e-9);
  check("cycle numbering is untouched by the insert", bands.filter((b) => !b.isBreakout).map((b) => b.n).join() === "2,3,4");
}

{
  // Marks that start exactly at the breakout leave no gap - claiming a zero-width gold band would
  // invent a stroke that is not there.
  const flush = [{ cycle_num: 1, start_idx: 100, end_idx: 140, duration_s: 0.45 }];
  const bands = buildBands(flush, { ...win, breakoutFirst: true });
  check("no gap means no breakout band at all", bands.length === 1 && !bands[0].isBreakout);
}

{
  const bands = buildBands(rows, { ...win, breakoutFirst: false });
  check(
    "breakoutFirst false adds nothing and leaves the lead-in grey (auto sessions, Underwater)",
    bands.length === 3 && bands.every((b) => !b.isBreakout) && bands[0].startIdx === 110
  );
}

console.log(`\n${pass} passed, ${fail} failed\n`);
process.exit(fail ? 1 : 0);
