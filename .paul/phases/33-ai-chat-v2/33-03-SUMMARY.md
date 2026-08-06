# 33-03 SUMMARY — Drill library + metric tag-matching recommender

**Status:** ✅ Complete (APPLY + UNIFY) 2026-06-16. Loop closed.
**Branch/PR:** stacked on `feat/coach-chat-team-tools` (33-02 not yet merged) — joins that PR.

## What shipped
The chat's call-to-action is now grounded in a curated drill library, matched to the
swimmer's actual metric problems. Tag-matching only (semantic RAG = 33-04); no new dependency.

- **drills.py** (new, pure): `FLAGS` taxonomy (low_dps, low_trough_vel, high_cv_isi,
  inconsistent_power, high_fatigue, passive_coast); `DRILLS` (8 flagship drills, our own
  descriptions, each tagged with target flags + a one-line "why"); `flags_from_session`
  (metrics→flags via thresholds reused from coach.py prose: cv_isi>0.15, fatigue>8,
  trough<0.05, cv_arm>0.20, dps<1.5, passive_coast compound); `match_drills` (overlap-ranked).
- **coach.py** — `DRILL_TOOLS` (`recommend_drills`) + `_DRILL_HINT` folded into the prompt
  with the guardrail: call recommend_drills first, recommend ONLY from its list, tie to the
  numbers, and say "looks solid" (no invented fix) when nothing is flagged.
- **api.py** — `import drills`; `_exec_recommend_drills` (uses the in-memory anchor session —
  no extra query) registered in `_EXECUTORS`; tools = COACH_TOOLS + TEAM_TOOLS + DRILL_TOOLS;
  `_DRILL_HINT` added to the simple branch. Drill shortlist flows into the {reply, data} hedge.
- **tests** — `tests/test_drills.py` (7 pure: threshold boundaries, compound passive_coast,
  None-safety, overlap ranking, library well-formed, every flag covered) + `TestCoachChatDrills`
  + `test_drill_tool_declared` (flagged session → matching drills; clean session → [] + note).

## Verification
- Full suite **64 passed** (was 54). `import drills/coach/api` clean.
- No new `requirements.txt` entry.
- Every DRILLS.targets is a known FLAG; every FLAG has ≥1 drill (asserted).

## Decisions
- The metric→problem→drill BRIDGE is encoded as a `targets` field per drill; the AI matches
  flags→drills and explains — it does not invent the mapping. This is what makes the
  recommendation quantitative + reviewable.
- recommend_drills uses the current (anchor) session only — cross-session drill recs deferred.
- DRAFT content: drill text + thresholds + mapping are an expert-informed first draft and need
  a real coach's review before customer-facing use (documented in drills.py docstring).

## Deviations from plan
None material.

## Deferred / next
- **33-04 (next):** semantic drill RAG (free-text "breathing drill?") — needs an embeddings
  provider (new key + dependency + cost; user-owned decision). Isolated on purpose.
- Coach review/tuning of the draft library + thresholds (trust gate before selling).
- Live human-verify still bundled into the streaming plan (now 33-05).
- Deploy: api.py/coach.py/drills.py changed → Railway auto-deploys on merge to main.
