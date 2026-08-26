// phaseBaseline.js — last-5 same-stroke baseline for the race-phase report card (Phase 75-05).
//
// "His usual range" = median ± K·sMAD over the athlete's most recent same-stroke swims. MAD and
// median (not mean/SD) because n≈5 makes SD noisy and one odd swim shouldn't move the band. The
// reducer is pure (repo doctrine: pure core, I/O at the edge); the supabase read is the thin edge
// and is lazily imported so the reducer stays testable without the client/env. Reads bypass the
// FastAPI by design (supabase-js + RLS).

export const K = 1.5; // band half-width in scaled-MAD units — documented, tunable
export const BASELINE_LIMIT = 5;

const PHASE_KEYS = ["start", "underwater", "swim", "whole"];

function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// summarize — robust stats for one metric's prior values. n<2 → band:null (no usable spread),
// so callers render "baseline building (n/5)" instead of inventing a range.
function summarize(vals) {
  const n = vals.length;
  const med = median(vals);
  const mean = vals.reduce((a, b) => a + b, 0) / n;
  const mad = median(vals.map((v) => Math.abs(v - med)));
  const sMAD = 1.4826 * mad; // scale MAD so it is σ-comparable
  const sd =
    n >= 2
      ? Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1))
      : 0;
  const band = n >= 2 ? [med - K * sMAD, med + K * sMAD] : null;
  return { median: med, mad, sMAD, band, mean, sd, n };
}

// reducePhaseBaseline — walk PHASES×keys over the prior `phases` objects, collect each metric's
// non-null numeric values, and summarize. Returns a lookup keyed "<phase>.<key>". Pure.
export function reducePhaseBaseline(priorPhasesArr) {
  const buckets = {};
  for (const phases of priorPhasesArr ?? []) {
    if (!phases || typeof phases !== "object") continue;
    for (const phase of PHASE_KEYS) {
      const metrics = phases[phase];
      if (!metrics || typeof metrics !== "object") continue;
      for (const key of Object.keys(metrics)) {
        const v = metrics[key]?.value;
        if (typeof v !== "number" || !Number.isFinite(v)) continue;
        (buckets[`${phase}.${key}`] ??= []).push(v);
      }
    }
  }
  const out = {};
  for (const [id, vals] of Object.entries(buckets)) out[id] = summarize(vals);
  return out;
}

// fetchPhaseBaseline — the ≤5 most recent same-stroke swims strictly before this session, reduced
// to the baseline lookup. {} when the athlete or stroke is unknown (new session with no context).
export async function fetchPhaseBaseline({ athleteId, strokeType, beforeCreatedAt }) {
  if (!athleteId || !strokeType) return {};
  // Lazy so the reducer above imports cleanly without the Supabase client/env.
  const { supabase } = await import("@/lib/supabase");
  let query = supabase
    .from("sessions")
    .select("metrics_json, created_at")
    .eq("athlete_id", athleteId)
    .eq("stroke_type", strokeType)
    .order("created_at", { ascending: false })
    .limit(BASELINE_LIMIT);
  if (beforeCreatedAt) query = query.lt("created_at", beforeCreatedAt);
  const { data, error } = await query;
  if (error || !data) return {};
  const priorPhases = data.map((r) => r.metrics_json?.phases).filter(Boolean);
  return reducePhaseBaseline(priorPhases);
}
