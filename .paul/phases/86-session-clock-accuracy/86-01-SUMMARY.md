---
phase: 86-session-clock-accuracy
plan: 01
subsystem: api
tags: [fastapi, supabase, postgres, clock-sync, video-overlay, epoch-ms]

# Dependency graph
requires:
  - phase: 84-mobile-user-feedback
    provides: "the go_signal_s Form(None) + _post_csv(go_signal_s=None) pattern this mirrors; its commit (54cb8d1) and Railway deploy lifted 86-01's APPLY gate"
  - phase: 70-qr-recording-slate
    provides: "the recording_token conditional-subscript insert precedent that made patch_14 and the api.py deploy order-independent"
provides:
  - "supabase/patch_14_session_clock.sql — three nullable sessions columns (UNAPPLIED; user runs it)"
  - "POST /process accepts + persists session_start_utc_ms, sync_error_ms, clock_offset_ms"
  - "GET /time — unauthenticated, zero-I/O server clock in epoch ms"
  - "_valid_session_start_ms() sanity window + _finite_or_none() diagnostic coercion"
affects: [86-02-mobile-round-trip, 86-03-tap-test, swimclips-integration, video-overlay]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "conditional-subscript insert keys (absent key == explicit NULL) to decouple code deploy from schema patch"
    - "drop-and-log, never 422, on any request that carries the unrepeatable swim"

key-files:
  created: [supabase/patch_14_session_clock.sql]
  modified: [api.py, tests/test_api.py]

key-decisions:
  - "D1: keys assigned by subscript, NOT in the session_row literal — deviates from Task 2 as written; makes patch_14 and the Railway deploy order-independent and keeps TestSchemaContract honest"
  - "D2: sanity window = 2020-01-01 floor to now+48h — catches both seconds-for-ms and micros-for-ms with zero realistic false rejections"
  - "D3: NaN/inf dropped from the two diagnostics (_finite_or_none) — not in the plan; they break JSON on insert"

patterns-established:
  - "A new nullable column's writer must be deployable before its patch is applied"
  - "Unauthenticated is sometimes a correctness requirement, not an oversight — pin the reason in a comment AND an AC"

# Metrics
duration: ~5min execution (APPLY), ~15min reconciliation (UNIFY)
started: 2026-08-31T07:53:48Z
completed: 2026-08-31T08:35:00Z
---

# Phase 86 Plan 01: Session Clock Accuracy (backend) Summary

**The backend can now store the absolute UTC instant of encoder sample #0 with its two measured error bars, and hand the phone a zero-I/O clock reference to measure itself against — three optional form fields on `POST /process`, three unapplied `sessions` columns, and an unauthenticated `GET /time`.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~5 min APPLY (file mtimes 00:53:48–00:58:45 local) + UNIFY reconciliation |
| Started | 2026-08-31T07:53:48Z |
| Completed | 2026-08-31T08:35:00Z |
| Tasks | 4 of 4 completed |
| Files modified | 3 (1 created, 2 modified) |
| Test suite | 505 → **520** (+15, zero pre-existing failures) |

⚠ **APPLY ran in a prior session; this UNIFY reconciled from the tree, not from execution memory.** Every claim below was re-verified against the working tree during UNIFY rather than recalled — commands and outputs are in Verification Results.

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Absolute start accepted and persisted | **Pass** | `test_valid_start_is_persisted` — reaches the insert unchanged and as `int`, not `str`. ⚠ Proven against the **mocked** insert only; patch_14 is unapplied, so this is untested against the live DB |
| AC-2: Field is optional, existing callers unaffected | **Pass** | Three tests. `test_absent_start_changes_no_other_stored_field` pins the exact 13-key pre-change key set, which is stronger than the AC asked for |
| AC-3: Bad value dropped, swim is not | **Pass** | Parametrized over 4 values — negative, zero, **seconds-not-ms**, **micros-not-ms**. Plan asked for 3; the micros case was added. 200 + key absent + `velocity_profile` still saved |
| AC-4: `GET /time` answers without auth | **Pass** | 4 tests. `test_handler_performs_no_network_io` monkeypatches `_get_supabase`, `_get_supabase_admin` and `create_client` to raise — the no-I/O half is **proven, not asserted in prose**. Live-checked during UNIFY: `{'server_utc_ms': 1788163867182}` vs host `1788163867185` (3 ms) |
| AC-5: Error bars ride along, independently nullable | **Pass** | 3 tests incl. `test_error_bars_do_not_gate_on_a_valid_start` — a **rejected** start with a recorded offset still persists both diagnostics, the forensic case they exist for |
| AC-6: No regression | **Pass** | `pytest tests/` → **520 passed**, 1 pre-existing numpy `All-NaN slice` warning in `test_metrics.py`. +15 is exactly the count of new tests (11 + 4), so no pre-existing test was altered or lost |

## Accomplishments

- **The absolute-time seam exists end-to-end on the server side.** `session_start_utc_ms` (BIGINT epoch ms), `sync_error_ms` and `clock_offset_ms` are accepted, validated, and written. 86-02 can now send them.
- **`GET /time` is live and provably I/O-free**, which is the whole point — the phone derives its clock offset from RTT/2 against this endpoint, so any network call inside the handler would land inside the interval being measured.
- **A second deploy-ordering hazard was found during APPLY and designed out** (see Deviations D1). The plan as written would have made `api.py` un-deployable until the user ran patch_14.
- **The unrepeatable-measurement posture is now pinned in code and in tests**, not just in the plan: a malformed clock annotation costs the annotation, never the session.

## Task Commits

**None — the work is uncommitted in the working tree.** `git status` shows `M api.py`, `M tests/test_api.py`, `?? supabase/patch_14_session_clock.sql`. The repo's standing pattern for this phase family has been whole-tree commits at transition (see `20c0432`), and Phase 86 is not complete (86-02, 86-03 unwritten).

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Task 1: patch_14 | *uncommitted* | feat | 3 nullable columns + a 30-line WHY header |
| Task 2: `/process` fields | *uncommitted* | feat | 3 Form fields, validation, conditional persist |
| Task 3: `GET /time` | *uncommitted* | feat | unauthenticated, zero-I/O |
| Task 4: tests | *uncommitted* | test | +15 tests across 2 classes |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `supabase/patch_14_session_clock.sql` | Created | `session_start_utc_ms` BIGINT, `sync_error_ms` + `clock_offset_ms` DOUBLE PRECISION, all `IF NOT EXISTS`. Header records why epoch-ms not timestamptz, why NULL means *unknown* and never `recorded_at`, and why no backfill can ever exist. **NOT APPLIED** |
| `api.py` | Modified (+84) | `_EPOCH_MS_FLOOR`/`_EPOCH_MS_FUTURE_SLACK_MS`, `_valid_session_start_ms()`, `_finite_or_none()`, `GET /time` at `api.py:162`, 3 Form fields at `api.py:191`, validation at `api.py:307`, conditional insert keys at `api.py:444` |
| `tests/test_api.py` | Modified (+167) | `_post_csv` gains 3 optional kwargs (~20 existing callers untouched); `TestSessionClockPersisted` (11 tests) and `TestServerTimeEndpoint` (4 tests) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **D1: Insert keys assigned by subscript, not in the `session_row` literal** | The plan's Task 2 said "add all three to the sessions insert payload". Done literally, deploying `api.py` before the user applies patch_14 would break **every upload** (PostgREST rejects unknown columns), and it would fail `TestSchemaContract`, whose static extractor checks every column named in an `.insert({…})` literal against `supabase/live_schema.json` — hand-adding them to the snapshot would make the guard lie. The Phase 70 `recording_token` precedent three lines above already solved this | **patch_14 and the Railway deploy can land in either order.** Absent key ≡ explicit NULL (nullable, no default), so the AC-2/AC-5 "store NULL when absent" contract is met either way |
| **D2: Sanity window = 2020-01-01 floor, now + 48 h ceiling** | The two realistic client unit errors land nowhere near a real "now": seconds-for-ms lands in 1970, micros-for-ms lands tens of thousands of years out. A window this wide costs nothing in false rejections even against a badly skewed phone clock | Encoded as `_EPOCH_MS_FLOOR` / `_EPOCH_MS_FUTURE_SLACK_MS` with the reasoning in a comment. 86-02 must not send seconds |
| **D3: NaN/inf dropped from both diagnostics** | Not requested by the plan. `float('nan')` serializes to invalid JSON on insert and would fail the whole upload — which would violate AC-3's own principle (never lose the swim over a clock annotation) | `_finite_or_none()` |
| **D4: No commit** | 86-02/86-03 unwritten, phase not complete, and the phase family's pattern is a whole-tree commit at transition | Work sits in the tree; deploy ordering (below) is the live risk |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 2 | Both prevent a production break the plan would have caused |
| Scope additions | 2 | One extra bad-value case, one extra `/time` test — both tighten existing ACs |
| Deferred | 0 | — |

**Total impact:** No scope creep. The one structural deviation (D1) contradicts Task 2's literal wording and is strictly safer than what was written.

### Auto-fixed Issues

**1. [Deploy ordering] Task 2's literal insert would have made `api.py` un-deployable before patch_14**
- **Found during:** Task 2
- **Issue:** Adding the three keys to the `session_row` dict literal means PostgREST sees unknown columns on a DB without patch_14 → every upload 400s. Also fails `TestSchemaContract`'s static `.insert({…})` extractor
- **Fix:** Conditional subscript assignment, mirroring `recording_token` (Phase 70) three lines above
- **Verification:** Confirmed the contract extractor ignores the subscript form; suite green
- **Commit:** uncommitted

**2. [Serialization] NaN/inf in a diagnostic would fail the insert**
- **Found during:** Task 2
- **Issue:** `float('nan')` is not valid JSON; an insert carrying it fails, losing the session
- **Fix:** `_finite_or_none()` drops non-finite values to None
- **Verification:** covered by the float-typed AC-5 assertions
- **Commit:** uncommitted

### Scope Additions

- **AC-3 parametrized over 4 values, not 3** — added `1756500000123456` (microseconds-for-milliseconds) alongside the plan's negative / zero / seconds cases.
- **`GET /time` got 4 tests, not 1** — added the monkeypatched no-I/O proof, a host-clock bracket, and `test_auth_header_is_neither_required_nor_rejected` (a client that sends a garbage Bearer must be neither 401ed nor verified).

### Plan verification checklist — one literal miss

The plan's checklist says `grep -n "recorded_at" api.py` **still returns nothing**. It now returns **one line, `api.py:301` — a comment** stating that a reader must never substitute `recorded_at` because it is upload time. `recorded_at` is still never *set*, so the boundary holds; the check's literal form is what changed, not the behaviour. A future reader running that grep should expect the comment.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| APPLY gate on Phase 84 | **Lifted, verified not assumed:** backend clean at `54cb8d1` = `origin/main`; mobile clean at `6b24c79` = `origin/main`; deployed `/openapi.json` returns 200 containing `go_signal_s`, so 84-02's backend is genuinely live on Railway |
| `/process` insert vs unapplied schema | D1 |
| APPLY executed in a prior session, no execution memory at UNIFY | Reconciled entirely from the tree: full `git diff`, `pytest tests/`, live `TestClient` call on `/time`, `python -c "import api"` |

## Verification Results

```
$ python -m pytest tests/ -q
520 passed, 1 warning in 75.89s          # 1 pre-existing numpy All-NaN warning

$ python -c "import api"
import ok

$ grep -c "ADD COLUMN" supabase/patch_14_session_clock.sql
3

$ python -c "TestClient(api.app).get('/time')"      # no Authorization header
status 200 {'server_utc_ms': 1788163867182}  host 1788163867185     # 3 ms

$ git diff -U0 api.py | grep -E "^[-+].*go_signal_s"
+        # Same drop-don't-422 posture as go_signal_s above, ...   # comment only, no minus line

$ grep -n "recorded_at" api.py
301:        # ... never substitute recorded_at, which is UPLOAD    # comment only, never set

$ git diff --stat
 api.py            |  84 +++++++++++
 tests/test_api.py | 167 +++++++++++++++++++++
```

Boundaries held: no `ESP_32_V5/` change, no `recorded_at` write, `go_signal_s` block untouched, no `metrics_json`/`phases` write, no pipeline file touched, no new dependency, no existing endpoint's auth posture changed.

## Next Phase Readiness

**Ready:**
- 86-02 (mobile round-trip + send) is unblocked at the code level — the three field names, their units, and the `/time` contract are fixed and tested.
- The clock-diagnostic seam (`sync_error_ms`, `clock_offset_ms`) exists for 86-03 to write its measured numbers into.

**Concerns:**
- ⚠ **AC-1 and AC-5 are proven only against the mocked insert.** Nothing has been written to a real column yet.
- ⚠ **Every accuracy figure in this phase remains an ESTIMATE until 86-03 runs.** The 20–80 ms BLE flight time is inferred, not measured.
- ⚠ **No backfill is possible, ever.** All 99 existing sessions hold NULL permanently.
- The work is **uncommitted**, so it is not on Railway.

**Blockers for 86-02:**
1. **User must apply `supabase/patch_14_session_clock.sql`** in the Supabase SQL editor (standing pattern: the user runs patches).
2. **`api.py` must be committed and live on Railway BEFORE the 86-02 app build ships.** If the app sends the fields to an old backend, FastAPI drops the unknown form fields **silently** and those sessions lose their absolute start with no error anywhere. Thanks to D1 these two can happen in either order relative to each other — but both must precede the app build.
3. 86-02 and 86-03 are not yet written (`/paul:plan`). 86-02 collides with 84-02 and 84-05 in `RecordScreen.js`.

---
*Phase: 86-session-clock-accuracy, Plan: 01*
*Completed: 2026-08-31*
