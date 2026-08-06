# Summary: 03-01 BLE Record View

**Phase:** 03-ble-record-view  
**Plan:** 01  
**Completed:** 2026-05-20  
**Status:** ✅ All AC met, human verify approved

---

## What Was Built

Added a third "Record" mode to `app.py` — a full BLE state machine that runs poolside without a laptop serving as the interface.

**New in `app.py`:**
- `_rec_status` module-level dict for thread→UI communication
- `_ble_scan(timeout_s)` — discovers BLE devices via BleakScanner
- `_recording_thread(address, raw_path, stop_event)` — background thread with own asyncio event loop; streams Nordic UART packets, writes raw CSV
- `_run_pipeline(raw_path, processed_path)` — calls vel_acc_extraction.process_file with browser.open patched out
- `_record_view()` — 7-state machine: idle → scanning → scan_done → connecting → connected → recording → processing → done

**State machine flow:** Scan → select device → connect → label → record (sample counter ticks) → stop → auto-process → auto-switch to Simple view with new session loaded.

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Background thread with own asyncio loop | Avoids conflict with Streamlit's main thread |
| Raw CSV always written first | Preserved even if processing fails |
| `processed/` CSV also kept permanently | Useful for debugging; decided Phase 3 |
| Patched `webbrowser.open` during pipeline | Prevents browser tab opening on headless runs |

---

## Acceptance Criteria

- ✅ AC-1: Record tab visible in mode radio
- ✅ AC-2: BLE scan discovers devices with 5s spinner
- ✅ AC-3: Recording lifecycle — counter + stop button work
- ✅ AC-4: Auto-switch to Simple view after processing
- ✅ AC-5: Raw CSV persisted to `raw/` directory
- ✅ AC-6: Error resilience — errors shown, raw CSV preserved

---

## Files Modified

- `app.py` — extended with BLE record mode (~250 lines added)

## Files Not Modified (as per boundaries)

- `vel_acc_extraction.py`, `metrics.py`, `logger_ble.py` — untouched
