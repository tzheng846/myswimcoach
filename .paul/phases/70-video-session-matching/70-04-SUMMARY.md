---
phase: 70-video-session-matching
plan: 04
subsystem: mobile
tags: [qr, expo-crypto, react-native-qrcode-svg, recordscreen, mobile]
requires:
  - phase: 70-video-session-matching
    provides: /process accepts recording_token (70-02); web decodes it (70-03)
provides:
  - RecordScreen generates a recording_token at plain record start, displays it as a QR for an external camera, and sends it to POST /process
affects: []
tech-stack:
  added: [react-native-qrcode-svg@^6.3.21]
  patterns:
    - "QR shown only in the plain encoder-only 'recording' UI (phone-camera path auto-syncs, needs no slate)"
key-files:
  created: []
  modified: ["swimnetics-mobile: src/screens/RecordScreen.js", "swimnetics-mobile: package.json"]
key-decisions:
  - "Token = Crypto.randomUUID() (expo-crypto, already a dep); QR via react-native-qrcode-svg (JS-only, rides existing react-native-svg — no new native module)"
  - "recording_token is an optional /process param (matches 70-02's conditional store); QR only in plain 'recording' state"
duration: ~loop
started: 2026-08-19T00:00:00Z
completed: 2026-08-19T00:00:00Z
---

# Phase 70 Plan 04: Mobile QR slate Summary

**RecordScreen now mints a `recording_token` at plain record start, renders it as a scannable QR for an external over-water camera to film, and forwards it to `POST /process` — the producer half that makes the web QR pre-fill (70-03) actually match a session.**

## Acceptance Criteria Results
| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: token generated + shown as QR at plain record start | **Code-complete / device-UAT pending** | `Crypto.randomUUID()` before `setBleState('recording')`; `<QRCode value={recordingToken} size={160}/>` in the plain 'recording' UI. Rendering verified only on a device (paid EAS build). |
| AC-2: token reaches the session | **Code-complete / UAT pending** | `parameters.recording_token` added to the `/process` multipart upload; stored by 70-02 once patch_13 is applied. |
| AC-3: no regression to existing / phone-video paths | **Pass (by construction)** | QR shows only in `bleState==='recording'` (not `videoRecording`); token is an added optional param; BLE/upload logic untouched. `expo-doctor` shows no new-dep failure. |

## Verification
- `grep` confirms token gen, QR view, and the upload param.
- `npx expo-doctor`: the 4 flagged mismatches (expo, expo-audio, expo-dev-client, expo-media-library, react-native-screens) are **pre-existing SDK drift, NOT from this change** — `react-native-qrcode-svg` is not flagged. ⚠ That drift is the known "run expo-doctor before every paid build" gotcha; reconcile before building.
- Committed + pushed to `swimnetics-mobile` (`e5e814e`).

## Files
| File (swimnetics-mobile) | Change | Purpose |
|------|--------|---------|
| `src/screens/RecordScreen.js` | Modified | token gen + QR display + `recording_token` upload param + `qrWrap/qrHint` styles |
| `package.json` (+lock) | Modified | react-native-qrcode-svg@^6.3.21 (JS-only, uses existing react-native-svg) |

## Deviations
None. Scoped the QR to the plain-record path (the external-camera use case, D9) rather than the phone-camera path.

## Next Phase Readiness
**Ready:** QR slate is code-complete across all three surfaces (backend 70-02, web 70-03, mobile 70-04).
**Concerns / human steps:** device UAT rides a **paid EAS build**; **patch_13 must be applied** before tokens store; end-to-end needs a real external camera filming the on-screen QR. No native module added, so no extra native linking beyond the existing react-native-svg.
**Blockers:** None in code; value gated on the paid build + patch_13 (both human).

---
*Phase: 70-video-session-matching, Plan: 04 — mobile committed+pushed in swimnetics-mobile (`e5e814e`). LAST plan of the QR slate.*
*Completed: 2026-08-19*
