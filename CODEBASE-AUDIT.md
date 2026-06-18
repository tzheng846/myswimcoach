# Swimnetics Codebase Audit

*Produced 2026-06-12 (PAUL Phase 25, plan 25-01). Every claim below was verified against
code, test runs, or live probes on that date — file:line references are evidence, not
decoration. Project history and decision log live in `.paul/STATE.md`; this document is
the cross-system map.*

*Last refreshed 2026-06-18 (Phase 35-03 doc reconciliation) for Phases 33–36 + the 35-02
iOS work: added the `/coach/chat` tool-use loop (coach.py + roster_metrics.py + drills.py),
the rating engine (ratings.py + `GET /sessions/{id}/ratings` + RATINGS-SPEC.md), the iOS
ratings UI, DiagnosticsScreen / VideoOverlayScreen, and the iPhone-first device family;
resolved the 2026-06-12 Railway/Vercel deploy-drift rows (35-01 verified prod live); added
the Feature Status Ledger below. Rows still dated 2026-06-12 carry their original evidence.*

---

## 1. System overview

```
ESP32 + AS5600 encoder (ESP_32_V5/, firmware 1.1.0, buffer-and-dump)
   │  BLE Nordic UART — button-only recording into RAM, META/DUMP retrieval
   ▼
iOS app (separate repo: C:\Users\TonyZheng\Desktop\swimnetics-mobile)
   │  retrieves samples → CSV → FileSystem.uploadAsync
   ▼
FastAPI on Railway (api.py — swimnetics-api-production.up.railway.app)
   │  vel_acc_extraction.run_pipeline() → metrics.compute_session_metrics()
   ▼
Supabase (ujrotuijxrbscjhzekjk.supabase.co — auth, Postgres+RLS, raw-csvs storage)
   ▲                                    ▲
   │ reads via supabase-js (RLS)        │ service-role writes
Website (web/ — Next.js 16, Vercel target, not yet deployed)
   ├─ marketing site (/)
   ├─ coach portal (/app/*) — reads supabase-js, writes via Railway API
   └─ parent report pages (/report/[token]) — public, served by GET /reports/{token}

Streamlit app.py — desktop analysis tool + AI coach (coach.py). Dev tool, not product.
```

**Two repos.** `myswimcoach` (this repo) = backend + firmware + website + analysis tools.
`swimnetics-mobile` = the iOS app. They share three contracts: the BLE protocol
(firmware↔iOS), the Railway API (iOS/web↔backend), and the Supabase schema (everything).

---

## Feature Status Ledger (refreshed 2026-06-18)

One-glance "what works / what's deferred / what's draft." Detail + evidence in the sections below.

| Surface | Status | Note |
|---------|--------|------|
| Signal pipeline + breaststroke metrics | ✅ WORKING | 93 tests pass; kick metrics flagged unreliable by design |
| Wavelet segmentation (all strokes) | ⚠️ DRAFT | `segmentation_reliable=False` always → ratings provisional; tuning = future 16-06 |
| Railway API (process/sessions/devices/athletes) | ✅ WORKING | live + verified (35-01 prod probe) |
| Parent reports (`/reports/{token}`) | ✅ WORKING | prod verified (35-01) — was the 06-12 deploy-drift ❌, now resolved |
| AI coaching chat (`/coach/chat`) | ✅ WORKING (web) | tool-use loop live; `ANTHROPIC_API_KEY` set on Railway (35-01); **web only — not on iOS** |
| Coach-friendly ratings (`/sessions/{id}/ratings`) | ✅ WORKING / ⚠️ DRAFT thresholds | engine + endpoint live (PR #5); breaststroke bands DRAFT — coach review owed |
| Web coach portal + marketing | ✅ WORKING | live on Vercel (35-01); all surfaces verified |
| iOS ratings pillar UI | ✅ WORKING | shipped 35-02, verified on device (breaststroke); non-breaststroke render unexercised (no data) |
| iOS iPad support | ➖ DE-SCOPED | iPhone-first (TARGETED_DEVICE_FAMILY=1); responsive iPad = future phase |
| iOS device diagnostics (34-01) | ◐ PARTIAL | screen verified live; full magnet→buffer flow DEFERRED (resolder) |
| iOS recording / retrieval / video (21-02 / 26-01 / 22-02) | ⏸ DEFERRED | post-resolder build (one build; no rebuild cost) |
| AI chat + advanced per-cycle graphs on iOS | ❌ NOT BUILT | web-only parity gap (not a regression) — candidate future iOS-parity phase |
| Stripe billing checkout/portal | ⚠️ UNREACHABLE | endpoints exist, no client UI (deliberate per Phase 23) |
| Email dispatch of parent reports | ⏸ DEFERRED | mailto/copy-link shipped; Resend slots in later |

---

## 2. Folder map — myswimcoach

| Item | Role | Status |
|------|------|--------|
| `api.py` | FastAPI server — all production endpoints (see §4) | **Production** |
| `vel_acc_extraction.py` | Signal pipeline: counts → velocity @ 100 Hz. Owns `WHEEL_DIAMETER_M = 0.06` (vel_acc_extraction.py:27) — the only copy of this constant in the system | **Production** |
| `metrics.py` | Breaststroke feature extraction, pure functions | **Production** |
| `ratings.py` | Coach-friendly rating engine (pure): 4 pillars + 0–100 score + direction-aware trend; source of truth for `/sessions/{id}/ratings` + web/iOS pillar cards (Phase 36; contract `.paul/.../RATINGS-SPEC.md`). DRAFT breaststroke thresholds | **Production** |
| `drills.py` | Drill library + metric tag-matching recommender (pure) — used by `/coach/chat` (Phase 33) | **Production** |
| `roster_metrics.py` | Team/roster aggregation (pure) — powers `/coach/chat` team questions (Phase 33) | **Production** |
| `supabase/` | `schema.sql` + 3 patch files — **stale vs live DB, see §5.2**; patch_03 not in git (§5.3) | Production (drifted) |
| `web/` | Next.js 16 website: marketing + coach portal + parent reports | **Production** (live on Vercel — verified 35-01) |
| `tests/` | Pytest suite (93 tests incl. `test_ratings.py`, all passing). `conftest.py` mocks the supabase module and overrides `require_auth` — no network | **Production** |
| `ESP_32_V5/` | Current firmware 1.1.0 — buffer-and-dump (+ STATUS command, Phase 34) | **Production** |
| `Procfile` | Railway entry: `uvicorn api:app` | **Production** |
| `requirements.txt` | Railway deps — includes Streamlit-only packages (streamlit, plotly, matplotlib, stumpy, anthropic); missing `python-dotenv` used by dev tools | Production (untidy) |
| `app.py` | Streamlit desktop dashboard + AI coach chat | Dev/analysis tool |
| `coach.py` | Anthropic coaching system-prompt builder — **shared** by app.py (Streamlit) AND api.py `/coach/chat` (Phase 31/33). (06-12 note "only app.py" is obsolete) | **Production** (+ dev) |
| `fetch_sessions.py`, `inspect_cycles.py`, `pipeline_view.py` | Dev utilities (Supabase fetch, cycle inspection, pipeline view) | Dev tools |
| `logger.py`, `logger_ble.py` | Bench logging (serial / BLE incl. META/DUMP support) | Dev tools |
| `motor_logger_esp32/` | Firmware base for ESP_32_V5 (live-streaming + motor). Kept untouched as reference. Contains `gpio32_test/` diagnostic | Legacy/reference |
| `as5600_logger_ble/` | Arduino Nano 33 BLE logger (4-sample packets) | Legacy |
| `as5600_logger_esp32/` | Early ESP32 logger (2-sample packets) | Legacy |
| `logger_esp32/` | ESP32-S3 live-streaming logger | Legacy |
| `landing/index.html` | Pre-Phase-23 placeholder — superseded by `web/` | Legacy (delete candidate) |
| `wavelet_spike.py`, `segment_motif_spike.py` | Phase 16 freestyle-segmentation research | Experimental |
| `vel_acc_extraction_testing*.py`, `vel_acc_extraction_test2.py` | Signal-processing diagnostics | Experimental |
| `pose/`, `pose_extraction.py`, `merge_streams.py`, `scripts/visualize_pose.py`, `vision_pipeline_plan.md` | Pose/video pipeline (future kick-labeling effort) | Experimental |
| `video_sync.py`, `swim_pipeline.py`, `AP.mp4` | Video-overlay validation tooling (Phase 22) | Experimental |
| `Aerial/`, `Front/`, `Side_*/`, `Breaststroke/` | Reference swim video datasets | Data |
| `raw/`, `processed/` | Encoder CSVs (raw + pipeline output) | Data |
| `.paul/` | PAUL project management — STATE.md is the project's memory | Meta |
| `STRATEGY.md`, `COACHING_PHILOSOPHY.md`, `HANDOFF.md`, `README.md`, `dataset_structure.md` | Docs | Meta |

## 3. Folder map — swimnetics-mobile

| Item | Role |
|------|------|
| `App.js` | Navigation stack + AuthProvider + BleProvider wrapper |
| `src/config.js` | `API_BASE` (Railway URL), Supabase URL + anon key — all hardcoded |
| `src/lib/supabase.js` | supabase-js client (Metro CJS redirect in `metro.config.js` for Hermes) |
| `src/context/AuthContext.js` | Coach JWT session; reads `coaches` table |
| `src/context/BleContext.js` | App-lifetime BLE singleton; known devices in SecureStore; chipId derived from BLE name `SwimLogger-XXXXXX` (BleContext.js:58) |
| `src/screens/LoginScreen.js` | Supabase email/password auth |
| `src/screens/AthletesScreen.js` | Roster + dashboard; adds athletes via `POST /athletes` |
| `src/screens/DevicesScreen.js` | Pair/scan flow + device list via `GET /devices`, rename/deregister via `PATCH`/`DELETE /devices/{chip_id}` |
| `src/screens/RecordingConfigScreen.js` | Pre-session config: athlete, stroke, name, notes, device picker |
| `src/screens/RecordScreen.js` | Buffer-and-dump retrieval: META → clock correlation → DUMP → CSV → upload. Constants META_SIZE=8, END_OF_DUMP_MARKER=0xEE (RecordScreen.js:24-25) |
| `src/screens/SessionHistoryScreen.js` | Per-athlete history; star/delete via `PATCH`/`DELETE /sessions/{id}` |
| `src/screens/ReportCardScreen.js` | Historical report card; **Simple/Advanced toggle** — Simple = ratings pillar cards, Advanced = raw metric cards (Phase 36, 35-02); CSV export built client-side via Share |
| `src/screens/DiagnosticsScreen.js` | Live magnet/wiring/buffer/link health via the STATUS BLE command (Phase 34); plain-English verdicts |
| `src/screens/VideoOverlayScreen.js` | In-app record-with-video playback overlay synced to the velocity cursor (Phase 26) |
| `src/components/PillarCards.js` | RN ratings pillar UI — fetches `GET /sessions/{id}/ratings`, mirrors web (band/marker/verdict/trend/expand); colors from payload (Phase 36, 35-02) |
| `src/components/VelocityChart.js`, `DataQualityCard.js` | Shared display components |
| `ios/`, `android/` | Native projects (edited directly — no Mac for prebuild). **iPhone-first**: `TARGETED_DEVICE_FAMILY=1` in the pbxproj (iPad de-scoped, 35-02) |

---

## 4. Connection matrix

Legend: ✅ MATCH (verified both sides) · ⚠️ GAP (works, but something is unwired or
undocumented) · ❌ MISMATCH/DRIFT · ❔ UNVERIFIED

### 4.1 BLE protocol — firmware ↔ iOS

| Contract | Verdict | Evidence |
|----------|---------|----------|
| NUS UUIDs (service/TX/RX) | ✅ | ESP_32_V5.ino:96-98 ↔ RecordScreen/BleContext; matches STATE.md locked spec |
| Device name `SwimLogger-<chipID>` → chipId source | ✅ | ESP_32_V5.ino:517 ↔ BleContext.js:58 |
| Commands START/STOP/META/DUMP/REEL_ON/REEL_OFF, write-with-response | ✅ | ESP_32_V5.ino:395-400 ↔ RecordScreen.js:126,281,304 |
| Sample = 7 B `<IHB`; packets any multiple of 7 | ✅ | ESP_32_V5.ino:175 (packed struct) ↔ RecordScreen parser |
| META = 8 B `[start_us][now_us]` LE; 0 = no session | ✅ | ESP_32_V5.ino:307-318 ↔ RecordScreen.js:256-277 |
| DUMP: 24×7 B packets + 1 B 0xEE end marker; buffer cleared on success, retained on disconnect | ✅ | ESP_32_V5.ino:326-356 ↔ RecordScreen.js:288-297 |
| ID characteristic 6E400004 (chip ID, read) | ⚠️ | Firmware exposes (ESP_32_V5.ino:550-553); **no iOS consumer** — chipId comes from the name instead (recorded decision) |
| FW characteristic 6E400005 (firmware version, read) | ⚠️ | Firmware exposes (ESP_32_V5.ino:555-558); **iOS never reads it and never sends `firmware_version` to `/process`** → `devices.firmware_version` stays null from the app path. Phase 14's "expose firmware version" is half-wired |

### 4.2 Railway API — endpoint ↔ caller

| Endpoint (api.py) | iOS caller | Web caller | Verdict |
|---|---|---|---|
| `GET /health` (api.py:93) | — | — | ✅ Railway healthcheck; live 200 |
| `POST /process` (api.py:98) | RecordScreen.js:165 — sends file, head_waist_m, stroke_type, athlete_id, name, notes, device_id | — | ✅ (fields match Form params; `firmware_version` accepted but never sent — see 4.1) |
| `GET /sessions/{id}/export` (api.py:312) | **none** — iOS builds CSV client-side (ReportCardScreen.js:146) | **none** | ⚠️ **Orphan endpoint** — no caller anywhere; duplicates the iOS client-side logic |
| `GET /sessions/{id}/ratings` (Phase 36) | PillarCards.js (35-02) | PillarCards.js (36-02) | ✅ live + auth-guarded (prod probe 2026-06-18: unauth → 401, bogus route → 404 = per-route auth, route deployed). Baseline = athlete's previous same-stroke session |
| `POST /coach/chat` (Phase 31/33) | **none** (web-only) | CoachChat.js | ✅ live; bounded tool-use loop (coach.py + roster_metrics.py + drills.py), coach-scoped; returns `{reply, data}`; needs `ANTHROPIC_API_KEY` (set on Railway, 35-01) |
| `PATCH /sessions/{id}` (api.py:403) — allowed fields `name, notes, is_starred` only (api.py:418) | ReportCardScreen.js:185, SessionHistoryScreen.js:144 | sessions/page.js:73, sessions/[id]/page.js:62 | ✅ (note: root CLAUDE.md claimed `stroke_type` is patchable — it is **not**; doc fixed in this audit) |
| `DELETE /sessions/{id}` (api.py:451) | SessionHistoryScreen.js:165 | sessions/page.js:92 | ✅ |
| `GET /reports/{token}` (api.py:488, no auth, service role) | — | report/[token]/page.js:43 | ✅ **deployed + verified** (35-01 prod probe 2026-06-17: `/reports/{valid}` 200, junk → route-specific 404). Was the 06-12 deploy-drift ❌ in §5.1 — now resolved |
| `GET /devices`, `PATCH/DELETE /devices/{chip_id}` (api.py:566-673) | DevicesScreen.js:27,45,64 | — (descoped from web) | ✅ |
| `POST /athletes` (api.py:676) | AthletesScreen.js:60 | AddAthleteModal.js:17 | ✅ |
| `POST /billing/checkout-session`, `/billing/portal-session`, `GET /billing/status`, `POST /billing/webhook`, `GET /billing/complete` (api.py:760-923) | **none** | **none** | ⚠️ No client UI calls billing (only iOS 402 *handling* exists, RecordScreen.js:174). Intentional per Phase 23 decision (checkout not exposed), but checkout/portal are currently unreachable by any user |

### 4.3 Supabase — code ↔ schema ↔ clients

| Contract | Verdict | Evidence |
|----------|---------|----------|
| Project ref `ujrotuijxrbscjhzekjk` consistent | ✅ | mobile config.js:5, web `.env.local` (`NEXT_PUBLIC_SUPABASE_URL`), Railway env (`SUPABASE_URL`) |
| Railway URL consistent | ✅ | mobile config.js:3; web lib/api.js:3-5 and report/[token]/page.js:9-10 (env override + same fallback) |
| Committed SQL reproduces live DB | ❌ | **No.** Code references columns absent from `supabase/*.sql` — see §5.2 |
| iOS reads: `sessions`, `athletes`, `coaches` via anon client + RLS | ✅ | AthletesScreen.js:31-42, SessionHistoryScreen.js:120, ReportCardScreen.js:83, AuthContext.js:18 |
| Web reads: `athletes`, `sessions`, `reports` via anon client + RLS | ✅ | app/page.js, sessions/, compare/, ReportBuilder.js:20, ReportSendList.js:25 |
| "Web writes go through Railway" (Phase 23 decision) | ⚠️ | True for athletes + session metadata, **except `reports`**: insert/update/delete go directly via supabase-js (ReportBuilder.js:49, ReportSendList.js:41,66). Works because patch_03's RLS policy is `FOR ALL`; it's a deliberate-looking exception, just not recorded in the decision log |
| Parent report pages get data only via service-role endpoint (no anon RLS on `reports`) | ✅ | patch_03 comment + api.py:488 docstring agree |
| `raw-csvs` storage bucket | ✅ | api.py:247 upload; iOS only uploads via `/process` |

### 4.4 Pipeline constants

| Constant | Verdict | Evidence |
|----------|---------|----------|
| `WHEEL_DIAMETER_M = 0.06` | ✅ single-sourced | vel_acc_extraction.py:27. The old duplicate (`WHEEL_CIRC_M` in RecordScreen.js) was **removed** with the live velocity graph in Phase 21-02 — grep of mobile src finds no wheel constant. Root CLAUDE.md still claimed it existed (fixed in this audit) |
| `TARGET_FS_HZ = 100` | ✅ | vel_acc_extraction.py:36; api.py:136 calls `run_pipeline(df, 100.0)`; export endpoint and iOS exportCsv both assume `i/100` (api.py:382, ReportCardScreen.js:168) |
| `EXCLUDED_SEGMENTS` | ✅ safe | Empty (vel_acc_extraction.py:19-22) **and** only applied in the standalone `process_file()` path (vel_acc_extraction.py:223-230) — `run_pipeline()` used by api.py never applies it |
| Sample rate ~270 Hz | ✅ | firmware `SAMPLE_INTERVAL_US 3704` (ESP_32_V5.ino:104); pipeline infers native rate from data, doesn't hardcode it |

### 4.5 Tests and builds (run 2026-06-12)

| Check | Result |
|-------|--------|
| `pytest tests/` | ✅ **30/30 passed** in 7.9 s (test_api.py 15, test_metrics.py 15; includes `TestPublicReport` for `/reports/{token}`) |
| `npm run build` in `web/` | ✅ Clean — Next.js 16.2.9, TypeScript pass, 10 routes (8 static, `/app/sessions/[id]` + `/report/[token]` dynamic) |
| Railway `GET /health` | ✅ 200 `{"status":"ok"}` |
| Railway `GET /reports/<dummy>` | ❌ (2026-06-12) Generic `{"detail":"Not Found"}` → ✅ **RESOLVED 2026-06-17** — now returns route-specific `"Report not found"`; route deployed (§5.1) |

---

## 5. What's broken or drifted

Ordered by impact. Nothing here was fixed in this audit (documentation-only pass) —
each row is a candidate for `/paul:consider-issues`.

### 5.1 Railway is running a pre-Phase-24 api.py ❌ → ✅ RESOLVED 2026-06-17
~~Live probe (§4.5): `/reports/{token}` does not exist on the deployment. Every parent
report link 404s in production.~~ **RESOLVED:** Railway is GitHub-auto-deploy; current api.py
is live. 35-01 prod probe (2026-06-17): `/reports/{valid}` 200, junk → route-specific 404;
`/coach/chat` 401 unauth; and (2026-06-18) `/sessions/{id}/ratings` 401 unauth, bogus route
404 — i.e. all Phase 24/31/33/36 endpoints are deployed. Parent links work in production.

### 5.2 Committed Supabase SQL cannot rebuild the live database ❌
The live DB was evolved through SQL-editor migrations that were never committed.
Columns/tables referenced by working code but absent from `supabase/schema.sql` + patches:

| Table | Missing from committed SQL | Referenced by |
|-------|---------------------------|---------------|
| `sessions` | `name`, `notes`, `is_starred`, `device_id` as **TEXT chip-id** (schema.sql:56 declares `UUID REFERENCES devices(id)`) | api.py:268-280, PATCH allowed-fields, iOS/web session cards |
| `devices` | Entire live shape: `chip_id` (PK-ish, TEXT), `coach_id`, `name`, `firmware_version`, `last_seen_at`. Committed shape (schema.sql:18-25) is the abandoned QR-claim design: `serial_number`, `mac_address`, `team_id`, `label` | api.py:258-263, 645-650; DevicesScreen |
| `coaches` | Billing columns: `stripe_customer_id`, `subscription_tier`, `subscription_status`, `athlete_limit`, `device_limit`, `monthly_session_limit` | api.py:178, 782-790, 854-860, 886-922 |
| `athletes` | `coach_id` (api.py:723 inserts it; api.py:700 filters on it) | api.py, web athletes pages |

The Phase 12-01, 14-01, and 15-01 migrations exist only in the live DB (and possibly in
old PLAN files under `.paul/phases/`). **Risk:** a new environment, a disaster recovery,
or RLS reasoning from the committed files will all be wrong.
**MITIGATED 2026-06-12 (post-audit):** `supabase/patch_04_backfill.sql` reconstructs the
missing migrations from code evidence (guarded/idempotent, documentation-first). It is
inference, not a dump — verify column types/defaults against the dashboard, or replace
with `supabase db dump` output for ground truth.

### 5.3 Version control excludes production-critical files ❌ (single-machine loss risk)
`git status` looks deceptively clean because `.gitignore` swallows whole production
surfaces. Verified via `git ls-files` + `git check-ignore` (2026-06-12):

**myswimcoach — NOT in git** (exist only on this machine):
- `ESP_32_V5/` — the production firmware (`/ESP_32_V5` ignore rule; all firmware dirs ignored)
- `tests/` — the entire 30-test suite (`/tests` rule)
- `supabase/patch_03_parent_reports.sql` — swallowed by the `/supabase` rule (schema.sql
  + patch_01/02 predate the rule and remain tracked; patch_03 did not survive it)
- `scripts/`, `.paul/` (project management — possibly intentional)
- Every `*.md` except README.md: `CLAUDE.md`, `STRATEGY.md`, `COACHING_PHILOSOPHY.md`,
  and **this audit document** are all untracked. Same for `*.txt` (except requirements.txt)
  and `*.html`.

**swimnetics-mobile — untracked** (never committed, `??` in git status):
`src/components/`, `src/context/` (BleContext!), `src/lib/`, `src/screens/LoginScreen.js`,
`src/screens/RecordingConfigScreen.js`, `src/screens/DevicesScreen.js`, `.easignore`,
`commands.txt` — i.e. most of the app's source. The GitHub remote (if pushed) does not
contain a buildable app.

~~A disk failure loses the firmware, the tests, the latest schema migration, all project
docs, and most of the iOS app.~~ **RESOLVED 2026-06-12 (post-audit, user-requested):**
myswimcoach commits `0b45ce9` + `4f152f7` track firmware/tests/docs/patch_03/web agent
docs and fix the ignore rules; swimnetics-mobile commit `6abcbaa` tracks all of src/.
Still open: (a) **swimnetics-mobile has NO git remote** — commits are local-only until a
(private) remote is added and pushed; (b) `.paul/`, `STRATEGY.md`, `COACHING_PHILOSOPHY.md`
remain deliberately untracked because the GitHub repo is **public** — they exist only on
this machine, so back them up by other means.

### 5.4 Orphan / unreachable endpoints ⚠️
- `GET /sessions/{id}/export` (api.py:312): no iOS or web caller; iOS re-implements the
  identical CSV client-side (ReportCardScreen.js:152-170). Either wire web's session
  page to it or delete it.
- Billing checkout/portal (api.py:760, 802): no client reaches them. Deliberate for the
  website ($15/swimmer is informational), but there is **no path for any customer to
  subscribe** today. Tracked implicitly by PROJECT.md "checkout intentionally not exposed".

### 5.5 Phase 14 firmware-version loop never closed ⚠️
Firmware publishes FW 1.1.0 via the `6E400005` read characteristic (ESP_32_V5.ino:555);
api.py accepts `firmware_version` on `/process` and upserts it onto `devices`
(api.py:261); DevicesScreen displays `firmware_version`. But the iOS app **neither reads
the characteristic nor sends the field** (grep of mobile src: zero hits), so the value is
permanently null via the app. One small iOS change (read characteristic in BleContext,
pass through RecordScreen upload params) completes it.

### 5.6 AI-context files were stale (fixed in this audit's Task 3) ✅→
- Root `CLAUDE.md`: claimed `WHEEL_CIRC_M` lives in RecordScreen.js (removed Phase
  21-02); claimed PATCH `/sessions` accepts `stroke_type` (it doesn't, api.py:418);
  endpoint list omitted `/reports`, `/devices`, `/athletes`, `/billing/*`, `/export`;
  no mention of `web/`, `supabase/`, `coach.py`.
- Mobile `CLAUDE.md`/`AGENTS.md`: documented the **old live-streaming protocol**
  (14-byte packets, START/STOP only, scan-in-RecordScreen state machine, live velocity
  graph) — all superseded by buffer-and-dump + BleContext (Phases 21–22); missing
  BleContext.js and DevicesScreen.js entirely.

### 5.7 Minor
- ~~`DELETE /sessions/{id}` deletes only the DB row — raw CSV orphaned forever.~~
  **FIXED 2026-06-12 (post-audit):** delete_session now captures `raw_csv_path` before
  the row delete and removes the storage object (non-fatal). Pre-fix orphans from
  earlier deletions remain in the bucket — clean manually if storage cost matters.
- `requirements.txt` ships Streamlit-only deps (streamlit, plotly, matplotlib, stumpy,
  anthropic) to Railway — slow builds/bigger image, no breakage. `python-dotenv` is used
  by fetch_sessions.py:23 and pipeline_view.py:28 but isn't listed (works locally only
  because it happens to be installed).
- Local `.env` has no `SUPABASE_ANON_KEY`, so api.py auth verification 503s when run
  locally against real tokens (api.py:53). Tests don't care (conftest mocks supabase and
  overrides `require_auth`). Add the anon key locally if you ever run uvicorn + real JWTs.
- `landing/index.html` is superseded by `web/` — delete candidate after Vercel cutover.
- Web `reports` writes bypass the "writes via Railway" convention (§4.3) — works via
  RLS, but record the exception or route through the API for consistency.

---

## 6. What's working (verified)

- **Signal pipeline + metrics**: 30/30 tests pass, including real-session fixtures and
  edge cases (flat/short signals). Kick metrics remain flagged unreliable by design
  (`kick_metrics_reliable = False` always).
- **BLE buffer-and-dump contract**: firmware and iOS parser agree byte-for-byte with the
  STATE.md locked spec (§4.1) — *on paper*; on-device UAT is still pending (§7).
- **Railway deployment**: healthy, serving the pre-Phase-24 surface (process/sessions/
  devices/athletes/billing endpoints).
- **Web build**: production build clean; portal pages wired to live Supabase reads and
  Railway writes; report builder/send-list/parent-page complete locally.
- **Auth chain**: Supabase JWT → `auth.get_user()` verification → coach-row ownership
  checks on every mutating endpoint (consistent `coach_row_id` pattern across api.py).
- **Tier enforcement**: session/device/athlete limits enforced in `/process` and
  `POST /athletes` (api.py:183-241, 696-714) with 402s handled in iOS.

## 7. What's unverified (pending, not broken)

| Item | Why pending | Where tracked |
|------|------------|---------------|
| All on-device behavior from Phases 12–21 (BleContext persistence, pairing UX, retrieval flow on real hardware) | EAS build credits exhausted — no TestFlight build since the rewrite | STATE.md deferred issues; run 21-02-PLAN Task 3 checkpoint when credits renew |
| Phase 22-02 video-overlay demo | Same EAS blocker (Task 1/ffmpeg done) | 22-02-PLAN parked checkpoint |
| Vercel deployment of `web/` | A Vercel project exists but serves the legacy `landing/` placeholder (probed 2026-06-12) — `web/` not deployed; runbook exists from Phase 23-03 | STATE.md user follow-ups (deploy + DNS cutover) |
| Email dispatch of parent reports | Deliberately deferred (mailto/copy-link shipped) | Phase 24 decision — Resend slots into ReportSendList |
| Freestyle segmentation | Research ongoing — wavelet/CWT spike (16-04) is the only standing candidate | .paul/phases/16-*, wavelet_spike.py |
| Git state | Phases 21–24 work uncommitted in both repos (user runs git) | STATE.md user follow-ups |

## 8. Deploy state (2026-06-12)

| Surface | State |
|---------|-------|
| Railway (`swimnetics-api-production.up.railway.app`) | Live, healthy, **current code** — Phase 24/31/33/36 endpoints all deployed + verified (35-01/35-03). GitHub-auto-deploy on push to main |
| Vercel | ✅ **Live serving `web/`** — marketing + portal + parent pages verified (35-01, 2026-06-17). (Was the legacy `landing/` placeholder on 2026-06-12.) |
| Supabase (`ujrotuijxrbscjhzekjk`) | Live; schema = committed SQL **+ uncommitted SQL-editor migrations** (§5.2); patch_03 applied by user 2026-06-11 |
| TestFlight | EAS build w/ Phase 36 ratings UI + Phase 34/26 screens installed (35-02, 2026-06-18); recording-gated checks pending a post-resolder build |
| Firmware on device | 1.1.0 buffer-and-dump (ESP_32_V5) |
| Version control | ⚠ Both repos missing production files from git — firmware, tests, patch_03, most mobile src/ (§5.3) |

## 9. Picking this up cold (future AI: start here)

**Read in this order:**
1. `.paul/STATE.md` — current position, decision log, locked BLE protocol, deferred issues
2. This file — what actually connects to what, and what's drifted
3. Root `CLAUDE.md` — pipeline/metrics reference (refreshed 2026-06-18: + ratings.py, /coach/chat, /sessions/{id}/ratings)
4. `swimnetics-mobile/CLAUDE.md` — iOS specifics (refreshed 2026-06-12; pre-dates the 35-02 ratings UI + iPhone-first change)

**Run things:**
```bash
pytest tests/                          # backend suite (mocked supabase, no network)
uvicorn api:app --reload --port 8000   # API (needs SUPABASE_* env for auth/saves)
python vel_acc_extraction.py raw/x.csv # pipeline standalone
streamlit run app.py                   # desktop analysis tool
cd web && npm run dev                  # website + portal (needs web/.env.local)
```

**Gotchas that will bite you (all earned the hard way — details in STATE.md decisions):**
- iOS: Hermes can't import supabase-js `.mjs` → Metro CJS redirect in metro.config.js.
  `fetch+FormData` upload fails on RN 0.85 → `FileSystem.uploadAsync` MULTIPART.
  `expo-file-system/legacy` import required. No Mac: never `expo prebuild`; native dirs
  are edited directly; new native deps need an EAS build (credits currently exhausted).
- BLE: subscribe **before** writing commands; RX char is write-with-response; protocol
  is locked (STATE.md block) — change firmware and iOS together or not at all.
- Backend: RLS INSERT needs `WITH CHECK` (USING is ignored); `devices.coach_id` has no
  FK (Supabase editor rejected it — ownership is application-enforced);
  `_clean()` in api.py exists because metrics emit numpy types + NaN.
- Signal: **no post-gradient filtering** — inter-stroke velocity troughs are real signal.
  `segment_cycles` anchors on breaststroke's glide trough; it will not transfer to
  freestyle (that's the whole Phase 16 research thread).
- Supabase: do **not** trust `supabase/schema.sql` for the live column list (§5.2).
- Git: do **not** trust a clean `git status` — `.gitignore` swallows `*.md`, `*.txt`,
  `*.csv`, firmware dirs, `/tests`, `/supabase` (§5.3). New docs, migrations, and
  firmware changes will silently never be committed unless un-ignored or force-added.

**Where state lives:** `.paul/` (project loop + decisions), `~/.claude/.../memory/`
(assistant memory), Railway env vars (secrets), `web/.env.local` (web env),
`src/config.js` (mobile constants — hardcoded, no env system).
