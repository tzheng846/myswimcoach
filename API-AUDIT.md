# API Audit — `api.py`

**Date:** 2026-07-30 · **Target:** `api.py` (1808 lines, 24 routes) · **Plan:** 51-01
**Schema snapshot:** `supabase/live_schema.json`, generated 2026-07-30 (7 tables, 67 columns)

**This is a report. No production code was changed.** Fixes land in 51-02.

## Method

- Live schema pulled from PostgREST's OpenAPI document via `tools/introspect_schema.py`
  (catalog metadata only — no table rows read, nothing written).
- Column references extracted from `api.py` with an AST walker (`tools/schema_contract.py`)
  that scopes names to genuine supabase builder chains.
- Callers determined by grepping `web/` and `../swimnetics-mobile/src/`.
- Pure modules (`metrics.py`, `ratings.py`, `annotations.py`, `vel_acc_extraction.py`) read where
  `api.py` depends on their contracts.

`supabase/schema.sql` and `patch_04_backfill.sql` were treated as untrusted — both have been proven
wrong about the live database. The snapshot is the only authority used here.

---

# Findings

Ranked by severity. Severity means *observable damage today*, not effort to fix.

## S1 — Breaks in production

### F1. Phantom `athletes.coach_id` breaks four features
**Severity: S1 · Disposition: fix in 51-02**

The live `athletes` table has no `coach_id` column. Its columns are exactly:
`id, team_id, name, dob, stroke_type, created_at, head_waist_m, parent_name, parent_email`.
`api.py` references `athletes.coach_id` at four sites:

| Site | Endpoint | Observable behavior |
|------|----------|---------------------|
| `api.py:1301` | `POST /athletes` insert payload | Hard 500 `PGRST204`. **Coaches cannot add athletes.** |
| `api.py:1277` | `POST /athletes` limit count | Raises → `except: count = 0` → athlete limit never enforced |
| `api.py:1517` | `POST /coach/chat` `_load_roster_rows` | Raises and **deliberately propagates** → every team-wide chat question has failed since Phase 33-02 |
| `api.py:1784` | `GET /billing/status` | Raises → `except: pass` → `athlete_count` always reports 0 |

The file already documents the correct scoping against itself:

```
api.py:513-515
# Roster is scoped by team_id (the live athletes table has no coach_id column — scoping that
# the web gets from RLS; the service-role client must filter explicitly). Sessions stay on
# coach_id (that column exists).
```

`sessions.coach_id`, `devices.coach_id` and `reports.coach_id` all exist and are used correctly —
only `athletes` is wrong. **Recommended fix:** scope athletes by `team_id` at all four sites. Note
`team_id` is not currently fetched by the coach-row selects at `api.py:1396` and `api.py:1771`.

**Do not** run `supabase/patch_04_backfill.sql` to add the column. Its stated premise ("documents
migrations ALREADY APPLIED") is false — its `device_id` migration was never run either (that was
Phase 45) — and line 51 holds a `DROP TABLE IF EXISTS devices` inside a guard whose premise has
already failed once.

### F2. Stored profiles are ~89.5 Hz, but three consumers assume exactly 100 Hz
**Severity: S1 · Disposition: own phase, before 50-02**

Independently verified against the code (not carried over from the prior summary).

`vel_acc_extraction.decimate_signal` decimates by an **integer** factor:

```python
vel_acc_extraction.py:93-97
factor = round(native_fs / target_fs)      # round(268.5 / 100) = 3
dist_dec = decimate(dist_native, factor, zero_phase=True)
actual_fs = native_fs / factor             # 268.5 / 3 = 89.5 Hz
```

The requested 100 Hz is never achieved. But `annotations.py:25` hardcodes `FS_HZ = 100`, and three
`api.py` sites consume the stored profile at that rate:

- `api.py:783` — `duration_s = len(vel) / annot.FS_HZ` (annotation GET)
- `api.py:813` — same, on PUT
- `api.py:844` — `t_arr = np.arange(vel_arr.size) / annot.FS_HZ` — **the recompute time axis**

Error factor is `100 / 89.5 = 1.117`. Consequences on real sessions, not just demo data:

- The annotate page displays a 47.1 s swim as 42.2 s.
- **Recomputing metrics from a saved annotation shifts every time-derived metric by ~11.7%** —
  stroke rate, lap time, DPS, and anything else divided by elapsed time.

Two precisions worth carrying into the fix:

1. **Cycle boundaries themselves are correct.** The coach clicks at displayed time `T`, and
   `annotations.py:126` converts back with `idx = round(T × FS_HZ)`. Both directions use the same
   wrong constant, so the round-trip lands on the sample the coach actually clicked. Only the
   *time interpretation* is wrong — segmentation is not corrupted.
2. **The original auto metrics are correct.** `compute_session_metrics` runs on the true `t_dec`
   clock inside `/process`, so `metrics_json.session` is right until an annotation overwrites it.

### F3. The true sample rate is discarded at write time
**Severity: S1 · Disposition: own phase (with F2)**

```python
api.py:143
t_dec, dist_dec, vel, _accel, _actual_fs = vae.run_pipeline(df, 100.0)
```

`_actual_fs` is captured and thrown away. The `session_row` written at `api.py:280-292` stores
`velocity_profile` and `distance_profile` but **no sample rate**, and `sessions` has no column for
one. Every downstream consumer therefore has to guess — and guesses wrong (F2).

This escalates F2: it is not merely a wrong constant, it is that the correct value is destroyed at
write time. Fixing it properly needs either a new `sessions` column or reprocessing the raw CSV.

**Repair lead:** for sessions not yet recomputed, the true rate is recoverable by comparing
`len(velocity_profile)` against the duration implied by `metrics_json.session` — the two disagree
by exactly the factor. Worth confirming before designing a migration.

---

## S2 — Wrong data, silently

### F4. All three tier limits fail open
**Severity: S2 · Disposition: fix in 51-02 (athlete), own plan (session/device)**

Every limit check computes a count inside `try/except`, defaults to `0` on failure, then compares
against the limit:

| Site | Limit | Failure default |
|------|-------|-----------------|
| `api.py:210-211` | `monthly_session_limit` | `_session_count = 0` |
| `api.py:244-245` | `device_limit` | `_device_count = 0` |
| `api.py:1283-1284` | `athlete_limit` | `count = 0` |

A transient DB error silently grants unlimited usage. For athletes this is not transient — the
query has *always* thrown (F1), so that limit has never fired in production even once.

This is also how F1 stayed invisible for so long: `/billing/status` reported `athlete_count: 0`
confidently rather than surfacing the error.

**Recommended:** a failed count should surface as 5xx, not be treated as zero. Per the 2026-07-30
decision the athlete limit is being switched off entirely for now — that decision does not apply to
the session and device limits, which should either be fixed or explicitly switched off the same way.

### F5. The app displays one limit and the API enforces a different column
**Severity: S2 · Disposition: fix in 51-02 (decide authority), then own plan**

Two parallel limit systems exist in the schema:

- `coaches`: `athlete_limit` (default 3), `device_limit`, `monthly_session_limit`
- `teams`: `swimmer_limit`, `device_limit`, `coach_limit`

`api.py` enforces the **`coaches`** columns. iOS displays the **`teams`** column:

```js
AthletesScreen.js:46
const { data: t } = await supabase.from('teams').select('swimmer_limit').eq('id', teamId).single();
```

So the "N / 20" a coach sees on the Athletes screen is unrelated to the number the API would
enforce (3, on the free-tier default). **`api.py` never reads the `teams` table at all** — zero
occurrences of `table("teams")` — and neither does the web portal. Only iOS touches it.

One of these must be declared authoritative. Given `api.py` is the enforcement point and billing
state lives on `coaches`, `coaches` is the natural winner — but `teams.coach_limit` has no
`coaches` equivalent, so the merge is not purely mechanical.

### F6. DB failures masked as 403 at 7 of 11 coach lookups
**Severity: S2 · Disposition: own plan**

The coach-row lookup is inlined 11 times. Two distinct patterns are in use:

**Hardened (4 sites — `api.py:431, 500, 722, 1016`):** `.limit(1)`, no `try/except`, so a genuine
query failure propagates as 5xx. This is the Phase-36 review-hardening pattern, and it is correct:

```
api.py:430
# No row → 403; a real query/DB failure propagates as 5xx (not masked as 403).
```

**Masked (7 sites — `api.py:342, 632, 670, 1158, 1184, 1210, 1396`):** `.single()` wrapped in
`try/except: pass`, leaving `coach_row_id = None`, which then raises **403 "Coach profile not
found"**. A database outage is reported to the client as an authorization failure.

The correct pattern already exists in the file and was simply never propagated to the other 7 sites.

---

## S3 — Duplicated state

### F7. Billing state duplicated across `coaches` and `teams`
**Severity: S3 · Disposition: accept and document, revisit with F5**

`subscription_tier` and `stripe_customer_id` exist on **both** tables. `api.py` reads and writes
only the `coaches` copies (`_get_coach_row` at 1667/1695/1771, webhook at 1711-1764). The `teams`
copies are written by nothing in this repo and read by nothing in this repo.

Not currently harmful — the unused copy is inert. It becomes harmful the moment anything starts
reading it, which is exactly what happened with `teams.swimmer_limit` in F5.

---

## S4 — Leanness

### F8. `_get_coach_row` exists but 11 sites re-implement it
**Severity: S4 · Disposition: own plan**

`_get_coach_row(sb_admin, user_id, fields)` is defined at `api.py:1330` and used at only 5 call
sites (188, 1267, 1667, 1695, 1771). Eleven other sites inline the same query by hand with varying
select lists and — per F6 — two incompatible error-handling behaviors.

Consolidating would fix F6 in the same pass. **Caveat:** the two behaviors are not equivalent, so
this is not a pure refactor — the consolidation must pick the hardened semantics deliberately, and
that changes 403s into 5xxs on 7 endpoints. Worth doing, worth doing as its own reviewed change.

### F9. `GET /sessions/{session_id}/export` has no caller
**Severity: S4 · Disposition: decide in 51-02**

Zero references in `web/` and zero in `swimnetics-mobile/src/` (iOS builds its CSV client-side).
It is authenticated and ownership-scoped, so it is not a security hole — just ~90 lines of
untested surface area. Confirms the existing `CLAUDE.md` note. Keep or delete; no third option.

### F10. Four billing endpoints have no client caller
**Severity: S4 · Disposition: accept and document**

`POST /billing/checkout-session`, `POST /billing/portal-session`, `GET /billing/complete` and
`GET /billing/status` have zero references in either client. `POST /billing/webhook` has an
external caller (Stripe) and is live.

This is known and intentional (`CLAUDE.md`: "⚠ no client UI calls these yet") — recorded here so
the audit is complete, not as a defect. It does mean the Stripe integration is effectively
unexercised end-to-end.

### F11. No input validation layer
**Severity: S4 · Disposition: accept, with one caveat**

Six handlers hand-parse `await request.json()` then `body.get(...)` with no schema:
`api.py:617, 799, 1147, 1260, 1371, 1651`.

**My assessment: pydantic models here would be ceremony, not safety.** Every one of these routes is
authenticated, the bodies are small and flat, and the handlers already coerce and default the
fields they use. Adding models would be a large diff for little behavioral change.

The one caveat is `api.py:818-823` (annotation PUT), which builds a document from client-supplied
values and passes it to `annotations.validate_annotation`. That validation is the real boundary and
it already exists. Prefer strengthening it over adding a framework.

---

# Endpoint inventory

> ⚠ **SUPERSEDED — 2026-08-13.** [DATA-FLOW.md](DATA-FLOW.md) §5 carries the current
> endpoint × caller table, re-derived from source rather than from this document. This
> inventory was taken 2026-07-30 and predates Phases 57–61. The *findings* above (F1–F11) are
> still the record of what was wrong and why; only this inventory is superseded.

Auth: all routes require a Supabase bearer JWT except where noted.
Scope column = how ownership is enforced for the service-role client.

| # | Route | Auth | Tables | Scope | Callers | Verdict |
|---|-------|------|--------|-------|---------|---------|
| 1 | `GET /health` | none | — | — | Railway | OK |
| 2 | `POST /process` | yes | sessions, devices, coaches, athletes | `coach_id` | iOS ×2 | F4 (session+device limits fail open); 49-01 (error leak, no size cap, no athlete-ownership check) |
| 3 | `GET /sessions/{id}/export` | yes | sessions, coaches | `coach_id` | **none** | F9 — dead |
| 4 | `GET /sessions/{id}/ratings` | yes | sessions, coaches | `coach_id` | web ×1, iOS ×2 | OK — hardened lookup |
| 5 | `GET /team/overview` | yes | athletes, sessions, coaches | `team_id` + `coach_id` | web ×2, iOS ×2 | OK — correct scoping, hardened lookup |
| 6 | `PATCH /sessions/{id}` | yes | sessions, coaches | `coach_id` | web, iOS | F6 (masked lookup) |
| 7 | `DELETE /sessions/{id}` | yes | sessions, coaches, storage | `coach_id` | web, iOS | F6 |
| 8 | `GET /sessions/{id}/annotations` | yes | sessions, session_annotations | `_owned_session` | web ×1 | **F2** — `duration_s` wrong by 11.7% |
| 9 | `PUT /sessions/{id}/annotations` | yes | sessions, session_annotations | `_owned_session` | web ×1 | **F2** — recompute time axis wrong |
| 10 | `DELETE /sessions/{id}/annotations` | yes | sessions, session_annotations | `_owned_session` | web ×1 | OK |
| 11 | `POST /sessions/{id}/video` | yes | sessions, storage | `_owned_session` | web ×1, iOS ×4 | 49-01 (no size cap) |
| 12 | `GET /sessions/{id}/video-url` | yes | sessions | `_owned_session` | web ×1 | OK |
| 13 | `GET /annotations/export` | yes | sessions, session_annotations, coaches | `coach_id` | dev tool | OK — hardened lookup |
| 14 | `GET /reports/{token}` | **none** | reports, athletes, sessions | token | web ×1 | 49-01 (no token expiry) |
| 15 | `PATCH /devices/{chip_id}` | yes | devices, coaches | `coach_id` | iOS | F6 |
| 16 | `DELETE /devices/{chip_id}` | yes | devices, coaches | `coach_id` | iOS | F6 |
| 17 | `GET /devices` | yes | devices, sessions, coaches | `coach_id` | iOS ×1 | F6 |
| 18 | `POST /athletes` | yes | athletes, coaches | **broken** | web ×2, iOS ×1 | **F1 — 500s. Live blocker.** F4 |
| 19 | `POST /coach/chat` | yes | athletes, sessions, coaches | **broken** | web ×1, iOS ×2 | **F1 — team tools broken.** F6 |
| 20 | `POST /billing/checkout-session` | yes | coaches | `coach_id` | **none** | F10 |
| 21 | `POST /billing/portal-session` | yes | coaches | `coach_id` | **none** | F10 |
| 22 | `GET /billing/complete` | **none** | — | — | **none** | F10 — static redirect |
| 23 | `POST /billing/webhook` | **none** (Stripe sig) | coaches | Stripe customer id | Stripe | OK — signature verified (49-01 confirmed) |
| 24 | `GET /billing/status` | yes | athletes, devices, sessions, coaches | `coach_id` | **none** | **F1** — `athlete_count` always 0 |

Route count matches `grep -c "^@app\." api.py` = 24. All 24 accounted for.

---

# Ownership rule

Derived from the live schema, not from the code:

| Table | Ownership column | Rule |
|-------|-----------------|------|
| `athletes` | **`team_id`** | No `coach_id` exists. Team-scoped only. |
| `sessions` | `coach_id` | Column exists and is populated by `/process`. |
| `devices` | `coach_id` | Column exists, no FK (Phase 14-01 decision). |
| `reports` | `coach_id` | Column exists; public reads go by `token`. |
| `session_annotations` | via `sessions` | No own owner column; `_owned_session` enforces through the parent. |
| `coaches` | `user_id` | Maps the JWT subject to a coach row. |
| `teams` | — | **Never touched by `api.py`.** |

**Deviations from this rule:** the four F1 sites, and nothing else. Every other `coach_id` filter
in the file targets a table that genuinely has the column.

---

# Recommended fix sequence

| Order | Item | Findings | Where |
|-------|------|----------|-------|
| 1 | Scope athletes by `team_id`; athlete limit behind `ENFORCE_ATHLETE_LIMIT` (default off); promote the AST check into a test | F1, F4 (athlete), F9 decision | **51-02** (planned) |
| 2 | Sample-rate contract: persist the true rate, stop assuming 100 Hz, decide on repairing affected sessions | F2, F3 | **Own phase — before 50-02** |
| 3 | Security hardening | — | **49-01** (already planned, still valid) |
| 4 | Consolidate coach lookups onto `_get_coach_row` with hardened semantics | F6, F8 | Own plan |
| 5 | Declare one limit system authoritative; align iOS | F5, F7 | Own plan |
| 6 | Session/device limits: fix or explicitly disable, matching the athlete decision | F4 | Own plan, with #5 |

Accepted and documented, no work planned: F10 (billing endpoints unused), F11 (no pydantic layer).

---

# What this audit could not check

Stated plainly so the coverage is not overread:

- **Runtime behavior.** Everything here is static analysis plus schema comparison. No endpoint was
  executed against real data.
- **RLS policy correctness.** `api.py` uses the service-role key, which bypasses RLS entirely, so
  every ownership guarantee in this file is manual. The audit verified the manual checks exist; it
  did not verify the RLS policies that protect the clients' direct supabase-js reads.
- **Two extractor blind spots**, both verified by hand instead:
  - Column lists passed to helpers as string arguments are invisible to the AST walker
    (`_get_coach_row(sb, uid, "id, team_id, athlete_limit")`). All 5 call sites were checked
    manually — every field named exists on `coaches`.
  - Payload dicts built in a variable before the call (`.update(updates)`) are not seen. This makes
    the "columns live but never referenced" list a **lead list, not proof** — `sessions.notes` and
    `is_starred` appear there but are genuinely used via dynamic update dicts.
- **How many stored sessions carry recomputed (F2-affected) metrics.** This needs a data read, which
  is outside the read-only-catalog scope approved for this audit. To find out:
  ```sql
  select count(*) from sessions
  where metrics_json->'data_quality'->>'recomputed_from_annotation' = 'true';
  ```
- **Concurrency and races** — e.g. two simultaneous `/process` calls against the same limit.
- **The Stripe integration end-to-end.** The webhook's signature check was confirmed present
  (per 49-01); no payment flow was exercised, and no client calls the other billing endpoints.

---
*Generated by plan 51-01. Regenerate the schema snapshot with `python tools/introspect_schema.py`
before relying on the contract check after any migration.*
