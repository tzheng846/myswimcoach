---
phase: 05-ios-testflight
plan: 01
subsystem: infra
tags: [expo, eas-build, testflight, ios, react-native, bare-workflow]

requires:
  - phase: 04-fastapi-backend
    provides: POST /process endpoint (iOS app will call this in Plan 05-03)

provides:
  - "Expo bare workflow iOS app scaffold at C:\\Users\\TonyZheng\\Desktop\\swimnetics-mobile"
  - "EAS Build pipeline proven: git → cloud Mac build → TestFlight"
  - "Provisioning profile + distribution cert for com.swimnetics.app"

affects: [05-02-ble-recording, 05-03-upload-chart]

tech-stack:
  added: [expo SDK 56, react-native 0.85.3, react 19, eas-cli, fetch-nodeshim]
  patterns: [swimnetics-mobile is a separate repo from myswimcoach, EAS Build for cloud iOS compilation]

key-files:
  created: [app.json, eas.json, ios/mobile/Info.plist, ios/mobile.xcodeproj/project.pbxproj, ios/mobile/Images.xcassets/AppIcon.appiconset/*, .gitattributes, ios/.xcode.env]
  modified: []

key-decisions:
  - "swimnetics-mobile lives at Desktop/swimnetics-mobile (separate repo, not inside myswimcoach)"
  - "Bundle ID: com.swimnetics.app"
  - "Icons generated as placeholder navy-blue 'S' squares (120, 180, 1024px)"
  - "ITSAppUsesNonExemptEncryption=false declared in Info.plist"
  - "fetch-nodeshim added manually (missing transitive dep in SDK 56)"

patterns-established:
  - "All eas commands run from swimnetics-mobile/, never from myswimcoach/"
  - "iOS native files (pbxproj, Info.plist) edited directly — prebuild cannot run on Windows"
  - ".xcode.env sources nvm before command -v node to handle Xcode restricted PATH"

duration: ~3h (including 4 build iterations debugging)
started: 2026-05-21T00:00:00Z
completed: 2026-05-22T00:00:00Z
---

# Phase 5 Plan 01: iOS TestFlight Scaffold Summary

**Expo bare workflow app scaffolded, built via EAS on Expo's Mac servers, and installed on Tony's iPhone via TestFlight — EAS Build + provisioning pipeline proven.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~3 hours |
| Completed | 2026-05-22 |
| Build iterations | 4 (debugging native issues) |
| Tasks | 4 of 4 complete (1 auto + 3 checkpoints) |
| Files modified | 8 native iOS files + config |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: EAS Build completes without error | Pass | Build `48887e3a` succeeded on 4th attempt |
| AC-2: App appears in TestFlight | Pass | Visible under Team (Expo) internal group |
| AC-3: App installs and runs on device | Pass | Approved by Tony on iPhone |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 6 | All essential, no scope creep |
| Scope additions | 0 | — |
| Deferred | 0 | — |

### Auto-fixed Issues

**1. EAS init git root conflict**
- **Issue:** `eas init` failed because a stray `package.json` at `C:\Users\TonyZheng\` was found before the project's own, putting the project root outside the git repo
- **Fix:** Moved `mobile/` out of `myswimcoach/` to `C:\Users\TonyZheng\Desktop\swimnetics-mobile\` as a standalone repo
- **Files:** Entire project relocated

**2. Missing `fetch-nodeshim` dependency**
- **Issue:** `expo config --json` exited with code 7 — `Cannot find module 'fetch-nodeshim'` in `@expo/cli`
- **Fix:** `npm install fetch-nodeshim`
- **Files:** `package.json`, `package-lock.json`

**3. Wrong bundle ID in native Xcode project**
- **Issue:** Scaffold generated `org.name.mobile`; `app.json` had `com.swimnetics.app` but EAS bare workflow reads native files, not `app.json`
- **Fix:** `sed` replaced both `PRODUCT_BUNDLE_IDENTIFIER` entries in `project.pbxproj`
- **Files:** `ios/mobile.xcodeproj/project.pbxproj`

**4. `NODE_BINARY` empty in Xcode script phase environment**
- **Issue:** Build failed with `.xcode.env: line 5: : command not found` — `command -v node` returned empty because Xcode script phases run in a restricted PATH that excludes nvm
- **Fix:** Added `source $NVM_DIR/nvm.sh --no-use` to `ios/.xcode.env` before `command -v node`
- **Files:** `ios/.xcode.env`

**5. Missing app icons + `CFBundleIconName`**
- **Issue:** Apple rejected the IPA — no icon PNG files in asset catalog, `CFBundleIconName` missing from Info.plist
- **Fix:** Generated placeholder navy-blue 'S' icons (120, 180, 1024px) via matplotlib; updated `Contents.json`; added `CFBundleIconName=AppIcon` to Info.plist
- **Files:** `ios/mobile/Images.xcassets/AppIcon.appiconset/*`, `ios/mobile/Info.plist`

**6. Missing export compliance declaration**
- **Issue:** First `eas submit` failed — Apple requires apps to declare encryption usage
- **Fix:** Added `ITSAppUsesNonExemptEncryption = false` to Info.plist
- **Files:** `ios/mobile/Info.plist`

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `prebuild --clean` deleted `ios/` before stopping (Windows blocks iOS prebuild) | `git checkout -- ios/` restored from initial commit; native files edited directly hereafter |
| EAS submit failed on first attempt (existing IPA pre-icon-fix) | Rebuilt with icon fix and resubmitted |
| TestFlight showed "Invited" but iPhone asked for redeem code | Used email invite link from Apple in Mail app |

## Next Phase Readiness

**Ready:**
- EAS Build pipeline is proven and repeatable — future builds just need `eas build -p ios --profile preview`
- `swimnetics-mobile/` is the iOS project root; all native configs are correct
- Provisioning profile + cert already generated for `com.swimnetics.app`
- TestFlight distribution set up with Team (Expo) internal group

**Concerns:**
- Icons are placeholder (navy square with 'S') — fine for TestFlight, need real assets before App Store
- Android native files still have `com.mobile` package name — irrelevant for iOS-only V1 but will need fixing before Android support
- `prebuild` cannot run on Windows — any future native config changes must be made directly to iOS files or run via EAS Build

**Blockers:** None

---
*Phase: 05-ios-testflight, Plan: 01*
*Completed: 2026-05-22*
