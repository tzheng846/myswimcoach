// Phase 90-01 check — the pure leaderboard ranking core.
// Phase 90-03 added section 7 — the BOARD RENDER, through the real LeaderboardBoard component.
//
// Sections 1–6 need nothing but a bare import: web/lib/leaderboard.js is plain ESM with no JSX and
// no "@/" alias imports (90-01 AC-6). Section 7 uses the standing render pattern from
// scratch/unit_check.mjs / split_picker_check.mjs — transpile the JSX with the `typescript` package
// already in web/node_modules, drop the CJS output inside node_modules so `react` resolves by the
// normal walk-up, render with react-dom/server, assert on the markup, then remove the staging
// directory. Still no auth, no network and no dev server.
//
// ⚠ MEASURED LIMITATION OF SECTION 7, stated rather than left silent: `renderToStaticMarkup` never
// runs effects and never dispatches a click, so `expanded` cannot be toggled from outside. The
// expanded branch is covered the 87-02 way — the harness rewrites the ONE state initializer to a
// global while transpiling its own private copy, and asserts on the exact initializer text so the
// rewrite fails loudly if that line ever moves. Production source is untouched. That the BUTTON
// actually flips the board when clicked is step 4 of 90-03's human-verify.
//
// Run: node scratch/leaderboard_check.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

import {
  DEFAULT_N,
  LEADERBOARD_METRICS,
  MIN_DIST_M,
  SESSION_SELECT,
  isEligible,
  lastNMean,
  metricByKey,
  metricValue,
  rankBoard,
} from "../web/lib/leaderboard.js";
import { M_TO_YD, displayUnit } from "../web/lib/unitConvert.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const LIB = path.resolve(here, "..", "web", "lib", "leaderboard.js");

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
const near = (a, b, eps = 1e-9) => a != null && Math.abs(a - b) < eps;

// ─── 1. AC-1: lap time is derived from boundaries, never read from the stored scalar ───────────
console.log("\n1. AC-1  derived lap time");
{
  // The stored scalar on this fixture is 39.0 — the firmware's fixed record length. The swim is
  // 15.1 s. If metricValue ever reads the scalar, this check reports 39.
  const row = { dive_start_s: 4.0, finish_s: 19.1, lap_time_s: 39.0 };
  const v = metricValue(row, "elapsed_s");
  check("elapsed_s = finish_s − dive_start_s, not the stored 39.0", near(v, 15.1, 1e-9), `got ${v}`);

  check("null when dive_start_s missing", metricValue({ finish_s: 19.1 }, "elapsed_s") === null);
  check("null when finish_s missing", metricValue({ dive_start_s: 4.0 }, "elapsed_s") === null);
  check(
    "null when finish <= dive",
    metricValue({ dive_start_s: 19.1, finish_s: 19.1 }, "elapsed_s") === null &&
      metricValue({ dive_start_s: 19.1, finish_s: 4.0 }, "elapsed_s") === null
  );
  check(
    "null when a boundary is non-finite",
    metricValue({ dive_start_s: 4.0, finish_s: NaN }, "elapsed_s") === null &&
      metricValue({ dive_start_s: null, finish_s: 19.1 }, "elapsed_s") === null
  );

  // Source-text lock: a future edit cannot quietly reintroduce the stored field.
  const src = fs.readFileSync(LIB, "utf8");
  check("leaderboard.js never mentions the stored lap-time field", !src.includes("lap_time_s"));
  check("and never reimplements it as t[-1]", !src.includes("t[-1]"));
  check("and imports neither supabase nor react", !/supabase|react/i.test(src));
}

// ─── 2. AC-2: the eligibility guard ────────────────────────────────────────────────────────────
console.log("\n2. AC-2  15 m eligibility guard");
{
  check("MIN_DIST_M is exported and equals 15", MIN_DIST_M === 15, `got ${MIN_DIST_M}`);
  const cases = [
    [0, false],
    [14.31, false],
    [15.0, true],
    [21.5, true],
  ];
  for (const [d, want] of cases) {
    check(`total_dist_m ${d} -> ${want}`, isEligible({ total_dist_m: d }) === want);
  }
  check("null total_dist_m is ineligible", isEligible({ total_dist_m: null }) === false);
  check("undefined total_dist_m is ineligible", isEligible({ total_dist_m: undefined }) === false);
  check("missing total_dist_m is ineligible", isEligible({}) === false);
  check("a null row is ineligible", isEligible(null) === false);
  check("a string total_dist_m is ineligible", isEligible({ total_dist_m: "20" }) === false);
}

// ─── 3. AC-3: last-N mean, nulls dropped before the window ─────────────────────────────────────
console.log("\n3. AC-3  last-N mean");
{
  check("DEFAULT_N is 5", DEFAULT_N === 5, `got ${DEFAULT_N}`);
  const six = [2, 4, 6, 8, 10, 12];
  check("mean of the first 5 of 6 is 6, not 7", near(lastNMean(six, 5), 6), `got ${lastNMean(six, 5)}`);

  // Nulls dropped BEFORE the slice: n counts values, not rows. Windowing first would take
  // [2, null, 4, null, 6] and average 3 values; dropping first takes [2,4,6,8,10] -> 6.
  const interleaved = [2, null, 4, null, 6, 8, 10, 12];
  check(
    "nulls are dropped before the window is taken",
    near(lastNMean(interleaved, 5), 6),
    `got ${lastNMean(interleaved, 5)}`
  );
  check("fewer than n values averages what exists", near(lastNMean([3, 5], 5), 4));
  check("an empty list is null, not 0 or NaN", lastNMean([], 5) === null);
  check("an all-null list is null", lastNMean([null, null], 5) === null);
  check("undefined input is null", lastNMean(undefined, 5) === null);
  check("NaN is treated as missing", near(lastNMean([NaN, 4, 6], 5), 5));
}

// ─── 4. AC-4: ranking is direction-aware, stable, and refuses to rank a missing value ──────────
console.log("\n4. AC-4  ranking");
{
  // One eligible swim each, so the value IS the swim's value.
  const row = (athlete, v) => ({
    athlete_id: athlete,
    total_dist_m: 21.5,
    mean_vel_ms: v,
  });
  const names = { a: "Ana", b: "Bo", c: "Cy", d: "Dane" };
  const nameFor = (id) => names[id];
  const rows = [row("a", 1.9), row("b", 1.4), row("c", 1.4), row("d", null)];

  const board = rankBoard(rows, "mean_vel_ms", { nameFor });
  check("every athlete appears, including the one with no value", board.length === 4);
  check(
    "higher-is-better order: 1.9, then the two 1.4s by name, then the null",
    board.map((e) => e.name).join(",") === "Ana,Bo,Cy,Dane",
    board.map((e) => `${e.name}:${e.value}`).join(" ")
  );
  check(
    "ties share a rank (1, 2, 2) and the null entry is unranked",
    JSON.stringify(board.map((e) => e.rank)) === "[1,2,2,null]",
    JSON.stringify(board.map((e) => e.rank))
  );
  check("the null entry carries value null, not 0", board[3].value === null && board[3].n === 0);

  // Shared ranks skip: 1, 2, 2, 4.
  const four = [row("a", 1.9), row("b", 1.4), row("c", 1.4), row("d", 1.1)];
  const skipped = rankBoard(four, "mean_vel_ms", { nameFor });
  check(
    "a tie consumes the next rank: 1, 2, 2, 4",
    JSON.stringify(skipped.map((e) => e.rank)) === "[1,2,2,4]",
    JSON.stringify(skipped.map((e) => e.rank))
  );

  // Order invariance: reverse the input, assert the output is byte-identical.
  const reversed = rankBoard([...rows].reverse(), "mean_vel_ms", { nameFor });
  check(
    "reversing the input does not change the board",
    JSON.stringify(reversed) === JSON.stringify(board)
  );

  // Lower-is-better inverts the order and nothing else.
  const lapRow = (athlete, dive, finish) => ({
    athlete_id: athlete,
    total_dist_m: 21.5,
    dive_start_s: dive,
    finish_s: finish,
  });
  const lap = rankBoard(
    [lapRow("a", 4, 20), lapRow("b", 4, 18), lapRow("c", 4, 19)],
    "elapsed_s",
    { nameFor }
  );
  check(
    "lower-is-better puts the smallest first",
    lap.map((e) => e.name).join(",") === "Bo,Cy,Ana",
    lap.map((e) => `${e.name}:${e.value}`).join(" ")
  );
  check("and still ranks 1, 2, 3", JSON.stringify(lap.map((e) => e.rank)) === "[1,2,3]");

  // Ineligible swims never reach the board.
  const mixed = [row("a", 1.9), { ...row("b", 9.9), total_dist_m: 8.0 }];
  const guarded = rankBoard(mixed, "mean_vel_ms", { nameFor });
  check("a sub-15 m swim is excluded entirely", guarded.length === 1 && guarded[0].name === "Ana");

  // Purity.
  const before = JSON.stringify(rows);
  rankBoard(rows, "mean_vel_ms", { nameFor });
  check("rankBoard does not mutate its input rows", JSON.stringify(rows) === before);
  check("an unknown metric returns an empty board", rankBoard(rows, "nope", { nameFor }).length === 0);
}

// ─── 5. AC-5: the catalog, and that it cannot drift from the query ─────────────────────────────
console.log("\n5. AC-5  catalog + SESSION_SELECT");
{
  check("exactly 8 entries", LEADERBOARD_METRICS.length === 8, `got ${LEADERBOARD_METRICS.length}`);
  const want = [
    "mean_vel_ms",
    "max_vel_ms",
    "elapsed_s",
    "uw_avg_speed",
    "splits_5m",
    "splits_10m",
    "splits_15m",
    "splits_20m",
  ];
  check(
    "the exact key set",
    JSON.stringify(LEADERBOARD_METRICS.map((m) => m.key)) === JSON.stringify(want),
    LEADERBOARD_METRICS.map((m) => m.key).join(",")
  );
  check(
    "every entry carries { key, label, unit, direction }",
    LEADERBOARD_METRICS.every(
      (m) => m.key && m.label && typeof m.unit === "string" && m.direction
    )
  );
  check(
    "every direction is higher or lower — never neutral",
    LEADERBOARD_METRICS.every((m) => m.direction === "higher" || m.direction === "lower")
  );
  const lower = LEADERBOARD_METRICS.filter((m) => m.direction === "lower").map((m) => m.key);
  check("elapsed_s is the only lower-is-better metric", JSON.stringify(lower) === '["elapsed_s"]');

  // Drift lock: the query must name every field the catalog and the guard read.
  for (const m of LEADERBOARD_METRICS) {
    if (m.key === "elapsed_s") continue; // derived — its two inputs are checked below
    check(`SESSION_SELECT names ${m.key}`, SESSION_SELECT.includes(m.key));
  }
  check(
    "SESSION_SELECT names elapsed_s's two inputs instead",
    SESSION_SELECT.includes("dive_start_s") && SESSION_SELECT.includes("finish_s")
  );
  check("SESSION_SELECT names the guard's total_dist_m", SESSION_SELECT.includes("total_dist_m"));
  check(
    "SESSION_SELECT names the grouping and ordering fields",
    ["id", "athlete_id", "stroke_type", "recorded_at"].every((f) => SESSION_SELECT.includes(f))
  );
  check(
    "SESSION_SELECT does NOT pull the stored lap-time scalar",
    !SESSION_SELECT.includes("lap_time_s")
  );
  check(
    "SESSION_SELECT selects deep scalars, not whole phase objects",
    !/metrics_json\s*,/.test(SESSION_SELECT) && SESSION_SELECT.includes("->value")
  );
}

// ─── 6. A realistic end-to-end board ───────────────────────────────────────────────────────────
console.log("\n6. end-to-end board");
{
  // 8 rows, 3 athletes, newest-first per athlete. Cy has no splits_20m on either swim — the live
  // shape of the real data (one athlete has no splits_20m on either eligible breaststroke swim).
  const s = (athlete, dist, splits20) => ({
    athlete_id: athlete,
    stroke_type: "freestyle",
    total_dist_m: dist,
    splits_20m: splits20,
  });
  const rows = [
    s("a", 21.5, 1.8),
    s("a", 21.5, 1.6),
    s("a", 21.5, 1.4),
    s("a", 21.5, 9.9), // 4th — inside the window of 5
    s("a", 9.0, 9.9), // ineligible, must not count as a swim either
    s("b", 21.5, 1.5),
    s("b", 21.5, 1.5),
    s("c", 21.5, null),
    s("c", 21.5, null),
  ];
  const names = { a: "Ana", b: "Bo", c: "Cy" };
  const board = rankBoard(rows, "splits_20m", { nameFor: (id) => names[id] });

  check("three athletes on the board", board.length === 3);
  check(
    "Ana leads on the mean of her 4 eligible swims",
    board[0].name === "Ana" && near(board[0].value, (1.8 + 1.6 + 1.4 + 9.9) / 4),
    `value ${board[0].value}`
  );
  check("her n is 4 values", board[0].n === 4);
  check("her swims count excludes the sub-15 m row", board[0].swims === 4, `got ${board[0].swims}`);
  check("Bo is second at 1.5", board[1].name === "Bo" && near(board[1].value, 1.5));
  check(
    "Cy appears last, unranked, with 2 swims and 0 values",
    board[2].name === "Cy" &&
      board[2].value === null &&
      board[2].rank === null &&
      board[2].n === 0 &&
      board[2].swims === 2
  );
  check(
    "every entry carries the full shape",
    board.every(
      (e) =>
        "athleteId" in e && "name" in e && "value" in e && "n" in e && "swims" in e && "rank" in e
    )
  );

  // The window really is last-N: with n=2 Ana's value is the mean of her two newest only.
  const n2 = rankBoard(rows, "splits_20m", { nameFor: (id) => names[id], n: 2 });
  check("n=2 uses only the two newest swims", near(n2[0].value, 1.7), `got ${n2[0].value}`);

  // Interleaving the athletes (round-robin instead of blocks) preserves each athlete's newest-first
  // order but changes the input order completely — the board must be identical.
  const interleaved = [];
  for (let i = 0; i < 5; i++) {
    for (const id of ["c", "b", "a"]) {
      const forId = rows.filter((r) => r.athlete_id === id);
      if (forId[i]) interleaved.push(forId[i]);
    }
  }
  check(
    "interleaving the athletes does not change the board",
    JSON.stringify(rankBoard(interleaved, "splits_20m", { nameFor: (id) => names[id] })) ===
      JSON.stringify(board)
  );
}

// ─── 7. Phase 90-03: the board render ──────────────────────────────────────────────────────────
console.log("\n7. 90-03  board render");
{
  const web = path.resolve(here, "..", "web");
  const require = createRequire(path.join(web, "package.json"));
  const ts = require("typescript");
  const React = require("react");
  const { renderToStaticMarkup } = require("react-dom/server");

  const out = path.join(web, "node_modules", ".leaderboard-check");
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });

  // The 87-02 trick: rewrite the ONE state initializer in the harness's private copy so the
  // expanded branch is reachable without an effect or a click. Asserted first, so a moved line
  // fails here instead of silently leaving the branch uncovered.
  const SRC = path.join(web, "components", "portal", "LeaderboardBoard.js");
  const EXPANDED_INIT = "const [expanded, setExpanded] = useState(false);";
  let code = fs.readFileSync(SRC, "utf8");
  check("harness: expanded initializer found for rewrite", code.includes(EXPANDED_INIT));
  code = code.replace(
    EXPANDED_INIT,
    "const [expanded, setExpanded] = useState(globalThis.__TEST_EXPANDED__ || false);"
  );
  fs.writeFileSync(
    path.join(out, "LeaderboardBoard.cjs"),
    ts.transpileModule(code, {
      compilerOptions: {
        jsx: ts.JsxEmit.ReactJSX,
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
      fileName: "LeaderboardBoard.js",
    }).outputText
  );
  const LeaderboardBoard = require(path.join(out, "LeaderboardBoard.cjs")).default;

  const render = (props, expandedState = false) => {
    globalThis.__TEST_EXPANDED__ = expandedState;
    return renderToStaticMarkup(React.createElement(LeaderboardBoard, props));
  };

  // Markup readers. Each keys off a class fragment unique to its cell, so a row is parsed by role
  // rather than by position — the nested unit <span> makes a positional parse wrong.
  const liRows = (html) =>
    [...html.matchAll(/<li class="flex items-baseline[\s\S]*?<\/li>/g)].map((m) => m[0]);
  const cell = (row, re) => {
    const m = row.match(re);
    return m ? m[1].trim() : "";
  };
  const rankIn = (row) => cell(row, /font-mono text-xs text-muted">([^<]*)</);
  const nameIn = (row) => cell(row, /flex-1 truncate [^"]*">([^<]*)</);
  const valueIn = (row) => cell(row, /shrink-0 font-mono text-(?:ink|muted)">([^<]*)</);
  const unitIn = (row) => cell(row, /font-sans text-muted">([^<]*)</);
  const namesOf = (html) => liRows(html).map(nameIn);
  const ranksOf = (html) => liRows(html).map(rankIn);

  // ── fixtures ────────────────────────────────────────────────────────────────
  const NAMES = { a: "Ana", b: "Bo", c: "Cy", d: "Dee", e: "Eli", f: "Fay", g: "Gus" };
  const VALUES = { a: 1.88, b: 1.8, c: 1.72, d: 1.64, e: 1.56, f: 1.48, g: 1.4 };
  const nameFor = (id) => NAMES[id];
  const swims = (athlete, key, value, count = 5) =>
    Array.from({ length: count }, () => ({
      athlete_id: athlete,
      total_dist_m: 21.5,
      [key]: value,
    }));

  const speed = metricByKey("mean_vel_ms");
  const ids7 = ["a", "b", "c", "d", "e", "f", "g"];
  const entries7 = rankBoard(
    ids7.flatMap((id) => swims(id, "mean_vel_ms", VALUES[id])),
    speed,
    { nameFor }
  );
  const si = displayUnit(speed.unit, false);
  const board7 = render({ metric: speed, entries: entries7, ...si });

  // ── AC-1: a board reads as an ordering ──────────────────────────────────────
  check(
    "AC-1  the title is the catalog label",
    board7.includes(`>${speed.label}</h2>`),
    speed.label
  );
  check("AC-1  a higher-is-better board says so", board7.includes("higher is better"));
  check(
    "AC-1  a lower-is-better board says so instead",
    (() => {
      const lap = metricByKey("elapsed_s");
      const html = render({
        metric: lap,
        entries: rankBoard(
          [{ athlete_id: "a", total_dist_m: 21.5, dive_start_s: 4.0, finish_s: 19.1 }],
          lap,
          { nameFor }
        ),
        ...displayUnit(lap.unit, false),
      });
      return html.includes("lower is better") && !html.includes("higher is better");
    })()
  );
  {
    const first = liRows(board7)[0];
    check(
      'AC-1  row one is "1  Ana  1.88 m/s  n=5"',
      rankIn(first) === "1" &&
        nameIn(first) === "Ana" &&
        valueIn(first) === "1.88" &&
        unitIn(first) === "m/s" &&
        first.includes("n=5"),
      `${rankIn(first)} | ${nameIn(first)} | ${valueIn(first)} ${unitIn(first)}`
    );
    check(
      "AC-1  ranked best-first",
      namesOf(board7).join(",") === "Ana,Bo,Cy,Dee,Eli",
      namesOf(board7).join(",")
    );
  }

  // ── AC-2: top five, with the full order one click away ──────────────────────
  check("AC-2  a 7-athlete board renders 5 rows collapsed", liRows(board7).length === 5);
  check(
    "AC-2  the ranks shown are 1..5",
    ranksOf(board7).join(",") === "1,2,3,4,5",
    ranksOf(board7).join(",")
  );
  check('AC-2  the control reads "Show all 7"', board7.includes("Show all 7"));
  check("AC-2  and not the collapse label", !board7.includes("Show top 5"));
  {
    const expanded = render({ metric: speed, entries: entries7, ...si }, true);
    check("AC-2  expanded renders all 7 rows", liRows(expanded).length === 7);
    check('AC-2  and the control flips to "Show top 5"', expanded.includes("Show top 5"));
    check("AC-2  with no stale show-all label", !expanded.includes("Show all 7"));
    check(
      "AC-2  expanding adds rows and reorders nothing",
      namesOf(expanded).slice(0, 5).join(",") === namesOf(board7).join(","),
      namesOf(expanded).join(",")
    );
  }
  {
    const four = rankBoard(
      ["a", "b", "c", "d"].flatMap((id) => swims(id, "mean_vel_ms", VALUES[id])),
      speed,
      { nameFor }
    );
    const html = render({ metric: speed, entries: four, ...si });
    check("AC-2  a 4-athlete board renders all 4 rows", liRows(html).length === 4);
    check(
      "AC-2  and renders NO show-all control at all",
      !html.includes("Show all") && !html.includes("Show top") && !html.includes("<button"),
      "butterfly 4 / backstroke 2 is the live case"
    );
  }

  // ── AC-3: a missing value is shown, not hidden, and not ranked ──────────────
  {
    const split = metricByKey("splits_20m");
    const rows = [
      ...["a", "b", "c", "d", "e", "f"].flatMap((id) => swims(id, "splits_20m", VALUES[id])),
      ...swims("g", "splits_20m", null, 2), // Dane's live shape: eligible swims, no value
    ];
    const entries = rankBoard(rows, split, { nameFor });
    const html = render({ metric: split, entries, ...displayUnit(split.unit, false) });
    const rowsOut = liRows(html);

    check("AC-3  6 ranked + 1 unranked = 5 shown + the unranked row", rowsOut.length === 6);
    const last = rowsOut[rowsOut.length - 1];
    check("AC-3  the unranked athlete is at the bottom", nameIn(last) === "Gus", nameIn(last));
    check("AC-3  with an em dash where the value goes", valueIn(last) === "—", valueIn(last));
    check("AC-3  and no rank number", rankIn(last) === "", `got "${rankIn(last)}"`);
    check(
      'AC-3  "Show all N" counts RANKED athletes only',
      html.includes("Show all 6") && !html.includes("Show all 7")
    );
    check(
      "AC-3  the no-rank note distinguishes it from last place",
      html.includes("not last place")
    );
    check(
      "AC-3  and that note is absent when every athlete is ranked",
      !board7.includes("not last place")
    );
  }

  // ── AC-4: THE LOAD-BEARING CHECK — imperial converts every value, reorders nothing ──
  {
    const imp = displayUnit(speed.unit, true);
    const metricHtml = render({ metric: speed, entries: entries7, ...si });
    const imperialHtml = render({ metric: speed, entries: entries7, ...imp });

    check(
      "AC-4  the athlete sequence is identical between the two renders",
      namesOf(imperialHtml).join(",") === namesOf(metricHtml).join(","),
      namesOf(imperialHtml).join(",")
    );
    check(
      "AC-4  the rank sequence is identical between the two renders",
      ranksOf(imperialHtml).join(",") === ranksOf(metricHtml).join(","),
      ranksOf(imperialHtml).join(",")
    );
    const mv = liRows(metricHtml).map(valueIn);
    const iv = liRows(imperialHtml).map(valueIn);
    check(
      "AC-4  every value string changed",
      mv.length === 5 && iv.length === 5 && mv.every((v, i) => v !== iv[i]),
      `${mv.join(",")} -> ${iv.join(",")}`
    );
    check(
      "AC-4  the unit string changed m/s -> yd/s",
      liRows(metricHtml).every((r) => unitIn(r) === "m/s") &&
        liRows(imperialHtml).every((r) => unitIn(r) === "yd/s")
    );
    check(
      "AC-4  the conversion is exactly M_TO_YD applied at format time",
      iv[0] === (entries7[0].value * M_TO_YD).toFixed(2),
      `${iv[0]} vs ${(entries7[0].value * M_TO_YD).toFixed(2)}`
    );
  }

  // ── AC-6: lap time is visibly the derived one, and seconds never convert ────
  {
    const lap = metricByKey("elapsed_s");
    // The stored scalar rides along on the row at the firmware's fixed 39.0 s record length. If it
    // is ever read, this board prints 39.0.
    const rows = [
      { athlete_id: "a", total_dist_m: 21.5, dive_start_s: 4.0, finish_s: 19.1, lap_time_s: 39.0 },
      { athlete_id: "b", total_dist_m: 21.5, dive_start_s: 4.0, finish_s: 20.4, lap_time_s: 39.0 },
    ];
    const entries = rankBoard(rows, lap, { nameFor });
    const html = render({ metric: lap, entries, ...displayUnit(lap.unit, false) });
    check("AC-6  the derived 15.1 s renders", valueIn(liRows(html)[0]) === "15.1", valueIn(liRows(html)[0]));
    check("AC-6  the stored 39.0 s appears nowhere on the board", !html.includes("39.0"));
    check("AC-6  seconds print to 1 decimal", liRows(html).map(valueIn).join(",") === "15.1,16.4");
    check(
      "AC-6  lower-is-better puts the faster swim first",
      namesOf(html).join(",") === "Ana,Bo",
      namesOf(html).join(",")
    );
    check(
      "AC-6  the seconds board is byte-identical under imperial",
      render({ metric: lap, entries, ...displayUnit(lap.unit, true) }) === html
    );
  }

  fs.rmSync(out, { recursive: true, force: true });
  check("harness: staging directory removed", !fs.existsSync(out));
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
