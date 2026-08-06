# 33-02 SUMMARY — Team-wide tools

**Status:** ✅ Complete (APPLY + UNIFY) 2026-06-16. Loop closed.
**Branch/PR:** to push as `feat/coach-chat-team-tools` (user runs git).

## What shipped
The coaching chat can now answer **roster-wide** questions ("who's lagging on DPS?", "who
progressed most?", "how's my team?") via three team tools plugged into 33-01's tool-use loop.
Backend only; no new dependency.

- **roster_metrics.py** (new, pure/no-I/O): `latest_per_athlete`, `rank_athletes`
  (metric-agnostic, ascending/descending, drops missing metric), `rank_progress`
  (% change earliest→latest, athletes below `min_sessions` set aside as `insufficient_data` —
  never a fabricated trend), `team_summary` (count + mean/min/max across latest-per-athlete).
- **coach.py** — `TEAM_TOOLS` (rank_athletes, rank_progress, team_summary) + `_TEAM_HINT` folded
  into `_build_system_prompt`, including a guardrail: do NOT rank swimmers on kick-specific
  metrics (kick detection unreliable) — say so if asked.
- **api.py** — `import roster_metrics`; cached roster loader (ONE athletes query + ONE sessions
  query per turn, both `coach_id`-filtered; sessions whose athlete isn't in the coach's map are
  dropped — defense in depth); three coach-scoped executors registered in `_EXECUTORS`; loop
  passes `COACH_TOOLS + TEAM_TOOLS`; `_TEAM_HINT` added to the simple branch too.
- **Hedge (visual proof):** the loop now collects each executed tool's `{tool, input, result}`
  and `/coach/chat` returns `{"reply", "data": [...]}` (was `{"reply"}`). New field only —
  backward compatible. Makes a future "show the data" panel / compare deep-link front-end-only.
- **tests** — `tests/test_roster_metrics.py` (6 pure tests) + `TestCoachChatTeam` /
  `test_team_tools_declared` in test_api.py (coach scoping on both queries, out-of-roster
  exclusion, structured `data` return, progress thin-data exclusion).

## Verification
- Full suite **54 passed** (was 45). `import coach / api / roster_metrics` clean.
- No new `requirements.txt` entry.
- Roster executors use exactly one athletes + one sessions query per turn, both `coach_id`-scoped
  (asserted in tests).

## Decisions
- **Team tools return athlete NAMES** — a deliberate, narrow exception to 33-01's no-PII stance,
  justified: team triage is meaningless without names, and names go only to the owning coach
  (who already sees their full roster). Names never leave the coach's own context.
- Coach-scoped (not athlete-scoped); server-side aggregation only — the model never receives raw
  multi-athlete cycle data.
- One canonical "progress" definition: (latest − earliest)/|earliest| × 100 on the chosen metric.
- Kick-ranking questions declined honestly via a prompt guardrail (kick metric not fixed here).

## Deviations from plan
None material. Added the visual-proof hedge (`data` in the response) per user decision mid-plan.

## Deferred / next
- **Live human-verify** still bundled into 33-04 (key on Railway + signed-in coach).
- Cohort/age-group/gender comparison + `gender` schema → later plan (needs demographics).
- Dashboard-level "Ask your coach" entry point → later (works from the session chat today).
- **Visual proof / compare deep-link** → new plan 33-05 (front-end-only now, thanks to `data`).
- Deploy: api.py/coach.py/roster_metrics.py changed → Railway auto-deploys on merge to main.
