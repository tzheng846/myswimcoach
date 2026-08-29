// scratch harness for Phase 83-05's pure lib (cycleTraces, over cycleShape + cycleBands).
//
// `web/package.json` has no test runner and no `"type": "module"`, so node treats web/lib/*.js as
// CJS and cannot import them despite their ESM syntax. Precedent: 75-05's engine checks and
// 83-03's `shape_checks.mjs`. This copies each lib to a .mjs beside this file and imports the copy,
// so the libs stay untouched and the checks stay throwaway.
//
// Run: node scratch/overlay_checks.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const libDir = path.resolve(here, "..", "web", "lib");
for (const name of ["cycleShape", "cycleBands", "cycleTraces"]) {
  fs.copyFileSync(path.join(libDir, `${name}.js`), path.join(here, `_${name}.mjs`));
}
// cycleTraces imports "./cycleShape" — the copies sit side by side, so that specifier only resolves
// once it is pointed at the copy. Cheaper than a loader hook.
{
  const p = path.join(here, "_cycleTraces.mjs");
  fs.writeFileSync(p, fs.readFileSync(p, "utf8").replace("./cycleShape", "./_cycleShape.mjs"));
}
const { buildTraces } = await import("./_cycleTraces.mjs");
const { buildBands } = await import("./_cycleBands.mjs");
const { POINTS, MIN_ITEMS } = await import("./_cycleShape.mjs");

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

// ---------- fixture helpers ----------

// A plausible stroke profile: one hump, non-zero floor.
const profile = (L, scale = 1) =>
  Array.from({ length: L }, (_, i) => scale * (0.6 + 0.9 * Math.sin(Math.PI * (i / (L - 1))) ** 2));

// Lay profiles end to end into one velocity array + the item rows that index into it.
// A 3-sample gap between items mirrors the real trace, where bands do not abut.
function layout(profiles, key = null) {
  const velocity = [];
  const items = [];
  profiles.forEach((p, i) => {
    const start = velocity.length;
    velocity.push(...p);
    const item = { start_idx: start, end_idx: velocity.length, duration_s: p.length / FS };
    if (key) item[key] = i;
    items.push(item);
    velocity.push(0.2, 0.2, 0.2);
  });
  return { velocity, items };
}

const nsOf = (rows) => rows.map((r) => r.n).join(",");

// ---------- 1. gutter rows are identical across both modes ----------

{
  const { velocity, items } = layout([profile(24), profile(30), profile(21), profile(27), profile(25), profile(23)]);
  const sec = buildTraces(items, velocity, { fsHz: FS, mode: "seconds" });
  const nor = buildTraces(items, velocity, { fsHz: FS, mode: "normalized" });
  check("gutter row COUNT identical across modes", sec.rows.length === nor.rows.length, `${sec.rows.length} vs ${nor.rows.length}`);
  check("gutter row NUMBERS + order identical across modes", nsOf(sec.rows) === nsOf(nor.rows), nsOf(sec.rows));
  check("all 6 traces drawable in seconds", sec.traces.length === 6);
  check("all 6 traces drawable normalized", nor.traces.length === 6);
  check("normalized traces are POINTS long", nor.traces.every((t) => t.points.length === POINTS), `POINTS=${POINTS}`);
  check("maxDuration is the longest span", Math.abs(sec.maxDuration - 30 / FS) < 1e-9, sec.maxDuration.toFixed(4));
}

// ---------- 2. `n` matches buildBands for both array shapes ----------

for (const key of ["cycle_num", "kick_num"]) {
  const { velocity, items } = layout([profile(24), profile(30), profile(21)], key);
  const t = buildTraces(items, velocity, { fsHz: FS, mode: "seconds" });
  const b = buildBands(items, { fsHz: FS, i0: 0, i1: velocity.length - 1 });
  check(
    `n matches buildBands for a ${key} array`,
    nsOf(t.rows) === b.map((x) => x.n).join(","),
    `${nsOf(t.rows)} vs ${b.map((x) => x.n).join(",")}`
  );
}

// A cycle_num array that does NOT start at 0 must carry its own numbering through, not renumber.
{
  const { velocity, items } = layout([profile(24), profile(30), profile(21)]);
  items.forEach((it, i) => (it.cycle_num = i + 4));
  const t = buildTraces(items, velocity, { fsHz: FS, mode: "seconds" });
  check("stored cycle_num wins over array position", nsOf(t.rows) === "5,6,7", nsOf(t.rows));
}

// ---------- 3. dropouts: drawn in seconds, listed-but-absent normalized ----------

{
  const { velocity, items } = layout([profile(24), profile(30), profile(21), profile(27), profile(25)]);
  // punch a hole in the middle of item 1 (n = 2)
  velocity[items[1].start_idx + 10] = NaN;
  const sec = buildTraces(items, velocity, { fsHz: FS, mode: "seconds" });
  const nor = buildTraces(items, velocity, { fsHz: FS, mode: "normalized" });

  const secRow = sec.rows.find((r) => r.n === 2);
  const norRow = nor.rows.find((r) => r.n === 2);
  const secTrace = sec.traces.find((t) => t.n === 2);

  check("dropout trace IS drawn in seconds mode", !!secTrace && secRow.available === true);
  check("dropout trace carries a pen-up break", !!secTrace && secTrace.points.some((p) => p === null));
  check("dropout trace is ABSENT from the normalized pack", !nor.traces.some((t) => t.n === 2), `${nor.traces.length} traces`);
  check("dropout row still LISTED normalized, marked unavailable", !!norRow && norRow.available === false && norRow.reason === "dropout");
  check("dropout does not renumber the rows after it", nsOf(sec.rows) === "1,2,3,4,5" && nsOf(nor.rows) === "1,2,3,4,5");
}

// ---------- 4. median gating ----------

{
  const five = layout([profile(24), profile(30), profile(21), profile(27), profile(25)]);
  const four = layout([profile(24), profile(30), profile(21), profile(27)]);
  const n5 = buildTraces(five.items, five.velocity, { fsHz: FS, mode: "normalized" });
  const n4 = buildTraces(four.items, four.velocity, { fsHz: FS, mode: "normalized" });
  const s5 = buildTraces(five.items, five.velocity, { fsHz: FS, mode: "seconds" });
  check(`median present at MIN_ITEMS (${MIN_ITEMS}) traces`, Array.isArray(n5.median) && n5.median.length === POINTS);
  check("median null below MIN_ITEMS traces", n4.median === null, `${n4.traces.length} traces`);
  check("median NEVER computed in seconds mode", s5.median === null);
  check("median x-grid spans 0..1", n5.median[0][0] === 0 && Math.abs(n5.median[POINTS - 1][0] - 1) < 1e-12);
  // A pointwise median of same-shape traces must sit inside their value range at every point.
  const lo = Math.min(...n5.traces.map((t) => t.points[25][1]));
  const hi = Math.max(...n5.traces.map((t) => t.points[25][1]));
  check("median value lies within the pack at midpoint", n5.median[25][1] >= lo - 1e-12 && n5.median[25][1] <= hi + 1e-12);
}

// ---------- 5. breakout row ----------

{
  const { velocity, items } = layout([profile(24), profile(30), profile(21)]);
  const off = buildTraces(items, velocity, { fsHz: FS, mode: "seconds" });
  const on = buildTraces(items, velocity, { fsHz: FS, mode: "seconds", excludeBreakout: true });
  check("no breakout row unless asked", nsOf(off.rows) === "1,2,3", nsOf(off.rows));
  check("breakout row is prepended as n:0", nsOf(on.rows) === "0,1,2,3", nsOf(on.rows));
  check("breakout row is inert", on.rows[0].available === false && on.rows[0].reason === "breakout");
  check("breakout adds NO trace", on.traces.length === off.traces.length && !on.traces.some((t) => t.n === 0));
  const onNorm = buildTraces(items, velocity, { fsHz: FS, mode: "normalized", excludeBreakout: true });
  check("breakout row survives the mode switch unchanged", nsOf(onNorm.rows) === nsOf(on.rows), nsOf(onNorm.rows));
}

// ---------- 6. degenerate inputs ----------

{
  const one = layout([profile(24)]);
  const none = buildTraces([], one.velocity, { fsHz: FS, mode: "seconds" });
  check("empty items -> no rows, no traces", none.rows.length === 0 && none.traces.length === 0);

  const t1 = buildTraces(one.items, one.velocity, { fsHz: FS, mode: "seconds" });
  check("single item -> 1 row, 1 trace (component gates at <2, not the lib)", t1.rows.length === 1 && t1.traces.length === 1);

  check("null items array -> empty", buildTraces(null, one.velocity, { fsHz: FS }).traces.length === 0);
  check("no velocity -> empty", buildTraces(one.items, [], { fsHz: FS }).traces.length === 0);
  check("bad fsHz -> empty", buildTraces(one.items, one.velocity, { fsHz: 0 }).traces.length === 0);

  // A span of 1 sample cannot be a line.
  const shortItems = [{ start_idx: 0, end_idx: 1, duration_s: 0.01 }, ...one.items];
  const ts = buildTraces(shortItems, one.velocity, { fsHz: FS, mode: "seconds" });
  check("1-sample span -> row listed, marked too-short, no trace", ts.rows[0].reason === "too-short" && !ts.traces.some((t) => t.n === 1));

  // A null entry mid-array is skipped entirely, exactly like buildBands does.
  const tn = buildTraces([null, ...one.items], one.velocity, { fsHz: FS, mode: "seconds" });
  check("null item is skipped, later items keep array-position n", nsOf(tn.rows) === "2", nsOf(tn.rows));

  // Entirely non-finite span: not drawable in EITHER mode.
  const deadVel = [...one.velocity];
  for (let i = 0; i < 10; i++) deadVel[i] = NaN;
  const deadItems = [{ start_idx: 0, end_idx: 10, duration_s: 0.1 }];
  const ds = buildTraces(deadItems, deadVel, { fsHz: FS, mode: "seconds" });
  const dn = buildTraces(deadItems, deadVel, { fsHz: FS, mode: "normalized" });
  check("all-dropout span drawable in neither mode", ds.traces.length === 0 && dn.traces.length === 0 && ds.rows[0].reason === "dropout");
}

console.log(`\n${pass}/${pass + fail} checks passed${fail ? `  (${fail} FAILED)` : ""}`);
process.exit(fail ? 1 : 0);
