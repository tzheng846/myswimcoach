---
phase: 84-mobile-user-feedback
plan: 02
subsystem: api
tags: [fastapi, react-native, ble, expo-secure-store, reaction-time, race-phase, cross-repo]

requires:
  - phase: 75-report-card-phase-model
    provides: PUT /sessions/{id}/go-signal, _compute_reaction_time, and the PhaseContext
      go_signal_s slot this plan finally populates on the primary path
  - phase: 47-ble-meta-correlation
    provides: sessionStartPhoneMs (encoder t=0 on the phone clock) computed off the 8-byte
      META reply — the correlation 75-04 wrongly documented as deferred
provides:
  - POST /process accepts an optional go_signal_s form field and threads it into PhaseContext
  - a silent, re-pressable coach GO button on both live recording states
  - the Phase-41 race-start sequence switched off for every user (key bumped, not defaulted)
  - reaction_time can compute on the first pass instead of being structurally null
affects: [84-05 items 2+3, the phase-end EAS build, any future reaction_time consumer]

tech-stack:
  added: []
  patterns:
    - "A marker rides the swim's own request as a form field, never a follow-up PUT — a
       fire-and-forget second call is the silent-loss shape item 2 exists to hunt"
    - "Deliberate validation asymmetry: PUT /go-signal 422s, POST /process drops-and-logs,
       because on /process the request carries the irreplaceable artifact"
    - "Disabling a persisted opt-in means bumping the storage key, not flipping the default —
       a flip misses exactly the users who chose the feature"

key-files:
  created: []
  modified:
    - api.py
    - tests/test_api.py
    - ../swimnetics-mobile/src/screens/RecordScreen.js
    - ../swimnetics-mobile/src/lib/startSequencePrefs.js
    - ../swimnetics-mobile/src/screens/RecordingConfigScreen.js

key-decisions:
  - "Checkpoint answered `hide`: SHOW_START_SEQUENCE_TOGGLE = false — the toggle is hidden,
     the code intact. Costs AC-9's four-file blast radius and AC-7's reversibility clause."
  - "A bad go_signal_s is dropped and logged, never 422'd — pinned by AC-3 and five tests"
  - "A GO resolving before t=0 is dropped on the phone, not clamped to 0"
  - "No commit in either repo; both halves sit in their working trees"

patterns-established:
  - "Where a repo has no test runner, parse the changed files with web/node_modules/typescript
     and prove the check is not vacuous with a mutant self-test"

duration: unrecorded (APPLY ran in an unlogged session; reconciled at UNIFY 2026-08-30)
started: unknown
completed: 2026-08-30T02:00:00-07:00
---

# Phase 84 Plan 02: Coach GO Marker + Race-Start Sequence Off Summary

**`reaction_time` stops being structurally null: `POST /process` now takes an optional
`go_signal_s` form field, a silent GO button on both live recording states stamps the send-off and
converts it onto the session clock at META, and the Phase-41 horn — the thing that made an honest GO
stamp impossible — is off for every user via a bumped SecureStore key. Backend proven by 8 new tests
in a 505-green suite; the device half is written, statically verified, and deliberately unverified
until the phase-end EAS build.**

## ⚠ How this plan reached UNIFY

**The APPLY session was never recorded.** 84-01's closing `git status` discovered this plan's code
already substantially applied in both trees with no SUMMARY, no checkpoint answer on record, and its
suite never run. This UNIFY is therefore a **reconciliation of found work against the plan**, not a
write-up of a session I ran. Everything below is evidence gathered at UNIFY on 2026-08-30:

| Question | How it was answered here |
|----------|--------------------------|
| Does the code match the plan? | Read both repos' full diffs against the plan's tasks |
| Does the suite pass? | Ran `pytest tests/` — **505 passed** (baseline 497, +8) |
| Was the checkpoint answered? | Inferred from shipped code (`hide`), not from a recorded answer |
| Is the mobile half sound? | TypeScript parse of all three JS files + token/scope checks |
| Was it verified on a device? | **No.** Deferred to the phase-end build by standing decision. |

Timestamps are not recoverable — the mobile tree is OneDrive-synced and its mtimes cluster at sync
time, not authoring time (84-01's operational note). Duration is recorded as unknown rather than
invented.

## Performance

| Metric | Value |
|--------|-------|
| Duration | Unrecorded (see above) |
| Completed | 2026-08-30 (reconciled) |
| Tasks | 3 of 3 code tasks applied; 1 decision checkpoint answered in code; 1 human-verify deferred |
| Files modified | 5 (2 backend, 3 mobile) |
| Suite | 505 passed, 1 warning, 67s |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: `/process` accepts and threads the GO time | **Pass** | `api.py:145` adds `go_signal_s: Optional[float] = Form(None)`; `:233` passes `go_signal_s=_go` where `None` was hardcoded. `test_go_signal_form_field_threads_through` asserts `phases.go_signal_s == 3.5` |
| AC-2: Omitting the field is byte-compatible | **Pass** | `_post_csv` only adds the key when supplied, so the ~20 existing callers post the identical field set. `test_go_signal_absent_stays_none` asserts both `go_signal_s` and `start.reaction_time.value` are `None` |
| AC-3: A bad GO value never costs the session | **Pass, with one documented exception** | `api.py:224-228` drops non-finite/negative with a server-side log and processes on. `test_go_signal_bad_value_is_dropped_not_rejected` covers `-1.0/nan/inf/-inf` → 200 + `go_signal_s is None` + `mean_vel_ms is not None`. ⚠ `"banana"` **does** 422, at FastAPI's `Optional[float]` coercion before any handler code — pinned deliberately by `test_go_signal_unparseable_is_the_one_422` |
| AC-4: GO present, silent, re-pressable on both states | **Deferred** (code verified) | Two `TouchableOpacity` GO controls render — `RecordScreen.js:834` (videoRecording, camera controls) and `:887` (plain recording). `onPressGo` (`:772-777`) has no sound, no haptic, no flash, and does not touch `bleState`. Last-press-wins by overwrite. **Needs a device.** |
| AC-5: The stamp survives the lifecycle and reaches the server | **Deferred** (code verified) | Two refs on the documented `videoUriRef` mirror pattern; conversion at the META handler (`:460-472`) where `startPhoneMs` is in scope; `parameters.go_signal_s` set at `:272` inside `uploadAndProcess` with no dep-array change. Ordering (META → DUMP → saveCSV → upload) unchanged. **Needs a device.** |
| AC-6: A GO resolving before t=0 is dropped, not clamped | **Pass (backend) / Deferred (phone)** | Phone: `:463-471` drops when `g < 0` and logs `GO resolved to N.NN s (before t=0) — dropped`. Backend: same rule, tested. |
| AC-7: Race-start sequence off for every user, including prior opt-ins | **Partial — see deviation 1** | Key bumped to `startSequenceEnabled.v2`, default `false`, `catch` fails closed (`startSequencePrefs.js:13,20,24`); `RecordScreen`'s `startSequence` param default flipped to `false`; `RecordingConfigScreen`'s seed state flipped to `false`. ⚠ The AC's final clause — *"the toggle can still turn it back on"* — is **superseded** by the `hide` checkpoint answer |
| AC-8: The start-sequence code survives intact | **Pass** | `git status` reports **no modification** to `src/hooks/useStartSequence.js` or `src/components/StartSequenceOverlay.js`; `assets/audio/beep.mp3` and `takeyourmarks.mp3` both present |
| AC-9: Blast radius is exactly four files | **Fail by one, by decision — see deviation 1** | Five files. `myswimcoach`: `api.py` + `tests/test_api.py` only (the `.paul/` and `assets/icon/` entries belong to 84-01/85). Mobile: `RecordScreen.js` + `startSequencePrefs.js` + **`RecordingConfigScreen.js`**. Phase-74's `CycleCharts.js`, `BleContext.js`, `CLAUDE.md` untouched. Suite green above its prior count (497 → 505) |

**7 pass · 1 partial · 1 failed-by-decision · 3 clauses deferred to the device.**

## Accomplishments

- **The stale-clock-sync claim is dead in the one place it could keep misleading people.**
  `api.py:1168-1175` now states outright that the "real phone↔encoder clock sync is deferred
  (CONTEXT D13)" note **was stale** — the app has computed the correlation since Phase 47 — and
  names `PUT /go-signal` as the *correction* path and `POST /process` as the primary one. That note
  had already misled two documents.
- **`reaction_time` has a filling path for the first time in the project's history.** It is 0 of 99
  stored sessions today and no backfill is possible (B4).
- **The horn is off for the users who opted into it**, not just for the ones who never touched the
  toggle — the whole point of G10, and the reason this is a key bump rather than a default flip.
- **The validation asymmetry is defended in three places** (an AC, a test docstring, and an inline
  comment) because it is the single most "fixable"-looking thing in the diff.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `api.py` | Modified (+20/−5) | Optional `go_signal_s` form field; drop-and-log guard; `PhaseContext(go_signal_s=_go)`; both docstrings corrected |
| `tests/test_api.py` | Modified (+70/−4) | `_post_csv` gains the optional param; new `TestGoSignalOnProcess` (8 tests); the stale `# no GO button yet` comment amended |
| `../swimnetics-mobile/src/screens/RecordScreen.js` | Modified | GO refs + label state, META-time conversion, upload param, reset-site clearing, the two GO buttons and their styles |
| `../swimnetics-mobile/src/lib/startSequencePrefs.js` | Modified (+17/−4) | Key → `.v2`, default OFF, fail-closed `catch` |
| `../swimnetics-mobile/src/screens/RecordingConfigScreen.js` | Modified (+24/−12) | `SHOW_START_SEQUENCE_TOGGLE = false` gate; seed state flipped to `false` |

⚠ `RecordScreen.js`'s working-tree diff also carries **Phase 74's** retrieval work (stall 30 s → 8 s,
`MAX_RETRIEVAL_ATTEMPTS`, the `sendDumpHandshake` retry, the post-save `CLEAR`). That is pre-existing
uncommitted work, **not** this plan's — a commit scoped to 84-02 cannot be a whole-file commit of
that file.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Checkpoint → **`hide`** (`SHOW_START_SEQUENCE_TOGGLE = false`) | A settings toggle for a feature D9 just argued cues nobody is the same false affordance D9 killed | +1 file over AC-9; AC-7's reversibility clause becomes a one-line flag flip instead of a user action. ⚠ Answered in code, not at a recorded checkpoint |
| Seed `startSequence` state `false`, not `true` | The async pref read made the toggle flash on then snap off, and a fast Continue shipped `startSequence: true` to `RecordScreen` despite a stored OFF | A real bug fixed in passing; also why `RecordScreen`'s param default flipped |
| `"banana"` is allowed to 422 | It fails at FastAPI's coercion layer, above any code this plan owns; catching it would mean taking the field as `str` and parsing by hand | Documented and tested rather than hidden — AC-3 holds for every value that reaches the handler |
| No commit in either repo | Both trees carry other in-flight work; commit boundaries are the user's call | The deploy-ordering constraint below is still entirely unmet |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Scope additions | 1 | `RecordingConfigScreen.js`, chosen by the checkpoint's own `hide` option |
| Auto-fixed | 1 | The `startSequence` seed-state flash/leak |
| Process | 1 | APPLY ran unrecorded; verification reconstructed at UNIFY |
| Deferred | 1 | The entire human-verify, by standing phase decision |

**Total impact:** no scope creep. The one added file is an option the plan itself wrote and priced.

### 1. `RecordingConfigScreen.js` joins the diff (AC-9 fail, AC-7 partial)

- **Found during:** the decision checkpoint
- **Issue:** AC-9 pins a four-file blast radius, and AC-7 promises the toggle still works
- **Resolution:** the checkpoint's `hide` option explicitly costs both — its stated con is
  *"adds RecordingConfigScreen.js to the diff"*, and hiding a control is what removes the user's
  ability to flip it back. Both ACs were written before the checkpoint chose; they are **superseded,
  not violated**
- **Mitigation:** the flag, the hook, the overlay, the audio and the prefs module are all intact, and
  the gate constant carries a comment saying exactly what to flip

### 2. The APPLY session left no record

- **Issue:** no SUMMARY, no checkpoint log, suite never run, timestamps unrecoverable on a
  OneDrive-synced tree
- **Resolution:** reconciled at UNIFY — full diff review, suite run, static parse of the mobile half.
  Duration is recorded as **unknown** rather than fabricated
- **Residual risk:** if any exploratory edit was made and reverted during that session, this
  reconstruction cannot see it. The diffs are internally consistent and carry `Phase 84-02` comments
  throughout, so the risk is low

### Deferred Items

- **The whole human-verify checkpoint** — by standing Phase-84 decision, no item gets a human check
  until the phase is finished and one EAS build carries everything (84-01's checkpoint-2 `defer`).
  This plan's mobile half is JS, but G1 says there is no OTA channel, so it needs that build too.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| The mobile repo has no test runner and no lint script | Parsed all three changed JS files with `web/node_modules/typescript` (83-05 `createRequire` pattern) — all clean; proved non-vacuous with a mutant self-test on deliberately broken source |
| STATE's "485 green" baseline did not match | The suite is **505** with this plan's 8 tests, i.e. a **497** baseline. 485 was the count at 75-06's commit; 83-05 and later work moved it. Not a defect — STATE's figure is simply stale |

## Verification Results

```
pytest tests/  →  505 passed, 1 warning in 67.44s
                  (8 of those are TestGoSignalOnProcess; baseline 497)

parse check    →  RecordScreen.js (1313 lines)          parses clean
                  startSequencePrefs.js (35 lines)      parses clean
                  RecordingConfigScreen.js (328 lines)  parses clean
                  mutant self-test: PASS (broken input rejected)

AC-8 check     →  useStartSequence.js, StartSequenceOverlay.js — no modification
                  assets/audio/{beep,takeyourmarks}.mp3 — present

scope check    →  colors.good / colors.white / colors.textMuted exist (tokens.js:40,26,19)
                  elapsedS in scope at onPressGo (RecordScreen.js:91 → :776)
                  toggleStartSequence + getStartSequenceEnabled still wired (:85, :92)
```

## Next Phase Readiness

**Ready:**
- The backend half is deployable and backward-compatible on its own — every existing caller is
  unaffected, and that is a tested property, not an assumption.
- The mobile half is complete, parses, and touches no file 84-03 or 84-04 will need.

**Concerns:**
- ⚠ **Deploy ordering is the live risk and it is currently unmet.** `api.py` is uncommitted and
  unpushed. If the app ships before Railway has the field, every session recorded in the gap loses
  its marker with no error anywhere — the exact silent-loss shape item 2 exists to hunt. **Backend
  push must precede the EAS build**, and neither has happened.
- ⚠ **The number itself is unjudged.** It embeds the coach's own thumb latency and is a within-coach
  *relative* measure. The human-verify must judge the value, not just its presence; if it reads as
  noise the fix is a hardware starter signal, not more code.
- ⚠ **B4 stands:** no backfill is possible, so `reaction_time` begins mid-history and
  `phaseBaseline.js` (last-5-same-stroke) will see a metric that simply starts one day.
- A commit scoped to this plan must be **path-scoped** — `RecordScreen.js` also carries Phase 74's
  uncommitted retrieval work, and `myswimcoach`'s tree carries 84-01 and 85 artifacts.

**Blockers:** None for 84-03/84-04 — both have zero file overlap with this plan.

---
*Phase: 84-mobile-user-feedback, Plan: 02*
*Completed: 2026-08-30 (reconciled from an unrecorded APPLY)*
