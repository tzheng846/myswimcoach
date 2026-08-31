// cycleTraces — the pure trace model behind the per-cycle OVERLAY panel (Phase 83-05).
//
// Where `cycleBands` lays cycles out along the real timeline (each in its own place, clamped to the
// inset's window), this lays them ON TOP OF EACH OTHER: every cycle starts at x = 0 so the coach can
// see the pack and spot the stroke that leaves it. Data in, data out — no React, no SVG geometry.
//
// Why a pack instead of a flag: 83-03 measured that no MAD threshold separates a clean swim from a
// ragged one at a median of 7 cycles a lap (it fired on 75% of sessions at k=3.0 and still 39% at
// k=8.0). The honest replacement for a classifier that cannot work at this sample size is to draw
// the strokes and let the coach's eye do it.
//
// Deliberately shape-agnostic, like `cycleBands`: it reads only `start_idx` / `end_idx` / a duration
// key, so `phases.kick_bands` passes through unmodified for the Underwater panel.
//
// Indices are SAMPLE indices at the session's own `sample_rate_hz` — never assume 100 Hz.

import { resample, median, POINTS, MIN_ITEMS } from "./cycleShape";

const fin = (v) => typeof v === "number" && Number.isFinite(v);

// items (metrics_json.cycles or phases.kick_bands) + the session's velocity array
//   → { rows, traces, median, maxDuration }
//
// `rows` is the GUTTER MODEL. Its `n` sequence, order and length come ONLY from the stored array, so
// they are identical in both modes — that is the promise that switching to % of cycle never
// renumbers anything. `available` / `reason` legitimately DO vary by mode: a dropout is drawable in
// seconds (pen up, pen down) and not drawable normalized (a resample cannot span a hole).
//
// `n` uses the SAME rule as `cycleBands.buildBands` (`cycle_num + 1` when stored, else array
// position + 1) because it is the cross-highlight key shared with CycleCharts. There is exactly one
// numbering in this codebase; do not invent a second.
//
// `excludeBreakout` prepends the synthetic `n: 0` row that accounts for the inset's gold band. The
// breakout is never IN `items` — it is synthesised by `buildBands` from the gap between
// `stroke_start_s` and the coach's first stroke mark — so the row exists here only to explain why
// the pack has one fewer trace than the inset has bands. It is never drawn and never interactive.
//
// `numberKey` / `parity` (87-02). `numberKey` mirrors `buildBands`' seam so a strokes array numbers
// itself by `stroke_num`; the default keeps cycles and kick bands exactly as they are. `parity` tags
// every row and trace with the ALTERNATING-ARM side — `side: n % 2 ? "A" : "B"`, stated once here —
// and adds two pointwise per-side medians in normalized mode, each gated independently at
// MIN_ITEMS. ⚠ A and B are never left and right: a 1-D axial encoder cannot observe which arm is
// which (87-01 D3). The rule matches PhaseVelocity's band colouring (`s.n % 2 ? cycle-a : cycle-b`)
// so side A is blue in the inset, in the pack and in the Arm balance chips — one alignment, not
// three. The combined `median` key is computed exactly as before either way, so the cycle path is
// untouched.
export function buildTraces(
  items,
  velocity,
  {
    fsHz,
    mode = "seconds",
    durationKey = "duration_s",
    numberKey = "cycle_num",
    excludeBreakout = false,
    parity = false,
  } = {}
) {
  const empty = { rows: [], traces: [], median: null, medianA: null, medianB: null, maxDuration: 0 };
  if (!Array.isArray(items) || !items.length) return empty;
  if (!Array.isArray(velocity) || velocity.length < 2) return empty;
  if (!fin(fsHz) || fsHz <= 0) return empty;

  const normalized = mode === "normalized";
  const rows = [];
  const traces = [];
  let maxDuration = 0;

  if (excludeBreakout) rows.push({ n: 0, available: false, reason: "breakout", duration: null });

  items.forEach((c, i) => {
    if (!c) return; // same skip as buildBands — a null item is not a row
    const n = fin(c[numberKey]) ? c[numberKey] + 1 : i + 1;
    const side = parity ? (n % 2 ? "A" : "B") : null;
    const a = fin(c.start_idx) ? Math.max(0, Math.trunc(c.start_idx)) : null;
    const b = fin(c.end_idx) ? Math.min(velocity.length, Math.trunc(c.end_idx)) : null;
    const span = a != null && b != null ? b - a : 0;

    // Prefer the stored duration; fall back to the span so a gutter row can still name itself.
    const duration = fin(c[durationKey]) ? c[durationKey] : span >= 2 ? span / fsHz : null;

    const row = { n, side, available: false, reason: "too-short", duration };
    rows.push(row);
    if (span < 2) return;

    if (normalized) {
      // `resample` returns null on ANY non-finite sample: a dropout must exclude the trace, never
      // be filled. A filled hole would be scored as if it were signal.
      const prof = resample(velocity, a, b, POINTS);
      if (!prof) {
        row.reason = "dropout";
        return;
      }
      traces.push({ n, side, points: prof.map((v, j) => [j / (POINTS - 1), v]) });
    } else {
      // Seconds mode keeps the dropout: `null` is a pen-up marker, so the component draws a gap
      // rather than a straight line across missing signal.
      const points = [];
      let finiteCount = 0;
      for (let k = a; k < b; k++) {
        const v = velocity[k];
        if (!fin(v)) {
          if (points.length && points[points.length - 1] !== null) points.push(null);
          continue;
        }
        points.push([(k - a) / fsHz, v]);
        finiteCount++;
      }
      while (points.length && points[points.length - 1] === null) points.pop();
      if (finiteCount < 2) {
        row.reason = "dropout";
        return;
      }
      traces.push({ n, side, points });
    }

    row.available = true;
    row.reason = null;
    maxDuration = Math.max(maxDuration, span / fsHz);
  });

  // Pointwise median — NORMALIZED ONLY. A pointwise median needs a common x-grid and seconds mode
  // has none. Gated at MIN_ITEMS for the same reason 83-03 gated its reference profile: below five
  // usable traces a within-session median is not a reference, it is noise.
  let pointwise = null;
  if (normalized && traces.length >= MIN_ITEMS) {
    pointwise = [];
    for (let j = 0; j < POINTS; j++) {
      pointwise.push([j / (POINTS - 1), median(traces.map((t) => t.points[j][1]))]);
    }
  }

  // Per-side medians (87-02), normalized only and gated PER SIDE at the same MIN_ITEMS — so ten
  // strokes are needed for two lines, roughly the five cycles the combined median already asks for.
  // Either side short of it draws NEITHER: a median of one arm is not the picture, and silently
  // falling back to the combined median would hide the very split this mode exists to show.
  let medianA = null;
  let medianB = null;
  if (normalized && parity) {
    const bySide = (want) => {
      const ts = traces.filter((t) => t.side === want);
      if (ts.length < MIN_ITEMS) return null;
      const out = [];
      for (let j = 0; j < POINTS; j++) out.push([j / (POINTS - 1), median(ts.map((t) => t.points[j][1]))]);
      return out;
    };
    medianA = bySide("A");
    medianB = bySide("B");
    if (!medianA || !medianB) {
      medianA = null;
      medianB = null;
    }
  }

  return { rows, traces, median: pointwise, medianA, medianB, maxDuration };
}

export default buildTraces;
