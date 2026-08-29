// phaseValence.js — direction-of-good valence + deterministic flagging (Phase 75-05).
//
// Pure module (repo convention: pure core, I/O at the edge — metrics.py / ratings.py).
// DIRECTION_OF_GOOD is the ONE place the report card asserts good/bad. It is
// direction-of-CHANGE coloring keyed to a metric's established direction of good — NOT an
// absolute/normative threshold. Doctrine's "no national/age thresholds" still holds: a flag
// only ever means "outside HIS own usual range", and the color only says whether moving that
// way is generally good for THIS metric. It is a deliberate, user-approved (2026-08-25)
// evolution of the old no-valence display rule. Kept as plain data so a coach can correct one
// line; a key absent from the map is treated as "neutral" (flagged if it moved, never judged).

// Keyed by phase_metrics REGISTRY key. Flat (keys are unique across phases) for O(1) lookup;
// the plan groups them by phase for readability only.
export const DIRECTION_OF_GOOD = {
  // Start (dive | push-off)
  peak_vel: "up",
  time_to_peak_vel: "down",
  max_accel: "up",
  dive_duration: "neutral",
  glide_duration: "neutral",
  glide_distance: "neutral",
  glide_avg_speed: "up",
  glide_decel: "down",
  break_into_kick_vel: "neutral",
  reaction_time: "down",
  // Underwater (dolphin kicks | breaststroke pulldown)
  uw_duration: "neutral",
  uw_distance: "neutral",
  uw_avg_speed: "up",
  uw_surface_ratio: "up",
  kick_count: "neutral",
  dist_per_kick: "up",
  kick_tempo: "neutral",
  kick_consistency: "down",
  uw_ivv: "down",
  per_kick_decay: "up",
  first_kick_impulse: "up",
  pulldown_peak_vel: "up",
  pulldown_duration: "neutral",
  // Swim (Phase 75-06). `splits` is one key per 5 m segment rather than one list-valued key,
  // because the baseline engine looks a metric up by key across the athlete's past sessions —
  // see phaseBaseline.js. Faster on any given split is better.
  ivv: "down",
  breakout_vel: "up",
  breakout_vel_loss: "down",
  breakout_vs_steady: "neutral",
  splits_5m: "up",
  splits_10m: "up",
  splits_15m: "up",
  splits_20m: "up",
  splits_25m: "up",
  sr_dps_coupling: "neutral",
  dead_spot_timing: "neutral",
  accel_asymmetry: "neutral",
  // Whole race (Phase 75-06). Budgets stay neutral — how a race SHOULD be divided between
  // start, underwater and swimming is a race-plan call, not something a threshold can judge.
  // Peak speed within a phase is the one whole-race family with a clear direction.
  phase_time_budget_start: "neutral",
  phase_time_budget_underwater: "neutral",
  phase_time_budget_swim: "neutral",
  phase_dist_budget_start: "neutral",
  phase_dist_budget_underwater: "neutral",
  phase_dist_budget_swim: "neutral",
  vel_envelope_start: "up",
  vel_envelope_underwater: "up",
  vel_envelope_swim: "up",
  vel_envelope_overall: "up",
  jerk_smoothness: "down",
};

// Safe default: any key we haven't judged is "neutral" (flagged if out of range, never colored
// green/red). Never throws.
export function directionOfGood(key) {
  return DIRECTION_OF_GOOD[key] ?? "neutral";
}

// flagVerdict — deterministic. `band` is [lo, hi] (the athlete's usual range) or null when no
// baseline exists. Returns:
//   { flagged, direction:"above"|"below"|null, valence:"good"|"bad"|"neutral"|null }
// An in-range value → {flagged:false, valence:null} (renders a quiet "in range").
export function flagVerdict(value, band, good) {
  if (band == null || value == null || !Number.isFinite(value)) {
    return { flagged: false, direction: null, valence: null };
  }
  const [lo, hi] = band;
  const direction = value < lo ? "below" : value > hi ? "above" : null;
  if (direction === null) {
    return { flagged: false, direction: null, valence: null };
  }
  const g = good ?? "neutral";
  const valence =
    g === "neutral"
      ? "neutral"
      : (g === "up") === (direction === "above")
        ? "good"
        : "bad";
  return { flagged: true, direction, valence };
}

// statusWord — the short human status shown at the row's right edge. Arrow shows which way it
// moved; the word shows whether that direction is good.
export function statusWord(direction, valence) {
  if (!direction) return "in range";
  const arrow = direction === "above" ? "↑" : "↓";
  const word = valence === "good" ? "better" : valence === "bad" ? "worse" : "changed";
  return `${arrow} ${word}`;
}
