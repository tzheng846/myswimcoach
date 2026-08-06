# 39-03 SUMMARY — Pillar explainer + remove impulse + athlete limit + trend relabel

**Status:** Code-complete; device verify DEFERRED. iOS export green (3.2MB); `pytest tests/test_ratings.py`
26 passed. Built directly from the DU specs (no design fork).

## What shipped
- **DU1 — remove "Impulse per stroke"** (≈ DPS for an always-forward swimmer):
  - `ratings.py` — dropped `mean_impulse_m` from the Stroke-length pillar's contributing `metrics`.
  - `swimnetics-mobile` ReportCardScreen + RecordScreen — removed the "Impulse" MetricItem from the
    advanced Efficiency grids.
  - ⚠ `ratings.py` is BACKEND → the pillar-expand removal only takes effect once Railway redeploys
    (user push). The advanced-grid removal is client-side (immediate). Mild interim mismatch until deploy.
- **DU2 — long-press metric explainer** (`PillarCards.js`): each contributing/primary metric cell is
  now a Pressable; long-press opens a concise raised card (Modal) showing the metric label,
  explanation (from the /ratings payload; primary falls back to the pillar explanation), and unit.
- **DU3 — athlete limit** (`AthletesScreen.js`): header now reads "N / limit swimmers"; limit =
  `teams.swimmer_limit` (fetched via supabase, now readable; the patch_05 SELECT was already allowed),
  default **20** if unset. (Note: if this should mirror the enforced 402 cap exactly, reconcile the
  source later — schema default is 20.)
- **Bug #2 — trend vs band clarity** (`PillarCards.js`): trend chip relabeled "↑ Up vs last / ↓ Down
  vs last / → Same as last" so a green (still-good) band beside a "down vs last" chip reads clearly —
  band = absolute quality, trend = vs previous session. (`ratings._trend` was already correct.)

## Deploy note
- `ratings.py` → Railway auto-deploys on push to main (user-owned). Required for DU1's pillar-expand
  change + so the explainer text stays accurate.

## Verified at code level
- export green; ratings suite 26 passed; PillarCards modal closes on scrim tap; AthletesScreen limit
  fetch uses the now-readable teams row.
