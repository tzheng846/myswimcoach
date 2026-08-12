# Phase Context

**Phase:** 61 — Web Portal Rework
**Discussed:** 2026-08-11 (`/paul:discuss`, ×5 rounds, 14 questions)
**Grilled:** 2026-08-11 (`/grilling`, 3 rounds + 4 measurement runs) — see P1b, D5, D15
**Status:** Ready for `/paul:plan`
**Decisions:** 15 (D1–D15). **Zero open blocking questions.**

⚠ **This is NOT a web-only phase.** D5 removes `ramp_up` from `metrics.py`, which moves
`stroke_count`, `stroke_rate_spm`, every `mean_*`/`cv_*`, `fatigue_index_pct` and
`outlier_cycle_count` on **every session ever recorded**. That is a **fourth comparability
break** after Phase 57's, 59-03's and 59-05's. The user was shown this consequence explicitly
in the option text and chose it anyway. It is their call, recorded, and it gets its own plan.

---

## Why now

The user asked for three web changes and then, mid-discussion, two more:

1. Add a button to see video + velocity overlay (*"so that it's not just hidden behind annotations"*)
2. Remove the table for graphs
3. Remove the data quality card
4. **Redesign Compare** — two separate line graphs, per-session nudge to line up, creative
   auto-names (*"it's almost impossible to tell the sessions apart when they're all the same
   date"*), metrics as graphs, video alongside
5. **Rework reports** — *"it feels like the numbers are coming out of nowhere. And also for the
   graphs the numbers don't reflect what's actually shown on graph"*

Asks 1–3 are the **mirror image of Phase 60**, which just did the same job on the phone. Ask 5
turned out to be a **real, mechanically explainable defect** that Phase 60 met on mobile and
deliberately did not fix. Ask 4 exposed **three separate defects** on the compare page.

Standing product direction: *"Note when trying to convey qualities, always try to use visuals."*
This is now a phase-level constraint, not a per-item preference.

---

## What was measured (2026-08-11, current source)

### P1 — "the numbers don't reflect the graph" is REAL, and the cause is exact

```
metrics.py:841-854   tag each cycle "steady" | "ramp_up"
                     steady_floor = 0.50 * percentile(arm_peak_vels, 75)
                     then: an isolated ramp_up between two steady cycles is promoted to steady
metrics.py:892       ss_cycles = [c for c in cycles if c.get("phase") == "steady"]
metrics.py:893       n_ss = len(ss_cycles)          → stroke_count IS the STEADY count
metrics.py:896       stroke_rate_spm = 60 / mean(steady durations)
metrics.py:912-917   every mean_* / cv_* over steady only
metrics.py:958-960   outlier_cycle_count over steady only  → feeds data_quality
```

`web/components/portal/CycleCharts.js` plots **all** cycles as dots and draws
`session.mean_arm_peak_vel_ms` as a `ReferenceLine` across them. The line is the mean of a
**subset**; the dots are the **full set**. Hence:

- the mean line does not sit at the visual average of the dots
- the stated `stroke_count` is lower than the number of dots

⚠ **Phase 60-01 hit both on mobile and recorded them as "two mismatches now knowingly ACCEPTED
and not to be fixed."** `swimnetics-mobile/src/components/CycleCharts.js:12` and `:139` still
carry that as source comments. D5 **retires that acceptance** — those two comments become wrong
and must be updated (see D5c).

### P1b — ⚠⚠ MEASURED 2026-08-11 (grilling session): `ramp_up` IS NOT RAMP-UP

An earlier draft of this file hedged that ramp-ups "may well be rare or zero on most real
sessions." **That was wrong, and so is the name.** Two independent measurements:

| | `raw/` (43 CSVs, untrusted pre-2026-06-22 corpus) | **live DB (67 sessions, 61 from August — TRUSTED)** |
|---|---|---|
| sessions with ≥1 non-steady cycle | 13/31 = **42%** | 21/54 = **39%** |
| non-steady cycles overall | 20/203 = 9.9% | — |
| position of excluded cycles | **0/13 a leading run; 13/13 scattered** | **median 0.91**; 59% fall in the final 20% of the swim |

⭐ **`ramp_up` is a velocity gate (`arm_peak < 0.50 × p75`), not a positional one, and what it
actually catches is the swimmer DECELERATING INTO THE WALL.** On `raw/`, 11 of 13 affected
sessions tag the *final* cycle; only 3 tag cycle 0. Examples: `carlos_fr_1` = `[9]` of 10,
`leo1` = `[18]` of 19, `leo2` = `[0, 16]` of 17, `leo4` = `[4, 5]` of 6. The live corpus agrees
independently (median normalized position **0.91**).

**The name is wrong everywhere it appears** — in `metrics.py`, in Phase 60's record, and in the
first draft of this file. Reproduce with the scratchpad scripts noted under "Measurement scripts".

**Why removing it detonates two metrics** — the wall-touch cycle becomes a stroke:
- it is a low outlier in the arm-peak array → `cv_arm_peak_vel` (a std/mean *ratio*) explodes
- it lands in `q4` of `fatigue_index_pct = (q1−q4)/q1` → sessions report severe fatigue that is
  really just "the swimmer touched the wall". `swim_t` −1.9% → **+99.3%**; `swim_o` +9.0% → **+100.0%**

**Distribution shift on the TRUSTED corpus** — note the median barely moves; the tail doubles:

| metric | median old → new | p90 old → new |
|---|---|---|
| `cv_arm_peak_vel` | 0.149 → 0.176 | **0.277 → 0.638** |
| `fatigue_index_pct` | 12.8 → 15.6 | **35.4 → 73.6** |

So D5 degrades the ~39% of sessions with excluded cycles, not all of them.

**Rating-band flips on `raw/`, all downward** — Consistency 5/11 flip and **11/11 end on
`needs_work`**; Endurance 8/11 flip and 7/11 end on `needs_work`. This is what D15 exists to fix.

### P2 — Compare has three separate defects, all confirmed in source

| # | Defect | Evidence |
|---|---|---|
| 1 | Both x-axes hardcoded to 100 Hz | `CompareChart.js:28` `t: Math.round(i)/100`; the page does not even **select** `sample_rate_hz` (`compare/page.js:93`, `:106`) |
| 2 | Same-day sessions are indistinguishable | `compare/page.js:8-15` — `sessionLabel` = `name — date`, and `name` is usually null, so every session from one day renders a **byte-identical string** |
| 3 | Session metrics only, no per-cycle detail | `MetricDeltaTable.js` is 8 session-level scalars in a table |

Defect 1 is **the same class of bug Phase 60-01 measured at −10% on mobile** and fixed there. It
is the last known-wrong time axis in the system. `CLAUDE.md` currently documents the 100 Hz
assumption here as *deliberate* ("two sessions may have two different rates, so there is no
single axis to draw them on") — **D9 supersedes that**, and the CLAUDE.md line must be updated.

⚠ `sessions.name` is coach-editable and PATCHable (`PATCH /sessions/{id}`). Auto-writing
generated names into it would **silently clobber names the coach typed**. D8 therefore derives
labels at render time and never writes.

### P3 — the video button needs no backend, but it drags 58-04 in with it

`GET /sessions/{id}/video-url` has existed since Phase 47. `VideoPane.js` already does
signed-URL playback, chart↔video seek, frame stepping, speed control, an upload branch, and a
manual ±0.1 s sync nudge with Save. Mobile 60-03 did this exact ask with **zero backend work**.

⚠ **`video_origin_s` is written by exactly ONE thing in the entire system** — the phone's
`VideoOverlayScreen`. A record-with-video session never opened there arrives on the web at
`origin_s = 0`, silently unsynced. Phase 58's close-out and Phase 60's both record 58-04 as
**"owed and homeless… It is WEB work… Needs a home in a future phase."** **This phase is that
home** (D2). Shipping a read-only video door without it would make the feature look broken on
exactly the sessions it exists for.

### P4 — Time to Distance is ALREADY annotation-driven on the web

The user's instinct was right, and the mechanism already exists end to end:

```
annotation.phases.dive_start_s
  → annotations.py:187-189   manual["baseline_end_idx"]
  → metrics.py:765-766       b_end
  → metrics.py:904           session.baseline_end_s
  → PUT /annotations rewrites metrics_json
  → web sessions/[id]/page.js:320 → TimeToX baselineEndS
```

**No web work is needed to make Time to Distance annotation-based — it already is.** The mobile
override the user described also already exists and behaves exactly as they specified:
`ReportCardScreen.js:553` is `baselineEndS={startTimeS ?? metrics.session?.baseline_end_s}` —
local marker wins, annotation-derived value is the fallback, and the marker never writes.
**Nothing to note as broken on mobile.**

⭐ **This retires a Phase 60 carried-out concern.** That close-out flagged *"three unconnected
notions of when the swim starts"* as an open Phase 53 input. The user's answer connects them into
a hierarchy — see D6.

⚠ Residual gap: the annotate page labels that mark **"Dive"**, and nothing anywhere tells the
coach that dragging it moves Time to Distance. The annotate page is out of scope (D14), so the
provenance is surfaced on the report card instead (D7).

### P5 — blast radius of the `ramp_up` removal (D5)

Every site that reads the cycle `phase` key:

| File | Lines | Note |
|---|---|---|
| `metrics.py` | 841-854, 892-893, 896, 912-917, 935-937, 958-960 | tagging + all aggregation |
| `metrics.py` | 1120, 1205, 1231, 1250 | `--plot` debug paths + legend |
| `coach.py` | 295, 301 | ⚠ **emits `ph: S=steady R=ramp_up` into the LLM prompt** — shared by `app.py` AND `api.py /coach/chat` |
| `app.py` | 354 | Streamlit steady filter |
| `inspect_cycles.py` | 46 | dev tool |
| `pipeline_view.py` | 169, 240, 303 | dev tool colouring |
| `tests/test_api.py` | 222, 224 | fixtures carry `"phase": "steady"` |

⭐ **The web reads it ZERO times.** No `ramp_up` or cycle-`phase` reference exists anywhere in
`web/`. So the charts never used the distinction — the mismatch was always population-vs-
population, never a rendering bug.

⚠ `outlier_cycle_count` (`metrics.py:958-960`) is computed over `ss_cycles`, so `data_quality`
moves too — even though D4 removes its card from the web, `SessionCard.js` still uses those
thresholds for the session-list indicator.

⚠ `ratings.py` is untouched by D5 but **AFFECTED** — pillar scores and the team needs-attention
list sit on `stroke_rate_spm` and the `mean_*`/`cv_*` family. Report the movement; do **not**
compensate. Phase 53 owns the thresholds.

---

## Goals

1. **Make the report card's numbers explainable.** Every figure should be traceable to something
   visible — the population it was computed over, the window it used, or the mark it came from.
2. **Give video a front door.** Session video reachable from the report card, correctly synced,
   without going through the annotation tool.
3. **Make Compare actually comparable.** True time axes, distinguishable session names,
   alignable traces, per-cycle visual detail, and video side by side.
4. **Close 58-04**, homeless since 2026-08-07.
5. **Remove the ramp-up/steady split** so the numbers and the graphs describe the same cycles.

---

## Decisions

### D1 — Video lives at a new route `/app/sessions/[id]/video`
A dedicated read-only page: `VideoPane` + `VelocityChart`, no annotation tools. The report card
gets a **`▶ Video + Velocity`** button. Mirrors mobile 60-03's `VideoOverlayScreen`. The annotate
page stays the labeling tool and is not the viewing surface.

### D2 — The web computes `video_origin_s` itself — and never overwrites a saved one
End-anchor formula: `origin = session_duration − video.duration`. Applies mobile 60-03's
**amended D11** verbatim: *use the stored origin if there is one, otherwise compute it and save
it.* **This closes 58-04.**
⚠ The computation lands in the shared `VideoPane`, so the annotate page inherits it — that is the
only way this phase touches annotate (D14) and it must stay backward-compatible.

### D3 — `CycleTable` is removed; `CycleCharts` grows to 4 panels
Mobile 60-01 parity: `dist_m`, `coast_fraction`, `duration_s`, `arm_peak_vel`, each captioned
with the mean or CV it summarizes.
⚠ **Impulse and Trough are dropped from the web entirely** — say so in the summary, do not let it
pass silently.
⚠ `CycleTable.js` also exports `outlierDurations`; grep confirms no other importer, so it goes
with the file.

### D4 — Data Quality removal, at mobile parity
Exactly mobile 60-01 D3 + D9 + D10: delete `DataQualityCard.js`; add a dropout strip that
appears **only above 5%**; demote `MetricGrid.js:65`'s `cv_isi > 0.8` **blackout** to a banner so
the two clients stop disagreeing about the same session.
⚠ The card is currently the only renderer of `data_quality.warnings` free text. Deciding where
(or whether) those surface is a plan-time call — do not drop them by accident.

### D5 — `ramp_up` is removed from `metrics.py` entirely  ⚠ FOURTH COMPARABILITY BREAK
**User decision, REAFFIRMED THREE TIMES** — at discussion, then again after the frequency and
band-flip measurements, then again after P1b established that `ramp_up` is really a wall-touch
filter. The consequences below were on screen each time. **This is settled; do not re-open it in
planning.** Every cycle counts. `stroke_count` becomes the total cycle count, not the steady count.

⚠ **Accepted, measured consequence:** the wall-touch cycle is now a stroke. On the trusted corpus
that doubles the p90 of both band-driving metrics (P1b). Two of four pillars would stop
discriminating — **D15 is the mitigation and is not optional.**
- **D5a** — all sites in the P5 table updated, including `coach.py`'s prompt line
- **D5b** — old → new recorded for every moved metric on a real corpus; `tools/backfill_preview.py`
  already exists for exactly this kind of quantification. **Nothing may be loosened or deleted
  from the test suite to make it green** — re-baseline with the movement recorded.
- **D5c** — `swimnetics-mobile/src/components/CycleCharts.js:12` and `:139` document the two
  mismatches as permanent; they become **wrong** and must be corrected. ⭐ This is an upside:
  D5 **resolves the mobile mismatch too**, retiring Phase 60-01's "accepted and not to be fixed."
- **D5d** — measure and report how many stored sessions actually had ramp-up cycles (P1), so the
  observable impact is known rather than assumed.
- ⚠ `ratings.py` untouched but affected. Report, do not compensate.

### D6 — One hierarchy for "when the swim starts"
**Annotation is authoritative → auto-detect is the fallback → the mobile marker is a local,
in-memory override that never writes.** Already true in code (P4); recorded here because Phase 60
left it open as an unresolved Phase 53 input. **No code change follows from this decision** — it
is a documentation and design-intent decision.

### D7 — The report card names the source of its Time-to-Distance start
One line under Time to Distance: `Start: 1.31 s — from your annotation` / `— auto-detected`.
When it is auto-detected, the label doubles as the fix: **`Set it yourself ›`** linking to
`/app/annotate/[id]`. Reuses the `recomputed_from_annotation` flag already on the page.
⚠ **No user-dropped start marker on the web.** The user ruled it out explicitly — the web already
has the annotate page, which is where a start gets set. Mobile's local marker exists only because
the phone has no annotate page.

### D8 — Compare session names: deterministic creative mnemonics from the session id
e.g. *Amber Otter*, *Copper Heron* — stable across renders because they hash the id.
⚠ **Derived at render time, never written to `sessions.name`** (P2), so coach-typed names are
never clobbered and it works retroactively on every stored session.

### D9 — Compare gets two stacked charts on true time axes, with a per-session nudge
Each session its own panel, its own real `sample_rate_hz` — **fixes the last known-wrong time
axis in the system** and supersedes the CLAUDE.md note calling the 100 Hz assumption deliberate.
Stacked with a shared x-axis so features line up vertically. A ± offset control shifts one
relative to the other; **in-memory only**, matching the mobile start marker's precedent.

### D10 — Compare video: right column, one per session, colour-matched
Charts stacked left, videos stacked right in the same order, each bordered and labelled in its
session's colour (A `#2196f3`, B `#f59e0b`). **Position, colour and label all agree** so
which-is-which is unambiguous. Shown only when that session has video.

### D11 — `MetricDeltaTable` is replaced by per-cycle line charts, both sessions overlaid
Same `TrendPanel` shape as the report card, two series per panel — showing **where in the swim**
the two sessions differ, not just that their averages differ.
⚠ The compare page does not fetch `metrics_json->cycles` today (it selects only
`metrics_json->session`) — that query changes.

### D12 — Prev/next session navigation on the report card
Move between an athlete's sessions without returning to the list.

### D13 — The video route shows `VideoPane`'s upload input when no video exists
So tripod footage can be attached from the report card, not only from the annotate page. Relevant
because Phase 58's **R1 is still unanswered** — whether ~40 arm-entry marks are placeable from
tripod footage — and lowering the friction to attach video serves it.

### D14 — The annotate page is otherwise out of scope
It works and it feeds the Phase 53/59 ground-truth corpus. Keeping it out means a video-view
failure cannot be confused with an annotation regression. **`VideoPane` is shared, so
backward-compatibility on the annotate page is an acceptance criterion, not an assumption.**

### D15 — Re-anchor the `ratings.py` bands D5 invalidates  ⚠ ADDED 2026-08-11 (grilling)
`THRESHOLDS["breaststroke"]` anchors `cv_arm_peak_vel` and `fatigue_index_pct` to the
**pre-D5** distribution. After D5 they no longer discriminate (P1b). Re-anchor from the measured
post-D5 distribution on the **live** corpus, not `raw/`.

Measured suggestion (percentiles of the post-D5 live distribution, both "lower is better"):

| metric | current anchors | measured post-D5 suggestion |
|---|---|---|
| `cv_arm_peak_vel` | worst .30 / ok .20 / good .10 / best .03 | worst **0.638** / ok **0.224** / good **0.080** / best **0.050** |
| `fatigue_index_pct` | worst 40 / ok 20 / good 8 / best 0 | worst **73.6** / ok **23.6** / good **5.3** / best **−15.8** |

These are **corpus percentiles, not coaching judgement** — label them as such. The table is
already marked DRAFT / breaststroke-only / "coach review owed", so re-anchoring invalidates
nothing that was ever validated.
⚠ `ratings.py` is therefore **in scope for this phase**, contrary to the pre-grilling draft which
said "untouched but affected."

### D16 — The video page's chart is a rolling playhead window  ⚠ RECORDED LATE 2026-08-11
Presets **1 / 2 / 5 s / All**, default 2 s, centred on the video playhead — mobile 60-03 parity.
**The user chose this during the discussion (round 2) and it was never written down as a numbered
decision**; it survived only as a passing mention in Constraints. Recorded here at 61-03 plan time
so the plan has a basis rather than an inference.
⚠ Phase 60's close-out records this as **specifically unverified on a device** — "whether the 2 s
rolling window reads well during playback" was the point of the original ask and was never
confirmed. The web is its first real read.

### Explicitly declined by the user
- CSV export button (`GET /sessions/{id}/export`, still caller-less system-wide)
- "Borrowed bands" caveat on non-breaststroke sessions (58-03's accepted gap — stays Phase 53's)
- 57-03 annotation batch queue
- A user-dropped start marker on the web (D7)

---

## Constraints and risks

### ⚠ D5 is a pipeline change inside a web phase
It must be its **own plan, in its own wave, committed separately.** This repo has documented
history of silent metric drift (Phases 51 / 52 / 57 / 59) and of refactors sharing a diff with
features (59's D14 lesson, 60-02's byte-identical gate). If the `ramp_up` removal shares a commit
with chart work, any unexpected movement becomes unattributable.

### ⚠ The web charts' correctness depends on D5 landing first
D3's four panels and D11's compare charts are only *consistent with* the session numbers once
`ss_cycles` is gone. Building them first means shipping the mismatch twice more.

### Deploy surfaces
- `metrics.py` / `coach.py` → **Railway** (backend deploy required)
- `web/` → **Vercel**
- `swimnetics-mobile` → doc-comment correction only (D5c); **no EAS build needed**

### Recharts is the web chart library
Unlike mobile (hand-rolled SVG), the web has recharts already wired — `Brush` is live at
`VelocityChart.js:137`. The rolling playhead window and the stacked compare charts are library
features here, not hand-rolled primitives.

### Unmeasured
- Whether the 2 s rolling playhead window reads well during playback — **Phase 60's close-out
  records this as specifically unverified on device**, so the web will be its first real read
- Whether the wall-touch cycle should be trimmed *positionally* instead (offered and declined at
  grilling; recorded because it is the natural follow-up if D15's re-anchor proves unstable)

### Incidental findings (NOT in scope — recorded so they aren't lost)
- `fetch_sessions.py:30` — `FS = 100.0` hardcoded with the comment "profiles stored at 100 Hz".
  Another stale pre-Phase-52 assumption, in a dev tool. Not fixed here.
- **6 of 67 live sessions still have NULL `sample_rate_hz`** — further motivation for the
  long-deferred Phase **52-02** backfill, consistent with Phase 60-01's finding that most NULL
  rows are ~90 Hz rather than ~100.

### Measurement scripts (scratchpad, reproduce before trusting the numbers above)
`measure_rampup.py` (frequency + metric movement over `raw/`), `measure_bands.py` (rating-band
flips), `rampup_position.py` (leading-run vs scattered), `live_distribution.py` (post-D5
distribution + suggested anchors over the live DB; read-only single SELECT). All read-only.
⚠ They live in the session scratchpad, not the repo — **re-create them under `tools/` if the plan
wants the measurement to be repeatable**, which D5b's "old → new recorded" requirement implies.

---

## Suggested plan structure

Sequential; they share `sessions/[id]/page.js` and the D5 semantics.

| Plan | Scope | Depends on |
|---|---|---|
| 61-01 | **D5 + D15** — remove `ramp_up` from the pipeline; re-anchor the two `ratings.py` bands; re-baseline tests; record old → new | — |
| 61-02 | **D3, D4, D7, D12** — report card rework | 61-01 |
| 61-03 | **D1, D2, D13** — new video route + 58-04 origin computation | 61-02 |
| 61-04 | **D8, D9, D10, D11** — Compare redesign | 61-01 |

⚠ **D5 and D15 belong in the SAME plan.** Splitting them ships a window in which two of four
pillars read `needs_work` on ~39% of sessions. They are one change with two halves.

---

## Files in scope

**Backend (61-01):** `metrics.py`, **`ratings.py` (D15)**, `coach.py`, `app.py`,
`inspect_cycles.py`, `pipeline_view.py`, `tests/test_metrics.py`, `tests/test_api.py`,
**`tests/test_ratings.py` (D15 moves banded values)**, `CLAUDE.md`
**Web:** `app/app/sessions/[id]/page.js`, NEW `app/app/sessions/[id]/video/page.js`,
`app/app/compare/page.js`, `components/portal/CycleCharts.js`, `components/portal/VideoPane.js`,
`components/portal/CompareChart.js`, `components/portal/MetricGrid.js`,
`components/portal/VelocityChart.js`, DELETE `components/portal/CycleTable.js`, DELETE
`components/portal/DataQualityCard.js`, replace `components/portal/MetricDeltaTable.js`
**Mobile:** `src/components/CycleCharts.js` — comment correction only (D5c)

---

## Success criteria

- [ ] Every number on the report card is traceable to something visible on screen
- [ ] `stroke_count` equals the number of dots plotted; the mean line sits on their average
- [ ] Video reachable from the report card in one click, correctly synced without manual nudging
- [ ] 58-04 closed — the web computes an origin when none is stored, and never overwrites one
- [ ] Two same-day sessions are distinguishable in the Compare dropdown at a glance
- [ ] Compare draws each session on its own true sample rate
- [ ] Old → new recorded for every metric D5 moves, on the **live** corpus (not `raw/`)
- [ ] After D15, Consistency and Endurance still **discriminate** — neither reads one band on
      more than ~60% of the live corpus (pre-D15 measurement: Consistency 11/11 `needs_work`)
- [ ] Annotate page behaviour unchanged (`VideoPane` backward-compatible)
- [ ] Test suite green with movement re-baselined, nothing loosened or deleted
