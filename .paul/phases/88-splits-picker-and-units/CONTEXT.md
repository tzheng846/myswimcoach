# Phase 88 — Selectable Splits + Unit Conversion (web report card)

*Created 2026-08-31 via `/paul:discuss` (3 question rounds). Handoff for `/paul:plan`.*

> ⚠ **Two things the user did not report were found during discussion and are larger than what
> they did report.** See F5 (three different anchors for "0 m" on one page, diverging by up to
> **12.4 s** on 27 of 99 sessions) and F6 (23 of 47 registry metrics never convert units).
> ⚠ **One thing the user did report was mis-priced by me during the discussion and is CHEAPER
> than I said.** See F4 — the backend head-waist path is already dead code.

## Why now

Two defects reported by the user against the **web session report card**
(`/app/sessions/[id]`), verbatim:

1. *"there's only splits for every 5m, and 20-25 which doesn't exist. The user should be able to
   select every 5 meters, like a toggle effect, and see what the avg velocity and time are. So
   they can do 0-10, or 5-15 or 0-15."*
2. *"when toggling yd vs meter the metrics don't seem to change."*

Both reproduce in code. Item 2 is the wider of the two.

## Goals

1. **Give the coach an arbitrary 5 m window**, not five fixed bins — select contiguous segments and
   read the average velocity and elapsed time for whatever span they picked.
2. **Stop showing a split that can never fill.** `splits_25m` is structurally unreachable on a
   25 yd swim; replace it with the part of the race that actually exists past 20 m.
3. **Make the yd/m toggle actually convert the metrics.** Today it converts the traces and the
   per-cycle surfaces and silently skips the entire phase-metric grid.
4. **Collapse the page onto one definition of "0 m".** It currently holds three.

## Decisions

| # | Decision | Notes |
|---|---|---|
| D1 | **All five split rows stay in the Swimming grid.** The picker is a **new card beside Time-to-Distance**, not a replacement for them and not inside the phase grid. | Keeps the usual-range bands and flags that the registry splits carry; the picker is additive. Splits then legitimately live in two places with two different jobs — fixed bins with history vs. an ad-hoc window for this swim. |
| D2 | **`splits_25m` is retired. A NEW registry key measures 20 m → `finish_s`.** | Not a relabel — a different function in `phase_metrics.py`. Needs a `POST /sessions/{id}/recompute` backfill across the library to fill 99 nulls. |
| D3 | **New key, not a reuse of `splits_25m`.** | Clean baseline history: the usual-range band only ever sees one definition. Old stored `splits_25m` values become orphaned, which is accepted. |
| D4 | **The picker shows this swim's numbers only — no usual-range baseline.** | Pure client-side from the already-loaded `distance_profile`. No new fetches, no backend. Deliberately gives up the alerting value on ad-hoc windows in exchange for a small, fast surface. |
| D5 | **Picker bins are unit-native.** Imperial gives true yard bins (5 yd = 4.572 m), matching `TimeToX`'s existing chip semantics. | The registry splits stay metre-binned, so the picker and the grid rows will disagree by name in imperial. Accepted — a yards-pool coach picking "15 m" is picking a distance no wall sits at. |
| D6 | **Raw `dive_start` is the single anchor for everything on the page.** `head_waist_m` stops being applied. | Resolves F5. This is the decision with the widest reach; see R1. |
| D7 | **`head_waist_m` is retired in computation only.** The DB column, the `POST /process` form field, the `POST /athletes` field and the athletes-page edit field all stay. | User's explicit call after being told the field would then edit a number nothing reads. Recorded, not softened — see R2. |
| D8 | **Picker interaction = toggle contiguous 5 m segments.** Clicking `0–5` then `10–15` fills `5–10` too; the selection can never be non-contiguous. | Chosen over a from/to boundary picker. Matches the user's own word, "toggle". |
| D9 | **Picker readout = average velocity + elapsed time, and it moves the trace marker** on the velocity chart above (the `onMarkerChange` path `TimeToX` already uses). | Distance-covered was offered and **declined**. See R5 — this makes the partial top segment's label load-bearing. |
| D10 | **The unit fix is scoped to the session report card's metric grid.** Other portal surfaces are not audited this phase. | Matches what was reported. Accepts that a metric may convert on this page and not on compare / group / parent-report pages. |
| D11 | **Unit conversion must move value, baseline median, baseline band, strip domain and unit label together.** | Not a style note — a correctness requirement. See R6. |

## What was verified in code (not assumed)

**F1 — the splits are backend registry metrics, not a frontend list.**
`phase_metrics.py:1048-1056` registers five `MetricSpec`s; `_split_velocity` (`phase_metrics.py:767`)
computes the mean velocity over the 5 m bin *ending* at N m, anchored at the distance sample at
`dive_start_s`. They render as five `RangeStrip` rows in the Swimming section, each with a
last-5-same-stroke usual-range band from `web/lib/phaseBaseline.js`.

**F2 — `splits_25m` is structurally unfillable on a 25 yd swim.**
The waist tether tops out at ≈21.9 m of travel for a 22.86 m lap (PROJECT.md constraint,
2026-08-28). Its `DISPLAY` entry at `PhaseReportCard.js:76` already carries
`emptyNote: "beyond this swim's distance"`, so this is a known-dead row rather than a
miscomputation — but it reads to a coach as a broken number, which is what was reported.

**F3 — an arbitrary-window picker needs no backend.**
`distance_profile` and the time array are both loaded on the page already
(`web/app/app/sessions/[id]/page.js:256-257`) and already handed to `TimeToX`.

**F4 — ⚠ the backend head-waist path is ALREADY DEAD CODE. I priced D6 too high during the
discussion and corrected it before writing this.**
- `metrics.time_to_distance` (`metrics.py:1415`) has **zero callers** anywhere in the repo or tests.
- `compute_session_metrics` accepts `head_waist_m` (`metrics.py:1656`) and **never uses it**;
  `api.py:228` dutifully passes it in.
- The **only live consumer is `TimeToX` on the web** (`web/components/portal/TimeToX.js`,
  fed from `page.js:366`).

Consequence: **D6 needs no recompute and touches no stored `metrics_json`.** The
originally-quoted "shifts numbers via the backend too" was wrong.

**F5 — ⚠ NOT REPORTED, and bigger than what was: the page holds THREE anchors for "0 m".**

| Surface | Anchor |
|---|---|
| The five registry splits | `phases.boundaries.dive_start_s` (raw) |
| `TimeToX` | `metrics_json.session.baseline_end_s`, **minus** `athlete.head_waist_m` |
| (after D6) the picker | `dive_start_s` (raw) |

Probed live against all 99 stored sessions:
- `dive_start_s` and `baseline_end_s` are present on **99/99** and differ on **69**.
- The median difference is **0.003 s** — index quantization, harmless.
- But **27 of 99 differ by more than 0.1 s**, and the tail is severe:
  **12.39 s** (udk), **12.27 s** and **11.62 s** (freestyle), **8.16 s** (butterfly), 3.22, 2.74, 1.36, 1.23, 0.89, 0.69 s.

So on roughly a quarter of the library, the split rows and the Time-to-Distance card directly
above them are measuring from instants **up to twelve seconds apart**, with nothing on screen
saying so. This is the substantial half of D6; the head-waist offset (F7) is the minor half.

**F6 — the unit toggle skips 23 of 47 registry metrics.**
`unit` correctly drives the velocity/acceleration traces (`page.js:291-293`), the cycle and kick
hover readouts (`PhaseReportCard.js:139,174`), `CycleCharts` and `TimeToX`. It does **not** reach
the metric grid: `PhaseReportCard.js:735-747` passes `r.disp.unit` (a hardcoded string from the
`DISPLAY` table) and `r.value` (raw) straight into `RangeStrip`. Counted from `DISPLAY`:

| Unit | Count | Converts today? |
|---|---|---|
| `m/s` | 17 | ❌ |
| `m` | 3 | ❌ |
| `m/s²` | 2 | ❌ |
| `m/s³` | 1 | ❌ |
| `s`, `%`, `×`, `/s`, dimensionless | 24 | ✅ correctly invariant |

**F7 — `head_waist_m` is set on exactly one athlete.**
Probed live: 10 athletes, **1** with a non-null non-zero value — **"Tony", 0.8 m, across 37 of the
99 sessions**. (`seed_demo_team.py` seeds 0.38–0.46 m, but those athletes are not in the live DB.)
0.8 m is consistent with PROJECT.md's "arm plus torso ≈ 1 m". At race speed the correction is worth
roughly **0.4–0.5 s** of Time-to-Distance.

**F8 — `TimeToX` is already ~80% of the requested picker.**
It has preset chips 5/10/15/20/25, hides presets the swim never reached, and is already
**unit-native** — imperial targets true yards (`TimeToX.js:44,62`). What it lacks is an arbitrary
*window* (it only measures from the start) and an average-velocity readout. The picker should be
built as a sibling that reuses these conventions, not as an independent invention.

## Risks

**R1 — D6 silently changes shipped numbers on 37 of the user's own sessions.**
Time-to-Distance shifts by 0.8 m of travel (~0.4–0.5 s) for athlete "Tony", plus whatever the
`baseline_end_s` → `dive_start_s` switch moves on the 27 divergent sessions (up to 12 s). No stored
data changes and no backfill is needed (F4), but a coach comparing against a remembered or
screenshotted reading will see a different number with no explanation on screen. **Planning should
decide whether the card states its anchor** — the page already has the precedent, the 61-02 D7
caveat line at `page.js:372`.

**R2 — D7 leaves a live edit field writing a value nothing reads.**
The athletes page (`web/app/app/athletes/page.js:137`) will still display and edit `head–waist`,
and `AddAthleteModal` will still collect it, after the last consumer stops applying it. The user
was told this is how dead settings survive and chose it anyway. Worth a code comment at the point
of retirement so the next reader does not "fix" it back.

**R3 — D2's new key has no usable baseline until the library is recomputed.**
`phaseBaseline` needs n≥2 prior same-stroke values to draw a band. Every session shows
"baseline building" until the backfill has run over enough of an athlete's history.

**R4 — "20 m → finish" spans different distances on different swims.**
On a 25 yd lap it is ~1.9 m; on a 50 m swim it is ~30 m. An athlete with a mixed-distance history
gets a usual-range band over unlike quantities. Planning must decide: gate the metric by swim
length, or accept the band and say so. A ~1.9 m window is also **few samples at ~89.5 Hz** —
a **minimum-span floor** is needed or the velocity will be noise.

**R5 — D9 declined the distance-covered readout, which makes the partial-segment label
load-bearing.**
On a 25 yd swim the top toggleable segment covers ~1.9 m, not 5 m. The average velocity over it is
*correct*; the label "20–25" is not. With no distance shown, the coach has no way to see the
window was short. Planning must either label partial segments honestly (e.g. "20–21.9") or refuse
to offer a segment the swim never filled — the same choice `TimeToX` already makes by hiding
unreachable presets (F8).

**R6 — converting the value without the band would invent false flags.**
`RangeStrip` positions the today-dot inside a domain computed from the baseline
(`computeDomain`, `PhaseReportCard.js:~198`), and `flagVerdict` compares value against band. A
value in yards against a band in metres reads as ~9% high on every length-dimensioned metric and
would flag metrics that did not move. This is why D11 is a correctness requirement, and why the
unit fix is not a one-line label swap.

**R7 — D10's scope leaves the portal internally inconsistent.**
The same metric will convert on the session report card and not on compare / group comparison /
parent report pages. Accepted this phase; worth a STATE item rather than silence.

## Open questions for `/paul:plan`

1. **Where does the picker get `dive_start_s` on a legacy session with no `phases`?** All 99 stored
   sessions currently have `phases` (probed), so this may be theoretically-only — but
   `PhaseReportCard` still carries a `!phases` legacy branch (`:790`), so the picker's card needs a
   defined behaviour there (most likely: do not render).
2. **Does D6 also re-anchor `TimeToX` itself onto `dive_start_s`, or only strip `head_waist_m`?**
   D6 says one anchor for everything, which implies both. F5 says the anchor swap is the larger
   effect. Confirm the plan does both, not just the head-waist half.
3. **What is the new remainder metric's key and label?** `splits_remainder` / "Split 20 m → finish"
   is the obvious pair; the `DISPLAY` entry needs a `desc` and an `emptyNote` for swims that never
   reach 20 m.
4. **Minimum span before the remainder metric reports at all** (R4) — and the same floor for the
   picker's partial top segment (R5). One constant, or two?
5. **Is the recompute backfill (D2) user-run at a blocking checkpoint**, following the 87-01
   precedent, or does the plan run it?
6. **Does the picker's marker replace or coexist with `TimeToX`'s marker?** Both write to the same
   `onMarkerChange`, and two cards competing for one marker on the chart is a live conflict, not a
   detail.
7. **Should the report card's grid state its anchor** now that it is changing (R1)?

## Out of scope

- Any change to the iOS app. Both defects are web-only as reported.
- Usual-range comparison on picker-selected windows (D4 declined it).
- Auditing units on compare / group comparison / parent report / alert summary (D10).
- Dropping the `head_waist_m` column, form field or UI (D7 keeps all three).
- The `dive_start_s` detector itself — Phase 79 redefined it and it is not reopened here. This
  phase changes which anchor the *page* reads, not how the anchor is found.

---

## Addendum — 2026-08-31: 88-05 is outside this document's charter

This CONTEXT was written from two user-reported defects on `/app/sessions/[id]` and everything
above scopes to them. **`88-05-PLAN.md` was appended afterwards, at the user's explicit direction,
and is neither of those defects.** It adds a grey dotted rolling-mean trend line over the raw
velocity trace with a persisted 0.00–3.00 s window slider.

It was placed in Phase 88 rather than opened as its own phase because it edits the same two files
as 88-04 (`VelocityChart.js`, `page.js`) on the same page, and because it stores nothing and adds
no registry metric — it is a second rendering of `velocity_profile`. It is recorded here so a later
reader does not have to reconcile a fifth plan against a four-plan charter and conclude the
document is stale. The decisions, risks, open questions and out-of-scope lists above are unchanged
and do **not** cover 88-05; its own `<decisions>` block (D1–D6) is self-contained.

Origin: a working prototype (`scratch/chantee_traces.html`) built against Chantee's three
2026-08-20 butterfly sessions, which showed that at raw ~90 Hz resolution the three swims are three
near-identical sawtooth walls, and at a ~1 s window their trends separate into something readable.
