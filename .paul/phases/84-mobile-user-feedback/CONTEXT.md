# Phase Context

**Phase:** 84 — Mobile App User Feedback (6 reported issues)
**Generated:** 2026-08-29 (`/paul:discuss`, AskUserQuestion ×1 / 4 questions, code survey first)
**Status:** Ready for planning
**Target repo:** ⚠ **`Desktop/swimnetics-mobile`** — a SEPARATE, user-owned git repo. PAUL docs stay
in `myswimcoach`; essentially all code in this phase lands in the mobile repo.
**Not to be confused with:** Phase 60 (mobile app rework) or Phase 55 (athlete flow fixes). This is a
user-feedback bug/polish batch, not a rework.

---

## Why now

Six items came back from users. They are not one theme — they are two native-config defects, one
silent data-loss bug, one missing-control gap, one consistency debt, and one gesture bug. They are
batched because they all ship in the same EAS build, not because they share a mechanism.

User ask (verbatim): *"1. update the app icon with the svg in asset folder / 2. autocall upload
function behind video overlay / 3. camera needs better options, such as zoom etc / 4. it should not go
into horizontal mode on ios / 5. disparity between athlete page indicator and dashboard — should
formalize indicators / 6. scroll bar feature is annoying — once finger leaves the bar, the scrolling
side to side stops and goes up and down"* — plus *"These are feedback from users, some of them I'm not
sure if i can recreate."*

**Four of six were root-caused from code during this discussion. One (item 2) is genuinely a
diagnostic and was rescoped as such. None turned out to be unrecreatable.**

---

## Grounded state (read from code, 2026-08-29)

### The native/JS split — the sequencing fact that shapes the whole phase

| Item | Layer | Lands via |
|---|---|---|
| 1 app icon | **native** (asset catalog) | new EAS build only |
| 4 orientation | **native** (Info.plist) | new EAS build only |
| 2 upload | JS | build, or OTA if configured |
| 3 camera | JS (expo-camera props) | build, or OTA |
| 5 indicators | JS | build, or OTA |
| 6 scroll bar | JS | build, or OTA |

⚠ **Memory rule applies: run `expo-doctor` before every paid EAS build.** SDK 56 precompiled
frameworks build fine under version skew and then dyld-crash at launch.

⚠ **The mobile tree has uncommitted Phase 74 work** (`RECORD_STALL_MS` 30 s→8 s, `MAX_RETRIEVAL_ATTEMPTS`,
retrieval auto-retry) in `RecordScreen.js` + `BleContext.js` + `CycleCharts.js`. No conflict with any
item here — but it will ride along in any commit, so the plan must decide whether to commit it first
or accept a mixed commit.

---

### Item 1 — App icon (real, cheap, native)

`app.json` has **no `icon` field at all**. Bare workflow, so `app.json` would be inert anyway. Icons
live natively:

- `ios/mobile/Images.xcassets/AppIcon.appiconset/` — `AppIcon-1024.png`, `AppIcon-180.png`,
  `AppIcon-120.png` + a `Contents.json` declaring exactly those three (60x60@2x, 60x60@3x,
  ios-marketing 1x). **Replacing the three PNGs in place needs no `Contents.json` edit.**
- Source SVG lives in the **backend** repo: `assets/icon/Swimnetics_icon.svg` (untracked — `??` in
  git status).
- `sharp` is present in the mobile repo's `node_modules` → SVG→PNG is a script, not a manual export.
  (`convert` on PATH is Windows' NTFS `convert.exe`, **not** ImageMagick — do not reach for it.)

⚠ iOS app icons **must not have alpha**. Flatten onto an opaque background when rasterizing, or App
Store validation rejects the build.

### Item 2 — Video upload fails sometimes (RESCOPED: diagnostic, not a feature)

**The premise in the original ask is false, and that matters.** Both plausible "missing" calls already
fire automatically:

- the video **file** auto-enqueues at [`RecordScreen.js:305`] into the app-wide FIFO queue,
  fire-and-forget, immediately after the CSV upload returns a `session_id`;
- the **sync origin** auto-saves at [`VideoOverlayScreen.js:164-181`] — once on mount, then debounced
  1 s on every manual nudge.

So there is nothing to "autocall". The real report is **"there's cases when video fails to upload —
find out why"** (user, this session). Five concrete failure paths, read from code, roughly in
descending suspicion:

**H1 — the 50 MB server cap (deterministic 413).** `api.py:1204` `MAX_VIDEO_BYTES = 50 * 1024 * 1024`,
enforced at `api.py:1232` **before** buffering. expo-camera's `CameraView` is rendered with **no
`videoQuality` prop** (`RecordScreen.js:776`), so it records at device default. A 20–30 s clip at
1080p60 lands in the tens of MB and at 4K blows straight past 50 MB. A 413 is **deterministic**, so
all three attempts fail identically and the retry budget is pure waste.

**H2 — Supabase storage is over quota.** Phase 82 measured 2.53 GB against a 1 GB free-tier cap and
flagged *"new uploads may already be blocked"*. If storage is rejecting writes, every video upload
fails regardless of size. ⚠ **This makes Phase 82 (or the Supabase Pro upgrade) a likely prerequisite
to even measuring H1 cleanly** — an unresolved dependency the plan must confront.

**H3 — the queue is in-memory and dies on app restart (silent loss).** `videoUploadQueue.js:6`
states it outright: *"In-memory only — jobs do not survive an app restart (the video file stays on
disk)."* App killed, crashed, or reclaimed by iOS before the queue drains ⇒ the job vanishes, the file
is orphaned on disk, nothing ever retries, **and no error is surfaced anywhere.** This is the path
most consistent with "sometimes it just isn't there."

**H4 — enqueue is skipped whenever the CSV path errors early.** The `enqueueVideoUpload` call sits
*after* `setBleState('results')` and is gated on `data.session_id`. Every earlier `return` (JSON parse
failure, non-2xx upload, network throw) skips it — so a hiccup on the **CSV** upload silently costs
the **video** too, even though the video file is intact on disk.

**H5 — the retry budget is ~13 s total.** `RETRY_DELAYS_MS = [3000, 10000]`, `MAX_ATTEMPTS = 3`. That
is not a poolside-wifi budget. After it, the job parks as `failed` for a `UploadToast` chip — which is
**dismissible and does not survive a restart**, so the only recovery affordance is transient.

**H6 (lower) — iOS background NSURLSession + multipart.** `sessionType: BACKGROUND` with
`uploadType: MULTIPART`, via the **legacy** import `expo-file-system/legacy`. Background-session
multipart is historically fragile, and the legacy import signals API drift worth checking against
SDK 56.

**Diagnosis must come before the fix.** The plan should establish which hypotheses actually fire
(clip sizes on disk, server logs / status codes, quota state) rather than shotgunning all six fixes.

### Item 3 — Camera options (real, straightforward, JS)

`CameraView` (`RecordScreen.js:776-784`) is rendered with **only** `mode="video"`, `facing="back"`
(hardcoded), `mute`, `onCameraReady`. No zoom, no lens pick, no torch, no quality. expo-camera
`~56.0.8` supports `zoom` (0–1), `facing`, `enableTorch`, `videoQuality`.

⚠ **Precedent for the control style already exists in this codebase.** `VideoOverlayScreen.js:36-42`
documents why presets beat a slider: *React Native dropped its built-in Slider at 0.60, so a
continuous control means `@react-native-community/slider` — a native module, and therefore a fresh EAS
build just to evaluate it.* `SPAN_PRESETS` is the shape to copy.

### Item 4 — Landscape on iOS (real, root-caused, one edit, native)

`app.json` declares `"orientation": "portrait"` — **but this is a bare workflow, so `app.json` is inert
for orientation.** The native file wins and disagrees:

```
ios/mobile/Info.plist → UISupportedInterfaceOrientations
  UIInterfaceOrientationPortrait
  UIInterfaceOrientationLandscapeLeft    ← delete
  UIInterfaceOrientationLandscapeRight   ← delete
```

The `app.json` value is the *intent* and was never wrong; only the native manifest drifted from it.

### Item 5 — Indicator disparity (real, and larger than reported: **three** vocabularies)

The user reported athlete-page vs dashboard. There is a third on the report card.

| Surface | Shows | Color source | `provisional` handling |
|---|---|---|---|
| `DashboardScreen` | averaged **0–100 score** (`overallScore`, :38) + a `needs_attention` reason chip | server `data.rating_colors`, theme fallback (:109) | **excluded from the score** (:39) |
| `AthleteDetailScreen` | per-pillar **band label** (:151-165) | **hardcoded local `BAND_COLOR`** (:18) — ignores `rating_colors` | **ignored entirely** |
| `PillarCards` (report card) | per-pillar **band label** | a **third** inline derivation (:68), has an `unknown` case | page-level warning banner (:166-168), and *does* pass `rating_colors` (:170) |

Consequence, stated plainly: **a provisional pillar is invisible on the dashboard, colored as if
trustworthy on the athlete page, and warned about on the report card.** `AthleteDetailScreen`'s
`BAND_COLOR` also has no `unknown` key, so an unknown band silently renders `textMuted` + `'—'`.

This is the "formalize" the user asked for: one shared indicator module, one color contract.

### Item 6 — Brush-bar gesture (real, root-caused, cheap, JS)

`VelocityChart.js:99-113` — the brush-strip `PanResponder` **never sets
`onPanResponderTerminationRequest`, which defaults to `true`.** Sequence:

1. Finger lands on the bar → `onStartShouldSetPanResponder: () => true` grants → `onInteractionStart`
   → `ReportCardScreen` sets `scrollEnabled=false` (:538).
2. Finger drifts vertically off the bar → the parent `ScrollView`'s **native** pan recognizer asks RN
   for the responder.
3. Default `onPanResponderTerminationRequest` says **yes** → brush hands it over →
   `onPanResponderTerminate` (:113) fires → `onInteractionEnd` → `scrollEnabled=true` (:539).
4. Page scrolls vertically. **Exactly the reported symptom.**

Note `setScrollEnabled(false)` is async React state, so it may not even have landed natively before
the recognizer engages — a second reason a drag can be stolen. The chart-body responder (:75-96) has
the same omission.

⚠ `VideoOverlayScreen.js:219` renders `VelocityChart` **without** `onInteractionStart`/`End` at all —
worth confirming whether that surface is inside a scroll container before assuming it is unaffected.

---

## Decisions taken in this discussion

- **D1 — Icon scope: iOS only.** `android/app/src/main/res/mipmap-*` exists but Android is not a
  shipping target. No splash/launch-screen work.
- **D2 — Item 2 is a DIAGNOSTIC, not a feature.** Deliverable is "find out why uploads fail", then
  fix what the evidence names. Explicitly *not* "add an autocall" — there is nothing to add.
- **D3 — Canonical indicator = band label + color, from the server's `rating_colors`.** Applied
  across all three surfaces via one shared component/module. The dashboard **keeps its 0–100 score as
  a secondary roll-up**, not as the primary indicator. Rationale: matches the report card and the web
  portal, honors the server color contract, and fits the product's within-athlete-contrast doctrine
  (`product_attention_allocation`) better than an absolute number.
- **D4 — Camera scope: discrete zoom presets + front/back lens toggle.** Torch and video-quality
  controls are **out of scope as features**. ⚠ See D5.
- **D5 — `videoQuality` may still enter the tree via item 2.** If H1 (50 MB cap) is confirmed,
  setting `videoQuality` is part of the *upload fix*, not a camera feature. The plan must place it in
  item 2's lane so D4 is not quietly violated.
- **D6 — Item 6 fix = `onPanResponderTerminationRequest: () => false`** on the brush responder (and
  evaluate the chart-body responder). Capture-phase guards to be settled at plan time.
- **D7 — Item 5 scope is all three surfaces**, not just the two the user named. Fixing only
  dashboard + athlete detail would leave a third vocabulary in the tree and re-open the same debt.

---

## Open questions for planning

1. **Is Phase 82 / the Supabase Pro upgrade a hard prerequisite for item 2?** If storage is still
   rejecting writes, item 2's diagnosis cannot separate H1 from H2. Sequencing decision.
2. **Is EAS Update (OTA) configured?** Determines whether items 2/3/5/6 can ship without waiting on
   the native build that items 1/4 require. Not verified during this discussion.
3. **Commit the uncommitted Phase 74 work first, or accept a mixed commit?**
4. **Does the queue need persistence (H3) in this phase, or is that its own phase?** AsyncStorage-backed
   job persistence is a meaningful chunk of work, not a one-liner.
5. **How much of item 2 is fixable without a device?** Verification of items 1, 3, 4 is device-only.
6. **Does `VideoOverlayScreen`'s `VelocityChart` need the item-6 fix too**, or is it outside a scroll
   container?

---

## Risks

- **Device verification is unavoidable for 1, 3, 4** — no Mac (`PROJECT.md` constraint), so every
  native check costs an EAS build cycle. Batch them into one build.
- **Item 2 could resolve to "the backend was over quota"** — a Phase 82 problem, not a mobile one.
  Plan should be willing to hand it back rather than manufacture a mobile fix.
- **Item 5 touches three screens' visual language** at once; regression surface is the whole app's
  read-at-a-glance layer.
- **Cross-repo bookkeeping:** the mobile repo's git history is user-owned and its `.gitignore` has
  historically swallowed files (`project_codebase_audit` memory — *don't trust a clean git status in
  either repo*).

---

*Next: `/paul:plan` — item 2 likely wants its own plan (diagnostic-first), with 1+4 (native), 3, 5, 6
grouped by verification cost.*
