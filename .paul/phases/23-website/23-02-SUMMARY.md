# Plan 23-02 Summary — Coach Portal Core

**Status:** Complete (2026-06-10). Build + pytest green; auth redirect verified live.
Data-dependent ACs (dashboard contents, report-card cross-check) deferred to the
23-03 human-verify checkpoint — requires the user's coach credentials.

## What was built

- `web/lib/supabase.js` — browser client from NEXT_PUBLIC_* env (values in `.env.local`,
  mirrored from swimnetics-mobile/src/config.js; publishable key, safe client-side).
- `web/lib/api.js` — `apiFetch(path, options)`: attaches Supabase access_token as Bearer,
  throws Error with `.status` on non-OK (402 handled in AddAthleteModal).
- `/login` — ports iOS LoginScreen branding (WaveMark, SWIMNETICS, amber tagline).
- `/app` layout (`web/app/app/layout.js`) — client-side auth guard (getSession +
  onAuthStateChange → /login), portal topbar (Dashboard/Athletes/Sessions + Sign out →
  signs out then lands on marketing `/`).
- Dashboard `/app` — athlete cards (letter Avatar, same color-hash as iOS) + latest-session
  metrics (two-query pattern from AthletesScreen).
- Athletes `/app/athletes` — roster, add via POST /athletes proxy (402 → friendly message),
  inline head_waist_m edit via supabase update.
- Sessions `/app/sessions[?athlete=]` — athlete dropdown, dynamic stroke chips (only
  strokes present), hover actions star/delete (PATCH/DELETE via apiFetch), 3-stat cards.
  List query uses `session:metrics_json->session` JSON-path alias to avoid pulling cycles.
- Report card `/app/sessions/[id]` — full iOS ReportCardScreen port: SessionSummaryCard,
  MetricGrid (Start Phase / Session / Efficiency + cv_isi>0.8 unreliable warn),
  DataQualityCard, TimeToX (head_waist_m offset, presets, chart marker), VelocityChart
  (Recharts: hover readout, Brush zoom, m/yd toggle, cycle-boundary ReferenceLines from
  metrics_json.cycles, ≤2000 pt decimation), editable name/star/notes, Coming Soon for
  non-breaststroke (null stroke_type = legacy = full analytics).

## Deviations from plan

- **api.py untouched**: CORS middleware already existed (allow_origins=["*"], api.py:65).
  Task 1's api.py change was unnecessary.
- Swipe actions → hover buttons (web idiom); badges hide on hover to avoid overlap.

## Gotchas

- `params` is a Promise in Next 16 dynamic routes → `use(params)` in the client page.
- `useSearchParams` requires a Suspense boundary (sessions page wraps SessionsView).
- @supabase/supabase-js had to be installed (wasn't in 23-01's dep batch).

## Verification

- `npm run build` exit 0 — routes: /, /login, /app, /app/athletes, /app/sessions, /app/sessions/[id]
- `pytest tests/` 26 passed
- Live: unauthenticated /app → /login redirect confirmed in preview; login page renders
