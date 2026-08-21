# Phase 74 — BLE Dump Reliability

**Trigger (2026-08-19):** During a pool test the iOS app repeatedly and *randomly* showed
**"The end-of-dump marker never arrived. Saving what was received."** Worse than the error text
implies: once it appeared, **the buffered session was not retrievable** — the user recorded fresh
sessions and retried until one dumped cleanly. The device stayed responsive throughout (they kept
driving it from the app), so the firmware was **not frozen**.

## How the retrieval protocol works (firmware 1.1.0 + RecordScreen.js)

```
phone: subscribe TX → write "META"
esp:   META reply (8 bytes: session_start_us, device_now_us)   [indication]
phone: on META → write "DUMP"
esp:   sample packets, 24 samples × 7 = 168 B each             [indications, notify(false)]
esp:   0xEE end-of-dump marker (1 byte)                        [indication]
phone: on 0xEE → finishRetrieval(false) → save + upload
```

- The dump loop `dumpBuffer()` bets everything on `pTxChar->notify(false)` **blocking for the ATT
  indication-confirm** — "No vTaskDelay: the indication confirm paces the loop … no drops"
  (`ESP_32_V5.ino:485-487`).
- The phone distinguishes packets purely by length/content: 8 → META, 1 && `0xEE` → end,
  multiple-of-7 → samples, else ignored (`RecordScreen.js:381-424`).
- The error is a **30 s stall timer** (`RETRIEVAL_STALL_MS`, `RecordScreen.js:37`) that resets on
  every packet and fires `finishRetrieval(true)` iff `!dumpDoneRef.current`
  (`RecordScreen.js:359-363`). **A true BLE disconnect produces a *different* message**
  ("Device disconnected…", `RecordScreen.js:159-171`) — so this error means the link stayed up but
  the stream stalled or the final marker was lost.

## Root causes (code-verified)

**C1 — DATA LOSS on a "completed-but-not-received" dump (severe; this is the retrievability bug).**
`dumpBuffer()` clears the buffer **unconditionally** after the marker send:
```c
sendEndOfDumpMarker();
...
bufCount = 0; dataReady = false; sessionStartUs = 0;   // ESP_32_V5.ino:494-496
```
The only retention path is a *disconnect mid-dump* (`:474-480`). So when the loop reaches the end
(all `notify()` calls returned) but the phone missed the tail/marker (drop, MTU, lost confirm), the
firmware still **wipes the buffer** → the session is gone. The device is not frozen (matches the
user report: they kept recording new sessions). `startRecording()` already resets
`bufCount/dataReady` (`:371-372`), so **retaining the buffer across a dump is safe** — the next
recording overwrites it.

**C2 — SINGLE-POINT-OF-FAILURE + no recovery.** Retrieval success depends on **one 1-byte `0xEE`
indication** arriving intact. The phone knows no expected sample count and never retries — any lost
marker ⇒ 30 s wait ⇒ error. The indication design has no drop/lost-confirm recovery: on
congestion/lost-confirm the Bluedroid `notify(false)` either skips that packet or (older cores)
blocks; if the skipped/lost packet is the marker, retrieval fails with the session already wiped by C1.

**C3 — Diagnostic firmware in the field.** `#define TRACE_BUFFER 1` (`:86`) — the header says
"SET BACK TO 0 FOR THE NORMAL BUILD." It blocks the main task printing up to 4000 samples to Serial
after each recording (`traceBuffer()`, `:289-295`) and forces verbose `DBG`. Confirmed flashed.

**C4 — No MTU negotiation (latent).** The mobile connect path never calls `requestMTU`
(`BleContext.js:66-107`, `react-native-ble-plx ^3.5.1`). 168-byte packets need MTU ≥ 171. iOS
auto-negotiates large MTU so it usually fits; **Android defaults to 23** → deterministic failure
(the reported case was iOS, so this is latent, not the trigger).

**C5 — No on-device diagnostics.** `log()` is `console.log` only, invisible in TestFlight
(`RecordScreen.js:108-109,137-139`). When it fails at the pool there is zero forensic data — the
error doesn't even say how many samples arrived vs were expected.

## Decisions

- **D1 — Fix the data loss first and with certainty.** Firmware must **not** wipe the buffer on a
  dump the phone hasn't confirmed. Retain across dumps; clear only on (a) a new recording
  overwriting it, or (b) an explicit phone **`CLEAR`** command sent *after* the phone has safely
  saved the CSV. This makes every failed retrieval retryable → zero data loss regardless of C2's
  exact drop mechanism.
- **D2 — Harden the marker, don't rewrite the transport.** Resend `0xEE` a few times (idempotent on
  the phone). Do **not** rip out indications for notifications in this phase — that was a deliberate
  anti-drop choice (Phase 44-02) and a blind, hardware-untestable rewrite is riskier than the bug.
  If the stall recurs after D1/D2 + observability, revisit the transport with logs in hand.
- **D3 — Phone recovers instead of giving up.** Shorten the stall (30 s → ~8 s; it resets per
  packet so active streaming is unaffected) and **auto-retry META→DUMP** a couple times before
  surfacing the error. With D1 the buffer is intact, so a retry re-streams cleanly.
- **D4 — Make failures forensic.** Surface received-sample-count in the error and log the packet
  sequence to something visible off-device (at minimum include counts in the on-screen error;
  ideally a rolling in-app log).
- **D5 — TRACE_BUFFER → 0** for the shipped build.
- **D6 — `requestMTU` on connect** (fixes the latent Android failure; harmless on iOS).
- **D7 — Hardware-gated.** Firmware and mobile changes cannot be verified in this sandbox — they
  ride a flash + pool re-test. `swimnetics-mobile` is a separate, user-owned git repo.

## Out of scope

- Notifications-with-pacing transport rewrite (deferred; only if D1–D4 don't resolve it).
- Multi-session buffering, compression, or protocol versioning.
- Any backend / pipeline / web change (this is firmware + mobile only).
