// leaderboard.js — the pure ranking core for team leaderboards (Phase 90-01). No JSX, no database
// client, no "@/" aliases: this module runs under bare node so scratch/leaderboard_check.mjs can
// import it directly. (The harness asserts on this file's SOURCE TEXT, so the names of the things
// deliberately not used here are spelled around rather than quoted.)
//
// Three things here are easy to get wrong, so they are decisions, not accidents:
//
// 1. LAP TIME IS DERIVED, NEVER READ. The scalar the pipeline stores under metrics_json.session
//    for lap time is the LAST TIMESTAMP of the trace — the duration of the RECORDING, not of the
//    swim (metrics.py:1870). Measured over
//    the 84 eligible sessions it disagrees with `finish_s − dive_start_s` on 84 of 84 (median
//    5.75 s, max 28.29 s) and 19 of 84 read exactly 39.0 s, the firmware's fixed record length.
//    Ranking on it would rank who stopped recording soonest. `elapsed_s` below is computed from
//    the two boundaries, and the stored scalar is not in SESSION_SELECT at all.
//
// 2. ALL EIGHT METRICS ARE BOUNDARY-DEPENDENT. mean_vel_ms and max_vel_ms are computed over
//    vel[b_end:swim_end], and the derived lap time needs two boundaries. What the eight actually
//    share is CYCLE-independence — none reads ctx.cycles — which is the point, because the
//    segmenter undercounts strokes by ~2–3× and a leaderboard would publish that failure by name.
//
// 3. `recorded_at` IS UPLOAD TIME, NOT SWIM TIME. api.py never sets it, so it takes the schema
//    default NOW(). "Last 5 swims" is therefore "last 5 uploads" — the same thing when upload
//    follows the swim by minutes, wrong for a late queued upload. `session_start_utc_ms` (86-01)
//    is the correct field but exists only for sessions recorded after Phase 86 ships, so it cannot
//    order the library today. There is deliberately no fallback chain: callers pass rows ordered
//    newest-first by `recorded_at`, and the caveat is surfaced in the UI rather than hidden here.
//
// Ranking runs on SI only. unitConvert.js is display-only (88-03 D2) and is NOT imported here, so
// toggling units structurally cannot reorder a board.

export const MIN_DIST_M = 15; // swims shorter than this are not comparable — see isEligible
export const DEFAULT_N = 5; // a row value is the mean of the athlete's last N swims

// `direction` uses reportMetrics.js's vocabulary exactly. There is no "neutral" entry by
// construction: a metric with no sort order cannot be ranked, so it was excluded from the catalog
// rather than carried with a meaningless direction. Labels are copied from PhaseReportCard.js's
// DISPLAY table so one metric is not named two things across two portal pages.
export const LEADERBOARD_METRICS = [
  { key: "mean_vel_ms", label: "Average speed", unit: "m/s", direction: "higher" },
  { key: "max_vel_ms", label: "Top speed", unit: "m/s", direction: "higher" },
  { key: "elapsed_s", label: "Lap time", unit: "s", direction: "lower" },
  { key: "uw_avg_speed", label: "Underwater speed", unit: "m/s", direction: "higher" },
  { key: "splits_5m", label: "Split 0–5 m", unit: "m/s", direction: "higher" },
  { key: "splits_10m", label: "Split 5–10 m", unit: "m/s", direction: "higher" },
  { key: "splits_15m", label: "Split 10–15 m", unit: "m/s", direction: "higher" },
  { key: "splits_20m", label: "Split 15–20 m", unit: "m/s", direction: "higher" },
];

export function metricByKey(key) {
  return LEADERBOARD_METRICS.find((m) => m.key === key);
}

// The PostgREST select string, kept beside the catalog so the query cannot drift from it.
// Deep scalar selection is what keeps this cheap: measured against the live DB, 99 rows cost 47 KB
// this way, 503 KB pulling the phase objects whole and 1.5 MB for the full metrics_json.
export const SESSION_SELECT = [
  "id",
  "athlete_id",
  "stroke_type",
  "recorded_at",
  "mean_vel_ms:metrics_json->session->mean_vel_ms",
  "max_vel_ms:metrics_json->session->max_vel_ms",
  "total_dist_m:metrics_json->session->total_dist_m",
  "dive_start_s:metrics_json->phases->boundaries->dive_start_s",
  "finish_s:metrics_json->phases->boundaries->finish_s",
  "uw_avg_speed:metrics_json->phases->underwater->uw_avg_speed->value",
  "splits_5m:metrics_json->phases->swim->splits_5m->value",
  "splits_10m:metrics_json->phases->swim->splits_10m->value",
  "splits_15m:metrics_json->phases->swim->splits_15m->value",
  "splits_20m:metrics_json->phases->swim->splits_20m->value",
].join(",");

// A missing or non-numeric total_dist_m is INELIGIBLE, never coerced to 0-and-compared: unknown
// distance is not the same claim as "we measured zero".
export function isEligible(row) {
  return Number.isFinite(row?.total_dist_m) && row.total_dist_m >= MIN_DIST_M;
}

// One row's value for one metric: a finite number, or null. Never NaN, never 0 as a stand-in for
// missing — lastNMean and rankBoard both key off null.
export function metricValue(row, key) {
  if (key === "elapsed_s") {
    const dive = row?.dive_start_s;
    const finish = row?.finish_s;
    if (!Number.isFinite(dive) || !Number.isFinite(finish)) return null;
    const elapsed = finish - dive;
    return elapsed > 0 ? elapsed : null;
  }
  const v = row?.[key];
  return Number.isFinite(v) ? v : null;
}

// Mean of the first n non-null values, or null when there are none. Nulls are dropped BEFORE the
// window is taken, so n counts VALUES, not rows: a swim missing this one metric does not consume a
// slot in the window.
export function lastNMean(values, n = DEFAULT_N) {
  const xs = (values ?? []).filter((v) => v != null && Number.isFinite(v)).slice(0, n);
  if (xs.length === 0) return null;
  return xs.reduce((s, x) => s + x, 0) / xs.length;
}

// One board for one metric. `rows` are the session rows for a SINGLE stroke, already ordered
// newest-first; `metric` is a catalog entry or its key. Pure — `rows` is never mutated.
//
// Every athlete with at least one eligible swim appears, including one whose swims all lack this
// metric: that entry carries value null and rank null and sorts last. That branch is live on the
// real data on day one — one athlete has no splits_20m on either of his eligible breaststroke
// swims.
//
// Ties share a rank (1, 2, 2, 4) and break by name with a plain `<`, not localeCompare, so the
// ordering is not locale-dependent.
export function rankBoard(rows, metric, { n = DEFAULT_N, nameFor } = {}) {
  const spec = typeof metric === "string" ? metricByKey(metric) : metric;
  if (!spec) return [];

  const byAthlete = new Map();
  for (const row of rows ?? []) {
    if (!isEligible(row)) continue;
    const id = row.athlete_id;
    if (!byAthlete.has(id)) byAthlete.set(id, []);
    byAthlete.get(id).push(row);
  }

  const entries = [];
  for (const [athleteId, swims] of byAthlete) {
    const values = swims.map((r) => metricValue(r, spec.key)).filter((v) => v != null);
    entries.push({
      athleteId,
      name: nameFor ? nameFor(athleteId) : String(athleteId),
      value: lastNMean(values, n),
      n: Math.min(values.length, n),
      swims: swims.length,
    });
  }

  const lowerIsBetter = spec.direction === "lower";
  entries.sort((a, b) => {
    if (a.value == null || b.value == null) {
      if (a.value != null) return -1;
      if (b.value != null) return 1;
    } else if (a.value !== b.value) {
      return lowerIsBetter ? a.value - b.value : b.value - a.value;
    }
    if (a.name === b.name) return 0;
    return a.name < b.name ? -1 : 1;
  });

  let rank = 0;
  let seen = 0;
  let prev = null;
  for (const e of entries) {
    if (e.value == null) {
      e.rank = null;
      continue;
    }
    seen += 1;
    if (prev === null || e.value !== prev) rank = seen;
    e.rank = rank;
    prev = e.value;
  }
  return entries;
}
