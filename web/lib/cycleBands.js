// cycleBands — the pure band model behind the phase insets' per-cycle coloring (Phase 83-01).
//
// Turns a `metrics_json.cycles` array into a drawable band list: one band per surviving cycle,
// clamped to the inset's window, carrying its ORIGINAL 1-based cycle number. No React, no SVG
// geometry — that lives in PhaseVelocity, so this stays testable as data.
//
// Deliberately shape-agnostic: it reads only `start_idx` / `end_idx` / a duration key, so 83-02
// passes `phases.kick_bands` through it unmodified for the Underwater inset.
//
// Indices are SAMPLE indices at the session's own `sample_rate_hz` — never assume 100 Hz.

const fin = (v) => typeof v === "number" && Number.isFinite(v);

// items → [{ n, startIdx, endIdx, duration, isBreakout }]
//
// `n` is the item's original 1-based position (`{numberKey} + 1` when stored, else array position
// + 1) and NOT a renumbering of the survivors: it is the cross-highlight key shared with
// CycleCharts' `n: i + 1`, so dropping a band must not shift the ones after it.
//
// `breakoutFirst` (83-03) inserts a SYNTHETIC band, `n: 0`, spanning `i0` → the lowest-n cycle's
// start. That span is exactly the breakout pull: `i0` is `stroke_start_s`, the coach's
// streamline-break mark, and their first stroke mark lands where a hand RETURNS overhead, so the
// pull between them belongs to no cycle. Measured across the library it is a real 1.04 s median gap
// on all 43 annotated sessions, never negative.
//
// It is its own band rather than an extension of cycle 1, because it is ONE stroke and cycle 1 is
// another — merging them gilds two strokes and misstates what a breakout is. `n: 0` cannot collide
// with the cross-highlight keys (CycleCharts numbers from 1), so hovering the breakout correctly
// highlights nothing in the per-cycle charts: there is no row there for it.
//
// It defaults false and is NEVER inferred from the data. Two reasons: an underwater kick has no
// breakout, and on AUTO-segmented sessions "cycle 1" is not the breakout at all — 28 of 47 start
// BEFORE `stroke_start_s` (worst −12.9 s). Only a caller that knows the cycles are coach-marked may
// pass true.
// `numberKey` (87-02) names the field the item numbers itself by. Default `cycle_num` keeps cycles
// and kick bands numbering exactly as they always have (kick bands carry `kick_num` and are
// deliberately numbered by array position — this must NOT start reading it). Strokes pass
// `numberKey: "stroke_num"`: numerically identical to the array-position fallback while that field
// is dense and 0-based, but it makes the numbering read from the field the backend owns, which is
// what the A/B colour alignment in PhaseVelocity's `s.n % 2` rests on.
export function buildBands(
  items,
  { fsHz, i0, i1, durationKey = "duration_s", numberKey = "cycle_num", breakoutFirst = false } = {}
) {
  if (!Array.isArray(items) || !items.length) return [];
  if (!fin(i0) || !fin(i1) || i1 <= i0) return [];

  const bands = [];
  items.forEach((c, i) => {
    if (!c) return;
    const a = c.start_idx;
    const b = c.end_idx;
    if (!fin(a) || !fin(b) || b <= a) return;
    const startIdx = Math.max(i0, Math.min(i1, a));
    const endIdx = Math.max(i0, Math.min(i1, b));
    if (endIdx <= startIdx) return; // fell entirely outside the window
    bands.push({
      n: fin(c[numberKey]) ? c[numberKey] + 1 : i + 1,
      startIdx,
      endIdx,
      duration: fin(c[durationKey]) ? c[durationKey] : null,
      isBreakout: false,
    });
  });

  // Anchor on the surviving band with the LOWEST n, not array position 0 — a dropped first cycle
  // must not let cycle 2 define where the breakout ends. No survivor, and no gap to fill, means no
  // breakout band at all: an empty gap is an honest "the marks start at the breakout".
  if (breakoutFirst && bands.length) {
    let first = bands[0];
    for (const b of bands) if (b.n < first.n) first = b;
    if (first.startIdx > i0) {
      bands.unshift({
        n: 0,
        startIdx: i0,
        endIdx: first.startIdx,
        duration: fin(fsHz) && fsHz > 0 ? (first.startIdx - i0) / fsHz : null,
        isBreakout: true,
      });
    }
  }

  return bands;
}

export default buildBands;
