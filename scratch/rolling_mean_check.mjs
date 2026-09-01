// Phase 88-05 check — the velocity trend overlay's rolling mean, and the decimation trap that is
// the one way this plan can be quietly wrong (D3).
//
// Same harness shape as scratch/split_picker_check.mjs / unit_check.mjs (88-03, 88-04): transpile
// with the `typescript` package already in web/node_modules, drop the CJS output inside
// node_modules so `react` resolves by the normal walk-up, require it back.
//
// ⚠ MEASURED LIMITATION inherited from 87-02: recharts renders an EMPTY wrapper under
// renderToStaticMarkup, so the trend LINE itself is not assertable here. Section 6 covers the
// no-regression half (smoothWindowS absent must leave VelocityChart's markup byte-identical, and
// a window must not throw); that the dotted line is VISIBLE and correctly shaped is the plan's
// human-verify. Stated here rather than left as a silent gap.
//
// Run: node scratch/rolling_mean_check.mjs

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

const out = path.join(web, "node_modules", ".rolling-mean-check");
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

compile(path.join(web, "lib", "rollingMean.js"), "rollingMean.js");
compile(path.join(web, "components", "portal", "VelocityChart.js"), "VelocityChart.js");

const { rollingMean } = require(path.join(out, "rollingMean.cjs"));
const VelocityChart = require(path.join(out, "VelocityChart.cjs")).default;

// VelocityChart.js:17 — mirrored here so the trap section decimates exactly as the component does.
const MAX_POINTS = 2000;
const strideOf = (n) => Math.max(1, Math.ceil(n / MAX_POINTS));
const strideBy = (arr, step) => arr.filter((_, i) => i % step === 0);
const ptp = (arr, skip) => {
  const mid = arr.slice(skip, arr.length - skip).filter((v) => v != null);
  return Math.max(...mid) - Math.min(...mid);
};

// ── 1. The window is off, or too narrow to mean anything ─────────────────────
console.log("\nD2/AC-3 — 0.00 s is off, and a sub-sample window is a no-op");
{
  const v = [1, 2, 3, 4, 5];
  check("windowS = 0 returns the input values", JSON.stringify(rollingMean(v, 100, 0)) === JSON.stringify(v));
  check("and returns a COPY, not the same array", rollingMean(v, 100, 0) !== v);
  check("a negative window is off too", JSON.stringify(rollingMean(v, 100, -1)) === JSON.stringify(v));
  check("NaN / undefined is off, not a crash", JSON.stringify(rollingMean(v, 100, NaN)) === JSON.stringify(v));
  // 0.004 s at 100 Hz rounds to 0 samples -> clamped to 1 -> nothing to average.
  check("a window narrower than one sample is a no-op", JSON.stringify(rollingMean(v, 100, 0.004)) === JSON.stringify(v));
}

// ── 2. A constant is preserved everywhere, including the clamped edges ────────
console.log("\nNo edge droop — the clamped span averages fewer samples, never zeros");
{
  const v = new Array(500).fill(1.42);
  const sm = rollingMean(v, 100, 1.0);
  check("length is preserved", sm.length === 500);
  check("a constant returns that constant at every index", sm.every((x) => Math.abs(x - 1.42) < 1e-12));
  check("including index 0 and the last index", Math.abs(sm[0] - 1.42) < 1e-12 && Math.abs(sm[499] - 1.42) < 1e-12);
}

// ── 3. Nulls are skipped, not counted as zeros (AC-6) ────────────────────────
console.log("\nAC-6 — dropouts do not break the line");
{
  // 0.03 s at 100 Hz => N = 3, h = 1: index 1 spans [0, 2].
  const sm = rollingMean([1, null, 3], 100, 0.03);
  check("[1, null, 3] over a 3-wide window gives 2, not 1.33", Math.abs(sm[1] - 2) < 1e-12, `got ${sm[1]}`);
  check("the clamped ends see only their own value", sm[0] === 1 && sm[2] === 3);

  const allNull = rollingMean([null, null, null, null, null], 100, 0.03);
  check("an all-null window yields null, not NaN or 0", allNull.every((x) => x === null));

  // A gap wider than the window: the interior of the gap has no non-null sample in range.
  const gappy = new Array(300).fill(1);
  for (let i = 100; i < 200; i++) gappy[i] = null;
  const smg = rollingMean(gappy, 100, 0.11); // N = 11, h = 5
  check("a gap wider than the window yields null in its interior", smg[150] === null);
  check("and real values resume outside it", Math.abs(smg[50] - 1) < 1e-12 && Math.abs(smg[250] - 1) < 1e-12);
  check("NaN is treated as a gap, not averaged in", rollingMean([1, NaN, 3], 100, 0.03)[1] === 2);
}

// ── 4. The window is CENTRED, not trailing ───────────────────────────────────
console.log("\nCentred, not trailing — a trailing mean would shift every feature later in time");
{
  const v = new Array(101).fill(0);
  v[50] = 1;
  const sm = rollingMean(v, 100, 0.11); // N = 11, h = 5 -> [j-5, j+5]
  check("the impulse spreads BEFORE its index", sm[45] > 0);
  check("and after it, by the same half-width", sm[55] > 0);
  check("and not one sample further either way", sm[44] === 0 && sm[56] === 0);
  check("symmetrically", Math.abs(sm[45] - sm[55]) < 1e-12);
}

// ── 5. THE DECIMATION TRAP (D3 / AC-2) ───────────────────────────────────────
console.log("\nAC-2 — the window means what it says at the session's own rate (D3)");
{
  const FS = 90;
  const N = 4000; // 44.4 s — long enough that VelocityChart's step becomes 2
  const step = strideOf(N);
  check("a 4000-point profile does decimate (step === 2)", step === 2, `step=${step}`);

  // A 2.0 s sine: a 1.0 s centred mean keeps ~64% of its amplitude, a 2.0 s mean cancels it
  // entirely. So smoothing at the wrong rate is not a rounding difference here, it is visible.
  const full = Array.from({ length: N }, (_, i) => 1.5 + 0.4 * Math.sin((2 * Math.PI * (i / FS)) / 2.0));

  const smoothThenStride = strideBy(rollingMean(full, FS, 1.0), step); // CORRECT
  const strideThenSmooth = rollingMean(strideBy(full, step), FS, 1.0); // THE BUG

  check("both orderings yield the same point count", smoothThenStride.length === strideThenSmooth.length);

  const ampCorrect = ptp(smoothThenStride, 200);
  const ampBug = ptp(strideThenSmooth, 200);
  // Peak-to-peak of a centred boxcar over a sine: 2 * 0.4 * |sin(pi*W/T)/(pi*W/T)|.
  // N = round(1.0 * 90) = 90 is even, so the symmetric span is 89 samples = 0.9889 s, giving
  // W/T = 0.4944 and an expected ptp of 0.515. At W = 2 s the same factor is 0, hence ampBug ~ 0.
  check("smoothing at the native rate keeps the 1.00 s attenuation", Math.abs(ampCorrect - 0.515) < 0.01, `ptp=${ampCorrect.toFixed(4)}`);
  check("smoothing AFTER the stride erases the signal (it spans 2.00 s)", ampBug < 0.02, `ptp=${ampBug.toFixed(4)}`);
  check("so the two orderings are NOT interchangeable", Math.abs(ampCorrect - ampBug) > 0.2);

  // Name the failure mode precisely: the buggy path is a 2.00 s window wearing a 1.00 s label.
  const twoSecond = strideBy(rollingMean(full, FS, 2.0), step);
  const mid = (a, b) => Math.max(...a.slice(200, a.length - 200).map((x, i) => Math.abs(x - b[i + 200])));
  const dTo2s = mid(strideThenSmooth, twoSecond);
  const dTo1s = mid(strideThenSmooth, smoothThenStride);
  check("and the buggy one IS the 2.00 s window mislabelled 1.00 s", dTo2s < dTo1s / 10, `d2s=${dTo2s.toFixed(4)} d1s=${dTo1s.toFixed(4)}`);

  // The component's own loop, reproduced: it must compose as smooth-then-stride.
  const sm = rollingMean(full, FS, 1.0);
  const asComponent = [];
  for (let i = 0; i < N; i += step) asComponent.push(sm[i]);
  check("VelocityChart's strided loop reproduces smooth-then-stride", JSON.stringify(asComponent) === JSON.stringify(smoothThenStride));

  // A 20 s swim would NOT have caught this — the reason the synthetic profile above exists.
  check("⚠ a 20 s swim at 89.99 Hz does not decimate (step === 1)", strideOf(1799) === 1);
}

// ── 6. A missing or unknown sample rate (CLAUDE.md: NULL means unknown) ───────
console.log("\nAn unknown rate falls back to annotations.FS_HZ, it does not crash");
{
  const v = new Array(300).fill(2);
  check("fsHz null falls back to 100", rollingMean(v, null, 1.0).every((x) => Math.abs(x - 2) < 1e-12));
  check("fsHz 0 falls back to 100", rollingMean(v, 0, 1.0).every((x) => Math.abs(x - 2) < 1e-12));
  check("fsHz NaN falls back to 100", rollingMean(v, NaN, 1.0).every((x) => Math.abs(x - 2) < 1e-12));
  // At the fallback rate a 1.0 s window is 100 samples: an impulse must spread ~49 either side.
  const imp = new Array(301).fill(0);
  imp[150] = 1;
  const sm = rollingMean(imp, null, 1.0);
  check("and the fallback really is 100 Hz, not 1 sample", sm[110] > 0 && sm[90] === 0);
  check("an empty / missing profile yields an empty array", rollingMean(null, 100, 1.0).length === 0);
}

// ── 7. An absent prop leaves VelocityChart exactly as it was (D5 / AC-3 / AC-7) ─
console.log("\nAC-7 — the /video route and today's chart are untouched");
{
  const n = 1000;
  const time = Array.from({ length: n }, (_, i) => i / 100);
  const velocity = Array.from({ length: n }, (_, i) => 1.4 + 0.3 * Math.sin(i / 20));
  const base = { time, velocity, fsHz: 100 };

  const absent = renderToStaticMarkup(React.createElement(VelocityChart, base));
  const zero = renderToStaticMarkup(React.createElement(VelocityChart, { ...base, smoothWindowS: 0 }));
  check("smoothWindowS absent === smoothWindowS 0, byte for byte", absent === zero);
  check(
    "and passing a window does not throw",
    (() => {
      try {
        renderToStaticMarkup(React.createElement(VelocityChart, { ...base, smoothWindowS: 1.0 }));
        return true;
      } catch {
        return false;
      }
    })()
  );
  check(
    "88-04's spanS still renders alongside it",
    (() => {
      try {
        renderToStaticMarkup(
          React.createElement(VelocityChart, { ...base, smoothWindowS: 1.0, spanS: [2, 5], spanLabel: "0-15 m" })
        );
        return true;
      } catch {
        return false;
      }
    })()
  );
  // ⚠ recharts renders an empty wrapper under SSR (87-02), so the second <Line> is not assertable
  // here. Assert the limit openly rather than pretending the line was checked.
  check("⚠ recharts wrapper is empty under SSR — the dotted line is human-verify step 3", !absent.includes("recharts-line"));
}

// ── 8. The source-text rule Task 2 must not silently lose ────────────────────
console.log("\nD3 as a source-text assertion — smoothing must precede the stride");
{
  const src = fs.readFileSync(path.join(web, "components", "portal", "VelocityChart.js"), "utf8");
  const iSmooth = src.indexOf("rollingMean(");
  const iStride = src.indexOf("i += step");
  check("VelocityChart calls rollingMean", iSmooth > 0);
  check("and it calls it BEFORE the strided loop", iSmooth > 0 && iStride > 0 && iSmooth < iStride);
  check("smoothWindowS is in the data memo's dependency array", /\[[^\]]*smoothWindowS[^\]]*\]/.test(src));
  check("and so is fsHz, which was not a dependency before 88-05", /\[\s*time,\s*velocity,\s*unitFactor,\s*fsHz,\s*smoothWindowS\s*\]/.test(src));
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
