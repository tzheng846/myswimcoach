# Plan 24-02 Summary — Portal: Parent Info + Report Builder + Send List

**Status:** Complete (2026-06-11). Build exit 0 (/app/reports in route table).
Live AC flows (persistence, generation against real Supabase) deferred to the
24-03 checkpoint per plan — requires coach login.

## What was built

- `web/lib/reportMetrics.js` — REPORT_METRICS: mean_vel_ms, max_vel_ms,
  stroke_rate_spm, mean_dps_m, lap_time_s, cv_arm_peak_vel with
  {label, unit, direction (higher/lower/neutral), improvePhrase, decimals} +
  metricByKey(). 24-03 extends with formatValue/computeImprovement.
- Athletes page rebuilt: per-card Edit panel (parent name, parent email
  type=email, head_waist_m) saved in one supabase update; roster shows parent
  line; missing email → amber "No parent email". (Replaces old head_waist-only
  inline edit.)
- `/app/reports` (+ nav link): ReportBuilder + ReportSendList with refreshKey.
- ReportBuilder: swimmer checklist (Avatar, no-email amber flag, select-all),
  date range (date inputs, blank = unbounded; end-of-day on `end`; `[color-scheme:dark]`
  for native picker), metric chips (all on default), batch message, Generate →
  supabase insert one row per swimmer {athlete_id, token: crypto.randomUUID(),
  config_json {start, end, metrics, message}}. coach_id omitted (athlete_id drives RLS).
- ReportSendList: reports joined `athletes(name, parent_name, parent_email)`
  newest-first; per row View (/report/{token}, new tab), Copy link, Email draft
  (mailto w/ first-name subject + greeting + URL), Delete (confirm). Copy/Email
  set sent_at (supabase update) → "Sent ✓". Header "Copy all links" → one line
  per report (name — email — URL).

## AC results

| AC | Status | Notes |
|----|--------|-------|
| AC-1 parent contact | Code complete | Persistence verified at 24-03 checkpoint |
| AC-2 builder | Code complete | Generation against live reports table at checkpoint |
| AC-3 send list | Code complete | mailto/copy/sent_at round-trip at checkpoint |

## Notes for 24-03

- Send list links to `/report/${token}` — the route 24-03 creates.
- config_json contract honored exactly as 24-01 expects.
- api.py untouched (boundary held).
