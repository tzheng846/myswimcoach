# 38-03 SUMMARY — Team tab (table + athlete hub + parent reports)

**Status:** Code-complete; device verification DEFERRED (38-TEST-PLAN.md). `npx expo export
--platform ios` exits 0 (3.2MB). Built directly from the design locked 2026-06-19 (mock+ask) — no
separate 38-03-PLAN.md (momentum cadence: design forks confirmed via AskUserQuestion, then build).

## Contracts verified before building
- `reports` table (patch_03): { athlete_id, coach_id?, token UNIQUE, config_json, sent_at }; RLS
  "coach manages own reports" FOR ALL (team-scoped) → mobile inserts via supabase-js.
- Report token: web uses `crypto.randomUUID()`; config_json = {start,end,metrics[],message}. Report
  URL = `${origin}/report/{token}`.
- `athletes` RLS = FOR ALL (team-scoped) → edit + delete via supabase-js work (no API endpoint
  needed; there is no DELETE /athletes).
- `teams` RLS = SELECT only (no UPDATE) → confirms the 38-02 team-name-edit caveat (won't persist
  until a teams UPDATE policy is added — backend follow-up).
- REPORT_METRICS keys mirrored from web/lib/reportMetrics.js.

## What shipped (swimnetics-mobile)
- `src/screens/AthletesScreen.js` — REWRITTEN as the Team tab labeled-pillar TABLE: reads
  `/team/overview`, icon-header legend (gauge/ruler/wave/battery), rows = name + last-tested + 4
  band dots (never-tested → dashes), bottom band legend, (+) inline add-athlete (POST /athletes,
  402-aware), row → AthleteDetail. No avatars.
- `src/screens/AthleteDetailScreen.js` — NEW full hub: Send report (supabase reports insert + RN
  Share sheet + mark sent) + Record (→ RecordingConfig preselected), pillar band cards from the
  athlete summary, session list (supabase → ReportCard), ⋯ menu → Edit fields (name + head-waist,
  supabase update) / Delete athlete (confirm → supabase delete → back).
- `src/config.js` — added `WEB_BASE` (https://swimnetics.com — ⚠ confirm vs deployed domain).
- `src/navigation/RootTabs.js` — registered `AthleteDetail` on the root stack.
- `package.json` — added **expo-crypto** (report-token UUIDs) — FIRST native dep of the phase.

## Bug caught + fixed in self-review
- Band colors: pillar bands are snake_case (`needs_work`) but theme tokens are camelCase
  (`needsWork`) → a needs-work dot/label would render grey. Added explicit `BAND_FALLBACK` /
  `BAND_COLOR` maps in both screens (and Team table prefers payload `rating_colors`, also snake).

## Deviations / limitations (deferred)
- expo-crypto = native → forces the one end-of-phase build (flagged in 38-TEST-PLAN build reqs).
- WEB_BASE is a best-guess domain — confirm before customer use.
- Edit covers name + head-waist (not stroke_type) — minimal; expand later if needed.
- Report send is streamlined per-athlete (all metrics, full range, no message) via the OS share
  sheet; mailto/date-range/metric-pick parity stays web-only (by the streamlined-mobile decision).

## Verified at code level
- export green; no raw hex in new screens (tokens only); Team table consumes only documented
  /team/overview fields; pillar keys match ratings.PILLARS; report insert matches the reports schema.
