# Phase Context

**Phase:** 73 — Group Comparison (A/B experiments on Compare)
**Discussed:** 2026-08-19 (`/paul:discuss`, 3 forks via AskUserQuestion)
**Status:** Ready for `/paul:plan`
**Decisions:** 11 (D1–D11). Web-only, metrics-first, honest-with-tiny-n. No backend/schema.

⚠ **NUMBERING:** taken as 73. Phase 72 is reserved for the tablet-responsive annotate-hub candidate
(noted in Phase 71's CONTEXT/PROJECT footer). If neither is built yet when planning, the numbers are
free to swap — but this doc + dir own 73.

---

## Why now

The Compare page today is strictly **swim vs swim** (`web/app/app/compare/page.js`: two pickers → two
velocity traces + per-cycle paired bars + optional video, baseline = older session). The user wants to
run **controlled A/B experiments** — put a GROUP of swims under condition A against a GROUP under
condition B and get a fast, honest read on whether the conditions differ. Verbatim intent:

> *"compare two groups of swims … technique A three times and technique B three more times … does
> breathing matter? I do three swims without breathing and three more with breathing. I want to be
> able to easily tell the difference between the two. And if there is, in fact, a difference [where]."*

And the explicit anti-goal:

> *"if we just list all the velocity traces, it's gonna be very busy and almost too much information …
> the metrics will give much more info without being overbearing."*

**The reframe that settles the design:** the deliverable is not a trace, it is a **per-metric verdict**
— for each metric, do the two groups pull apart or overlap? That is exactly the project's
"attention-allocation" north star (**alert whether there's a difference, and where** — not detail-comb),
and within-athlete contrast needs **no absolute thresholds** (the Phase 53 direction).

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Purpose = an A/B experiment tool.** Compare two GROUPS of swims and answer "is there a difference, and on which metrics?" The unit of comparison is a **metric**, not a trace. |
| **D2** | **Metrics-first, traces out (V1).** No overlaid velocity traces — the user's own steer (6 curves = noise). The per-metric row carries the signal. |
| **D3** | **Per-metric row = strip/dot plot + delta + cue.** For each metric: each swim is a **dot** on a small horizontal strip (colored by group), the **group means** marked, the **delta** shown direction-aware, reusing the existing `web/lib/reportMetrics.js` catalog (avg speed, top speed, stroke rate, DPS, lap time, consistency) + `formatValue`. The coach SEES separation vs overlap in one glance. |
| **D4** | **NO p-values / significance test (Claude pushed back; user agreed).** n=3 per group makes a t-test fragile and a p-value falsely authoritative. Show the honest distribution (dots), means, delta, and a plain **"clear separation / overlapping"** cue instead. |
| **D5** | **One athlete per comparison** (both groups are the same swimmer's swims — the "does breathing matter for ME" case). Cross-athlete/squad pooling deferred (adds between-swimmer variance that muddies small-n). |
| **D6** | **Same stroke enforced within a comparison.** Cross-stroke metrics (breaststroke DPS vs fly DPS) are not comparable — the picker restricts/warns to one stroke. |
| **D7** | **Two groups in V1, built to generalize to ≤5.** Model groups as an ARRAY; render 2 now; adding groups later is a UI flip, not a rewrite. |
| **D8** | **Ephemeral groups + coach-typed labels.** No saved-experiment table — the coach picks sessions into Group A / Group B each visit and labels them ("No breath" / "With breath") so the read is meaningful. Saved/named experiments = a future schema-bearing phase. |
| **D9** | **Metrics only in V1 (traces deferred).** A group-average velocity trace (mean ±SD band per group — 2 clean traces, not 6) was offered and DEFERRED: it needs resampling swims of different durations/rates onto a common grid, with real interpretation questions. V2 candidate. |
| **D10** | **Web-only; no backend, no schema.** Reuse the Compare pattern exactly: supabase-js reads of each session's `metrics_json->session` scalars (RLS), all group statistics computed **client-side**. Surfaced as a **"Groups" mode toggle on `/app/compare`** (the user said "expand the comparison section"), not a separate nav item. |
| **D11** | **LLM plain-English summary = deferred V2.** A one-liner ("breathing lowered stroke rate but not speed") fits the "LLM in the phrasing layer only" rule, but is not V1. |

---

## Scope

- **In (V1, web-only):** a "Groups" mode on Compare; two labeled groups of one athlete's same-stroke
  sessions (multi-select); a per-metric comparison over the `REPORT_METRICS` set — group means, each
  swim as a dot, direction-aware delta, and an honest clear/overlapping separation cue; group data
  modeled as an array (≤5-ready).
- **Out (deferred):** p-values/significance tests (D4); traces / group-average trace (D9); cross-athlete
  groups (D5); saved/named experiments + any schema (D8); LLM summary (D11); more than 2 groups rendered.

---

## For `/paul:plan` — open design calls

1. **Separation-cue rule.** How "clear vs overlapping" is computed. Recommend the simplest honest one:
   the two groups' **[mean ± 1 SD] bands** don't overlap → "clear", else "overlapping" (needs ≥2 swims
   per group for an SD; with n=1 show the dot, suppress the cue). Alternatives: min–max range overlap, or
   a coarse effect-size (|Δmean| / pooled SD) bucketed to negligible/small/large in words.
2. **Group-selection UX.** Multi-select checklist per group vs add-from-a-searchable-list; must prevent
   the same session landing in both groups, and lock the stroke to the first pick (D6).
3. **Metric set.** The 6 `REPORT_METRICS` for V1 (recommended, matches the report card), or add
   `fatigue_index_pct` / `mean_coast_fraction`.
4. **Placement.** Mode toggle on `/app/compare` (recommended) vs a `/app/compare/groups` sub-route.
5. **Unequal / tiny n.** Allow 3-vs-2 etc.; require ≥1 per group to render, ≥2 for the separation cue.

## Files likely in scope

| File | Change |
|---|---|
| `web/app/app/compare/page.js` | Add a "Groups" mode (toggle) alongside the existing two-swim mode; group pickers (athlete → multi-select same-stroke sessions ×2, labels). |
| `web/components/portal/GroupCompare.js` (likely new) | The groups view: fetch each group's `metrics_json->session`, compute per-metric group stats client-side, render the rows. |
| `web/components/portal/GroupMetricRow.js` / a small strip-plot (likely new) | Per-metric dot strip (swims as dots by group) + means + delta + separation cue. |
| `web/lib/reportMetrics.js` | REUSE (metric catalog + `formatValue`); maybe extend the set (open call #3). |
| `web/lib/sessionName.js` | REUSE (`sessionLabel`/`displayName`) for the session multi-select + group members. |

Untouched: `api.py` / all endpoints, the signal pipeline / `metrics.py`, mobile, the existing two-swim
Compare behavior (the new mode sits beside it).

## Success criteria

- [ ] The coach picks **two labeled groups** of one athlete's **same-stroke** swims and, per metric,
      sees both **group means**, **every swim as a dot**, the **delta**, and an honest
      **clear/overlapping** cue — telling at a glance whether the conditions differ and where.
- [ ] **No p-values**; tiny-n honesty preserved (D4).
- [ ] **Metrics only** — no traces (D2/D9).
- [ ] **Web-only** — no backend/schema change; reuses the supabase-read + client-stats Compare pattern;
      build green.
- [ ] Group data is an **array** so ≤5 groups is a later flip, not a rewrite (D7).
