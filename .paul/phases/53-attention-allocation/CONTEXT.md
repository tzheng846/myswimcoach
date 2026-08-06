# Phase Context

**Phase:** 53 — Attention Allocation (SPC detection engine)
**Generated:** 2026-08-03
**Status:** Ready for planning

---

## The reframe

**Before:** Swimnetics is a magnifying glass — it gives the coach the ability to comb through
stroke-level detail.

**Now:** nobody wants to hunt for a needle in a haystack. A head coach cannot track 30 swimmers
across a 2-hour practice, every day. The core value is **attention allocation**: the tool tells the
coach when something is going wrong *or going right* for a specific athlete. The detail view stays —
it is where the coach lands after an alert — but it is no longer the product.

Budget: roughly **90 seconds of analytical attention per athlete per week**. For a 30-athlete roster
that means the weekly artifact is a ranked list from which **most of the roster is absent**.

---

## The layer contract

| Layer | Question | Output |
|---|---|---|
| Measurement | Is this number trustworthy *for this session*? | gate — a metric that fails never reaches contrast |
| Contrast | Different from **what** reference? | signed deviation + the identity of the reference |
| Persistence | Has it held across sessions? | run-rule verdict, never a single-point delta |
| Co-occurrence | What moved **with** it? | the metric cluster, described |
| Synthesis (LLM) | How do I say this in one line? | phrasing only — cannot change the flag set |

**Hard boundary: stop at co-occurrence.** "DPS down 8%, tempo up 6%, speed flat, held 3 sessions" is
a description and is in scope. "Losing the catch" is a causal claim and is out. "Do sculling drills"
is prescription and is out. Both belong to the coach.

---

## Technical framing

- This is **statistical process control**, not classic anomaly detection. Within-athlete control
  charts, common-cause vs special-cause, run rules. Not outlier scoring, not a learned model.
- **LLMs belong in the synthesis/phrasing layer only, never the detection layer.** Detection must be
  deterministic and reproducible: the same session data always produces the same flag set,
  independent of any model call.
- **Determinism requirement:** the alert payload must be complete and human-readable *without* the
  LLM. A template fallback is mandatory, not a nicety. The LLM makes an alert legible; it never makes
  one exist or disappear.
- **Alerts are symmetric.** "Something going right" is a first-class output, not a byproduct. It is
  also the retention argument — it confirms to a coach that a change they made is working.
- Alerts carry their own evidence (reference used, n sessions in baseline, which run rule fired) so
  the coach can discount them. An alert the coach cannot audit is an alert they will stop trusting.

---

## Verified starting conditions

Checked against the repo on 2026-08-03, not taken from notes:

1. **The existing attention surface is inert.** `metrics.py:617` sets
   `segmentation_reliable = bool(manual_bounds)` — True only for hand-annotated sessions. That makes
   every pillar `provisional` (`ratings.py:176`), and `summarize_team` skips provisional pillars for
   both `needs_work` and `declined` (`ratings.py:298`). In production the team dashboard's
   needs-attention list can emit only `stale` and `never_tested`. **It has been a calendar reminder
   since Phase 37.**
2. **The trend has no noise model.** `ratings._trend` is ±5% vs a single prior session
   (`ratings.py:154-167`). No persistence, no σ. This is the classic false-alarm generator that SPC
   exists to replace.
3. **The `raw/` corpus is not usable as evidence.** Every file is dated 2026-05-13 → 2026-06-10. The
   BLE packet-loss fix (loss grew with sample count) and the warmup-transient fix both landed
   2026-06-22, and 44-03 was never device-verified. The whole corpus predates every encoder-integrity
   fix. User assessment: 2-3 files trustworthy at most. **50-01's "24/43 usable" was a structural
   check (parseable, long enough), not a data-integrity judgment.**
4. **The clock is wrong and may not be wrong by a constant.** `run_pipeline` decimates by an integer
   factor (~268.5/3 ≈ 89.5 Hz) while `annotations.py` and the api.py recompute path both assume
   exactly 100 Hz; `api.py:143` discards `_actual_fs` and `sessions` has no rate column (audit F2/F3).
   If the native rate varies per session then the decimated fs varies per session, and that variance
   lands in every time-derived metric as fake signal. **Unmeasured — this is a hypothesis to test,
   not a finding.**
5. **Prescription surfaces contradict the boundary.** `drills.py` (8 drills, tag-matched) is wired
   into `/coach/chat` as `recommend_drills`. `ratings.THRESHOLDS` asserts absolute breaststroke bands
   with no validation behind them. Noted, not scoped for deletion this phase (see Constraints).

---

## Decisions taken in discussion (2026-08-03)

| Decision | Choice |
|---|---|
| Alert cadence | **Weekly test set** — each athlete produces a tethered trial ~weekly |
| Throughput | **Under 2 min/athlete** end-to-end → one unit covers 30 swimmers in ~1 hour. **Hardware throughput is NOT a constraint** and is off the critical path |
| Target | **Demo-credible first, then true**, with the two explicitly separated |
| Roadmap scope | **Whole system** (analytics + measurement trust + collection + surface). Cull list of contradicting features NOT requested — note conflicts, don't delete |
| Validation data | User produces it personally (self + recruited friends) |
| Depth | **~10 sessions per swimmer, 1-2 swimmers** — real per-athlete series, not breadth |
| Spacing | **One single day, crank out 10 sessions.** User will inject known perturbations (deliberately slower, extra breaths) rather than wait for natural signal |
| Stroke | **Freestyle** — user override of the breaststroke recommendation; freestyle restriction must lift |
| Demo basis | **The real 10-session series**, not the Phase-50 synthetic team |
| Operator | **User, on site** for all collection this phase |
| Hardware readiness | **Unknown — needs checking.** Roadmap opens with a verification gate |

---

## Roadmap

### Track A — make one number trustworthy *(blocking; nothing else proceeds without it)*

- **A1. Hardware gate.** Flash 44-03, run a stationary trial, confirm the trace head starts at the
  true angle with no pulse and that firmware `# DUMP_SENT` == app Retrieved == `# TRACE n=`. Until
  this passes, no collected data counts. Rides the pending EAS build.
- **A2. Sample-rate contract — ALREADY PLANNED as Phase 52** (52-01 + 52-02, created 2026-08-03 in a
  parallel session). Persists `sessions.sample_rate_hz` (patch_09, nullable, no default; NULL → 100
  keeps existing rows byte-identical) and reads it across the 6 backend + 3 web consumers that
  currently assume 100. **52-02 measures and backfills — that is where "does fs vary per session?"
  gets answered.** Track A depends on 52; do not re-plan it here. **Touches api.py — sequences after
  51-02.**
- **A3. Collect.** One pool day, freestyle, video on, per the protocol below.
- **A4. Annotate all sessions** with the Phase-47 tool (~1 hour for 10). Yields three things at once:
  `segmentation_reliable=True`, metrics recomputed from human boundaries, and the 16-06 ground-truth
  export via `GET /annotations/export` / `fetch_annotations.py`.
- **A5. Saturation + repeatability analysis.** Two questions: (a) does the freestyle wavelet ridge
  rail at the 120-SPM ceiling? (b) which of the 18 session metrics have usable variance? Output is an
  **evidence-based cull list** of metrics that can carry an alert.

**A5 is the go/no-go for the entire phase.** If no metric survives it, Tracks B-D are moot — and that
is worth learning in two weeks rather than six months.

### Track B — the engine

Pure module, no I/O, no LLM, deterministic. Implements the four detection layers. Tuned against the
injected perturbations and reported with **both sensitivity and specificity** — catching the planted
change is only half the result; staying quiet on the unchanged trials is the other half. Symmetric
(wrong *and* right) from the first version.

### Track C — the surface

The 90-second artifact: ranked, mostly-empty, bidirectional, click-through to the trace. Plus the
synthesis layer — LLM phrases a flag it cannot select, with the deterministic template fallback.

### Track D — later, for truth

Real weekly spacing over ≥8 weeks (the only source of a genuine between-session noise floor);
16-06 segmenter tuning against the A4 ground truth; then a pilot team.

### Distance

- **Demo-credible:** Tracks A-C, gated on one pool day plus an hour of annotation. Weeks, not months
  — *if* A1 passes.
- **Actually true:** adds 8-10 weeks of calendar that cannot start until Track A is complete.

---

## Data collection protocol (A3) — draft, confirm before the pool day

- Freestyle, same distance every trial, same push-off, **do not re-clamp the wheel between trials**.
- 2 warm-up trials, not counted.
- **Baseline block: 10+ normal trials** (user decision 2026-08-03). At <2 min/trial that is ~20
  minutes of swimming. Still below the ~20-point SPC convention for stable limits, so limits will be
  wide — but enough to compute them at all, which 6 was not.
- **Effort is deliberately submaximal** (user decision 2026-08-03) — the swimmer will not be at max
  capacity, so fatigue is not expected to contribute drift across the series. This is what makes 10+
  consecutive trials viable. It also means the series measures *repeatability at controlled effort*,
  not performance variance — the noise floor it yields is correspondingly narrower than real
  competitive testing would produce.
- Injected perturbations interleaved *after* the baseline block, each followed by a normal trial to
  test whether the alert clears: e.g. deliberately slower (~10-15%), then normal; altered breathing
  pattern, then normal.
- **Video on for every trial** — annotation quality depends on it.
- **Log the perturbations to a separate file and do not read it while tuning the engine.** Otherwise
  you tune to the answer and the specificity number is worthless.

### Known limitations to record, not paper over

- A same-day series has no re-clamping and no day-to-day physiology, so its noise floor
  **understates** true session-to-session noise. Limits tuned on it will run too tight in real use
  and produce false alarms. Fine for the demo and for proving the detection logic; not a substitute
  for Track D.
- Fatigue is **ruled out by design** — effort stays submaximal (user decision). If a monotonic
  downward drift shows up anyway across the baseline block, that is an unmodelled effect and must be
  investigated before any limit is trusted, not explained away.
- n=1-2 swimmers is one or two replications of the go/no-go, not a population result.

---

## Constraints

- **Do not delete the contradicting features this phase.** User chose whole-system scope *without*
  the cull list. `drills.py`, `recommend_drills`, and `ratings.THRESHOLDS` conflict with the boundary
  and should be noted in the plan, not removed.
- **Detection layer stays LLM-free.** No exceptions, including "just for ranking."
- **Phase 51 is being applied concurrently in another environment.** It modifies `api.py`, `tools/`,
  `supabase/live_schema.json`, and `tests/`. Any Track-A work touching `api.py` (notably A2) must
  sequence after 51-02 lands or expect conflicts.
- Backend pipeline is not rewritten: `vel_acc_extraction.py` + `metrics.py` stay.

---

## Supersedes / re-scopes

- **Phase 50 (Demo Team & Synthetic History) — PAUSED.** The demo now runs on the real 10-session
  series, not the synthetic 12-athlete team. Its source CSVs are the untrusted pre-fix corpus.
  `seed_demo_team.py` (565 lines) remains **untracked and the only copy — commit it regardless.** If
  a team-scale demo is wanted later, reseed it from clean sessions; the seeder is largely agnostic to
  which CSVs it eats, so that is a source swap rather than a rewrite.
- **"Freestyle unlock" as previously scoped is superseded.** The Phase-48 batch item 3
  ([48-01-PLAN.md:165](../48-athlete-create-fix/48-01-PLAN.md:165)) was: port breaststroke
  `THRESHOLDS` to all strokes, drop `provisional`, flip `isAnalyticsReady` to always-true. That
  asserts unvalidated bands onto freestyle. **Within-athlete contrast needs no thresholds at all** —
  the reframe makes freestyle cheaper, not harder. What freestyle actually needs is a segmenter whose
  output is *repeatable*, not *accurate*: a consistently-biased segmenter still detects drift.
  **Exception:** ceiling-railing is saturation, not bias — a railed metric reads constant, has zero
  variance, and can never show drift. A5 must check for it.
- **Phase 52 (sample-rate contract)** — planned 2026-08-03 in a parallel session (52-01 fix + 52-02
  measure/backfill). **Track A depends on it; A2 is not separate work.**
- **16-06 (wavelet tuning)** has been waiting on "freestyle data available" since 2026-06-12. A3+A4
  produce exactly that. Knobs recorded at `STATE.md:1777`: `_PERIOD_MIN/MAX_S`,
  `_RIDGE_JUMP_PENALTY`, `_RIDGE_LOW_BAND_BIAS`.

---

## Open questions for planning

1. ~~How many baseline trials?~~ **RESOLVED 2026-08-03 — 10+.**
2. ~~Fatigue: positive control or confound?~~ **RESOLVED 2026-08-03 — neither; effort stays
   submaximal so fatigue should not contribute. Treat any observed drift as unmodelled.**
3. Which reference does the contrast layer use first — within-athlete only, or within-athlete plus a
   peer reference for cold-start athletes? (Peer contrast answers a different question and risks
   being read as a ranking.)
4. Which run rules? Classic Western Electric is the obvious starting set, but with a 6-10 point
   baseline most of them cannot fire — the rule set may need to be chosen *after* A5.
5. Where does the alert land — rewrite the existing (inert) needs-attention path, or a new weekly
   digest? Deferred deliberately; decide once the engine's real output is visible.
6. ~~Does A2 need a `sessions` schema change or can fs live in `metrics_json`?~~ **RESOLVED** —
   Phase 52 chose `sessions.sample_rate_hz` (patch_09, nullable, NULL → 100).

---

*Created by /paul:discuss 2026-08-03. Consumed by /paul:plan.*
