// Phase 84-04 GESTURE check for VelocityChart's two pan responders.
//
// ⚠ WHAT THIS PROVES: that both `PanResponder.create` configs still declare
// `onPanResponderTerminationRequest: () => false`, and that neither lost its other callbacks.
// ⚠ WHAT IT DOES NOT PROVE: that the gesture behaves. It never mounts the component and never
// touches a screen. Only the on-device verify proves a brush drag survives vertical drift.
//
// The mobile repo has no test runner and no linter (package.json scripts = start/android/ios/web),
// so the harness lives here, following the 83-05 / 85-01 / 84-03 precedent. Unlike 84-03's pure
// indicators.js, VelocityChart.js imports react-native and react-native-svg, so it cannot be
// imported headlessly by rewriting one specifier — this parses the source and asserts on the AST,
// reusing the `typescript` package already in web/node_modules (no new dependency in either repo).
//
// Check 4 is a self-test: it strips the property from an in-memory copy and asserts the checks
// FAIL on the mutant. A guard that passes on the unfixed source is worse than no guard.
//
// Run: node scratch/gesture_check.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..");
const web = path.resolve(repo, "web");
const require = createRequire(path.join(web, "package.json"));
const ts = require("typescript");

const target = path.resolve(repo, "..", "swimnetics-mobile", "src", "components", "VelocityChart.js");
const source = fs.readFileSync(target, "utf8");

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

const REQUIRED = [
  "onPanResponderGrant",
  "onPanResponderMove",
  "onPanResponderRelease",
  "onPanResponderTerminate",
];

// ---------- AST extraction ----------

// Returns one descriptor per PanResponder.create(...) call, in source order:
//   { line, keys: [prop names], refusesTermination: bool }
function inspect(code, fileName) {
  const sf = ts.createSourceFile(fileName, code, ts.ScriptTarget.ES2022, true, ts.ScriptKind.JS);
  const found = [];

  const walk = (node) => {
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      ts.isIdentifier(node.expression.expression) &&
      node.expression.expression.text === "PanResponder" &&
      node.expression.name.text === "create"
    ) {
      const arg = node.arguments[0];
      const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
      if (!arg || !ts.isObjectLiteralExpression(arg)) {
        found.push({ line, keys: [], refusesTermination: false, literal: false });
      } else {
        const keys = [];
        let refusesTermination = false;
        for (const p of arg.properties) {
          const name = p.name && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name)) ? p.name.text : null;
          if (!name) continue;
          keys.push(name);
          if (name !== "onPanResponderTerminationRequest") continue;
          // Accept `() => false` and `function () { return false; }`; nothing looser.
          const fn = ts.isPropertyAssignment(p) ? p.initializer : ts.isMethodDeclaration(p) ? p : null;
          if (!fn) continue;
          if (ts.isArrowFunction(fn) && fn.body.kind === ts.SyntaxKind.FalseKeyword) {
            refusesTermination = true;
          } else if (fn.body && ts.isBlock(fn.body)) {
            const only = fn.body.statements.length === 1 ? fn.body.statements[0] : null;
            if (only && ts.isReturnStatement(only) && only.expression?.kind === ts.SyntaxKind.FalseKeyword) {
              refusesTermination = true;
            }
          }
        }
        found.push({ line, keys, refusesTermination, literal: true });
      }
    }
    ts.forEachChild(node, walk);
  };

  walk(sf);
  return found;
}

// Checks 1-3 over an arbitrary source string. Returns { ok, notes } so the self-test can reuse it.
function evaluate(code, fileName) {
  const configs = inspect(code, fileName);
  const notes = [];
  let ok = true;

  if (configs.length !== 2) {
    ok = false;
    notes.push(`expected exactly 2 PanResponder.create calls, found ${configs.length}`);
    return { ok, notes, configs };
  }

  for (const [i, c] of configs.entries()) {
    const label = i === 0 ? "chart-body" : "brush-strip";
    if (!c.literal) {
      ok = false;
      notes.push(`${label}: argument is not an object literal`);
      continue;
    }
    if (!c.refusesTermination) {
      ok = false;
      notes.push(`${label}: no onPanResponderTerminationRequest returning false`);
    }
    const missing = REQUIRED.filter((k) => !c.keys.includes(k));
    if (missing.length) {
      ok = false;
      notes.push(`${label}: missing ${missing.join(", ")}`);
    }
  }

  return { ok, notes, configs };
}

// ---------- checks against the real source ----------

console.log("\nVelocityChart.js  —  responder configuration");
const real = evaluate(source, "VelocityChart.js");
const [body, brush] = real.configs;

check(
  "exactly two PanResponder.create configs (a third would be unguarded)",
  real.configs.length === 2,
  `found ${real.configs.length}${real.configs.length ? " at lines " + real.configs.map((c) => c.line).join(", ") : ""}`
);

if (real.configs.length === 2) {
  check("chart-body config refuses termination (() => false)", body.refusesTermination, `line ${body.line}`);
  check("brush-strip config refuses termination (() => false)", brush.refusesTermination, `line ${brush.line}`);

  const bodyMissing = REQUIRED.filter((k) => !body.keys.includes(k));
  const brushMissing = REQUIRED.filter((k) => !brush.keys.includes(k));
  check(
    "chart-body kept Grant/Move/Release/Terminate",
    bodyMissing.length === 0,
    bodyMissing.length ? "missing " + bodyMissing.join(", ") : `${body.keys.length} props`
  );
  check(
    "brush-strip kept Grant/Move/Release/Terminate",
    brushMissing.length === 0,
    brushMissing.length ? "missing " + brushMissing.join(", ") : `${brush.keys.length} props`
  );
}

// ---------- self-test: the mutant MUST fail ----------

console.log("\nself-test  —  checks are not vacuous");
const mutant = source
  .split("\n")
  .filter((l) => !/onPanResponderTerminationRequest\s*:/.test(l))
  .join("\n");

check(
  "mutant differs from the real source (the strip actually removed lines)",
  mutant !== source,
  `${source.split("\n").length - mutant.split("\n").length} line(s) stripped`
);

const mutated = evaluate(mutant, "VelocityChart.mutant.js");
check(
  "checks FAIL on a copy with onPanResponderTerminationRequest stripped",
  mutated.ok === false,
  mutated.ok ? "MUTANT PASSED — this guard proves nothing" : mutated.notes.join("; ")
);

// ---------- tally ----------

console.log(`\n${fail === 0 ? "ALL PASS" : "FAILURES"}  ${pass} passed, ${fail} failed`);
if (fail) {
  console.log("failed: " + failed.join(", "));
  process.exit(1);
}
console.log("Configuration is present. Gesture behaviour is NOT proven here — verify on device.");
