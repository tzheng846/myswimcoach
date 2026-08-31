---
phase: 84-mobile-user-feedback
plan: 01
subsystem: mobile-native
tags: [ios, app-icon, pillow, info-plist, orientation, eas, native-config]

requires:
  - phase: 85-website-home-refresh
    provides: the Swimnetics mark committed at assets/icon/Swimnetics_icon.svg — this plan's
      source of truth, and the precedent this plan deliberately diverges from (web icons are
      correctly transparent; iOS icons must not be)
provides:
  - a re-runnable, byte-deterministic iOS app-icon rasterizer (scratch/make_app_icons.py)
  - the Swimnetics mark as the iOS app icon at 1024/180/120, opaque RGB, App-Store-legal
  - portrait-only iOS orientation (Info.plist native manifest now agrees with app.json's intent)
affects: [the next EAS build, 84-02 GO marker, 84-03 indicators, any future icon re-export]

tech-stack:
  added: []
  patterns:
    - "Decode-and-compose, never render: the 'SVG' is a base64 PNG wrapper whose viewBox would anchor the mark top-left"
    - "Rasterizer emits to scratch/ first; installing into the user-owned mobile repo is a separate reviewed step"
    - "Resize each output independently from the full-resolution source, never downsample the 1024 output"

key-files:
  created:
    - scratch/make_app_icons.py
    - scratch/_icon_preview_sheet.py
    - scratch/appicon/AppIcon-1024.png
    - scratch/appicon/AppIcon-180.png
    - scratch/appicon/AppIcon-120.png
    - scratch/appicon/_preview_sheet.png
  modified:
    - ../swimnetics-mobile/ios/mobile/Images.xcassets/AppIcon.appiconset/AppIcon-1024.png
    - ../swimnetics-mobile/ios/mobile/Images.xcassets/AppIcon.appiconset/AppIcon-180.png
    - ../swimnetics-mobile/ios/mobile/Images.xcassets/AppIcon.appiconset/AppIcon-120.png
    - ../swimnetics-mobile/ios/mobile/Info.plist

key-decisions:
  - "Background #FFFFFF, fill 80% — approved at the decision checkpoint from a 3x3 contact sheet"
  - "EAS build DEFERRED, not spent: the working tree holds both items until later Phase-84 plans batch into one build"
  - "AC-3's aspect tolerance is unreachable at 180/120 px and was documented, not chased"
  - "No commit in either repo; the mobile repo's history is user-owned"

patterns-established:
  - "On the OneDrive-synced mobile repo, verify file state by hashing content — a single git status can return a stale directory view"
  - "When an AC states a numeric tolerance, brute-force the achievable floor before treating a miss as a defect"

duration: ~35min across two sessions
started: 2026-08-30T00:15:00-07:00
completed: 2026-08-30T01:34:00-07:00
---

# Phase 84 Plan 01: iOS App Icon + Portrait Lock Summary

**The placeholder iOS app icon is replaced by the Swimnetics mark on a white ground at 80% fill —
opaque, alpha-free and App-Store-legal — and the native manifest finally agrees with `app.json` that
this app is portrait-only. Both are in the mobile working tree, statically verified, and deliberately
unbuilt: the EAS build was deferred so one build can carry all seven Phase-84 items.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min of work across two sessions |
| Tasks | 5 of 5 reached (3 auto + 1 decision checkpoint + 1 human-verify **deferred**) |
| Files changed | 4 in `swimnetics-mobile` (3 PNGs + `Info.plist`), 6 created in `myswimcoach/scratch/` |
| Commits | **none** — both trees left for the user's own git decisions |
| Build spent | **none** — deferred by decision |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Rasterizer deterministic and re-runnable | **Pass** | `python scratch/make_app_icons.py` run three times; SHA-256 of all three outputs byte-identical every run (`7b5360fe…`, `e8fc95c0…`, `bfebd9ee…`). Prints mode, size and tRNS state per file. |
| AC-2: Every emitted PNG is App-Store-legal | **Pass** | Re-checked **at the destination**, not just in scratch: all three `mode='RGB'`, `tRNS` absent, sizes exactly 1024²/180²/120². |
| AC-3: Centred, measured padding, never distorted | **Pass on 2 of 3 clauses; third is unreachable** | Centring: margins (102,103)/(120,121) at 1024, (18,18)/(21,21) at 180, (12,12)/(14,14) at 120 — all within 1 px. Fill: 79.98% / 80.00% / 80.00%, inside ±1%. **Aspect: 0.0137% at 1024 but 0.2252% at 180 and 120, against a 0.1% tolerance.** See Deviation 1 — the floor is 0.164%/0.180%. |
| AC-4: Icon set replaced in place, no manifest churn | **Pass** | Directory holds exactly 4 files; `git diff` on `Contents.json` is empty (byte-identical to HEAD); no added or deleted file anywhere under `ios/`. |
| AC-5: iOS can no longer enter landscape | **Pass** | `plistlib` parses the file and reads `UISupportedInterfaceOrientations == ['UIInterfaceOrientationPortrait']`; 25 keys total; no `~ipad` variant. `git diff --numstat` = `0 2` — two deletions, **zero insertions**. |
| AC-6: Change set is exactly two items wide | **Pass** | `git diff --name-only -- ios/` contains zero `.js`; this plan's diff is exactly `Info.plist` + the three PNGs. Nothing staged, nothing untracked. ⚠ The mobile tree carries **more** than the four Phase-74 files — 84-02's mobile half is also present. That is not this plan's doing and does not violate AC-6, but the first reading of it was stale; see the operational note. |

## Accomplishments

- **The icon is composed, not rendered.** G2 held up exactly: `Swimnetics_icon.svg` is an SVG wrapper
  around a base64 **1004×960 RGBA PNG** anchored at x=0,y=0 inside a 1028×1028 viewBox. Rendering the
  SVG would have shipped the mark off-centre, up and left. The script b64-decodes the payload,
  crops to the alpha bbox, scales longest-side-to-80% with LANCZOS, and pastes onto an opaque canvas
  using the alpha as its own mask — so the 56%-transparent art blends against white rather than black.
- **Alpha is stripped where it actually matters.** `.convert('RGB')` before save is what removes the
  channel; `optimize=True` and no `transparency` kwarg keep the writer deterministic. This is a
  deliberate divergence from Phase 85's web icons, which are correctly transparent — G3 exists so
  nobody "fixes" one to match the other.
- **The orientation bug was a two-line deletion with no JS accomplice.** G5 verified: one
  `UISupportedInterfaceOrientations` key, no `~ipad` variant, `"supportsTablet": false`, and
  `grep -rn "ScreenOrientation|orientation|Landscape" src/` returns nothing. `app.json`'s
  `"orientation": "portrait"` was never wrong — inert in a bare workflow, but a correct record of
  intent the native manifest had drifted from. Task 3 made the manifest agree with it, not the reverse.
- **The aesthetic call was shown, not argued.** `scratch/_icon_preview_sheet.py` renders a 3×3
  contact sheet (3 backgrounds × 3 fills), each tile masked to the iOS superellipse radius and paired
  with a **120 px actual-home-screen-size** twin, because that is where the tentacles thin out first.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `scratch/make_app_icons.py` | Created (97) | The rasterizer. `BG`/`FILL` at `:31` are the two checkpoint knobs |
| `scratch/_icon_preview_sheet.py` | Created (39) | Throwaway 3×3 contact sheet for the decision checkpoint |
| `scratch/appicon/AppIcon-{1024,180,120}.png` | Created | Staging outputs — the install source |
| `scratch/appicon/_preview_sheet.png` | Created | The sheet the decision was made from |
| `…/AppIcon.appiconset/AppIcon-1024.png` | Modified | 6,580 → 74,697 bytes |
| `…/AppIcon.appiconset/AppIcon-180.png` | Modified | 652 → 9,550 bytes |
| `…/AppIcon.appiconset/AppIcon-120.png` | Modified | 449 → 6,175 bytes |
| `…/ios/mobile/Info.plist` | Modified | Two landscape `<string>` lines deleted |
| `…/AppIcon.appiconset/Contents.json` | **Untouched** | Already declares all three filenames; a same-name replacement needs no manifest edit |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Background `#FFFFFF`, fill 80%** (checkpoint answered `approve`) | The mark's white highlight sits *inside* the purple dome and the dome-to-tentacle gap is negative space, so a white ground renders the mark as designed. Max contrast against `#7200FF`; anything darker than ~`#D8C4FF` eats the mark | The shipped defaults were kept. Re-runnable in one line if revisited |
| **EAS build deferred, not spent** | G1: there is no OTA channel, so all seven Phase-84 items need a build anyway. The working tree holds this code safely while 84-02 and 84-03 land, then one build carries everything. 84-03 needs no build at all to verify | **Device verification is owed.** Icon + rotation are invisible in Metro, dev-client refresh, and any simulator on the old binary |
| AC-3's aspect tolerance documented rather than chased | Brute-forced every integer `(w,h)` in the AC's own ±1% fill window; the floor is above the tolerance at both small sizes | The AC should be loosened, not the code. See Deviation 1 |
| No commit in either repo | The mobile repo's history is user-owned and already carries uncommitted Phase 74 work whose commit boundary is CONTEXT open question 3 | Both trees left as found, plus this plan's 4 files |
| Pillow in the backend repo, not `sharp` | G4: `sharp` is not in the mobile repo. It also puts the script where the source art lives, matching `scratch/_export_marketing_geom.py` | One fewer cross-repo dependency |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| AC stated an unachievable tolerance | 1 | Documented with proof; no code change |
| Checkpoint deferred rather than resolved | 1 | Device verification owed; nothing else blocked |

**Total impact:** no scope creep, no unplanned files, no boundary touched.

### 1. AC-3's aspect clause is unreachable at 180 px and 120 px (forced by pixel quantization)

- **Found during:** Task 1 verification
- **Issue:** AC-3 demands the aspect ratio be preserved "to within 1 part in 1000". The 1024 output
  hits 0.0137%, but **180 and 120 land at 0.2252%**. The source is 1004×960 (1.045833:1); at 144 px
  wide the ideal height is 137.69, and neither 137 (0.51% error) nor 138 (0.225%) is inside 0.1%.
- **Fix:** none. Brute-forced every integer `(w,h)` pair inside the AC's *own* ±1% fill window to
  find the achievable floor:

  | edge | best w×h | best achievable aspect error |
  |------|----------|------------------------------|
  | 1024 | 821×785  | 0.0025% |
  | 180  | 142×136  | **0.1640%** |
  | 120  | 95×91    | **0.1795%** |

  Both small sizes are structurally above the tolerance. Chasing it would mean either distorting the
  art or breaking the fill clause, and 0.2% is invisible at 120 px.
- **Verification:** the sweep above; centring and fill clauses independently pass at all three sizes.
- **Owed at UNIFY:** loosen AC-3's aspect tolerance to ~0.3%, or scope the 0.1% clause to the 1024 output.

### 2. The human-verify checkpoint was deferred, not answered

- **Found during:** Task 5
- **Issue:** the checkpoint requires a paid EAS build, and the plan's own sequencing note flags that
  the same build could carry items 2, 3, 5, 6 and 7 if those land first.
- **Fix:** user chose `defer`. The plan anticipated this explicitly — "landing this plan's code does
  not commit you to building immediately."
- **Consequence:** **the only unverified thing is how the icon reads at real home-screen size and
  whether rotation is genuinely blocked on device.** Every static property (alpha, mode, dimensions,
  centring, plist validity, diff shape) is proven without a build.

## Corrections to CONTEXT (carry these into 84-02+)

Recorded per the plan's `<output>` requirement — CONTEXT's stale claims should not mislead later plans.

| # | CONTEXT said | Truth |
|---|--------------|-------|
| **G1** | Open question 2: is there an OTA channel? | **No.** No `expo-updates` dep, no `updates` key in `app.json`, no channels in `eas.json` — only build/submit profiles. **All seven Phase-84 items need a build.** The native/JS split drives *verification cost*, not shipping order |
| **G2** | `Swimnetics_icon.svg` is a vector | **It is a base64 1004×960 RGBA PNG in an SVG wrapper.** 56.4% fully transparent, two inks (`#7200FF` 403,299 px + `#FFFFFF` 7,356 px), ink bbox = the whole canvas (zero margin on all four sides), `<image>` anchored top-left in a 1028×1028 viewBox. So 1024 is a 2% upscale, padding must be invented, and the SVG must never be rendered |
| **G3** | (implied) follow the web icon precedent | **Do not.** `web/app/icon.png` and `apple-icon.png` are RGBA with transparent grounds — correct for a favicon, and **rejected by App Store validation** for an app icon |
| **G4** | `sharp` is in the mobile repo | **It is not.** It lives at `myswimcoach/web/node_modules/sharp@0.34.5`. This plan used Python Pillow in the backend repo instead |
| **G5** | Item 4's root cause is `Info.plist` | **Exact and complete.** Confirmed: one orientation key, no `~ipad` variant, `"supportsTablet": false`, zero JS orientation code anywhere in `src/` |
| **(84-01 G-fact 3)** | `AthleteDetailScreen` can look up `rating_colors` | **It cannot** — its pillars come from `route.params.athlete`, not a fetch. Item 5 needs **navigation-param plumbing**, not a lookup swap. ⚠ Already carried into 84-03's plan; leaving it here as the origin |

## ⚠ Operational note — the mobile tree read stale TWICE, and the second time mattered

The mobile repo sits under a OneDrive-synced Desktop path, and its state materialised progressively
across this session rather than being stable at first read.

**First stale read (harmless):** `ls` and `git status` on `AppIcon.appiconset/` returned the May-21
placeholders (6,580 / 652 / 449 bytes) several minutes after the install had actually written the new
bytes; a later read showed the correct 74,697 / 9,550 / 6,175. This nearly caused a redundant re-copy
of files that were already correct.

**Second stale read (consequential):** the opening `git status` on that tree listed **four** modified
files. By the end of the session it listed **nine**. The newcomers were not random — they are
**84-02's entire mobile half**, carrying explicit `Phase 84-02` comments:

| File | numstat | What it is |
|------|---------|------------|
| `src/screens/RecordScreen.js` | 120/8 (was read as 53/7) | The coach GO marker: `goPressPhoneMsRef` / `goSignalSRef`, the `go_signal_s` upload param, the silent GO button |
| `src/lib/startSequencePrefs.js` | 17/4 | Key bumped to `startSequenceEnabled.v2`, default flipped to OFF, fail-closed |
| `src/screens/RecordingConfigScreen.js` | 24/12 | `SHOW_START_SEQUENCE_TOGGLE = false`, toggle hidden not deleted |

**And 84-02's backend half is in `myswimcoach` too:** `api.py` (20/5 — the optional `go_signal_s`
form field, invalid values dropped-and-logged rather than 422'd, the stale clock-sync docstring
corrected) and `tests/test_api.py` (70/4 — `_post_csv` gains the optional param, plus the four new
GO tests).

**Consequences for this plan: none.** AC-6 constrains *this plan's* diff, which is still exactly
`Info.plist` + three PNGs with zero `.js`. My files were re-verified by content hash at the end of
the session and had not drifted.

**Consequences for 84-02: material.** Its code appears substantially applied but it has **no SUMMARY,
no checkpoint answers recorded, and its test suite was not run here.** Do not assume it is finished.

**Rule going forward:** on this tree, verify file state by hashing content, and re-read `git status`
at the END of a session as well as the start. A single opening `git status` is not trustworthy.

## Owed / Next Actions

1. **`npx expo-doctor` in `swimnetics-mobile`, then `eas build --platform ios --profile preview`** —
   standing SDK-56 rule: precompiled frameworks build clean under version skew and then dyld-crash at
   launch, so a green doctor is the only cheap signal before paying for the build.
2. **Device verify both items** — icon on home screen / Settings list / App Switcher; rotation blocked
   on Dashboard, Report Card (velocity chart) and Record-with-Video, **with the device rotation lock
   OFF** or the test proves nothing.
3. **Batch the build** with 84-02 (GO marker) and 84-03 (indicators) if they land first — 84-03 needs
   no build to verify, so it is free to land in the meantime.
4. **Commit boundary** for both trees is still the user's call. The mobile tree carries this plan's
   4 files alongside the Phase-74 work **and 84-02's mobile half**; `myswimcoach` carries 84-02's
   backend half. A commit that is meant to be "84-01 only" must be path-scoped to
   `ios/mobile/**` — a bare `git commit -a` would sweep in 84-02.
5. **⚠ Reconcile 84-02 before applying it.** Its code is largely in both trees already (see the
   operational note) but it has no SUMMARY and its suite was not run here. Run `pytest tests/` and
   review its checkpoints rather than re-applying blind.
