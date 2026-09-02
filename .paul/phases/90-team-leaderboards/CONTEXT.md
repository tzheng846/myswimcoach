# Phase 90 — Team Leaderboards (within-team, per-stroke, detector-independent metrics)

*Created 2026-09-01 via `/paul:discuss` (2 question rounds, 8 decisions). Handoff for `/paul:plan`.
No plans, no code.*

> ⚠ **The single most important finding: the metric set the user first asked for cannot be ranked.**
> Four of the eight approved headline metrics are cycle-derived, and freestyle cycle segmentation
> currently detects a **median of 5 strokes on a 25 that should be 12–18**. Ranking them would
> publish segmenter failures as swimmer standings, by name, on a shared board. Measured, not
> assumed — see **F4**. The metric set was changed at the user's direction to eight
> **detector-independent** metrics (**D3**), and the resulting board was built and inspected before
> this document was written (**F6**).

## Why now

User's ask, verbatim across two rounds:

> *"I need to build a simple leaderboard system. It should be within team. Separated by gender, age
> group. there should be a leaderboard for every metric, showing the top 5, though the full list is
> stored somewhere."*

then, after the first round of findings:

> *"reduce consideration. demographics will be implemented later. for now, assume all swims are 25
> yard swims. seperate by stroke type it's ok if currently only one team. create a leader board in
> simple rankings. each swimmer should appear on every metric ranking. the rankings metrics will be
> metrics that obviously have a good vs bad, such as avg speed. time spent underwater are not
> included"*

Everything shipped to date is **within-athlete**: the report card compares a swimmer to their own
usual range, Compare runs one athlete's swims against each other, and the recorded product north
star is attention allocation with **no absolute thresholds** (Phase 53 direction). A leaderboard is
the first **between-athlete** surface in the product. That is a deliberate widening, and it is
recorded here rather than left for a future reader to notice.

## Goals

1. **A coach can see their squad ordered on a metric, per stroke, in one glance** — the ordering is
   the deliverable, not the cut.
2. **Every swimmer appears on every board for a stroke they have swum.** Achieved by choosing
   metrics that do not depend on stroke-cycle segmentation (**D3**).
3. **Nothing on the board can be wrong for a reason the coach cannot see.** Broken sessions are
   excluded by a stated rule (**D5**), not silently.
4. **No schema, no backfill, no stored ranking** — computed on read from data already loaded
   (**D6**).
5. **Leave a clean seam for what is deferred** — demographics (Phase 89 territory), cycle-derived
   metrics (Phase 80 territory).

## Decisions

| # | Decision | Notes |
|---|---|---|
| **D1** | **Partition by stroke only.** Gender and age group are **out**, deferred to a later phase. | User's explicit reduction. Neither axis exists in the DB today — see **F1**. One team is accepted as a no-op partition. |
| **D2** | **All swims are assumed to be 25 yd.** No distance field is added and none is read. | User's explicit simplification. ⚠ This assumption is **unverifiable in the data** and unenforced — see **R1**. It is the load-bearing premise of every lap-time and split comparison on the board. |
| **D3** | **Eight detector-independent metrics: Avg speed, Top speed, Lap time, UW avg speed, and the four 5 m splits (0–5, 5–10, 10–15, 15–20).** | Replaces the user's first headline set. The four cut metrics (`mean_dps_m`, `cv_arm_peak_vel`, `cv_isi`, `fatigue_index_pct`) are all cycle-derived and unrankable today (**F4**). The eight chosen read only the window and the distance grid, never `ctx.cycles`. |
| **D4** | **Row value = mean of the athlete's last N=5 swims of that stroke**, newest first. | Measured: N=3, 5 and 10 give **near-identical orders** (**F7**), because most athletes have ≤5 swims. N=5 damps one bad swim without becoming "all swims". Uses every available swim for 5 of 7 freestyle athletes today. |
| **D5** | **Plausibility guard: a session is eligible only if `total_dist_m >= 15`.** Stated on the page as an exclusion, never silent. | Keeps **84 of 99**. Removes exactly the junk: three "Test" bench sessions (0–0.6 m) and Leo's truncated 39.0 s partials (**F5**). Defensible against the documented tether constraint — a 25 yd lap tops out at ~21.9 m of travel, so <15 m never completed a lap and cannot be compared on lap time or splits. |
| **D6** | **Nothing is stored. Ranks are computed on read, client-side.** Top 5 shown; "show all" expands to the full order. | Answers the user's "the full list is stored somewhere" — it is not stored, it is *computed*, and the full order is one click away. Same pattern as `GroupCompare` / `TeamPulse`. No schema, no backfill, never stale. At 99 sessions this is instant. |
| **D7** | **Every swimmer is ranked regardless of swim count; the count is shown on the row.** | Michael's 1 freestyle swim ranks beside Tony's 20, with `n=1` visible. Satisfies "each swimmer appears on every metric ranking" literally, and refuses to hide that some rows rest on a single swim. |
| **D8** | **New `/app/leaderboard` page in the coach portal.** Stroke tabs, eight metric boards. Web only. | Room to grow when Phase 80 makes cycle metrics rankable and Phase 89 makes "team" mean something. Not on iOS (would need an EAS build, which Phase 84 already owes one for). Not visible to athletes or families — that needs Phase 89's login work, and 89 D8 says families see curated reports only. |

## What was verified in code and against the live library (not assumed)

Five read-only probes were run against the live DB during this discussion
(`scratch/_lb_probe*.py`, `_lb_preview.py`, `_lb_filters.py`, `_lb_clean.py`, `_lb_guard.py`),
applying the 83-03 / 88-01 lesson — **measure a threshold before shipping it** — preemptively.

**F1 — Neither requested demographic axis exists.**
Live `athletes` = `id, team_id, name, dob, stroke_type, head_waist_m, parent_email, parent_name,
created_at` ([supabase/live_schema.json](supabase/live_schema.json)). There is **no `gender`
column anywhere in the repo**, and `dob` is set on **0 of 10** athletes. Phase 33-02 already logged
this as needing "the demographics schema; later plan". D1 defers it; nothing about the leaderboard
is blocked by it.

**F2 — There is exactly one team, and Phase 89 will redefine what a team is.**
All 10 athletes share `team_id c37a0c1a`. ⚠ **Phase 89 D1 deletes `athletes.team_id NOT NULL`** in
favour of a membership table. Any roster query written against `team_id` is rewritten by 89 — see
**R4**.

**F3 — Nothing on a session records what swim it was.**
`sessions` carries `stroke_type` and no distance, effort, or set field. D2's "all swims are 25 yd"
is therefore an assumption the data cannot confirm or contradict.

**F4 — 🔴 Cycle segmentation is undercounting by ~2–3×, which is what disqualifies four metrics.**
Strokes detected across the 45 freestyle sessions, sorted:
`0 0 0 0 0 1 1 2 2 2 2 3 3 3 3 3 4 4 4 5 5 5 6 6 7 7 7 7 7 8 8 8 8 8 8 8 9 11 12 13 13 14 14 14 16`
A real freestyle 25 is ~12–18 cycles. **Only 8 of 45 sessions land in that range; the median is 5.**
Concretely, on the board this produced:
- **Titus led "distance per stroke" at 7.9 m** — his four swims detected **1, 2, 2 and 4** strokes.
- **Michael (0.14 m/s) and Jenna (0.02 m/s) sat last on breakout velocity** — both swims detected
  **0** strokes and **0** cycles.
- All of these sessions are **auto-segmented, none coach-marked**.
This is the open scope of **Phase 80** (*Stroke-Cycle Segmentation — count-centric re-measurement*,
🚧, freestyle-only) and matches 88-05's note that butterfly found 5 cycles where there should be
~12. It is a pre-existing defect that a leaderboard would **publish**, not one this phase creates.

**F5 — No trust filter can rescue the cycle metrics, so filtering was not the answer.** Measured:

| filter | freestyle | butterfly | breaststroke | backstroke |
|---|---|---|---|---|
| none | 7 ath / 45 sw | 4 / 29 | 6 / 18 | 2 / 2 |
| coach-annotated only | **4** / 22 | 3 / 14 | 2 / 4 | **0 / 0** |
| `stroke_count >= 6` | **4** / 23 | 3 / 23 | 4 / 10 | 1 / 1 |

Either filter cuts the roster to ~4 **and deletes the backstroke board entirely**, which directly
contradicts goal 2. Hence D3 (change the metrics) rather than filtering the sessions. Only
**41 of 99** sessions have fully coach-marked boundaries; **56 of 99** carry at least one
`provisional` metric.

**F6 — ✅ The chosen eight produce a clean board, verified by building it.**
Coverage first: every one of the eight has a value for **every athlete in every stroke** —
freestyle 7/7, butterfly 4/4, breaststroke 6/6, backstroke 2/2. The rendered board (N=5, guard
applied) has no impossible values and is internally consistent — Max leads freestyle on all eight,
Leo is consistently last, and the split-by-split ordering is stable rather than random. Goal 2 is
met by construction, not by hope.

**F7 — N barely matters.** N=3, 5 and 10 produce the same freestyle order except for Tony and Leo
swapping positions 6/7. Most athletes have ≤5 swims, so the window rarely binds. D4's N=5 is
therefore a low-stakes choice and should not be argued about in planning.

**F8 — Three metrics fail the "obvious good vs bad" test on inspection, not on taste** — all
excluded:
- `jerk_smoothness` — its own docstring says *"Usable as a within-athlete relative proxy; do not
  read it as an absolute smoothness number."* A between-athlete board is exactly the reading it
  forbids.
- `accel_asymmetry` — 1.0 is balanced, so the target is *toward 1*, not higher or lower. It has no
  sort order.
- `breakout_vs_steady` and `uw_surface_ratio` — ratios where a **slow surface swim inflates the
  score**, so higher is not reliably better.

**F9 — `reaction_time` is empty on all 99 sessions** and cannot be ranked. It only fills for
sessions recorded after 84-02 deploys, and 84-02 is still uncommitted.

**F10 — `web/lib/reportMetrics.js` is the existing direction-aware catalog** (`direction: higher |
lower | neutral`, plus `formatValue`), built in Phase 24 and reused by Phase 73's `GroupCompare`.
It carries 3 of the 8 chosen metrics already (`mean_vel_ms`, `max_vel_ms`, `lap_time_s`); the four
splits and `uw_avg_speed` are not in it. This is the convention to extend, not to reinvent.

**F11 — The four splits are the most detector-independent metrics in the registry.**
`splits_5m` … `splits_20m` are distance-gated mean velocities computed by `_split_velocity`
([phase_metrics.py:767](phase_metrics.py:767)), clamped at `finish_s`. They read no cycles and no
breakout detector. 88-04 independently re-implemented this arithmetic and matched it to
**max |Δ| = 0.00e+0**, so the derivation is already twice-verified.

## Risks

**R1 — D2's "all swims are 25 yd" is unverifiable, unenforced, and load-bearing.** Nothing in the
data distinguishes a 25 yd from a 50 m swim (**F3**). Lap time and all four splits are only
comparable under this premise. The moment a coach records a 50, that swimmer's lap time ranks last
and their splits rank normally, with nothing on screen explaining the contradiction. The page must
state the assumption; it cannot check it.

**R2 — This is the product's first between-athlete surface, against a recorded within-athlete
strategy.** The attention-allocation direction (Phase 53) is explicitly *"SPC not anomaly
detection, no absolute thresholds"*. A leaderboard is an absolute ranking. Not a blocker — the user
asked for it directly — but it is a strategy widening and should be a conscious one.

**R3 — Ranking children by name is a different privacy posture than the product has today.** Every
existing surface shows a coach one athlete, or a parent their own child. A board shows a named
minor ranked below their teammates. D8 keeps it coach-only, which contains this — but it must stay
contained: **do not** surface it to families or on a tokenized public page without a deliberate
decision.

**R4 — Phase 89 rewrites the roster query.** D1 of Phase 89 replaces `athletes.team_id NOT NULL`
with a membership table. Whatever this phase writes to fetch "the team's athletes" is on 89's
rewrite list. Cheap to absorb if the roster fetch is one function; expensive if it is inlined into
eight boards.

**R5 — The guard is a silent filter unless it is stated.** D5 removes 15 of 99 sessions. A coach
who recorded a short swim and cannot find it on the board must be able to learn why from the page,
not from this document.

**R6 — Six of the eight metrics depend on race-phase boundaries**, which are auto-detected on 58
of 99 sessions. `uw_avg_speed` needs `underwater_start_s` and `stroke_start_s`; the splits need
`dive_start_s` and `finish_s`. Boundaries are in far better shape than cycles (Phase 79 got
`dive_start` MAE to 0.15 s; Phase 59 made the swim window rhythm-based) — but they are not exact,
and this is the residual accuracy risk after D3 removes the large one. **Avg speed, top speed and
lap time are the only three with no detector dependence at all.**

**R7 — Small boards look like rankings but behave like lists.** Backstroke has 2 athletes,
butterfly 4. "Top 5" hides nobody on three of the four stroke boards. The design should not lean on
a cut that does not exist (goal 1 says so explicitly).

## Open questions for `/paul:plan`

1. **Does the page show the metric's value, the rank, or both?** The measured board reads well as
   `1. Max 1.88 m/s (n=5)`. Confirm before building 8 × 4 of them.
2. **Does the leaderboard respect the Phase 88 unit toggle?** `unitConvert.js` shipped in 88-03 and
   is page-scoped by 88's own R7. Seven of the eight metrics are unit-bearing. Reusing it is cheap
   and consistent; not reusing it means a metres-only board next to a page that converts.
3. **How is the roster fetched, and is it one function?** Directly bears on **R4**. Note that
   `GET /team/overview` already returns a team-scoped roster ([api.py:648](api.py:648)) and is the
   only endpoint that scopes by `team_id` rather than `coach_id`.
4. **Is the guard (D5) and the 25 yd assumption (D2) stated in one caveat line or two?** 88-02
   established the precedent of one caveat line per page stating its anchor.
5. **Client-side ranking needs every session's `metrics_json`** — does the existing supabase-js read
   pattern pull the whole roster's sessions in one query, and is 99 sessions of jsonb an acceptable
   payload? (Probably yes; confirm rather than assume, since `metrics_json` carries the full
   `phases` object plus `cycles` and `strokes`.)
6. **Does a tie need a defined order?** Unlikely at these magnitudes, but a stable sort avoids the
   board reshuffling between renders.
7. **Where do the four cut metrics get recorded as owed?** They are Phase 80's payoff — when
   segmentation is fixed, `mean_dps_m`, `cv_arm_peak_vel`, `cv_isi` and `fatigue_index_pct` become
   rankable and this page gains four boards. Worth a STATE item so the link is not lost.

## Out of scope

- **Gender and age group** (D1) — no `gender` column, no `dob` backfill, no age-band convention, no
  athlete-form changes. A later phase, and one that overlaps Phase 89's athlete-profile rework.
- **Any distance / effort / test-set field on `sessions`** (D2) — the 25 yd assumption is stated,
  not enforced.
- **All cycle-derived metrics** (D3, **F4**) — distance per stroke, stroke consistency, rhythm
  consistency, fatigue index. Blocked on **Phase 80**, not on this phase.
- **Stored rankings, a leaderboard table, rank-movement history** (D6) — computed on read.
- **`reaction_time`** (**F9**) — 0 of 99 sessions, blocked on 84-02 deploying.
- **Arm-asymmetry metrics** (Phase 87) — 87-01 measured them as **uncorrelated with coach-mark
  truth on auto sessions (r = −0.06)**, which is disqualifying for a between-athlete board.
- **iOS** (D8) — web portal only; mobile would need an EAS build, which Phase 84 already owes.
- **Athlete or family visibility** (D8, **R3**) — needs Phase 89's logins, and 89 D8 limits families
  to curated reports.
- **Any backend, schema, migration or pipeline change.** Nothing here touches `metrics.py`,
  `phase_metrics.py`, `vel_acc_extraction.py`, or `api.py`.
- **Fixing the segmenter.** This phase routes around **F4**; it does not repair it. That is Phase 80.
