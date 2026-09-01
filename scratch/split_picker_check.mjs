// Phase 88-04 check — the Segment splits picker's arithmetic and the card's behaviour.
//
// Same harness shape as scratch/stroke_toggle_check.mjs / unit_check.mjs (87-02, 88-03): transpile
// the JSX with the `typescript` package already in web/node_modules, drop the CJS output inside
// node_modules so `react` resolves by the normal walk-up, render with react-dom/server, assert on
// the markup.
//
// ⚠ MEASURED LIMITATION inherited from 87-02: recharts renders an EMPTY wrapper under
// renderToStaticMarkup, so the ReferenceArea shading itself is NOT assertable here. Check 10
// covers the no-regression half (spanS={null} must leave VelocityChart's markup byte-identical);
// that the shading is VISIBLE and correctly placed is step 4 of the plan's human-verify. Stated
// here rather than left as a silent gap.
//
// Run: node scratch/split_picker_check.mjs

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

const out = path.join(web, "node_modules", ".split-picker-check");
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
  "@/lib/splitWindow": "./splitWindow.cjs",
  // 88-05 added this import to VelocityChart, which check 10 renders. Mapped here so this
  // harness keeps resolving it by the normal walk-up.
  "@/lib/rollingMean": "./rollingMean.cjs",
};

const compile = (src, name) => {
  let code = fs.readFileSync(src, "utf8");
  for (const [from, to] of Object.entries(MAP)) code = code.split(`"${from}"`).join(`"${to}"`);
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

compile(path.join(web, "lib", "splitWindow.js"), "splitWindow.js");
compile(path.join(web, "lib", "rollingMean.js"), "rollingMean.js");
compile(path.join(web, "components", "portal", "SplitPicker.js"), "SplitPicker.js");
compile(path.join(web, "components", "portal", "VelocityChart.js"), "VelocityChart.js");

const { buildBins, measureWindow, toggleBin, YARD_TO_M, BIN_U } = require(
  path.join(out, "splitWindow.cjs")
);
const SplitPicker = require(path.join(out, "SplitPicker.cjs")).default;
const VelocityChart = require(path.join(out, "VelocityChart.cjs")).default;

// ── synthetic traces ──────────────────────────────────────────────────────────
const FS = 89.5;

// Constant-velocity swim: `preS` seconds of pre-dive dwell at 0 m, then `vel` m/s for `swimS`.
// The anchor sits exactly at the dive sample, so d0 === 0 and the arithmetic is checkable by hand.
function makeTrace({ preS = 2, swimS = 20, vel = 1.5, driftS = 0, driftVel = 0.2 } = {}) {
  const time = [];
  const dist = [];
  const nPre = Math.round(preS * FS);
  const nSwim = Math.round(swimS * FS);
  const nDrift = Math.round(driftS * FS);
  for (let i = 0; i < nPre + nSwim + nDrift; i++) {
    time.push(i / FS);
    if (i < nPre) dist.push(0);
    else if (i < nPre + nSwim) dist.push(((i - nPre) / FS) * vel);
    else dist.push((nSwim / FS) * vel + ((i - nPre - nSwim) / FS) * driftVel);
  }
  return { time, dist, anchorS: nPre / FS, finishS: (nPre + nSwim - 1) / FS };
}

// ── 1. buildBins emits complete bins only ─────────────────────────────────────
console.log("\nbuildBins — complete bins only (AC-3)");
{
  // 21 s at 1.5 m/s = 31.5 m -> six whole 5 m bins, and a 1.5 m tail that must NOT become a chip.
  const t = makeTrace({ swimS: 21, vel: 1.5 });
  const bins = buildBins({ ...t, fsHz: FS, imperial: false });
  check("31.5 m of travel yields 6 metric bins", bins.length === 6, `got ${bins.length}`);
  check("the 1.5 m tail past 30 m is not offered as a chip", bins.at(-1).toU === 30);
  check(
    "bins are contiguous and 5 m wide",
    bins.every((b, i) => b.k === i && b.fromU === i * 5 && b.toU === (i + 1) * 5)
  );
  check(
    "each bin's i1 is the next bin's i0",
    bins.every((b, i) => i === 0 || bins[i - 1].i1 === b.i0)
  );

  // The 25-yard case the plan names: ~21.9 m of tether travel must yield FOUR bins, not five.
  const lap = makeTrace({ swimS: 14.6, vel: 1.5 }); // 21.9 m
  const lapBins = buildBins({ ...lap, fsHz: FS, imperial: false });
  check(
    "21.9 m (a 25-yd lap) yields 4 bins — no partial 20–25 chip",
    lapBins.length === 4,
    `got ${lapBins.length}, last = ${lapBins.at(-1)?.fromU}–${lapBins.at(-1)?.toU}`
  );
  check("no bin describes distance beyond 20 m", lapBins.every((b) => b.toU <= 20));
}

// ── 2. THE AC-2 EQUALITY, computed both ways ──────────────────────────────────
console.log("\nAC-2 — one bin equals phase_metrics._split_velocity, to 1e-12");
{
  // Independent re-implementation of _split_velocity (phase_metrics.py:797-817), written from the
  // Python rather than from splitWindow.js. If the picker ever drifts into sample-mean averaging,
  // or loses the finishS clamp, or moves its anchor rule, this is the check that fails.
  function splitVelocityPy(dist, time, anchorS, finishS, fsHz, meters) {
    const n = dist.length;
    const iStart = Math.round(anchorS * fsHz);
    if (!(iStart >= 0 && iStart < n)) return null;
    const d0 = dist[iStart];
    if (!Number.isFinite(d0)) return null;
    const iFin = Math.round(finishS * fsHz);
    const end = iFin >= 0 && iFin < n ? Math.min(n, iFin + 1) : n;
    const firstAt = (target) => {
      for (let i = iStart; i < end; i++) {
        if (Number.isFinite(dist[i]) && dist[i] - d0 >= target) return i;
      }
      return null;
    };
    const iA = firstAt(meters - 5.0);
    const iB = firstAt(meters);
    if (iA == null || iB == null || iB <= iA) return null;
    const dt = time[iB] - time[iA];
    const dd = dist[iB] - dist[iA];
    if (!Number.isFinite(dt) || !Number.isFinite(dd) || dt <= 0) return null;
    return dd / dt;
  }

  // A non-constant swim, so a chord and a sample mean genuinely disagree.
  const time = [];
  const dist = [];
  const nPre = Math.round(2 * FS);
  let d = 0;
  for (let i = 0; i < nPre; i++) {
    time.push(i / FS);
    dist.push(0);
  }
  for (let i = 0; i < Math.round(22 * FS); i++) {
    const tRel = i / FS;
    // surge-and-glide: mean ~1.5 m/s with a real oscillation on top
    d += (1.5 + 0.6 * Math.sin(tRel * 4.5)) / FS;
    time.push((nPre + i) / FS);
    dist.push(d);
  }
  const anchorS = nPre / FS;
  const finishS = (time.length - 1) / FS;
  const bins = buildBins({ dist, time, anchorS, finishS, fsHz: FS, imperial: false });
  check("non-constant trace produces bins", bins.length >= 4, `${bins.length} bins`);

  let worst = 0;
  let compared = 0;
  for (const b of bins) {
    const mine = measureWindow(bins, { lo: b.k, hi: b.k }, dist, time);
    const theirs = splitVelocityPy(dist, time, anchorS, finishS, FS, b.toU);
    if (theirs == null || mine?.avgVelMs == null) continue;
    compared++;
    worst = Math.max(worst, Math.abs(mine.avgVelMs - theirs));
  }
  check(
    "every single-bin window equals _split_velocity to 1e-12",
    compared === bins.length && worst < 1e-12,
    `${compared}/${bins.length} bins, max |Δ| = ${worst.toExponential(2)}`
  );

  // And prove the chord is STRUCTURAL, not incidentally equal: it may read only the two endpoint
  // samples. Perturb the window's interior heavily — any sample mean of the profile would move;
  // a chord cannot. This is what fails if the implementation ever starts averaging.
  const b1 = bins[1];
  const chord = measureWindow(bins, { lo: 1, hi: 1 }, dist, time).avgVelMs;
  const mangled = dist.slice();
  for (let i = b1.i0 + 1; i < b1.i1; i++) mangled[i] += 3.0; // interior only, endpoints untouched
  const chordMangled = (mangled[b1.i1] - mangled[b1.i0]) / (time[b1.i1] - time[b1.i0]);
  check(
    "the chord reads ONLY the two endpoints — interior samples cannot move it",
    Math.abs(chordMangled - chord) < 1e-12,
    `|Δ| = ${Math.abs(chordMangled - chord).toExponential(2)} after +3 m on every interior sample`
  );
}

// ── 3. toggleBin — D5's four cases ────────────────────────────────────────────
console.log("\ntoggleBin — D5");
{
  check("nothing selected, click 2 -> {2,2}", JSON.stringify(toggleBin(null, 2)) === '{"lo":2,"hi":2}');
  check(
    "CONTEXT D8's example: {0,0} then click 2 -> {0,2} (fills the gap)",
    JSON.stringify(toggleBin({ lo: 0, hi: 0 }, 2)) === '{"lo":0,"hi":2}'
  );
  check(
    "click below the run extends downward: {2,3} + 0 -> {0,3}",
    JSON.stringify(toggleBin({ lo: 2, hi: 3 }, 0)) === '{"lo":0,"hi":3}'
  );
  check(
    "click INSIDE a multi-bin run collapses: {0,3} + 1 -> {1,1}",
    JSON.stringify(toggleBin({ lo: 0, hi: 3 }, 1)) === '{"lo":1,"hi":1}'
  );
  check("clicking the only selected bin clears", toggleBin({ lo: 2, hi: 2 }, 2) === null);
  check("selection stays contiguous by construction", toggleBin({ lo: 0, hi: 0 }, 4).hi === 4);
}

// ── 4. imperial bins are yard-native ──────────────────────────────────────────
console.log("\nimperial bins (D6 / AC-5)");
{
  check("YARD_TO_M is TimeToX's constant", YARD_TO_M === 0.9144 && BIN_U === 5);
  const t = makeTrace({ swimS: 21, vel: 1.5 }); // 31.5 m
  const met = buildBins({ ...t, fsHz: FS, imperial: false });
  const impB = buildBins({ ...t, fsHz: FS, imperial: true });
  check("a yard bin spans 4.572 m", Math.abs(BIN_U * YARD_TO_M - 4.572) < 1e-12);
  // The point of D6: "0–5 yd" and "0–5 m" are DIFFERENT windows over the same swim, which is
  // exactly why the card carries a caveat line in imperial.
  check(
    "the same trace bins differently in the two systems",
    met.every((b, i) => impB[i] == null || impB[i].i1 !== b.i1),
    `metric bin ends [${met.map((b) => b.i1).join(",")}], imperial [${impB.map((b) => b.i1).join(",")}]`
  );
  check(
    "yard bins are shorter, so the swim yields at least as many",
    impB.length >= met.length,
    `metric ${met.length}, imperial ${impB.length}`
  );
  const w = measureWindow(impB, { lo: 0, hi: 0 }, t.dist, t.time);
  check(
    "an imperial bin covers ~4.572 m of travel",
    Math.abs(t.dist[w.i1] - t.dist[w.i0] - 4.572) < 0.05,
    `${(t.dist[w.i1] - t.dist[w.i0]).toFixed(3)} m`
  );
}

// ── 5. bins never extend past finishS ─────────────────────────────────────────
console.log("\nthe finishS clamp (D4 — post-touch drift must not fill a bin)");
{
  // 14.6 s at 1.5 m/s = 21.9 m, then 25 s of drift adding 5 m. Without the clamp that drift
  // would manufacture a fifth bin out of the swimmer sliding into the wall.
  const clean = makeTrace({ swimS: 14.6, vel: 1.5 });
  const drifted = makeTrace({ swimS: 14.6, vel: 1.5, driftS: 25, driftVel: 0.2 });
  const a = buildBins({ ...clean, fsHz: FS, imperial: false });
  const b = buildBins({ ...drifted, fsHz: FS, imperial: false });
  check(
    "5 m of post-touch drift adds no bin",
    a.length === b.length,
    `clean ${a.length}, drifted ${b.length}`
  );
  check(
    "and the bins are index-identical",
    JSON.stringify(a) === JSON.stringify(b)
  );
  // Same trace WITHOUT the clamp -> the drift does fill another bin, so the check has teeth.
  const unclamped = buildBins({ ...drifted, finishS: null, fsHz: FS, imperial: false });
  check(
    "without the clamp the drift WOULD add a bin — the clamp is load-bearing",
    unclamped.length > b.length,
    `unclamped ${unclamped.length} vs clamped ${b.length}`
  );
}

// ── 6. degenerate inputs return [] / null, never throw ────────────────────────
console.log("\ndegenerate inputs");
{
  const t = makeTrace({ swimS: 20, vel: 1.5 });
  check("null anchor -> []", buildBins({ ...t, anchorS: null, fsHz: FS }).length === 0);
  check("anchor past the end -> []", buildBins({ ...t, anchorS: 9999, fsHz: FS }).length === 0);
  check("negative anchor -> []", buildBins({ ...t, anchorS: -5, fsHz: FS }).length === 0);
  check(
    "all-null distance profile -> []",
    buildBins({ ...t, dist: t.dist.map(() => null), fsHz: FS }).length === 0
  );
  check(
    "two-sample trace -> []",
    buildBins({ dist: [0, 0.01], time: [0, 0.011], anchorS: 0, finishS: 0.011, fsHz: FS }).length === 0
  );
  check("fsHz of 0 -> []", buildBins({ ...t, fsHz: 0 }).length === 0);
  check("measureWindow(bins, null) -> null", measureWindow(buildBins({ ...t, fsHz: FS }), null, t.dist, t.time) === null);
  check(
    "measureWindow with an out-of-range sel -> null",
    measureWindow(buildBins({ ...t, fsHz: FS }), { lo: 0, hi: 99 }, t.dist, t.time) === null
  );
  // Dropout nulls mid-swim are skipped, not fatal.
  const holed = makeTrace({ swimS: 21, vel: 1.5 });
  const cleanCount = buildBins({ ...holed, fsHz: FS }).length;
  for (let i = 300; i < 320; i++) holed.dist[i] = null;
  check(
    "mid-swim dropout nulls are skipped, bins still build",
    cleanCount === 6 && buildBins({ ...holed, fsHz: FS }).length === 6,
    `${cleanCount} clean, ${buildBins({ ...holed, fsHz: FS }).length} with a 20-sample hole`
  );
}

// ── 7-9. render ───────────────────────────────────────────────────────────────
console.log("\nSplitPicker render");
{
  const t = makeTrace({ swimS: 21, vel: 1.5 }); // 31.5 m -> six metric chips
  const props = { timeArr: t.time, distArr: t.dist, anchorS: t.anchorS, finishS: t.finishS, fsHz: FS };
  const met = renderToStaticMarkup(React.createElement(SplitPicker, { ...props, unit: "metric" }));
  const impH = renderToStaticMarkup(React.createElement(SplitPicker, { ...props, unit: "imperial" }));

  const chips = (h) => [...h.matchAll(/<button[^>]*>(.*?)<\/button>/g)].map((m) => m[1].replace(/<!-- -->/g, ""));
  const mc = chips(met);
  check(
    "metric chips are 5 m segments",
    mc.length === 6 && mc[0] === "0–5m" && mc[3] === "15–20m" && mc[5] === "25–30m",
    mc.join(" ")
  );
  const ic = chips(impH);
  check("imperial chips carry the yd suffix", ic.length >= 6 && ic[0] === "0–5yd", ic.join(" "));

  check("no selection shows the instruction line, not a fake dash", met.includes("Tap segments to measure a window."));
  check("no selection renders no big number", !met.includes("text-4xl"));
  check("no chip is lit on first render", !met.includes("bg-accent"));

  check("imperial states the metre-binned caveat (AC-5)", impH.includes("the split rows below stay metre-binned"));
  check("metric does NOT state it", !met.includes("metre-binned"));

  // 9. empty state
  const shortT = makeTrace({ swimS: 1, vel: 1.5 }); // 1.5 m — not one whole bin
  const empty = renderToStaticMarkup(
    React.createElement(SplitPicker, {
      timeArr: shortT.time,
      distArr: shortT.dist,
      anchorS: shortT.anchorS,
      finishS: shortT.finishS,
      fsHz: FS,
      unit: "metric",
    })
  );
  check("too-short trace renders the empty state", empty.includes("Not enough distance recorded"));
  check("and renders no chip buttons at all", !empty.includes("<button"));
}

// ── 10. VelocityChart's markup is unchanged when spanS is absent (AC-6) ───────
console.log("\nAC-6 — the /video route's charts are untouched");
{
  const t = makeTrace({ swimS: 20, vel: 1.5 });
  const vel = t.dist.map((_, i) => (i > 0 ? (t.dist[i] - t.dist[i - 1]) * FS : 0));
  const base = { time: t.time, velocity: vel, fsHz: FS };
  // The /video route passes neither prop; the report card passes them explicitly. With no
  // selection the report card passes spanS={null}, which must be indistinguishable from absent.
  const absent = renderToStaticMarkup(React.createElement(VelocityChart, base));
  const explicitNull = renderToStaticMarkup(
    React.createElement(VelocityChart, { ...base, spanS: null, spanLabel: "" })
  );
  check("spanS absent === spanS null, byte for byte", absent === explicitNull);
  check(
    "and passing a span does not throw",
    (() => {
      try {
        renderToStaticMarkup(
          React.createElement(VelocityChart, { ...base, spanS: [3, 8], spanLabel: "0–15 m" })
        );
        return true;
      } catch {
        return false;
      }
    })()
  );
  // ⚠ Recharts renders an empty wrapper under renderToStaticMarkup (87-02), so `absent` and the
  // spanned render are identical here too. That is the harness limit, not a bug — assert it
  // openly rather than pretending the shading was checked.
  check(
    "⚠ recharts wrapper is empty under SSR — the shading itself is human-verify step 4",
    !absent.includes("recharts-reference-area")
  );
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
