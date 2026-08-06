# 39-01 SUMMARY — Redesign bug fixes (4 located, 3 fixed + 1 deferred)

**Status:** Code-complete; device verify DEFERRED to phase end (39-TEST-PLAN.md). `npx expo export
--platform ios` exits 0 (3.2MB).

## Fixed
1. **CRASH (biggest)** — `AthleteDetailScreen.js:149` referenced undeclared `rc` (dropped in the
   38-04 self-review). Changed `(p.band && rc[p.band])` → `BAND_COLOR[p.band]`. Tested athletes now
   open without a redbox. (grep confirms no `rc` left in the file.)
2. **Pillar expand units** — `PillarCards.js` gained a `unit` prop + `displayMetric()` converter
   (m→yd ×1.09361, m/s→yd/s; spm/%/s/unitless pass through), applied in the contributing-metric grid;
   `ReportCardScreen` now passes `unit={unit}` (from UnitsContext). Expanded values follow the
   Settings m/yd toggle.
3. **Team-name RLS** — `supabase/patch_05_teams_update_rls.sql` adds an UPDATE policy on `teams`
   (USING + WITH CHECK `id = current_team_id()`). USER-APPLIED SQL; the Settings update already
   issues the write, so the name persists once the policy exists.

## Deferred (decision not taken; user moved on)
4. **Band vs trend ("declined" + green)** — confirmed NOT a logic bug: `ratings.py _trend` is correct;
   band=absolute, trend=vs-previous are independent by design. → UI-clarity work (relabel the chip
   "↓ vs last session" + visually separate it from the band bar) FOLDED INTO 39-03 (which already
   touches PillarCards). Recommended option: `clarify-label`.

## Files
- swimnetics-mobile/src/screens/AthleteDetailScreen.js (crash)
- swimnetics-mobile/src/components/PillarCards.js + src/screens/ReportCardScreen.js (units)
- supabase/patch_05_teams_update_rls.sql (new; user-applied)

## Verified at code level
- export green; no `rc` reference remains; units convert only distance/velocity; RLS SQL reviewed.
- Device checks → 39-TEST-PLAN.md (batched, per user: defer testing to phase end).
