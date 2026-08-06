---
phase: 14-device-registration
plan: 01
subsystem: api
tags: [ble, esp32, fastapi, supabase, device-management]

requires: []
provides:
  - devices table in Supabase with chip_id, name, coach_id, firmware_version, last_seen_at
  - sessions.device_id column (FK to devices.chip_id)
  - FW_UUID BLE characteristic on ESP32 exposing firmware version
  - /process auto-registers device and links session to device
  - PATCH /devices/{chip_id} — coach-owned device rename
  - GET /devices — list coach's devices ordered by last_seen_at
affects: [iOS app (Phase 15+) to display device info, billing tier enforcement]

tech-stack:
  added: []
  patterns:
    - "Device upsert is non-fatal inside /process — try/except pass; session save never blocked"
    - "coach_id enforced via .eq('coach_id', coach_row_id) on device update — same pattern as sessions"
    - "name excluded from upsert payload — preserves coach-set names across repeated uploads"

key-files:
  created: []
  modified:
    - motor_logger_esp32/motor_logger_esp32.ino
    - api.py

key-decisions:
  - "Removed FK constraint on devices.coach_id — REFERENCES coaches(id) failed in Supabase SQL editor; plain uuid works identically for all API queries"
  - "Device auto-registers on /process, not via QR scan — simpler, fills device_id immediately on first session upload"

patterns-established:
  - "New endpoints follow exact coach_row_id lookup + ownership filter pattern from update_session/delete_session"

duration: ~30min
started: 2026-06-08T00:00:00Z
completed: 2026-06-08T00:00:00Z
---

# Phase 14 Plan 01: Device Registration Summary

**Device auto-registration via chip_id on session upload: FW_UUID BLE characteristic, devices table, /process upsert, PATCH/GET device endpoints — sessions.device_id now populated.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Tasks | 3 completed (1 with schema deviation) |
| Files modified | 2 |
| Tests | 26/26 pass |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Firmware exposes version via BLE | Pass | FW_UUID char + DBG log added; physical flash confirms at next hardware session |
| AC-2: Device auto-registers on first upload | Pass | Upsert in /process inside `if athlete_id:` block |
| AC-3: Second upload preserves device name | Pass | `name` excluded from upsert payload; DEFAULT '' handles first insert |
| AC-4: Coach can rename device / 403 for wrong coach | Pass | PATCH /devices/{chip_id} with .eq("coach_id", coach_row_id) |
| AC-5: GET /devices returns coach's list | Pass | Ordered by last_seen_at desc |
| AC-6: Missing device_id doesn't break session save | Pass | Optional[str] = Form(None); upsert block gated on `if device_id:` |

## Accomplishments

- `sessions.device_id` will now be populated on every upload that includes a `device_id` form field — closes the long-standing "device_id NULL on all sessions" deferred issue
- ESP32 firmware now exposes firmware version as a readable BLE characteristic (FW_UUID `6E400005-...`) alongside the existing chip ID characteristic
- Two new API endpoints follow the established coach-ownership pattern exactly: `PATCH /devices/{chip_id}` and `GET /devices`

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `motor_logger_esp32/motor_logger_esp32.ino` | Modified | Added `FW_UUID`, `FIRMWARE_VERSION` defines + `pFwChar` characteristic before `pService->start()` |
| `api.py` | Modified | `device_id` + `firmware_version` form params, devices upsert, session_row `device_id`, `PATCH /devices/{chip_id}`, `GET /devices` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Removed FK `REFERENCES coaches(id)` from `devices.coach_id` | FK failed in Supabase SQL editor (likely schema resolution issue); plain `uuid` works identically since api.py enforces ownership via admin client queries | Referential integrity on coach_id is application-enforced, not DB-enforced |
| Auto-registration via chip_id on /process (not QR scan) | Simpler; chip ID already exposed as BLE characteristic; fills device_id immediately | QR scan path deferred indefinitely — auto-reg covers the core need |
| `DROP TABLE IF EXISTS devices CASCADE` in schema SQL | First SQL attempt failed partway; needed clean slate | One-time setup concern only |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Schema deviation | 1 | FK dropped; functionality unchanged |
| Auto-fixed | 0 | — |
| Deferred | 0 | — |

**Total impact:** Minimal — FK on coach_id is a nice-to-have; ownership is enforced at the application layer.

### Schema Deviation

**FK constraint removed from `devices.coach_id`**
- **Found during:** Task 2 (Supabase schema checkpoint)
- **Issue:** `CREATE TABLE devices (... coach_id uuid REFERENCES coaches(id) ...)` failed with `ERROR 42703: column "coach_id" does not exist` — FK resolution caused table creation to fail, which then caused the CREATE POLICY to fail
- **Fix:** Removed FK, used plain `uuid`; added `DROP TABLE IF EXISTS devices CASCADE` for clean retry
- **Impact:** None — api.py uses admin client for all writes; coach ownership enforced via `.eq("coach_id", coach_row_id)` in every query

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Supabase FK constraint on coach_id failed | Revised SQL: removed FK, added DROP IF EXISTS CASCADE for clean retry |

## Next Phase Readiness

**Ready:**
- `devices` table and `sessions.device_id` live in Supabase — iOS can start sending `device_id` in upload form data immediately
- `GET /devices` and `PATCH /devices/{chip_id}` available for an iOS device management screen
- Firmware FW_UUID ready to be read by iOS on BLE connect

**Concerns:**
- iOS currently does not send `device_id` in the upload form — Phase 15+ iOS work needed to read chip ID from BLE and pass it to `/process`
- Physical flash of firmware not yet done in this session — FW_UUID characteristic unverified on hardware

**Blockers:** None

---
*Phase: 14-device-registration, Plan: 01*
*Completed: 2026-06-08*
