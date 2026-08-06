# Plan 24-01 Summary — Parent Data Layer + Public Report API

**Status:** Complete (2026-06-11). Schema applied by user; pytest 30 passed.

## What was built

- `supabase/patch_03_parent_reports.sql` — athletes.parent_name + parent_email;
  reports table (id, athlete_id CASCADE, coach_id SET NULL, token UNIQUE, config_json
  JSONB, created_at, sent_at) + token index + team-scoped RLS (USING + WITH CHECK,
  mirrors sessions policy). **User ran it in the Supabase SQL editor — confirmed.**
  No anon policy by design — public access only via service-role API.
- `GET /reports/{token}` in api.py (after DELETE /sessions) — **no auth**:
  reports-by-token (404 on miss) → athlete (name, parent_name) → sessions for athlete
  filtered by config start/end (null = unbounded), ascending. Response:
  `{athlete:{name,parent_name}, period:{start,end}, message, metrics:[keys],
  sessions:[{date, values:{key:val}}], generated_at}` — values restricted to
  config_json.metrics, sessions lacking metrics_json.session skipped, _clean()ed.
  No profiles, no coach identifiers in the payload.
- `tests/test_api.py` — TestPublicReport: 404 unknown token, payload shape, session
  filtering/ordering/metric-key restriction, empty-session case. Fake admin =
  MagicMock with chainable table mock keyed by table name (`_fake_admin`), patched
  via `monkeypatch.setattr(api, "_get_supabase_admin", ...)` — reusable pattern.

## AC results

| AC | Status | Evidence |
|----|--------|----------|
| AC-1 schema | Pass | patch_03 run by user without errors (live write-verify lands in 24-02) |
| AC-2 payload | Pass | test_valid_token_shape + test_sessions_filtered_and_ordered |
| AC-3 404/empty | Pass | test_unknown_token_404 + test_no_sessions_returns_empty_list |

## Deviations

- Planned local curl check replaced by TestClient tests: direct prod-DB verification
  was denied by the permission classifier (reasonable — no explicit authorization to
  query prod). Live confirmation deferred to 24-02 portal usage + 24-03 checkpoint.

## For 24-02/24-03

- config_json contract: `{start: ISO|null, end: ISO|null, metrics: [keys], message: str|null}`
- Endpoint URL: `${NEXT_PUBLIC_API_URL}/reports/${token}` — plain fetch, no Authorization
- pytest count now 30
