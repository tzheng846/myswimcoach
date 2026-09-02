// leaderboardData.js — the ONE read behind /app/leaderboard (Phase 90-02).
//
// Presentation lives in the page and the ranking maths in lib/leaderboard.js; this module exists
// only so that "which swims are on the leaderboard" has exactly one answer, in one place.

import { supabase } from "@/lib/supabase";
import { SESSION_SELECT, isEligible } from "@/lib/leaderboard";

/**
 * Roster + their eligible swims, newest-first, in a single round trip.
 *
 * ⚠ PHASE 89 LANDS HERE. Phase 89 D1 removes `athletes.team_id NOT NULL` in favour of a
 * membership table, so "the coach's athletes" stops being a column lookup and becomes a join.
 * This function is the single seam that has to be rewritten when it does — the page below never
 * queries `athletes` itself, and no board reaches back into the roster, precisely so that rewrite
 * is one function and not eight components.
 *
 * There is no `team_id` filter written here today either: reads go straight to Postgres under RLS
 * (DATA-FLOW.md — `sessions.coach_id` is the ownership column), so the roster is already scoped to
 * the signed-in coach.
 *
 * ⚠ `recorded_at` is UPLOAD time, not swim time (STATE owed item 22). api.py never sets it, so it
 * takes the schema default NOW(). It is nonetheless the only ordering key that exists across all
 * 99 sessions — `session_start_utc_ms` (86-01) covers only sessions recorded after Phase 86 ships
 * — so "last N swims" is really "last N uploads". Deliberately no fallback chain: the caveat is
 * surfaced in the UI rather than papered over here.
 *
 * @returns {Promise<{athletes: Map<string,string>, rows: object[], excluded: number, total: number}>}
 *   `rows` are roster-scoped and guard-passing, each carrying the athlete's `name`.
 *   `total` counts the roster's swims BEFORE the 15 m guard, `excluded` how many it removed —
 *   so the page's caveat is computed from the loaded data, never hard-coded.
 */
export async function fetchLeaderboard() {
  const athleteQuery = supabase.from("athletes").select("id, name").order("name");
  const { data: athleteRows, error: athleteError } = await athleteQuery;
  if (athleteError) throw athleteError;

  const athletes = new Map((athleteRows ?? []).map((a) => [a.id, a.name]));

  // One query for every stroke and every metric. Measured against the live DB at 99 rows (the
  // library was 108 by the time this shipped): 47 KB with this deep-scalar select, against 503 KB
  // pulling the phase objects whole and 1.5 MB for the full metrics_json, in 0.76 s. The
  // per-stroke partition is a client-side filter, never a second round trip.
  const sessionQuery = supabase.from("sessions").select(SESSION_SELECT);
  const { data: sessionRows, error: sessionError } = await sessionQuery.order(
    "recorded_at",
    { ascending: false }
  );
  if (sessionError) throw sessionError;

  // Roster-scoped first: a session whose athlete is not on this roster is not "excluded by the
  // guard", it was never a candidate, and counting it would inflate the caveat.
  const mine = (sessionRows ?? []).filter((r) => athletes.has(r.athlete_id));

  const rows = mine
    .filter(isEligible)
    .map((r) => ({ ...r, name: athletes.get(r.athlete_id) }));

  return { athletes, rows, excluded: mine.length - rows.length, total: mine.length };
}
