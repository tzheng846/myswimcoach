---
phase: 61-web-portal-rework
plan: 04
subsystem: ui
tags: [nextjs, react, recharts, compare, supabase]

requires:
  - phase: 61-01
    provides: the cycle semantics the per-cycle overlays summarize
  - phase: 61-02
    provides: TrendPanel and the legacy-vintage caption rule
provides:
  - web/lib/sessionName.js — deterministic mnemonic session labels
  - CompareChart as two stacked panels on true per-session sample rates + alignment nudge
  - CompareCycleCharts — per-cycle overlays + paired actual-value metric bars
affects: [61-05 video on compare]

tech-stack:
  added: []
  patterns:
    - "Derived display identity from a hash of the row id, never written back to the table"
    - "Scale paired bars by max(|a|,|b|) — signed metrics break max(a,b)"

key-files:
  created: [web/lib/sessionName.js, web/components/portal/CompareCycleCharts.js]
  modified: [web/components/portal/CompareChart.js, web/components/portal/CycleCharts.js, web/app/app/compare/page.js]
  deleted: [web/components/portal/MetricDeltaTable.js]

key-decisions:
  - "% deltas removed entirely at the checkpoint — actual values in paired bars instead"
  - "TrendPanel gained an optional multi-series form; single-series output preserved verbatim"
  - "Cycle series never padded/truncated/resampled to a common length"

patterns-established:
  - "Same-day disambiguation needs the TIME; the mnemonic makes a session sayable, not unique"

duration: ~40min including one checkpoint revision
started: 2026-08-11
completed: 2026-08-11
---

# 61-04 SUMMARY — Compare redesign (D8, D9, D11)

**Compare stopped being a page where three sessions from one morning looked identical, and where
both traces were drawn on a sample rate neither of them had.**

## Performance

| Metric | Value |
|---|---|
| Tasks | 3 auto + 1 checkpoint (1 revision round) |
| Files | 2 created, 3 modified, 1 deleted |
| Python | **0** — suite held at 274 |
| Build | clean at every task boundary |

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 same-day sessions distinguishable | **Pass** | Measured on the real corpus: the worst case is **19 sessions, one athlete, one day** — all 19 labels distinct; 62/62 distinct globally; deterministic across calls |
| AC-2 each trace on its own true rate | **Pass** | `fsA`/`fsB` read per row, NULL → 100 unchanged |
| AC-3 stacked panels, alignable | **Pass** | Offset shifts only panel B; reset restores; in-memory only, labelled "not saved" |
| AC-4 per-cycle replaces the table | **Pass** | 4 two-line panels; degradation verified over 7 shapes, zero throws |
| AC-5 nothing else regresses | **Pass** | Report-card tooltip preserved verbatim — see Deviation 2 |

## Measured, not assumed

**Label uniqueness.** ⚠ The mnemonic **alone collides 3 times in 62 sessions** — 40 adjectives ×
32 nouns = 1280 combinations, and the birthday paradox predicts ~1.4 at this size. **Uniqueness
comes from the appended TIME, not the words.** If the corpus reaches thousands the word lists need
widening; the labels would still be unique, but the mnemonics would repeat visibly.

**Bar scaling**, 7 cases including the one that would have broken it: `fatigue_index_pct` goes
**negative** when a swimmer speeds up through a swim (real value `−73.9`). Bars scale by
`max(|a|,|b|)`, not `max(a,b)` — the naive form renders a negative as zero-width or inverted.

**Per-cycle merge**, 7 shapes (equal, A-longer, B-longer, one empty, both empty, one null, both
null): zero throws, `null` where a session has no cycle N.

## ⚠ AC-2 fixes an absolute error, not a visible skew

Required by the plan to be stated plainly: of 62 stored sessions, **56 are 90.0 Hz and 6 are
NULL — none differ from each other.** `CompareChart.js:28`'s hardcoded 100 was therefore an ~11%
error applied *equally to both traces*, not the differential misalignment CLAUDE.md's "two sessions
may have two rates" note implies. This removes the last hardcoded rate on the web and is correct;
it did **not** fix a misalignment anyone could see, because that case does not occur in the data.

CLAUDE.md's note calling the assumption deliberate ("no single axis to draw them on") is superseded
— stacked panels give each series its own axis, which is precisely the answer.

## Deviations

**1. The % deltas were kept, then removed.** The plan allowed keeping a compact summary or dropping
them with a note; I kept them as a `A → B  +13.4%` strip. At the checkpoint the user asked for
*"two graphs of actual value - not difference"*, so the strip became **8 paired-bar cards showing
actual values**, and the percentage is gone entirely. `MetricDeltaTable`'s direction convention
(`normal`/`inverse`/`off`, ported from `app.py`) went with it — nothing now colours a change as
good or bad, which is a real reduction in interpretation and was the point.

⚠ **I asked before acting here.** "Two graphs… two separate lines" was ambiguous: the four
per-cycle panels *already* drew two lines of actual values, so the request could have meant they
were broken. They were not. Guessing would have produced the wrong work.

**2. ⚠ I broke a shipped surface and caught it in verification.** Extending `TrendPanel` to
multi-series changed the report card's tooltip from `Cycle 3: 1.42 m` on one line to a two-line
form — a violation of AC-5, on a surface this plan was not meant to touch. The single-series
branch now reproduces the original markup **verbatim**. Found by reading the diff, not by testing.

**3. `CompareCycleCharts.js` is a new file the plan did not name.** `files_modified` listed
`MetricDeltaTable.js` as if it would be edited in place; the replacement is a new component and the
old file was deleted. Same net effect, different file list.

## Files

| File | Change |
|---|---|
| `web/lib/sessionName.js` | **NEW** — FNV-1a over the session id → stable mnemonic; render-time only |
| `web/components/portal/CompareCycleCharts.js` | **NEW** — 4 two-line per-cycle panels + 8 paired-value bars |
| `web/components/portal/CompareChart.js` | Rebuilt: two stacked panels, per-session rates, offset, exported colours |
| `web/components/portal/CycleCharts.js` | `TrendPanel` exported + optional multi-series; single-series preserved |
| `web/app/app/compare/page.js` | New labels, extended queries, alignment control |
| `web/components/portal/MetricDeltaTable.js` | **DELETED** |

Skill audit: no `.paul/SPECIAL-FLOWS.md` — step skipped.

## Next phase readiness

**Ready:** 61-05 (D10, video on Compare) is unblocked. `COLOR_A`/`COLOR_B` are exported from
`CompareChart` specifically so the video column can colour-match without duplicating the hexes.

**Concerns**
- ⚠ **Not committed, not deployed.** Working tree carries this plan's 6 files.
- ⚠ Losing the % deltas removes the only place the portal said whether a change was *good*. If
  that turns out to matter, it returns as a visual, not a table.
- ⚠ Two `VideoPane` instances on one Compare page (61-05) each carry upload, frame-step, speed and
  sync controls — check density before committing to full reuse.

**Blockers:** None.

---
*Phase: 61-web-portal-rework, Plan: 04*
*Completed: 2026-08-11*
