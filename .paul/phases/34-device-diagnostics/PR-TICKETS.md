# Phase 34 — Device Diagnostics: PR Tickets

Two PRs, one per repo. The split follows the wire contract: the firmware adds a
`STATUS` command, the app consumes it. Review the firmware ticket first (it defines
the 15-byte packet both sides depend on).

> Git is yours to run — commands below are copy-paste ready, nothing has been
> committed for you. `.paul/` is gitignored, so this file and the plan are local-only.

---

## Shared contract — STATUS packet (review both sides against this)

Firmware notifies this on the existing TX characteristic when it receives `STATUS`:

| Byte(s) | Field | Notes |
|---------|-------|-------|
| 0       | `0xDD` marker | distinct from the `0xEE` end-of-dump marker |
| 1       | AS5600 status register (0x0B) | bits MD=0x20, ML=0x10, MH=0x08 |
| 2       | `magnet_ok` (0/1) | MD set AND ML/MH clear |
| 3       | AGC register (0x1A) | gain → magnet-gap health |
| 4..5    | raw angle `uint16` LE | 0x0C, 12-bit |
| 6       | flags | bit0=recording, bit1=dataReady, bit2=motorRunning |
| 7..10   | `bufCount` `uint32` LE | |
| 11..14  | `maxSamples` `uint32` LE | |

**Why length 15 is safe:** 15 is not 8 (META), not 1 (end marker), and not a
multiple of 7 (samples). Every existing TX parser keys off length, so STATUS slots
in without touching the sample/META/DUMP paths. App side also guards on
`buf[0] === 0xDD`.

---

## TICKET A — Firmware: `STATUS` BLE diagnostics command

**Repo:** `myswimcoach` (has GitHub remote)
**Branch (suggested):** `feat/device-diagnostics-firmware` off `main`
**File:** `ESP_32_V5/ESP_32_V5.ino` (only)

### Summary
The firmware silently refuses to record when the AS5600 doesn't detect a magnet
(`startRecording()` → 10 Hz error blink → idle), and the only evidence is a USB
serial log nobody reads at poolside. This adds a `STATUS` command that notifies a
15-byte live snapshot — magnet/AGC/raw-angle + recording/buffer flags — so the phone
can show why a recording failed. Reuses the existing deferred-flag command pattern
(no I2C on the BLE task); no change to recording, motor, LED, or the sample/META/DUMP
wire formats.

### Changes
- `readAgc()` helper + `REG_AGC 0x1A`.
- `STATUS_MARKER 0xDD`, `STATUS_PACKET_SIZE 15`.
- `pendingStatus` flag (set in `RxCallbacks`, cleared on disconnect, run in
  `processPending`).
- `sendStatus()` builds + notifies the packet above.
- Header-comment docs for the `STATUS` command.

### AC
- AC-1: `STATUS` → the 15-byte packet in the contract table; existing parsers
  unaffected.

### Risk / blast radius
Additive only. Length-15 packet cannot collide with sample (×7) / META (8) / end
(1) demux. No timing or recording-path changes.

### How to test (on hardware)
Flash this build, then run the **iOS ticket B** app build and follow the device
checkpoint in `34-01-PLAN.md` Task 3 (magnet absent → "NOT DETECTED"; align →
"Detected"; spin wheel → angle changes; record → buffer count climbs).

### Commands
```bash
# From repo root. NOTE: the working tree currently also has UNRELATED uncommitted
# changes (CW_FORWARD true→false in this same file, plus CLAUDE.md and video_sync.py).
# Keep them OUT of this PR. Easiest: stash them, branch, re-apply only what you want.

git stash push -m "wip: cw_forward + misc" -- ESP_32_V5/ESP_32_V5.ino CLAUDE.md video_sync.py
# ^ this also stashes the STATUS work since it's in the same file — so instead:

# Option B (recommended) — branch from main, then cherry-pick just this file's STATUS
# changes by committing the file but reverting the CW_FORWARD line first if you don't
# want it in this PR. If you DO want CW_FORWARD shipped too, it's one line and harmless
# to include — your call. Simplest clean path:

git checkout main
git checkout -b feat/device-diagnostics-firmware
git checkout feat/coach-chat-drills -- ESP_32_V5/ESP_32_V5.ino   # bring the edited file over
# (review `git diff main -- ESP_32_V5/ESP_32_V5.ino`; if you want to drop the CW_FORWARD
#  flip from this PR, edit that one line back to `true` before committing)
git add ESP_32_V5/ESP_32_V5.ino
git commit -m "feat(firmware): STATUS BLE command for on-phone diagnostics

Add a STATUS command returning a 15-byte live snapshot (AS5600 magnet/AGC/
raw-angle + recording/buffer flags) so the app can surface why a recording
failed. Reuses the deferred-flag pattern; length 15 avoids the sample/META/
end demux. No recording/motor/LED changes.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push -u origin feat/device-diagnostics-firmware
gh pr create --fill --base main
```

---

## TICKET B — iOS: Device Diagnostics screen

**Repo:** `swimnetics-mobile` (⚠ NO git remote yet — see CODEBASE-AUDIT §5.3)
**Branch (suggested):** `feat/device-diagnostics-screen`
**Files:** `src/screens/DiagnosticsScreen.js` (new), `src/screens/DevicesScreen.js`
(entry button), `App.js` (nav registration)

### Summary
New "Diagnostics" screen (reached from Devices → "Run Diagnostics") that polls the
firmware `STATUS` command ~2 Hz and renders three plain-English cards: magnet &
wiring (detected / not detected / too weak / too strong, live raw angle with a
"spin the wheel" hint, AGC), recording & buffer (recording on/off, buffered sample
count / capacity), and connection (device, link freshness "last status Xs ago").
Built on the existing `useBle()` singleton and the RecordScreen write/monitor
patterns — no BLE-plumbing refactor.

### AC
- AC-2 magnet/wiring legible; AC-3 record/buffer explains "no recording found";
  AC-4 link health shown.

### Verify
`npx expo export --platform ios` exits 0 (done — bundles, 1012 modules).

### Risk / blast radius
Additive screen + one nav route + one button. Parses only `len==15 && [0]==0xDD`;
all other TX notifies ignored. Stops its STATUS poll + monitor subscription on
unmount. RecordScreen retrieval flow untouched.

### How to test (on hardware)
Needs a **paid EAS build** (run `npx expo-doctor` first — version skew = launch
crash, per the mobile-build-gotchas note). See `34-01-PLAN.md` Task 3.

### Commands
```bash
# This repo has no remote, so there is no GitHub PR target yet. Commit locally now;
# open a PR once a remote exists.
git checkout -b feat/device-diagnostics-screen
git add src/screens/DiagnosticsScreen.js src/screens/DevicesScreen.js App.js
git commit -m "feat(diagnostics): on-phone Device Diagnostics screen

Poll the firmware STATUS command (~2 Hz) and show magnet/wiring, recording/
buffer, and BLE link health in plain English. Reached from Devices. Built on
the existing BleContext singleton; parses only the 15-byte 0xDD STATUS packet.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

# When you add a remote later:
# git remote add origin <url> && git push -u origin feat/device-diagnostics-screen
# gh pr create --fill   # then paste the Summary/AC above as the PR body
```

---

## Build/test order
1. Merge/flash **Ticket A** firmware (defines the packet).
2. Build **Ticket B** app (EAS), install.
3. Run `34-01-PLAN.md` Task 3 device checkpoint → reply "approved" to close the loop.
