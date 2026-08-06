---
phase: 22-video-overlay-validation
plan: 01
subsystem: firmware
tags: [esp32, ble, nus, as5600, buffer-and-dump, bleak, opencv, matplotlib, video-sync]

requires:
  - phase: 14-device-registration
    provides: chip-ID BLE name convention (SwimLogger-XXXXXX), ID_UUID/FW_UUID characteristics
provides:
  - Buffer-and-dump firmware (ESP_32_V5 1.1.0) — phone-free recording, META/DUMP retrieval
  - META protocol for phone clock correlation (8-byte [session_start_us][device_now_us])
  - logger_ble.py bench tooling (META/DUMP commands, end-marker exit, prefix name match)
  - video_sync.py --video-origin-s (wall-clock sync path, no visual marker)
affects: [22-02 iOS retrieval flow, 21-02 RecordScreen refactor, underwater video productization]

tech-stack:
  added: []
  patterns:
    - Deferred BLE command flags (set in callback, execute in loop) extended to META/DUMP
    - Runtime buffer sizing from heap_caps_get_largest_free_block minus BLE headroom
    - Packed 7-byte Sample struct == wire format (notify straight from buffer)

key-files:
  created: []
  modified: [ESP_32_V5/ESP_32_V5.ino, logger_ble.py, video_sync.py]

key-decisions:
  - "Firmware rebased on motor_logger_esp32.ino — that is the real hardware (GPIO27/32, DRV8833, chip-ID name)"
  - "Button: short press = record toggle, long press (>=800ms) = motor toggle"
  - "Buffer sized at boot from largest free heap block - 32KB headroom (~41s on current board), not fixed 60s"
  - "DUMP: 168-byte packets (24x7), 5ms pacing, 0xEE end marker; abort-on-disconnect retains buffer"
  - "META returns session_start_us=0 when no session buffered"

patterns-established:
  - "Sample parsers accept any non-zero multiple of 7 bytes (logger_ble.py, already true in RecordScreen.js)"
  - "Non-sample TX packets must not be multiples of 7 (META=8B, end marker=1B)"

duration: ~3h (including hardware bench iteration)
started: 2026-06-10T00:00:00Z
completed: 2026-06-10T00:00:00Z
---

# Phase 22 Plan 01: Buffer-and-Dump Firmware + Sync Tooling Summary

**ESP_32_V5 firmware 1.1.0 records phone-free into RAM (~41 s) and dumps over BLE with clock metadata; logger_ble.py drives META/DUMP from the bench; video_sync.py accepts a wall-clock origin — all verified on hardware end to end through vel_acc_extraction.py.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~3 h (incl. 3 hardware bench iterations) |
| Completed | 2026-06-10 |
| Tasks | 4 of 4 (3 auto + 1 human-verify checkpoint, approved) |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Phone-free recording with LED status | Pass | Recording independent of BLE; user confirmed on hardware (motor long-press also confirmed) |
| AC-2: META returns session metadata | Pass | `logger_ble.py --command META` decoded start/now/age correctly on bench |
| AC-3: DUMP streams the full buffer | Pass | 11,116 rows received = full buffer; end marker exits cleanly; pipeline produced sane velocity (0–1.07 m/s) |
| AC-4: Buffer-full stops cleanly | Pass | Bench session hit capacity (11,116 = maxSamples); truncated session retained and dumped intact |
| AC-5: video_sync accepts a direct origin | Pass | Real 90-frame render from AP.mp4 + sample_br_1.csv with `--video-origin-s 5.0`; both error cases + legacy path verified |

## Accomplishments

- Data capture decoupled from data retrieval: device records with no phone present; any client retrieves afterward — the architectural unlock for phone-as-camera validation and the long-term "swim now, review later" UX
- META clock-correlation protocol in place — everything Plan 22-02 needs to compute `sessionStartPhoneMs`
- Full bench path proven without the iOS app: button → buffer → META → DUMP → raw CSV → `vel_acc_extraction.py` (processed/swim_test_20260610_094117.csv)

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `ESP_32_V5/ESP_32_V5.ino` | Rewritten | motor_logger base + RAM buffering, META/DUMP, READY LED, dynamic buffer sizing, short/long press |
| `logger_ble.py` | Modified | META/DUMP commands, multiple-of-7 parsing, 0xEE end-marker exit, `SwimLogger-*` prefix match |
| `video_sync.py` | Modified | `--video-origin-s` CLI path; matplotlib ≥3.8 render fix (`buffer_rgba`) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Rebase firmware on motor_logger_esp32.ino | That is the actual hardware: GPIO27 LED, GPIO32 button, DRV8833 motor, chip-ID BLE name, ID/FW chars | ESP_32_V5 is now the buffer-and-dump variant of the production firmware; motor_logger_esp32.ino untouched |
| Short press = record, long press (≥800 ms) = motor | One physical button, two functions; recording must be phone-free | Swimmer records without phone; reel rewind still button-driven |
| Dynamic buffer sizing (largest block − 32 KB headroom) | Fixed 113 KB malloc failed: 127 KB free but largest contiguous block 110 KB (heap fragmentation) | ~41 s capacity on current board; prints achieved seconds at boot |
| DUMP packets = 24 samples (168 B), 5 ms pacing | Any multiple of 7 valid for all parsers; MTU ≥171 from bleak/iOS; ~3.5 s dump | Fallback to 4/packet documented if truncation ever observed |
| META=8 B, end marker=1 B (0xEE) | Neither is a multiple of 7 → sample parsers naturally ignore them | No parser changes needed for coexistence |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 4 | Essential — plan's hardware assumptions were wrong; fixes discovered at bench/verification |
| Boundary deviation | 1 | Minimal 3-line fix inside protected rendering code (pre-existing breakage) |
| Deferred | 1 | Logged below |

### Auto-fixed Issues

**1. Wrong hardware model in plan (firmware rewritten on motor_logger base)**
- **Found during:** Task 4 bench checkpoint — LED dark, button dead on GPIO4/23
- **Fix:** Full rebase on motor_logger_esp32.ino (pins, motor, chip-ID name, ID/FW chars, DBG logging, deferred-command pattern)

**2. Heap fragmentation broke fixed buffer allocation**
- **Found during:** Task 4 bench — `malloc(113400)` failed with 127 KB free
- **Fix:** Size from `heap_caps_get_largest_free_block()` − 32 KB headroom, halve-and-retry, fatal below 10 s

**3. Broken debounce inherited from old V5 (button presses could never fire)**
- **Found during:** Bench diagnosis — edge condition and debounce-timer reset on same iteration
- **Fix:** Debounced stable state tracked separately from raw reads; short/long press logic on top

**4. matplotlib ≥3.8 removed `tostring_rgb()` — video_sync.py crashed on every run (boundary deviation)**
- **Found during:** AC-5 verification render
- **Fix:** `buffer_rgba()` + RGBA→RGB slice in `render_strip` — both workflows now render

Also: latent `logger_ble.py` bug fixed per plan (PACKET_SIZE=14 rejected V5's 28-byte packets), plus prefix name matching for `SwimLogger-<chipID>`.

### Deferred Items

- video_sync.py crashes with `FileNotFoundError` (instead of degrading) when ffmpeg is absent; frames still saved to `<name>.noaudio.mp4`. ffmpeg not installed on dev machine — needed anyway for ffprobe in the validation procedure.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Stale firmware on board (old FATAL string in Serial) | Re-upload; distinguishing log lines identified |
| Button appeared dead in heartbeat (`btn=1` constant) | Was wrong-pin assumption (fix #1); user later confirmed motor toggle works |

## Next Phase Readiness

**Ready:**
- META/DUMP protocol live and bench-verified — Plan 22-02 (iOS retrieval + `sessionStartPhoneMs`) can build directly on it
- `video_sync.py --video-origin-s` ready to consume the computed offset

**Concerns:**
- Live-streaming is gone from this firmware: the current iOS RecordScreen flow (subscribe → START → live samples) will retrieve nothing until 22-02 converts it to META/DUMP. Live in-swim velocity graph is inherently unavailable in dump mode.
- 22-02 and 21-02 both modify RecordScreen.js — sequence them before planning either
- `micros()` wraps at ~71.6 min — META math is modular-safe but a session must be retrieved within one wrap of recording
- STATE.md "BLE Protocol (locked)" section still describes the live-stream protocol the iOS app uses today; update it when 22-02 lands

**Blockers:** None

---
*Phase: 22-video-overlay-validation, Plan: 01*
*Completed: 2026-06-10*
