---
phase: 86-session-clock-accuracy
plan: 02
subsystem: mobile
tags: [ble, clock-sync, cristian, video-overlay, react-native, epoch-ms]

# Dependency graph
requires:
  - phase: 86-01
    provides: "the three POST /process form fields, patch_14's columns, and GET /time — all three LIVE and verified before this close (see Verification Results)"
  - phase: 84-mobile-user-feedback
    provides: "the goSignalSRef / form-field-on-the-swim's-own-request pattern; its commit 6b24c79 lifted this plan's mobile-repo gate"
  - phase: 74-ble-dump-reliability
    provides: "MAX_RETRIEVAL_ATTEMPTS / RETRIEVAL_STALL_MS and the stalled-retry path the probe burst must not race"
provides:
  - "swimnetics-mobile/src/lib/sessionClock.js — pure, zero-import clock math (Cristian's algorithm)"
  - "RecordScreen.js — META probe burst, BLE-corrected session start, concurrent /time offset probe, three new form fields"
  - "scratch/session_clock_check.mjs — headless harness + cross-repo constant guard (45 checks)"
affects: [86-03-tap-test, swimclips-integration, video-overlay, go-signal-marker]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "best-of-N minimum-RTT probing (Cristian's algorithm) instead of a single round trip"
    - "generation ref (probeGenRef) to abort an in-flight async burst the retry path superseded"
    - "pure zero-import module + data:-URL import so a runner-less RN tree is still headlessly testable"
    - "measured-and-reported, never applied — a diagnostic must not change what the primary number means"

# Metrics
tests-added: 45      # scratch/session_clock_check.mjs (mobile tree has no pytest)
tests-passing: 45
backend-suite: 566   # unchanged — no tracked backend file was modified
---

# Phase 86 Plan 02: Session Clock Accuracy (mobile round-trip + send) Summary

**Status: CLOSED 2026-09-01. Applied in an unrecorded session on 2026-08-31; this SUMMARY was
re-derived from the diff and by re-running every gate, not written from an APPLY transcript.**

## Reconciliation posture (read this first)

The code for this plan was found on disk, uncommitted and with no SUMMARY — the same found-work
situation as 88-05 and 84-02. Nothing here is taken on trust from a transcript that does not exist.
Every claim below was re-established from the diff or by running the gate named beside it, from a
tree that was clean against `HEAD` for all tracked files (only untracked files existed in
`myswimcoach`, so nothing was quietly fixed up during this reconciliation).

Three things the **ROADMAP row for Phase 86** still asserted as blockers were checked rather than
believed, and **all three were already satisfied**. (STATE.md's own owed-item 27 had already been
self-corrected on 2026-08-31 and was accurate; the ROADMAP row was never updated to match, which is
exactly the drift this reconciliation exists to catch.)

| Asserted blocker | Checked how | Actual state |
|---|---|---|
| "86-01 is uncommitted, so it is not on Railway" | `git log` / `git rev-list --left-right --count` | **False.** `861040b`, an ancestor of `origin/main`; `main` and `origin/main` are 0/0 |
| "patch_14 written and NOT applied" | live PostgREST select of each column with the service role | **False.** All three columns exist and return `null` |
| "backend live on Railway before the 86-02 build" (deploy ordering) | `GET https://swimnetics-api-production.up.railway.app/time` | **Met.** HTTP 200, `{"server_utc_ms":...}` |

## Accomplishments

1. **The live overlay bias is fixed.** `deviceNowUs` is captured on the ESP32 when it *builds* the
   META reply, so the inbound BLE leg (20-80 ms) was silently attributed to the encoder and
   `sessionStartPhoneMs` came out biased **late** by roughly one one-way flight time. The one-shot
   META is replaced by a burst of up to 10 timed round trips; the **minimum**-RTT probe wins
   (Cristian's algorithm) and the start is corrected by `minRtt/2`.
2. **The number is now sent.** All three fields ride the swim's own `POST /process` — never a
   follow-up PUT, which is the silent-loss shape 84-02 exists to avoid.
3. **The phone measures its own offset against `GET /time`** concurrently with the ~20 s dump, so it
   costs zero added wall clock, and reports it without ever applying it.
4. **`sessionClock.js` is pure with zero imports**, which is the only thing that makes it checkable
   from a tree with no test runner (84-03 G28) — `scratch/session_clock_check.mjs` imports it
   through a `data:` URL.

## Acceptance Criteria Results

| AC | Verdict | Evidence |
|----|---------|----------|
| AC-1 start corrected by measured one-way latency | PASS | harness fixture: `corrected=1756499970030` vs `uncorrected=1756499970060`, earlier by exactly `rtt/2` = 30 ms |
| AC-2 probe can fail completely without costing the swim | PASS (code-read) | `runProbeBurstThenDump` `continue`s a null probe; `resolveSessionClock()` returns early on no probes; `writeCmd('DUMP')` is unconditional after it |
| AC-3 `session_start_utc_ms` sent as an INTEGER string | PASS | harness asserts the literal `String(Math.round(sessionStartUtcMsRef.current))`, that the result contains no `.`, and that `String()` alone would *not* be safe |
| AC-4 server offset best-effort, never blocks | PASS (code-read) | the `/time` probe is an un-awaited IIFE with a 2 s `AbortController` and an empty `catch`; harness asserts it sends no `Authorization` header |
| AC-5 phone's window agrees with the server's | PASS | harness parses `_EPOCH_MS_FLOOR` / `_EPOCH_MS_FUTURE_SLACK_MS` out of `api.py` and asserts equality: `1577836800000` and `172800000` both sides |
| AC-6 nothing else in retrieval changes | PASS | `probeGenRef` guard returns before any `writeCmd('DUMP')`; harness pins `MAX_RETRIEVAL_ATTEMPTS === 2` and `RETRIEVAL_STALL_MS === 8000` |
| AC-7 verified on a device | **OWED** | build-gated — needs an EAS build; rides Phase 84's owed batch |

## Verification Results

- `node scratch/session_clock_check.mjs` -> **45/45 passed**
- `python -m pytest tests/ -q` -> **566 passed**, 1 warning (pre-existing all-NaN slice) — identical
  to Phase 88's close, as expected: `git status` showed **no modified tracked files** in
  `myswimcoach`, so `api.py`, `web/` and every other standing harness input are untouched by this
  plan. The other standing harnesses (`anchor_check`, `stroke_toggle_check`, `overlay_render_check`,
  `marketing_render_check`, `unit_check`, `split_picker_check`) were **not** re-run, and the reason
  is a proof rather than an assumption: their inputs are provably unchanged against `HEAD`.
- Live `GET /time` -> HTTP 200; live `sessions` select -> all three patch_14 columns present, `null`.

**A trap avoided during the first pytest attempt, recorded because it will recur:**
`.venv/Scripts/python.exe` has **no pytest installed**, and `python -m pytest ... | tail` returns
**exit code 0 from the pipe** even when the module is missing. The suite silently did not run. The
working interpreter is the conda one (`C:\Users\TonyZheng\miniconda3\python.exe`, pytest 9.0.2).

## Files Created/Modified

| File | Repo | Change |
|------|------|--------|
| `src/lib/sessionClock.js` | swimnetics-mobile | **new**, 6.6 KB — pure clock math |
| `src/screens/RecordScreen.js` | swimnetics-mobile | +211 / -53 |
| `scratch/session_clock_check.mjs` | myswimcoach | **new**, 11.8 KB — 45 checks |
| `.paul/phases/86-session-clock-accuracy/86-02-PLAN.md` | myswimcoach | **new** (was untracked) |

## Decisions Made

- **D1: minimum RTT, not mean or median.** The minimum is the sample least contaminated by queueing
  delay, which is the whole basis of Cristian's algorithm. Asserted by the harness against a fixture
  where the winner is neither first nor last.
- **D2: the offset is measured and reported, NEVER applied.** Applying it would make the meaning of
  `session_start_utc_ms` depend on whether an unrelated network call happened to succeed at a
  poolside phone. One definition, every session: "phone clock, corrected for BLE flight only."
  Sign convention: **positive = phone ahead of server**.
- **D3: the retry path re-probes ONCE, not a fresh burst.** A retry keeps its META-then-DUMP shape;
  a successful retry probe joins the same array and the best is recomputed, so a lower RTT is a free
  improvement and a worse one changes nothing.
- **D4: the GO-marker resolution MOVED** out of the META handler into `resolveSessionClock()` so it
  resolves against the *corrected* start. `go_signal_s` therefore shifts by ~`rtt/2` — tens of ms,
  far below the coach thumb latency the metric already embeds.
- **D5: a stray-reply fallback exists but never uploads.** If every probe times out yet a META reply
  eventually lands, the pre-86-02 *uncorrected* formula still feeds the in-app overlay so it has a
  t=0 — but the refs stay `null`, so a start whose flight time was never measured is never sent.

## Issues Encountered

None blocking. The plan's own load-bearing `Math.round` hazard and its cross-repo constant-drift
hazard were both already designed out in the found code, and both are pinned by harness assertions.

## Next Phase Readiness

**86-03 (tap test) is the only remaining plan and is not yet written.** Until it runs, `rtt/2`
remains an **estimate** — bounded by two verified facts (`processPending()` is the first call in a
free-running `loop()` with no `delay` while not recording, and both BLE directions are acknowledged)
but not measured against ground truth.

**AC-7 and 86-03 both need the same EAS build**, which rides Phase 84's owed batch. Nothing in this
plan is on a device yet.

**No backfill is possible.** All 99 pre-Phase-86 sessions hold `NULL` permanently; consumers must
read `NULL` as *unknown* and must never substitute `recorded_at`, which is upload time (STATE item
22, deliberately unfixed).
