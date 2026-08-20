# Phase Context

**Phase:** 75 — Report Card Revamp (Race-Phase Model)
**Discussed:** 2026-08-19 (`/paul:discuss`, 4 forks via AskUserQuestion + 1 clarification round)
**Status:** Ready for `/paul:plan`
**Decisions:** 14 (D1–D14).

⚠ **RESEQUENCED (user directive, 2026-08-19) → BACKEND-FIRST, 3 STEPS.** (1) **Skeleton** — a storage
slot + a metric **registry** + an integration endpoint, so metrics plug in later. (2) **Metrics** —
decide true feasibility, rank by effort tier (low/med/high), implement **one-by-one at the user's
approval**. (3) **UI** — the phase-organized report card, designed later; web first, iOS after. The
taxonomy below is the compute-everything target; the layout is now step 3, not the lead. **See Build
workflow below — this process must survive a new session.**

⚠ **NUMBERING:** taken as 75 (74 = ble-dump-reliability is the current max). Free to swap at plan time.

---

## Build workflow (user directive — 2026-08-19) — MUST persist across sessions

The user restructured this phase into three ORDERED steps. A fresh session must follow this exact
sequence and not let context loss re-plan it.

**Step 1 — Skeleton / integration (build first).**
- A **storage slot** for the new per-phase metrics: a `phases` object inside `sessions.metrics_json`
  (jsonb, **no migration**) — NOT a relational table (D15). Reaction-time's GO-signal = one nullable field.
- A metric **registry**: one declarative source of truth per metric — key, phase, unit, difficulty
  tier, `status: planned | implemented`, and a compute-function slot — so every metric "has a space"
  and plugs in one at a time.
- An **integration endpoint** = **recompute-from-stored-profiles** (`POST /sessions/{id}/recompute`):
  re-derive phase metrics from the stored velocity/distance/accel arrays (no raw-CSV reprocessing) so a
  metric added later backfills existing sessions, mirroring Phase 64's accel backfill (D16).

**Step 2 — Metrics (implement one-by-one, approval-gated).**
- Decide TRUE feasibility first (the ✅/🟡/🔶/⛔ tags below), then **rank by implementation effort:
  low / medium / high**.
- Implement **one metric at a time, each at the user's explicit approval** — never a batch.
- ⭐ **Reaction time is IN (D13).** Coach **"GO" button** = a poolside start system; `reaction_time =
  first-encoder-movement − GO`. Reserve the GO-signal slot + `reaction_time` (planned) in the skeleton
  now; the button UI is Step 3; needs phone↔encoder clock sync (same idea as the video-sync origin).

**Step 3 — Connect + UI (last).** The phase-organized report card / display, designed later under the
D7 alerting doctrine. Web first, iOS after.

**Meta (D14):** recorded here + in a `project` memory so a new session continues this unchanged.

---

## Why now

The user wants a "complete revamp of report card layout," and the reframe that drives it is to
organize the whole thing around the **phases of a swim** rather than the current flat surface
(four per-cycle stroke charts + Time-to-Distance). Verbatim structure the user gave, plus the
clarification round:

> *dive → underwaters (# kicks, distance/kick, kick consistency, kick-speed constancy, avg kick
> speed) → breakout stroke (specially marked) → strokes (everything in underwaters + intracycle
> velocity). Come up with more interesting ones. Don't worry if there's currently no support, like
> dolphin kick.*

> *(recording protocol)* *"Always dive/pushoff (will differentiate), underwater (or pulldown if
> breaststroke), swim (breakout labeled special but still counts as stroke). This will be universal.
> No drills, no extra stuff."*

> *(backend vs presentation)* *"From a backend perspective we should compute all the features we can.
> Presentation to the user is a separate problem, where 'attention allocation' comes into play. In
> presentation we maintain alerting doctrine, organized by phase of the swim."*

**The load-bearing discovery (verified in repo):** the phase model the user is describing **already
exists as a first-class, coach-correctable contract** — `annotations.py:8-16,44-49` defines
`dive_start_s → underwater_start_s → stroke_start_s → finish_s`, where `underwater_start_s` is
*"displayed as pulldown for breaststroke,"* `stroke_start_s` **is** the breakout, and *"THE FIRST
STROKE CYCLE CONTAINS THE BREAKOUT and is expected to be atypical"* (Phase 58). The user's universal
model maps onto it **one-to-one**. So this revamp READS an existing phase decomposition; it does not
invent one.

**What is NOT built:** Phase 65 fixed auto-breakout placement for free/back/fly (`65-02`, the
low-rail `f_ref` guard) but **65-03 — the underwater metrics + reporting — was never executed.**
`metrics.py` today emits **no** `underwater_duration_s`, `underwater_dist_m`, kick count, glide, or
IVV metric (grep-confirmed 2026-08-19); only the breaststroke-shaped `dive_duration_s` /
`pulldown_*` from `detect_initial_phase`. The report card surfaces essentially none of the phase
structure it already has access to.

---

## The universal phase model (maps 1:1 onto the existing annotation contract)

| # | Phase | Content by stroke | Existing boundary |
|---|-------|-------------------|-------------------|
| 1 | **Start** | **dive** (fly/back/free) *or* **push-off** — system differentiates | `dive_start_s` |
| 2 | **Underwater** | **dolphin kicks** (fly/back/free) *or* **pulldown** (breast) | `underwater_start_s` |
| 3 | **Swim** | strokes; the **first stroke = breakout**, marked-special but still a stroke | `stroke_start_s` (=breakout) … `finish_s` |

Exactly one of each per recording (one lap, no turns — D9). Push-off starts have no dive; the layout
must degrade (D5/open-call-3).

---

## Metric taxonomy (the SPEC deliverable — the backend compute-everything target)

Sensor reality: one **1-D axial trace** — velocity(t), distance(t), acceleration(t) at ~90 Hz
(accel stored since Phase 64/66). Feasibility tags:

- ✅ **computed today** (in `metrics_json` / stored profiles)
- 🟡 **cheap** — boundary/data already exists, just not computed (small `metrics.py` add, no new detector)
- 🔶 **new signal-processing** (a detector, peak-picker, or model-fit we don't have)
- ⛔ **not in a 1-D axial trace** — needs pose / depth / extra sensor; will not fake it

### Phase 1 — Start (dive | push-off)
| Metric | Feas | Note |
|---|---|---|
| Peak / entry velocity | ✅ | `max_vel_ms`; usually the race max |
| Time-to-peak velocity (explosiveness) | 🟡 | argmax of stored velocity — **user's dive #1** |
| Max acceleration off block/wall | 🟡 | peak of stored accel profile |
| Start type (dive vs push-off) | 🔶 | classification — dive has a large flight/entry spike |
| Dive duration | ✅/🔶 | `dive_duration_s` exists but is breaststroke-shaped; refine for the dolphin strokes |
| Glide duration / distance / avg speed | 🔶 | **user's dive #2**; needs a reliable entry→first-kick window |
| Glide speed-loss rate (deceleration) | 🔶 | **user's dive #2** — the drag / streamline signature |
| **Streamline drag coefficient** | 🔶 | fit v(t) decay → one "how tight is the streamline" number *(Claude add)* |
| **Break-into-kick velocity** | 🔶 | speed they start kicking at — glided too long / too short? *(Claude add)* |
| **Reaction time (coach "GO" button)** | 🔶 | **now feasible** — poolside start system; `reaction_time = first-movement − GO`; needs a GO-timestamp + phone↔encoder sync (D13) |

### Phase 2 — Underwater (dolphin kicks | breaststroke pulldown)
| Metric | Feas | Note |
|---|---|---|
| Underwater duration | 🟡 | boundaries exist — the deferred 65-03 metric |
| Underwater distance | 🟡 | deferred 65-03 metric; racing-critical (≤15 m) |
| Underwater avg speed | 🟡 | |
| **Underwater-speed ÷ surface-speed ratio** | 🟡 | is staying under paying off? *(Claude add)* |
| Kick count | 🔶 | **user's underwater #1** — peak-count the segment at ~2 Hz |
| Distance per kick | 🔶 | **user's underwater #2** |
| Kick tempo (kicks/s) | 🔶 | |
| Kick consistency (CV of interval / distance) | 🔶 | **user's underwater #3** |
| Intra-underwater velocity variation (smoothness) | 🔶 | **user's underwater #4** — oscillation amplitude vs mean |
| Avg / peak underwater speed per kick + decay | 🔶 | **user's underwater #5** + are the last kicks dying? *(Claude add)* |
| **First-kick impulse** | 🔶 | the first downkick is the most propulsive *(Claude add)* |
| Breaststroke pulldown peak vel / duration | ✅ | `pulldown_peak_vel_ms` / `pulldown_duration_s` (duration measured to trough — caveat) |
| Kick amplitude / body depth | ⛔ | needs pose/depth |

### Phase 3 — Swim (strokes; breakout = special first stroke)
| Metric | Feas | Note |
|---|---|---|
| Stroke rate, DPS, count, arm-peak, coast, cv_isi, cv_arm_peak, impulse, trough, fatigue | ✅ | already computed |
| **Intracyclic velocity variation (IVV)** | 🟡 | **user's "intracycle velocity"** — gold-standard efficiency metric; per-cycle velocity slices already exist *(cheap!)* |
| Breakout velocity | 🟡 | velocity at `stroke_start_s` |
| **Velocity-loss at breakout** | 🟡 | Δ underwater-mean → first-cycle-mean; the single most common place swimmers throw away the dive *(Claude add)* |
| Breakout stroke vs steady-state | 🟡 | first cycle vs the rest — did they carry dive speed in? |
| Split velocities (v @ 5/10/15/20/25 m) | ✅ | distance profile stored |
| Stroke-rate ↔ DPS tradeoff / coupling | ✅ | both exist; the relationship is the insight |
| Dead-spot timing within cycle | 🟡 | where the velocity min sits — glide timing *(Claude add)* |
| Accel asymmetry (propulsion vs decel time per cycle) | 🟡 | how much of the cycle is spent accelerating *(Claude add)* |
| Breathing-stroke velocity dip | 🔶 | exploratory — Phase 73 says breathing is visible in the trace |
| Left/right arm asymmetry | ⛔ | axial tether can't separate arms |

### Whole race (cross-phase)
| Metric | Feas | Note |
|---|---|---|
| **Phase time budget** (% of swim per phase) | 🟡 | "your underwater = 38% of this 25" *(Claude add)* |
| **Phase distance budget** (% of distance per phase) | 🟡 | *(Claude add)* |
| Velocity envelope (peak → decay by phase) | ✅ | |
| Whole-swim smoothness / jerk | 🟡 | ∫\|da/dt\| efficiency proxy *(Claude add)* |

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Universal 3-phase model: Start → Underwater → Swim**, mapping 1:1 onto the existing annotation contract (`dive_start_s / underwater_start_s / stroke_start_s / finish_s`). Breakout = the special-marked FIRST STROKE of Swim, **not** its own top-level phase (matches Phase 58: the first cycle contains the breakout). |
| **D2** | **Start differentiates dive vs push-off.** Both are captured; the system labels which. (Classification itself is 🔶 — see D5 for whether the label ships this phase.) |
| **D3** | **Underwater is one phase slot with stroke-dependent content** — dolphin kicks for free/back/fly, pulldown for breaststroke (`underwater_start_s` already renders as "pulldown" for breast). |
| **D4** | **Backend/presentation split (user's steer).** Backend computes EVERY feature the 1-D trace supports (the taxonomy above). Presentation is a *separate* problem governed by attention-allocation: **alerting doctrine, organized by phase** — not a raw number dump. |
| **D5** | **This phase = SPEC + LAYOUT (web).** Deliver the ratified taxonomy + a phase-organized web report card wiring up ✅ metrics and the clearly-cheap 🟡 ones (no new detector). The 🔶 heavy extraction (kick count/per-kick/tempo/consistency, glide-drag, start-type classify, breakout per-kick loss, breathing) is a NAMED FOLLOW-ON extraction phase. Exact cheap/new line = open-call-1. |
| **D6** | **Web first; iOS ports later.** Iterate the layout on web (no EAS builds). The mobile repo is separately owned and out of this phase's diff (same split as Phases 60/61/65-D10). |
| **D7** | **Display doctrine = within-athlete contrast / trend, NO absolute thresholds** (Phase 53 direction). Reinforced by data reality: underwater metrics have **zero** validation (breast n=2, back n=0, dolphin kicks n=0). Numbers *display*; they are not *graded* against absolute bands. |
| **D8** | **The revamp READS existing boundaries; it does not reinvent detection.** Phase 65-02 fixed auto-breakout for free/back/fly; boundaries are also coach-correctable via the annotate page. Inherited caveats: free/back ~1–2 s early residual (ROADMAP #69), backstroke unproven (n=0). Weak auto-detect degrades to the coach's annotation. |
| **D9** | **One lap, no turns, no drills** (user: "no drills, no extra stuff"; inherits Phase 65 D3). Exactly one Start / Underwater / Swim per recording; no mid-swim underwater. |
| **D10** | **Metrics ride in `metrics_json` (schemaless jsonb).** Any cheap 🟡 additions need no schema/migration and are available to both repos. If a 🟡 add changes a stored scalar, DB backfill is a separate task per the standing pattern (57 / 59-03 / 59-05 / 61-01 / 65). |
| **D11** | **Resequenced backend-first (user 2026-08-19): skeleton → metrics one-by-one → UI.** Supersedes the spec+layout lead ordering in D5; the taxonomy stays, the layout becomes step 3. |
| **D12** | **Metrics ship ONE AT A TIME at the user's explicit approval, after an effort-tier ranking (low/med/high).** Feasibility is decided first; no batch implementation. |
| **D13** | **Reaction time is feasible via a coach "GO" button** (poolside start system): `reaction_time = first-movement − GO-timestamp` on a shared clock. Upgrades it from ⛔ to a 🔶 metric with a mobile + clock-sync dependency (same idea as the video-sync origin). Skeleton reserves the GO-signal slot + `reaction_time` (status `planned`) now; the button UI is step 3. |
| **D14** | **This workflow + these instructions are RECORDED** (this CONTEXT + a `project` memory) so a new session continues the sequence unchanged rather than re-planning it. |
| **D15** | **Storage = `metrics_json.phases` (jsonb, no migration) + a code metric registry** (key / phase / unit / tier / `status` / compute-fn). No relational table (a table can't hold compute functions; the registry is the "define + provide space" skeleton). Reaction-time GO-signal = one nullable field. (user, 2026-08-19) |
| **D16** | **Integration endpoint = recompute-from-stored-profiles** (`POST /sessions/{id}/recompute`): re-derive phase metrics from the stored velocity/distance/accel arrays, no raw-CSV reprocessing — the seam for adding a metric later + backfilling existing sessions (mirrors Phase 64). (user, 2026-08-19) |
| **D17** | **ROADMAP cleanup = conflicts-only, remove-and-report** (user, 2026-08-19). |

---

## Scope

- **In (this phase, web-first):** ratify the taxonomy (spec); rebuild the web report card into
  Start / Underwater / Swim sections with the breakout marked in Swim; populate each section with
  ✅ + in-scope 🟡 metrics; 🔶 metrics shown as clearly-labeled "coming soon"; display honors
  alerting doctrine (within-athlete contrast, no absolute thresholds); graceful degradation when a
  phase is absent (push-off ⇒ no dive) or auto-detect is weak.
- **Out (named follow-on / deferred):** all 🔶 heavy extraction (kick count/per-kick/tempo/
  consistency, glide duration/drag-coefficient, start-type classification, breakout per-kick
  velocity-loss, breathing detection); iOS port; turns / multi-length / drills; absolute thresholds
  or cross-athlete norms for non-breast strokes (blocked on data); ⛔ pose/depth metrics.

---

## For `/paul:plan` — open design calls

1. **Where is the cheap/new line?** Which 🟡 metrics ship in THIS phase vs the follow-on. Candidates
   for "cheap, ship now" (boundaries/data already exist, no new detector): underwater duration /
   distance / avg-speed / surface-ratio, IVV (per-cycle slices exist), phase time+distance budget,
   breakout velocity + vs-steady-state, splits, dead-spot timing. Recommend shipping these so no
   section is empty; hold everything needing a peak-picker or model-fit.
2. **Layout / display design** (the part the user deferred: *"find ways to most effectively display
   these numbers"*). How the alerting doctrine renders per phase — the per-phase "look here" read,
   within-athlete contrast, trend vs the athlete's previous same-stroke session (the `ratings.py`
   baseline pattern already exists). This is a design sub-task; a mockup/artifact is likely worth it.
3. **Weak-auto-detect UX.** Backstroke is unproven (n=0) and free/back has a ~1–2 s early residual.
   How the Underwater section behaves when the boundary is untrusted — lean on the coach annotation,
   show a confidence/"needs review" affordance, or blank the section.
4. **Follow-on relationship to Phase 65.** Is the heavy extraction "Phase 65-03+" (its lineage) or a
   fresh Phase 76? Recommend a fresh phase — its scope (kicks, glide-drag, start-type across all
   strokes) is far broader than 65's breakout-detection bug.
5. **Start-type label (dive vs push-off).** Ship the *label* this phase (a coarse classifier is
   modest) or defer with the rest of the 🔶 work?

## Files likely in scope (this phase)

| File | Change |
|---|---|
| `web/app/app/sessions/[id]/page.js` | The layout revamp — reorganize into Start / Underwater / Swim sections; mark the breakout in Swim |
| `web/components/portal/*` (likely new) | Per-phase card / section components |
| `web/lib/reportMetrics.js` | REUSE / extend the metric catalog + `formatValue` |
| `metrics.py` | The in-scope 🟡 metric additions (if included per open-call-1) — additive to the session dict; breaststroke path unchanged |
| `tests/test_metrics.py` | New tests for any added metrics + regression guards (breaststroke byte-identical) |
| `api.py` | Likely none — metrics ride in `metrics_json`; confirm |

Untouched: the mobile repo, the Part-2 cycle segmenter, breaststroke detection, `detect_swim_window`
(65 owns it), `supabase/` schema.

## Success criteria

- [ ] The metric taxonomy is ratified as the backend compute-everything target — by phase,
      feasibility-tagged (this doc's spec section is the artifact).
- [ ] The web report card is reorganized into **Start / Underwater / Swim**, breakout marked in Swim.
- [ ] Each phase section is populated with ✅ + in-scope 🟡 metrics; 🔶 shown as clearly-marked
      "coming soon."
- [ ] Display honors alerting doctrine — within-athlete contrast / trend, **no absolute thresholds**.
- [ ] Degrades gracefully: push-off session (no dive) and untrusted underwater boundary both render
      sanely.
- [ ] `next build` green; new metric tests pass; breaststroke + existing-session behavior unchanged
      where not deliberately extended.
- [ ] The follow-on extraction phase is named and its scope captured (the 🔶 backlog).

## Carried out (recorded, not scoped here)

- Heavy per-phase extraction: kick count / distance-per-kick / tempo / consistency / per-kick decay,
  glide duration+drag-coefficient, start-type classification, breakout per-kick velocity-loss,
  breathing detection → the named follow-on phase (open-call-4).
- iOS report-card port (D6 — separate repo, EAS build).
- Absolute thresholds / cross-athlete norms for non-breast strokes (D7 — blocked on data; Phase 53).
- DB backfill if a shipped 🟡 metric re-scales stored values (D10 — standing separate-task pattern).
- ⛔ pose/depth metrics (kick amplitude, body angle, left/right asymmetry, true reaction time).
