# Project State

*Lean current-state snapshot — updated as work lands. How the pipeline **works** lives in
[PIPELINE.md](../PIPELINE.md) (repo root); the phase index in [ROADMAP.md](ROADMAP.md); the data map
in [DATA-FLOW.md](../DATA-FLOW.md). The full pre-2026-08-20 running log (4,905 lines) is archived at
[.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md).*

## Current Position

- **Milestone:** v0.5 Commercial Foundation
- **✅ 86-04 LOOP CLOSED 2026-09-02** (`PLAN ✓ → APPLY ✓ → UNIFY ✓`) —
  [86-04-PLAN.md](phases/86-session-clock-accuracy/86-04-PLAN.md) ·
  [86-04-SUMMARY.md](phases/86-session-clock-accuracy/86-04-SUMMARY.md). 3/3 tasks, **8/8 AC**, each
  task committed separately so the measurement provably predates the constants it produced
  (`2043026` → `b40bcaf` → `78711b6`). Gates: self-test **PASS** incl. the new ring-down case,
  `--validate-timebase` **39/39 at 0.000000 ms**, pytest **566 passed**.
  🔴 **THE REPAIR WORKED AND ACCEPTANCE STILL FELL, 83.3% → 66.7% — WHICH IS THE CORRECT
  TRADE.** Accepted taps sitting >50 ms from their session median went **10 → 0**, worst deviation
  **315.1 ms → 33.7 ms**, worst over-trigger ratio **5.6 → 1.0**. 86-03's laundering is gone; what
  replaced it is visible rejections. **B3 still fails on this corpus (66.7% < 90%)** — expected,
  written down before the re-run, and unfixable here because the data was collected through the
  broken instrument. **B1 REMAINS UNMEASURED.**
  UNIFY found: 3 auto-fixed defects, each of which would have read as success — the interval check
  ran session-wide and regressed the standing desync gate **11/1 → 0/12** (moved to a PASS 3 over
  scatter-surviving taps); the fixture's 200 counts/s baseline was **8.5 % of peak `|velocity|`** and
  lifted every planted ring over the cut; and `|velocity|` of an overshooting impulse has **two
  lobes**, so one strike raised two candidates refining to the same raw sample and inflated the very
  over-trigger field meant to expose that. 1 AC amended: AC-5's 2 ms bar moved off a frame-quantised
  residual (±16.7 ms by construction) onto the encoder time vs the fixture's known strike — **0.46 ms**.
  AC-7's verdict on under-detection is **split, not tidy**: of 7 unmatched onsets, **4 are real soft
  strikes** (7.2–19.0 % of peak) and **3 are at the noise floor** (1.7–3.3 %) — the phone heard
  something that was not a strike, so the **audio onset count is not clean ground truth either**.
  🔴 **PHASE 86 NOW READS 4 PLANS / 4 SUMMARYS AND THE COUNT IS WRONG AGAIN** — the same trap as
  83-01, 83-02, 88-04 and 86-03. **No transition, no phase commit.**
  **Next action: 86-05 — the confirmatory run, already registered in
  [TAP-TEST-PROTOCOL.md](phases/86-session-clock-accuracy/TAP-TEST-PROTOCOL.md) §10 with B1–B4
  unchanged in value.** It is **gated on a mobile change + EAS build** (persist `videoStartPhoneMs`)
  and a pool session with ≥ 8 consistent-force strikes per rep. With Phase 90 closed 2026-09-02 and
  this loop closed, **there is no open PAUL loop in the repo** — the next move is a plan, not an apply.
- **✅ 86-03 LOOP CLOSED 2026-09-01** (`PLAN ✓ → APPLY ✓ → UNIFY ✓`). Its device run happened and was
  **VOID** under its own pre-registered B3 bar; 86-02's AC-7 passed in the process, which closes
  86-02. 🔴 **PHASE 86 IS NOT TRANSITIONED AND HAS NO PHASE COMMIT — 3 of 3 plans had SUMMARYs, and
  that is exactly the plan-count trap that wrongly called 83-01, 83-02 and 88-04 done.** The phase
  existed to replace estimates with measurements; it replaced three and left its headline one (the
  end-anchored residual a coach sees) unmeasured. **Closing it on counts would bank a void run as a
  finished measurement.** ~~A successor plan (86-04) is owed~~ → **WRITTEN 2026-09-01, see above.**
  The phase is now **3 of 4 closed, 4 planned**, so the count heuristic no longer reads done either.
- **Phase 90** (Team leaderboards) — ✅ **COMPLETE AND TRANSITIONED 2026-09-02. 3 of 3 plans, every
  loop closed, phase commit made.** Closed on the phase's five CONTEXT goals being delivered and
  **seen on screen**, not on the plan count: the deliverable is a ranked board a coach looked at and
  approved. (Contrast Phase 86, which had 3 of 3 SUMMARYs and its headline measurement still
  untaken — that is the trap this close deliberately does not repeat.) Loop: 90-01
  `PLAN ✓ → APPLY ✓ → UNIFY ✓` (closed 2026-09-01, [90-01-SUMMARY.md](phases/90-team-leaderboards/90-01-SUMMARY.md));
  90-02 ✅ **LOOP CLOSED 2026-09-02** `PLAN ✓ → APPLY ✓ → UNIFY ✓`
  ([90-02-SUMMARY.md](phases/90-team-leaderboards/90-02-SUMMARY.md));
  90-03 ✅ **LOOP CLOSED 2026-09-02** `PLAN ✓ → APPLY ✓ → UNIFY ✓`
  ([90-03-SUMMARY.md](phases/90-team-leaderboards/90-03-SUMMARY.md)).
  CONTEXT: [90/CONTEXT.md](phases/90-team-leaderboards/CONTEXT.md) (2 discuss rounds, 8 decisions).
  Waves are strictly serial — 90-01 → 90-02 → 90-03 — because 02 imports 01's catalog and select
  string, and 03 rewrites the `page.js` 02 creates.
  - **90-01 — ranking core** ✅ **LOOP CLOSED 2026-09-01** (wave 1, `depends_on: []`, autonomous).
    New pure `web/lib/leaderboard.js` (162 lines) + `scratch/leaderboard_check.mjs` (314): the
    8-metric catalog, `SESSION_SELECT`, the 15 m guard, the derived lap time, the last-N mean, and
    `rankBoard` with a stable tie-break. **6/6 AC pass.** Purely additive — no existing file
    touched. Harness **63 passed, 0 failed**, exit 0 with no auth, no network, no dev server and no
    `typescript` staging (a pure ESM lib with no JSX and no `@/` aliases is imported directly — a
    cheaper harness pattern than 87-02/88-03/88-04/88-05's transpile-and-render). eslint clean,
    `npm run build` clean. The module's own source text is asserted on, so `lap_time_s`, `t[-1]`,
    `supabase` and `react` are absent from it **by test**, and a per-metric loop pins the catalog to
    `SESSION_SELECT` so the two cannot drift. ⚠ One deviation: Task 1's requested header comment
    contained the very strings Task 2 bans, so the header was reworded rather than the assertions
    weakened. ⚠ One addition: `metricByKey` (matches `reportMetrics.js`), so `rankBoard` takes a key
    string or a catalog entry.
    See [90-01-PLAN.md](phases/90-team-leaderboards/90-01-PLAN.md) ·
    [90-01-SUMMARY.md](phases/90-team-leaderboards/90-01-SUMMARY.md).
  - **90-02 — data layer + route** ✅ **LOOP CLOSED 2026-09-02** (wave 2, autonomous, 3/3 tasks,
    **6/6 AC**). New `web/lib/leaderboardData.js` (one export, `fetchLeaderboard()`, both queries,
    the Phase-89 seam comment on the function) + `web/app/app/leaderboard/page.js` + one `navLinks`
    entry + `scratch/_lb_expect.py`. `npm run build` clean at **21 routes** (was 20), eslint
    **26 problems / 23 errors = zero new**, and **all eight** standing harnesses green *unedited*
    (`leaderboard_check` 63/63, `anchor_check` 17/17, `stroke_toggle_check` 63/63,
    `overlay_render_check` 40/40, `marketing_render_check` 45/45, `unit_check` 63/63,
    `split_picker_check` 44/44, `trend_toggle_check` 39/39).
    ✅ **The stroke census holds exactly:** `_lb_expect.py` prints **freestyle 7 ath / 42 sw ·
    butterfly 4 / 28 · breaststroke 5 / 12 · backstroke 2 / 2**, four blocks summing to 84, and
    **no udk block** — all five udk sessions measure 9.87–13.48 m and the guard removes every one.
    Breaststroke reads **4 of 5** on Split 15–20 m, so CONTEXT F6's live counter-example is
    confirmed on real data, not hypothesised.
    ⚠ **The library grew to 108 sessions during Phase 86** — the plan measured 99. The 9 new rows
    are 86-03's tap-test bench runs (2026-09-01 22:04–22:15 local, 0.0008–0.095 m), **all under the
    guard, so eligible is still exactly 84 and every stroke count is unchanged.** Only the
    denominator moved: because AC-4 requires the caveat to be computed, the page reads "24 of 108
    excluded", not the plan's 15 of 99. That is the AC working.
    ⚠ **Deviation:** the plan said to reuse `GroupCompare.js`'s `STROKE_LABELS`, but that copy is
    module-local; an identical map is **exported** from `SessionCard.js` and already imported by two
    other files, so that one was imported instead. `web/lib/leaderboard.js` was therefore never
    edited and the boundary's sanctioned exception went unused. `GroupCompare.js` keeps its private
    duplicate — deduplicating it would touch a file AC-5 forbids changing.
    ⚠ **AC-3/AC-4/AC-6 are verified by the build plus an independent server-side census, NOT by a
    rendered page.** The route sits behind the portal auth gate and this plan shipped no render
    harness by design. **90-03's blocking human-verify is the first human sighting of these tabs,
    and it should diff the on-screen counts against `scratch/_lb_expect.py`.**
    See [90-02-PLAN.md](phases/90-team-leaderboards/90-02-PLAN.md) ·
    [90-02-SUMMARY.md](phases/90-team-leaderboards/90-02-SUMMARY.md).
  - **90-02 — data layer + route** (wave 2, `depends_on: ["90-01"]`, autonomous). One
    `fetchLeaderboard()` in `web/lib/leaderboardData.js` — **the single seam Phase 89 D1 will
    rewrite** (CONTEXT R4) — plus `/app/leaderboard` with stroke tabs, the caveat block and one nav
    entry. Deliberately a horizontal cut against `plan-format.md`'s advice, and the reason is
    stated in the plan: what is most likely wrong here is *which swims are in the page*, and that is
    verifiable before any board exists.
    See [90-02-PLAN.md](phases/90-team-leaderboards/90-02-PLAN.md).
  - **90-03 — the boards** ✅ **LOOP CLOSED 2026-09-02** (wave 3,
    `depends_on: ["90-02"]`, **not autonomous**). 3/3 auto tasks, **8/8 AC**, blocking human-verify
    **approved**. New `web/components/portal/LeaderboardBoard.js` (82 lines); `page.js`'s
    placeholder per-metric count replaced by a `sm:grid-cols-2` grid of eight boards plus the
    metric/imperial toggle on the standing `swimnetics.unit` key; `scratch/leaderboard_check.mjs`
    grew a render half — **63 → 97 checks, 0 failed**, still no auth, no network, no dev server.
    Its load-bearing assertion holds: a metric render and an imperial render produce the **same
    sequence of names and ranks** while every value string changes — structural, because
    `rankBoard` runs on SI and `displayUnit` is applied at format time (88-03 D2). The seconds
    board is asserted **byte-identical** under imperial rather than special-cased. Gates: `npm run
    build` clean (21 routes), eslint **exactly the 26/23 baseline**, all seven standing harnesses
    pass **unedited**, `pytest tests/` **566 passed**.
    ⚠ Two facts the plan text predates: the library grew to **108 sessions, 84 eligible, 24
    excluded** (the plan said 15 of 99 — the caveat block computes it live, so the page is right
    and the plan text is stale); and the unit toggle sits on the stroke-tab row rather than
    below the caveat block, approved at the checkpoint.
    ⚠ **AC-8 rested entirely on the human.** In-session browser navigation to `localhost` was
    denied and the page sits behind a coach sign-in that must not be performed on the user's
    behalf, so the machine half stopped at "route returns 200, dev-server logs clean" and the
    census was printed for side-by-side comparison. Recorded rather than implied to have been
    machine-checked.
    See [90-03-PLAN.md](phases/90-team-leaderboards/90-03-PLAN.md) ·
    [90-03-SUMMARY.md](phases/90-team-leaderboards/90-03-SUMMARY.md).
  🔴 **PLANNING FOUND A DEFECT CONTEXT MISSED, and it is the phase's biggest single finding:
  `metrics_json.session.lap_time_s` IS NOT A LAP TIME.** [metrics.py:1870](../metrics.py) computes
  it as `float(t[-1])` — the **duration of the recording**. Measured across the 84 eligible
  sessions it disagrees with `finish_s − dive_start_s` on **84 of 84**, median **5.75 s**, max
  **28.29 s**, and **19 of 84 read exactly 39.0 s** (the firmware's fixed record length). Ranking on
  it ranks who stopped recording soonest. `finish_s − dive_start_s` is present on **84/84** (median
  15.1 s, range 4.8–21.9) and uses the same anchor 88-02 hoisted, so 90-01 derives it under the key
  `elapsed_s` and the string `lap_time_s` is banned from the module by a harness check.
  ⚠ **This defect is WIDER than this phase** — the same field is what `web/lib/reportMetrics.js`
  labels "Lap Time" on the **parent report card**, and it also feeds `GroupCompare`,
  `windowMetrics.js` and `api.py:1678`. Routed around here, not fixed. **New owed item 30.**
  ⚠ **The last-N window rides on owed item 22.** D4 means "the athlete's last 5 swims", and the only
  ordering key that exists across all 99 sessions is `recorded_at` — which stores **upload** time,
  not swim time. Fine while upload follows the swim by minutes; wrong for a late queued upload.
  `session_start_utc_ms` (86-01) is the correct field and exists only for sessions recorded after
  Phase 86 ships, so it cannot order the library yet. Stated in the plans, not silently assumed.
  ⚠ **CONTEXT R6 is CORRECTED by planning:** it claims *"avg speed, top speed and lap time are the
  only three with no detector dependence at all."* Wrong on all three — `mean_vel_ms` and
  `max_vel_ms` are computed over `vel[b_end:swim_end]` ([metrics.py:1763](../metrics.py)), both
  detector-resolved, and the derived lap time needs two boundaries. **All eight metrics are
  boundary-dependent.** What survives, and what F4 was actually about, is **cycle-independence**:
  none of the eight reads `ctx.cycles`.
  ⚠ **CONTEXT F6 is CORRECTED by planning:** "every one of the eight has a value for every athlete
  in every stroke" fails on exactly one live cell — **Dane has no `splits_20m` on either of his two
  eligible breaststroke swims**. So the unranked-row branch is live on real data on day one, which
  is why 90-03 AC-3 exists rather than being a hypothetical.
  ⚠ **CONTEXT F5's census is pre-guard.** Under D5's `total_dist_m >= 15` the eligible board is
  **freestyle 7 ath / 42 sw · butterfly 4 / 28 · breaststroke 5 / 12 · backstroke 2 / 2** — the
  guard removes an entire athlete ("Test", 3 bench sessions at 0.00–0.59 m) from breaststroke, and
  **deletes `udk` as a board** (all 5 udk sessions are Leo's, all under 15 m).
  ✅ **CONTEXT open question 5 answered by measurement, not assumption:** a **deep scalar** PostgREST
  select of exactly the 9 needed values costs **47 KB / 99 rows / 0.76 s**, against 503 KB for the
  scoped phase objects and 1.5 MB for the full `metrics_json`. One query, no pagination. Also
  measured: `recorded_at` is non-null on **99/99**, so it is safe as the newest-first ordering key.
  ✅ Boundary provenance on the 84 eligible: `dive_start_s` manual 41 / detected 20 / auto 23;
  `finish_s` detected 43 / manual 41.
  ⚠ **R1 has teeth and planning did not remove them.** Among eligible sessions `finish_s −
  dive_start_s` spans 4.8–21.9 s and one session implies **4.35 m/s** — a detector failure the
  guard does not catch. The page states the 25 yd assumption; nothing can check it.
  Read-only probes (uncommitted): `scratch/_lb_payload.py`, `_lb_payload2.py`, `_lb_cov.py`,
  `_lb_edge.py`, `_lb_lap.py`, `_lb_lap2.py`, on top of the discuss-phase `_lb_probe*.py`.

- **Phase 89** (Account model rework) — **📋 NEXT AFTER 90. CONTEXT.md exists
  ([89-account-model-rework/CONTEXT.md](phases/89-account-model-rework/CONTEXT.md), untracked), no
  plans written.** ⚠ Its D1 deletes `athletes.team_id NOT NULL` for a membership table, which
  rewrites Phase 90's roster read — kept to one function (90-02 AC-1) so the cost stays small.

- **Phase 88** (Selectable splits + unit conversion — web report card) — **✅ COMPLETE 2026-09-01,
  5 of 5 plans, every loop closed. Code shipped in `e2c5814` (pushed check owed).**
  Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓` on all five.
  **88-05 CLOSED 2026-09-01** ([88-05-SUMMARY](phases/88-splits-picker-and-units/88-05-SUMMARY.md))
  — the velocity trend overlay. Its APPLY **ran in an unrecorded session and was committed without
  a SUMMARY**, discovered when the user asked whether the phase had been approved; UNIFY therefore
  **re-derived every claim from the diff and by re-running the gates from a clean tree**, the same
  reconciliation-of-found-work posture as 84-02 and 88-03. Re-verified at close: `rolling_mean_check`
  **39/39**, `pytest` **566 passed**, `next build` clean (20 routes), `npx eslint .` **26 problems /
  23 errors = zero new**, and all six standing harnesses green — `anchor_check` 17/17,
  `stroke_toggle_check` 63/63, `overlay_render_check` 40/40, `marketing_render_check` 45/45,
  `unit_check` 63/63, `split_picker_check` 44/44. `web/` and `scratch/` were clean against `HEAD`,
  so nothing was quietly fixed up during UNIFY.
  🔴 **88-05's blocking human-verify was NEVER PERFORMED.** The commit message says so itself
  ("deferred at the user's direction"); the user approved it **retroactively on 2026-09-01, without
  looking at the chart**. AC-2, AC-6 and AC-7 are proven mechanically (the decimation trap is pinned
  by a synthetic 4000-point assertion plus source-text checks that `rollingMean` is called *before*
  the stride; `/video` is not in the commit at all and `AccelerationChart` has zero references to
  it). **AC-1, AC-3, AC-4 and AC-5 have no on-screen evidence** — recharts emits an empty wrapper
  under `renderToStaticMarkup`, which the harness flags in its own output. The cheapest close:
  `cd web && npm run dev`, open a Chantee 2026-08-20 butterfly session, drag the slider 0 → 1 → 3 s,
  flip metric/imperial, and open `/video` to confirm no dotted line.
  ⚠ **88-05's human-verify step 8 was impossible as written** — it asks to confirm "the
  Time-to-Distance marker still draws", but 88-04's verify **deleted that card**. 88-05 was planned
  against a pre-88-04 tree. `markerTimeS` / `markerLabel` survive on both charts with no caller on
  either route.
  ⚠ **Observation carried forward:** `VelocityChart`'s strided loop skips indices where raw
  velocity is null *before* pushing a point, so the trend line inherits the raw trace's dropout
  gaps even though `rollingMean` computed a valid mean there. The mean at every **plotted** point is
  correct — this is a rendering consequence, not a bug in the library.
  ⚠ **STILL OWED after the phase close:** (a) 88-05's visual check above; (b) **88-02's blocking
  human-verify**, never separately confirmed, on a change that moves numbers a coach has already
  read (~0.4–0.5 s on 37 "Tony" sessions, up to 12.39 s on 27 divergent ones); (c) the **one-word
  wording fix** — the caveat line should read *"from your annotation"*, it still reads *"from your
  marks."*, and `anchor_check` check 5 pins that exact string, so it is a one-word edit **plus** one
  line in the gate.

  *Historical record below, as written 2026-08-31 while the phase was in flight:*
  WAVE 1 CLOSED 2026-08-31: 88-01 and 88-02 are `PLAN ✓ → APPLY ✓ → UNIFY ✓`
  ([88-01-SUMMARY](phases/88-splits-picker-and-units/88-01-SUMMARY.md),
  [88-02-SUMMARY](phases/88-splits-picker-and-units/88-02-SUMMARY.md)).
  WAVE 2 CLOSED 2026-08-31: 88-03 and 88-04 are `PLAN ✓ → APPLY ✓ → UNIFY ✓`, both human-verifies
  APPROVED ([88-03-SUMMARY](phases/88-splits-picker-and-units/88-03-SUMMARY.md),
  [88-04-SUMMARY](phases/88-splits-picker-and-units/88-04-SUMMARY.md)).
  ~~**88-05 remains `PLAN ✓ → APPLY ○ → UNIFY ○`.**~~ → **RESOLVED 2026-09-01: applied,
  committed in `e2c5814`, unified.** Suite 563 → **566 green**;
  backfill applied by the user across **99 of 99** sessions.
  ~~🔴 **PHASE NOT TRANSITIONED, NO PHASE COMMIT — the phase is 4 of 5, not 4 of 4.**~~ →
  **RESOLVED 2026-09-01 at 5 of 5.** The warning held: 88-04's success criteria said "Phase 88
  closes at 4 of 4 plans", written BEFORE 88-05 was appended at the user's direction, and acting on
  it would have repeated the plan-count trap flagged four times over for phase 83. The phase was
  held open until 88-05's loop actually closed.
  🔴 **WAVE 2 SCOPE ADDITION — Time-to-Distance was REMOVED at 88-04's verify, on the user's
  explicit direction** ("it's redundant when segment splits exists"). This contradicts 88-04's own
  D1 rationale and its explicit `DO NOT CHANGE: TimeToX.js` boundary, and it lands ONE DAY after
  88-02 re-anchored that very card — so **88-02's shipped work now has no UI**. The anchor caveat
  block MOVED into the Segment splits section and **stayed in `page.js`** (not pushed into
  `SplitPicker`), which is why `scratch/anchor_check.mjs` still passes **17/17 unedited**.
  ⚠ **`web/components/portal/TimeToX.js` now has ZERO importers**, and the `markerTimeS` /
  `markerLabel` props + their `ReferenceLine` blocks on both charts have **no caller on either
  route**. Left in place and named, per the 88-02 D4 convention.
  ~~⚠ **OWED — one-word wording question:** the line should read *"from your annotation"*.~~ →
  **DONE 2026-09-01** in the follow-up below; `anchor_check` check 5 rewritten to pin the new
  string AND assert the old one is gone.
  ⚠ **iOS still ships its own Time-to-Distance** (`ReportCardScreen`), so web and mobile now differ
  in what the session screen offers — on top of the ~0.4–0.5 s TimeToX disagreement 88-02 logged.
  ⚠ **88-05 edits `VelocityChart.js` AND `page.js`, both touched by 88-04** — its PLAN must be
  re-read against the CURRENT tree, not the version it was written against; the Time-to-Distance
  removal changed `page.js`'s `middleSlot` shape.
  ✅ **Wave 2 verification, all green:** `unit_check` **63/63**, `split_picker_check` **44/44**,
  `npm run build` clean, `npx eslint .` **26 problems / 23 errors = zero new** against the
  post-87-02 baseline, and the four gates pass **unedited** (`anchor_check` 17/17,
  `stroke_toggle_check` 63/63, `overlay_render_check` 40/40, `marketing_render_check` 45/45).
  🔴 **88-04's AC-2 landed exactly:** all 6 single-bin windows equal an independent
  re-implementation of `_split_velocity` at **max |Δ| = 0.00e+0**, and the `finishS` clamp is
  proven load-bearing — 5 m of post-touch drift manufactures a fifth bin without it (4 → 5).
  ⚠ **88-03's three auto tasks were NOT executed this session** — found already applied in the
  tree (as this file warned), reviewed rather than re-applied, every AC re-verified from scratch.
  Same reconciliation-of-found-work posture as 84-02.
  ⚠ **`scratch/stroke_toggle_check.mjs` WAS edited** despite both wave-1 plans listing it as
  must-pass-UNEDITED. Mechanically forced (`PhaseReportCard` now imports `@/lib/unitConvert`, so the
  harness cannot transpile it without a MAP entry), additive, still 63/63 — but a real breach.
  ✅ **POST-PHASE FOLLOW-UP 2026-09-01 (3 user-reported items, one commit, gated by
  `scratch/trend_toggle_check.mjs` 39/39):**
  (1) the caveat wording, above;
  (2) 🔴 **the metric/imperial toggle never reached the video** — `TraceOverlay` hardcoded `"m/s"` /
  `"m/s²"` and printed raw SI in its rAF readout, and `/video` never hydrated `swimnetics.unit` at
  all. The unit pref is now `web/lib/useUnitPref.js`, read by BOTH routes; the factor is applied to
  the READOUT ONLY (the band self-scales to its own min/max, so the drawn path is byte-identical in
  either unit — pinned);
  (3) the velocity trend is now a **switch** (`swimnetics.showTrend`, default on) with the window
  behind it, because the slider's 0.00 s "off" discarded the window the coach had chosen.
  ⚠ **Still unverified on screen** — the portal is Supabase-auth-gated, so these are render- and
  source-gated only, exactly like 88-05's. Same ~2-minute check closes both.
  ⚠ **New pattern worth reusing:** clamp a stale index-selection by DERIVING it during render, never
  by resetting it in an effect — the effect form trips `react-hooks/set-state-in-effect`, which is
  what forced 87-02 to ship a new error.
  🔴 **88-01's D3 floor was measured wrong and was corrected at its own checkpoint:**
  `_MIN_REMAINDER_M` shipped at **0.5 m, not the planned 1.0 m**. D3 assumed a 25-yard lap leaves
  ~1.9 m past the 20 m mark; it does not — `finish_s` clamps before the wall touch and `dist_m`
  already runs short of it, so across the 56 stored sessions that reach 20 m the tail is
  **median 0.872 m** (p25 0.486, p75 1.839, min 0.019, max 5.206). At 1.0 m the new metric filled
  **23 of 56 (41%)**, under the plan's own two-thirds stop condition; at 0.5 m it fills
  **42 of 56 (75%)**. AC-5 existed to catch exactly this and did. **Second time after 83-03 that a
  reasoned-about threshold was wrong on real data — measure before shipping is now twice-validated.**
  ⚠ **Live DB now:** `splits_25m` on **0** of 99 rows, `splits_remainder` present on 99 and non-null
  on 42. So `RETIRED_KEYS` matches nothing today — it was correct (it covered the window between
  the web deploy and the backfill) but is defensive-only from here.
  ⚠ **The new row's span varies ~10×** (0.5–5.2 m, median 0.87 m). On a typical 25-yard lap it
  reads closer to *closing speed over ~0.9 m* than to a 5 m split, directly beneath four true 5 m
  splits. Structurally not comparable to the rows above it; watch this in 88-04's verification.
  ⚠ **88-02's blocking human-verify was NOT separately confirmed.** Its mechanical half is covered
  (`scratch/anchor_check.mjs` 17/17), but the on-screen read against a real "Tony" session and a
  real divergent session was not performed before UNIFY was directed to run. The change moves
  numbers a coach has already read — ~0.4–0.5 s on 37 sessions, up to 12.39 s on 27 of them.
  ⚠ **88-03 (wave 2) is PARTIALLY APPLIED in the working tree and entangled with wave 1.**
  `web/lib/unitConvert.js`, `scratch/unit_check.mjs` (63/63 passing), the unit-conversion edits
  inside `PhaseReportCard.js`, and one MAP line added to `scratch/stroke_toggle_check.mjs` — which
  BOTH wave 1 plans listed as must-pass-UNEDITED. It is correct and green, so it was left rather
  than discarded, but wave 1 cannot be committed without carrying wave 2 along, and 88-03's APPLY
  must start by reviewing what is already there rather than assuming a clean tree.
  ~~⚠ **Nothing is committed yet**~~ → **RESOLVED: all three waves committed together in
  `e2c5814` (2026-08-31 19:01 -0700), 33 files.**
  ⚠ **Dead code deliberately left (88-02 D4):** `metrics.time_to_distance` (zero callers),
  `compute_session_metrics`'s unused `head_waist_m` kwarg, `api.py:183/228`'s form field,
  `tests/test_metrics.py:156`. iOS keeps its own head-waist-adjusted TimeToX, so the two surfaces
  now disagree by ~0.4–0.5 s on Tony's sessions until a mobile phase carries it across.

  *Planning record below, as written 2026-08-31 (pre-apply — read the summaries above for what
  actually shipped):*
  CONTEXT (`/paul:discuss`, 3 rounds) covered two user-reported defects; planning split the work
  into **4 plans in 2 waves**, sized so the two unreported defects CONTEXT found do not ride
  inside the two reported ones:
  - **88-01 — splits registry** (wave 1, `depends_on: []`) — `splits_25m` retired (fills on **2 of
    99** sessions, structurally: a waist tether tops out at ~21.9 m on a 25 yd lap) and replaced by
    a NEW `splits_remainder` measuring 20 m → `finish_s`. Backend + display tables + tests.
    ✅ **No new backfill tool** — verified `tools/backfill_phases.py` already performs exactly this
    derivation and is what 75-02 / 75-06 / 83-02 used; it gains two fill counters so the new
    `_MIN_REMAINDER_M = 1.0` floor is **measured on the real library at a `--dry-run` checkpoint
    before `--apply`** (83-03's lesson). ✅ **No `SCHEMA_VERSION` bump** — verified the version
    tracks the `phases` object's *shape* (2 = boundaries, 3 = provisional, 4 = kick_bands) and
    75-06 added 23 metrics without touching it; a test pins `== 4`.
    ⚠ Retiring a key is not enough on the client: `PhaseReportCard` renders whatever keys the
    STORED object carries and falls back to `m.label`, so deleting the `DISPLAY` entry alone would
    keep the dead row rendering — worse, without the `emptyNote` that explained the blank. Hence an
    explicit `RETIRED_KEYS` skip.
  - **88-02 — one anchor** (wave 1, `depends_on: []`, no file overlap with 88-01) — CONTEXT F5,
    **not reported and larger than what was**: the page holds THREE origins for "0 m". Probed live,
    `dive_start_s` and `baseline_end_s` are both present 99/99 with a 0.003 s median gap, but **27
    of 99 differ by >0.1 s**, tail **12.39 / 12.27 / 11.62 / 8.16 s**. `TimeToX` moves onto raw
    `dive_start_s` and drops `head_waist_m`; the existing 61-02 D7 caveat line becomes the page's
    single statement of its anchor and that anchor's provenance, read from
    `boundaries.sources.dive_start_s` (not `recomputed_from_annotation`, which says the *session*
    was recomputed, not that *this boundary* came from a mark).
    ✅ **Re-verified CONTEXT F4 directly: the backend head-waist path is already dead code** —
    `metrics.time_to_distance` has zero callers and `compute_session_metrics` takes the kwarg and
    never uses it. So **web-only: no recompute, no backfill, no stored change.** Python is
    deliberately left alone (repo convention: mention dead code, do not delete it).
    ⚠ Numbers a coach has already read WILL move — ~0.4–0.5 s from head-waist on the 37 "Tony"
    sessions, up to 12 s from the anchor swap on the 27 divergent ones. Hence a blocking
    human-verify rather than an autonomous apply. ⚠ iOS keeps its own head-waist-adjusted TimeToX,
    so the two surfaces will disagree until a mobile phase carries it across.
  - **88-03 — unit conversion** (wave 2, `depends_on: ["88-01"]` — file serialization on
    `PhaseReportCard.js`, not an import) — reported defect 2. **Re-counted directly off `DISPLAY`
    and CONTEXT F6 confirmed exactly: 17 `m/s` + 3 `m` + 2 `m/s²` + 1 `m/s³` = 23 of 47 metrics
    never convert; the other 24 are correctly invariant.** New pure `web/lib/unitConvert.js` keyed
    on the **unit string**, not a 23-key metric list. 🔴 **The load-bearing decision: the verdict is
    computed on SI and NEVER on converted values** — conversion is a display transform applied at
    the last moment, so "toggling units cannot change a flag" is structural rather than hoped for
    (R6: a yards value against a metre band reads ~9% high and invents flags). ⚠ CONTEXT named one
    display site; reading the file found **three** — the `RangeStrip` props, `metricExplain`, and
    the `activeFlags` model that `PhaseTimeline.js:156-158` renders as "value unit vs median unit".
    The harness's central assertion is that flag count, every status word, and every strip's band /
    median / dot position are identical between the two renders.
  - **88-04 — the picker** (wave 2, `depends_on: ["88-02"]` — page.js serialization + it consumes
    88-02's hoisted anchor) — reported defect 1. Chips for each **complete** 5 m / 5 yd segment;
    clicking selects a contiguous run (`{lo, hi}`, so contiguity is structural) and reads back
    average velocity + elapsed time. ✅ **Open question 6 answered by NOT competing**: the picker
    gets its own `spanS` `ReferenceArea` on both charts and never touches `onMarkerChange` — two
    cards writing one marker is a live conflict, and a *window* is not a *point*. ✅ **Open
    question 5 deleted rather than answered**: only complete bins are offered (the `TimeToX`
    hide-unreachable-presets precedent), so there is no partial "20–25" label to lie — that
    stretch is exactly what 88-01's new row reports instead. ⚠ The picker's chord arithmetic must
    reproduce a grid split **exactly** (asserted to 1e-12), which is why its search is clamped at
    `finish_s` the same way `_split_velocity` clamps it — otherwise post-touch drift into the wall
    fills a bin and the two silently diverge.
  - **88-05 — velocity trend overlay** (wave 3, `depends_on: ["88-04"]` — genuine file conflict:
    both edit `VelocityChart.js` **and** `page.js`) — ⚠ **NOT one of the two reported defects and
    outside CONTEXT.md's charter**; appended 2026-08-31 at the user's explicit direction after a
    prototype (`scratch/chantee_traces.html`) built against Chantee's three 2026-08-20 butterfly
    swims. A **grey dotted centred rolling mean drawn over the raw trace**, window set by a
    persisted 0.00–3.00 s slider (default 1.00 s, `swimnetics.smoothWindowS` on the existing
    `useTracePrefs` localStorage pattern). Stores nothing, adds no registry metric — it is a second
    rendering of `velocity_profile`, which is why it is a plan and not a phase. Why it earns a
    place: a ~90 Hz butterfly trace is a sawtooth of real surge-and-glide peaks that must not be
    smoothed away, but at raw resolution the lap-scale story is invisible — on the prototype the
    three Chantee swims are three near-identical sawtooth walls raw, and at ~1 s separate cleanly
    (the dive's advantage is spent inside the first quarter of the lap; 80% and 100% are
    indistinguishable from 3 m to 18 m). 🔴 **The one way this plan can be quietly wrong is
    `VelocityChart`'s `MAX_POINTS = 2000` decimation** — the mean MUST be computed at the native
    rate BEFORE the stride, or a 1.00 s label covers `1.00 × step` seconds. ⚠ **It would not
    reproduce on the obvious test sessions**: a 20 s swim at 89.99 Hz is 1799 points, so
    `step === 1` and nothing decimates; the trap only bites past ~22 s. A synthetic 4000-point
    assertion in `scratch/rolling_mean_check.mjs` pins both orderings apart. ✅ **Cycle-denominated
    windows were considered and REJECTED** (D1): "one cycle" is the more meaningful unit, but it
    would read `mean_isi_s`, which on butterfly comes from the segmenter that found **5 cycles
    where there should be ~12** — a cycle slider would silently inherit a 2× error. Seconds are
    dumb and correct. ✅ Report card only (D5): `VelocityChart`'s other consumer,
    `/app/sessions/[id]/video`, passes no prop and must render byte-identically; this also respects
    rather than bends the `AccelerationChart.js:21-24` boundary, which forbids a second **x**-
    windowing slider — a smoothing window is a y-domain control and cannot desync the x axes.
    ⚠ Acceleration gets no trend (D6): smoothing a signed derivative raises a real question (mean of
    a zero-crossing signal, or mean of its magnitude?) this plan does not answer.
  ⚠ **Waves are 88-01 + 88-02 in parallel, then 88-03 + 88-04, then 88-05.** ⚠ 88-01 is the only
  plan with a backend diff and the only one needing a library backfill. ⚠ R7 stands and is
  accepted: the same metric will convert on this page and not on compare / group / parent-report
  pages. ⚠ **88-05 widens the phase past its own CONTEXT**, which covers only the two reported
  defects — recorded here rather than left for a future reader to notice.
- **Phase 87-01** (Stroke-level segmentation + arm asymmetry — BACKEND) — **✅ CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-31; backfill applied by the user. Loop:
  `PLAN ✓ → APPLY ✓ → UNIFY ✓`.** Summary:
  [87-01-SUMMARY.md](phases/87-stroke-level-asymmetry/87-01-SUMMARY.md). Suite 520 → **563 green**
  (43 new tests, no pre-existing test modified). Backfill wrote **47 of 101** sessions —
  24 from coach marks, 20 from the auto segmenter, 3 with a window but no strokes, 11 left
  asymmetry None for <3 strokes per side; 54 skipped as non-free/back, 0 failed.
  ⚠ One plan deviation: `segment_strokes` gates on stroke_type (freestyle/backstroke), NOT on
  the segmenter's `.k == 1` as the plan's Task 1 step 3 said — fly/breast carry `k=2` (a
  detector property), so a `.k` gate would have contradicted the plan's own AC-1. New phase; **2 plans** (87-01 backend,
  87-02 frontend toggle + visuals). Goal: make the individual arm stroke a stored unit
  (`metrics_json.strokes` beside `cycles`) for freestyle/backstroke, plus seven session keys —
  3 signed asymmetry percentages (tempo / distance / peak velocity) and 4 per-side CVs.
  ✅ **Four read-only probes were run against the live library during planning** — the 83-03
  lesson ("measure a threshold's fire rate before shipping it") applied preemptively:
  (1) **The signal is real and it separates.** Across the 23 usable annotated freestyle sessions,
  odd/even contrast is **6.1% median in tempo** (0.4–29.4%) and **9.4% in distance per stroke**
  (0.1–33.2%), clearing the within-side noise floor (t>2) on 7/23 and 9/23. Some sessions sit at
  0.4%, others at 30% — unlike 83-03's MAD gate, which fired on everything.
  🔴 (2) **On AUTO sessions the same number is uncorrelated with truth: Pearson r = −0.06**,
  median error **10.2 percentage points** against a 6.1% signal, agreeing on only **2 of the 7**
  most-lopsided sessions. Cause is **parity, not precision** — un-paired wavelet boundaries land at
  **1.10× the coach's mark count** (0.50–1.33) and match 88% of marks within 0.35 s, but one extra
  or missing boundary **flips the A/B assignment of every later stroke**. ⚠ **The user saw this
  measurement and chose to ship the number on auto sessions anyway, marked only by the existing
  `auto` chip (D2).** Recorded as their call, not an oversight.
  ⚠ (3) **Backstroke has 0 annotated sessions.** Census: freestyle 45 (24 annotated), **backstroke
  2 total / 0 annotated**, butterfly 29 (16), breaststroke 20 (4), udk 5 (1). It shares freestyle's
  code path exactly so it costs nothing to include, but nothing about it can be verified —
  confirms owed item 10.
  ⚠ (4) **The user's premise when choosing storage was wrong and was corrected before planning:
  stroke segmentation is NOT stored today.** `metrics_json.cycles` is already the *paired* product;
  coach marks live in `session_annotations.stroke_marks_s`, a table the report card never queries;
  and the auto boundaries are built and **discarded inside `_pair_boundaries`**
  ([metrics.py:388-397](../metrics.py)). So the backend must start *emitting* strokes, not
  re-reduce something on hand.
  **Decisions:** D1 `metrics_json.strokes` **top-level beside `cycles`**, not inside `phases` —
  83-02's D5 reversal does not transfer, because `strokes` comes from the same call and the same
  two write sites as `cycles`, so it cannot go stale against it; no `SCHEMA_VERSION` bump (that
  version lives inside `phases`). D3 sides are **A / B, never left/right** — a 1-D axial encoder
  cannot observe which arm is which. D4 the Swimming **usual-range strips do NOT switch** with the
  toggle (their baselines are five *cycle-level* swims deep), so `phase_metrics.py` is untouched
  and the two `needs_cycles` specs are out of scope. D5 backfill is a **new additive-only tool**
  writing exactly two keys.
  ⚠ **Blast radius is small by measurement:** only 2 of the 47 registry specs read `ctx.cycles`.
  ⚠ **The riskiest edit is a refactor, not a feature** — the per-cycle derived-metrics loop is
  extracted verbatim into `_derive_item_metrics` so cycles and strokes cannot drift; AC-2 (cycles
  byte-identical, 505 suite green, no pre-existing test modified) is what proves it.
  ⚠ The `_anchors_from_marks` **leading-pad drop is load-bearing and must be SHARED, not
  reimplemented**: 59-05 measured boundary F1 **0.000 with the pad vs 0.458 without**, and it went
  unnoticed because `stroke_rate_spm` is blind to it.
  ⚠ Carries a **blocking human-action checkpoint** — the user runs the backfill, as with every
  prior one. Probes at `scratch/_asym_probe.py`, `scratch/_asym_auto_probe.py`,
  `scratch/_asym_auto_vs_truth.py` (read-only, uncommitted).
  See [87-01-PLAN.md](phases/87-stroke-level-asymmetry/87-01-PLAN.md).
- **Phase 87-02** (Stroke-level view — FRONTEND toggle + visuals) — **✅ CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-31, human-verify approved. Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`.**
  Summary: [87-02-SUMMARY.md](phases/87-stroke-level-asymmetry/87-02-SUMMARY.md).
  All 9 acceptance criteria pass. All 4 auto tasks + the blocking human-verify done. New `scratch/stroke_toggle_check.mjs` **63/63**; the two
  regression gates pass **unedited** (`overlay_render_check.mjs` 40/40,
  `marketing_render_check.mjs` 45/45); `npm run build` clean; `pytest` 563 green (no Python in the
  diff). Diff is exactly the nine planned files.
  ⚠ **Two APPLY deviations, both small and both recorded here rather than in a comment:**
  (1) **AC-7's hover/pin clearing lives in the toggle's click handler, not an effect on `mode`** as
  Task 3 step 7 said — the repo's eslint config errors on `react-hooks/set-state-in-effect`, and the
  click is the only way `mode` ever changes under a coach's hand. (2) **`npx eslint .` is NOT clean
  at baseline** (25 problems / 22 errors before this plan, incl. `useTracePrefs.js` and
  `PhaseReportCard`'s own pre-existing `dismissed` hydrate), so the plan's "eslint clean" could not
  be met literally; the diff adds **exactly one** new error — the granularity `localStorage` hydrate,
  identical in kind to the `dismissed` one directly above it and **required by D2** (a lazy
  initializer would desync hydration).
  ⚠ **Harness limitation, worked around and stated in the file:** `renderToStaticMarkup` never runs
  effects, so stroke mode is unreachable from outside — the check rewrites the ONE
  `useState("cycle")` initializer in its own transpiled copy (production source untouched; it
  asserts the exact initializer exists so it fails loudly if that line moves). The hydrate itself is
  therefore covered only by the human-verify's reload step, which passed.
  `depends_on: ["87-01"]`, wave 2, 4 auto tasks + a blocking
  human-verify. Puts a **cycles / strokes** toggle in the Swimming section header; in stroke mode
  the inset bands, the count badge, the `CycleOverlay` pack and all four `CycleCharts` panels
  rebuild from `metrics_json.strokes`, and a new **Arm balance** block renders 87-01's three signed
  asymmetry percentages plus the four per-side CVs.
  ✅ **Two live code findings during planning, both load-bearing:**
  (1) **The A/B sides are already drawn — for free.** `PhaseVelocity.js:236-241` has painted bands
  `s.n % 2 ? var(--color-cycle-a) : var(--color-cycle-b)` since 83-01, and 87-01 D3 makes side A the
  **even array positions**, so `stroke_num` 0 → `n = 1` → odd → `cycle-a`. **Side A is blue, side B
  is purple, with zero change to the band renderer** — the tokens were named `cycle-a` / `cycle-b`
  before there were sides. ⚠ It is an accidental alignment of two independent conventions, holding
  only while `stroke_num` is dense and 0-based, so it is pinned by AC-4 and a render assertion, not
  a comment.
  (2) **The whole `PhaseReportCard` renders headlessly** — proven, not assumed:
  `scratch/_prc_render_probe.mjs` produces 55 KB of markup with the badge, the overlay and all four
  chart captions, so the toggle can be machine-checked end to end rather than component by
  component. ⚠ **Measured limitation:** recharts emits an EMPTY wrapper under
  `renderToStaticMarkup`, so the dashed mean line and the dots are **not** assertable — the panel
  captions carry the same numbers and are what the harness keys on.
  **Decisions (all mine, at the user's direction — "all decisions are up to your recommendations"):**
  D2 toggle state is **local to `PhaseReportCard`**, not lifted into `useTracePrefs` (that hook is
  shared with the `/video` route, where granularity has no meaning); persisted **globally** at
  `swimnetics.swimGranularity`, hydrated in an effect never a lazy initializer. D3 effective mode is
  `strokes?.length ? pref : "cycle"` and the fallback is **never persisted**. D4 stroke-level means
  are **re-derived client-side** (new pure `web/lib/strokeStats.js`, population std to match numpy) —
  87-01 stores no stroke means and a cycle is two strokes, so the stored `mean_isi_s` would draw the
  dashed line clean off the top of the dots. D6 **one deliberate exception to `PhaseVelocity.js`'s
  standing DO-NOT-CHANGE** — an optional `itemLabel` used ONLY in its aria-label, because that string
  would otherwise read "one band per cycle" to exactly the users who cannot see the colours;
  geometry untouched, diff bounded by AC-8. D7 in stroke mode the overlay pack is **tinted by side**
  and its single median is replaced by **two per-side medians** (normalized only, `MIN_ITEMS = 5`
  gated per side) — 83-05's all-grey rule was about not *asserting* which stroke is odd, and naming
  which arm produced a trace asserts nothing. D8 **no warning banner on auto sessions** — 87-01 D2
  is the user's explicit call; what is added is the *definition* of A and B, without which the
  readout is unreadable. D9 the readout states **magnitude and direction, never a verdict** — no
  "even" threshold (83-03's cut classifier is the precedent), no good/bad colour, and it is
  **unit-invariant** (percentages and ratios do not convert). D10 one 8-word line in stroke mode:
  *"Usual-range comparisons below stay per cycle"* — 87-01 D4 keeps the strips cycle-level, and a
  coach who just switched the section would otherwise misread the band.
  ✅ **Gate cleared** — 87-01 applied and backfilled (47 of 101 sessions carry `strokes`), so the
  human-verify ran on real data. On the other 54 the toggle is simply absent, the designed
  degradation.
  ⚠ Regression gates that must pass **unedited**: `scratch/overlay_render_check.mjs` (40 checks) and
  `scratch/marketing_render_check.mjs`.
  See [87-02-PLAN.md](phases/87-stroke-level-asymmetry/87-02-PLAN.md).
- **Phase 75-06** (Swim + Whole metric batch) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28**
  (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). ✅ **Committed `20c0432`** (whole-tree commit, 2026-08-29).
  **The race-phase registry is now complete** (37 → **47 specs**; `streamline_drag` is the only
  `planned` one left). 23 Swim + Whole metrics implemented and rendered as the report card's last two
  sections; the two `<ComingSoon>` stubs are gone. Suite **485 green** (+38); web build clean.
  **User rule that shaped it:** *prioritize existing annotations first, then fall back to auto
  segmentation* — boundary-level precedence already existed (`resolve_boundaries`: manual > detected >
  auto), so the new work was **per-cycle**: `PhaseContext.cycles` + `segmentation_reliable`, plus a
  `needs_cycles` spec flag that becomes an emitted **`provisional`** (schema_version 2 → **3**), which
  the UI renders with valence forced neutral. **Verified on the live library: `dead_spot_timing` =
  43 TRUSTED (coach cycles) / 44 provisional**, exactly matching the 43 annotated sessions.
  ✅ **Backfill applied (user-run, twice):** 99 sessions, all schema_version 3, **0 stale keys** — this
  also closed the never-run **75-04 Start backfill** (Start now 95–97/99). Decisions: D7 vector metrics
  → **N scalar specs**, never list-valued (`phaseBaseline` looks up by key across history, so list
  indices would misalign); D11 **`breathing_dip` DELETED**, not deferred — a 1-D axial encoder cannot
  observe breaths. ⚠ **AC-7 human-verify NOT run** (portal is Supabase-auth-gated) — owed, same posture
  as 81-01; includes judging the ~23-row panel length.
  See [75-06-SUMMARY.md](phases/75-report-card-phase-model/75-06-SUMMARY.md) ·
  [75-06-CONTEXT.md](phases/75-report-card-phase-model/75-06-CONTEXT.md) ·
  [75-06-PLAN.md](phases/75-report-card-phase-model/75-06-PLAN.md).
  **New owed items from this plan → 13–16 below.**
- **Phase 83-01** (Per-cycle trace coloring — cycles half) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28,
  AC-7 approved.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. **Frontend only, zero Python — suite still 485 green.** The
  Swimming-section inset now draws one alternating blue/purple band per `metrics_json.cycles` entry over
  a neutral-grey base, a boundary tick at every edge, an amber halo on the duration-outlier cycle, a
  `N cycles · annotated|auto` badge, a per-band hover readout, and bidirectional cross-highlight with the
  four `CycleCharts` panels. Annotations-first needed **no precedence code** — `PUT /annotations` already
  replaces `metrics_json.cycles` with the coach's, so reading the stored array *is* the precedence.
  New pure `web/lib/cycleBands.js` is shape-agnostic and **83-02 reuses it for kicks unmodified**
  (verified: a `{kick_num, interval_s}` fixture bands + flags correctly via `durationKey`).
  **Unlike 75-06 and 81-01, the human-verify WAS run** — user approved on the live portal 2026-08-28.
  ⚠ **Two silent-failure bugs found during verification, both fixed — both matter to 83-02:**
  (1) `PhaseVelocity`'s new `bands` prop was **shadowed** by the hero variant's existing phase-tint local
  inside `geom`, so the prop was never read (now aliased `cycleBands`); (2) **Tailwind v4 tree-shakes
  `@theme` tokens that no utility class references** — the three new colours are read only as raw `var()`
  in an SVG `stroke`, so they compiled away and every band rendered `stroke: none`, i.e. invisible. The
  block is now **`@theme static`** ([globals.css](../web/app/globals.css)); any future token consumed only
  via `var()` needs the same. Neither bug is visible to `next build` or `eslint` — only to a render check.
  Deviations from PLAN: `web/app/app/sessions/[id]/page.js` joined `files_modified` (plan-sanctioned —
  `segmentationReliable` threaded explicitly, never inferred from an annotation row); `@theme static`
  rather than a plain block; the hover readout **replaces** the inset caption instead of adding a line
  beneath it, so the four charts don't shift down mid-gesture; badge pluralises (`1 cycle`).
  ✅ **Committed `20c0432`** with the rest of the tree, 2026-08-29.
  ⚠ **Phase 83 itself stays 🚧 — NOT transitioned, NO phase commit.** 83-01 is 1 of 2 plans; the
  plan-count heuristic would have called the phase done, but 83-02 is the kicks half.
  See [83-01-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-01-SUMMARY.md) ·
  [83/CONTEXT.md](phases/83-per-cycle-trace-coloring/CONTEXT.md) ·
  [83-01-PLAN.md](phases/83-per-cycle-trace-coloring/83-01-PLAN.md).
- **Phase 83-02** (Per-cycle trace coloring — kicks half) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-28,
  apply outcome approved.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. **Backend + frontend.** New pure
  `metrics.segment_kick_bands` splits trough-to-trough at the plain argmin between consecutive detected
  peaks (**no new tuning constant**, D4); `compute_phases` emits **`phases.kick_bands`** beside
  `boundaries`; `SCHEMA_VERSION` **3 → 4**; the Underwater inset renders it through 83-01's `buildBands`
  and `PhaseVelocity` with **zero configuration** (`duration_s` was chosen so the default `durationKey`
  applies). Badge reads `N kicks · auto` — kicks are **auto-only**, no reliability half, until 81-02 ships
  a coach kick-marking path. Breaststroke gated off (`pulldown · not kicks`). Suite **485 → 497 green**
  (+12); web build clean, 19 pages.
  ⚠ **CONTEXT D5 REVERSED at the decision checkpoint** — bands live **inside `phases`**, not at top-level
  `metrics_json.kicks`. D5's premise ("`phases` is a pure metrics-registry payload") is factually
  incomplete: `phases` already carries `schema_version`, `go_signal_s`, `boundaries`. A top-level key
  needs writes at **all three** `PhaseContext` sites — the exact bug 75-06 shipped — and `PUT /annotations`
  would carry it forward **stale** against a window the coach just replaced. Inside `phases` it re-derives
  with the boundaries and cannot go stale. Cost: kicks read from `phases.kick_bands` while cycles come from
  `metrics.cycles`; **81-02 may want a coach-writable kick array outside the derived object.**
  ✅ **Backfill applied (user-run), verified against STORED state** — 99/99 sessions at `schema_version` 4,
  **0** missing the key, **63 of 81 non-breaststroke carry bands** (84/99 have a resolvable underwater
  window — matches item 14). `tools/backfill_phases.py` gained a `with_kick_bands` counter because AC-7
  requires the run to make a zero *visible*; it had none.
  ⚠ **Two deviations worth carrying forward:** (1) **AC-5 failed by the letter** — `web/lib/cycleBands.js`
  is genuinely untouched, but **`PhaseVelocity.js` was modified**: the user directed removal of the
  **peak dot** from the hero chart and all four insets mid-verify (its `argmax` helper deleted as an
  orphan). (2) Tasks 2–3 were found **already applied** in the tree from a cut-off prior session, and
  Task 4 was **half**-applied — the `kickBands`/`hoverKick` memos existed but nothing in the render read
  them, so no band was ever drawn; only the render wiring was written this session.
  ⚠ **`web/lib/cycleBands.js:9` now carries a false comment** (says 83-02 passes `metrics_json.kicks`
  through it) — left alone under the DO-NOT-CHANGE boundary; **83-03 fixes it**, since it edits that file.
  ⚠ **Phase 83 still 🚧 — NOT transitioned, NO phase commit.** Plan/summary counts are now equal (2/2),
  which is exactly the heuristic that would wrongly call the phase done — same trap as 83-01. **83-03 is
  next.**
  See [83-02-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-02-SUMMARY.md) ·
  [83-02-PLAN.md](phases/83-per-cycle-trace-coloring/83-02-PLAN.md).
- **Phase 83-03** (Breakout band + shape-anomaly investigation) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-29.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. AC-8 approved on the
  SECOND attempt — the first verify was **RETRACTED** by the user. Frontend only; no Python, no
  schema change.
  ⚠ **The plan's central feature was CUT on evidence.** A read-only probe over the stored library
  (90 usable sessions / 618 cycles, `scratch/shape_viability_probe.py` + `shape_sweep_probe.py`)
  measured the shipped MAD gate: it fired on **75% of sessions at k=3.0** (15.5% of all bands) and
  still **39% at an absurd k=8.0**. There is no k where a clean swim is quiet and a ragged one is
  not. Cause = **sample size**: a lap holds a **median of 7 cycles**, so the MAD is small and
  unstable — a within-lap outlier test on n=7 is not an abnormality test. Dropping cycle 1 helps
  marginally (67% → 55% at k=4.0) and costs 10 sessions their eligibility. This also contradicts the
  product's own SPC doctrine (baseline from HISTORY, not from within the sample).
  **→ `web/lib/cycleShape.js` is kept but PARKED and unwired**, with the numbers in its header; the
  red anomaly colour, halo, `anomalies` plumbing and flag hover copy are all removed. **New owed
  item 17.**
  ✅ **What DID ship — the breakout gold, now on measured ground.** The user's annotation convention
  (recorded 2026-08-29, see below) makes the Swimming inset's grey lead-in **structural**:
  `stroke_start_s` is the coach's **streamline-break** mark while `stroke_marks_s[0]` is the first
  hand **returning overhead**, so the breakout pull itself lies between them and belongs to no cycle
  (freestyle `k=2`, cycles = `marks[0::2]`). Measured: on all **43 annotated** sessions that gap is
  **positive**, median **1.04 s** (0.08–1.63) — never negative. `buildBands({breakoutFirst})` inserts a
  **SYNTHETIC `n: 0` band** spanning `i0` → the lowest-n cycle's start, painted `--color-cycle-breakout`
  gold. ⚠ **Corrected mid-verify:** the first re-cut *merged* the pull into cycle 1 (gold = streamline
  break → end of cycle 1) and the user rejected it — **"gold is two strokes instead of one"**. The
  breakout is ONE stroke; cycle 1 keeps its own colour. **No gap ⇒ no gold band** (never invent a
  zero-width stroke). `n: 0` is outside CycleCharts' keyspace, so hovering it highlights nothing there —
  correct, it has no row. Badge counts non-breakout bands so "5 cycles" stays 5.
  ⚠ **Gold is gated on `segmentationReliable`** — on **AUTO** sessions cycle 1 is NOT the breakout:
  **28 of 47** start BEFORE `stroke_start_s`, worst **−12.9 s**. Auto sessions keep the grey.
  Verified: `scratch/shape_checks.mjs` **15/15**, `next build` clean 19 pages, eslint clean apart
  from the pre-existing `set-state-in-effect`, **no Python touched**, suite **497**. Production CSS
  greps confirm `--color-cycle-breakout` survives tree-shaking and `--color-cycle-anomaly` is gone.
  ⚠ The retracted verify's other two complaints — the pink halo and the ambiguous shape-vs-duration
  hover copy — were **dissolved** by cutting the flag, not fixed.
  ⚠ **Process lesson recorded:** `k = 3.0` was justified in the PLAN by Gaussian reasoning that needs
  dozens of samples; **the cycle count was never checked before the gate was written.** Measure a
  threshold's fire rate on real data before shipping it.
  ⚠ **`annotations.py:25` is WRONG about the breakout** — it says "THE FIRST STROKE CYCLE CONTAINS THE
  BREAKOUT", but under the coach's marking convention the pull sits AHEAD of cycle 1. Left alone
  (Python boundary); owed a future correction, and anything reasoning from that docstring is suspect.
  ⚠ Also fixed `cycleBands.js:9`'s false `metrics_json.kicks` comment (owed from 83-02).
  ⚠ **Phase 83 stays 🚧 — NOT transitioned, NO phase commit.** PLAN/SUMMARY counts are now 3/3, the
  exact heuristic that would wrongly call the phase done — the same trap flagged at 83-01 and 83-02.
  **83-04 has no PLAN yet.**
  See [83-03-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-03-SUMMARY.md) ·
  [83-03-PLAN.md](phases/83-per-cycle-trace-coloring/83-03-PLAN.md) — ⚠ the PLAN's AC-1/2/4/5/6
  describe the CUT feature and no longer match the tree; read the SUMMARY, not the PLAN.
- **Phase 83-04** (inset window framing) — **📋 dropped out of 83-03 when option B was chosen; not yet
  planned.** Two usability findings from 83-02's verify, both confirmed against the code:
  (1) **a single-dolphin-kick underwater stretches ~0.5 s across the full chart width** — there is no
  minimum span; (2) **every inset hard-clips to its own phase**
  ([PhaseVelocity.js:67](../web/components/portal/phases/PhaseVelocity.js)) — the grey the user read as
  out-of-phase context is actually the band **base trace** showing un-segmented time *inside* the
  window, so context padding is genuinely **new behaviour, not a consistency fix**. Scope: pad
  Start/Underwater/Swimming past their boundaries with the extension drawn grey, plus a minimum span in
  **seconds** (never samples — the rate is per-session, ~89.5 Hz typical). Bands must keep clamping to
  the **phase** window, not the padded one. Whole-race inset is already the full trace ⇒ no-op there.
- **Phase 83-05** (cycle/kick OVERLAY panel) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-29,
  AC-8 approved after two live corrections.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. **Frontend only;
  no Python, no schema, no backfill — suite still 497.** The replacement for 83-03's cut classifier:
  instead of *asserting* which stroke is odd, every cycle (or downkick) is drawn on ONE shared axis
  beneath its phase inset, in neutral grey, with a left number gutter that hover-previews and
  click-pins. New pure `web/lib/cycleTraces.js` + `CycleOverlay.js`; `PhaseReportCard` lifts the pin
  state and resolves `active = hovered ?? pinned` ONCE (D9). Seconds axis by default, normalized
  `% of cycle` toggle adding a pointwise-median line gated at 5 traces. **`PhaseVelocity.js`,
  `cycleBands.js` and `CycleCharts.js` are byte-identical — absent from `git diff`**, unlike 83-02
  which broke its own zero-diff AC.
  ⚠ **Two live corrections at the verify, both now shipped:**
  (1) **the gutter wraps at 10 rows** — a 15-dolphin-kick underwater made a single column stand
  taller than the chart beside it (`grid-auto-flow: column`; 9→1 col, 15→2×8, 25→3×9). The
  `0 · breakout` row moved OUTSIDE the grid so its long label cannot set every column's width.
  (2) **AC-3 was OVERRIDDEN by the user** — the breakout row is no longer inert; hovering it now
  highlights the gold `n: 0` band in the inset. It stays dim (no trace of it in the pack) and nothing
  in CycleCharts reacts, since 0 is outside that keyspace. ⚠ Numbered `dropout`/`too-short` rows are
  **still inert** — the same argument applies to them but was not generalised.
  ⚠ **Two boundary widenings, both forced by contradictions inside the PLAN itself:**
  (a) `cycleShape.js` gained **two `export` keywords** (Task 1 mandates importing `resample` +
  `median`; the boundary said "header comment only"). `analyzeShapes` + `K` untouched and, by grep,
  **still imported nowhere**. (b) **`niceMax` is DUPLICATED** from the DO-NOT-CHANGE `PhaseVelocity.js`
  — guarded by a render check asserting the two function bodies are **byte-identical**, so the copy
  cannot drift.
  ✅ **New reusable harness: `scratch/overlay_render_check.mjs`** (40 checks) — transpiles the
  component with the bundled `typescript` package, server-renders it with `react-dom/server`, and
  asserts on markup. **Needs no auth, so it works despite the Supabase-gated portal.** It targets
  83-01's two silent-failure classes directly: no path may render `stroke: none`, every trace must
  carry real `d="M…"` geometry. Plus `scratch/overlay_checks.mjs` (32 data checks). Build clean
  19 pages; eslint clean apart from the pre-existing `set-state-in-effect`.
  ⚠ **Ships the item-18 kick-tiling artifact knowingly** (D8) — but see the item-18 correction below:
  at 15 kicks the two tiling bands are 2 of 15, not "2 of 5", and the live pack read as tight.
  ⚠ **D5's auto-session posture survived the verify unchanged** — no caution copy was requested, so
  auto sessions carry only the existing `auto` badge to signal that spread may be segmentation.
  ⚠ **STATE item 17 stays open** — `resample` + the median are wired, the MAD gate is not.
  ⚠ **Peak-alignment surfaced as a better axis mode than align-center and was DECLINED** → new item 19.
  ✅ **Committed + pushed `45a858b`** (2026-08-29).
  ⚠ **Phase 83 stays 🚧 — NOT transitioned, NO phase commit.** PLAN/SUMMARY counts are now **4/4**, the
  exact heuristic that has falsely signalled "done" at 83-01, 83-02 AND 83-03. **83-04 (inset window
  framing) is scoped in STATE but still has no PLAN.**
  See [83-05-SUMMARY.md](phases/83-per-cycle-trace-coloring/83-05-SUMMARY.md) ·
  [83-05-PLAN.md](phases/83-per-cycle-trace-coloring/83-05-PLAN.md) ·
  [83-05-CONTEXT.md](phases/83-per-cycle-trace-coloring/83-05-CONTEXT.md).
- **Phase 85** (Marketing home page refresh) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-29,
  AC-8 approved on the live local site; PHASE TRANSITIONED, 1/1 plans.** Frontend only, no Python touched, suite still 497.
  The marketing site had not moved since `17086cb` (2026-06-22); it now leads with the race-phase
  report card. Shipped: the Swimnetics mark enters the web surface for the first time (nav lockup
  inverted over the hero, footer lockup, `app/icon.png` + `app/apple-icon.png` replacing
  `favicon.ico`); hero copy per D21 with the floating chart card gone; new `PhaseStory` (one whole-lap
  real trace, three phase windows tinted in place, grey post-finish tail) + reusable `PhaseRadar`
  (axis count read from the data); `UsualRange`, `CyclePack`, `VideoSync`, `Device`; `Features.js`
  and `SampleChart.js` retired. Geometry is **baked at author time** into `web/lib/marketingGeom.js`
  by `scratch/_export_marketing_geom.py`, so a public page makes **no Supabase call** — whole-lap
  polyline decimated 1762 → 882 points (10 KB), cycles left whole.
  ⚠ **Copy rule now enforced by a check, not by eye:** `scratch/marketing_render_check.mjs`
  (**45 checks green**) counts BOTH dash forms (the FAQ was 10 `&mdash;` entities to 2 literals, so a
  character-only grep read it as clean), flags the banned strings, and — the 83-05 pattern — headlessly
  server-renders the components to assert no `stroke: none`, no empty `points`, and the usual-range
  coherence rule (a coloured strip sits OUTSIDE its band, a grey one inside).
  ⚠ **Four deviations:** (1) the copy check is scoped to the **marketing surface**, not all of
  `web/components` — the portal carries ~285 comment dashes, says "GoPro" legitimately in its upload
  help, and holds `changed (unclear)` inside the `AlertSummary.js` that **D27 forbids this plan to
  touch**; a permanently red check is a check nobody reads. (2) **AC-7's "still 19 pages" is now 20**,
  measured: `favicon.ico` is worth one static page and the two icon file conventions are worth two.
  (3) The three phase cards align their radars with a per-card **CSS grid row** (`1fr` on the blurb)
  rather than the mockup's reserved `min-height`, which held at 1280 but broke at 880 where the
  underwater blurb wraps to a fifth line and pushed its radar 21 px low; still never a flex column,
  and the radar SVG measures 227/159/119 px at 1280/880/700 so nothing collapsed. (4) `Brand` uses
  `next/image` because `@next/next/no-img-element` IS enabled in this config.
  ⚠ `web/src/data/sample-session.json` is now an **orphan** (SampleChart was its only reader), left in
  place. `/privacy` and `/blog` keep their em dashes by D5, including in their `<title>`.
  ✅ **Committed + pushed `a75c373` (2026-08-29) — Vercel auto-deploys `main`, so this is the public
  site now.** Excluded from the commit: `scratch/_home_session.json` (the raw probe dump carries the
  source athlete), `scratch/_mockup_template.html` (`*.html` is gitignored), and the round-1 leftovers.
  ✅ **Phase 85 IS complete and WAS transitioned — unlike 83, the plan-count heuristic is trustworthy
  here.** The trap that misfired at 83-01/02/03/05 is a phase with known remaining scope; Phase 85 has
  none: all four CONTEXT goals shipped in one plan, and D27's portal chip rename was scoped as a
  SEPARATE phase from the start, not as 85-02.
  See [85-01-SUMMARY.md](phases/85-website-home-refresh/85-01-SUMMARY.md) ·
  [85-01-PLAN.md](phases/85-website-home-refresh/85-01-PLAN.md) ·
  [85/CONTEXT.md](phases/85-website-home-refresh/CONTEXT.md).
- **Phase 84-01** (Mobile user feedback — NATIVE CONFIG half: items 1 icon + 4 orientation) —
  **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-30 — all three code tasks done and statically verified;
  the build-gated human-verify was DEFERRED by decision, not failed.** Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`
  (SUMMARY written 2026-08-30 01:38; STATE's loop marker corrected 2026-08-30 during the 84-02 UNIFY).
  Phase 84 is
  **7 items → 5 plans**; this is the first, chosen because it is the only lane touching **no JS at
  all**, so it cannot collide with the mobile repo's uncommitted Phase 74 work or with item 7's
  GO marker. Target repo is **`Desktop/swimnetics-mobile`** (separate, user-owned git).
  ⚠ **G1 — CONTEXT open question 2 is answered NO: there is no OTA channel.** No `expo-updates`
  dependency, no `updates` key in `app.json`, no channels in `eas.json` — only build/submit
  profiles. **All seven Phase-84 items ship in an EAS build.** The native/JS split survives as a
  *verification-cost* driver only, not a sequencing one.
  ⚠ **Three CONTEXT claims about this phase were checked against code and are WRONG:**
  (1) **`sharp` is not in the mobile repo** — it is in `myswimcoach/web/node_modules` (0.34.5);
  the plan uses Python **Pillow** in the backend repo instead, where the source art already lives.
  (2) **`assets/icon/Swimnetics_icon.svg` is not a vector** — it is an SVG wrapper around a
  base64 **1004×960 RGBA PNG** (56.4% transparent, `#7200FF` + a white interior highlight), with
  **zero ink margin on all four sides** and the `<image>` anchored top-left in a 1028×1028 viewBox.
  So 1024 is a 2% upscale, alpha **must** be flattened (iOS rejects alpha; Phase 85's web icons are
  deliberately transparent and that precedent does **not** transfer), and padding has to be invented
  rather than inherited — rendering the SVG would put the mark off-centre up-and-left.
  (3) **`AthleteDetailScreen` has no access to `rating_colors`** — its pillars come from
  `route.params.athlete`, not a fetch, so **item 5 needs navigation-param plumbing, not just a
  lookup swap**. (Item 5 is a **four**-surface problem; `AthletesScreen.js:84` is the fourth and
  already correct.)
  ✅ CONTEXT's item-4 and item-6 root causes both **verified exactly**: `Info.plist:44-49` lists two
  landscape values with **no** JS orientation code anywhere and **no** `~ipad` variant key (a clean
  2-line deletion); and neither `PanResponder` in `VelocityChart.js` sets
  `onPanResponderTerminationRequest`. `expo-file-system` is **fine** — absent from `package.json` but
  a transitive dep of `expo` (~56.0.8) and present in the lockfile, so H6 stands as written.
  Plan = rasterizer → **decision checkpoint** (background + fill fraction, judged at 120 px) →
  install → plist edit → **human-verify gated on an EAS build** (⚠ `npx expo-doctor` first, standing
  SDK-56 rule). No commit in either repo; no build spent by the plan itself — batching it with the
  later Phase-84 plans is a decision left to the checkpoint.
  ✅ **APPLY 2026-08-30 — decision checkpoint answered `approve`: background `#FFFFFF`, fill 80%**
  (the rasterizer's shipped defaults; `BG`/`FILL` at `scratch/make_app_icons.py:31` are the one-line
  knobs if it is ever revisited). Tasks 1–3 all landed: rasterizer byte-deterministic across three
  runs; three opaque `RGB` PNGs installed at 1024/180/120 with no tRNS; `Contents.json`
  byte-identical to HEAD; `Info.plist` diff is `0 insertions, 2 deletions` and `plistlib` reads
  `UISupportedInterfaceOrientations == ['UIInterfaceOrientationPortrait']` with no `~ipad` variant.
  Zero `.js` in the plan's diff; the four Phase-74 entries (`CLAUDE.md`, `CycleCharts.js`,
  `BleContext.js`, `RecordScreen.js`) are present and untouched. Nothing staged, nothing committed.
  ⚠ **AC-3 deviation — the AC is unachievable, not the code.** Its aspect clause demands ≤1 part in
  1000; 1024 hits 0.0137% but 180/120 land at 0.2252%. Brute-forcing every integer `(w,h)` inside
  the AC's own ±1% fill window gives a floor of **0.164% @ 180** and **0.180% @ 120** — integer pixel
  dimensions cannot do better at that scale (144 px wide at 1.0458:1 wants h=137.69, and neither 137
  nor 138 is within 0.1%). Centring and fill clauses pass. Loosen the AC at UNIFY; do not chase it.
  ⚠ **Windows/OneDrive staleness bit TWICE during APPLY, and the second time matters.** (a) `ls` +
  `git status` of `AppIcon.appiconset/` returned the May-21 placeholders minutes after the install had
  written the new bytes. (b) The tree's opening `git status` listed **4** modified files; the closing
  one listed **9**. **Verify mobile-repo state by hashing content, and re-read `git status` at the END
  of a session as well as the start — one opening read is not trustworthy on that tree.**
  🔴 **What (b) surfaced: 84-02's code is ALREADY SUBSTANTIALLY APPLIED in both repos, with no
  SUMMARY.** Mobile: `RecordScreen.js` 120/8 (`goPressPhoneMsRef`/`goSignalSRef`, the `go_signal_s`
  upload param, the silent GO button), `startSequencePrefs.js` 17/4 (key bumped to
  `startSequenceEnabled.v2`, default flipped OFF, fail-closed), `RecordingConfigScreen.js` 24/12
  (`SHOW_START_SEQUENCE_TOGGLE = false`). Backend: `api.py` 20/5 (optional `go_signal_s` form field,
  invalid values dropped-and-logged not 422'd, the stale clock-sync docstring corrected) and
  `tests/test_api.py` 70/4 (four new GO tests). **Its suite was NOT run and its checkpoints were NOT
  answered — do not treat 84-02 as done, and do not re-apply it blind.**
  ⚠ **A commit meant to be "84-01 only" must be path-scoped to `ios/mobile/**`** — a bare
  `git commit -a` in either repo would sweep in 84-02.
  ✅ **Checkpoint 2 answered `defer`: the EAS build was NOT spent.** G1 says all seven Phase-84 items
  need a build anyway, so the working tree holds these two while 84-02/84-03 land and one build carries
  everything. **Owed: `npx expo-doctor` then `eas build --platform ios --profile preview`, then device
  verify** — the icon and the orientation lock are both native and invisible in Metro, a dev-client
  refresh, or any simulator on the old binary. Rotation must be tested with the device's own rotation
  lock OFF or the test proves nothing.
  See [84-01-SUMMARY.md](phases/84-mobile-user-feedback/84-01-SUMMARY.md) ·
  [84-01-PLAN.md](phases/84-mobile-user-feedback/84-01-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-02** (Mobile user feedback — item 7, the coach GO marker + race-start sequence off) —
  **✅ LOOP CLOSED 2026-08-30 — but the APPLY session was NEVER RECORDED and this UNIFY is a
  reconciliation of found work, not a write-up of a session anyone logged.** Loop:
  `PLAN ✓ → APPLY ✓(unrecorded) → UNIFY ✓`. **Cross-repo**
  (`api.py` + `tests/test_api.py` here; `RecordScreen.js` + `startSequencePrefs.js` in
  `swimnetics-mobile`). `depends_on: []` — shares 84-01's EAS build but has **zero file overlap**
  with it. **This plan closes STATE item 15** and fills `reaction_time`, which is **0/99 today**.
  ⚠ **G6 — the "phone↔encoder clock sync is deferred" claim is STALE and has now misled two
  documents** (`api.py:1160` and 75-04's CONTEXT D13). `RecordScreen.js:445-447` has computed it
  since Phase 47: `sessionStartPhoneMs = phoneNowMs − elapsedUs/1000` off the 8-byte META reply, so
  `go_signal_s = (goPressPhoneMs − sessionStartPhoneMs)/1000`. **Only the button was ever missing.**
  Both docstrings are corrected by Task 1.
  ⚠ **G7/G8/G9 — three plumbing facts that shape the mobile half.** META lands at *retrieval*, i.e.
  after the swim, so the press must stash raw `Date.now()` and convert later, at the one site where
  `startPhoneMs` is already in scope. `uploadAndProcess` is a `useCallback` that cannot read state,
  so the value rides **two refs** on the established `videoUriRef` mirror pattern (`:105`) — not new
  state and not a dep-array change. Ordering already works unchanged: META → DUMP → saveCSV →
  uploadAndProcess.
  ⚠ **G10 — disabling the horn is NOT just a default flip.** `startSequencePrefs.js` reads
  `v === null ? true : v === '1'`, so flipping the default misses **everyone who explicitly toggled
  it on** — precisely the users who chose it. The plan **bumps the SecureStore key to
  `startSequenceEnabled.v2`** so every stored value is discarded once. `useStartSequence.js`,
  `StartSequenceOverlay.js` and the audio assets stay **byte-identical** (D9 is "for now").
  ⚠ **Deliberate asymmetry with `PUT /go-signal`:** that endpoint 422s on a bad value because the
  request is only about the GO time. On `/process` the request carries the **swim**, so a negative,
  non-finite or unparseable marker is **dropped and logged, and the session still processes 200**.
  An AC and a test both pin this, because it is the thing a future reader is most likely to
  "fix" into a 422.
  ⚠ **Deploy ordering is a real constraint, not bookkeeping:** backend must be live on Railway
  BEFORE the app that sends the field, or every session recorded in the gap loses its marker with
  no error anywhere — the exact silent-loss shape item 2 exists to hunt.
  ⚠ **G11 — `tests/test_api.py:117` already asserts `phases["go_signal_s"] is None  # no GO button
  yet`.** It keeps passing (the field is optional) but its comment goes false and the populated
  path has no coverage; Task 1 amends it and adds four tests.
  ⚠ **B4 — no backfill is possible.** No stored session carries a GO time and none can be
  reconstructed, so `reaction_time` fills only for sessions recorded *after* this ships — a
  permanent discontinuity that `phaseBaseline.js` (last-5-same-stroke) will see as a metric that
  simply begins one day.
  ⚠ **The metric embeds the coach's own thumb latency** — a within-coach *relative* measure, never
  an absolute block reaction. The plan requires the human-verify to **judge the number, not just its
  presence**; if it reads as noise the fix is a hardware starter signal, not more code.
  ✅ **UNIFY 2026-08-30 — reconciled and verified. 7 AC pass · 1 partial · 1 failed-by-decision ·
  3 clauses deferred to the device.** All three code tasks are applied in both trees.
  **`pytest tests/` = 505 passed** (8 of them this plan's `TestGoSignalOnProcess`; baseline 497 —
  ⚠ STATE's older "485 green" figure is the 75-06 count and is stale). The mobile repo has no test
  runner, so all three changed JS files were parsed with `web/node_modules/typescript` (83-05
  `createRequire` pattern) — clean, with a mutant self-test proving the check non-vacuous.
  ✅ **Decision checkpoint was answered `hide` — in code, not at a recorded checkpoint:**
  `SHOW_START_SEQUENCE_TOGGLE = false` in `RecordingConfigScreen.js`, hook/overlay/audio all intact.
  That answer knowingly **breaks AC-9's four-file blast radius (it is 5) and supersedes AC-7's
  "the toggle can still turn it back on" clause** — both costs the `hide` option itself listed.
  A second, unplanned fix rode along: the `startSequence` seed state was flipped `true → false`
  because the async pref read made the toggle flash on, and a fast Continue could ship
  `startSequence: true` to `RecordScreen` despite a stored OFF.
  ⚠ **One AC-3 exception is deliberate and pinned by a test:** `go_signal_s="banana"` **does** 422 —
  it fails at FastAPI's `Optional[float]` coercion above any handler code. Every value that reaches
  the handler (negative, `nan`, `±inf`) is dropped-and-logged with a 200.
  🔴 **OWED and currently unmet — deploy ordering.** `api.py` is uncommitted and unpushed. If the app
  ships before Railway has the field, every session recorded in the gap loses its marker with **no
  error anywhere** — the exact silent-loss shape item 2 exists to hunt. **Backend push must precede
  the EAS build.** ⚠ A commit scoped to this plan must be **path-scoped**: `RecordScreen.js` also
  carries Phase 74's uncommitted retrieval work (stall 30 s → 8 s, `MAX_RETRIEVAL_ATTEMPTS`, the
  `sendDumpHandshake` retry, post-save `CLEAR`), which is **not** 84-02's.
  ⏸ **Human-verify DEFERRED by standing phase decision** — no Phase-84 item gets a human check until
  the phase is finished and one EAS build carries everything. When it happens, **judge the number,
  not just its presence.**
  See [84-02-SUMMARY.md](phases/84-mobile-user-feedback/84-02-SUMMARY.md) ·
  [84-02-PLAN.md](phases/84-mobile-user-feedback/84-02-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-03** (Mobile user feedback — item 5, indicator formalization) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-31; device verify DEFERRED to the EAS-build batch.** Loop:
  `PLAN ✓ → APPLY ✓ → UNIFY ✓`. ✅ **Committed + pushed 2026-08-31.** Harness re-run at close:
  `node scratch/indicator_check.mjs` = **30/30, exit 0**. → [84-03-SUMMARY.md](phases/84-mobile-user-feedback/84-03-SUMMARY.md).
  ⚠ **STATE's earlier 🔴 NOT APPLIED marker (written 02:31 during the phase-84 UNIFY sweep) was
  overtaken by events, not wrong at the time** — file mtimes put the apply at **02:29–02:35**, i.e.
  straddling that sweep. The `/paul:apply` run at 03:xx therefore **verified rather than re-applied**;
  it wrote no mobile code. Present and green: `src/lib/indicators.js` + `src/components/ui/BandDot.js`
  (new), all four surfaces rewired, and `scratch/indicator_check.mjs` (229 lines) — **`node
  scratch/indicator_check.mjs` = 30/30, exit 0**, including the two static checks the plan expected red
  until Task 3. AC-1…AC-6 satisfied; `BAND_COLOR`/`BAND_FALLBACK`/`VERDICT`/`verdictColor` gone from
  `src/` outside the module; mobile diff = exactly 4 modified + 2 new under `src/`; **no `.py` and no
  `web/` change** (the dirty `api.py`/`tests/test_api.py` are 84-02's `go_signal_s` field — read, not
  assumed). **Owed: AC-7 only** — the Metro trace of one athlete across roster → detail → dashboard →
  report card, plus the judgement call on G27's title-case + "No data" copy change. **User deferred it
  2026-08-30 so the whole phase is verified in one sitting**, alongside 84-01/84-02's build-gated
  checks; this lane needs no EAS build of its own.
  Mobile-repo only, `depends_on: []`,
  **zero file overlap with 84-01 or 84-02** — it is the one Phase-84 lane that touches none of
  `RecordScreen.js` / `BleContext.js` / `CycleCharts.js`, so it is provably clear of the uncommitted
  Phase 74 work. Third of the phase's five plans.
  ⚠ **G20 — the headline finding, and it demotes CONTEXT's diagnosis: `provisional` is STRUCTURALLY
  UNREACHABLE.** `ratings.py:206` is `provisional = (thr_table is None) or (thr is None)`, and both
  halves are dead — `thr_table` falls back to the breaststroke table so it is never None (`:251`), and
  all four pillar primary keys (`mean_vel_ms`, `mean_dps_m`, `cv_arm_peak_vel`, `fatigue_index_pct`)
  **have threshold rows** (`:110,111,133,134`). `tests/test_ratings.py:142` confirms it from the other
  side: the test named `test_provisional_driven_by_missing_threshold` could not construct a provisional
  pillar and asserts `is False` instead. So **CONTEXT's item-5 consequence — "a provisional pillar is
  invisible on the dashboard, colored as if trustworthy on the athlete page, and warned about on the
  report card" — describes a state that cannot occur.** `PillarCards`' provisional banner has never
  rendered; `DashboardScreen`'s provisional exclusion has never excluded anything; `summarize_team`'s
  provisional skip never skips. There is **no device test for provisional**, so the plan proves that
  path on synthetic input in the harness and says so out loud.
  ⚠ **G21 — the band hexes are byte-identical between `ratings.py:33` and `tokens.js:40-42`**
  (`#2d9e5f` / `#d4860a` / `#c0392b`), so `AthleteDetailScreen`'s hardcoded `BAND_COLOR` renders
  **exactly the same pixels** as the three surfaces that read the payload. Real defect, but *latent
  drift*, not a live bug — that screen will not look different afterwards.
  ✅ **G22 — what the user actually saw is four indicator FORMS for one band:** a dot (roster), a
  lowercase word (athlete page), a 0-100 number (dashboard), a title-case word over a meter (report
  card). Fully observable, and the thing D3 settles. That is the item's real justification.
  ✅ **G23 — `unknown` IS reachable** (primary metric missing/NaN, e.g. `cv_arm_peak_vel` on a
  low-cycle session) and is where the four surfaces genuinely diverge — muted dot / `—` / "Not enough
  data" / silently dropped from the average — every one of them reached through an *accidental*
  undefined lookup rather than a defined answer. It is the band the plan can be device-verified against.
  ⚠ **G24 — `rating_colors` has only 3 keys**, so a server-first lookup is not total; the client must
  own the `unknown` color. Do NOT add `unknown` to `RATING_COLORS`.
  ⚠ Also corrected: STATE's own note that `AthletesScreen.js:84` is "already correct" — true for the
  **color source only**; it is provisional-blind and gives `unknown` an accidental answer like the
  other three. And **G28: the mobile repo has no test runner and no lint script** (`package.json`
  scripts = start/android/ios/web), so "verify" cannot mean `npm test` — the plan brings a headless
  harness (`scratch/indicator_check.mjs`, 83-05 / 85-01 precedent) that imports the RN-free module by
  rewriting one specifier into a `data:` module (G29). One user-visible change ships: the athlete
  page's labels go title case and `—` becomes "No data" (G27).
  Plan = shared `src/lib/indicators.js` + `BandDot.js` + harness → **decision checkpoint** (what the
  dashboard needs-attention card leads with; specimen-judged, no build) → rewire roster + athlete page
  (incl. the `ratingColors` nav param 84-01's G-fact 3 called for) → rewire report card + dashboard →
  **human-verify over Metro** (this lane needs no EAS build, unlike 84-01/84-02). No commit in either
  repo; no backend or `web/` change.
  ✅ **DECISION (user-ratified 2026-08-30, APPLY Task 1.5) — Option A:** the dashboard
  needs-attention card **leads with four band dots** (the same `BandDot` the roster draws, in
  `ratings.PILLARS` order) and demotes the 0-100 roll-up to a small secondary `caption`. Provisional
  treatment = **hollow ring in the band color**. This is now the app's single convention: the next
  surface that renders a band follows it. ⚠ The code had already been written to Option A before it
  was put to the user; the ratification is what makes it a decision rather than an accident.
  See [84-03-PLAN.md](phases/84-mobile-user-feedback/84-03-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-04** (Mobile user feedback — item 6, the brush-bar gesture) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY) 2026-08-31; device verify DEFERRED to the EAS-build batch (user call).** Loop:
  `PLAN ✓ → APPLY ✓ → UNIFY ✓`. ✅ **Committed + pushed 2026-08-31.** Harness re-run at close:
  `node scratch/gesture_check.mjs` = **7/7, exit 0**. → [84-04-SUMMARY.md](phases/84-mobile-user-feedback/84-04-SUMMARY.md). The earlier 🔴 NOT APPLIED marker (phase-84 UNIFY sweep) is now
  cleared: `onPanResponderTerminationRequest: () => false` is present on **both**
  `PanResponder.create` configs in `VelocityChart.js` (now `:75` body / `:104` brush, each with its
  own reason comment — the two reasons differ and both are written down), and
  `scratch/gesture_check.mjs` (new, 190 lines) is **7/7 PASS, exit 0**, including the mutant
  self-test that strips the property from an in-memory copy and asserts the checks FAIL. Mobile diff
  = **+11 lines, one file, nothing else**; `ReportCardScreen.js` / `VideoOverlayScreen.js` /
  `chartWindow.js` byte-identical to HEAD; `RecordScreen.js` untouched by this plan. TS transpile of
  the JSX: **0 syntactic diagnostics**, so Metro will not choke. AC-1/2/3 satisfied.
  **Owed: AC-4 + AC-5 only** — the on-device drag, and the judgement on G36's two dead zones.
  ⚠ **The plan said this lane needs no EAS build (Metro is enough); the user chose to defer it to
  the build batch anyway**, so it now verifies in one sitting with 84-01/84-02/84-03. → owed item 23.
  ⚠ **Deviation, recorded:** AC-2 names the pre-existing mobile baseline as four Phase-74 files
  (`CLAUDE.md`, `CycleCharts.js`, `BleContext.js`, `RecordScreen.js`). That list was stale by apply
  time — 84-01/84-02/84-03 had landed, so the real baseline is **14 modified + 2 untracked**. The
  substance of AC-2 holds (exactly one file added to that set); the literal enumeration does not.
  Mobile-repo only, `depends_on: []`,
  **one component file**. Fourth of the phase's five plans; chosen next because it is the only
  remaining item that touches neither `RecordScreen.js` (84-02's file, and the mobile repo's
  uncommitted Phase 74 work) nor `CameraView` — items 2 and 3 both do.
  ⚠ **G33 — the bug is WORSE on a surface CONTEXT never examined.** `RecordScreen.js:994` renders the
  post-recording results chart with `interactive brush dark` and **no `onInteractionStart` /
  `onInteractionEnd`**, inside the `ScrollView` at `:919` — so that brush has **no scroll lock at
  all**, where the report card at least sets `scrollEnabled=false`. This is the argument for fixing
  it in `VelocityChart.js` rather than per consumer: one edit repairs a surface nobody reported AND
  keeps the plan out of 84-02's file.
  ✅ **G31 — CONTEXT's root cause verified in RN 0.85.3's own source.** `PanResponder.js:520-522` is
  `onPanResponderTerminationRequest == null ? true : …`, and neither config in `VelocityChart.js`
  (`:75-94` body, `:99-118` brush) sets it. ✅ **G32 — `onShouldBlockNativeResponder` needs no change**
  (`:468-470` already defaults `true` in this RN, not the historical Android-only `false`), so the fix
  is one property per responder, not two.
  ✅ **G34 — CONTEXT open question 6 answered NO, twice over.** `VideoOverlayScreen.js:219` passes
  neither `interactive` nor `brush`, and both responders are gated on exactly those props at render
  (`:343` / `:311`), so **neither responder is attached there**; independently its container is a
  `SafeAreaView` with no `ScrollView` in the file.
  ⚠ **G35 — "make the bar taller" is the obvious wrong fix.** A responder does not lose a gesture by
  leaving the view's bounds; once granted, moves keep arriving and the ONLY loss path is termination.
  `hitSlop` or a bigger `BRUSH_H` would improve the grab, not the drag.
  ⚠ **G36 — the fix's cost is the exact mirror of the bug:** two thin dead zones where a drag that
  *starts* on the 30 px strip (or horizontally on the chart body) can no longer scroll the page until
  the finger lifts. Deliberately **no decision checkpoint** — that is a device-feel judgment nobody
  can make from a chair, so the plan implements D6 as written and puts the tradeoff in the
  human-verify with the directional fallback (`Math.abs(g.dy) > Math.abs(g.dx) * 2`) pre-specified,
  making a "no" a one-line swap instead of a re-plan.
  ⚠ **G38 — the guard is source-level and the plan says so.** `VelocityChart.js` imports
  `react-native` + `react-native-svg`, so 84-03's one-specifier-rewrite trick does not apply; the new
  `scratch/gesture_check.mjs` parses the AST (via `web/node_modules/typescript`, 83-05's
  `createRequire` pattern) and proves it is not vacuous by re-running its checks over a stripped
  copy. It asserts CONFIGURATION, never gesture behaviour — only the device verify proves the drag.
  ✅ **G37 — `VelocityChart.js` is the only file in the app with a `PanResponder`**, so there is no
  second instance of this bug and no shared gesture helper to extract.
  Plan = fix both responders → AST guard with mutant self-test → **human-verify over Metro** (no EAS
  build, no encoder needed). No commit in either repo. ✅ First two tasks done and verified; the
  third (human-verify) is the deferred one.
  **Remaining Phase-84 scope after this: items 2 (upload diagnostic) + 3 (camera options)** — grouped
  into the fifth plan because both touch `RecordScreen.js` and the same `CameraView` JSX, both need
  encoder-plus-camera to verify, and CONTEXT's **D5** already routes `videoQuality` into item 2's
  lane. ⚠ Two facts read while scoping that bear on that plan: expo-camera 56.0.8's iOS default is
  **1080p**, not 4K (`CameraViewModule.swift:184`), so H1's "4K blows past 50 MB" is overstated and
  the TS docstring calling the 16:9 values Android-only is wrong (`CameraRecordingOptions.swift:17-30`
  maps all of them); and **there is no pre-recording camera preview** — `onCameraReady` writes START
  and calls `recordAsync` immediately, so a lens/`facing` control has nowhere safe to live (changing
  `facing` mid-record hits `updateDevice()` and reconfigures the session). Zoom is safe mid-record but
  maps **exponentially** (`videoZoomFactor = maxZoomFactor ^ zoom`, `CameraSessionManager.swift:218`)
  against a device-dependent max that JS cannot read, so "2×/4×" preset labels would be a lie.
  See [84-04-PLAN.md](phases/84-mobile-user-feedback/84-04-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 84-05** (Mobile user feedback — items 2 upload-failure + 3 camera options) — **✅ APPLY
  code-complete 2026-08-30, **LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-31**; device verify DEFERRED to
  the phase-wide EAS build (user decision), so the human-verify checkpoint is OWED, not approved.**
  Loop: `PLAN ✓ → APPLY ✓ → UNIFY ✓`. ✅ **Committed + pushed 2026-08-31.** Harness re-run at close:
  `node scratch/upload_retry_check.mjs` = **36/36**; `pytest tests/` = **505 passed**.
  → [84-05-SUMMARY.md](phases/84-mobile-user-feedback/84-05-SUMMARY.md).
  Decision at the Task 2 checkpoint: **option-a, `videoQuality="720p"`** (one prop, no codec risk;
  option-b's `videoBitrate` route needs a `getAvailableVideoCodecsAsync()` guard whose failure mode
  is *rejecting `recordAsync`*, on the critical path seconds before START, to buy 67 s vs 72 s).
  Verified here: probe reproduces G1/G2/G4, `upload_retry_check.mjs` **36/36**, `pytest` **505**
  (no drift), Metro bundles (1296 modules), nothing staged or committed in either repo.
  ⚠ **G12 was already stale when written:** 84-03 and 84-04 are **applied**, not merely planned —
  `indicators.js` / `BandDot.js` exist and `VelocityChart.js` carries the gesture edit. Neither was
  touched here; only the AC-8 pre-existing baseline is larger than G12 listed. **The fifth and last
  Phase-84 plan**; cross-repo (two new files in `tools/` + `scratch/` here, five files in
  `swimnetics-mobile`). `depends_on: []`, but ⚠ it **shares `RecordScreen.js` and
  `RecordingConfigScreen.js` with 84-02** (loop closed, device verify still owed, **uncommitted**) —
  there is no path-scoping that separates the two. The backend drift baseline is 84-02's
  **505 passed**, not the older 485/497 figures still quoted above. 84-03 and 84-04 stay independent:
  neither of their files is touched here.
  🔴 **Item 2's cause is now MEASURED, not hypothesised** — a read-only probe was run against the
  live project during planning. **H1 (the 50 MB cap) is CONFIRMED and quantified:** 37 stored phone
  clips give a **median encode rate of 1.38 MB/s** (range 0.90–2.20) at iOS's default 1080p, so the
  cap is reached at **≈36 s of video** — ≈23 s on the fastest device — while `recordAsync` allows
  300 s and auto-stop allows 300 s. The bucket's own distribution shows the ceiling: 97 phone clips,
  **max 48.3 MB, nothing ≥50 MB**, 5 at ≥45 MB. **9 sessions carry the lost-clip fingerprint**
  (`video_origin_s` set, `video_path` NULL); recovering each clip's length from
  `deviceDuration − origin` prices **6 of them at 54–110 MB** and two more inside the device spread,
  so **6–8 of 9 are H1**. One (25 MB, 2026-08-20) is unexplained and stays the residual.
  ✅ **CONTEXT open question 1 answered NO — H2 is REFUTED and Phase 82 is NOT a prerequisite.** A
  1-byte probe object uploaded to the `videos` bucket **succeeded (200)** with the bucket at 2.63 GB
  against the 1 GB free-tier figure, then was deleted. Storage is not rejecting writes.
  ⚠ **The 413 is invisible three times over** (G5): the queue wraps it as `Server error (413)` and
  then **retries it twice over ~13 s** on an outcome that cannot change; `UploadToast.js:66` renders
  a constant `"Video upload failed"` and never shows `job.lastError`; and the chip is dismissible and
  dies with the app. That stack is exactly the reported *"sometimes it just isn't there."*
  ✅ **CONTEXT open question 4 answered "not here"** — queue persistence (H3) stays out of scope:
  G4 attributes 6–8 of 9 losses to H1, and two facts soften H3 materially — `saveVideoToLibrary`
  copies **every** recording to Photos (the footage is never lost, only the attachment), and the web
  annotate page can attach a clip to an existing session (Phase 67). **H4 is not a bug** (the early
  returns happen precisely when there is no `session_id` to attach to); **H6 is not implicated**.
  ⚠ **New fragility found while checking H6:** `expo-file-system` is **absent from `package.json`
  and not hoisted** — it exists only at `node_modules/expo/node_modules/expo-file-system`, yet two
  modules import `expo-file-system/legacy` and it resolves today. The plan reuses the existing
  specifier and adds no new one.
  ✅ **expo-camera's iOS internals decide where each control lives** (read at `~56.0.8`): `zoom` →
  `device.lockForConfiguration()` only, so it is **safe mid-record**; `facing` → session input swap
  and `videoQuality` → `session.beginConfiguration()`, so **both must be set before recording**. And
  there is **no pre-recording preview** (`onCameraReady` writes START and calls `recordAsync` at
  once), so zoom in the live overlay is the only place a coach can actually frame a shot.
  ⚠ **No zoom preset may claim a magnification factor**: `videoZoomFactor = maxZoomFactor ** zoom`
  against a device- and format-dependent maximum JS cannot read, so `zoom=0.5` is 4× on one phone and
  11× on another. Only `zoom=0` is truthfully 1×.
  ⚠ **Two CONTEXT/docs claims corrected:** iOS defaults to **1080p, not 4K** (`CameraViewModule.swift:184`),
  so H1's "4K blows past 50 MB" was overstated — 1080p alone does it; and the TS docstring calling the
  16:9 `videoQuality` values Android-only is **wrong** (`CameraRecordingOptions.swift:17-30` maps all
  of them). `videoBitrate` is honoured **only** when `recordAsync` is also given an available codec —
  which is what makes the resolution-preserving option two coupled changes, not one prop.
  Plan = commit the probe as `tools/probe_video_uploads.py` → **decision checkpoint** on the quality
  lever (720p recommended / 1080p at 6 Mbps / both) → pure `uploadRetry.js` + queue pre-flight size
  refusal + no-retry-on-4xx + a chip that names the reason, guarded by a new headless
  `scratch/upload_retry_check.mjs` that cross-checks the constant against `api.py` → camera controls
  → **build-gated human-verify** (⚠ `expo-doctor` first; needs encoder **plus** camera). No commit in
  either repo; `api.py`'s `MAX_VIDEO_BYTES` deliberately untouched (Phase 82 / Pro territory, and it
  is a RAM guard as well as a quota one).
  See [84-05-PLAN.md](phases/84-mobile-user-feedback/84-05-PLAN.md) ·
  [84/CONTEXT.md](phases/84-mobile-user-feedback/CONTEXT.md).
- **Phase 82** (Storage Quota Cleanup) — **🚧 PLAN created 2026-08-27, awaiting APPLY.** Supabase free
  tier is over quota (2.53 GB vs 1 GB cap — ⚠ but the *"new uploads may already be blocked"* worry is
  **REFUTED**: 84-05 planning uploaded and deleted a probe object successfully on 2026-08-30 at
  2.63 GB, so this is a cost/hygiene phase, not an outage). Two leak sources found
  in `DELETE /sessions/{id}`: `video_path` never removed from the `videos` bucket, and `session_videos`
  externals `ON DELETE CASCADE` at the DB level without their storage objects being removed — together
  716 MB (28%) of the 2.5 GB video bucket is orphaned. Confirmed exhaustive against `live_schema.json`
  (only these two tables reference `session_id`). Plan: fix both leak sources in `api.py` + tests, ship
  a dry-run-by-default `tools/cleanup_orphan_videos.py`, then a human-action checkpoint to actually run
  `--apply` and reclaim the space. User separately decided to close the remaining ~800 MB gap by
  upgrading to Supabase Pro ($25/mo, out-of-band billing action) rather than compressing/deleting
  ground-truth video. See [82-CONTEXT.md](phases/82-storage-quota-cleanup/CONTEXT.md) ·
  [82-01-PLAN.md](phases/82-storage-quota-cleanup/82-01-PLAN.md).
- **Arc:** Race-phase report-card model (Phases 75–77) — segment the 4 phase boundaries, then compute
  per-phase metrics, then build the UI.
- **Phase 77** (fly breakout) — closed + committed (`d6e00c8`, `0ff29e7`).
- **Phase 76** (free/back breakout) — closed + committed (`046b8d1`).
- **Phase 75-03** (7 underwater kick metrics + `detect_underwater_kicks`) — **✅ CLOSED 2026-08-21.**
  Eyeball (AC-4) approved on ground-truth windows; hypothesis 1 (peaks+prominence) accepted. The
  review surfaced + FIXED a bigger defect: stored `stroke_start`/`finish` were stale and the backfill
  couldn't refresh them → new `metrics.detect_swim_boundaries` + `detected` branch in
  `resolve_boundaries` (auto `stroke_start` err **3.56 s → 0.40 s**). Suite 426 green.
  See [75-03-SUMMARY.md](phases/75-report-card-phase-model/75-03-SUMMARY.md).
- **Phase 75-04** (Start-phase metrics batch — Step 2) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY), 2026-08-21.**
  [75-04-SUMMARY.md](phases/75-report-card-phase-model/75-04-SUMMARY.md). 10 of 11 Start metrics implemented in
  one pass (D12 gate **waived**); `streamline_drag` stays planned. New `PUT /sessions/{id}/go-signal` stores the
  GO time in `metrics_json` (jsonb, no migration) → `reaction_time` derives (motion onset − GO; anchor is the
  jump, not `dive_start`). `recompute_phases` refactored into shared `_rebuild_phases` (reads the stored GO time).
  Suite **443 green** (+17). Committed `defed65`. ⚠ **owed: user-run `python tools/backfill_phases.py --apply`**
  to populate the 9 non-reaction Start metrics across the stored library. Key finding: registry tiers are stale —
  75-02/79 turned the "high" glide/break-into-kick metrics cheap (PIPELINE §6 flagged).
- **Phase 75 Step 3** (report-card UI, Plan 75-05) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-25**
  (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). New `/app/sessions/[id]/phases` route renders Start + Underwater
  in the v3 visual language (1D usual-range strips, valence coloring, hover-explain, dismissable alert
  line, phase timeline); Swim/Whole = "coming soon". First Phase-75 surface visible in any UI.
  See [75-05-SUMMARY.md](phases/75-report-card-phase-model/75-05-SUMMARY.md). **Phase 75 stays 🚧 —
  Swim (9) + Whole (4) metrics + their UI still owed (item 7); those become new plans (75-06+).**
- **Phase 75-07** (report-card CONSOLIDATION — the race-phase view is now the PRIMARY `/app/sessions/[id]`) —
  **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-26** (loop: PLAN ✓ → APPLY ✓ → UNIFY ✓). Code committed
  **`040ce0d`** (frontend only) + docs. Classic analytics (SessionSummaryCard / PillarCards / MetricGrid /
  Simple-Advanced) removed; **`PhaseReportCard` is the body** with velocity / Time-to-Distance / video threaded
  via a new **`middleSlot`** seam; Swimming section = the existing per-cycle line charts (`CycleCharts`);
  standalone legend gone; delete → header **⋯ overflow**; **coach chat = floating bottom-right blob** (z above
  the hover scrim); `/app/sessions/[id]/phases` → **server-component redirect** to the primary page. Kept the
  **interim** classic VelocityChart+AccelerationChart (un-regressed). Build clean (19 pages); redirect
  (`NEXT_REDIRECT …;307`) + SSR verified; **AC-6 human-verify approved**. Decisions: coach-chat `simple`
  dropped (full depth, coach audience); ⋯ = Delete only (Export/Manage-videos not trivial). Pillars **not
  deleted**, just unrendered (relocate to a roster surface later).
  See [75-07-SUMMARY.md](phases/75-report-card-phase-model/75-07-SUMMARY.md).
  **Next in the merge:** **75-08** (compare-vs-last-X slider + alert "N Changes" rebuild + `phaseBaseline` as a
  persisted pref + timeline hover dot+range strips) → **75-09** (unified interactive phase-tinted trace, gated
  on the "new functionality" decision). ⚠ **75-06** (Swim/Whole *metrics*,
  [75-06-DISCOVERY.md](phases/75-report-card-phase-model/75-06-DISCOVERY.md)) composes independently at
  Swimming/Whole. CONTEXT + PLAN: [75-07-CONTEXT.md](phases/75-report-card-phase-model/75-07-CONTEXT.md) ·
  [75-07-PLAN.md](phases/75-report-card-phase-model/75-07-PLAN.md).
- **Phase 78** (multi-swimmer segmentation diagnostic — owed item 2) — **✅ CLOSED + committed
  2026-08-21** (`status: complete`, AC-1/2/3 met — pure diagnostic, no detector changes). Resolved
  (fork **b**): *scored* corpus = **4 swimmers** (Tony/Leo/Chantee/Dane),
  but the DB holds **~15 humans** — Titus (8), AlexGroup (9, a stand-in = 8 named testers), Jenna (2),
  Michael (1) are **real but unannotated** (37/92 sessions labeled). Validation is confined by
  *annotation coverage*, not data. See [78-01-SUMMARY.md](phases/78-multiswimmer-seg-diagnostic/78-01-SUMMARY.md).
  New owed gaps below (items 9–12).
- **Phase 79** (redefine `dive_start_s` = foot of first ≥X surge — owed item 1) — **✅ LOOP CLOSED
  (PLAN→APPLY→UNIFY), 2026-08-21, X=2.0.** Code committed **`e1934ba`**; docs (PIPELINE §3 / STATE /
  ROADMAP) landed; **backfill applied 2026-08-21.**
  ([79-01-SUMMARY.md](phases/79-dive-start-redefine/79-01-SUMMARY.md)).
- **Phase 81** (annotation video marking) — **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-26**, committed
  **`a73db03`** (frontend only). Shipped **well beyond** the plan's keyboard slice via three live redirections:
  the **active annotate camera is now a stage-fullscreen video overlay** whose control bar carries the
  **marker buttons** (Dive/UW/Stroke/Finish + stroke-mark, at the current frame) + **4/8/All window presets**
  — so a coach marks in **fullscreen without exiting** (the actual ask). Placed marks render as strip ticks
  (in-fullscreen confirmation, `TraceOverlay` used as-is). `overlayMode = active && synced` gate: native
  controls until synced (scrub to Set-sync landmark), custom marking stage once synced. Keys **1/2/4/5+M**
  retained as an alias. **Shared report-card components (VideoTracePanel/VideoPane/PlaybackControls/
  TraceOverlay) UNTOUCHED → zero report regression.** New shared `placeBoundary()` (chart-tool/keys/buttons
  DRY). ESLint + compile clean. ⚠ **Blocking human-verify NOT run** (annotate page is Supabase-auth-gated;
  shipped on user instruction + lint/compile + mockup approval) — owed against a live synced-video session.
  See [81-01-SUMMARY.md](phases/81-annotation-video-marking/81-01-SUMMARY.md). **Phase 81 stays 🚧 — 81-02
  (key-3 UW-kick marker + ALL backend: annotations/phase_metrics/api recompute) still owed.** Enables STATE
  item 9 (annotate the backlog fast).
- **Phase 86** (session clock accuracy — absolute, measured session start) — **🚧 4 of 4 plans
  CLOSED, 4 planned — AND THE PHASE IS STILL NOT DONE. 86-04 LOOP CLOSED 2026-09-02
  (`PLAN ✓ → APPLY ✓ → UNIFY ✓`).** 🔴 **THE PLAN COUNT NOW READS 4/4 AND WOULD TRIGGER A
  TRANSITION. IT IS WRONG — for the fifth time after 83-01, 83-02, 88-04 and 86-03's own 3/3.**
  The phase exists to replace estimates with measurements. It has replaced three and left its
  headline one untaken: **B1 (the end-anchored residual a coach actually sees) is UNMEASURED**, B2
  and B4 are **unmeasurable** until `videoStartPhoneMs` persists, camera warm-up is unmeasured and
  doubtful, and `rtt/2` is still an estimate. 86-04 spent **zero device time and produced no B1 by
  construction**. Closing on counts would bank a void run plus an in-sample instrument diagnostic as
  a finished measurement. **86-05 is owed. No phase commit.**
  - **86-04 — find on velocity, time on raw** ✅ **LOOP CLOSED 2026-09-02** (wave 4,
    `depends_on: ["86-03"]`, **autonomous: true**), 3/3 tasks, **8/8 AC**,
    [86-04-SUMMARY.md](phases/86-session-clock-accuracy/86-04-SUMMARY.md).
    `scratch/tap_test.py` 1061 → **1722** lines; `TAP-TEST-PROTOCOL.md` **+111/−0, append-only**.
    ✅ **The repair worked**: worst `encoder_overtrigger_ratio` **5.6 → 1.00**, accepted taps sitting
    >50 ms from their session median **10 → 0**, worst deviation **315.1 ms → 33.7 ms**,
    `readout_spread_frames` ≤ 1.2 on all 8 (improved on 5). ⚠ **And acceptance fell 83.3 % → 66.7 %**
    (28/42; rejections **7 unmatched · 5 readout-disagreement · 2 contention**) — the correct trade,
    pre-stated, and **B3 still fails on this corpus**, which is unfixable here because the data was
    collected through the broken instrument. The **interval-pattern check never fired** (worst
    38.4 ms against a 50 ms tolerance) — it cost nothing and stands as a guard for 86-05.
    Constants came out exactly as their rules anticipated: `TAP_FRAC` **0.20** (inside 8 of 8
    plateaus), `RAW_REFINE_WINDOW_S` **0.25** (4 × 55.7 ms), `PAIR_TOL_S` **0.05** (2 × 21.7 ms,
    **thin basis: 3 of 8 sessions, 12 intervals**).
    🔴 **AC-7's verdict on under-detection is SPLIT, and the unanticipated half is the useful one.**
    Of 7 unmatched onsets, **4 are real soft strikes** (19.0 / 16.7 / 9.0 / 7.2 % of session peak —
    the peak-relative threshold dropped them) and **3 sit at the noise floor** (1.9 / 1.7 / 3.3 %):
    nothing happened on the wheel, so **the audio onset count is not clean ground truth either**.
    ⚠ **Two findings deferred to §10's operator protocol rather than a second round of tuning**, per
    the plan's own rule that a second failed repair means a new plan, not more tuning: (a) `av_offset`
    is only estimated with **≥ 3 paired taps**, else it silently falls back to 0.0 and the scatter
    check is miscentred — **Tap_test_1 paired only 2**, so its one disagreement rejection is not
    trustworthy, and each failure mode makes the other worse; (b) **Tap_test_8's first two onsets are
    0.52 s apart** against a 2.54–4.42 s population, on the audio detector's own 0.5 s refractory
    edge — that single false onset produced **both** contention rejections and is why the
    `RAW_REFINE_WINDOW_S` assertion cleared by 0.01 s instead of 1.02 s.
    ⚠ **3 defects auto-fixed during APPLY, each of which would have read as success**: the interval
    check ran **session-wide** and regressed the standing desync gate **11/1 → 0/12** (moved to a
    PASS 3 over taps the scatter check already vouched for — the ordering is load-bearing); the
    fixture's 200 counts/s baseline was **8.5 % of peak `|velocity|`**, lifting every planted ring
    over the 0.20 cut for a reason unrelated to ring-down; and `|velocity|` of an overshooting
    impulse has **two lobes**, so one strike raised two candidates refining to the *identical* raw
    sample, inflating the very over-trigger field meant to expose that (deduped keeping the **first**
    candidate's offset — taking the smaller would bias the reported velocity-to-raw lag toward zero,
    which §10 makes a **void** condition).
    ⚠ **1 AC amended:** AC-5's `|residual| ≤ 2 ms` is unreachable on a single frame-quantised tap
    (uniform ±16.7 ms at 30 fps, the same mistake 86-03 made and corrected in its AC-1). The 2 ms bar
    moved onto the **encoder time vs the fixture's known strike** — exact, and it tests what the AC
    cares about. Result **0.46 ms**; 86-03 on the same zero-error fixture accepts **6 taps carrying
    >150 ms** (worst +190 ms).
    *Plan record as written 2026-09-02, before APPLY:*
    3 auto tasks, **zero device time and zero EAS
    builds** — everything runs off the 8 sessions already in `scratch/taptest/`.
    🔴 **THE 2026-09-01 DRAFT WAS AIMED AT THE WRONG DOMAIN.** It proposed measuring the wheel's
    ring-down and setting a `REFRACTORY_S` to collapse it, all inside the raw `|diff(counts)|` domain.
    Tony pushed back — *"on the velocity trace it looked like a giant spike, it was very obvious when
    the tap was"* — and read-only probes (`scratch/_tap_domain.py`, `_tap_domain2.py`) confirmed it on
    all 8 sessions: with a **peak-relative** threshold, decimated `|velocity|` holds a **flat event
    count from 10 % to 35 %** of the session maximum on every session, while raw jerk never stabilises
    (6–12 events, wobbling at every threshold step). **The strike was never hard to see — it was hard
    to see in that domain.** No refractory constant is needed at all; the smoothing collapses ring-down.
    ⚠ **BUT VELOCITY CANNOT CARRY THE TIMING.** The velocity peak lags the raw strike by **+16.3 ms
    pooled (n = 34, SD 22.6)**, per-session means **−5.0 → +39.4 ms**. Against B1's 33 ms bar, and
    varying session to session so it would **not** cancel as a constant, timing on velocity would
    manufacture exactly the clock error the test exists to detect. Hence the split the plan is built on:
    **FIND on velocity, TIME on raw (argmax of `|diff(counts)|` in a ±0.25 s window, 3.7 ms, no filter
    in the path), CHECK by interval pattern** (encoder gaps vs audio gaps — clock-offset-free by
    construction, so it is a real encoder-side check and not a disguised look at the answer).
    🔴 **THE PLAN NO LONGER CLAIMS TO PRE-REGISTER ITS CONSTANTS, BECAUSE IT CANNOT.** The sweep was
    already run on this corpus. `TAP_FRAC` / `RAW_REFINE_WINDOW_S` / `PAIR_TOL_S` are **tuned in-sample
    and say so**. What is genuinely pre-registered: each constant must equal what its written
    derivation rule produces from Task 1's printed measurement (**the rule wins over the anticipated
    value**), all three are frozen before 86-05's data exists, and **this corpus is spent** — it
    developed the instrument, so it can never measure the clock.
    🔴 **THE PLAN STILL FORBIDS THE OBVIOUS FIX**, and now a second one. (a) No rejection rule keyed
    on the residual or its session median — 86-03 already measured what that gives (**−1.79 ± 9.88 ms**)
    and it would rescue B1 by construction. (b) **No audio-onset-count hint into the encoder detector**:
    it would raise acceptance by coupling the two sensors the test keeps independent. The honest cost of
    under-detection is n, and §7 shows n is cheap — so the fix belongs in the protocol (strike with
    consistent force, ≥ 8 strikes per session), not in the detector.
    ⚠ **UNDER-DETECTION IS PREDICTED AND PRE-STATED**: velocity candidates total **34 against 42 audio
    onsets**, an **~81 % ceiling still under B3's 90 % bar**. Written into the plan before Task 3 runs so
    it cannot be discovered and then rationalised. Its cause is **not established** — Task 1 measures it
    by reporting the velocity amplitude at each unmatched onset. Under-detection is the **safe** failure:
    a missed strike leaves its onset unmatched inside `MATCH_WINDOW_S` (1.4 s vs ~3 s spacing) and is
    rejected and counted — visible, not laundered, unlike 86-03's confident wrong answers.
    ⚠ **`MATCH_WINDOW_S` stays frozen**, and now for a positive reason: with a clean encoder list it is
    what converts a missed strike into an honest rejection. `find_taps` and its `k=10.0` must also
    survive — the fixture needs the 86-03 detector to reproduce the defect, so deleting it deletes the
    test.
    ⚠ **B1 IS NOT MEASURED BY THIS PLAN.** It stays unmeasured until 86-05.
    ⚠ **86-05 is owed and needs a mobile change**: `videoStartPhoneMs` is never persisted, so B2
    (camera warm-up) and B4 (`rtt/2` symmetry) are unmeasurable without an app edit + EAS build.
    See [86-04-PLAN.md](phases/86-session-clock-accuracy/86-04-PLAN.md).

  *Record below as written 2026-09-01, when 86-03 closed and 86-04 did not yet exist:*
  **🚧 3 of 3 plans
  APPLIED, but 86-03 ENDED IN A VOID RUN, so the phase does NOT close. 86-01 LOOP CLOSED 2026-08-31;
  86-02 LOOP CLOSED 2026-09-01 and its AC-7 is now PASSED (see below); **86-03 LOOP CLOSED 2026-09-01
  (PLAN ✓ → APPLY ✓ → UNIFY ✓) — run VOID under its own pre-registered B3 bar.**
  🔴 **THE LOOP CLOSED; THE PHASE DID NOT.** All three plans now have SUMMARYs, so the plan-count
  heuristic reads 3/3 and would trigger a transition. **It is wrong here**, for the fourth time after
  83-01, 83-02 and 88-04: 86-03's deliverable was a *measurement*, and the measurement was voided by
  its own instrument bar. Transitioning would record "session clock accuracy — complete" over a
  phase whose central number is still an estimate. **Phase 86 stays 🚧 pending a successor (86-04).**
  committed `828ee49` (backend repo: plan + summary + harness) and `1aa45cb` (swimnetics-mobile:
  `sessionClock.js` + `RecordScreen.js`).**
  🔴 **86-03's DEVICE RUN HAPPENED AND WAS VOIDED BY ITS OWN INSTRUMENT BAR.** The EAS build shipped,
  8 tap sessions were recorded on the Test athlete (wheel on a desk), and all 16 files were pulled
  from Storage. **B3 — acceptance ≥90%, the bar the protocol says VOIDS THE RUN — FAILED at 35/42 =
  83.3%**, and AC-6 failed with only 4 of 8 sessions reaching 5 accepted taps. B1 would have passed
  both its bars (+14.17 ± 16.06 ms, n=35; between-session SD 44.03 ms) **and is deliberately NOT
  reported as a result**, because B3 is a precondition, not a companion metric. Recorded as void at
  the user's explicit direction. → [86-03-SUMMARY](phases/86-session-clock-accuracy/86-03-SUMMARY.md)
  🔴 **THE DEFECT: the encoder tap detector over-triggers, and AC-4's rejection rule is STRUCTURALLY
  BLIND TO IT.** A struck wheel rings; `REFRACTORY_S = 0.5` does not span the ring-down, so the
  detector found **10–28 events for ~5 real strikes** (28 in one session) and `MATCH_WINDOW_S = 1.4`
  paired audio onsets with ringing instead of strikes. AC-4 rejects on **audio-vs-frame** disagreement
  — two readouts of the *video* — so an **encoder** mispair leaves both in perfect agreement and is
  marked ACCEPTED carrying a 180–320 ms residual. **10 of the 35 accepted taps sit >50 ms from their
  own session median.** Protocol §7 predicts a within-session SD of ~9.6 ms from frame quantisation;
  only 3 of 8 sessions are near it. **A rejection rule that cannot see the failure mode that actually
  occurs launders bad taps as good ones** — the most valuable output of the run. The video side was
  healthy throughout (`readout_spread` 0.28–1.11 frames against a 1.2 bar).
  ⚠ **DO NOT quote the post-hoc per-session median of −1.79 ± 9.88 ms (n=8) as a result.** It is
  temptingly close to zero and it is exactly what pre-registration exists to stop.
  ✅ **86-02's AC-7 PASSES — its only unmet AC, closed by this run.** All 8 sessions uploaded with
  non-NULL `session_start_utc_ms`, `sync_error_ms`, `clock_offset_ms`. The probe burst, the
  `Math.round` guard, the plausibility window and the concurrent `/time` probe all survived a real
  device. ✅ **The end-anchor claim is now EVIDENCED, not just read off a source line:** on the 2
  sessions carrying a stored `sessions.video_origin_s`, the analyzer's independently computed
  `deviceDuration − videoDuration` agrees to **+3.5 ms** and **+10.9 ms**.
  ✅ **The "20–80 ms" BLE flight estimate is BOUNDED and its upper end is WRONG:** `sync_error_ms` is
  `minRTT/2` by construction, and the 8 measured values span **0.5–30.0 ms** (mean 18.50 ± 4.37).
  ⚠ **B2 and B4 are UNMEASURED and `videoStartPhoneMs` is UNRECOVERABLE.** It is **never persisted** —
  only React state and the `RecordScreen.js:854` log line; not in the DB, not in the clip container
  (`creation_time` is 1-second resolution against a 33 ms bar). The protocol asked an operator to
  hand-copy a number the app throws away. **Persisting it is a mobile change and a successor's job.**
  ⚠ **Camera warm-up "~2 s" ([VideoOverlayScreen.js:52](../swimnetics-mobile/src/screens/VideoOverlayScreen.js))
  is still unmeasured but now DOUBTFUL:** `deviceDuration − videoDuration` is **0.6913 s ± 28.4 ms**
  across all 8. That is start-lag + stop-lag and does not isolate warm-up, but a ~2 s warm-up needs a
  stop-lag near −1.3 s, which is not physically sensible.
  ⚠ **Successor brief, and the data is already on disk in `scratch/taptest/`:** (1) measure the
  ring-down from the 8 raw CSVs and set the refractory period from that measurement, committed BEFORE
  looking at its effect on B1; (2) add an **encoder-side** pairing check so a mispair is rejected
  rather than laundered; (3) persist `videoStartPhoneMs`. **Re-analysis needs no new device run** — a
  re-run is needed only for B2/B4.
  ⚠ One post-run protocol amendment, dated and justified in `## Amendments`:
  `--video-start-phone-ms` made optional so B1 stayed computable and B2/B4 were reported as unmeasured
  rather than invented. No bar, threshold, rejection rule or formula moved; self-test unchanged.
  ⚠ **86-02's APPLY also ran in an unrecorded session** and was left uncommitted with **no SUMMARY** —
  found on disk 2026-09-01, the third instance of this pattern after 84-02 and 88-05. Closed with the
  same reconciliation posture: every claim re-derived from the diff and by re-running the gates.
  Re-verified at close: `session_clock_check` **45/45**, `pytest` **566 passed** (unchanged from
  Phase 88's close — `git status` showed **no modified tracked files**, so `api.py`, `web/` and every
  other standing-harness input are provably untouched; the other six harnesses were deliberately NOT
  re-run for that reason). Live `GET /time` → 200; live `sessions` select → all three `patch_14`
  columns present and `null`. → [86-02-SUMMARY](phases/86-session-clock-accuracy/86-02-SUMMARY.md)
  ~~🔴 **AC-7 (device verify) is the only unmet AC and is BUILD-GATED** — Nothing in 86-02 has run on
  a phone.~~ → **RESOLVED 2026-09-01 by 86-03's device run: AC-7 PASSES, 8 of 8 sessions non-NULL on
  all three columns.** ⚠ But the accuracy figures did NOT all become measurements — 86-03's run was
  voided by B3, so the end-anchored residual, camera warm-up and the `rtt/2` symmetry check remain
  **estimates**. What did become measured: AC-7 itself, the end-anchor claim, and the BLE flight
  bound. See the 86-03 block above for the measured/estimated table.
  ⚠ **Tooling trap found while closing, will recur:** `.venv/Scripts/python.exe` has **no pytest**,
  and `python -m pytest … | tail` still exits **0** when the module is missing — the suite silently
  does not run. Use the conda interpreter (`C:\Users\TonyZheng\miniconda3\python.exe`, pytest 9.0.2).
  Suite **505 → 520** at 86-01
  (+15, zero pre-existing failures — +15 is exactly the new-test count, so nothing pre-existing was
  altered). ✅ **`patch_14` APPLIED by the user 2026-08-31** — the three columns are live.
  ✅ **86-01 COMMITTED `861040b` and PUSHED to `main` 2026-08-31; Railway deploy VERIFIED live** —
  `GET /time` went 404 → 200 across the rollout and the deployed `/openapi.json` carries all three
  form fields plus `/time` with no security requirement. **Item 27's deploy-ordering gate is now
  SATISFIED: the backend is live BEFORE any 86-02 build exists.**
  🔴 **86-03's PLANNING FOUND THAT PHASE 86's STATED MOTIVATION IS WRONG ABOUT THE OVERLAY.**
  86-01 and 86-02 both justify themselves as fixing "a live bug in the shipped video overlay."
  **The shipped overlay does not use the mapping 86-02 corrected.** `VideoOverlayScreen.js:69`
  computes `endAnchoredOriginS = deviceDurationS − videoDurationS` — a difference of two
  **durations**, in which `sessionStartPhoneMs` cancels exactly — and that is what is persisted to
  `sessions.video_origin_s` and read back by both the iOS overlay and the web annotate page. Its own
  header comment records that the start-anchored predecessor was dropped in Phase 60 because camera
  warm-up put it **~2 s off**, 25–100× larger than the error this phase chases. What 86-02 genuinely
  changed is narrower and still real: **`session_start_utc_ms`** (the absolute export for an external
  video system, which has no end-anchor because its camera is not stopped by our tap) and 84-02's
  **`go_signal_s`**. ⚠ `RecordScreen.js:769` still carries the stale comment
  `video_origin_s = (sessionStartPhoneMs − videoStartPhoneMs)/1000`, which is how the mistaken framing
  survived into two plans — NOT fixed by 86-03, which must not edit the app it measures.
  → [86-03-PLAN](phases/86-session-clock-accuracy/86-03-PLAN.md).
  ✅ **86-03 TASKS 1-3 APPLIED 2026-09-01** (`3f4d2c7`), **Tasks 4-5 APPLIED 2026-09-01** — the
  build gate lifted, the run happened, and the analysis is written (void; see above). Tasks 1-3's
  gates were **re-verified from a clean tree** at the start of the resumed session rather than taken
  on trust, all three green: `scratch/tap_test.py` **self-test PASS** (five injected offsets −500/−50/0/+50/
  +500 ms recovered within **0.33 ms** against a 2 ms bar, rejection path fires, container offset
  provably does not leak); `--validate-timebase raw/` → **39/39 clean files agree with
  `vel_acc_extraction` SAMPLE BY SAMPLE at 0.000000 ms and 0.000000 mm**, one file excluded for a
  stated provable reason (one count step of exactly half a revolution, where modular arithmetic
  and `np.unwrap` break the tie one full revolution apart). `pytest` **566 passed**, unchanged.
  → [TAP-TEST-PROTOCOL](phases/86-session-clock-accuracy/TAP-TEST-PROTOCOL.md), committed BEFORE
  the run so the bars cannot move to meet the data (AC-5).
  🔴 **BUILDING THE INSTRUMENT FOUND THREE DEFECTS, ALL OF WHICH WOULD HAVE CORRUPTED THE
  MEASUREMENT SILENTLY.** (1) An **off-by-one in the tap detector** — `jerk[k]` spans samples
  `k→k+1`, so reporting `k` put every tap one raw sample (**3.7 ms**) early, a constant positive
  residual that would have been attributed to the clock. (2) **Encoder dropouts look exactly like
  strikes** — aliased count steps appear in **37 of 40** real raw recordings, up to 66 in one
  file, so the detector now refuses any step above 1024 counts/sample (12.7 m/s at the tether).
  (3) A **naive `micros()` unwrap invents time** — `raw/leo3.csv` has 17 backward timestamp steps
  in a 46 s recording, and treating each as a uint32 rollover put its time base **20.3 hours**
  out; only a step below −2³¹ is a rollover.
  ⚠ **FOUR ACs WERE AMENDED BEFORE ANY DATA EXISTED**, each dated and justified in the protocol's
  `## Amendments`: AC-1's flat 2 ms bar was kept by **stratifying the fixture's sub-frame phases**
  rather than loosening it; AC-2's coach-mark landmark was replaced by the stricter sample-by-
  sample comparison above (a coach's dive mark is a human judgement, not a threshold crossing);
  AC-4's half-frame rejection was widened to 1.5 frames because the self-test showed a
  median-centred half-frame bound **rejects the tails of a uniform distribution and biases the
  surviving mean** — observed at +9.6 ms in a fixture with zero true error; and the camera-warm-up
  sign was flipped (the PLAN's order made a real warm-up negative).
  ✅ **A decision the PLAN had only asserted is now evidenced:** the decimated trace sits a median
  **103 ms** (worst 353 ms) from raw at distance landmarks, because a small vertical difference
  becomes a large horizontal one wherever the distance curve is flat. Reading the raw CSV rather
  than the processed trace is load-bearing, not a preference.
  **86-03 redirects the tap test
  accordingly:** its primary target is the **end-anchored playback origin** (the number a coach
  actually sees, never validated, independent of 86-02); differencing the two origins on one rep
  gives the **first real measurement of camera warm-up**; and it **bounds rather than isolates**
  `rtt/2`, which the plan pre-registers rather than discovering afterwards. Instrument = new
  `scratch/tap_test.py` reading the **raw** 270 Hz CSV (not the processed trace) plus ffmpeg audio
  onset cross-checked against ffprobe frame timestamps; bars pre-registered in a committed
  `TAP-TEST-PROTOCOL.md` BEFORE the run. ✅ **Needs no pool, no swimmer, no water** — the wheel on a
  desk is enough; the only gate is the EAS build.
  **86-02 = the mobile half, and the only thing that can ever fill 86-01's columns.** Replaces the
  one-shot META with a **burst of 10 timed round trips**, keeps the **minimum** RTT (Cristian's — the
  least-congested sample), and corrects `sessionStartPhoneMs` by `minRTT/2`. That correction is the
  **live overlay bug fix**: `deviceNowUs` is captured when the ESP32 *builds* the reply, so the
  inbound BLE leg is currently attributed to the encoder and the start is biased **late** by one
  one-way flight time. Then measures the phone's offset against `GET /time` **concurrently with the
  ~20 s dump** (so it costs no wall clock) and sends all three fields on the swim's own
  `POST /process`. Files: new pure `swimnetics-mobile/src/lib/sessionClock.js` (zero imports) +
  `RecordScreen.js` + new `scratch/session_clock_check.mjs` — the 84-05 harness pattern, since the
  mobile tree has no test runner.
  🔴 **`Math.round` on `session_start_utc_ms` is load-bearing:** `api.py` declares `Optional[int]`, so
  a fractional string 422s at **Pydantic coercion, before the handler runs** — 86-01's
  drop-don't-422 posture cannot protect a value that never reaches it, and the whole swim is lost.
  Pinned by AC-3 and a source-level harness assertion.
  ⚠ **86-01's D2 window bites the phone:** floor 2020-01-01, ceiling `now + 48 h`. Seconds-for-ms
  lands in 1970 and is discarded **with a log line the phone never sees** — so the harness parses
  `_EPOCH_MS_FLOOR` / `_EPOCH_MS_FUTURE_SLACK_MS` out of `api.py` and fails on drift (the
  `MAX_VIDEO_BYTES` precedent).
  ✅ **`clock_offset_ms` is measured and reported, NEVER applied.** The app records at poolside where
  `GET /time` can fail outright; applying it would make the primary number's meaning depend on
  whether an unrelated network call succeeded. `session_start_utc_ms` is therefore always "phone
  clock, corrected for BLE flight only" — one definition, every session. Matches api.py:292-297.
  Sign is documented: **positive = phone ahead of server**; convert with `start − offset`.
  ⚠ **The clock probe may never cost a swim** (AC-2): every probe can time out and DUMP still runs,
  the CSV still saves, the fields are simply absent. It also must not race the Phase 74 stalled
  retry — a generation ref aborts an in-flight burst, and the retry keeps its one-META-then-DUMP shape.
  ⚠ **84-02's GO marker moves** — it resolves against the corrected start now, shifting `go_signal_s`
  by ~`rtt/2` (tens of ms), far below the coach thumb latency the metric already embeds.
  ⚠ **`rtt/2` assumes symmetric legs and remains an ESTIMATE until 86-03.** Two facts bound it, both
  verified: `processPending()` is the **first** call in a free-running `loop()` with no `delay` while
  not recording, so device-side queueing is negligible; and both directions are acknowledged
  (`writeCharacteristicWithResponseForService` out, `notify(false)` — an indication — in). ⚠ **The tap
  test has now RUN and was VOID, so this stands unchanged: no document may quote a corrected-overlay
  accuracy figure as measured.** B4 was never run for want of `videoStartPhoneMs`.
  ~~⚠ **AC-7 is build-gated**~~ → **PASSED 2026-09-01 on the 86-03 run.**
  Out of scope and named as such: STATE item 25's ISO debug line at `RecordScreen.js:1155`, which this
  plan makes more meaningful but does not get to redesign.
  ⚠ **UNIFY reconciled from the TREE, not from execution memory** — APPLY ran in a cut-off prior
  session. Every claim was re-verified: full `git diff`, `pytest tests/`, a live `TestClient` call on
  `/time` (200, 3 ms off the host clock, no auth header), `python -c "import api"`.
  ⚠ **Phase 86 stays 🚧 — NOT transitioned, NO phase commit. 2 of 3 plans.** Plan/summary counts are
  equal (2/2), which is exactly the heuristic that wrongly called 83-01 and 83-02 done. **86-03 is now
  written but not applied**, and 86-02's AC-7 is unmet, so the phase cannot close on counts alone.
  Both 86-03 and AC-7 ride the SAME owed EAS build as Phase 84's device-verify batch.
  New phase, not in ROADMAP's 1–85 index and not derived from
  any owed item; it comes out of the SwimClips integration conversation but the first two plans are
  **useful with or without that partnership** — they fix a live bug in the shipped video overlay.
  **The problem:** every sample is stamped `micros()` (boot-relative, wraps at 71.6 min). Absolute time
  exists only as `sessionStartPhoneMs`, computed on the phone from META
  (`RecordScreen.js:457`), used for the local overlay, and **thrown away** — never sent to the server.
  `api.py` never sets `recorded_at`, so the DB default `NOW()` stores **upload time, not swim time**.
  So nothing in the system can answer *"what UTC instant was sample #0?"* — and the phone's own
  mapping carries an **unmeasured 20–80 ms error** (BLE flight time between `sendMeta()` sampling
  `micros()` and iOS firing the callback), which is a real defect in the current overlay.
  ✅ **Firmware is OUT of scope for the whole phase** — verified, not assumed: `sendMeta()` already
  returns `device_now_us` captured at send time (`ESP_32_V5.ino:426`) and `pendingMeta` is a plain
  re-arming flag (`:528`), so **META is idempotent and repeatable**. The round trip runs against the
  existing command; the only blocker is the phone-side `metaSeenRef` one-shot (`RecordScreen.js:440`).
  No flash, no device access, no risk to buffer-and-dump. (Firmware IS git-tracked and not ignored —
  checked, since CODEBASE-AUDIT warns `.gitignore` swallows it.)
  ⚠ **`GET /time` must be UNAUTHENTICATED, and that is correctness, not convenience:** `require_auth`
  (`api.py:74`) calls `sb.auth.get_user(token)` — a **network round trip to Supabase per request**.
  The client uses this endpoint to measure its own RTT and derive clock offset from RTT/2; an
  uncontrolled network call inside the handler lands *inside the interval being measured*. It reads
  like an auth oversight, so the reason is pinned in a code comment and an AC.
  ✅ **The Phase-84 gate is LIFTED — verified 2026-08-31, not assumed.** Backend repo clean at
  `54cb8d1` = `origin/main`; mobile repo clean at `6b24c79` = `origin/main` (the 14 modified files are
  gone); and the **deployed** `/openapi.json` returns 200 containing `go_signal_s`, so 84-02's backend
  is genuinely live on Railway. That was the whole prerequisite (`api.py` + `tests/test_api.py` no
  longer hold uncommitted 84-02 work), so 86-01 could be applied without entangling two phases.
  ⚠ **Deploy ordering is load-bearing** (same constraint as 84-02, now doubled): `api.py` live on
  Railway **before** the 86-02 build that sends the fields, or FastAPI drops the unknown form fields
  silently and sessions recorded in the gap lose their start with no error anywhere.
  ✅ **A SECOND ordering hazard was found during APPLY and designed out.** The plan's Task 2 says to add
  the three keys to the `session_row` dict literal — which would have made **deploying `api.py` before
  the user applies `patch_14` break every upload** (PostgREST rejects unknown columns), and would also
  have failed `TestSchemaContract`, whose static extractor checks every column named in an `.insert({…})`
  literal against the `supabase/live_schema.json` snapshot (the columns are not in the live DB yet, and
  hand-adding them to the snapshot would make the guard lie). Both are avoided by the **Phase 70
  `recording_token` precedent three lines above**: assign each key by subscript, only when a value
  survived validation. Verified the extractor ignores that form. Absent key ≡ explicit NULL in the
  stored row (nullable, no default), so the contract is unchanged — **patch_14 and the deploy can now
  land in either order.**
  ⚠ **No backfill is possible** — only the phone can produce this at record time, so all 99 existing
  sessions hold NULL permanently. Consumers must treat NULL as *unknown* and never substitute
  `recorded_at`; same reasoning that forbids backfilling NULL `sample_rate_hz` with 100.
  **Decisions (2026-08-30):** storage = **new columns, BIGINT epoch ms** (`patch_14`, unapplied) rather
  than `metrics_json.phases` — this is session provenance like `sample_rate_hz` (patch_09), not a
  metric, and `phases` is rewritten by recompute and `PUT /annotations`; `recorded_at` semantics
  **deliberately unchanged** (fixing it is a library-wide comparability break → new owed item 22).
  **3 plans: 86-01 backend (✅ closed, uncommitted) · 86-02 mobile round-trip + send (📋 planned) · 86-03 the tap test (not written).**
  ⚠ **Every accuracy figure in this phase is an ESTIMATE until 86-03 runs** — hence its own plan.
  **Two UNIFY findings beyond the plan:** (1) `_finite_or_none()` was added un-planned — a NaN/inf
  diagnostic serializes to invalid JSON and would fail the whole insert, which would violate AC-3's own
  principle (never lose the swim over a clock annotation); (2) the sanity window is **2020-01-01 floor →
  now + 48 h** (`_EPOCH_MS_FLOOR`), wide on purpose: both realistic client unit errors land nowhere near
  a real "now" (seconds→1970, micros→tens of thousands of years out), so a wide window costs nothing in
  false rejections even against a badly skewed phone clock. **86-02 must not send seconds.**
  ⚠ **The plan's checklist item `grep -n "recorded_at" api.py` "returns nothing" is now literally
  false** — it returns `api.py:301`, a **comment** warning readers never to substitute it. Never *set*,
  so the boundary holds; the check's form changed, not the behaviour.
  ⚠ **AC-1/AC-5 are proven only against the MOCKED insert** — nothing has touched a real column.
  **Two blockers before the 86-02 app build ships → new owed items 26–27 below.**
  See [86-01-SUMMARY.md](phases/86-session-clock-accuracy/86-01-SUMMARY.md) ·
  [86-01-PLAN.md](phases/86-session-clock-accuracy/86-01-PLAN.md) ·
  [86-02-PLAN.md](phases/86-session-clock-accuracy/86-02-PLAN.md).
- **✅ Working tree RESOLVED 2026-08-29 — committed + pushed as `20c0432`.** The shared-`api.py`
  deadlock (75-06's cycle threading + `PUT /annotations` repair tangled with 82-01's session-delete
  storage cleanup, hunk-level staging unavailable) was broken by taking the **whole tree in one
  commit**: 75-06 + 82-01 + 83-01/02/03 + Phase-80 notebook/scripts + research docs + app icons,
  **74 files**. ⚠ **This pushed to `main`, which auto-deploys** — Railway (api.py: the delete-cleanup
  and the annotations repair) and Vercel (web). Excluded deliberately: `*.html` (already gitignored,
  incl. the 14 MB Phase-80 plotly figures) and `scratch/_cycle*.mjs` (generated copies of
  `web/lib/` sources).
- **Committed history:** 75-03 = `7035157`, Phase 79 = `e1934ba`, Phase 78 + doc reconciliation =
  `76d2a18`, **75-05 report-card UI = `9dd5f7a`**, **75-07 report-card merge = `040ce0d`**, **81-01
  annotate marking = `a73db03`** (frontend only; `.claude/launch.json` is gitignored, stays local),
  **75-06 + 82-01 + 83-01/02/03 whole-tree = `20c0432`** (2026-08-29, pushed to `main`),
  **83-05 overlay panel = `45a858b`** (2026-08-29, pushed to `main` — frontend + docs only, so this
  deploy is Vercel-only; `scratch/_cycle*.mjs` excluded again as generated copies of `web/lib/` sources),
  **Phase 85 marketing home = `a75c373`** (2026-08-29, pushed to `main` — Vercel-only; excludes
  `scratch/_home_session.json`, which carries the source athlete's raw session).
  Stored library backfilled 2026-08-21 (all four boundaries) and again **2026-08-28** (75-06 metrics +
  the 75-04 Start metrics). Other dirty files belong to **other streams:** `ESP_32_V5/ESP_32_V5.ino`
  (firmware), `.gitignore`, `assets/icon/`, `scratch/`, `segmenter_report.json`, the untracked Phase-80
  dir, and the 75-04/75-06 discovery docs.

## Segmentation status — the 4 phase boundaries
Mechanisms in [PIPELINE.md §3](../PIPELINE.md).

| Boundary | State |
|---|---|
| `dive_start_s` | ✅ `detect_dive_start` (79) — foot of first ≥2 m/s surge; median 0.15 s vs 36 marks (vs `baseline_end` 0.72 s); falls back to `baseline_end` on sub-X starts |
| `underwater_start_s` | ✅ `detect_underwater_start`, median 0.13 s |
| `stroke_start_s` (breakout) | ✅ free 0.42 s (Tony+Leo) · fly 0.38 s (Tony/Leo; ⚠ 0.87 s Chantee) · ⛔ **back n=0 unvalidated** · ⚠ **breaststroke = incumbent, untuned** (Phase 78). **Now `detected` via `detect_swim_boundaries` in `resolve_boundaries`** (75-03), so backfill/recompute refresh it (was stale seed, 3.56 s → 0.40 s) |
| `finish_s` | `detect_swim_window` end — **now `detected` via `detect_swim_boundaries`** (75-03), no longer the stale last-cycle seed. Still weakest marker (item 12) |

## Owed / next actions (priority order)

**1. ✅ RESOLVED (Phase 79, eyeball approved 2026-08-21). → [79-01-SUMMARY.md](phases/79-dive-start-redefine/79-01-SUMMARY.md).**
`dive_start_s` now = **`detect_dive_start`** ([metrics.py](../metrics.py)): the foot of the first surge
that clears **X = 2.0 m/s** — the last prominent trough (prominence ≥ 0.15·X) left of the first upward
crossing. Wired in `resolve_boundaries` as source `detected`; `build_seed` reads the stored boundary back
for the annotate draft (mirrors the 75-02 underwater precedent). When no sample reaches X (weak wall
push-off) → **falls back to `baseline_end`** (source `auto`), so never worse than the old rule. Swept
(`tools/score_dive_start.py`, 36 hand-marked sessions): **0.15 s mean|err| vs `baseline_end` 0.72 s**;
detector-only 0.11 s (16/16); all 36/36 within 0.5 s. X=2.0 chosen for tug-margin (accuracy statistically
tied across X∈[1.25,2.0]). ✅ **BACKFILL APPLIED 2026-08-21** (user-run `python tools/backfill_phases.py
--apply`): stored `dive_start_s` re-resolved across the library, comparability break closed (standing
pattern 57/59-03/61-01/65/76-77). Code committed `e1934ba`; docs landed with the Phase 78 commit.

**2. ✅ RESOLVED + CLOSED (Phase 78, committed `76d2a18`; pure diagnostic, AC-1/2/3). → [78-01-SUMMARY.md](phases/78-multiswimmer-seg-diagnostic/78-01-SUMMARY.md).**
Answer = fork **(b): validation is confined by ANNOTATION COVERAGE, not data.** "One swimmer" was
false (4 annotated: Tony 18, Leo 14, Chantee 3, Dane 2) — but so is "clean multi-swimmer set."
**92 sessions exist, only 37 (40%) annotated.** STATE's roster instinct was RIGHT: **Titus** (8) and
**AlexGroup** (9, a stand-in whose session names are testers Henry/Ben/Desi/Spencer/Alina/Tate/
Olivia/Anna) are real, plus Jenna (2), Michael (1) — **all unannotated**, so no scorer sees them.
Where measured, detectors hold (underwater 0.13 s, free breakout 0.42 s across both swimmers; fly
0.38 s but 0.87 s on Chantee). PIPELINE §8 + the `score_segmenter.py` banner corrected. The fix that
matters is item 9. Residual gaps → items 9–12.

**3. ✅ DONE (2026-08-21).** 75-03 eyeball run on ground-truth windows
(`tools/plot_kicks.py --annotated-only`), hypothesis 1 approved, `75-03-SUMMARY.md` written. The
review also surfaced + fixed the stale-`stroke_start` backfill defect (see item 6). Two known
over-detection cases logged (`udk` alternating peaks; shallow-freestyle ripple) — not blockers.

**4. Fix `tools/breakout_band_probe.py` (DEFER-77-A).** The probe plots the exploratory/rejected
detector, not the shipped one — 3 defects, one root cause. Defect (a): `:270` passes `cand_idx` (the
probe's own `_detect_breakout`) to `_plot` instead of `ship_idx`, so even the freestyle plots draw a
detector materially different from production. **This blocks Phase 76's owed AC-4** (item 5). Fix (a)
before item 5, all three before the next breakout human-verify. Detail in
[77-01-SUMMARY.md](phases/77-fly-breakout-detection/77-01-SUMMARY.md) DEFER-77-A.

**5. Run Phase 76's AC-4 eyeball.** Never run — both 76 corrections were found by measurement, not the
checkpoint. Needs item 4(a) first.

**6. ✅ DONE (2026-08-21) — Backfills applied (user-run).** ⚠ CORRECTED 2026-08-21: the earlier
claim that `backfill_phases.py --apply` refreshes 76/77's `stroke_start` was **wrong** — it only re-ran
`compute_phases`, which read the stale stored `initial_phase_end_idx`. **Fixed** (75-03):
`resolve_boundaries` resolves `stroke_start`/`finish` via `metrics.detect_swim_boundaries`, so a single
`python tools/backfill_phases.py --apply` refreshes **all four** boundaries + 75-03's kick metrics from
live detectors. **Ran 2026-08-21** — comparability break landed across the library (dive_start +
all-four-boundary refresh in one pass). Standing pattern (57 / 59-03 / 61-01 / 65 / 79).

**7. ✅ RESOLVED + CLOSED (75-06, 2026-08-28). → [75-06-SUMMARY.md](phases/75-report-card-phase-model/75-06-SUMMARY.md).**
The Step-2 metric registry is **complete**: Start 10/11 (75-04) + Underwater 13/13 (75-02/03) +
**Swim 12/12 and Whole 11/11 (75-06)** = 46 of 47 specs implemented; `streamline_drag` is the only
one still `planned`. Backfill applied — Start 95–97/99, Swim window 97/99, Whole 84–98/99.
⚠ `reaction_time` is **0/99 and cannot fill**: the `PUT /sessions/{id}/go-signal` endpoint shipped in
75-04 but the coach **GO button never did**, so no session has a GO time (item 15).

**8. Step-3 UI.** Phase-organized web report card (Dive/Push-off / Underwater / Swim), then iOS.
Display doctrine = within-athlete contrast, **no absolute thresholds**. Design docs:
[CONTEXT-ui-consolidation.md](phases/75-report-card-phase-model/CONTEXT-ui-consolidation.md) (spine =
race-phase timeline; pillars → roster surface) +
[75-05-DISCOVERY-ui-visual-language.md](phases/75-report-card-phase-model/75-05-DISCOVERY-ui-visual-language.md)
(2026-08-22). **Visual language re-settled 2026-08-25 in the rendered mockup `scratch/report-card-concept-v3.html`
(the source of truth; v1/v2 are earlier drafts):** (1) each metric = a **1D usual-range strip**
(shaded median±1.5·MAD band + median tick + today dot on a 0-based scale) — the Today-vs-Usual paired
bars are **out** (two equal bars carried no info); (2) color = **direction-of-good valence** — green
better / red worse / **grey "changed, unclear"** where "better" is a coaching call — via a new
reviewable `DIRECTION_OF_GOOD` map (⚠ a deliberate, user-approved evolution of the old no-valence rule;
still no absolute thresholds); (3) **almost no always-on prose** — descriptions + comparisons live in a
page-dimming **hover overlay**; (4) per-phase layout = **inset chart on top, metrics in 2 columns**;
(5) terse titles ("Dive / Push-off" — dive & wall-push are the *same* Start window per registry, so no
metric split). Top = the deterministic **alert line** (count + "N worse / N changed / N better" chips,
**coach-dismissable**). Baseline = **last 5 same-stroke swims**, band = **median ± 1.5·MAD** (robust for
n=5; was mean±SD). Placement = **new `/app/sessions/[id]/phases` route** (isolated, additive).
**→ PLAN [75-05-PLAN.md](phases/75-report-card-phase-model/75-05-PLAN.md) (created 2026-08-22, REVISED to
the v3 language 2026-08-25) — ✅ APPLIED + human-verify approved 2026-08-25 (loop: PLAN ✓ → APPLY ✓ →
UNIFY ○). → [75-05-SUMMARY.md](phases/75-report-card-phase-model/75-05-SUMMARY.md).** Shipped: new
`/app/sessions/[id]/phases` route rendering Start + Underwater as 1D usual-range strips (median±1.5·sMAD
of last 5 same-stroke), valence-colored via a new reviewable `DIRECTION_OF_GOOD` map (a user-approved
evolution of the no-valence rule — **still no absolute thresholds**), a deterministic dismissable alert
line, phase timeline, phase-tinted velocity line, and a page-dimming hover-explain overlay; Swim/Whole =
"coming soon". New pure libs `web/lib/phaseBaseline.js` + `web/lib/phaseValence.js`; components under
`web/components/portal/phases/`. Build clean; engine scratch checks 18/18. Deferred (documented in
SUMMARY): server-side dismiss persistence (client localStorage now), LLM headline, imperial/iOS, richer
signal insets. **✅ LOOP CLOSED (PLAN→APPLY→UNIFY) 2026-08-25, committed `9dd5f7a`.** Next
Phase-75 work = Swim/Whole metric batches (item 7) + their strips, as new plans 75-06+.

**9. ⭐ Annotate the backlog — 20 real-swimmer sessions sit unscored (Phase 78, highest leverage).**
Titus 8, AlexGroup 9 (8 named testers), Jenna 2, Michael 1 — all 0 annotations. Labeling them converts
"generalises, probably" into a measured cross-swimmer number, and **unlocks backstroke** (annotate the 2
existing bk sessions: Tony + AlexGroup/Tate) and far more breaststroke. Then **re-run
`python tools/annotated_roster.py` + the 3 scorers** — the diagnostic is now a repeatable audit.

**10. ⛔ Backstroke breakout unvalidated (n=0) — Phase 78.** 2 labelable bk sessions exist (Tony,
AlexGroup/Tate). Stop claiming "back" in Phase 76's "free/**back**" until at least those are scored.
⚠ **WIDENED 2026-08-31 (Phase 87).** The same n=0 now blocks a second claim: `segment_strokes` and
the arm-asymmetry readout both run for backstroke on exactly freestyle's code path, so the toggle,
the two-colour pack and the Arm balance block all render for a bk session — and **nothing about any
of it has ever been checked against a human mark.** Inclusion was free; validation is still zero.
Annotating those 2 sessions now buys two phases at once.

**11. ⚠ Fly breakout thins outside Tony/Leo — Phase 78.** Chantee (post-tuning, 3 sessions) sits at
0.87 s median (0/3 ≤0.5 s) vs Tony 0.26 s / Leo 0.29 s. Re-check after item 9; don't oversell fly
breakout as "generalises."

**12. ⚠ `finish_s` is the weakest phase marker (MAE 2.76 s, worst 6.43 s) — Phase 78.** Inherited from
`detect_swim_window`; no phase has ever owned tuning it. Candidate for a dedicated pass. ⚠ Note the
2026-08-28 domain fact (PIPELINE.md): the mark **belongs before velocity reaches zero** — swimmers
drift into the wall after touching — so any retune must not chase stillness.

**13. ⚠ 75-06 AC-7 human-verify OWED.** The four phase sections have never been looked at on a live
session (portal is Supabase-auth-gated). Specifically owed: confirm no "coming soon" remains, hover
shows window provenance + the provisional note, provisional rows are not colored, and — the one thing
deliberately left to the user's eye — **judge whether ~23 new rows need grouping or collapse.**

**14. ⚠ ~15 sessions have an UNRESOLVABLE underwater window.** Every underwater-dependent metric
ceilings at 84/99 (`uw_*`, `breakout_vel_loss`, `phase_*_budget_underwater`, `vel_envelope_underwater`).
This is why a coach can open a session and find the whole Underwater panel blank with no inset chart.
Pre-existing (not caused by 75-06) and never diagnosed. Candidate for its own pass alongside item 12.

**15. 🟡 SHIPPED TO BACKEND, AWAITING THE APP BUILD (84-02 loop closed 2026-08-30; committed + pushed
2026-08-31). → [84-02-SUMMARY.md](phases/84-mobile-user-feedback/84-02-SUMMARY.md).**
✅ **The load-bearing deploy ordering is now MET.** Backend committed and pushed FIRST
(`b3c07e5`, `myswimcoach@main` → Railway), then the mobile half (`6b24c79`,
`swimnetics-mobile@main`). Because `/process` accepts `go_signal_s` before any app can send it,
there is **no gap in which a session loses its marker silently**.
🔴 **Still 0/99, and stays there until the EAS build ships** — the app that sends the field is not
built yet. ⚠ **No backfill is possible**: `reaction_time` fills only for sessions recorded *after*
the build lands, a permanent discontinuity `phaseBaseline.js` (last-5-same-stroke) will see as a
metric that simply begins one day. ⚠ The first device check must **judge the NUMBER, not just its
presence** — the coach's own thumb latency is inside it. Original entry below.
Backend done in 75-04
(`PUT /sessions/{id}/go-signal`); no UI writes to it, so 0/99 sessions carry a GO time.
⚠ **CORRECTED 2026-08-29 (Phase 84 discuss):** the "also needs the phone↔encoder clock sync that
75-04 deferred" clause is **STALE**. The mobile app has computed that correlation since Phase 47 —
`RecordScreen.js:446` derives `sessionStartPhoneMs = phoneNowMs − elapsedUs/1000` from the 8-byte
META reply, which is encoder t=0 on the phone clock. The only missing piece was ever the button.
**→ PLANNED as [84-02-PLAN.md](phases/84-mobile-user-feedback/84-02-PLAN.md), created 2026-08-29** (Phase 84 item 7, CONTEXT D8–D13): a silent GO marker pressed while recording is
live (both plain and video states), stashed as raw `Date.now()` and converted after META, sent as a
new `/process` form field rather than a follow-up `PUT` (item 2's silent-loss lesson). The Phase-41
race-start sequence is **switched off** with it (D9) — the phone speaker is inaudible poolside, so
the horn was a false affordance; that also removes the negative-`go_signal_s` problem, since the
blare fired *before* `writeCmd('START')`. ⚠ The resulting metric is a **within-coach relative**
number — the coach's thumb latency is inside it — and no backfill is possible.

**16. ❓ Are 5/10/15/20/25 m the right split points?** `splits_25m` fills on **2 of 99** sessions —
structurally, not by failure: the tether is waist-mounted, so a 25-yard lap (22.86 m) records only
~21.9 m of travel (PIPELINE.md). `splits_20m` is 56/99. Options: drop the 25 m split, move to four
splits, or re-anchor to yardage. **Not changed unilaterally — user decision.**

**17. Shape-anomaly detection needs a CROSS-SESSION baseline (83-03 finding, measured).** Per-lap
self-comparison is dead: median 7 cycles/lap makes the MAD gate fire on 75% of sessions at k=3.0 and
39% at k=8.0 — no usable threshold exists. The algorithm in `web/lib/cycleShape.js` is correct and
duration-invariant (12/12 scratch checks); only its **reference population** was wrong. The fix is to
build the median profile from the athlete's **last N same-stroke SESSIONS** — the same within-athlete
contrast `web/lib/phaseBaseline.js` already uses for every metric strip, and the SPC posture the
product doctrine asks for. Needs prior sessions' velocity arrays reachable from the browser, so it is
a **backend/data question, not a frontend one**. Probes: `scratch/shape_viability_probe.py`,
`scratch/shape_sweep_probe.py` (read-only, re-runnable).

**18. ⚠ Kick bands TILE their window — the first and last are not kicks (found 2026-08-29, 83-05 discuss).**
`segment_kick_bands` builds `edges = [i0, ...troughs..., i1]` ([metrics.py:926](../metrics.py)), so band 1
spans `underwater_start` → first trough (the **push-off glide**) and band N spans last trough →
`stroke_start` (the **breakout transition**). Only the interior bands are true trough-to-trough kicks.
Harmless in 83-02's banded inset — the bands simply tile — but it means the badge's "N kicks" **overcounts
by up to 2**, and any surface that compares bands to each other (83-05's overlay) shows ~2 of ~5 traces
departing for a reason that has nothing to do with the swimmer. ⚠ **CORRECTED 2026-08-29 (83-05 verify):
the "~2 of ~5" figure is worst-case, not typical** — the artifact is a FIXED cost of two bands, so its
visual weight scales inversely with kick count. On the live 15-kick session used for 83-05's AC-8 it is
2 of 15 and the overlay pack read as tight. The badge overcount and the defect are still real.
**Fix:** emit only interior spans and let
the inset draw honest grey for the glide and the breakout edge. Cost is Python + `SCHEMA_VERSION` bump +
backfill across the 63 sessions carrying bands, which is why 83-05 accepts the artifact rather than
absorbing a backend change (83-05 D8).

**19. Peak-alignment as an overlay axis mode (83-05, declined for that plan).** The overlay's
seconds mode anchors every trace on the cycle **start** — a segmentation artifact — so all error
accumulates rightward, which is the fan visible at the right of the underwater pack. Anchoring instead
on each cycle's **velocity peak** (the arm-pull, read from the signal itself) would make the spread real
stroke variation, keep durations honest (no rescaling, unlike normalized), and **largely dissolve 83-05
D5's accepted caveat** that auto-session spread may be segmentation rather than stroke. Align-CENTER was
considered and argued against: the midpoint inherits jitter from both boundaries and corresponds to no
physical event. Cost ~30 lines in `web/lib/cycleTraces.js` + a third toggle state; frontend only, no
schema. User declined for 83-05 — revisit if the pack ever reads too loose to judge.

**20. Portal alert chip still reads "changed (unclear)" while the site says "Normal" (Phase 85 D26/D27).**
The **gate already matches on both surfaces** — `flagVerdict` in `web/lib/phaseValence.js` returns
`flagged: false` for anything inside the band, so an alert already means out-of-range everywhere. What
does NOT match is the wording of the out-of-range-but-direction-ambiguous bucket:
`web/components/portal/phases/AlertSummary.js:38` labels it `changed (unclear)`, and D26 renames it
**"to review"**. One component, one string, deliberately deferred out of Phase 85 (D27, marketing-only
scope). ⚠ Note the marketing page shows **no example of that bucket at all**, an accepted
simplification, so a coach meets it first in the portal.

**21. ❓ Should `ratings.py`'s dead `provisional` flag be re-armed, retired, or left dormant?
(84-03 planning finding, 2026-08-30.)** `provisional = (thr_table is None) or (thr is None)`
(`ratings.py:206`) can never be True: `thr_table` falls back to breaststroke (`:251`) and all four
pillar primary keys have threshold rows. Phase 54 deliberately defused the `seg_reliable` gate that
used to drive it — because it made *every* pillar provisional and silenced the needs-attention list
entirely (`:201-204`) — and kept the parameter so restoring it is one line. Consequence today: three
provisional code paths in the mobile app and one in `summarize_team` are unreachable, and the app has
**no way to tell a coach that a reading came off unvalidated segmentation** even though
`segmentation_reliable` is still hardcoded `False` on the auto path. Three options, all real:
re-arm it and accept that nearly everything reads provisional; retire the flag and delete the dead
branches; or leave it dormant as the landing site for a future finer-grained trust signal. 84-03
handles it correctly by construction and **deliberately does not decide it** — this is a ratings
decision, not an indicator-vocabulary one. Related: [83-03's cut MAD classifier](#) and item 17 both
point the same way, at a cross-session trust baseline rather than a per-session boolean.


**22. ❓ `sessions.recorded_at` stores UPLOAD time, not swim time (found 2026-08-30, Phase 86 planning).**
`api.py` never sets it, so it falls back to the schema default `NOW()` — which fires when the row is
written, not when the swim happened. DATA-FLOW.md documents it as *"when swum"*, so the map and the
behaviour disagree. Usually harmless (upload follows the swim within minutes) but wrong whenever a
session is uploaded late from the queue, and it is the field a reader would reach for first when
looking for absolute time. Phase 86 **deliberately does not fix it**: `recorded_at` is already read by
history and baseline queries across 99 sessions, so changing its meaning is a library-wide
comparability break of the same class as the boundary backfills. 86-01 adds
`session_start_utc_ms` **beside** it rather than correcting it. Open question: correct `recorded_at`
to the true swim time once `session_start_utc_ms` exists (and accept the break), leave it as upload
time and rename/redocument it honestly, or keep both with the distinction written down. ⚠ Note it can
only ever be corrected for sessions recorded **after** Phase 86 ships — the older 99 have no other
record of when they were swum, so any fix creates a permanent discontinuity, the same shape as
`reaction_time` (item 15).

**23. 🟡 84-04's device verify (AC-4 + AC-5) DEFERRED TO THE EAS-BUILD BATCH — user call, 2026-08-30.**
The code is applied and statically green (see Phase 84-04 above): both `VelocityChart` responders now
answer `false` to a termination request, so the parent `ScrollView` can no longer steal a brush drag
mid-gesture. ⚠ **This lane does not technically need a build** — it is pure JS and Metro against the
installed dev build would prove it today — but the user chose to fold it into the one sitting that
verifies 84-01/84-02's genuinely build-gated items, so it now waits on the same build. What is owed
is **two things, not one**: (a) **AC-4**, the symptom is gone — a sideways brush drag survives
vertical drift on both the report card AND the post-recording results chart (G33's unreported
surface, which never had a scroll lock at all); and (b) **AC-5**, a *judgement*, not a pass/fail —
G36's accepted cost is two thin dead zones where a drag that STARTS on the 30 pt strip, or
horizontally on the chart body, can no longer scroll the page until the finger lifts. If that reads
wrong on the device, the fallback is pre-specified and needs no re-plan:
`onPanResponderTerminationRequest: (evt, g) => Math.abs(g.dy) > Math.abs(g.dx) * 2` in each config —
restores page-scroll-from-the-strip at the cost of reintroducing the original bug for a near-vertical
drag. Also worth 10 seconds in the same sitting: confirm **Video Overlay is unchanged** (G34 says it
has no responders attached at all, so any difference there means G34 is wrong).
⚠ `scratch/gesture_check.mjs` proves the CONFIGURATION only. It cannot see a gesture, and its banner
says so — a green run is not evidence for (a) or (b).

**24. 🔴 BLE DISCONNECTS DURING THE DATA DUMP (user-reported 2026-08-31, from pool testing).**
⚠ **This is NOT the failure Phase 74 was built for.** Phase 74 addressed a **stall** ("the end-of-dump
marker never arrived"); the new report is a **disconnect**. Phase 74's retained-buffer work makes a
disconnect *survivable* (a re-issued META → DUMP re-streams the session) but addresses no disconnect
**cause**. Different bug, same phase area.
✅ **Feedback loop BUILT, not yet run: `tools/dump_stress.py`** — drives the real META → DUMP → `0xEE`
handshake from the laptop over `bleak`, N cycles against one buffered session, and reports a
**disconnect rate** plus where each failure died (clustered = deterministic boundary; scattered =
timing/link). It never sends `CLEAR`, so Phase 74's retained buffer means you record **once** and
stress many. Its whole point is the phone-vs-firmware split: *drops here too* → firmware/link;
*clean here* → phone side.
🔴 **Blocked on two things:** (a) this PC's Bluetooth radio is OFF (`MediaTek Bluetooth Adapter →
Present: False`, `bthserv` Stopped) — hardware exists, just switched off; (b) the encoder must be
powered, in range, holding a buffered session.
⚠ **The single most discriminating measurement is a serial line at 115200:**
`[DUMP] Aborted at N/M — disconnected` → the ESP32 is alive and the link dropped cleanly;
a boot banner → the ESP32 **RESET**. Completely different causes.
⚠ **Instrumentation gap:** the firmware has **no `esp_reset_reason()`, no task-watchdog config, and no
brownout handling** (verified by grep) — so a reset is currently only inferable from the boot banner.
Three lines in `setup()` would make it explicit; worth adding at the next flash.
**Ranked, UNTESTED hypotheses** (each falsifiable):
1. **Bluedroid heap starvation** — `BLE_HEAP_HEADROOM` leaves the stack just **32 KB**; the sample
   buffer takes the rest (60 s ≈ 113 KB). *Predicts:* failure rate tracks recording LENGTH. Testable
   with no code change — dump a 10 s session vs a 55 s one.
2. **Supervision timeout** — firmware never calls `updateConnParams`; iOS picks them; 675 back-to-back
   indications with no latency margin + pool-deck 2.4 GHz contention. *Predicts:* failures scatter and
   worsen with distance.
3. **Phone-side re-render storm** — `RecordScreen.js:513` calls `setSampleCount` **once per packet**,
   ~675 React re-renders during a dump. *Predicts:* bleak clean, phone drops. This is the hypothesis
   `dump_stress.py` exists to kill.
4. **The dump loop never yields** — `dumpBuffer()` runs on the Arduino loopTask with no
   `delay`/`vTaskDelay`/`yield`; `loop()` does not return for ~20 s. ⚠ Ranked 4th because
   `notify(false)` blocks on a FreeRTOS semaphore, which *does* yield — the idle task should still feed
   the WDT. *Predicts:* a RESET in the serial log, not `[DUMP] Aborted`.
5. **Brownout** — motor + BLE on one supply. *Predicts:* correlates with battery level; vanishes on USB.
**Next action:** turn Bluetooth on, power the encoder with a buffered session, then
`python tools/dump_stress.py -n 25 --csv scratch/dump_runs.csv`. Belongs with **Phase 74**.

**25. 📋 The post-recording results page duplicates the report card (found 2026-08-31, not scoped).**
`RecordScreen`'s results view and `ReportCardScreen` render the **same Start Phase and Session cards
from effectively copy-pasted JSX**, and duplicate three helpers verbatim (`MetricItem`,
`computeTimeToX`, `TimeToX` — `RecordScreen.js:1184/1198/1210` ↔ `ReportCardScreen.js:625/639/651`).
The Efficiency cards have **already diverged** (Phase 60 replaced four scalars with `CycleCharts` on
the report card only), and the identical D10 comment in both files exists because they *did* disagree
and were synced by hand.
✅ **Two things only the results page can do**, and they are why it should shrink rather than vanish:
it renders from the in-memory `POST /process` response so it still shows a session whose **save
failed**, and its video button uses the **local** `videoUri` rather than the uploaded `video_path`
(which item 24's sibling — 84-05's 50 MB finding — shows is exactly when the upload may not exist yet).
🔴 **The structural cause: the results page has NO route to the report card.** `navigate('ReportCard')`
is called only from `AthleteDetailScreen` / `DashboardScreen` / `SessionHistoryScreen`; RecordScreen's
only `navigate` is to `VideoOverlay`. After a swim the coach's only exit is "Record Again", so the
results page grew a full analysis surface because it was a dead end.
**Sketch:** keep save status + failure paths + local video + capture confirmation; cut Start Phase /
Efficiency / TimeToX / the chart; **add a "View Report Card" button** (that one button is what makes the
cuts safe); extract the shared helpers. Also decide the fate of the ISO timestamp at
`RecordScreen.js:1155` — developer debug output on a coach-facing screen, which **Phase 86 is about to
make load-bearing**.
⚠ **Touches `RecordScreen.js`, so it must land AFTER Phase 84 is committed**, not inside it.

**26. ✅ RESOLVED 2026-08-31 — user applied `supabase/patch_14_session_clock.sql`, run reported clean.**
The three columns are live in the DB. ⚠ **Still unproven end-to-end:** AC-1/AC-5 remain verified only
against the mocked insert — no real row has carried a non-NULL `session_start_utc_ms` yet, because only
the phone can produce one and 86-02 has not shipped. The first real write is 86-02's own AC. Original
item text follows for the record.
**26-orig. USER ACTION: apply `supabase/patch_14_session_clock.sql` (86-01 UNIFY, 2026-08-31).**
Three nullable `sessions` columns — `session_start_utc_ms` BIGINT, `sync_error_ms` and
`clock_offset_ms` DOUBLE PRECISION, all `ADD COLUMN IF NOT EXISTS`. Standing pattern: the user runs
patches against the live DB (patch_11 / patch_12 precedent). **Until it runs, AC-1 and AC-5 are proven
only against the mocked insert** — nothing has been written to a real column. ✅ **Not urgent relative
to the deploy**: 86-01's conditional-subscript insert means `api.py` is safe to deploy first (the keys
are omitted entirely when absent), so patch and deploy can land in either order. Both must precede the
86-02 app build.

**27. ✅ RESOLVED 2026-08-31 — 86-01 committed `861040b`, pushed to `main`, Railway deploy VERIFIED.**
Not assumed: polled the deployed host until `GET /time` returned 200 (404 → 200 across the rollout,
`{"server_utc_ms":1788164715302}`), then confirmed the deployed `/openapi.json` lists
`session_start_utc_ms`, `sync_error_ms` and `clock_offset_ms` on `POST /process` and `/time` with **no
security requirement**. The backend is live **before** any 86-02 build exists, which is the ordering
the item existed to protect. ⚠ **The constraint still binds in the other direction for every future
change to these fields:** an app that sends a field an older backend does not know gets it dropped
**silently** — no 4xx, no log — and item 22's reasoning means no backfill can ever repair those rows.
Original item text follows for the record.
**27-orig. DEPLOY ORDERING: `api.py` must be live on Railway BEFORE the 86-02 app build (86-01 UNIFY).**
Identical in shape to 84-02's constraint. If an app that sends `session_start_utc_ms` /
`sync_error_ms` / `clock_offset_ms` reaches an older backend, **FastAPI drops the unknown form fields
silently** — no 4xx, no log, nothing. Sessions recorded in that gap lose their absolute start
permanently, and item 22's reasoning means there is **no backfill that could ever repair them**. ⚠ The
86-01 work is currently **uncommitted** (`M api.py`, `M tests/test_api.py`, `?? supabase/patch_14…`),
so it is not on Railway yet. Commit + push (auto-deploys) before 86-02 ships, and confirm with a
deployed `/openapi.json` fetch — the same check that lifted 86-01's own Phase-84 gate.
⚠ **CORRECTED 2026-08-31 (verified, not assumed):** the "uncommitted" clause above is **stale**.
`861040b feat(86-01): absolute session clock backend` (api.py + tests/test_api.py +
supabase/patch_14_session_clock.sql + the SUMMARY) is committed **and pushed** — `main` is level
with `origin/main`, and `git status` shows no `M api.py`. The deploy-ordering constraint itself
still stands and `patch_14` is still unapplied; only the "not pushed" half is resolved.


**28. 🔴 The AUTO-path arm asymmetry is uncorrelated with coach-mark truth — and is now ON SCREEN
(Phase 87, 2026-08-31).** Measured, not suspected: Pearson **r = −0.06**, median error **10.2
percentage points** against a **6.1% median signal**, agreeing on only **2 of the 7** most-lopsided
sessions (`scratch/_asym_auto_vs_truth.py`, 23 annotated freestyle sessions). The cause is **parity,
not precision** — un-paired wavelet boundaries land at 1.10× the coach's mark count and match 88% of
marks within 0.35 s, but **one extra or missing boundary flips the A/B side of every stroke after
it**. ⚠ **The user saw this measurement and chose to ship anyway** (87-01 D2 / 87-02 D8), marked only
by the existing `auto` chip and no warning banner — their call, recorded not softened. What changed
at 87-02 is the **exposure**: the number is no longer a stored key, it is a sentence a coach reads
(`Tempo — 6.2% apart · A slower`) on 20 of the 47 backfilled sessions. Two ways out, neither scoped:
annotate the session (coach marks make it exact — `segmentation_reliable` flips true), or fix the
parity by pairing the auto boundaries against a stroke-side prior. Until one of them lands, treat
`auto` asymmetry as a prompt to annotate, never as a finding.

**29. 🟡 DEPLOY ORDERING FOR PHASE 87 — backend must reach Railway before the frontend reaches
Vercel (87-02 UNIFY, 2026-08-31).** The backfill has **already been applied to the live DB** (47 of
101 sessions carry `metrics_json.strokes`), so the coach portal would find data even if only Vercel
deployed. But `POST /process` and `PUT /annotations` on the **deployed** Railway backend do not yet
emit `strokes`, so every session recorded or re-annotated in a frontend-only gap silently loses its
stroke array and its seven asymmetry keys — the same silent-drop shape as items 27 and 84-02, and
the toggle simply does not appear for them. Phase 87 is committed locally and **not pushed**;
push once, which auto-deploys both, then confirm on a freshly-uploaded freestyle session that the
toggle appears. ⚠ Do **not** push the frontend alone.

**30. 🔴 `lap_time_s` IS THE RECORDING DURATION, NOT A LAP TIME — and it is on the parent report
card (found 2026-09-01, Phase 90 planning).** [metrics.py:1870](../metrics.py) computes
`"lap_time_s": float(t[-1])` — the last timestamp of the trace. Measured across the 84 sessions that
clear Phase 90's 15 m guard: it disagrees with `finish_s − dive_start_s` on **84 of 84**, median
**5.75 s**, max **28.29 s**, and **19 of 84 read exactly 39.0 s** — the firmware's fixed record
length, not a swim. Where it surfaces today: `web/lib/reportMetrics.js` labels it **"Lap Time"** on
the tokenized **parent report** (`/report/[token]`), `GroupCompare` ranks A/B experiments on it,
`windowMetrics.js` re-derives a windowed version from it, and `api.py:1678` reads it. ⚠ Measured, not
inferred: **all 6 rows in the live `reports` table name `lap_time_s` in their `config_json`**, so
every parent report that exists carries this field. **Phase 90 routes around it** — 90-01 derives
`elapsed_s = finish_s − dive_start_s` (present on 84/84, median 15.1 s) and bans the string
`lap_time_s` from its module — but every other surface still shows the stored field. Options: rename
it honestly (`recording_duration_s`) and add a real `elapsed_s` to the registry with a backfill;
correct it in place and accept the library-wide comparability break (the 57 / 59-03 / 61-01 / 65 /
76-77 / 79 pattern); or fix the display surfaces web-only, the 88-02 precedent. ⚠ Whichever is
chosen, the parent-report surface is the one with a real audience and should not wait for the
backend decision.

## Recent arc (compressed)
- **75-01** skeleton — `MetricSpec` registry (37 specs) + `metrics_json.phases` jsonb + `POST /sessions/{id}/recompute` backfill seam.
- **75-02** — `detect_underwater_start` + 4 underwater window metrics; backfilled all 108 sessions.
- **75-03** (closed 2026-08-21) — `detect_underwater_kicks` + 7 kick metrics (hypothesis 1 approved);
  also `detect_swim_boundaries` + `stroke_start`/`finish` `detected` branch so backfill refreshes all
  four boundaries (auto `stroke_start` 3.56 s → 0.40 s).
- **76** — free/back breakout by kick-band **disappearance**.
- **77** — fly breakout by arm-cycle **appearance**.
- **79** — `dive_start` redefined to foot-of-surge (`detect_dive_start`, X=2.0); MAE 0.72 s → 0.15 s.
- **75-04** (closed 2026-08-21) — 10 Start metrics (peak/time-to-peak/max-accel, dive duration, 4 glide,
  break-into-kick, reaction_time) + `PUT /sessions/{id}/go-signal`; `streamline_drag` deferred. Suite 443.
- **83-02** (closed 2026-08-28) — Underwater inset draws one band per detected downkick. `phases.kick_bands`
  (schema 4) trough-to-trough, no new constant; reuses 83-01's lib unmodified; breaststroke gated off;
  63/81 non-breaststroke backfilled. D5 reversed: bands ride inside `phases` so all three write sites get
  them from one change and they cannot go stale against an annotated window. Peak dot removed everywhere.
- **83-01** (closed 2026-08-28) — Swimming inset draws one alternating blue/purple band per stored cycle
  over grey, + ticks, amber outlier halo, annotated-vs-auto badge, hover readout, bidirectional highlight
  with `CycleCharts`. New pure `web/lib/cycleBands.js` (83-02 reuses it for kicks unmodified). Two
  silent-failure bugs caught only by a render check: a shadowed prop, and Tailwind v4 tree-shaking
  `@theme` tokens read only via `var()` (→ `@theme static`).
- **75-06** (closed 2026-08-28) — 23 Swim + Whole metrics; registry complete at 46/47. `PhaseContext.cycles`
  + `provisional` flag (schema 3) = annotations-first for per-cycle metrics (43 trusted / 44 provisional
  live). Fixed `PUT /annotations` destroying `phases`, and a THIRD `PhaseContext` site in
  `tools/backfill_phases.py` that had left both per-cycle metrics 0/99. Suite 485.

- **83-05** (closed 2026-08-29) — Overlay panel: every cycle/kick on one shared axis beneath its inset,
  grey pack + wrapping number gutter with hover-preview and click-to-pin, three-surface highlight,
  seconds/normalized toggle with a gated median line. New `web/lib/cycleTraces.js` + `CycleOverlay.js`;
  the three protected components stayed byte-identical. Two live corrections: gutter wraps at 10 rows,
  and AC-3 was overridden so the breakout row highlights `n: 0`. New reusable **headless render-check
  harness** — the concrete answer to 83-01's "build and lint are blind to this".

- **85** (closed 2026-08-29, phase transitioned 1/1) — Marketing home page rebuilt around the
  race-phase report card, ten weeks after the site last moved. Real trace geometry baked at author
  time into `web/lib/marketingGeom.js` (whole lap decimated 1762 → 882 pts), so a public page makes
  no Supabase call; the Swimnetics mark enters the web surface; `Features.js` + `SampleChart.js`
  retired. New reusable gate `scratch/marketing_render_check.mjs` (45 checks) counts BOTH dash forms
  — the FAQ was 10 `&mdash;` entities to 2 literals, so every character-only grep had read it as
  clean — and headlessly renders the components for the 83-01 silent-failure classes.

- **83-03** (closed 2026-08-29) — Gold breakout band = the coach's streamline-break mark → their first
  stroke mark, a SYNTHETIC `n: 0` band, annotated sessions only. **The plan's shape-anomaly flag was
  MEASURED AND CUT**: at 7 cycles a lap the MAD gate fired on 75% of sessions (k=3.0) and 39% at k=8.0
  — no threshold separates clean from ragged. `web/lib/cycleShape.js` parked unwired; fix needs a
  cross-session baseline (item 17). First human-verify retracted; gold re-cut twice.

## Pointers
- **How it works:** [PIPELINE.md](../PIPELINE.md) — signal, phase model, detectors, metrics registry
- **Phase index / milestones:** [ROADMAP.md](ROADMAP.md)
- **Data map (stores, endpoints, jsonb):** [DATA-FLOW.md](../DATA-FLOW.md)
- **Requirements / product intent:** [PROJECT.md](PROJECT.md)
- **Full historical log:** [.paul/archive/STATE-history-2026-08-20.md](archive/STATE-history-2026-08-20.md)
