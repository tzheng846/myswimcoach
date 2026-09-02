// Phase 90-01 check — the pure leaderboard ranking core.
//
// ⚠ SIMPLER THAN THE RECENT HARNESSES ON PURPOSE. 87-02 / 88-03 / 88-04 / 88-05 all transpile JSX
// and server-render because the thing under test was a component. web/lib/leaderboard.js is plain
// ESM with no JSX and no "@/" alias imports, so this harness imports it directly: no `typescript`,
// no react-dom/server, no node_modules staging, no cleanup. It needs no auth, no network and no
// dev server (AC-6).
//
// Run: node scratch/leaderboard_check.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  DEFAULT_N,
  LEADERBOARD_METRICS,
  MIN_DIST_M,
  SESSION_SELECT,
  isEligible,
  lastNMean,
  metricValue,
  rankBoard,
} from "../web/lib/leaderboard.js";

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

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
