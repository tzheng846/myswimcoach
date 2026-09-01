---
phase: 88-splits-picker-and-units
plan: 05
subsystem: ui
tags: [react, recharts, nextjs, signal-display, localstorage]

requires:
  - phase: 88-04
    provides: the `spanS` prop + `ReferenceArea` on VelocityChart and the `middleSlot` shape in page.js
  - phase: 61-02
    provides: the report card's trace section and `useTracePrefs`
provides:
  - "web/lib/rollingMean.js — pure null-aware centred moving average (O(n) prefix sums)"
  - "a grey dotted trend line over the raw velocity trace on the report card only"
  - "a persisted 0.00-3.00 s averaging window (swimnetics.smoothWindowS)"
affects: [75-09 unified trace, any future trend/smoothing surface, mobile chart parity]

tech-stack:
  added: []
  patterns:
    - "smooth at the native rate BEFORE a decimation stride, never after"
    - "a display-only rendering of an existing profile is a PLAN, not a phase — it stores nothing"

key-files:
  created: [web/lib/rollingMean.js, scratch/rolling_mean_check.mjs]
  modified: [web/lib/useTracePrefs.js, web/components/portal/VelocityChart.js, "web/app/app/sessions/[id]/page.js"]

key-decisions:
  - "D1: window in SECONDS, not cycles — a cycle unit would read the unreliable mean_isi_s"
  - "D3: rollingMean runs on the full-rate array, the RESULT is strided"
  - "Human-verify approved retroactively 2026-09-01 WITHOUT an on-screen check"

patterns-established:
  - "Source-text assertions in a harness can pin call ORDER (smoothing before striding) that a render test cannot see"

duration: unknown (applied in an unrecorded session)
started: 2026-08-31
completed: 2026-09-01
---

# Phase 88 Plan 05: Velocity Trend Overlay — Summary

**A grey dotted centred rolling mean over the report card's raw velocity trace, window on a persisted 0.00–3.00 s slider (default 1.00 s), smoothed at the native rate before `VelocityChart`'s 2000-point stride.**

## ⚠ How this loop was closed

This plan's APPLY **ran in an unrecorded session** and was committed as part of the phase commit
`e2c5814 feat(88): splits picker, units, trend` **without a SUMMARY**, so the loop stayed open while
the code shipped. UNIFY therefore **re-derived every claim from the diff and by re-running the
gates**, rather than trusting the plan or the commit message — the same
reconciliation-of-found-work posture used for 84-02 and 88-03.

🔴 **The blocking human-verify was never performed.** The commit message says so in its own words:
*"88-05's blocking human-verify was not performed — deferred at the user's direction."* The user
approved it retroactively on 2026-09-01 ("I thought it approved… approve it now"). **That approval
was given without anyone looking at the chart.** Every AC clause whose only possible evidence is
on-screen is marked **Partial / unverified** below, not Pass. Recorded, not softened.

## Performance

| Metric | Value |
|--------|-------|
| Applied | 2026-08-31 (commit `e2c5814`, 19:01:37 -0700) |
| Unified | 2026-09-01 |
| Tasks | 3 auto complete · 1 blocking checkpoint approved retroactively, unexecuted |
| Files created | 2 |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: trend on load, raw trace unchanged | **Partial** | Structure verified: default is `DEFAULT_SMOOTH_WINDOW_S = 1.0`, the raw `<Line>` is untouched in the diff, the slider label formats `1.00 s`. ⚠ The *drawn* line is unverified — recharts emits an empty wrapper under `renderToStaticMarkup`, which the harness itself flags. |
| AC-2: window means real seconds at the session's own rate | **Pass** | `rolling_mean_check.mjs` §"AC-2 … (D3)" — a synthetic 4000-point 90 Hz profile (where `step` becomes 2) proves smooth-then-stride ≠ stride-then-smooth, plus source-text assertions that `VelocityChart` calls `rollingMean` **before** the strided loop. |
| AC-3: 0.00 s removes the trend entirely | **Pass (mechanical)** | `!(windowS > 0)` returns a copy; the `<Line dataKey="m">` is gated on `smoothWindowS > 0`; harness asserts `smoothWindowS` absent === `0`, byte for byte. On-screen disappearance unverified. |
| AC-4: window persists across sessions and reloads | **Partial** | `swimnetics.smoothWindowS` added to `KEYS`; read in the **existing** effect (not a lazy initializer, per the file's own hydration comment); range-guarded to `[0, 3]` with the default surviving anything unparseable; `persist()` swallows storage errors. ⚠ The reload / session-change half was the human-verify's job and was not run. |
| AC-5: unit toggle scales the trend like the raw trace | **Pass (structural)** | `m` is computed as `Math.round(sm[i] * unitFactor * 1000) / 1000` — the same factor and the same precision as `v`, in the same loop. The two cannot diverge. Visual confirmation unverified. |
| AC-6: dropouts do not break the line | **Pass** | Prefix sums count nulls as 0/0, so `[1, null, 3]` over a 3-wide window gives **2**, not 1.33; an all-null window yields `null`, not NaN or 0. Harness §"AC-6". |
| AC-7: nothing else moved | **Pass** | `web/app/app/sessions/[id]/video/page.js` is **not in the commit at all** and passes no `smoothWindowS`. `AccelerationChart.js` contains zero references to `rollingMean` / `smoothWindowS` (D6 held). Y-axis domain untouched. `Brush`, cycle `ReferenceLine`s and 88-04's `spanS` `ReferenceArea` all intact. |

## Verification Results

| Check | Result |
|-------|--------|
| `node scratch/rolling_mean_check.mjs` | **39 passed, 0 failed** |
| `pytest tests/` | **566 passed**, 1 warning (unchanged — no Python in this plan's diff) |
| `cd web && npx next build` | clean, 20 routes |
| `npx eslint .` | 26 problems / 23 errors — **identical to the post-88-04 baseline, zero new** |
| `scratch/anchor_check.mjs` | 17/17 — **unedited** |
| `scratch/stroke_toggle_check.mjs` | 63/63 — unedited *since* 88-03's forced MAP line |
| `scratch/overlay_render_check.mjs` | 40/40 — **unedited** |
| `scratch/marketing_render_check.mjs` | 45/45 — **unedited** |
| `scratch/unit_check.mjs` | 63/63 |
| `scratch/split_picker_check.mjs` | 44/44 |
| working tree vs `HEAD` for `web/` + `scratch/` | clean — nothing was fixed up during UNIFY |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/rollingMean.js` | Created (53 lines) | Pure null-aware centred moving average via prefix sums; unknown `fsHz` falls back to `annotations.FS_HZ` = 100 |
| `scratch/rolling_mean_check.mjs` | Created (242 lines) | 39 assertions incl. the decimation trap and four source-text checks on call order |
| `web/lib/useTracePrefs.js` | Modified | `smoothWindowS` + `setSmoothWindowS`, `DEFAULT_SMOOTH_WINDOW_S = 1.0`, `MAX_SMOOTH_WINDOW_S = 3.0` |
| `web/components/portal/VelocityChart.js` | Modified | Optional `smoothWindowS` prop, `m` series in the data memo, second dotted `<Line>`, second tooltip row; `fsHz` becomes a memo dependency |
| `web/app/app/sessions/[id]/page.js` | Modified | "Trend window" range input inside the `showVelocity` branch; prop threaded to `VelocityChart` only |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Checkpoint not executed | 1 | Blocking gate approved retroactively without an on-screen check |
| Plan clause impossible as written | 1 | Human-verify step 8 references a card 88-04 deleted |
| Observation, not a defect | 1 | Trend inherits the raw trace's dropout gaps |

**Total impact:** no scope creep and no code deviation — the three auto tasks landed as specified.
The gap is in *evidence*, not implementation.

### 1. Human-verify step 8 could not hold as written

The plan's step 8 says *"Confirm the split-window shading from 88-04 **and the Time-to-Distance
marker** both still draw."* **Time-to-Distance was removed at 88-04's own verify**, one day after
88-02 re-anchored it. 88-05 was written against a pre-88-04 tree, so half that clause referenced a
card that no longer exists by the time this plan applied. The `markerTimeS` / `markerLabel` props
survive on both charts with **no caller on either route**; `page.js` replaced that state with
`spanS` / `spanLabel` and the diff records why in a comment. The split-window shading half of the
clause is confirmed by `split_picker_check` 44/44.

### 2. The trend line inherits the raw trace's gaps (observation)

`VelocityChart`'s strided loop does `if (velocity[i] == null) continue;` **before** pushing a point,
so at indices where the raw velocity is a dropout there is no data point at all — and therefore no
trend point either, even though `rollingMean` computed a perfectly valid mean there from the
surrounding window. The mean at every **plotted** point is correct, so AC-6 holds; the effect is
that the dotted line breaks wherever the red one does. Pre-existing loop behaviour, not introduced
here, and arguably the honest rendering. Noted so a future reader does not mistake it for a bug in
`rollingMean`.

### 3. Deliberate: `undefined`, not `null`, for a missing trend point

`m: sm && sm[i] != null ? … : undefined` — as the plan specified. Recharts treats the key's absence
as a gap, and `connectNulls={false}` keeps it from bridging one.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Approve the checkpoint retroactively, unexecuted | User's explicit direction, twice ("assume complete" at apply; "approve it now" at unify) | The visual behaviour of a coach-facing chart is **unconfirmed**. Carried into STATE as owed. |
| Keep `markerTimeS` / `markerLabel` on both charts | 88-02 D4 convention — name dead code, do not delete it | Two orphaned props on two components |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| No SUMMARY and no session record for an apply that had already shipped | Re-derived from `git show e2c5814`; re-ran all 7 harnesses + pytest + build from a clean tree |
| Plan written pre-88-04, verified post-88-04 | Reconciled explicitly above rather than silently marking step 8 pass |

## Next Phase Readiness

**Ready:**
- `web/lib/rollingMean.js` is pure and node-loadable — reusable by Phase 75-09's unified trace
- The "smooth before you stride" trap is pinned by a source-text assertion, so a future refactor
  that reorders it fails loudly

**Concerns:**
- 🔴 The on-screen behaviour of the trend line has **never been looked at**. The cheapest possible
  close: `cd web && npm run dev`, open a Chantee 2026-08-20 butterfly session, drag the slider
  0 → 1 → 3 s, flip metric/imperial, and open `/video` to confirm no dotted line.
- ⚠ **88-02's human-verify is also still owed** — it moves numbers a coach has already read
  (~0.4–0.5 s on 37 sessions, up to 12.39 s on 27 of them).
- ⚠ **OWED wording:** the anchor caveat line should read *"from your annotation"*; it still reads
  *"from your marks."* — `anchor_check` check 5 pins that exact string, so the fix is a one-word
  edit **plus** one line in the gate.
- iOS ships neither the trend nor the splits picker, and still carries its own head-waist
  Time-to-Distance — web and mobile now differ on the session screen in three ways.

**Blockers:** None.

---
*Phase: 88-splits-picker-and-units, Plan: 05*
*Completed: 2026-09-01*
