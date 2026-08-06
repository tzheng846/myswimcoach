---
phase: 35-feature-verification
plan: 02
subsystem: ios
tags: [ios, react-native, ratings, ipad, eas, diagnostics, ble]
requires:
  - phase: 36-01
    provides: GET /sessions/{id}/ratings + RATINGS-SPEC.md payload contract
  - phase: 35-01
    provides: web verification baseline
provides:
  - iOS ratings UI (RN PillarCards) on ReportCardScreen behind a Simple/Advanced toggle
  - iPhone-first device family (iPad de-scoped to compat mode)
  - 2 verification-surfaced BLE/diagnostics bug fixes
affects: [35-03 doc reconciliation, future iOS-parity phase, post-resolder device re-verify]
tech-stack:
  added: []
  patterns: ["RN component fetches the shared ratings endpoint; colors from payload; native device-family set in pbxproj (non-CNG)"]
key-files:
  created: [swimnetics-mobile/src/components/PillarCards.js, .paul/phases/35-feature-verification/35-02-DEVICE-CHECKLIST.md]
  modified: [swimnetics-mobile/src/screens/ReportCardScreen.js, swimnetics-mobile/app.json, swimnetics-mobile/ios/mobile.xcodeproj/project.pbxproj, swimnetics-mobile/src/context/BleContext.js, swimnetics-mobile/src/screens/DiagnosticsScreen.js, swimnetics-mobile/package.json, swimnetics-mobile/package-lock.json]
key-decisions:
  - "iPhone-first now (drop native iPad); proper responsive iPad layout = its own future phase"
  - "Closed at the verifiable boundary; recording-gated checks deferred to a post-resolder build (no rebuild cost)"
duration: ~2.5h (incl. 2 device-found bug fixes)
completed: 2026-06-18
---

# Phase 35 Plan 02: iOS Verification + Ratings UI Summary

**Shipped the Phase-36 rating UI on iOS (pillar cards mirroring web), de-scoped iPad to
iPhone-compat, aligned a version skew, and verified everything that doesn't need a working
encoder on a real build + device. Two bugs surfaced during testing were fixed. Recording-gated
checks are deferred to a post-resolder build (the encoder wiring came loose mid-test).**

## Acceptance Criteria Results
| AC | Status | Notes |
|----|--------|-------|
| AC-1 ratings UI mirrors web, ships in build | ✅ PASS | Breaststroke: Simple = 4 pillar cards (band+marker+verdict+trend), tap-expand metrics, Advanced = raw cards. Non-breaststroke render not exercised (no such data; covered by backend tests + web 36-02). |
| AC-2 34-01 diagnostics on device | ◐ PARTIAL / DEFERRED | Diagnostics screen reads the device live; full magnet→buffer flow deferred (no encoder). Found + fixed 1 bug (see below). |
| AC-3 21-02 + 26-01 on device | ⏸ DEFERRED | Recording-gated — needs resolder. Same build will do. |
| AC-4 22-02 laptop demo | ⏸ DEFERRED | Needs a fresh paired recording + video. |
| AC-5 iPad de-scoped to iPhone-compat | ✅ PASS | Letterboxed iPhone UI on iPad, not stretched. `TARGETED_DEVICE_FAMILY=1`. |
| AC-6 results recorded | ✅ PASS | DEVICE-CHECKLIST.md carries PASS/DEFERRED/FIXED per item. |

Also confirmed: **app launches with no dyld crash** (validates the version-skew fix vs the build-36 lesson).

## Accomplishments
- **`PillarCards.js` (RN)** — mirrors web PillarCards from RATINGS-SPEC.md: 3-segment traffic band + score marker + verdict + trend chip + tap-to-expand metrics + provisional notice; colors from the payload `rating_colors`; fetches `GET /sessions/{id}/ratings` with the Bearer token.
- **`ReportCardScreen.js`** — Simple/Advanced toggle (default Simple = pillars; Advanced = existing raw metric cards). Velocity chart / Time-to-Distance / Data Quality / Notes shown in both.
- **iPad de-scope** — `app.json supportsTablet:false` + the authoritative `TARGETED_DEVICE_FAMILY=1` in both target build configs of `project.pbxproj` (EAS ignores `app.json`'s `ios` block in a non-CNG project — confirmed by expo-doctor).
- **Version skew fixed** — `expo install --fix` → `expo ~56.0.12`, `expo-video ~56.1.4`; expo-doctor version check green; export exits 0.
- **Backend deploy (Gate 0) done by user** — PR #5 merged ratings to `main`; Railway live (`/sessions/{id}/ratings` → 401 unauth, route deployed; bogus route → 404 confirms per-route auth).

## Bugs found on device + fixed (code-only; ride the next build)
1. **"Forget" didn't disconnect BLE** — `BleContext.forgetDevice` only dropped the device from the saved list, never `cancelConnection()`, so the radio stayed connected (device LED on) + app state went stale. **Fixed:** disconnect + clear state when forgetting the connected device.
2. **Diagnostics mislabeled an unwired AS5600 as "Too weak"** — an unresponsive sensor reads `0xFF` (MD+ML+MH all set) → fell into the "Too weak / move magnet closer" branch. **Fixed:** `magnetVerdict` flags `0xFF` / the impossible weak+strong combo as **"SENSOR NOT RESPONDING — check wiring."**

## Files Created/Modified
| File | Change | Purpose |
|------|--------|---------|
| `swimnetics-mobile/src/components/PillarCards.js` | Created | RN ratings pillar UI |
| `swimnetics-mobile/src/screens/ReportCardScreen.js` | Modified | Mount pillars + Simple/Advanced toggle |
| `swimnetics-mobile/app.json` | Modified | supportsTablet:false |
| `swimnetics-mobile/ios/mobile.xcodeproj/project.pbxproj` | Modified | TARGETED_DEVICE_FAMILY=1 (×2 configs) |
| `swimnetics-mobile/src/context/BleContext.js` | Modified | Fix: forget disconnects BLE |
| `swimnetics-mobile/src/screens/DiagnosticsScreen.js` | Modified | Fix: sensor-not-responding verdict |
| `swimnetics-mobile/package.json` + lock | Modified | expo/expo-video version align |
| `.paul/.../35-02-DEVICE-CHECKLIST.md` | Created | On-device script + results ledger |

## Verification
- `npx expo export --platform ios` → exit 0, 1013 modules (was 1012; +1 = PillarCards), clean after every change incl. both fixes.
- `npx expo-doctor` → 20/21 (only the expected non-CNG warning).
- On device (user): app launches clean, ratings UI (breaststroke) ✓, iPad letterboxed ✓, Diagnostics live ✓.

## Deviations from Plan
| Type | Count | Impact |
|------|-------|--------|
| Scope add | 1 | iPad de-scope (config-only) — user decision, folded in |
| Scope add | 1 | Version-skew fix (`expo install --fix`) — pre-build hardening |
| Scope add | 2 | Two device-surfaced bug fixes (forget/BLE, diagnostics verdict) |
| Deferral | 4 | Recording-gated checks (full 34-01, 21-02, 26-01, 22-02) → post-resolder build |

## Deferred → tracked
- **Post-resolder device re-verify (one build):** the 4 recording checks + re-verify the 2 fixes. No rebuild cost beyond that single build.
- **iOS ↔ web parity gaps (NOT regressions):** AI coaching chat + advanced per-cycle graphs are web-only, absent on iOS → candidate future "iOS parity" phase; noted for 35-03.
- **Non-breaststroke ratings render** unexercised on iOS (no data); low risk (shared contract + tests).

## Next Phase Readiness
**Ready:** 35-03 doc reconciliation (no hardware) — the last Phase 35 step.
**Concerns:** DRAFT breaststroke thresholds still owe a coach review before customer-facing.
**Git:** mobile repo changes uncommitted + local-only (no remote) — commit before the next build for reproducibility (user-owned).

---
*Phase: 35-feature-verification, Plan: 02*
*Completed: 2026-06-18*
