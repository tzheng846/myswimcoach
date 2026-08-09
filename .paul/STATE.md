# Project State

**NEW FOCUS: Phase 58 (Video Ground Truth — solo capture + annotate-from-video)** — discussed
  2026-08-05 via /paul:discuss; CONTEXT.md written; **58-01 PLAN created, awaiting approval**.
  **58-02 PLAN created 2026-08-07, awaiting approval** — see Loop Position (58-02) below.
  TRIGGER: labeling the 19-session batch proved the Phase-57 tool's core assumption FALSE for
  alternating strokes. User: *"freestyle and backstroke — it's almost impossible to discern when does
  one stroke start and ends… for 3-4 of the freestyle swims, it's extremely jumbled together."*
  Fly/breast trough-labeling is fine. The 19 have ZERO video and none can be added retroactively.
  Tripod + video test scheduled **2026-08-06, run SOLO** — the swimmer IS the operator, which is why
  auto-stop is the blocker: today they must swim back to press Stop.
  ⚠ TWO OF THE FOUR ASKS WERE ALREADY BUILT — verified in code before planning:
    • **Web annotation already reaches iOS.** `PUT /annotations` rewrites `sessions.metrics_json`
      (47-04); `ReportCardScreen.js:94-95` selects it fresh on every open. NO CODE. Only the numbers
      cross over — marks are never drawn on the phone (no stated consumer → out of scope).
    • **Chart↔video scrubbing already works both directions.** `page.js:128` chart-click → video
      seek; `onPlayhead` → `playheadS` → chart marker. The missing direction is MARKING — marks land
      where you click the CHART, and there is no "mark at the video's current time." Both halves
      already exist in the page; only the wiring is absent. → 58-02.
    • The CAMERA itself was already shipped and device-verified (RecordScreen.js:473-580 one-tap
      video, `videoUploadQueue` background FIFO; 47-03 verified in the Phase-55 build). The 19 have
      no video because the mode wasn't used that day.
  REAL GAPS FOUND:
    • `video_origin_s` reaches the server ONLY from `VideoOverlayScreen.js:92-125` — the background
      upload sends the FILE ONLY. A record-with-video session never opened in Video Overlay arrives
      on the web at `origin_s = 0`, silently unsynced. Until 58-02, every video session needs that
      tap; it is an explicit checkpoint step in 58-01.
    • A failed `writeCmd('STOP')` is caught NON-FATAL while the device keeps recording, inflating
      `deviceDuration` and therefore the auto-posted end-anchored origin. Silent, plausible-looking
      corruption of the same shape as Phases 51/52/57. **Auto-stop removes it** by firing camera-stop
      and STOP off one timer — which is precisely the premise the end-anchor rests on.
  USER'S RECOLLECTION CONFIRMED (buffer-and-dump makes the swim BLE-free): `ESP_32_V5.ino:520-529`
    `onDisconnect` cancels pending meta/dump/status, restarts advertising, and deliberately leaves
    `recording` alone — *"Recording is independent of the connection in buffer mode — keep going."*
    `dumpBuffer` aborts on disconnect but RETAINS the buffer (:474-480). Buffer-full truncates and
    keeps the data, never wraps (:759-766) — you lose the tail, never the start. BLE is needed at
    exactly two moments: START, and STOP + dump. NO FIRMWARE CHANGE NEEDED.
  DECISIONS (user, 2026-08-05, AskUserQuestion ×4 + direct):
    • D1 auto-stop default **20 s** ("trust me") — CONFIRMED against their own data rather than taken
      on faith: the two supplied traces run 18.93 s and 16.53 s end to end with velocity back to zero
      before each recording ended, so 20 s clears both with ~1 s and ~3.5 s margin. My earlier 15 s
      warning stands; my 30 s suggestion was over-cautious and was withdrawn. Editable + live
      countdown, because unlike buffer-full (which truncates safely) a too-early stop genuinely
      loses the end of the swim.
    • D2 capture via the EXISTING one-tap video mode, **held provisional** — it structurally pins the
      tripod near the block (BLE range to the block-mounted encoder), i.e. the shallow ~4° rear angle
      most exposed to glare and occlusion.
    • D3 lab-now / product-later. NAMED COST: with the phone as camera a coach holds it every trial —
      a real burden against Phase 53's 30-swimmers-in-an-hour target.
    • D4 the 19: annotate what's legible, FLAG the rest. Needs vocabulary that does not exist —
      absence of an annotation currently conflates *not yet done* with *cannot be done*, the same
      failure mode 57's CONTEXT named for null markers. Must be exportable so 16-06 can exclude it.
    • D5 no IMU / no on-swimmer sensor — second device, second clock, sync protocol, waterproofing,
      and it contradicts PROJECT.md's "swimmer just swims."
  OPTICS, COMPUTED NOT ASSUMED: distance is NOT the constraint. ~70° HFOV → frame width ≈ 1.4×d, so
    at 25 m that is ~35 m: 55 px/m at 1080p, 111 at 4K. A 0.4 m hand-entry splash is 22-44 px;
    left-vs-right entry separation (~0.45 m) is 25-50 px. **Angle, glare and occlusion are the risks**
    — a deck tripod sits ~1.8 m above the water, so the depression angle at 25 m is ~4°. UNTESTED;
    this is the phase's one genuine unknown (R1), and it is answerable with NO encoder, NO BLE and NO
    app — film one 25 from three positions and try to mark entries off the footage.
  R2 (why R1 may not matter much): 57's CONTEXT already states the marks record **alternation timing,
    not verified arm identity**. Footage only has to show THAT an entry happened and WHEN.
  ⚠ SCHEDULING UNKNOWN, decides whether 58-01 lands before the pool: `expo-dev-client` is installed
    but `expo-updates` is NOT. A dev build loads JS off Metro with no EAS round trip; a TestFlight
    build needs a paid EAS build plus queue. **Confirm which is on the phone before starting.**
  ⚠ BLOCKING ON 58-02 (not on 58-01): **57-02's human-verify checkpoint is still open on an
    already-deployed page.** 58-02 edits that same page; starting first makes any defect found at the
    checkpoint indistinguishable from a 58 regression.
  OUT OF SCOPE: IMU; retroactive video for the 19; rendering marks on iOS; product-grade capture UX;
    pose estimation / auto-labeling (also barred by 57 D7); multi-angle; BLE auto-reconnect
    (`BleContext.js:94-98` has none — real, but not triggered by a stationary tripod setup); firmware.
  ⚠ **58-02 SCOPE AMENDED 2026-08-07** (/paul:discuss, AskUserQuestion ×7 — CONTEXT.md "Amendment").
    Two additions from the first real attempt to annotate with video open, both web-only:
    • D6 the video is UNBOUNDED and pushes the chart off-screen — verified structural, not styling:
      `VideoPane.js:143` renders `<video className="w-full …">` with NO height constraint inside
      `page.js:337`'s `max-w-5xl` `[1fr_300px]` (~700 px column), so 16:9 = ~394 px tall and
      **portrait 9:16 = ~1244 px** (portrait IS the expected case — 58-01 was told "assume
      portrait"), above a fixed 340 px chart. FIX: ~35 vh cap + `object-contain` + page to
      `max-w-7xl`. Side-by-side/sidebar/resizable all DECLINED — at ~40 marks per freestyle 25 the
      chart's horizontal pixels are the precision budget.
    • D7 **Breakout removed from the contract — SUPERSEDES Phase 57 D5** for that marker only (D5
      still holds for UW kick, which stays). Surface is small and verified: `annotations.py:41`,
      `AnnotationChart.js:38`, 3 tests, 2 SQL comments — **api.py never names it, `phases` is
      free-form JSONB → NO SQL patch.** ONE hazard: `validate_annotation:238-240` rejects unknown
      phase keys → legacy values are **stripped silently on read** (accepted cost: that time is lost
      on the next save). User: "what used to be breakout is absorbed into dolphin kick or pulldown
      for respective strokes" — the UW/Pulldown band now runs to `stroke_start_s` and the UI must say
      so. **NOTHING RECOMPUTES**: `annotation_to_overrides` only ever read dive/stroke/finish,
      `stroke_start_s` keeps its meaning, and "first cycle contains breakout" is DOCUMENTATION ONLY
      (export-flagging and excluding cycle 1 from averages both offered, both declined — the latter
      would have shifted mean_dps_m/cv_isi/mean_coast_fraction on every session, paying 57-01's
      comparability cost twice).
    • D8 frame-step (~1/30 s) + 0.25×/0.5×/1× ship WITH mark-at-playhead: native HTML5 has no frame
      step, so ±0.3 s scrubbing would make mark-at-playhead COARSER than clicking the chart.
      ⚠ `page.js:230` already binds ←/→ to nudge-selected-mark — collision needs a rule at plan time.
    • ⚠ DEPLOY ORDER — **CORRECTED 2026-08-07, EITHER ORDER IS SAFE.** The rule below was derived
      before `LEGACY_PHASE_KEYS` existed and was not re-derived afterwards. With the tolerance in
      place a NEW backend accepts `breakout_start_s` from an OLD page (validate_annotation skips
      it, api.py:857 drops it on write), so the 422 this guarded against cannot occur; the only
      effect of a backend-first window is that a Breakout mark placed on a stale tab silently does
      not persist — cosmetic, and that marker is being abandoned anyway. New-web/old-backend is
      also fine (the client stops sending the key; the old backend writes it as null).
      SUPERSEDED TEXT: web before backend, or together. NEVER backend first — `page.js:14-18`
      `normalizePhases` already filters to PHASE_KEYS so the client stops sending the key for free,
      but a backend-first deploy 422s a stale open tab.
    • 57-02's checkpoint gate on 58-02 is **LIFTED** (approved 2026-08-05). Remaining contention:
      57-03 and 58-02 both edit `web/app/app/annotate/[id]/page.js` — do not apply concurrently.
  Context: .paul/phases/58-video-ground-truth/CONTEXT.md
  Plan: 58-video-ground-truth/58-01-PLAN.md. DO NOT APPLY until user says so.
  ⚠ CONCURRENCY: ROADMAP.md was modified on disk mid-session by another PAUL environment (the edit
    still applied cleanly). Commit `.paul/` between sessions so this surfaces as a merge conflict.

## Loop Position (58-05)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [58-05 CLOSED 2026-08-07 — SUMMARY written. Checkpoint APPROVED.
                          All 5 ACs pass. 2 files, suite still 237, build exit 0, zero console
                          errors on /app/sessions.
                          ⭐ THE KICK TRAP WAS VERIFIED, NOT ASSUMED — shipped `qualityIssue`
                            extracted and run: kick-only → null, kick+real → the real one, 6.2%
                            dropout → flagged, 3.0% → null, thresholds matching DataQualityCard.
                            The ⚠ indicator will NOT be universal.
                          ⭐ 7-day boundary exact: 6.9 d → "Sun", 7.1 d → "08-01-26"; zero-padding
                            "01-09-26"; null/bogus stroke → "Session · 1:24 PM", no crash.
                          AUTO-FIX: header bottom margin made conditional on whether a chip row
                            follows, so cards with NO chips stay pixel-identical to before.
                          ⚠ **RECOMMENDATION ON 57-03 (required by the plan): DROP THE SEPARATE
                            QUEUE PAGE.** 57-03 existed because "a timestamp-only list will be
                            unusable" — that constraint is gone. The sessions list already IS a
                            queue: newest-first, filterable by stroke + athlete, shows annotated
                            state, revalidates on return. A second page would duplicate it and
                            need syncing forever. WHAT REMAINS: (1) prev/next on the annotate page
                            — the real throughput win, still unaddressed; (2) a "Not annotated"
                            filter chip beside the stroke chips, ~10 lines since the annotated Set
                            is already in that component's state.
                          ⚠ Checkpoint approved WITHOUT itemised answers to the two questions the
                            plan asked it to report: whether the 19 are in practice distinguishable,
                            and whether ⚠ is informative on real data. Mechanisms proven by the
                            extracted-function run; the real-data judgement is not recorded.
                          Prior detail: created 2026-08-07 — session-card legibility. Web only, 2 files
                          (`app/app/sessions/page.js`, `components/portal/SessionCard.js`), NO
                          backend, NO schema, NO new dep. autonomous:false, depends_on [].
                          TRIGGER: the card shows a bare date, so the 19-session corpus renders as
                          nineteen rows reading "Aug 5, 2026".
                          USER DECISIONS (AskUserQuestion ×4): web-only (mobile untouched, cards
                          will diverge — accepted); auto-name is DISPLAY-ONLY (`sessions.name` is
                          never written → all 19 fixed with no backfill, typed names still win);
                          weekday+time then date+time; extras = athlete name + 🎥 video + ⚠ quality.
                          Duration-instead-of-Distance was offered and DECLINED — stat row unchanged.
                          ⚠ **THE DATE RULE AS ASKED WOULD HAVE FAILED ON THIS EXACT CORPUS.**
                            57-01's Supabase read established the 19 are a TIME BLOCK on one evening
                            (19:50–20:59), not a date — plain day-of-week renders all nineteen as
                            "Wed". Resolution: time in the TITLE, weekday in the META line, so they
                            separate without duplicating.
                          ⚠ **TRAP FOUND AT PLAN TIME:** metrics.py sets `kick_metrics_reliable =
                            False` on EVERY session, so a naive `warnings.length > 0` quality check
                            would put ⚠ on literally every card, carrying zero information. Plan
                            mirrors DataQualityCard.js:28-31's kick-warning exclusion, and the
                            checkpoint explicitly asks the user to report if ⚠ is universal.
                          ⚠ **NO BACKEND NEEDED** — `session_annotations` is readable straight from
                            supabase-js (patch_07 creates a FOR ALL team-scoped RLS policy). One
                            key-only query, not an endpoint. Tooltip distinguishes *metrics
                            recomputed* from *marks saved, too few cycle boundaries* — conflating
                            them is how a coach concludes an annotation "did nothing".
                          Reuses 58-03's pageshow/focus revalidation (a marker that lags after
                            annotating reads as "not yet done"). 58-03's `resetEditable` hazard does
                            NOT apply here — no user-editable local state on this page; the plan
                            says confirm that rather than assume it.
                          ⚠ **RE-SCOPES 57-03**: that plan's summary names "a timestamp-only list
                            will be unusable" as its blocker; this solves it on the list that already
                            exists. The SUMMARY must recommend whether a separate queue page is still
                            worth building or whether prev/next is all that remains.
                          Numbering: 58-04 (VideoPane end-anchor) is already registered as owed and
                            referenced across 4 files, so this took 58-05 rather than renumbering it.
                          Plan: 58-video-ground-truth/58-05-PLAN.md. DO NOT APPLY until user says so.]
```

## Loop Position (58-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [58-03 CLOSED 2026-08-07 — SUMMARY written. Checkpoint APPROVED.
                          ONE file (`web/app/app/sessions/[id]/page.js`), no backend deploy.
                          Suite still 237 (proves no backend file touched); build exit 0; route
                          200 → /login with zero console errors.
                          ⚠ **THE PLAN'S ONE VERIFICATION REQUIREMENT CAME BACK NEGATIVE.** The
                            "Provisional — stroke segmentation is still being validated" banner
                            fires for **NO stroke**, verified by running ratings.rate_session:
                            breaststroke/freestyle/backstroke/butterfly all any_provisional=False.
                            MECHANISM: ratings.py:229 always falls back to the breaststroke table
                            so `thr_table` is never None, making `provisional` (:184) depend only
                            on whether a pillar's own metric has a threshold — stroke-independent.
                            54-01 dropped the seg_reliable condition and this was the collateral,
                            unnoticed because the WEB gate was believed not to exist so nobody
                            looked at what the web would show once lifted.
                            LIVE CONSEQUENCE: freestyle pillar bands/scores/verdicts now display
                            with NOTHING on screen saying they are breaststroke-derived and
                            unvalidated, over segmentation 16-04 measured at 3/8 within ±5 SPM.
                            **User was shown this at the checkpoint and approved.** Accepted and
                            recorded, NOT an oversight. Phase 53 owns whether those bands should
                            exist. STILL OPEN.
                          ⚠ AUTO-FIX that prevented a real regression: the mount effect also
                            assigns sessionName/notes/isStarred. Firing it on every window focus
                            would mean type notes → alt-tab → return → unsaved notes silently
                            replaced. `load({resetEditable})` is true only on first load.
                          ⚠ Whether the original staleness was EVER real is still unknown — the
                            Back-button observation was never reported. The pageshow/focus refetch
                            is hardening against an UNCONFIRMED cause; do not describe it as a
                            diagnosed bug fix.
                          ⚠ PHASE 54's RECORD IS WRONG — see below; ROADMAP row corrected.
                          Prior detail: created 2026-08-07 from two items raised at 58-02's
                          checkpoint; originally 3 tasks with a diagnosis bisect.
                          ⚠ **PHASE 54's RECORD IS WRONG AND THIS PLAN CORRECTS IT.** 54-01's
                            verified-surface note says "Web has NO stroke gate (already
                            unrestricted); the stroke gate is ratings.py:176 + mobile
                            ReportCardScreen.js:192 only." FALSE — `web/app/app/sessions/[id]/
                            page.js:99` has carried `isAnalyticsReady = !strokeType || strokeType
                            === "breaststroke"` since Phase 23, gating 5 sites (view toggle,
                            PillarCards/MetricGrid, TimeToX, per-cycle breakdown, CoachChat).
                            The mobile half shipped in the Phase-55 build; the web half was never
                            touched because the audit said there was nothing to touch. HOW IT
                            SURVIVED: both copies use the SAME identifier `isAnalyticsReady`, so a
                            grep would have found it — the miss was in the reading, not the search.
                            ROADMAP's Phase 54 row needs the correction at UNIFY.
                          T1 gate → true (one line, restorable, dead branch kept — 54-01's mobile
                            pattern). Accepted consequence now applies to web too: breaststroke-
                            derived bands over segmentation flagged unreliable. PillarCards.js:141
                            already renders the "Provisional" banner off `p.provisional` — VERIFY
                            it does rather than assume.
                          ⚠ **SCOPE REVISED SAME DAY, BEFORE APPLY.** Originally opened with a
                            diagnosis task for "saved annotation not reflected on the report card".
                            The user then observed it updating correctly. **58-02 touched NOTHING
                            on the report-card path** (its six files were annotations.py, tests,
                            VideoPane, AnnotationChart, AnnotationEditor and the *annotate* page),
                            so that improvement cannot be credited to a code change — leaving
                            either a cache-dependent bug between appearances, or `initial_phase`
                            carried over by design (api.py:905) being mistaken for staleness.
                            User chose CONFIRM-AND-HARDEN over a diagnosis campaign. Dropping the
                            diagnosis also dropped the api.py and annotate-page edits → no file
                            contention, `depends_on []`, ONE file, no backend deploy.
                          T2 extract the mount-only fetch (`:33-59`) into `load()`; also call it on
                            `pageshow`/`persisted` and window `focus`. ⚠ **The bfcache case is the
                            one `router.refresh()` CANNOT reach** — on a bfcache restore the
                            component never re-runs, so nothing React-side fires at all.
                            Records (non-blocking) whether a Back-button return actually reproduced
                            the staleness — the last cheap chance to catch the original report in
                            the act. If it does NOT reproduce, the SUMMARY must say the refetch is
                            hardening against an unconfirmed cause, not a diagnosed one.
                            Also surfaces `data_quality.recomputed_from_annotation` (api.py:899
                            sets it; NOTHING renders it) — worth doing regardless: without it the
                            coach cannot tell "annotation had no effect" from "annotation worked
                            and the numbers barely moved", the ambiguity that produced the report.
                          ⚠ T1 must VERIFY the "Provisional" banner still fires for freestyle —
                            54-01 dropped `(not seg_reliable)` from that flag, so it is unclear
                            whether PillarCards.js:141 still renders the only warning that those
                            bands are breaststroke-derived. Check, don't assume; don't substitute.
                          Plan: 58-video-ground-truth/58-03-PLAN.md. DO NOT APPLY until user says so.]
```

## Loop Position (58-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [58-02 CLOSED 2026-08-07 — SUMMARY written (58-02-SUMMARY.md).
                          **CHECKPOINT APPROVED** by the user. All 6 ACs pass.
                          ⚠ PHASE 58 IS **1 of 3** PLANS CLOSED, NOT COMPLETE. 58-01 is still
                            paused at its own checkpoint (iOS auto-stop) and 58-03 is created but
                            unapplied. Do NOT fire a phase transition.
                          ⚠ **R1 STILL UNANSWERED — SECOND CONSECUTIVE PLAN.** 57-02's SUMMARY had
                            to record it unknown; 58-02's checkpoint was approved without a report
                            on it either. Whether ~40 arm-entry marks are placeable from footage,
                            and whether the ~4° tripod angle is legible, remain OPEN. It gates
                            Phase 53 Track A4 and 16-06, and both 58-03 and 57-03 are being
                            designed without it. One freestyle session end to end answers it.
                          ⚠ AC-3 (legacy breakout annotation) was verified at UNIT level only —
                            never against a real stored row. Confirm whether one exists.
                          ⚠ DEPLOY ORDER — **CORRECTED 2026-08-07: EITHER ORDER IS SAFE.** The
                            "never backend first" rule was derived before `LEGACY_PHASE_KEYS`
                            existed and not re-derived after. The tolerance makes a new backend
                            accept `breakout_start_s` from a stale page, so the 422 it guarded
                            against cannot happen. Both directions verified by reading the paths.
                          Prior detail: APPLIED 2026-08-07 — all 3 auto tasks + a checkpoint scope
                          addition.
                          VERIFIED: pytest 236 → **237 passed**; `npm run build` exit 0, 18 routes;
                          route serves 200 → /login with **zero console errors on a clean tab**;
                          the swim-window guard exists EXACTLY ONCE in page.js; git shows exactly
                          the 6 planned files.
                          ⚠ **`npm run build` EXIT 0 IS NOT PROOF THE PAGE WORKS.** A `//` comment
                            placed between `return (` and the JSX made SWC fail to parse
                            annotate/[id]/page.js — reporting it at the CLOSING BRACE ~90 lines
                            below the real cause — and `next build` exited 0 anyway while the dev
                            server 500'd. Only loading the route in a browser caught it. Comment
                            now sits ABOVE the return, with a note. **Every future web plan must
                            treat "loads in a browser" as the verification, not the build.**
                          ⚠ SCOPE ADDED BY USER AT THE CHECKPOINT: dynamic sizing for chart, video
                            and tools (the fixed `max-h-[34vh]` from T2 was a magic number).
                            Replaced with viewport-relative clamps, MEASURED in a real browser at
                            two viewports rather than eyeballed:
                              video   `max-h-[clamp(140px,26vh,420px)]`   720h→187px  1000h→260px
                              chart   `height="clamp(220px,30vh,480px)"`  720h→220px  1000h→300px
                              sidebar `clamp(260px,20vw,360px)` (was a fixed 300px) 1440w→288px
                              sidebar `lg:sticky` + `lg:max-h-[calc(100dvh-2rem)]` + own scroll,
                                so Save/Undo stay reachable without scrolling the chart away.
                            Vertical budget fits at BOTH ends: ~671px used of 720, ~934 of 1000.
                            ⚠ AnnotationChart's `height` prop is now a CSS STRING, so
                              `initialDimension` had to be pinned to a literal 320 — recharts needs
                              a NUMBER there. A string would have silently zeroed the chart.
                            ⚠ The chart clamp is an INLINE STYLE, not a Tailwind class, so it does
                              NOT appear in the CSS bundle — verified instead via the live CSSOM
                              (accepted verbatim, computed correctly, floor honored at 720h).
                          DEVIATIONS (3, all minor): (1) `annotations.py:234` still contains the
                            word "breakout" in validate_annotation's docstring — an accurate
                            historical note on why the swim-window check exists; kept deliberately
                            over satisfying the plan's grep. (2) keyboard help text went into
                            AnnotationEditor.js, where the "Pick a tool…" copy lives, not page.js
                            as Task 3's <files> said — the task's own <action> pointed there.
                            (3) `test_round_trip_upsert`'s breakout assertion was carrying the
                            "absent keys normalized" coverage, so it was SPLIT into two assertions
                            rather than replaced — a straight swap would have silently dropped it.
                          Original plan record follows.
                          58-02 created 2026-08-07 — annotate page usable with video + Breakout
                          removed. autonomous:false, depends_on []. 3 auto tasks + 1 human-verify.
                          6 files: annotations.py, tests/test_annotations.py, VideoPane.js,
                          AnnotationChart.js, AnnotationEditor.js, annotate/[id]/page.js.
                          Suite 236 → 237 (one added legacy-tolerance test).
                          T1 Breakout removal as a VERTICAL SLICE (contract + tests + UI in one
                            task — the key is meaningless in isolation and the deploy-order rule is
                            only checkable across both halves). `LEGACY_PHASE_KEYS` tolerated by
                            validate_annotation but NOT added to the ordering walk — ignored, not
                            enforced. Deleting the single `PHASE_META` entry removes the marker from
                            the palette, the phase rows, the band tiling and `normalizePhases`,
                            because all four are derived; do not hand-edit consumers.
                          T2 VideoPane: `max-h-[34vh]` + **`object-contain`** (without it the cap
                            CROPS instead of letterboxing); frame-step pauses BEFORE seeking and
                            calls `onPlayhead` explicitly (`timeupdate` is throttled and misses
                            sub-100 ms seeks, leaving the chart playhead stale exactly when
                            precision matters); playbackRate applied in an effect AND
                            `onLoadedMetadata`, because a new `src` resets it to 1.
                          T3 page.js: `max-w-7xl`; `placeStrokeMark(t)` extracted so the
                            swim-window guard exists ONCE and cannot drift from the 57-01 server
                            rule; arrows step frames with nothing selected / nudge with something
                            selected, `preventDefault()` LOAD-BEARING (a focused `<video controls>`
                            seeks ±5 s on those keys in Chrome); Escape deselects; `M` marks at the
                            playhead and deliberately does NOT select the new mark, or the
                            step-mark-step loop breaks on its second iteration.
                          ⚠ NOTHING RECOMPUTES — the distinguishing property vs 57-01.
                            `annotation_to_overrides` only ever read dive/stroke/finish. If a metric
                            moves during apply, STOP and report; do not adjust a threshold.
                          ⚠ api.py deliberately UNTOUCHED — :857 rebuilds `phases` from PHASE_KEYS,
                            so the endpoint follows the contract change with no edit. Keeps this plan
                            off the Railway critical path.
                          ⚠ patch_07 comments naming Breakout are LEFT ALONE — rewriting the
                            comments of an APPLIED migration falsifies history.
                          ⚠ END-ANCHOR IS OUT (→ future 58-03): the D8 option the user declined was
                            the one bundling it. Until 58-03, every record-with-video session still
                            needs the Video Overlay tap on the phone or it arrives at origin_s = 0.
                          ⚠ CHECKPOINT NEEDS A SESSION WITH VIDEO — per 57-02's close, NONE of the
                            19 have one; only the 2026-07-20 session does. Use 2026-08-06 tripod
                            footage if it exists, else VideoPane's "Attach video" input.
                          ⭐ Checkpoint is also the first real chance to close **57-02's R1**, still
                            formally UNKNOWN — whether arm entries are placeable from footage. The
                            SUMMARY is required to record the answer; 57-02's could not.
                          Plan: 58-video-ground-truth/58-02-PLAN.md. DO NOT APPLY until user says so.]
```

## Loop Position (58-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [58-01 CLOSED 2026-08-07 — SUMMARY written (58-01-SUMMARY.md).
                          ⚠⚠ **CHECKPOINT APPROVED ON ASSUMPTION, NOT ON DEVICE EVIDENCE.** User:
                            "assume 58-01 is working. approve it." NO on-device verification was
                            reported. Every AC rests on static evidence (export, grep, extracted-
                            function testing) plus that approval. THREE THINGS REMAIN GENUINELY
                            UNVERIFIED:
                              1. Auto-stop has NEVER fired against real hardware. A too-early stop
                                 is the one failure mode here that DESTROYS data rather than
                                 annoying — it loses the end of the swim.
                              2. The checkpoint doubled as CONTEXT-R1's legibility test (film one
                                 25 from three tripod positions). Not reported. **R1 IS NOW
                                 UNANSWERED ACROSS THREE CONSECUTIVE CHECKPOINTS** — 57-02, 58-02,
                                 58-01. It gates Phase 53 Track A4 and 16-06.
                              3. `video_origin_s` still needs the Video Overlay tap until 58-04.
                          ⚠ MOBILE REPO ONLY (`swimnetics-mobile`, separate, user-owned git).
                            NOT part of the myswimcoach push. 7 files changed there, uncommitted.
                          Prior detail: APPLIED 2026-08-05 — all 3 auto tasks done, **PAUSED AT THE
                          human-verify CHECKPOINT** (iOS behavior on a hardware flow; neither
                          export nor grep can judge it).
                          VERIFIED SO FAR: `npx expo export --platform ios` exit 0, **1076 modules**
                          (was 1075 — the one new module is autoStopPrefs.js); `git status` in
                          swimnetics-mobile shows EXACTLY the 3 planned files; `git status` in
                          myswimcoach shows NO new changes from this plan (the web/blog entries and
                          57-02-SUMMARY.md predate it / come from the other environment).
                          `clampAutoStopS` was extracted and run through node: 999→300, -5→0, 0→0,
                          20→20, 2→5, "30"→30, "abc"/null/undefined→0, 300.7→300.
                          ⚠ DEVIATION (1, and it was a real latent bug): **the plan said 4 cleanup
                          sites; there are 5.** `reset()` (RecordScreen.js:626) also clears
                          `elapsedTimerRef` and was missed at plan time. It is the WORST one to miss:
                          reset() sets `isStoppingRef.current = false`, so a surviving deadline would
                          pass the double-stop guard and fire a real STOP + retrieval into an
                          abandoned session. Now cleared there too — parity is 5/5, asserted by grep
                          count. The plan's RULE ("every place that stops the elapsed tick must also
                          disarm this") was right; only its COUNT was wrong.
                          IMPLEMENTATION NOTE beyond the plan: the config field keeps the raw text in
                          `autoStopText` and commits on blur/submit, not per keystroke. Without that,
                          typing "20" passes through "2" → clamped up to the 5 s floor mid-typing, and
                          an empty field reads as 0 → silently switches auto-stop OFF. The clamp
                          itself is unchanged; this is purely about when it is applied.
                          Countdown renders in BOTH record states (plain :746, video :702).
                          ⚠ SCOPE ADDED BY USER AT THE CHECKPOINT (2026-08-05) — 3 more files,
                          explicitly authorized, and it CROSSES 58-01's "DO NOT CHANGE
                          VideoOverlayScreen.js" boundary by direction. Trigger: user reported "I
                          can't view video on mobile."
                          ROOT CAUSE FOUND (two, the second worse than the first):
                            (a) `video: { aspectRatio: 3/4 }` (VideoOverlayScreen.js:207) is a
                                WIDTH-locked box. Portrait 9:16 footage in it is ~693pt tall on a
                                390pt screen — it buries the 170pt chart. FIX: `flex: 1` instead,
                                so the video takes what the fixed rows below leave and
                                contentFit="contain" pillarboxes inside. No hardcoded aspect →
                                adapts to any screen or clip shape. User directed "assume portrait"
                                and "keep video separate from trace + playhead" (i.e. NOT the
                                HUD-overlay option) — stacked flex regions satisfy both.
                            (b) **Video was viewable in exactly ONE place, once.** VideoOverlay is
                                reachable only from RecordScreen.js:936 (the just-recorded results
                                state) and hard-gates on a LOCAL `videoUri`; nothing on mobile calls
                                `/sessions/{id}/video-url`; `expo-media-library` was not a
                                dependency, so the clip never reached the camera roll. Navigate away
                                → that footage is unviewable on the phone forever. Compounds with
                                the sync gap, since that same screen is the only thing that POSTs
                                `video_origin_s`. FIX: NEW dep `expo-media-library ~56.0.10` +
                                `saveVideoToLibrary()` called after recordAsync resolves.
                                Write-only grant (`requestPermissionsAsync(true)`) → needs only
                                NSPhotoLibraryAddUsageDescription, not full-library read. Every
                                failure path swallowed — a denied library permission must never cost
                                a session.
                          ⚠ Info.plist edited DIRECTLY, and expo-doctor confirms that was the only
                            working path: "native project folders but also native configuration
                            properties in app.json … EAS Build will not sync: scheme, orientation,
                            userInterfaceStyle, ios, **plugins**, android." Adding the plugin to
                            app.json would have been INERT. (Matches the standing bare-workflow note.)
                          ⚠ expo-doctor: 4 packages out of date — expo 56.0.12 vs ~56.0.18,
                            expo-audio, expo-dev-client, react-native-screens 4.25.2 vs ~4.26.0.
                            **PRE-EXISTING, NOT introduced here** (expo-media-library installed AT
                            the SDK-matched version). This exact combination is what the Phase-55
                            build shipped and it was verified on device 2026-08-05. RECOMMENDED
                            AGAINST running `expo install --check` before this build: upgrading 4
                            packages the night before a pool session is a bigger risk than a
                            device-proven skew, and SDK-56 version skew is precisely the failure that
                            builds clean then dyld-crashes at launch.
                          `npx expo export --platform ios` exit 0, bundle 3.2MB → 3.3MB
                          (expo-media-library). 7 files now changed in the mobile repo, not 3.
                          NOT committed (user runs git).
                          Original plan record follows.
                          58-01 created 2026-08-05 — iOS auto-stop, default 20 s. MOBILE REPO
                          ONLY (new src/lib/autoStopPrefs.js + RecordingConfigScreen.js +
                          RecordScreen.js). 3 tasks + 1 human-verify checkpoint; autonomous:false,
                          depends_on []. Nothing in myswimcoach/ is touched — that is an explicit
                          boundary and a verification item.
                          KEY DESIGN POINTS: armed immediately after `writeCmd('START')` resolves
                          (the blare) at the two sites where `elapsedTimerRef` already starts, so
                          countdown and deadline share one clock — arming in `beginPlain` /
                          `startVideoRecording` would fold in the race sequence's deliberately
                          RANDOM hold; fires the correct stop per path via a new `stopPlainRef`
                          mirroring the existing `stopVideoRef` (both stop callbacks are defined
                          AFTER their start functions, so neither is in scope at arm time);
                          cleared at all four sites that already clear `elapsedTimerRef`;
                          0 = disabled, so AC-6 falls out of the same `autoStopS > 0` guard and no
                          second SecureStore key is needed; route-param default is 0 so any caller
                          that omits it — including a stale never-unmounted params object on that
                          tab screen — behaves exactly as today.
                          CHECKPOINT DOUBLES AS THE R1 LEGIBILITY TEST (no encoder/BLE/app needed)
                          and carries the standing reminder that Video Overlay must be opened once
                          per video session or `video_origin_s` never posts.
                          Awaiting approval.]
```

**Prior focus: Phase 57 (Annotation Workflow — annotate-tool v2)** — discussed 2026-08-05 via
  /paul:discuss; CONTEXT.md written, NOT yet planned.
  TRIGGER: **19 trustworthy sessions collected 2026-08-05** — 10 freestyle, 4 breaststroke, 4 fly,
  1 backstroke. First corpus postdating the 2026-06-22 encoder-integrity fixes (every CSV in `raw/`
  predates them; user trusts 2-3 of 43). Blocking input to Phase 53 Track A4 and Phase 16-06.
  ⚠ THE REQUEST'S FRAMING WAS PARTLY WRONG, verified in code before answering:
    • Trailing trim ALREADY works — `finish_s`→`swim_end_idx` (annotations.py:158 → metrics.py:439)
      already truncates the analysis window. Missing is FEEDBACK, not mechanism: the chart still
      renders the full 39 s so the swim occupies half the width at ~18 px/s.
    • Non-overlap is ALREADY guaranteed — validate_annotation enforces non-decreasing marker order
      (annotations.py:222-229), so the five markers ARE contiguous half-open intervals. The UI just
      never says so: "Dive 1.31 s" reads as a duration, not a start time.
  REAL HOLES FOUND: stroke marks are NOT constrained to the swim window (annotations.py:190-192
    deliberately skips the check; annotation_to_overrides pairs every consecutive mark regardless →
    a stray mark in the dead tail becomes a garbage cycle feeding stroke_rate_spm + mean_dps_m);
    `stroke_start_s` and the first mark are seeded to coincide then drift with nothing relinking
    them; only 3 of 5 markers reach the metrics (`initial_phase` carried over from the AUTO result
    at api.py:896, so marking UW kick + Breakout moves no number); `v95` (metrics.py:431) is
    computed over the FULL trace, so a dead tail biases the dead-spot threshold on EVERY session;
    one entry point only (sessions/[id]/page.js:188), no queue, no undo, no drag-to-move.
  DECISIONS (user, 2026-08-05, AskUserQuestion ×4 rounds):
    • D1 view-fit chart + full-trace toggle, and the swim window becomes AUTHORITATIVE —
      out-of-window marks REJECTED, v95 windowed. Stored profiles NEVER truncated.
    • D2 the v95 fix is PIPELINE-WIDE, not annotation-only (two definitions of v95 in one codebase
      is exactly the split that produced the Phase-52 drift). ACCEPTED: dead_spot_s +
      coast_fraction shift on every session from here on → CLAUDE.md note + test re-baseline.
    • D3 ONE MARK PER ARM ENTRY everywhere; cycles derived by PAIRING. Factor is physiology, not a
      user choice: free/back = 2 marks/cycle, fly/breast = 1. stroke_rate_spm stays cycles/min.
      Derived from `stroke_type`, NOT stored — NO patch_10, no user-applied SQL. ⚠ stroke_type is
      NOT patchable, so a wrong value is unfixable via the API → the UI must show the derived
      pairing ("Freestyle → 2 marks/cycle · 18 marks → 9 cycles") so it is visible, not silent.
    • D4 reaction time: RECORD dive_start_s, caption it a LOWER BOUND, ship NO metric.
    • D5 UW kick + Breakout stay ground-truth-only (16-06 export) and the UI says so.
    • D6 **NO PRELOADED MARKS — the editor starts blank.** User: "in annotation, it should not have
      any preloaded." Stronger than the option offered and methodologically right: seeding ground
      truth from the segmenter 16-06 exists to evaluate is circular and anchors the annotator toward
      the very errors being hunted. Supersedes Phase-47's auto-seed (page.js:67
      `annRes.annotation ?? annRes.seed`). api.py keeps RETURNING `seed`; the page stops applying it.
    • D7 no auto-assist (no peak-picker, no even-spacing fill). • D8 batch queue + prev/next IN scope.
  REACTION TIME — verified in the mobile + firmware source, NOT assumed: `useStartSequence.run()`
    resolves AT the blare and `startRecording()` writes BLE START after it (RecordScreen.js:454), so
    t=0 IS cue-anchored, and the user confirms the sequence was enabled on all 19. BUT two latencies
    sit between blare and first buffered sample: the `await writeCmd('START')` round trip, and the
    firmware's warmup discard of **150-300 ms, VARIABLE** — it exits on a stability condition, not a
    fixed delay (ESP_32_V5.ino:383-392; the comment at :144 names the race-start blare explicitly).
    Block reaction time is ~0.6-0.8 s → dive_start_s understates it 25-50%, differently each trial,
    and renders as a plausible-looking number. Same silent-corruption shape as Phases 51/52. NO
    firmware change can retroactively fix the 19 already collected. Hence D4.
  ⚠ ACCEPTED RISK (offered alternatives, user declined both): D3+D6+D7+no-video compound to ~500
    hand-placed marks — ~40 per freestyle session, from the velocity trace alone, where each cycle
    shows ~2 peaks that CANNOT be attributed to a specific arm without footage. Per-session
    convention and per-cycle-only were both offered. Mitigation the plan MUST carry: the marks
    record ALTERNATION TIMING, not verified arm identity, and the UI must say that rather than imply
    ground truth. Precision affordances (zoom, undo, drag-to-move, keyboard nudge, live
    marks→cycles readout) are load-bearing, not polish.
  OUT OF SCOPE: firmware META warmup-duration reporting; any reaction_time_s metric or calibration
    constant; recomputing initial_phase from human marks; iOS; destructive profile truncation;
    left/right arm IDENTITY labelling; multi-length/turn support.
  Context: .paul/phases/57-annotation-workflow/CONTEXT.md.
  **57-01 PLAN created 2026-08-05 — backend contract + pipeline, awaiting approval (autonomous:true,
  depends_on []).** Deliberately FIRST: if the web rebuild shipped ahead of it, annotations created
  against the old contract would have to be redone. 3 tasks:
    T1 annotations.py — `MARKS_PER_CYCLE = {"freestyle":2,"backstroke":2}` + `marks_per_cycle()`
      (everything else, incl. `im`/`udk`/unknown/None → 1 = today's behavior);
      `annotation_to_overrides` gains `stroke_type=None` as an optional 4th param, boundaries become
      `marks[0::k]`, and **finish is appended as a boundary ONLY when k==1**. That exception is
      load-bearing, not an oversight: at k=1 a mark is a cycle start and the wall legitimately closes
      the last cycle (byte-identical to today); at k=2 a boundary is a SAME-SIDE arm entry and
      finish_s is a wall touch, so appending it would manufacture a half-populated cycle that skews
      stroke_rate_spm — the exact silent-plausible-corruption class this phase removes.
      validate_annotation gains out-of-window rejection (mark < stroke_start_s or > finish_s, each
      side independent, either may be null).
      REDUCED FROM CONTEXT: the separate "relink stroke_start_s to the first mark" mechanism is NOT
      built. Rejecting marks before stroke_start_s already guarantees marks[0] >= stroke_start_s,
      which is the only genuine overlap; a remaining GAP is real and legal → 57-02 shows it as a
      non-blocking hint. build_seed UNTOUCHED (D6 changes who applies it, not what it is).
    T2 metrics.py — v95 over the swim window at TWO sites. :431 must MOVE (it currently sits ABOVE
      detect_phases, so b_end/swim_end don't exist yet) to after the manual-override block, computing
      over vel[b_end:swim_end]; verified its only consumer in that function is :517. :373
      extract_cycle_peaks recomputes over the cycle-span union — that one drives arm/kick peak
      DETECTION via _PEAK_HEIGHT_FRAC/_PEAK_MIN_PROM_FRAC, so it is not cosmetic. :86 (dead
      segment_cycles_trough) and :286 (already windowed) LEFT ALONE. Empty/NaN window → full-trace
      fallback, never raise. Before/after deltas measured on 2-3 raw/ CSVs; a CHANGED CYCLE COUNT is
      a stop-and-report condition. CLAUDE.md records the comparability break (D2's accepted cost).
      Checked: no existing test asserts on dead_spot_s or a computed coast_fraction → expect zero
      forced re-baselines.
    T3 api.py — widen BOTH annotation `.select()`s to include stroke_type (GET :793, PUT :842). This
      is the Phase-52 lesson restated: an un-widened select makes the fallback hide the fix. PUT
      passes stroke_type into annotation_to_overrides; GET returns `marks_per_cycle` so the pairing
      rule is never duplicated in JS; PUT returns `cycles_derived` so a wrong stroke_type is visible
      immediately — it is NOT patchable, so a wrong value cannot be corrected through the API and
      would otherwise silently halve a stroke rate.
  FOLLOW-ON PLANS (not yet written): 57-02 = annotate page v2 (blank start per D6, window-fit chart +
    full-trace toggle, explicit interval display, lower-bound reaction-time caption, undo/drag/nudge,
    live marks→cycles readout); 57-03 = queue page + prev/next (D8).
  Plan: 57-annotation-workflow/57-01-PLAN.md. DO NOT APPLY until user says so.

**PHASE 55 ✅ COMPLETE (1/1 plans) 2026-08-05** — transition run. SUMMARY written, PROJECT.md evolved
  (the "breaststroke only for V1" constraint relaxed; freestyle unlock recorded as shipped-but-
  unvalidated), ROADMAP marked complete. Checkpoint approved on the EAS build.
  ONE KNOWN GAP carried forward, user-directed (note only, not fixed): deleting the CURRENTLY
  SELECTED athlete clears them from the dropdown but leaves them in the selection bar. `athlete`
  state is independent of `athletes`; the focus refetch updates the list and never revalidates the
  selection. Beyond cosmetic — recording against that stale selection would submit a deleted
  `athlete_id` (fails at /process or orphans the session). One-line fix specified in 55-01-SUMMARY.md.
  ALSO CLEARED BY THIS BUILD: 54-01's last outstanding piece (freestyle analytics verified on device)
  plus six long-deferred iOS checks (47-03, 41, 42, 44-03, 21-02, 34-01).

**NEXT ACTION — two loops still open, both already SHIPPED and only owed their SUMMARYs:**
  • 52-01 (sample-rate contract) — pushed `89205ca`, UNIFY ◐, SUMMARY owed. Two checkpoint items were
    never verified (annotate-page duration + recompute plausibility on a post-migration session).
  • 51-02 (athletes → team_id) — pushed `dedac17`, AC-1 verified live, SUMMARY owed. AC-3 (team-wide
    coach chat) and AC-4 (/billing/status athlete_count) still unverified — and note the coach-chat
    wrong-athlete defect below, which surfaced while exercising exactly that path.
  • 54-01 — its human-verify checkpoint is now effectively satisfied; needs UNIFY + SUMMARY too.

**Prior focus detail — Phase 55 (Athlete Flow Fixes — mobile)** — 55-01, autonomous:false.
  MOBILE REPO ONLY; nothing in myswimcoach/ was touched.
  ROOT INSIGHT tying all three items together: `RecordingConfig` is a TAB screen (RootTabs.js:29),
  so it mounts once per app launch and never remounts. Every defect follows from that —
  `useEffect(...,[])` runs once ever (frozen roster), `useState()` initializers run once ever
  (params ignored), and it lives under `Tabs` not Root (unreachable by name from a Root screen).
  B1 roster frozen at launch in BOTH directions — a new athlete is missing AND a deleted athlete
    persists until restart. Originally reported as add-only; delete case found the same day, same
    cause, one fix. Fix = `useFocusEffect`, the pattern the 3 sibling tab screens already use.
  B2 Record button on AthleteDetail is a silent no-op. TWO halves, and the plan-time investigation
    found the second one: (a) `navigate('RecordingConfig')` from a Root-stack screen only bubbles UP,
    never down into a child navigator → dropped unhandled; needs
    `navigate('Tabs', {screen, params})`. (b) EVEN THEN the params would be ignored —
    RecordingConfigScreen.js:29-34 reads them in `useState` INITIALIZERS, which never re-run on a
    screen that never remounts. Fixing only (a) would land the coach on an empty picker. Also
    forces AC-3: params on a never-unmounting screen persist forever, so they must be cleared after
    use or a later plain tab press silently inherits the previous athlete.
    Head-waist resolved from the roster row, NOT passed as a param — AthleteDetail's `hw` is a
    possibly-mid-edit TextInput string.
  B3 folded in by user decision: freestyle still blocked ON THE PHONE ONLY. Not a bug —
    ratings.py's threshold fallback went live in dedac17, but 54-01's `isAnalyticsReady = true` is
    uncommitted in the mobile tree and has never been built (mobile HEAD 1296494 still has the
    breaststroke-only gate at ReportCardScreen.js:169). Plan VERIFIES it, does not re-edit it.
  3 tasks + 1 human-verify checkpoint. Checkpoint deliberately BATCHES the six iOS checks deferred
  from 54-01/47-03/41/42/44-03/21-02/34-01 — it is a paid build, so clear the backlog in one pass.
  OUT OF SCOPE (user decisions): delete-athlete UX unchanged (it works; user simply never noticed
  the `⋯` glyph — the Team list lacking a delete affordance while sessions have swipe-to-delete, and
  athlete delete writing direct via supabase-js rather than the API, are recorded in CONTEXT.md for
  later); no dev-time guard for unhandled navigate() calls (offered, declined); no coach-chat work.
  Plan: 55-athlete-flow-fixes/55-01-PLAN.md. Context: same dir, CONTEXT.md.

**Phase 51 (API Correctness) — 51-02 SHIPPED 2026-08-05.** Applied (Tasks 0/1/3; Task 2 struck as
  superseded by 54-01), then **committed + pushed by the user as `dedac17` "Scope athletes by
  team_id (Phase 51-02)"** → Railway auto-deployed. The phantom `athletes.coach_id` is GONE — four
  sites scoped by `team_id`, two coach-row selects widened. Suite 176 green; schema_contract → **no
  violations** (was 4).
  ✓ AC-1 VERIFIED LIVE: user added an athlete successfully. The endpoint that had been 500ing since
    before 2026-07-30 now works.
  ○ AC-3 (team-wide coach chat) + AC-4 (`/billing/status` athlete_count) NOT reported — still
    unverified. See the coach-chat defect in Open Threads: team tools now function, but
    athlete-specific questions answer about the wrong athlete.
  ⚠ `dedac17` also carried 54-01's BACKEND half (`ratings.py` threshold fallback + dropped
    `provisional` gate, `tests/test_ratings.py`) — they could not be split from the same commit.
    Consequence: the freestyle unlock is LIVE server-side, and the team dashboard needs-attention
    list (inert since Phase 37) is now populating. 54-01's own loop is still open at its checkpoint;
    its remaining piece is the mobile one-liner, now folded into 55-01.
  SUMMARY still owed at UNIFY. Details: Loop Position (51-02) below.

**Prior focus: Phase 52 (Sample-Rate Contract)** — 52-01 PLAN created 2026-08-03, awaiting
  approval (autonomous:false). Fixes API-AUDIT findings F2+F3. DEFECT: `run_pipeline` decimates by
  an INTEGER factor (round(268.5/100)=3 → 89.5 Hz), the requested 100 Hz is never achieved, and
  api.py:143 DISCARDS the returned `actual_fs`. Six consumers then assume 100: annotations.py
  (build_seed ×3 + annotation_to_overrides), api.py 783/813/**844 (the recompute time axis)**/397
  (export), and THREE web files that build `i / 100` time axes (annotate page:150, sessions
  page:83, VelocityChart:46 cycle overlay — web reads sessions directly via supabase-js).
  Real impact TODAY: 47.1 s swim displays as 42.2 s; recompute-from-annotation shifts every
  time-derived metric ~11.7%.
  APPROACH — user decision 2026-08-03, Option A: **persist the real rate as
  `sessions.sample_rate_hz`** (nullable DOUBLE PRECISION, patch_09, user-applied). Fixes the class
  not the instance; survives firmware/device changes.
  KEY SAFETY PROPERTY: **NULL falls back to 100**, so un-backfilled rows behave byte-identically to
  today — no mid-flight shift, no backend/web drift. No DEFAULT on the column (a default of 100
  would erase the distinction 52-02's backfill needs).
  TWO PRECISIONS bounding the fix (re-verified, not carried over): (1) stored cycle indices are NOT
  corrupted — the time→index round-trip uses the same wrong constant both ways, so marks land on
  the clicked sample; do NOT "repair" them. (2) original auto metrics are correct —
  compute_session_metrics runs on the true t_dec clock inside /process; damage is confined to
  sessions RECOMPUTED from an annotation.
  5 tasks + 2 checkpoints: T1 patch_09 → CHECKPOINT:human-action (user applies SQL) → T2 persist on
  /process + seed_demo_team → T3 backend readers (annotations.py gains `fs_hz=FS_HZ` params;
  api.py `_session_fs(row)` helper; **every session .select() feeding those paths must be widened
  or the fallback silently hides the fix**) → T4 web readers → T5 CLAUDE.md → CHECKPOINT:human-verify.
  SCOPE LIMITS: NO backfill of existing rows (that's 52-02 — and how many sessions carry
  recomputed/corrupted metrics is still UNKNOWN, needs the data read whose SQL is in API-AUDIT.md);
  NO iOS (ReportCardScreen.js:168 exports at i/100 — separate repo, EAS build); CompareChart.js
  left alone (two sessions may have two rates — design question); NO Phase-51 fixes ride along even
  though both touch api.py — keep the diffs separable.
  ORDERING: lands BEFORE 50-02, whose annotation propagation across ~144 demo sessions would
  otherwise bake the 11.7% error in.
  Plan: 52-sample-rate-contract/52-01-PLAN.md. DO NOT APPLY until user says so.

**Prior focus: Phase 51 (API Correctness & Audit)** — 51-02 (the fixes) still awaiting approval;
  51-01 (audit) complete. Sequenced AFTER 52-01 per the audit's own assessment that F2+F3 are more
  serious than F1 (silent plausible-looking corruption vs. a loud 500). ACCEPTED COST: POST
  /athletes keeps 500ing until 51-02 lands. — 51-01 + 51-02 PLANS created 2026-07-30,
  awaiting approval. LIVE BUG (still unfixed): `POST /athletes` 500s with PGRST204 "Could not find
  the 'coach_id' column of 'athletes'". This is NOT the Phase-48 bug — that fix is deployed and
  working; reaching a PostgREST error proves the request now gets past Python. ROOT CAUSE: the live
  `athletes` table has NO `coach_id` column (verified 2026-07-30 by introspecting PostgREST's
  OpenAPI doc with the .env service key), yet api.py references it at FOUR sites:
    • api.py:1298 POST /athletes insert    → hard 500 (the blocker)
    • api.py:1277 POST /athletes limit count → raises → `except: count=0` → athlete limits have
      NEVER been enforced (free-tier cap silently inert)
    • api.py:1517 /coach/chat _load_roster_rows → raises + deliberately propagates → team-wide
      chat questions broken since Phase 33-02
    • api.py:1784 GET /billing/status → raises → `except: pass` → athlete_count always 0
  api.py:513-515 ALREADY documents that athletes has no coach_id and must be scoped by team_id —
  the file contradicts itself. FIX (51-01): scope athletes by team_id at all four sites (+ widen
  two coach-row selects that don't currently fetch team_id — CHECKED); commit
  tools/introspect_schema.py + supabase/live_schema.json; add an AST-based schema-contract test
  (regex was tried and produced ~2 false positives per true hit — response-dict keys; use ast).
  DO NOT run patch_04_backfill.sql — its premise "documents migrations ALREADY APPLIED" is proven
  false twice (device_id, coach_id) and L51 holds a DROP TABLE devices inside a failed-premise guard.
  ORDER REVISED 2026-07-30 by user: AUDIT FIRST, then fixes.
    • 51-01 ✅ COMPLETE 2026-07-30 — audit run, SUMMARY written. Delivered API-AUDIT.md (11 ranked
      findings + 24-endpoint inventory w/ callers + per-table ownership rule),
      tools/introspect_schema.py, supabase/live_schema.json (7 tables/67 cols — FIRST authoritative
      schema record in the repo), tools/schema_contract.py (AST extractor; 4 violations, 0 false
      positives; self-checked against injected bad columns AND response-dict literals — the regex
      failure mode). api.py UNTOUCHED; suite still 149. NEW FINDINGS BEYOND THE KNOWN LIST:
        - F3: api.py:143 DISCARDS `_actual_fs` and `sessions` has no rate column → the true sample
          rate is destroyed at write time, so F2 isn't just a wrong constant. Escalates F2.
        - F5 confirmed hard: api.py reads `teams` ZERO times; only iOS AthletesScreen.js:46 reads
          teams.swimmer_limit while api.py enforces coaches.athlete_limit → app displays a different
          column than the API enforces.
        - F6: 7 of 11 coach lookups mask DB failures as 403; the CORRECT hardened pattern already
          exists at the other 4 (Phase-36) and was never propagated.
        - F2 precision: segmentation is NOT corrupted — the time→index round-trip uses the same wrong
          constant both ways, so marks land on the clicked sample. Only time interpretation is wrong.
      ASSESSMENT: F2+F3 are likely MORE serious than F1 (silent, plausible-looking corruption vs a
      loud 500) and should precede 50-02, whose design propagates annotations across ~144 sessions.
      COVERAGE GAP (honest): "how many stored sessions carry recomputed metrics" needs a DATA read,
      outside the approved read-only-catalog scope — exact SQL recorded in API-AUDIT.md.
    • 51-02 = the FIXES (four sites → team_id, athlete-limit switch, promote the extractor into a
      permanent test). depends_on 51-01; Task 0 triages the audit findings before touching code.
      autonomous:false, human-verify.
  ATHLETE LIMIT — user decision 2026-07-30: DISABLE for now, keep trivially re-enablable. Mechanism =
  ENFORCE_ATHLETE_LIMIT env var read at module level, DEFAULT OFF; when off the count query is
  skipped entirely. Existing `if limit is not None` (NULL = unlimited) stays nested inside. Documented
  in CLAUDE.md. NOTE the limit has never actually fired in production (the count query always threw
  into `except: count=0`), so switching it off changes nothing observable — it only stops the fix
  from turning on a guard nobody asked for. This also REMOVES the earlier lockout risk.
  ACCEPTED COST of audit-first: POST /athletes keeps 500ing until 51-02 lands — coaches still cannot
  add athletes in the meantime. Explicit user decision.
  Scope/delivery/test-gap decided by user via AskUserQuestion ×4 (2026-07-30): live introspection YES,
  api.py + schema contract, audit-before-fix, and fix the conftest MagicMock blind spot.
  Plans: 51-api-correctness/51-01-PLAN.md + 51-02-PLAN.md. DO NOT APPLY until user says so.

**NEW FOCUS: Phase 53 (Attention Allocation)** — discussed 2026-08-03 via /paul:discuss; CONTEXT.md
  written, NOT yet planned. PRODUCT REFRAME (user): the tool is not a magnifying glass for combing
  through detail — "no one wants to find a needle in a haystack." A head coach cannot track 30
  swimmers across a 2-hour practice daily (~90 s of analytical attention per athlete per week), so
  the core value is ALERTING when something goes wrong OR RIGHT. Detail view stays as the landing
  place after an alert, demoted from core value.
  LAYER CONTRACT: measurement gate → contrast (vs what reference) → persistence (run rules, never a
  single-point delta) → co-occurrence (what moved together) → synthesis. HARD BOUNDARY: stop at
  co-occurrence — no causal claims, no drill prescription.
  TECHNICAL FRAMING: statistical process control, NOT classic anomaly detection. LLMs belong in the
  synthesis/phrasing layer ONLY, never detection; detection must be deterministic and the alert
  payload complete without any model call (template fallback mandatory).
  REPO-VERIFIED STARTING CONDITIONS: (1) the existing attention surface is INERT — metrics.py:617
  sets segmentation_reliable=bool(manual_bounds), which makes every pillar provisional
  (ratings.py:176), which summarize_team skips (ratings.py:298) → needs_attention can only emit
  `stale`/`never_tested`; it has been a calendar reminder since Phase 37. (2) ratings._trend is ±5%
  vs ONE prior session — no noise model, no persistence. (3) σ has never been measured for any
  metric. (4) the fs bug may not be a constant error (hypothesis, unmeasured).
  DECISIONS (user, 2026-08-03, AskUserQuestion ×4 rounds): weekly test cadence; <2 min/athlete
  end-to-end → 30 swimmers in ~1 h, so HARDWARE THROUGHPUT IS NOT THE CONSTRAINT and is off the
  critical path; demo-credible first then true, explicitly separated; whole-system scope but NO cull
  list (note conflicting features — drills.py/recommend_drills/ratings.THRESHOLDS — do not delete);
  ~10 sessions × 1-2 swimmers, ONE SINGLE DAY, user-collected, with INJECTED perturbations
  (deliberately slower / extra breaths) as a positive control rather than waiting for natural signal;
  FREESTYLE (user override of the breaststroke recommendation — freestyle restriction must lift);
  demo runs on the REAL series, not the Phase-50 synthetic team; user operates on site; hardware
  readiness UNKNOWN → roadmap opens with a verification gate.
  ROADMAP: Track A (blocking) A1 hardware gate (flash 44-03, stationary trial, counts match) → A2
  sample-rate contract (= the empty Phase-52 dir; TOUCHES api.py, must sequence after 51-02) → A3
  collect → A4 annotate all 10 via the Phase-47 tool (~1 h; yields segmentation_reliable=True +
  recomputed metrics + 16-06 ground truth in one pass) → A5 saturation + repeatability analysis =
  THE GO/NO-GO (does the freestyle ridge rail at the 120-SPM ceiling? which of the 18 metrics have
  usable variance? → evidence-based cull list). Track B engine (pure, deterministic, symmetric;
  report sensitivity AND specificity). Track C surface (90-second artifact + LLM phrasing layer).
  Track D later-for-truth (weekly spacing ≥8 weeks, 16-06 tuning, pilot team).
  DISTANCE: demo-credible ≈ Tracks A-C, gated on one pool day + 1 h annotation — weeks, not months,
  IF A1 passes. Actually-true adds 8-10 weeks of calendar that cannot start until Track A is done.
  SUPERSEDES: the Phase-48 batch item 3 "freestyle unlock" (port breaststroke THRESHOLDS to all
  strokes, drop provisional, flip isAnalyticsReady) is the WRONG unlock — within-athlete contrast
  needs no thresholds at all, so the reframe makes freestyle CHEAPER. What freestyle needs is a
  REPEATABLE (not accurate) segmenter; a consistently-biased one still detects drift. EXCEPTION:
  ceiling-railing is saturation, not bias — a railed metric has zero variance and can never show
  drift; A5 must check for it.
  COLLECTION DECISIONS (user, 2026-08-03): baseline block = **10+ trials** (still below the ~20-point
  SPC convention, so limits will be wide — but computable, which 6 was not); effort **deliberately
  submaximal**, so fatigue is ruled out by design and 10+ consecutive trials are viable. Consequence
  to keep in view: the series measures repeatability at controlled effort, not competitive
  performance variance. If monotonic drift appears anyway it is UNMODELLED — investigate, do not
  explain away.
  GITIGNORE: `/.paul` un-ignored 2026-08-03 (needed BOTH `!/.paul` and `!/.paul/**/*.md` — the
  repo-wide `*.md` rule at .gitignore:16 would otherwise swallow every file inside). 188 files now
  visible to git. Motivation: STATE.md/ROADMAP.md were being edited concurrently from two
  environments with zero conflict protection.
  Context: .paul/phases/53-attention-allocation/CONTEXT.md.
  53-01 PLAN created 2026-08-03 — **the instrument before the experiment**. Builds the Track-A5
  analyzer + the pool-day protocol; requires NO collected data. 3 tasks: (T1) NEW repeatability.py
  pure module + tests/test_repeatability.py — SPC individuals noise floor (sigma_mr =
  mean(moving_range)/1.128, chosen over plain SD because it is insensitive to the slow drift we
  later want to DETECT), minimum detectable change (3·sigma), saturation check with rails DERIVED
  from metrics._PERIOD_MIN_S/_MAX_S (15/120 SPM today, never hardcoded), usability ranking with an
  explicit caveat that low CV = repeatable ≠ discriminative, and zero-variance flagged as SUSPECT
  not perfect; tests recover a KNOWN injected sigma within tolerance so the tool is trustworthy
  before it ever sees real data. (T2) NEW tools/analyze_repeatability.py — offline CLI mirroring
  seed_demo_team.py:271-272; captures `actual_fs` from run_pipeline (the value api.py discards), so
  it answers Phase 52's "does fs vary session to session?" for free WITHOUT touching any file Phase
  52 owns. (T3) NEW COLLECTION-PROTOCOL.md — pool-day checklist, A1 hardware gate as a BLOCKING
  precondition. autonomous:true. depends_on [] — genuinely none; reading actual_fs directly makes it
  independent of Phase 52. BOUNDARIES: api.py / tools/introspect_schema.py / tools/schema_contract.py
  / supabase/ / tests/test_api.py all UNTOUCHED (Phase 51+52 concurrent in another env). SCOPE LIMITS:
  no detection engine (Track B), no perturbation scoring, no surface, no new deps, no data collection.
  Plan: 53-attention-allocation/53-01-PLAN.md. Awaiting approval.

**NEW: Phase 54 (Gate Removal)** — 54-01 PLAN created 2026-08-03, awaiting approval.
  TRIGGER: user hit the free-tier `device_limit`=1 while trying to run a test 2026-08-03 and believed
  it had already been removed. It had not — what was decided on 2026-07-30 was the ATHLETE limit
  (`ENFORCE_ATHLETE_LIMIT`, 51-02), a different limit, and that has not landed either (`grep ENFORCE_
  api.py` = 0 hits). Device limit is Phase 15 / 15-02 territory.
  WHY IT FIRED WHEN THE ATHLETE LIMIT NEVER DID: `devices.coach_id` is a real uuid column (verified in
  supabase/live_schema.json) so the device count query works and the guard triggers; `athletes.coach_id`
  is the phantom column, so that count always threw into `except: count=0`. Trigger condition is a NEW
  chip_id only (api.py:242) — chip id comes from the eFuse MAC (ESP_32_V5.ino:655) and survives
  reflash, so this means a DIFFERENT board than the registered one.
  URGENT SECOND FINDING: free-tier `monthly_session_limit`=20 (api.py:1348, enforced :215) would 402
  PARTWAY THROUGH the Phase-53 pool day — 10+ baseline trials plus warm-ups plus perturbation pairs
  ≈ 14-16 uploads, on top of anything already used this month. That would waste a collection session
  costing hardware, pool time and a swimmer.
  VERIFIED SURFACE: exactly THREE 402 sites (session :233, device :267, athlete :1311). Every other
  non-2xx in api.py is auth/ownership and must stay. `subscription_status` is only ever written and
  read back — it gates nothing. Web has NO stroke gate (already unrestricted); the stroke gate is
  ratings.py:176 + mobile ReportCardScreen.js:192 only.
  DECISIONS (user, 2026-08-03, AskUserQuestion ×2 rounds): ONE env kill switch `ENFORCE_TIER_LIMITS`
  default OFF (not deletion, not DB-NULL — the Stripe webhook would repopulate NULLed columns);
  SUPERSEDE 51-02's `ENFORCE_ATHLETE_LIMIT` with the single switch, depends_on 51-02; backend scope
  PLUS the mobile stroke gate; stroke unlock goes DEEP — thresholds fall back to breaststroke for all
  strokes AND `(not seg_reliable)` drops out of `provisional`.
  ⚠ ACCEPTED CONSEQUENCE (user informed, chose it anyway): the "thresholds only" option would have been
  a NO-OP — provisional stays True via the seg_reliable condition, which is False for every
  auto-segmented session. Dropping that condition is what makes the unlock visible, and it also
  un-gates `summarize_team` — the team dashboard needs-attention list, INERT since Phase 37, will now
  POPULATE, driven by breaststroke-derived bands applied to all strokes over segmentation flagged
  unreliable (16-04: 3/8 breaststroke sessions within ±5 SPM). Phase 53 decides whether those bands
  should exist at all; this plan only makes them visible.
  Plan: 54-gate-removal/54-01-PLAN.md. autonomous:false. Awaiting approval.

54-01 APPLIED 2026-08-03 — all 3 tasks done, suite 172 passed, paused at the human-verify checkpoint.
  T1 (api.py): NEW module-level `ENFORCE_TIER_LIMITS` (os.getenv default "0", truthy 1/true/yes) at
    api.py:26 next to the other config. Three gates: `if coach and ENFORCE_TIER_LIMITS:` wraps BOTH
    /process limits (session + device) in one edit since they share that block; `if
    ENFORCE_TIER_LIMITS and limit is not None:` on POST /athletes. Count queries now never run when
    off. Verified: default False, `ENFORCE_TIER_LIMITS=1` → True, `_TIER_LIMITS` byte-identical,
    ENFORCE_ATHLETE_LIMIT count = 0.
  T2 (ratings.py + 2 test files): `thr_table = THRESHOLDS.get(stroke) or THRESHOLDS["breaststroke"]`
    (fallback, not copied keys — keeps "borrowed" visible); `provisional` dropped `(not
    seg_reliable)`. `seg_reliable` param + read KEPT so the gate is one line to restore. Docstring
    rewritten (it asserted the opposite of both changes). Verified: freestyle now returns
    speed band=ok score=50 provisional=False, stroke_length band=good score=71.
  T3 (mobile ReportCardScreen.js:192): `isAnalyticsReady = true` with restore instructions; all 6
    usage sites + the dead "Coming Soon" branch retained. `strokeType` still used at :424 → not
    orphaned. `npx expo export --platform ios` exit 0 (1075 modules, 3.2MB).
  DEVIATION: a THIRD contradicted assertion existed beyond the two the plan named —
    tests/test_api.py:878 `assert speed["provisional"] is True  # segmentation unreliable`. Inverted
    to False. It was missed at plan time because the grep for `segmentation_reliable` only surfaced
    that file's fixture setup lines, not the assertion. tests/test_api.py is contended with 51-02 —
    the change is one line, clearly commented.
  ⚠ 51-02 NOT LANDED at apply time (`grep ENFORCE_ api.py` = 0) → depends_on relaxed to []. ACTION
    OWED IN THE OTHER ENV: drop 51-02's athlete-limit task before applying it, or it will re-add
    ENFORCE_ATHLETE_LIMIT and double-gate the block this plan already wrapped. 51-02's REAL fix (four
    phantom `athletes.coach_id` sites → team_id) is untouched by this plan and still needed.
  DECISION RECORDED: `segmentation_reliable` NOT flipped to default-True and NOT renamed. It is a
    provenance fact (metrics.py:617 = `bool(manual_bounds)`, "did a human draw these boundaries?"),
    not a reliability assessment — flipping it would record something false and destroy the marker
    distinguishing Phase 53's 10 hand-annotated sessions from auto ones. After T2 NOTHING reads it
    (web: 0 refs; the mobile "Segmentation is experimental" caption is a hardcoded string), so it is
    now inert metadata. Rename to `segmentation_source: "auto"|"human"` DEFERRED to Phase 53's
    measurement layer, which is the consumer that will define the vocabulary; doing it now means
    naming against an unwritten contract plus a stored-`metrics_json` migration.
  NOT committed (user runs git). REMAINING: push api.py + ratings.py → Railway, then the checkpoint.

## Loop Position (57-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [57-02 CLOSED 2026-08-05 — SUMMARY written (57-02-SUMMARY.md).
                          **CHECKPOINT APPROVED** by the user on the deployed portal. All 7 ACs pass.
                          ⚠ PHASE 57 IS **2 of 3** PLANS, NOT COMPLETE — the mechanical
                          "PLAN count == SUMMARY count" rule (2 and 2) would fire a phase transition
                          again; do NOT. 57-03 (queue + prev/next) is in ROADMAP and still owed.
                          ⚠ R1 STILL UNANSWERED — the plan asked the SUMMARY to record whether ~40
                          arm-entry marks are genuinely placeable from the velocity trace alone. The
                          checkpoint was approved without a report on that point, so it is recorded
                          as UNKNOWN, not settled. 57-03's queue design must not assume the answer;
                          annotating one real freestyle session end to end is what resolves it.
                          57-02 APPLIED 2026-08-05 — all 3 auto tasks done, then the checkpoint.
                          VERIFIED SO FAR: `npm run build` exit 0 (18 routes, /app/annotate/[id]
                          compiles); dev server serves the route 200 then correctly redirects to
                          /login; zero console errors, zero compile errors; `pytest tests/ -q` still
                          236 (proves no backend file was touched); `git status` shows EXACTLY the 3
                          planned web files.
                          ⭐ RISKIEST PIECE VERIFIED WITHOUT AUTH: the editor's `deriveCycles`
                          mirrors annotation_to_overrides, and a drift there would make the readout
                          LIE about what the server builds. Extracted the SHIPPED function (not a
                          reimplementation) into an .mjs, ran 10 cases through node, ran the same 10
                          through Python → **[2,4,1,4,0,0,0,3,1,3] both sides, exact match**,
                          including k=2-with-finish-beyond-last-mark (1 cycle, NOT appended), the
                          k=1 twin (4 cycles, appended), empty marks, and a sub-2-sample pair both
                          sides filter.
                          DEVIATION (1, found while wiring T3): the plan said selection is "set by
                          clicking an existing mark", but recharts fires onClick AFTER mouseup, so a
                          select-click would ALSO place a new mark on top of the one being targeted.
                          Fix: the chart sets suppressClickRef on any mousedown that HITS a mark, so
                          a press on an existing mark selects/drags and never places. Renamed from
                          didDragRef — it now covers the zero-movement case too.
                          ALSO: 57-01 was committed as `71d7012` and **PUSHED TO PRODUCTION
                          2026-08-05** (dedac17..71d7012 → Railway auto-deploy) at user direction.
                          WHY IT HAD TO GO FIRST: web/.env.local points the dev server at the
                          PRODUCTION Railway API, so a pre-57-01 backend returns no
                          `marks_per_cycle`; the page falls back to `?? 1` and a freestyle session
                          would read "18 marks → 17 cycles" instead of 9 — and PUT would build 17
                          server-side too. Testing against the old API would have verified the exact
                          bug this phase exists to prevent.
                          I recommended running the API locally and pushing only after the
                          checkpoint passed (prod then carries a contract nobody has exercised);
                          user chose to push first. Their call, recorded.
                          Backward-compatible, so the still-deployed OLD Vercel page is unaffected:
                          new optional 4th arg, new response keys, k=1 path byte-identical. The only
                          behavior change for existing clients is the intended 422 on out-of-window
                          marks.
                          **57-02 ALSO COMMITTED + DEPLOYED 2026-08-05 at user direction, BEFORE
                          the checkpoint ran** — `16c1d92` (web) + `de35c0d` (tooling/firmware),
                          pushed 71d7012..de35c0d → Vercel + Railway. I flagged twice that the
                          checkpoint is the gate and that this ships a page nobody has opened in a
                          browser; user chose to deploy anyway. Their call. Revert is one commit if
                          the checkpoint finds problems. **THE CHECKPOINT IS STILL OPEN** —
                          deploying verified nothing; it only moved where verification happens.
                          `de35c0d` also finally commits the long-flagged "untracked, only copy"
                          files: ESP_32_V5.ino warmup work, tools/introspect_schema.py +
                          schema_contract.py, supabase/live_schema.json, patch_06,
                          as5600_diagnostic/, assets/, .mcp.json, .gitignore. None deploy anywhere.
                          ⚠ DELIBERATELY HELD BACK from "commit and deploy everything": the BLOG —
                          `web/app/blog/`, `web/lib/blog.js` (7 posts) and the Footer/Nav links,
                          which are purely blog entry points. Committing those PUBLISHES founder-
                          journal posts to the public marketing site. That is outward-facing
                          publication, not internal tooling, and it was not part of anything asked
                          for in this session — so it needs an explicit yes rather than being swept
                          in. Phase 46 built it; it has never been committed. `.mcp.json` was
                          checked for credentials before committing (clean — shadcn npx only).
                          NOTE: no unauthenticated way exists to confirm the new code is live —
                          checkpoint step 5 doubles as the deploy check (a freestyle readout of N/2
                          proves `marks_per_cycle` arrived; N-1 means the deploy has not landed).
                          Original plan record follows.
                          57-02 created 2026-08-05 — annotate page v2. WEB ONLY (3 files):
                          page.js + AnnotationChart.js + AnnotationEditor.js. 3 tasks + 1
                          human-verify checkpoint (it is a UI — pytest cannot judge it).
                          autonomous:false, depends_on ["57-01"] (consumes marks_per_cycle,
                          cycles_derived, and the 422 error shape).
                          T1 chart — fit the view by SLICING THE DATA, not via XAxis domain: the
                            existing <Brush> also controls the domain and the two fight. Slicing
                            also re-spreads MAX_POINTS decimation over the shorter span, which is
                            where the precision win comes from. ReferenceArea bands between
                            consecutive markers make "phases tile, never overlap" VISIBLE rather
                            than asserted. Drag = nearest-mark grab within 1% of the visible span,
                            with cursor:grab so the affordance is discoverable.
                          T2 editor — phases rendered as INTERVALS (start → next marker + duration),
                            unplaced visibly ≠ placed; a persistent tag on each row saying whether
                            it moves a number (UW kick + Breakout do NOT — api.py:896 carries
                            initial_phase over from the auto result); Dive captioned as a LOWER
                            BOUND (170-400 ms of BLE + warmup latency, D4, no metric); live
                            "N marks → M cycles" derived EXACTLY as annotation_to_overrides does,
                            including the k==1-only finish-append — a readout that disagrees with
                            what the server will build is worse than none. "Reset to auto" REMOVED
                            (under D6 it contradicts the whole point) → "Undo" + "Discard saved
                            annotation".
                          T3 page — blank start (`annRes.annotation` only, seed still read but never
                            applied); viewRange lower bound is **0, never stroke_start** — the
                            leading region IS the reaction-time measurement; undo stack in a REF not
                            state (snapshotting into state would re-render the chart on every one of
                            ~500 clicks); arrow-key nudge by 1 sample / shift by 10; client-side
                            out-of-window guard mirroring 57-01's server rule; DELETE wiring for the
                            20:24 discard; cycles_derived surfaced in the saved message so a wrong
                            (unpatchable) stroke_type shows up.
                          BLANK-START CONSEQUENCE worth knowing: with no marks there is no finish_s,
                            so the chart opens on the FULL trace and auto-fits once Finish is placed.
                          BOUNDARY: annotations.py / metrics.py / api.py are OFF LIMITS — if this
                            plan seems to need a backend change, STOP and report. VideoPane also off
                            limits (zero video on the 19 → no way to verify a change).
                          Plan: 57-annotation-workflow/57-02-PLAN.md. DO NOT APPLY until user says so.]
```

## Loop Position (57-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [57-01 CLOSED 2026-08-05 — SUMMARY written (57-01-SUMMARY.md). All 5 ACs
                          PASS. ⚠ PHASE 57 IS **1 of 3** PLANS, NOT COMPLETE — the mechanical
                          "PLAN count == SUMMARY count" rule would call this the last plan and fire
                          a phase transition; do NOT. 57-02 (annotate page v2) and 57-03 (queue +
                          prev/next) are recorded in ROADMAP and still owed. No phase transition,
                          no PROJECT.md evolution, no phase commit yet.
                          57-01 APPLIED 2026-08-05 — all 3 tasks done, suite 176 → 236 (+60), zero
                          failures, NO existing assertion re-baselined.
                          T1 annotations.py — MARKS_PER_CYCLE {"freestyle":2,"backstroke":2} +
                            marks_per_cycle(); annotation_to_overrides gained stroke_type=None (4th,
                            optional → both existing callers unchanged); boundaries = marks[0::k];
                            finish appended only at k==1. validate_annotation rejects marks outside
                            [stroke_start_s, finish_s], each bound independent, malformed bound →
                            unenforced (the bad value already raised its own error). Its docstring
                            had asserted the OPPOSITE ("stroke marks are not required to sit inside
                            the stroke phase span") — rewritten, not left to rot.
                            MUTATION-TESTED: dropping the `k == 1` guard on the finish-append failed
                            2 tests (finish_closes_… and too_few_marks_to_pair); reverted, green.
                          T2 metrics.py — NEW _window_v95(vel, start, end) helper; empty window →
                            full-trace fallback. compute_session_metrics: v95 MOVED from above
                            detect_phases to after the manual-override block, now over
                            vel[b_end:swim_end]. extract_cycle_peaks: over the cycle span.
                            :103 (dead segment_cycles_trough) + :303 (already windowed) untouched.
                            The ":541 global threshold" comment was contradicted by the change —
                            rewritten.
                          T3 api.py — BOTH annotation selects widened with stroke_type (:794 GET,
                            :847 PUT); PUT passes it into annotation_to_overrides; GET returns
                            marks_per_cycle; PUT returns marks_per_cycle + cycles_derived.
                          ⚠ MEASURED — THE PLAN'S CLAIM WAS PARTLY WRONG, corrected in CLAUDE.md
                            rather than propagated: **coast_fraction does NOT shift.** It is scaled
                            by each cycle's own arm_peak_vel (metrics.py:521), never by v95. Only
                            dead_spot_s and the peak-prominence DETECTION floor depend on v95.
                            PLAN/CONTEXT/ROADMAP all said coast_fraction would move; they were wrong.
                          MEASUREMENT (tools in scratchpad, not committed): the raw/ corpus has a
                            0-5% post-swim tail so it barely exercises the change — v95 +1.5-2%,
                            dead_spot +0.0-0.6%. Re-run with a 45% tail appended (matching the
                            2026-08-05 sessions): **v95 +6.4% (carlos_fr_1) to +12.2% (leo1)**,
                            dead_spot_total_s +1.6% to +3.7%. CYCLE COUNTS UNCHANGED on every file
                            and every tail length → the plan's stop-and-report condition never fired.
                          DEVIATION (1, deliberate): the new endpoint tests went to
                            tests/test_annotations.py, not tests/test_api.py as the plan said —
                            that is where the annotation-endpoint fixtures (_annot_admin, AUTH,
                            SESSION_ROW) actually live. tests/test_api.py UNTOUCHED.
                          REDUCED FROM PLAN (recorded at plan time, held): no separate
                            "relink stroke_start_s to first mark" mechanism — window rejection
                            already guarantees marks[0] >= stroke_start_s, the only real overlap.
                          ✓ RESOLVED 2026-08-05 by a read-only Supabase query (user-authorized).
                            stroke_type is correct on all 19 (user entered them). FOUR further
                            findings, all bearing on 57-02:
                            (a) sample_rate_hz = **89.9928** on all 23 post-Phase-52 rows, NOT NULL
                                and NOT 100 → **Phase 52 is confirmed working in production**, which
                                its own AC-2/AC-3 never verified. The 19 will annotate on the right
                                clock. (7 older rows are NULL → 100 Hz fallback, as designed.)
                                Footnote: CLAUDE.md's illustrative "~89.5 Hz (268.5/3)" is from an
                                older trace; the live device reports ~269.98/3 = 89.993. The point
                                (never 100) stands; not worth churning the doc.
                            (b) **THE 19-BATCH IS THE CONTIGUOUS BLOCK 19:50:50 → 20:59:25** — that
                                window contains exactly 10 fr / 4 br / 4 fly / 1 back. But there are
                                THREE MORE 2026-08-05 uploads BEFORE it (14:31 fr, 18:22 br,
                                18:24 fr), so a queue filtered on "sessions from 2026-08-05" would
                                sweep in 22 and contaminate the Phase-53 repeatability series.
                                57-03's queue must not use a date filter alone.
                            (c) **ZERO video on any of the 19** (the only video in the last 30 rows
                                is a 2026-07-20 session). R1's "no video" is ABSOLUTE for this
                                batch, not "only a few" — every arm entry is inferred from the trace.
                            (d) **All 30 rows have name = None.** A queue that lists sessions by
                                timestamp alone will be miserable to navigate across 19 items;
                                57-03 needs athlete + stroke + index, or naming on arrival.
                          ⚠ ONE OF THE 19 IS ALREADY ANNOTATED UNDER THE OLD CONVENTION:
                            2026-08-05T20:24:03 freestyle, 11 marks, saved 20:28 (before this
                            phase). Its marks are all INSIDE the window, so 57-01's rejection does
                            not touch it — but they were placed when 1 mark = 1 cycle, and freestyle
                            now PAIRS. Re-saving it would reinterpret 11 marks as 5 cycles instead
                            of 10, and its stored metrics_json was already recomputed at the old
                            reading. **DECIDED (user, 2026-08-05): RE-ANNOTATE IT FROM SCRATCH.**
                            57-02 must DELETE that annotation first — DELETE /annotations restores
                            metrics_json from metrics_json_auto, and that backup exists because the
                            47-04 recompute ran — then it gets marked again under the arm-entry
                            convention like the other 18. NO migration path and NO convention-
                            mismatch warning are built: after the delete, no old-convention
                            annotation remains in the batch. Rationale: one session, and its 11
                            marks came off a wavelet seed that D6 already rejects as ground truth.
                            The other 2 annotated rows are older sessions outside the
                            batch (both rate=NULL → 100 Hz fallback, i.e. ~11% mis-timed; that is
                            Phase 52-02 territory, and they are 16-06 ground truth).
                          NOT committed (user runs git). Web untouched by this plan (the Footer/Nav/
                          blog entries in git status predate this session).
                          Original plan record follows.
                          57-01 created 2026-08-05 — annotation contract + pipeline. Makes the
                          annotated swim window authoritative (out-of-window marks rejected, v95
                          windowed pipeline-wide) and teaches the contract that one mark is one ARM
                          ENTRY (free/back pair into cycles; fly/breast do not). 3 tasks, no
                          checkpoint — every AC is pytest-verifiable. autonomous:true, depends_on [].
                          SAFE-DEFAULT PROPERTY (AC-3): the k=1 / unknown-stroke path is byte-
                          identical to today, the same NULL-means-legacy discipline Phase 52 used
                          for sample_rate_hz. BLAST RADIUS TO WATCH: T2's v95 change is
                          pipeline-wide by user decision (D2) — dead_spot_s, coast_fraction and the
                          peak-detection thresholds shift on every session computed from here on,
                          so old and new numbers stop being comparable.
                          Plan: 57-annotation-workflow/57-01-PLAN.md]
```

## Loop Position (55-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [55-01 CLOSED 2026-08-05 — SUMMARY written. Checkpoint approved on the EAS
                          build: AC-2/AC-3/AC-4 pass, AC-1 partial (one deferred gap, user-directed).
                          Phase 55 = 1/1 plans complete. Detail below.
                          55-01 APPLIED 2026-08-05 — all 3 tasks done, `npx expo export --platform
                          ios` exit 0 (3.2MB bundle). PAUSED at the human-verify checkpoint,
                          which needs the EAS build.
                          T1 RecordingConfigScreen.js — mount-only roster `useEffect` → `useFocusEffect`
                            + `useCallback` (stable deps; without it, refetch loops). NEW params
                            effect keyed on [athleteId, athletes]: resolves the athlete from the
                            fetched roster row (falls back to params before the fetch resolves), sets
                            strokeType when it is a known STROKES key, then CLEARS the consumed params
                            via navigation.setParams(undefined ×3). The clear is what stops a later
                            plain Record-tab press inheriting the previous athlete (AC-3) — a problem
                            created BY applying params post-mount, so it is our own cleanup.
                            The `getStartSequenceEnabled` mount-only effect deliberately left alone
                            (device pref, not roster data).
                          T2 AthleteDetailScreen.js:140 — `navigate('RecordingConfig', p)` →
                            `navigate('Tabs', {screen:'RecordingConfig', params:p})`. Same three param
                            names kept. headWaistM deliberately NOT passed — T1 reads head_waist_m
                            from the roster row instead of this screen's `hw`, a possibly-mid-edit
                            TextInput string. RootTabs.js:21 comment rewritten: it had asserted
                            cross-screen navigation "keeps working", which is true only between tab
                            siblings and became false for AthleteDetail at Phase 38-03. New comment
                            states the Root→Tab nested rule, that getting it wrong fails SILENTLY,
                            and that tab screens never remount (params in an effect, not a useState
                            initializer; useFocusEffect, not mount).
                          T3 ReportCardScreen.js VERIFIED ONLY, not re-edited — `isAnalyticsReady =
                            true` at :195, all 6 usage sites + the `!isAnalyticsReady` branch at :421
                            retained, so 54-01's gate stays a one-line revert.
                          VERIFIED: export exit 0; zero bare `navigate('RecordingConfig')` in code
                            (remaining grep hits are both explanatory comments); zero `[]`-dep
                            useEffect performing a roster read; useFocusEffect imported + wired.
                          NO DEVIATIONS from the plan.
                          ⚠ BUILD-SCOPE NOTE: the mobile repo has 13 modified + 7 untracked paths —
                            this plan's 4 files plus ALL the deferred iOS work (47-03 videoUploadQueue
                            /UploadToast, startSequencePrefs, deviceStatus, friendlyError, hooks/,
                            RecordScreen, VideoOverlay, BleContext, package.json). `.easignore` exists
                            and excludes only build artifacts, so EAS most likely uploads the working
                            directory rather than a git archive — but COMMIT ANYWAY: several of these
                            are the only copy, and committing removes all doubt about what ships.
                          CHECKPOINT APPROVED 2026-08-05 on the EAS build. AC-1 add ✓, AC-2 ✓,
                          AC-3 ✓ (the never-before-executed path — verified working), AC-4 freestyle
                          analytics ✓ on device. AC-1 delete PARTIAL — see the known gap below.
                          ⚠ KNOWN GAP, user said NOTE ONLY / do not fix now (found at the checkpoint):
                            deleting the CURRENTLY SELECTED athlete removes them from the dropdown but
                            leaves them displayed in the selection bar. CAUSE: `athlete` (the selected
                            one) is state independent of `athletes` (the list); the new useFocusEffect
                            refetches the LIST only and never revalidates the selection against it, so
                            a stale selected object survives. The picker is correct — only the
                            selection display is stale. CONSEQUENCE IF ACTED ON: recording could be
                            started against a deleted athlete_id, which would fail at /process or
                            orphan the session. FIX (one line, inside the existing focus effect):
                            after setAthletes(rows), if `athlete?.id` is absent from rows then
                            `setAthlete(null)`. Deliberately NOT applied — outside the approved plan.
                          Plan: 55-athlete-flow-fixes/55-01-PLAN.md]
```

## Loop Position (51-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [51-02 CLOSED 2026-08-05 — SUMMARY written. ⚠ That SUMMARY was authored by
                          a CONCURRENT SESSION at 11:49, not by this one (file mtime post-dates this
                          session's last STATE write at 11:43). Content reviewed and found accurate.
                          See the concurrency warning in Open Threads.
                          PHASE 51 COMPLETE (2/2 plans).
                          AC-1 + AC-2 + AC-5 pass. AC-3 (team-wide coach chat) and AC-4
                          (/billing/status athlete_count) remain UNVERIFIED — and exercising AC-3 is
                          what surfaced the coach-chat wrong-athlete defect (ROADMAP row 56).
                          Detail below.
                          51-02 APPLY 2026-08-05 — Tasks 0/1/3 done, suite 176 green (was 172,
                          +4 new). PAUSED at Task 4 human-verify (needs Railway deploy).
                          PLAN AMENDED BEFORE APPLY: Task 2 (ENFORCE_ATHLETE_LIMIT) STRUCK as
                          superseded by 54-01's ENFORCE_TIER_LIMITS (api.py:34, already wrapping
                          the athlete block at :1308) — two switches on one guard. CLAUDE.md
                          dropped from files_modified (Task 2 was its only edit). All plan line
                          numbers re-resolved; 52-01 + 54-01 had shifted them ~35-40 lines.
                          T1 (api.py) — six sites, `athletes` now scoped by team_id:
                            • :1335 insert — "coach_id" key removed (THE live 500)
                            • :1311 limit count — coach_id → team_id
                            • :1430 chat coach lookup — select("id") → select("id, team_id"),
                              NEW coach_team_id captured alongside coach_row_id
                            • :1551 _load_roster_rows — coach_id → coach_team_id
                            • :1807 billing _get_coach_row — team_id added to the field list
                            • :1818 billing athlete count — coach_id → team_id
                          ORPHAN REMOVED: `coach_id = coach["id"]` in create_athlete became unused
                          once both its readers changed. sessions/devices/reports coach_id scoping
                          untouched everywhere (verified).
                          TWO COMMENTS FIXED (they asserted the opposite after the change): the
                          "scoped to the coach's whole roster (coach_id)" header above the team
                          executors, and a new note on the athletes query explaining the split.
                          T3 (tests/test_api.py) — NEW TestSchemaContract, 4 tests: api.py vs
                          supabase/live_schema.json via tools.schema_contract.find_violations (AST,
                          imported as a namespace package — conftest already puts the repo root on
                          sys.path), plus 3 extractor self-checks (bad eq, bad insert payload,
                          and the regex-era false-positive case: response dicts + select("*")).
                          MUTATION-TESTED: reintroduced coach_id on the athletes count chain →
                          test failed with `api.py:1310 athletes.coach_id [eq]`; reverted, green.
                          DEVIATION (contradicted test, inverted not deleted):
                          tests/test_api.py:668 asserted "Both roster queries filtered by coach_id"
                          — that WAS the bug. Now asserts athletes→team_id AND that no athletes
                          query carries coach_id at all; sessions→coach_id assertion kept. The
                          _team_admin fixture gained a team_id="team-1" param and returns it on the
                          coaches row (without it the roster query would filter on None).
                          T0 triage of API-AUDIT.md's 11 findings:
                            • F1 → fixed here. F2+F3 → closed by Phase 52 (52-01 shipped 89205ca).
                            • F4 (limits fail open) → athlete half now moot (54-01 turned all three
                              off; count query no longer runs). Session/device fail-open → own plan.
                            • F5 (teams.swimmer_limit displayed vs coaches.athlete_limit enforced)
                              → RECOMMEND coaches authoritative (api.py is the enforcement point,
                              billing lives there); teams.coach_limit has no coaches equivalent so
                              the merge isn't mechanical. iOS out of scope → own plan. USER CALL.
                            • F6 (7/11 coach lookups mask DB errors as 403) → own plan; F8
                              (_get_coach_row inlined 11×) → own plan, would fix F6 in the same pass.
                            • F9 (GET /export has no caller) → KEPT for now; 52-01 just updated it
                              for sample_rate_hz. Keep-or-delete is a USER CALL, not done here.
                            • F7, F10, F11 → accept-and-document.
                          NOT committed (user runs git). REMAINING: push api.py + tests/test_api.py
                          → Railway, then the checkpoint (add an athlete; team-wide chat question;
                          /billing/status athlete_count non-zero).
                          Plan: 51-api-correctness/51-02-PLAN.md]
```

## Loop Position (54-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [54-01 CLOSED 2026-08-05 — SUMMARY written. PHASE 54 COMPLETE (1/1 plans).
                          Checkpoint satisfied in two parts: the backend half deployed in `dedac17`
                          (it could not be split from 51-02's commit), and the MOBILE half — which
                          sat uncommitted and unbuilt for two days, so freestyle still looked blocked
                          on the phone — was folded into Phase 55-01 and VERIFIED ON DEVICE
                          2026-08-05. That two-day gap between "green in the tree" and "actually
                          running" is the Phase-48 lesson repeating in miniature.
                          Original apply record follows.
                          54-01 APPLY: T1+T2+T3 done 2026-08-03, suite 172 green, expo export exit 0.
                          Was PAUSED at human-verify checkpoint — needed Railway deploy.
                          Was: ENFORCE_TIER_LIMITS kill switch (default OFF,
                          all 3 limits, supersedes ENFORCE_ATHLETE_LIMIT) + ratings.py stroke unlock
                          + mobile isAnalyticsReady→true. Billing infra PRESERVED. 3 tasks + 1
                          human-verify checkpoint (post-Railway-deploy: re-upload from the blocked
                          board, add an athlete, check a freestyle report card, eyeball the now-live
                          needs-attention list). depends_on 51-02. iOS device verify DEFERRED to the
                          pending EAS build. Awaiting approval.
                          Plan: 54-gate-removal/54-01-PLAN.md]
```

## Loop Position (53-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ○        ○     [53-01 created 2026-08-03 — Track-A5 repeatability/saturation analyzer +
                          pool-day collection protocol. NEW repeatability.py (pure) +
                          tools/analyze_repeatability.py (offline CLI) + tests/test_repeatability.py
                          + COLLECTION-PROTOCOL.md. Needs NO collected data. autonomous:true,
                          depends_on []. Awaiting approval.
                          Plan: 53-attention-allocation/53-01-PLAN.md]
```

## Project Reference

See: .paul/PROJECT.md (updated 2026-05-20)

**Core value:** Coaches get objective biomechanical data on every swimmer — no laptop at poolside.
**Prior focus:** Phase 50 (Demo Team & Synthetic History) — ⏸ **PAUSED 2026-08-03** by user decision
  during the Phase-53 product-direction discussion. REASON: the demo now runs on a REAL 10-session
  series (user-collected, one pool day, with injected perturbations), NOT the synthetic 12-athlete
  team. The seeder replays `raw/` CSVs which the user has assessed as untrustworthy — every file in
  `raw/` is dated 2026-05-13→2026-06-10 and predates BOTH encoder-integrity fixes (BLE packet loss +
  warmup transient, 2026-06-22); user trusts 2-3 of 43. 50-01's "24/43 usable" was a STRUCTURAL check
  (parseable, long enough), not a data-integrity judgment. NOT cancelled — if a team-scale demo is
  wanted later, reseed from clean sessions; the seeder is largely agnostic to which CSVs it eats, so
  that is a source swap, not a rewrite. ⚠ seed_demo_team.py (565 lines) is STILL UNTRACKED and the
  only copy — commit it regardless of the pause. Stopped at the T3 human gate (no demo coach email;
  apply env had no network). Do NOT resume without revisiting the source-data question.
  Historical description follows. 50-01 PLAN created 2026-07-27,
  awaiting approval (autonomous:false). Discussed via /paul:discuss same day; CONTEXT.md written.
  PROBLEM: the demo can't show long-term tracking — no history exists, so trend chips, team
  pulse, needs-attention and compare all render empty. APPROACH (decided, not fabrication):
  replay + perturb ~30 REAL raw encoder CSVs in raw/ through the REAL pipeline
  (vae.run_pipeline → m.compute_session_metrics), insert rows shaped exactly like /process's
  session_row with BACKDATED created_at via the service role. Everything downstream (ratings,
  /team/overview, compare, per-cycle, AI chat, annotate) then works with ZERO product code
  changes. KEY COST SAVER: user wanted every session hand-annotated (~144 sessions = 7–14 h of
  clicking); instead hand-annotate ~12 ARCHETYPES (~1 h) and PROPAGATE their marks through the
  seeder's own (invertible) time-warp into all derivatives — exact, since the seeder chose the
  warp. Forces a 2-stage sequence with a human gate: 50-01 = seeder core + Stage-1 archetype
  ingest → USER ANNOTATES 12 → 50-02 = generate ~144 + propagate + tune. DECISIONS (user,
  2026-07-27, AskUserQuestion ×3 rounds): dedicated demo coach acct in LIVE Supabase (RLS-
  isolated); WEB PORTAL only (no iOS, no parent reports); ~12 athletes × ~12 sessions over 6
  months; scripted story beats; **br + fr ONLY** (revised down from user's "all four strokes" —
  raw/ has ZERO backstroke and only 2 usable fly CSVs); upload raw CSVs to Storage (keeps
  annotate-recompute + /export working); config-driven re-runnable (--wipe/--stage1/--validate/
  --dry-run); session names+notes only (no parent fields/device/stars); obviously-demo naming;
  USER signs up the demo acct (no credential handling in script); archetypes KEPT as each
  athlete's earliest session. LANDMINES baked into the plan: created_at MUST be explicit
  (verified — api.py orders by it ×6 and the whole portal sorts on it; recorded_at does NOT
  drive the UI); device_id landmine RESOLVED 2026-07-30 — patch_06 IS applied live (column
  verified TEXT), so the chip-id string is now a legal value and the "must stay NULL / 22P02"
  constraint no longer applies;
  sys.path shim required (local supabase/ folder shadows the package); local _clean for NaN.
  Phase 48 + 45 bugs are BOTH FIXED (48 deployed 2026-07-30; 45 migration live) — no longer
  constraints on the seeder.
  Plan: 50-demo-team-seeding/50-01-PLAN.md.
  STATUS CORRECTED 2026-07-30: 50-01 was APPROVED and PARTIALLY APPLIED (not "awaiting approval").
  T1 seeder core ✅ + T2 roster/timeline ✅ (both verified offline; --validate = 24/43 CSVs usable;
  row shape matches /process + JSON-safe; suite 149) + T4 stage1 CODE written ✅ but NEVER RUN.
  STOPPED AT T3 (human gate): no demo coach email supplied, and the apply env had NO NETWORK
  (DNS to the Supabase host failed) so nothing could reach the DB. NEXT ACTION = sign up the demo
  coach acct, then run `python seed_demo_team.py --coach-email <demo> --stage1` from a networked
  machine; the write paths have never hit a live DB, so expect first-run debugging.
  ⚠ seed_demo_team.py is UNTRACKED and the only copy — commit it.
  ⚠ NEW FINDING (50-01, not fixed — outside plan boundaries): stored velocity_profile is ~89.51 Hz,
  NOT 100 Hz (run_pipeline decimates by an integer factor: 268.5/3). annotations.py FS_HZ=100 and
  api.py's annotation recompute (t_arr = arange(size)/FS_HZ) both assume exactly 100 → the annotate
  page mis-times real sessions (47.1 s shown as 42.2 s) and recompute-from-annotation shifts every
  time-derived metric ~11.7%. Affects REAL sessions today. Candidate phase; should probably land
  BEFORE 50-02, whose annotation propagation sits on that clock.
**Prior focus:** Phase 48 (Athlete-Create Fix) — ✅ APPLIED + DEPLOYED 2026-07-30. Was the LIVE
  BUG: POST /athletes 500s with `'SyncQueryRequestBuilder' object has no attribute 'single'` —
  coaches could not add athletes. ROOT CAUSE (postgrest 2.30.1 introspection): `.insert()`
  returns a SyncQueryRequestBuilder whose `.select()` stays a mutation builder with NO `.single()`
  → AttributeError before any network call. Unpinned `supabase` in requirements.txt → a Railway
  redeploy (likely Phase-47 627419c) pulled a postgrest where this chain is invalid. BLAST RADIUS
  = ONE endpoint (grep-verified: all other `.single()` calls are on SELECT chains and are correct).
  FIX SHIPPED: api.py:1306-1314 drops `.single()` and returns `(resp.data or [None])[0]` with a
  500 on an empty insert; requirements.txt pins supabase==2.30.1 + postgrest==2.30.1;
  tests/test_api.py:1068 regression test asserts the REAL postgrest builder class has no
  `.single()` (MagicMock can't reproduce the AttributeError — conftest's global create_client mock
  is exactly why this reached prod undetected). Suite 149 passed. Committed + pushed 2026-07-30
  → Railway auto-deploy. Backend-only (mobile sends correct payload). Plan:
  48-athlete-create-fix/48-01-PLAN.md.
  LESSON (drove the 2026-07-30 observability discussion): the verified fix sat GREEN AND UNPUSHED
  in the working tree for ~10 days while prod kept 500ing, and STATE still read "awaiting
  approval". No CI ran the tests; no error monitoring reported the live 500s. See the Phase-51
  candidate below.
  NEXT after 48: item 1 = iOS video replay (new "Watch replay" entry point off Session
  History/report card; adapt VideoOverlayScreen to stream signed cloud URL + saved
  video_origin_s); item 2 = BLE auto-reconnect (background reconnect, manual Retrieve — REVERSES
  Phase 42's "no silent auto-reconnect" decision, to be noted explicitly); item 3 = freestyle
  unlock (apply breaststroke THRESHOLDS to all strokes in ratings.py, drop provisional, flip
  ReportCardScreen isAnalyticsReady to always-true — no visual distinction). Each = its own
  later phase, planned in turn.
**⚠ CONCURRENCY WARNING — TWO SESSIONS ARE WRITING THIS REPO** (observed 2026-08-05). This session's
  last STATE write was 11:43:15; `.paul/phases/51-api-correctness/51-02-SUMMARY.md` appeared at
  11:49:24, authored by something else, while this session made no tool calls. Its content was
  reviewed and is accurate — it evidently read the APPLY record this session had written into STATE
  and closed the loop from it. It did NOT update STATE, so STATE and the phase directory had drifted
  apart until this entry.
  This is EXACTLY the hazard that motivated un-ignoring `/.paul` on 2026-08-03 ("STATE.md/ROADMAP.md
  were being edited concurrently from two environments with zero conflict protection"). Git makes the
  drift *visible*; it does not prevent it — nothing here locks.
  RECOMMENDATION: run one PAUL session at a time against this repo, or commit `.paul/` between
  sessions so conflicts surface as merge conflicts rather than silent last-write-wins. Any long
  STATE.md edit is a read-modify-write over a file the other session may have changed underneath.

**OPEN DEFECT — coach chat answers about the WRONG ATHLETE** (found 2026-08-05, user chose
  document-only, NOT scheduled). Asking "give me info on Sid specifically" returned another
  athlete's history under Sid's name — claimed a most-recent swim of Aug 5 when Sid has only two
  swims, both in May (Aug 5 = that day's date, i.e. the anchor athlete's session).
  ROOT CAUSE: `list_athlete_sessions` has NO athlete parameter — its schema is `limit` + `stroke`
  only (coach.py:141-142) — and the executor is bound to the athlete of the session the chat was
  opened from (api.py:1494, `.eq("athlete_id", athlete_id)` closing over the anchor session).
  Naming a different athlete CANNOT re-scope it: the model gets the anchor athlete's rows and
  attributes them to whoever was named. `get_session_metrics` inherits the same anchor scope.
  SEVERITY (my assessment, not the user's): this is cross-athlete data attribution — one swimmer's
  data presented as another's — not just an inaccurate answer.
  NOT caused by 51-02 (that path filters athlete_id + coach_id, untouched). But 51-02 DID repair the
  team tools (rank_athletes / rank_progress / team_summary, broken since 33-02), so the chat now
  answers roster questions confidently, which makes the wrong athlete-specific answers read as more
  authoritative than before.
  FIX DIRECTION (unplanned): either give the athlete tools an athlete_name/athlete_id parameter
  resolved against the coach's roster, or make the system prompt state plainly that athlete tools
  are locked to the anchor session's swimmer so the model declines instead of substituting.

**Other open threads (parallel, not blocking):** Phase 49-01 (SECURITY HARDENING — backend, plan
  created 2026-07-20, awaiting approval; from a full-surface security review: redact error-detail
  leaks + CORS allowlist + upload size caps + athlete-ownership on /process; autonomous:false,
  human-verify), 39-06 (flag abnormal
  sessions, needs design/backend decision), 43-01 (demo-readiness runbook, awaiting approval),
  44-03 (encoder warmup + overlay sync, at device-verify), 26-01 (in-app video overlay, at
  EAS-build checkpoint).
  41/42/44/47-03 iOS deferrals share ONE pending EAS build.
  RESOLVED + removed from this list 2026-07-30: 45-01 (device_id UUID→TEXT — patch_06 IS applied
  live, `information_schema` reports TEXT; iOS cloud saves are no longer blocked by 22P02).
**Prior focus:** Phase 47 (Trial Annotation — review + ground truth) — ✅ COMPLETE & CLOSED
  2026-07-20 (4/4 plans; 47-03 SUMMARY written; PHASE 47 TRANSITION run). 47-03 (iOS video
  auto-upload, LAST plan) REVISED 2026-07-12 per user ("Instagram-style — upload in background,
  don't block the app, out-of-the-way notice when done") + AskUserQuestion ×3: IN-APP TOAST
  (no expo-notifications); FIFO queue one-at-a-time; AUTO-RETRY ×2 w/ backoff then persistent
  dismissible Retry chip. Awaiting approval (autonomous:true — export-green gate; device verify
  DEFERRED to next EAS build, heads-up only). Mobile repo only, 3 tasks: (T1) NEW
  src/lib/videoUploadQueue.js — module singleton FIFO (enqueue/subscribe/retry/dismiss; fresh
  supabase token per attempt; FileSystem.uploadAsync MULTIPART + sessionType BACKGROUND so
  uploads survive screen unmount AND app backgrounding; retries at ~3 s/~10 s; in-memory only,
  no restart persistence) + NEW src/components/UploadToast.js (global transient toast
  "Uploading video…"/"Video saved to cloud ✓" + persistent failed chip above the TabBar w/
  Retry+✕; pointerEvents box-none) mounted once in App.js (root overlay inside
  NavigationContainer — AiBubble is per-screen, not global, so App.js is the mount).
  (T2) RecordScreen: enqueue (non-awaited) after /process success when videoUri+session_id;
  sessionId added to VideoOverlay nav params; no screen-local upload state. (T3)
  VideoOverlayScreen persists video_origin_s = videoOriginS + manualOffsetS via origin-only
  POST (string-only FormData = Hermes-safe) — once when origin known + debounced ~1 s on
  nudge; no sessionId → no calls. .mov stored as {id}.mp4 (playback risk noted, NO transcode).
  Boundaries: BLE/camera/race-start/overlay math/nav structure untouched; no new native deps.
  Plan: 47-trial-annotation/47-03-PLAN.md.
  47-03 APPLIED 2026-07-12 — ALL 3 TASKS DONE, export green ×2 (1075 modules, 3.2MB, exit 0).
  Implementation notes: FileSystem import = 'expo-file-system/legacy' (matches RecordScreen);
  NEW videoUriRef in RecordScreen mirrors videoUri (set at recordAsync resolve, cleared on both
  reset paths) because uploadAndProcess's useCallback deps don't include videoUri (stale-closure
  guard); queue worker = single-flight `working` flag + re-pump on finally; done-jobs pruned
  after 6 s (toast window); toast = dark pill (colors.text bg), failed chip = needsWorkBg/
  needsWork tokens, bottom = insets.bottom+88 (above TabBar pill). UploadToast subscribes with
  prev-status diff so toasts fire on transitions only. NOT committed (mobile repo local-only;
  user runs git). SUMMARY owed at UNIFY → UNIFY runs the PHASE 47 TRANSITION (last plan, 4/4).
  Prior: 47-04 ✅ CLOSED
  2026-07-12 (checkpoint approved: patch_08 applied live + E2E verified; committed + pushed
  627419c → origin/main, Railway+Vercel auto-deploy; suite 148). ANNOTATIONS NOW DRIVE
  METRICS: saving an annotation with ≥2 stroke boundaries recomputes the session through the
  real pipeline — metrics.py compute_session_metrics gained an ADDITIVE `manual` kwarg
  (baseline_end/ip_end/swim_end window overrides + full-trace cycle_bounds that bypass the
  wavelet; segmentation_reliable→True on human bounds; no-manual path proven identical);
  annotations.annotation_to_overrides maps times→indices (idx=round(t*100) clamped;
  swim_end = finish idx+1 EXCLUSIVE; boundaries = marks + finish; consecutive pairs →
  cycles). PUT overwrites metrics_json (once-only backup in NEW sessions.metrics_json_auto —
  patch_08, LIVE), carries dropout/warnings from raw-CSV processing, refreshes cycle counts,
  marks data_quality.recomputed_from_annotation; recompute failure is NON-FATAL
  (recompute_error in response, annotation kept). DELETE /annotations restores metrics_json
  from the backup. NEW GET /annotations/export (coach-scoped ground truth for 16-06) + NEW
  fetch_annotations.py (local dump, fetch_sessions.py pattern). Annotate-page save message
  reports recomputed/too-few-boundaries/error. Deviation: degenerate <2-sample cycle bounds
  are SKIPPED (first clamp coerced them; test caught it). KNOWN QUIRKS (accepted):
  initial_phase carried from auto detection even under manual windows; recomputed sessions
  shift ratings baselines (inherent to overwrite-by-design). PHASE 47 = 3/4 plans CLOSED
  (47-01 contract, 47-02 GUI, 47-04 recompute) — REMAINING: 47-03 (iOS auto-upload video
  after Record-with-Video; endpoint live + web-exercised; needs mobile repo + EAS build
  heads-up). Prior: 47-02 (web annotation
  GUI) ✅ CLOSED 2026-07-12 (checkpoint approved; committed + pushed to main e7f72f4). 47-02 =
  /app/annotate/[id] portal page (dark theme): NEW AnnotationChart (recharts, modeled on
  VelocityChart which is PROTECTED — click via LineChart activeLabel; 5 phase ReferenceLines +
  stroke marks + playhead), AnnotationEditor (tool palette, chip list, dirty state, Save PUT +
  422 inline, Reset-to-auto = seed), VideoPane (signed-URL playback, playhead sync sessionT =
  origin_s + currentTime, Seek tool, ±0.1 s origin nudge persisted via origin-only POST,
  Attach-video upload), lib/api.js additive apiUpload (multipart, NO Content-Type; apiFetch
  untouched — gained err.body for structured 422s), report-card "Annotate ›" link. Build green
  (18 routes). 47-01 ✅ CLOSED (contract locked, patch_07 LIVE; suite 131). Phase 2/4 done; NEXT:
  47-03 iOS video upload or 47-04 recompute + ground-truth export. Phase: review
  recorded trials + hand-mark swim phases (dive → underwater/pulldown → breakout → stroke → finish,
  SINGLE ORDERED PASS) + per-stroke boundaries by clicking the velocity trace with synced video;
  pre-seeded from the auto-segmenter; works velocity-only when no video. Purpose: (a) ground truth
  for 16-06 wavelet tuning, (b) correct auto-segmentation → recompute metrics. Built as an
  ESTABLISHED production API (later exposed to all app users). Video→cloud lands THIS phase
  (resolves the Phase-45 deferred "discuss first"): private `videos` bucket +
  sessions.video_path/video_origin_s (44-03 end-anchor convention); iOS auto-uploads after
  Record-with-Video — user: EAS builds no longer a blocker, heads-up only. 4-plan phase:
  47-01 backend contract (patch_07 + annotations.py pure seed/validate + 5 endpoints + tests) →
  47-02 web GUI /app/annotate/[id] → 47-03 iOS video auto-upload → 47-04 recompute + ground-truth
  export. Decisions (user, 2026-07-11, AskUserQuestion ×7): web-portal GUI; iOS upload in-phase;
  ground-truth + correction; pre-seed-then-edit; single-pass model; recompute in-phase;
  velocity-only must work. Plan: 47-trial-annotation/47-01-PLAN.md.

## Loop Position (52-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [52-01 CLOSED 2026-08-05 — SUMMARY written from the APPLY record below
                          (applied 2026-08-03 in a prior session, not first-hand). PHASE 52 = 1/1
                          plans; 52-02 (measure + backfill) remains a FUTURE plan, not a gap in this
                          one. CARRIED FORWARD UNCLOSED: AC-2 (annotate-page duration on a
                          post-migration session) and AC-3 (recompute plausibility) — both still need
                          a swim recorded after the migration. Original apply record follows.
                          52-01 APPLY COMPLETE 2026-08-03 — all 5 code tasks done, COMMITTED + PUSHED 89205ca "Persist per-session sample rate" → origin/main (Railway + Vercel auto-deploy). patch_09 APPLIED LIVE by user. VERIFIED: suite 170 passed (was 149, +21 new); web build green (18 routes); `import api` clean; tools/schema_contract.py api.py supabase/live_schema.json → exactly 4 violations, ALL the known Phase-51 athletes.coach_id sites, ZERO false positives from the new sample_rate_hz refs.
  CHECKPOINT PARTIALLY VERIFIED — do NOT record this as fully verified:
    ✓ AC-1 live: user confirmed a new session stores sample_rate_hz ≈ 89 (not 100).
    ✓ AC-4 live: a Jun-23 (NULL-rate) session renders EXACTLY as before — axis 0→13.08s,
      lap 13.1 s, 3 cycles. The fallback holds; nothing moved for existing sessions.
    ○ UNVERIFIED (needs a swim recorded AFTER the migration — user has none since):
      annotate-page duration on a NEW session, and recompute-from-annotation plausibility.
      RESUME BY: record one session, open /app/annotate/[id], confirm the chart's last x
      matches the real swim length, save marks, sanity-check stroke_rate_spm.
  CONCRETE 52-02 EXAMPLE from that Jun-23 session: ~1308 samples shown as 13.08 s under the
  100 Hz fallback; at the true ~89.5 Hz the trace is really ~14.6 s. lap_time_s (13.1 s) was
  always correct — it was computed on the true t_dec clock inside /process. This is exactly
  the residual error the 52-02 backfill must repair.
  DEVIATION 1 (ordering): the human-action gate was moved from between T1 and T2 to after all
  code tasks — writing code touches nothing live, so gating it cost a round-trip for no safety.
  DEVIATION 2 (BOUNDARY CROSSING, disclosed): 52-01's boundaries assigned
  supabase/live_schema.json to 51-02, but it was REGENERATED here via tools/introspect_schema.py
  (7 tables, 67→68 cols). Necessary — a snapshot predating the migration would make 51-02's
  contract test fail on correct code — but it did cross a stated line. Still UNTRACKED; user's
  call whether it rides with 51-02 or gets committed separately.
  ALSO COMMITTED IN 89205ca: seed_demo_team.py enters git for the FIRST time (565 lines, was the
  only copy — STATE had flagged it for 2 sessions), and CLAUDE.md carried pre-existing
  uncommitted Phase-47 doc catch-up (annotations.py + test_annotations.py rows, fetch_annotations
  note) that could not be split from the same file's diff.
  NOT MINE, still uncommitted: .gitignore (un-ignores .paul/), ESP_32_V5.ino, Footer.js, Nav.js,
  and untracked .paul/, tools/, supabase/live_schema.json, patch_06, web/app/blog/, web/lib/blog.js.
  SUMMARY still owed at UNIFY. Original plan text below.
  52-01 created 2026-08-03 — SAMPLE-RATE CONTRACT. Persist the true decimated rate as sessions.sample_rate_hz (patch_09, nullable, NO default) and make all 6 backend + 3 web consumers read it instead of assuming 100 Hz. NULL → 100 keeps existing rows byte-identical. 5 tasks + human-action (apply SQL) + human-verify (new session shows ~89.5; annotate page duration correct; recompute plausible; OLD session unchanged). Fixes API-AUDIT F2+F3. No backfill (52-02), no iOS, no Phase-51 fixes. autonomous:false. Awaiting approval. Plan: 52-sample-rate-contract/52-01-PLAN.md]
```

## Loop Position (50-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ◐        ○     ⏸ PAUSED 2026-08-03 (see Phase-50 block above — demo moved to a real
                          10-session series; seeder source CSVs are pre-fix and untrusted).
                          [50-01 created 2026-07-27 — demo-team seeder core + Stage-1 archetype ingest. NEW seed_demo_team.py (config block + service-role client + ingest_csv mirroring /process + wipe + dry-run) + python-dotenv → requirements-dev.txt. 4 tasks: T1 seeder core, T2 archetype validation pass + author DEMO_ROSTER (8 br / 4 fr, story-beat trajectories) + TIMELINE (6-mo window, clustered test weeks), T3 CHECKPOINT:human-action (user signs up the demo coach acct, reports email), T4 run Stage 1 = 12 athletes + 12 archetype sessions backdated to window start. autonomous:false. NO product/schema/web changes. Exit condition = the 12 sessions are annotatable at /app/annotate/[id], which is 50-02's entry gate. Awaiting approval. Plan: 50-demo-team-seeding/50-01-PLAN.md]
```

## Loop Position (49-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ○        ○     [49-01 created 2026-07-20 — SECURITY HARDENING (backend). From a full-surface review: (T1) redact 14 internal-error leaks (str(e) in 500s + /process & annotation bodies) → generic msg + server log + catch-all handler; (T2) CORS ["*"]→ALLOWED_ORIGINS env allowlist + memory-safe upload caps (_read_capped: MAX_CSV_BYTES 10MB /process, MAX_VIDEO_BYTES 200MB /video, +/coach/chat payload cap); (T3) enforce athlete_id∈coach.team_id on /process (cross-tenant write) + 2 regression tests. Verified NON-issues (leave): Stripe webhook sig OK, report tokens UUIDv4, no SQLi/XSS/committed secrets, RLS WITH CHECK present. Deferred w/ rationale: rate limiting, report-token expiry, full requirements.txt pinning. autonomous:false, human-verify (portal+record+add-athlete+video post-deploy w/ ALLOWED_ORIGINS set). Awaiting approval. Plan: 49-security-hardening/49-01-PLAN.md]
```

## Loop Position (48-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [48-01 CLOSED 2026-07-30 — SUMMARY written. APPLIED + DEPLOYED — api.py:1306-1314 drops .single() → (resp.data or [None])[0]; supabase/postgrest==2.30.1 pinned; regression test on the REAL postgrest builder class (tests/test_api.py:1068). Suite 149 passed. Committed + pushed → Railway auto-deploy. REMAINING: human-verify (add an athlete live in the portal), then UNIFY + SUMMARY]
```

## Loop Position (47-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [47-03 CLOSED 2026-07-20 — background upload queue + toast + origin save; export green (re-verified at UNIFY, 1075 modules); SUMMARY written. PHASE 47 COMPLETE (4/4)]
```

## Loop Position (47-04)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [47-04 CLOSED 2026-07-12 — recompute-on-save + export; patch_08 LIVE; suite 148; pushed 627419c; SUMMARY written. Phase 47 = 3/4]
```

## Loop Position (47-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [47-02 CLOSED 2026-07-12 — annotation web GUI; checkpoint approved; committed+pushed e7f72f4; SUMMARY written. Phase 47 = 2/4 plans]
```
47-02 APPLIED + SHIPPED (web): NEW web/app/app/annotate/[id]/page.js (loads session via
  supabase-js + GET /annotations via apiFetch; editor state seeded from annotation ?? seed;
  handleChartClick routes by activeTool — phase/stroke/seek; save PUTs full doc; Reset restores
  seed). NEW web/components/portal/AnnotationChart.js (recharts, NOT the shared VelocityChart
  which report-card/compare depend on; PHASE_META + phaseLabel export, "Pulldown" label on
  breaststroke; click via LineChart onClick activeLabel; 5 colored ReferenceLines + dashed
  stroke marks + amber playhead; Brush zoom kept). NEW
  web/components/portal/AnnotationEditor.js (tool palette incl. disabled Seek until video
  attached, phase rows w/ ✕ clear, mark chip list w/ ✕ + clear-all, Save/Reset buttons, dirty
  indicator, inline 422 error list). NEW web/components/portal/VideoPane.js (no-video state =
  Attach-video file input; video state = signed URL fetched fresh each mount [3600s expiry, never
  persisted], onTimeUpdate → sessionT = origin_s+currentTime, seekRef exposes seekTo for the Seek
  tool, ±0.1s nudge buttons + Save-sync origin-only POST). web/lib/api.js: NEW apiUpload
  (multipart, no Content-Type, same auth flow as apiFetch) + apiFetch gained err.body (structured
  422 {errors:[...]} surfaced to the editor) — apiFetch behavior otherwise unchanged.
  web/app/app/sessions/[id]/page.js: "Annotate ›" link added next to the Simple/Advanced toggle
  (shown even for non-breaststroke sessions). VERIFY: npm run build exit 0 (18 routes,
  /app/annotate/[id] registered dynamic ƒ). CHECKPOINT: user approved 2026-07-12 (seed→edit→
  save→reload, video attach+playhead+seek+sync-nudge, velocity-only path all confirmed).
  COMMITTED + PUSHED 2026-07-12: commit e7f72f4 "Add trial annotation tool (Phase 47, plans
  01-02)" → origin/main (10 files: the 47-01 backend + all 47-02 web files, staged individually
  to exclude unrelated pending Phase 44/45/46 changes — ESP_32_V5.ino, Footer/Nav.js blog links,
  web/lib/blog.js, patch_06, .mcp.json, as5600_diagnostic/ all left untouched/uncommitted).
  DEPLOY: Railway + Vercel auto-deploy from the push. SUMMARY owed at UNIFY.

## Loop Position (47-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [47-01 CLOSED 2026-07-11 — annotation backend contract; patch_07 LIVE; suite 131; SUMMARY written. Phase 47 = 1/4 plans]
```
47-01 APPLIED (backend): NEW supabase/patch_07_annotations.sql (session_annotations table +
  team-scoped RLS via sessions→athletes→current_team_id(); sessions.video_path +
  video_origin_s DOUBLE PRECISION; private `videos` bucket INSERT ON CONFLICT DO NOTHING) —
  USER APPLIED to live DB 2026-07-11. NEW annotations.py (pure: FS_HZ=100, PHASE_KEYS
  canonical order dive/underwater/breakout/stroke/finish — "underwater" displays as
  "pulldown" for breaststroke; build_seed from metrics_json [dive←baseline_end_s,
  underwater←dive peak, stroke_start←initial_phase_end_idx else first cycle, finish←last
  cycle end_idx/100, marks←cycle start_idx/100]; validate_annotation light-touch
  [range/order/sorted-marks/unknown-key/source]). api.py: NEW _owned_session helper (403 no
  coach / 404 foreign — ratings pattern, DB errors → 5xx); 5 endpoints: GET
  /sessions/{id}/annotations → {annotation, seed, video|null, duration_s}; PUT (validate →
  422 {errors}, upsert on_conflict=session_id, updated_by); DELETE; POST /sessions/{id}/video
  (multipart, file optional + video_origin_s Form; x-upsert to videos/{session_id}.mp4;
  origin-only update allowed; neither → 422); GET /sessions/{id}/video-url (signed URL
  3600 s + origin_s; 404 if none). NEW tests/test_annotations.py (28 tests). VERIFY:
  import api clean; pytest 131 passed (was 103). DEVIATION (design fix): seed
  ordering-consistency walks BACKWARDS through PHASE_KEYS so cycle-derived anchors
  (stroke_start/finish) beat the speculative dive-based underwater estimate when detections
  disagree. DEPLOY NOTE: api.py + annotations.py → Railway on next user push. NOT committed
  (user runs git). SUMMARY owed at UNIFY.

## Session Continuity

Last session: 2026-08-05
Stopped at: Phase 55 COMPLETE (transition run). Session arc: /paul:progress on 51 → amended 51-02
  (struck Task 2 as superseded by 54-01's ENFORCE_TIER_LIMITS, re-resolved all drifted line numbers)
  → applied it (suite 176, schema_contract 4 violations → 0) → user committed + pushed `dedac17` and
  verified AC-1 live → live use surfaced two mobile defects → /paul:discuss created Phase 55 →
  55-01 planned, applied, EAS-built, checkpoint approved → UNIFY + transition.
  Plan-time investigation caught a second half of B2 the bug report could not show: fixing the
  navigate() call alone would have landed on an empty picker, because params are read in useState
  initializers that never re-run on a tab screen.
Next action: UNIFY the two shipped-but-unclosed loops — `/paul:unify
  .paul/phases/52-sample-rate-contract/52-01-PLAN.md` and `.paul/phases/51-api-correctness/51-02-PLAN.md`
  (54-01 also needs closing). All three are already deployed; only SUMMARYs are owed.
Resume file: .paul/phases/55-athlete-flow-fixes/55-01-SUMMARY.md
Still open: 51-02 + 52-01 + 54-01 (SUMMARYs owed), coach-chat wrong-athlete defect (ROADMAP row 56,
  unscheduled), 53-01 + 49-01 (awaiting approval), 50-01 (paused), 43-01, 44-03, 26-01.

Prior session: 2026-08-03
Stopped at: Phase 52 planned AND applied in one session. Reviewed Phase 51 in depth → user chose
  Option A for the sample-rate repair → NEW Phase 52 → 52-01 PLAN → approved → APPLIED, committed +
  pushed 89205ca, patch_09 applied live. Planning found THREE web consumers of the 100 Hz
  assumption that API-AUDIT's F2 did not list (the web builds its own time axes from supabase-js
  reads), plus seed_demo_team.py:424 — all folded into 52-01. PAUSED at the tail of human-verify:
  AC-1 + AC-4 confirmed live, but the annotate-duration and recompute checks need a swim recorded
  AFTER the migration and the user has none since.
Next action: EITHER /paul:unify .paul/phases/52-sample-rate-contract/52-01-PLAN.md (write the
  SUMMARY now, carrying the two unverified checks forward as a known gap) OR record one swim first
  and finish the checkpoint. Then 51-02 (the athletes.coach_id fixes — POST /athletes is STILL
  500ing in production).
Resume file: .paul/phases/52-sample-rate-contract/52-01-PLAN.md
Still open: 51-02 (API fixes — awaiting approval, sequenced after 52-01), 50-01 (demo seeder —
  approved + partially applied, stopped at the T3 human gate), 49-01 (security hardening — awaiting
  approval), 43-01, 44-03, 26-01.

Prior session: 2026-07-30
Stopped at: Discussed a proposed "production hardening" list (product analytics, crash/error
  monitoring, automated testing, CI/CD, API-layer security, shared design tokens). Repo-checked
  each item rather than taking the list at face value — findings: 149 backend tests already
  exist but NOTHING runs them (no .github/workflows); deploys are already continuous (Railway +
  Vercel auto-deploy on push), so the missing half is the "I" not the "CD"; no error tracking
  anywhere (nothing in requirements.txt or web/package.json); no rate limiter; web light tokens
  in globals.css:26-39 are already BYTE-IDENTICAL to mobile src/theme/tokens.js, so the drift
  shared-design-tokens would prevent has not happened. RECOMMENDATION: CI test gate + Sentry
  (~half a day, both would have caught the two live bugs below); approve the existing 49-01 for
  API security; SKIP E2E, EAS workflows, shared tokens, and Expo product analytics until there
  are actual users. → Phase 51 candidate, NOT yet planned.
  Then audited the two "live bugs" — BOTH now closed out this session (see below).
Next action: human-verify the deployed athlete-create fix (add an athlete in the portal), then
  decide Phase 51 scope (CI + Sentry) vs. proceeding to 50-01.
Resume file: .paul/phases/50-demo-team-seeding/50-01-PLAN.md
Still open: 50-01 (demo team seeder — APPROVED + PARTIALLY APPLIED, stopped at the T3 human gate;
  NOT awaiting approval), 49-01 (security hardening — awaiting approval), 43-01, 44-03, 26-01.
  (37-02 removed — it shipped, 62a6f4f.)
CLOSED this session: 48-01 (fix committed + pushed → Railway), 45-01 (patch_06 confirmed applied
  live — column is TEXT).
STALE-STATUS SWEEP 2026-07-30 — STATE/ROADMAP had drifted well behind the working tree. Verified
  against the repo, not the notes:
  • 37-02 (team dashboard web UI) — actually SHIPPED, committed 62a6f4f, live on Vercel. Was
    listed as "plan awaiting approval". Corrected; SUMMARY still owed.
  • 50-01 (demo seeder) — seed_demo_team.py EXISTS (565 lines, untracked) despite STATE's "DO NOT
    APPLY until user says so". ~~Whether Stage 1 was ever RUN against the demo account is UNKNOWN
    (needs a DB check)~~ → **RESOLVED 2026-07-30 from the apply session: apply WAS approved (the
    "DO NOT APPLY" line was itself the stale part), and Stage 1 definitively NEVER RAN — execution
    stopped at the T3 human gate (no demo coach email) and the apply env had no network. No DB check
    needed.** SUMMARY now written + reconciled.
  • 43-01 — genuinely not applied (no DEMO-READINESS.md at repo root).
  • 49-01 — genuinely not applied (api.py:74 still `allow_origins=["*"]`, no upload caps).
  ROOT PATTERN: work gets applied but the loop never closes (no UNIFY/SUMMARY, sometimes no
  commit). Same failure mode that left the 48-01 fix unpushed for ~10 days. Trust the repo over
  these notes until that's fixed.
UNIFY SWEEP 2026-07-30 — 4 SUMMARYs written, loops closed:
  • 48-01-SUMMARY.md — CLOSED. Flags the systemic issue: conftest's global create_client MagicMock
    answers every attribute, so NO supabase call chain in api.py is actually covered by the 149
    tests. This bug class can recur on any dependency bump.
  • 45-01-SUMMARY.md — CLOSED. patch_06 confirmed live. Note: every iOS recording made during the
    ~5-week gap is unrecoverable (raw CSVs were never uploaded either).
  • 37-02-SUMMARY.md — CLOSED retroactively (shipped 62a6f4f 2026-06-18). PHASE 37 COMPLETE (2/2).
    Its "awaiting approval" status distorted Phase-50 planning, which was scoped around an empty
    portal that was already built.
  • 50-01-SUMMARY.md — PARTIAL. Seeder code complete by inspection, but whether Stage 1 was ever
    RUN is UNVERIFIED (needs a DB/portal check). Do that before planning 50-02.
  UNTRACKED FILES STILL NEEDING A COMMIT: seed_demo_team.py (565 lines, only copy),
  supabase/patch_06_*.sql (applied to prod, unversioned), web/app/blog/ + web/lib/blog.js
  (Phase 46 marked complete but never deployed).

Prior session: 2026-07-27
Stopped at: Phase 50 (Demo Team & Synthetic History) — discussed + 50-01 PLAN created, awaiting
  approval. CONTEXT.md written same session.

Prior session: 2026-07-20
Stopped at: Phase 48 (Athlete-Create Fix) 48-01 PLAN created, awaiting approval. First of a
  4-item batch (bug fix → iOS video replay → BLE auto-reconnect → freestyle unlock).

**Prior focus:** Phase 46 (Marketing Blog / build log) — ✅ COMPLETE & CLOSED 2026-06-23 (1/1 plan;
  loop closed, phase transition done). Shipped a public `/blog` on the marketing site — a `/blog`
  index + statically-generated `/blog/[slug]` post pages, linked from Nav + Footer, styled on the
  light `/faq` theme. Seeded with the founder dev-journal as **5 thematic posts** (battery/standalone;
  ASP demo & what broke; string-retraction saga reel→spring→motor→one-way-bearing; matrix-profile→
  wavelet segmentation breakthrough; current-state + video-overlay/auto-tracking-camera roadmap) in
  a **lightly polished candid** voice. NEW web/lib/blog.js (posts data + getPost/postsNewestFirst),
  web/app/blog/page.js (index), web/app/blog/[slug]/page.js (SSG + notFound); Nav.js + Footer.js
  "Blog" links. Build green, preview-verified, checkpoint approved. No new deps, no fabricated dates,
  portal/dark-theme untouched. Adding a future post = append one object to web/lib/blog.js. NOT
  committed (user runs git — commit cmd provided in chat). SUMMARY: 46-01-SUMMARY.md. NEXT:
  user-owned threads (the batched EAS build covering 38/39/41/42/44 device deferrals + 45 migration),
  16-06 wavelet tuning, or a new phase.

## Loop Position (46-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [46-01 CLOSED 2026-06-23 — /blog shipped + verified; SUMMARY written; PHASE 46 COMPLETE (1/1)]
```
46-01 APPLIED (web, all 3 tasks + checkpoint approved): NEW web/lib/blog.js (5 thematic posts,
  ESM, lightly-polished-candid voice — battery/standalone, ASP demo, retraction saga, wavelet
  segmentation, current-state+roadmap; getPost + postsNewestFirst helpers). NEW web/app/blog/page.js
  (index: light theme, Nav+Footer, 5 cards newest-first → /blog/[slug]). NEW
  web/app/blog/[slug]/page.js (async params per this Next 16; generateStaticParams +
  generateMetadata + notFound on unknown slug; renders {h}/{p} body blocks). Nav.js + Footer.js:
  "Blog" → /blog link added. VERIFIED: `npm run build` green (/blog static, /blog/[slug] SSG all 5
  paths prerendered); preview — index lists 5 posts newest-first, post page 200 (title+heading+
  back-link), bogus slug 404, 2 /blog links on homepage (Nav+Footer), no console errors. Deviation:
  plan's Task-1 `require()` verify N/A (file is ESM) → verified via build + preview instead. No new
  deps, no fabricated dates, portal/dark-tokens untouched. NOT committed (user runs git). SUMMARY
  owed at UNIFY.

**Prior focus:** Phase 45 (Cloud Session Save) — ✅ RESOLVED 2026-07-30: patch_06 IS applied to
  the live DB (`information_schema` reports `sessions.device_id` = `text`), so the 22P02 failure
  described below no longer occurs. The migration file remains UNTRACKED in git — commit it.
  Historical description follows. 45-01 created 2026-06-23
  (autonomous:false). ROOT-CAUSED, decisive fix. Bug: NO iOS session saves to the cloud — live
  Supabase `sessions.device_id` was type **UUID**, but api.py /process writes the device **chip-id
  string** (e.g. "64CD4D") into it → insert fails `invalid input syntax for type uuid: 64CD4D`
  (22P02). Save is non-fatal → swimmer sees the report, then `⚠ Save failed`, nothing persists.
  The UUID→TEXT migration was DOCUMENTED in patch_04:31-42 but never run (the error proves the column
  is still UUID); Phase-21 reliable pairing means every session now hits it. SAME bug hides the
  "advanced segmentation view" — 39-05's dashed overlay only renders on a *saved* session's
  ReportCard→Advanced, unreachable while saves fail. FIX: new
  supabase/patch_06_sessions_device_id_text.sql (idempotent, guarded UUID→TEXT + drop FK,
  `USING device_id::text`); NO app-code change (the chip-id write is correct once the column is TEXT;
  the devices table is chip-id-keyed). 1 auto task + human-action (run SQL) + human-verify (on-device
  save + overlay). DEFERRED by user decision: video→cloud upload ("discuss first" — undecided);
  RecordScreen segmentation-overlay parity (optional follow-up). Plan:
  45-cloud-session-save/45-01-PLAN.md. DO NOT APPLY until user says so.

## Loop Position (45-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [45-01 CLOSED 2026-07-30 — SUMMARY written. RESOLVED — patch_06 (sessions.device_id UUID→TEXT) IS applied to the live DB; information_schema reports `text`, so the 22P02 insert failure is gone and iOS cloud saves are unblocked. No app code was ever needed. NOTE: supabase/patch_06_sessions_device_id_text.sql is still UNTRACKED in git — commit it so the applied-migration record survives. REMAINING: on-device confirm that a session persists (rides the pending EAS build), then UNIFY + SUMMARY]
```

**Open parallel loop (44-03):** Phase 44 (Encoder Data Integrity) — 44-03 APPLIED 2026-06-22, paused
  at human-verify checkpoint (needs firmware flash + EAS build). Independent subsystem (firmware +
  VideoOverlay; does NOT touch the cloud-save path) — the Phase-45 EAS build can verify both at once.
  (autonomous:false). 44-01 (diagnostic) + 44-02 (warmup + indications) applied. 44-02 checkpoint:
  packet loss FIXED ✅; two defects remain → 44-03: (Task 1) warmup MIN-TIME FLOOR — the 44-02
  stability gate broke early on the stable 12×3444 garbage plateau (settled angle≈3444), so add
  WARMUP_MIN_MS≈150 so the break can't fire until the transient is past → kills the pulse. (Task 2)
  END-ANCHOR the video overlay — VideoOverlayScreen videoOriginS = deviceDuration − videoDuration
  (both stop on one tap; warm-up-agnostic) instead of the recordAsync-call timestamp that's ~2 s
  before the first frame → fixes the 2 s video desync. Checkpoint: flash + EAS build. Plan:
  44-encoder-data-integrity/44-03-PLAN.md. DO NOT APPLY until user says so.

## Loop Position (44-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ◐        ○     [44-03 APPLY: Tasks 1+2 done 2026-06-22, paused at human-verify checkpoint — needs flash + EAS build]
```
44-03 APPLIED. Task 1 DONE (ESP_32_V5.ino): added WARMUP_MIN_MS=150 (+ WARMUP_MAX_MS→300); warmup
  stability break now gated on `(millis()-warmStart) >= WARMUP_MIN_MS` so it can't settle on the
  stable 3444 plateau. Structural review only (no arduino-cli). Task 2 DONE (../swimnetics-mobile
  VideoOverlayScreen.js): videoOriginS = deviceDurationS (time[last]-time[0]) − videoDurationS
  (player.duration, read in the 20Hz poll once loaded); origin null until duration known (marker
  inert); gate no longer requires the start timestamps; debug line shows device/video durations +
  origin; removed now-unused sessionStartPhoneMs/videoStartPhoneMs destructure. `npx expo export
  --platform ios` exit 0 (3.2MB). NOT committed (user runs git). NEXT: user flashes firmware +
  EAS build, runs checkpoint — AC-1 (warmup settles ≈651, no pulse), AC-2 (overlay aligned at
  nudge 0, origin ≈ deviceDur−videoDur ≈2 s), AC-3 (plain+video+race-start OK, 44-02 counts still
  match). Reminder: set TRACE_BUFFER back to 0 once verified.
44-03 — Task 1 (ESP_32_V5.ino): add WARMUP_MIN_MS (~150) + raise WARMUP_MAX_MS (~300); gate the
  warmup stability break on elapsed ≥ MIN so it can't settle on the stable garbage plateau. Task 2
  (../swimnetics-mobile VideoOverlayScreen.js): videoOriginS = (time[last]-time[0]) − player.duration
  (read once video loads); keep ±nudge; start timestamps demoted to debug. Verify: structural review
  + expo export exit 0; checkpoint AC-1 (no pulse) / AC-2 (overlay aligned at nudge 0, origin≈2 s) /
  AC-3 (no regression, counts still match). Deferred: AS5600 CONF/power-mode root-cause for the 3444
  plateau (would remove the discard).

**Prior focus:** Phase 44 (Encoder Data Integrity — pulse + dump reconciliation) earlier
  (44-01 created 2026-06-22, autonomous:false). DIAGNOSTIC plan: localize the
  persistent startup velocity pulse + the firmware↔iOS sample-count mismatch to ONE stage
  (sensor read / RAM buffer / BLE dump / server processing / physical) before fixing. Driven by
  on-device testing 2026-06-22: read-path 4095 fix applied ([[firmware_i2c_4095_garbage]]) but
  (1) iOS received count ≠ serial count, (2) prior SERIAL_PLOT diagnostic unusable (BLE-off +
  drowned by debug-log numbers → plotter charts millis()), (3) giant pulse persists in app output.
  Task 1: replace SERIAL_PLOT free-run with a BLE-coexisting post-STOP RAM-buffer serial trace
  (clean single angle series, '#'-bracketed, debug noise gated). Task 2: surface firmware
  buffered/sent vs iOS received counts; record mismatch size+direction. Task 3 (human-verify
  checkpoint): run stationary recording, report a/b/c → decision tree picks the 44-02 fix target.
  SCOPE: diagnose only — NO pipeline/protocol changes; the pulse fix is follow-up 44-02. Plan:
  44-encoder-data-integrity/44-01-PLAN.md. DO NOT APPLY until user says so.

## Loop Position (44-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ◐        ○     [44-01 APPLY: Tasks 1+2 done 2026-06-22, paused at human-verify checkpoint — user runs stationary recording]
```
Task 1 DONE (ESP_32_V5.ino): removed SERIAL_PLOT free-run; added TRACE_BUFFER (default 1) —
  after each stopRecording() the RAM buffer prints to Serial as clean angle_counts lines
  ("# TRACE n=" header + "# END"), DEBUG forced off so the plotter shows only the trace, BLE
  buffer-and-dump intact. dumpBuffer() prints "# DUMP_SENT=" (firmware sent count). Structural
  review only (no arduino-cli). Task 2 DONE (../swimnetics-mobile RecordScreen.js): retrieved
  sample count now persists on the saving + uploading screens (was vanishing). `npx expo export
  --platform ios` exit 0 (3.2MB). NOT committed (firmware here / mobile local-only; user runs git).
  CHECKPOINT FINDINGS (2026-06-22, new EAS build): (a) firmware buffer trace is CLEAN — angle sits
  ~1183 dithering to 1182 (±1 LSB); the 4095 read-path fix WORKED. The "crazy" plotter look = Serial
  Plotter is the wrong tool (rolling live view + it plots the numbers in the "# TRACE n=" header →
  phantom value2). (b) firmware count > iOS count, equal for N<~1000, gap GROWS with N → BLE DUMP
  PACKET LOSS (ESP32 notify congestion; overflow silently dropped) — corrupts every recording. (c)
  velocity start pulse PERSISTS, now wavelet-shaped (giant spike + symmetric ripples) = Chebyshev
  decimate filter ringing on a single start-step → a real start discontinuity, NOT the sensor (and
  not explainable by loss on stationary data). SPLIT INTO TWO independent problems:
  → 44-02 (transport, ready to plan/build): make the DUMP guaranteed-delivery — TX via ATT
    INDICATIONS (acknowledged, self-flow-controlled, no loss; ~slower) or explicit chunk flow
    control. Fixes finding (b). High priority — data loss on all recordings.
  → 44-03 (pulse, needs one more datum): get the FIRST ~40 trace values via Serial MONITOR (not
    plotter) to localize the start step to firmware-buffer (sensor/physical) vs downstream
    (transport/processing). Then fix.
  Reminder: set TRACE_BUFFER back to 0 for normal builds.
  RESOLVED 2026-06-22: user pasted trace head — `3444 ×12 → 0 → 488 → 651…` (true=651). The
  startup transient (~52 ms of garbage reads) is IN THE FIRMWARE BUFFER at record start (pre-
  transport) → it is the start-step the Chebyshev decimate filter rings on (the wavelet pulse).
  Both defects now root-caused → combined into 44-02 (no separate 44-03).

## Loop Position (44-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ◐     [44-02 checkpoint 2026-06-22: AC-2 PASS (packet loss FIXED — indications worked). AC-1 FAIL (pulse remains). + new video desync. → 44-03]
```
44-02 CHECKPOINT RESULT (user, new EAS build): AC-2 ✅ packet loss fixed (ATT indications worked,
  no fallback needed). AC-1 ❌ pulse persists — warmup log reported settled angle ≈3444 (GARBAGE):
  the stability gate broke early on the stable 12×3444 plateau (identical reads = "settled"). NEW
  issue found: plain Record-with-Video (race-start OFF, one tap) desyncs — device 8 s vs video 6 s,
  video ~2 s ahead, seen in VideoOverlayScreen. Root cause: overlay anchors on videoStartPhoneMs =
  recordAsync() CALL time (RecordScreen.js:524), but the camera warm-up (~2 s) delays the first
  frame → origin ≈0 should be ≈2 s. Both → 44-03.
Task 1 DONE (ESP_32_V5.ino): WARMUP_* defines + bounded warmup loop in startRecording() (reads
  discarded until 5 reads within ±4 cnts, or 100 ms cap; seeds lastGoodAngle) → first buffered
  sample is settled, kills the 3444→ transient → kills the pulse. Task 2 DONE (ESP_32_V5.ino):
  TX char PROPERTY_NOTIFY→PROPERTY_INDICATE; all 4 pTxChar->notify() → notify(false) (ATT
  indication, confirm = flow control); removed the dump's per-packet vTaskDelay + orphaned
  DUMP_PACKET_DELAY_MS. iOS UNCHANGED (CoreBluetooth/ble-plx monitor enables the indicate CCCD
  automatically; packet formats untouched → parsePacket() valid). Structural review only (no
  arduino-cli); no expo export needed (iOS untouched this plan). NOT committed (user runs git).
  NEXT: user flashes firmware + builds/installs iOS, runs the checkpoint — AC-1 (stationary: trace
  head starts at true angle, no velocity pulse), AC-2 (N>2000: # DUMP_SENT == app Retrieved ==
  # TRACE n=), AC-3 (plain+video+race-start OK), + note dump duration. Risk to watch: if ble-plx
  keeps subscribing to notifications (loss persists) → fallback = app-driven windowed ACK. Reminder:
  set TRACE_BUFFER back to 0 once verified.
44-02 — fixes BOTH defects in one pass. Task 1 (firmware): record-start WARMUP gate in
  startRecording() — discard reads until stable (K=5/±4 cnts) or WARMUP_MAX_MS≈100 ms, then
  buffer, so sampleBuf[0] is the settled angle (kills the 3444→ transient → kills the pulse).
  Bounded for Phase-41 race start. Task 2 (firmware + maybe iOS): guaranteed-delivery DUMP via
  ATT INDICATIONS (TX char INDICATE; pTxChar->notify(false); confirm = flow control → no
  congestion loss); packet formats unchanged so iOS parsePacket() untouched (ideally no iOS
  change — verify received==# DUMP_SENT); fallback = app-driven windowed ACK. Tradeoff: dump
  slower (~1 pkt/conn-interval). Checkpoint (human-verify, needs flash + EAS build): AC-1 no
  start pulse / AC-2 counts match for N>2000 / AC-3 plain+video+race-start OK. Plan:
  44-encoder-data-integrity/44-02-PLAN.md. DO NOT APPLY until user says so.
44-01 — 2 auto tasks + 1 human-verify checkpoint. Files: ESP_32_V5/ESP_32_V5.ino +
  ../swimnetics-mobile/src/screens/RecordScreen.js. Builds a usable diagnostic + reconciles counts;
  the actual pulse fix is deferred to 44-02 (target chosen by the checkpoint decision tree). NOTE
  context: the firmware currently has SERIAL_PLOT (free-run, BLE-off) at flag 0 from the prior fix
  pass — Task 1 supersedes it with the BLE-coexisting buffer trace.

**Prior focus:** Phase 43 (Demo Readiness — Failure-Mode Catalog & Pre-Demo Checklist) — Planning
  (43-01 created 2026-06-22, awaiting approval, autonomous:true). Documentation deliverable (NOT code):
  one cross-system runbook DEMO-READINESS.md at repo root. Part A = failure-mode catalog (FMEA) across
  Hardware/Encoder + BLE/Connectivity + App(record/results) + Backend/Network/Account, each row =
  symptom/root-cause/current-mitigation(cite real Phase-42/34 code)/residual-risk/manual-workaround.
  Part B = ordered checkbox pre-demo checklist (Hardware bench + App + Backend/Account/Venue + a "T-10
  min" quick list; keystone = one record→retrieve→results dry-run). Part C = mid-demo fallback table
  (BT off / device not found / magnet not detected / empty buffer / offline upload / Railway cold-start
  / no athlete → on-the-spot fix vs. backup). 2 auto tasks. SCOPE: doc only — no in-app self-test
  this phase (noted as future option); cite real mitigations only. Plan: 43-demo-readiness/43-01-PLAN.md.
  DO NOT APPLY until user says so.
**Prior focus:** Phase 42 (Core-Flow Failsafes — iOS) — ✅ COMPLETE & CLOSED 2026-06-22 (1/1 plan;
  export green ×3). Hardened pairing/recording/results so each auto-recovers or fails with a
  specific, actionable reason; no session data ever lost. Shipped (code, swimnetics-mobile): NEW
  src/lib/friendlyError.js (BLE/upload reason mappers) + src/lib/deviceStatus.js (shared STATUS
  decode). Pairing: ensureBleReady (off/permission) + connect 10s timeout + 1 auto-retry + specific
  scan/connect reasons. Recording: pre-record checkEncoder (STATUS warn+override) + plain-start
  connection guard; mid-record drop handler already existed (reused). Results: upload Retry on the
  saved CSV + offline/server/parse reasons; ReportCardScreen load-reason branching (not-found/
  incomplete/offline) + Retry. NO new native deps. DEVICE VERIFY DEFERRED → next EAS build (failure
  paths need hardware/network: BLE off, timeout, magnet absent, network loss). NOT committed (mobile
  repo local-only; user runs git — git command provided in chat). SUMMARY: 42-01-SUMMARY.md. NEXT:
  user-owned threads (batched EAS build covering 38/39/41/42 device deferrals), 16-06 wavelet tuning,
  or a new phase.
**Prior focus:** Phase 41 (Race-Start Sequence — iOS) — ✅ COMPLETE & CLOSED 2026-06-22 (1/1
  plan; export green, 1071 modules). Shipped (code, swimnetics-mobile): optional meet-style race
  start on the record flow — giant 3-2-1 countdown → spoken "take your marks" → RANDOM 2–3 s hold →
  blare, recording (BLE START / camera) begins ON the blare; persisted default-ON toggle on
  RecordingConfigScreen; works over plain + Record-with-Video; toggle OFF = exact prior behavior.
  New files: useStartSequence hook, StartSequenceOverlay, startSequencePrefs (secure-store), 2
  bundled audio clips (takeyourmarks.mp3 + beep.mp3). New native dep: expo-audio. DEVICE VERIFY
  DEFERRED → next EAS build (audio incl. silent-mode, visuals/timing, START-on-blare plain+video,
  Cancel; confirm beep.mp3 is loud enough). NOT committed (mobile repo local-only; user runs git —
  git command provided in chat). SUMMARY: 41-01-SUMMARY.md. NEXT: user-owned threads (the batched
  EAS build covering 38/39/41 device deferrals), 16-06 wavelet tuning, or open a new phase.
**Prior focus:** Phase 40 (Website Redesign — iOS match) — ✅ COMPLETE 2026-06-22 (2/2 plans; loop
  closed, phase transition done). Marketing site redesigned to the iOS Template-B immersive purple
  gradient on shadcn/Tailwind-v4; pricing removed sitewide → "Request a quote" ContactDialog
  (Web3Forms → tzheng846@gmail.com). 40-01 SHIPPED + CLOSED (landing core). 40-02 =
  remaining marketing sections: Features+HowItWorks restyle to light; RequestQuote section (gradient
  CTA, reuses ContactDialog) REPLACES Pricing (Pricing.js DELETED — pricing removed sitewide);
  login restyle; /faq + /privacy retheme to light (content untouched EXCEPT the FAQ "How much does
  it cost?" answer — scrubbed of $300/$20 per the pricing-removal directive + bottom CTA → dialog).
  depends_on 40-01 (reuses shadcn + tokens + ContactDialog). LAST plan in Phase 40 → UNIFY triggers
  the phase transition. DO NOT APPLY until user says so.
  Redesign the MARKETING site (web/) to match the iOS app: **Template B (immersive purple→periwinkle
  gradient)** chosen via 2 mockup artifacts (web/design-mockups/template-a|b-*.html); shadcn/ui in
  plain JS (Tailwind v4 CSS-first, NO TS); pricing REMOVED → "Request a quote" ContactDialog (name +
  email + optional message) that emails leads to tzheng846@gmail.com via Web3Forms (form-to-email; no
  backend; public access key in lib/site.js WEB3FORMS_ACCESS_KEY — USER creates the key at
  web3forms.com w/ that gmail as destination; placeholder seeded). Decisions (user, 2026-06-21,
  AskUserQuestion ×5): Template B; marketing-site-only; shadcn-in-JS-keep-stack; CTA = form-to-email
  (revised from scheduling link). KEY CONSTRAINT: marketing + portal SHARE the global @theme tokens —
  40-01 ADDS a new light-purple iOS token set + rewrites marketing components onto it, leaving the
  dark --color-* tokens (portal/report depend on them) UNTOUCHED. 40-01 = foundation + landing core
  (shadcn+tokens+booking config; Nav scroll-aware; immersive Hero w/ floating SampleChart card;
  Footer light; page.js) + checkpoint. 40-02 (next) = Features, HowItWorks, Pricing→Book-a-call
  section, login restyle, faq/privacy retheme. Plan: 40-website-redesign/40-01-PLAN.md.
**Prior focus:** Phase 39 (Redesign Fixes & UX Iteration) — 39-01…05 CLOSED. 39-06 (DU4 flag
  abnormal + ignore) DEFERRED 2026-06-20 by user ("too much work, defer for later"). DECISIONS
  CAPTURED for when it resumes: abnormal = plausible_fraction<0.60 OR magnet_dropout_pct>10%
  (NOT cv_isi, NOT segmentation_reliable — always-false placeholder); ignore persists in a NEW
  sessions.flag_ignored column + PATCH /sessions/{id} (patch_06, user-applied); abnormal derived
  on read from metrics_json.data_quality (only flag_ignored stored); scope = api.py (PATCH allow
  flag_ignored + `flagged` in /team/overview recent/needs-attention) + supabase patch_06 + 3 screens
  (SessionHistory/AthleteDetail add metrics_json to their selects; Dashboard reads `flagged`). Phase
  39 effectively done pending 39-06 + the one EAS build. See "Loop Position (39-05)" below. (Original
  bug locations retained for reference.) BUGS LOCATED: (1) PillarCards expand ignores m/yd; (2) "declined"+green = band≠trend by
  design (ratings._trend correct) → UI clarity decision; (3) CRASH = AthleteDetailScreen.js:149
  undeclared `rc` (→ BAND_COLOR), crashes any tested athlete; (4) team-name edit blocked by teams
  SELECT-only RLS → patch_05 UPDATE policy. See 39-01-PLAN. Phase 38 = ✅ code-complete (awaits the one
  EAS build + 38-TEST-PLAN device checks). (Phase 37 web 37-02 still parked.)
**Prior focus:** Phase 38 (Mobile UI/UX Redesign) — ✅ CODE-COMPLETE 2026-06-19 (6/6 plans, all
  export-green). Light purple theme + bottom-tab nav (Record island), Dashboard team-health + ambient
  AI, Team pillar table + athlete hub + reports, History team-wide + Compare, session-detail restyle,
  dark/immersive record flow. Device testing → ONE EAS build (incl. expo-crypto); 38-TEST-PLAN.md.
**Prior focus:** Phase 37 (Team Coach Dashboard) — Planning. Revamp the web coach dashboard
  from a raw-numbers athlete list into a team-health home: team pulse (band-distribution chips),
  needs-attention list, recent-activity feed, color-banded roster grid. Reuses ratings.py (pillar
  bands) + roster_metrics.py — both already exist, never surfaced visually. Decisions (user,
  2026-06-18, AskUserQuestion ×3): all 4 sections; NEW GET /team/overview endpoint (bands stay
  Python-computed — Phase-36 source of truth); keep tight (NO per-athlete detail page — athlete card
  still links to filtered session list). iOS mirrors later. SPLIT like Phase 36: 37-01 BACKEND
  (endpoint + summarize_team + tests) created, awaiting approval; 37-02 WEB UI follows the locked
  payload. (Phase 35/36 history below.)
**Prior focus:** Phase 35 (Feature Verification & Doc Reconciliation) — ✅ COMPLETE 2026-06-18
  (3/3 plans). 35-01 web (all WORKING) + 35-02 iOS (ratings UI + iPad de-scope verified on device;
  2 device bugs fixed; recording checks deferred) + 35-03 docs (CLAUDE.md + CODEBASE-AUDIT.md
  reconciled to Phases 33–36; Feature Status Ledger added). TRACKED DEFERRALS (not blockers):
  post-resolder iOS device re-verify (4 recording checks + 2 fix re-verifies, one build); coach
  review of DRAFT breaststroke thresholds; iOS↔web parity gaps (AI chat + advanced graphs = future
  iOS-parity phase); 16-06 wavelet tuning (flips segmentation_reliable). NEXT: user-owned threads
  above, or open a new phase. (35-02 detail + Phase 36 below.)

**Prior focus:** Phase 35 35-02 iOS ✅ CLOSED 2026-06-18. Shipped the
  Phase-36 rating UI on iOS (RN PillarCards mirroring web + Simple/Advanced toggle on
  ReportCardScreen), de-scoped iPad to iPhone-compat (TARGETED_DEVICE_FAMILY=1 in pbxproj —
  authoritative since EAS ignores app.json's ios block in a non-CNG project), aligned a pre-build
  version skew (expo install --fix). Verified on a real EAS build + device: app launches (no dyld
  crash), ratings UI (breaststroke) ✓, iPad letterboxed ✓, Diagnostics live ✓. Found + FIXED 2
  device bugs (Forget didn't disconnect BLE; Diagnostics mislabeled an unwired AS5600 as "Too
  weak" instead of "SENSOR NOT RESPONDING"). Gate 0 backend deploy done by user (PR #5 → main →
  Railway live). DEFERRED (encoder wiring came loose; no solder station): the 4 recording-gated
  checks + re-verify the 2 fixes → all ride ONE post-resolder build (no extra cost). iOS↔web
  parity gaps logged (AI chat + advanced per-cycle graphs are web-only). NEXT: 35-03 doc
  reconciliation (no hardware — last Phase 35 step). (Phase 36 backend+web below.)

**Prior focus:** Phase 36 (Coach-Friendly Metric Ratings) — ✅ backend+web COMPLETE & CLOSED
  2026-06-17 (36-01 + 36-02 loops closed; iOS = future own phase). Replaced raw numbers with
  good/ok/needs-work across 4 pillars (Speed, Stroke Length, Consistency, Endurance); hybrid
  band+trend; shared ratings.py + GET /sessions/{id}/ratings; web pillar cards verified
  end-to-end vs a local backend. Review-hardening pass landed (DB errors → 5xx not masked
  403/404; a11y). Suite 93 passed. GO-LIVE (user-owned): commit review fixes + push the PR
  (feat/coach-chat-drills, bundles Phase 33+36) → Railway+Vercel auto-deploy → revert
  web/.env.local NEXT_PUBLIC_API_URL back to Railway. Coach review of DRAFT breaststroke
  thresholds owed. NEXT open work: Phase 35 (35-02 iOS device checkpoints + the new ratings UI
  on iOS, one EAS build; 35-03 doc reconciliation).
  Phase 35 (Feature Verification): 35-01 WEB ✅ CLOSED 2026-06-17 — ALL web features WORKING
  (public surfaces, portal, compare, parent reports, Railway writes). 0 web code bugs. Only
  issue = prod /coach/chat 503 "Coaching not configured" (ANTHROPIC_API_KEY unset on Railway) —
  USER FIXED: set key + redeployed + verified chat working (AC-3 satisfied). 35-02 (iOS, one EAS
  build batching 34-01/21-02/26-01/22-02 device checkpoints; hardware ready) + 35-03 (docs) still
  pending — to run AFTER Phase 36 (UI ratings change touches iOS, so do it before the iOS verify).
  35-01 SUMMARY + WEB-FINDINGS written. (Prior focus below.)
  Phase 34 (Device Diagnostics) — ✅ 34-01 loop CLOSED 2026-06-16 (code complete;
  on-device verify DEFERRED to a later plan per user). Shipped: firmware STATUS BLE command +
  in-app DiagnosticsScreen. Closes the "no recording found" black box — likely cause of the
  reported failure is magnet-not-detected at record start. PR creation SKIPPED (PR-TICKETS.md
  retained, nothing committed). NEXT: when EAS credits + a reflash are available, run a small
  follow-up plan for the 34-01 Task 3 device checkpoint (magnet absent→"NOT DETECTED", align→
  detected, spin→angle changes, record→buffer climbs). (Phase 33 AI Chat v2 below
  ✅ CLOSED 2026-06-16 — 33-01/02/03 shipped; semantic RAG / streaming+history+live-verify /
  visual-proof deferred to future (33-04/05/06). CLAUDE.md updated for the new chat architecture.)

## Loop Position (43-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ○        ○     [43-01 created 2026-06-22, awaiting approval — demo-readiness runbook (doc only), autonomous:true]
```
43-01 PLAN — autonomous:true, 2 auto tasks (type:research; doc deliverable, no code). Creates
  DEMO-READINESS.md at repo root. Task 1: Part A failure-mode catalog — 4 domain tables
  (Hardware/Encoder, BLE/Connectivity, App record/results, Backend/Network/Account); each row
  symptom/root-cause/current-mitigation(cite RecordScreen/BleContext/DiagnosticsScreen/friendlyError/
  deviceStatus/ESP_32_V5.ino/api.py)/residual-risk/manual-workaround; honest about uncovered modes.
  Task 2: Part B ordered checkbox checklist (Hardware bench + App + Backend/Account/Venue + T-10 quick
  list; keystone = record→retrieve→results dry-run; warm-up Railway to dodge cold-start) + Part C
  mid-demo fallback table (recover-live vs. backup; keep one known-good saved session as ultimate
  backup). Cross-references (not duplicates) swimnetics-mobile/38-TEST-PLAN.md + 39-TEST-PLAN.md.
  SCOPE: doc only — DO NOT change app/firmware/backend code; no in-app self-test (future option).
  VERIFY: grep DEMO-READINESS.md for the 4 domains + checklist groups + fallback table.

## Loop Position (42-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [42-01 CLOSED 2026-06-22 — core-flow failsafes; export green ×3; SUMMARY written; PHASE 42 COMPLETE (1/1). Device verify → next EAS build]
```
42-01 APPLIED (code, swimnetics-mobile): Task 1 Pairing — NEW src/lib/friendlyError.js
  (bleStateReason/bleReason/uploadReason); BleContext ensureBleReady (manager.state) + connectToDevice
  timeout:10000 + 1 auto-retry (throws mapped reason); DevicesScreen pre-scan ensureBleReady +
  scan-error/empty-scan messaging (pairMsg) + bleReason; RecordingConfigScreen pre-connect
  ensureBleReady. Task 2 Recording — NEW src/lib/deviceStatus.js (parseStatus/magnetVerdict +
  STATUS consts + hardFault flag) extracted from DiagnosticsScreen (now imports it, dupes deleted);
  RecordScreen checkEncoder (STATUS round-trip, 2s timeout, warn+override on hardFault) in beginPlain
  + before camera mount; plain-start connection guard. NOTE: mid-record BLE-drop handler ALREADY
  existed (RecordScreen useEffect L141 — stops timers, "session retained on device, reconnect+Retrieve",
  →error state); satisfied AC-2 as-is (video deliberately excluded — camera keeps filming). Task 3
  Results — uploadAndProcess classifies offline/server/parse via uploadReason (no throw) + error-state
  shows Retry-Upload (re-sends savedPath, no data loss) vs Try-Again when no CSV; ReportCardScreen
  fetchSession reason-branching (not-found PGRST116 / incomplete metrics_json / offline / generic) +
  cancel-safe + reloadKey Retry button. VERIFY: npx expo export --platform ios exit 0 ×3 (after each
  task); self-review clean (no dangling STATUS refs in Diagnostics; tokens white/good/ok/needsWork
  exist). DEVICE VERIFY DEFERRED → next EAS build (BLE-off/permission, connect timeout/retry,
  pre-record magnet warn, mid-record drop, upload retry on real network fail, report-card retry). NOT
  committed (mobile repo local-only; user runs git). SUMMARY owed at UNIFY. NEXT: /paul:unify.

42-01 PLAN — autonomous:true, 3 auto tasks (mobile-repo-only; no new native deps). Task 1 Pairing:
42-01 PLAN — autonomous:true, 3 auto tasks (mobile-repo-only; no new native deps). Task 1 Pairing:
  NEW src/lib/friendlyError.js (bleReason mapper) + BleContext ensureBleReady (manager.state/
  onStateChange) + connectToDevice timeout:10000 + 1 auto-retry (throws mapped reason) +
  DevicesScreen pre-scan BLE-ready check + scan-error/empty-scan messaging + RecordingConfigScreen
  pre-connect check. Task 2 Recording: extract parseStatus+magnetVerdict+STATUS consts to NEW
  src/lib/deviceStatus.js (DiagnosticsScreen imports it, dupes deleted) + RecordScreen checkEncoder
  (STATUS round-trip, ~2s timeout, warn+override on hard fault) called in beginPlain + before camera
  mount + plain-start connection guard + connectionStatus-drop effect → linkDropped banner ("data
  safe, reconnect+retrieve", stop timer, NO auto-reconnect). Task 3 Results: uploadAndProcess
  classify offline/server/parse + Retry-upload button on savedPath (no data loss) + ReportCardScreen
  fetchSession reason-branching (offline / not-found / corrupt metrics_json) + Retry. SCOPE: do NOT
  touch BLE sample/META/DUMP parsing, sync math, camera order, race-start timing, backend/web; no
  offline queue; no silent auto-reconnect; STATUS check warns (not hard-block). VERIFY each task:
  npx expo export --platform ios exit 0. Device verify → next EAS build.

## Loop Position (41-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [41-01 CLOSED 2026-06-22 — iOS race-start sequence; export green (1071 modules); audio bundled; SUMMARY written; PHASE 41 COMPLETE (1/1). Device verify → next EAS build]
```
41-01 APPLIED (code, swimnetics-mobile): expo-audio installed (~56.0.12) + app.json plugin; audio
  MOVED to assets/audio/ (takeyourmarks.mp3 voice + beep.mp3 blare — user-supplied, satisfies the
  human-action checkpoint up front) + README. src/lib/startSequencePrefs.js (secure-store get/set,
  default TRUE). RecordingConfigScreen: Switch "Race start sequence" (loads pref on mount, persists
  on toggle, default ON) → `startSequence` Record nav param. src/hooks/useStartSequence.js
  (useAudioPlayer ×2; setAudioModeAsync playsInSilentMode; run() phase count3/2/1→marks[awaits voice
  didJustFinish, 2.5s safety]→hold[random 2000–3000ms]→blare[plays horn, resolves AT play, clears
  +600ms]; cancelable canceledRef+timerRef; unmount-safe). src/components/StartSequenceOverlay.js
  (absoluteFill scrim; giant 3-2-1 / "Take your marks" / blare flash; Cancel). RecordScreen: seq
  hook + `startSequence` param (default true); beginPlain gates startRecording; onCameraReady gates
  writeCmd('START') behind seq.run() over the live preview (canceled→setVideoMode(false)); overlay =
  last child of flex:1; button→beginPlain; onCameraReady deps += startSequence,seq. Toggle OFF =
  exact prior behavior (immediate START). VERIFY: npx expo export --platform ios exit 0, 1071
  modules, both mp3s bundled. DEVICE VERIFY DEFERRED → next EAS build (expo-audio = new native
  module): countdown visuals, audio (incl. silent-mode), random hold, START-on-blare plain+video,
  Cancel. NOT committed (mobile repo local-only; user runs git). SUMMARY owed at UNIFY. NEXT:
  /paul:unify to close 41-01.

41-01 PLAN — autonomous:false (human-action checkpoint: user supplies the 2 audio files).
  Mobile-repo-only (swimnetics-mobile). 3 auto tasks + checkpoint. Task 1: expo-audio dep +
  app.json plugin + assets/audio/README + src/lib/startSequencePrefs.js (secure-store, default
  TRUE) + RecordingConfigScreen Switch "Race start sequence" (persisted, default ON, passed as a
  Record nav param). Task 2: src/hooks/useStartSequence.js (phase state count3/2/1→marks→hold→
  blare; run() resolves Promise AT the blare; cancel()) + src/components/StartSequenceOverlay.js
  (full-screen scrim overlay: giant 3-2-1, "Take your marks", blare flash, Cancel). Task 3:
  RecordScreen wiring — gate BOTH start paths (plain startRecording + onCameraReady's writeCmd
  ('START')) behind seq.run() when enabled; overlay rendered over plain+camera; toggle OFF = exact
  current behavior. Checkpoint: user drops take-your-marks.m4a + start-horn.m4a into assets/audio/.
  SCOPE: do NOT touch BLE/camera/META/DUMP/pipeline/sync logic (timing-gate only), backend, or web.
  Device verify deferred → next EAS build (expo-audio is a new native module). VERIFY each task:
  npx expo export --platform ios exit 0.

## Loop Position (40-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [40-02 CLOSED 2026-06-22 — full marketing site light-themed; 2 nav bugs fixed; SUMMARY written; PHASE 40 COMPLETE (2/2)]
```
40-02 APPLIED (web): Features + HowItWorks restyled to light (token map); NEW RequestQuote.js
  (purple gradient CTA card + ContactDialog, id="pricing", NO prices) REPLACES Pricing; Pricing.js
  DELETED; page.js = Nav(overHero) → Hero → Features → HowItWorks → RequestQuote → Footer. login
  restyled to light (shadcn Input/Button; auth logic untouched). /faq rethemed to light + cost
  answer scrubbed of $300/$20 (→ "request a quote") + bottom CTA → ContactDialog. /privacy rethemed
  to light (legal copy untouched; token swaps only, ordered to avoid text-ink→text-ink-900 collision).
  BUGS FIXED (user-reported at checkpoint, 2 rounds): (1) Nav white-on-light/invisible at top of
  /faq + /privacy → added Nav `overHero` prop (homepage passes it; other pages start SOLID).
  (2) Homepage nav still on a white strip ABOVE the gradient — sticky nav reserves a 64px row so the
  hero sat below it. Fix: `-mt-16` on the homepage `<main>` pulls the hero up UNDER the transparent
  nav so the gradient spans from y≈0 behind it (DOM: heroTop≈1, navBand 0–65, transparent, white
  wordmark). Verified via preview
  DOM: home top transparent/white wordmark + solid on scroll; /faq top solid dark; /privacy legal
  intact; /login light shadcn; no visible price sitewide. Build green (12 routes).
  COMMITTED + PUSHED 2026-06-22: commit 17086cb "Redesign marketing site" (web/ only, 26 files) →
  origin/main → Vercel production deploy. (.paul/ + web/design-mockups/ gitignored.)
  LAST plan in Phase 40 → UNIFY ran the phase transition (PROJECT/ROADMAP evolved).
40-02 PLAN — autonomous:false (human-verify checkpoint). depends_on 40-01. Task 1: Features +
  HowItWorks restyle to light (token map); NEW RequestQuote.js (gradient CTA card + ContactDialog,
  id="pricing", NO prices) replaces Pricing; page.js restores Nav→Hero→Features→HowItWorks→
  RequestQuote→Footer; DELETE Pricing.js. Task 2: login restyle to light (shadcn Input/Button; auth
  logic untouched); /faq retheme to light + scrub the "How much does it cost?" answer of $300/$20
  (pricing-removal) + bottom CTA mailto→ContactDialog; /privacy retheme to light (legal copy
  untouched). Checkpoint: dev-server review of / + /faq + /privacy + /login + portal-still-dark.
  SCOPE: marketing/public only — DO NOT touch portal/report/three/ or dark tokens. LAST plan →
  UNIFY runs the phase transition (PROJECT/ROADMAP + git commit).

## Loop Position (40-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [40-01 CLOSED 2026-06-21 — landing core redesign shipped + verified; SUMMARY written. Phase 40 = 1/2 plans; 40-02 next]
```
40-01 APPLIED (web): shadcn hand-authored in JSX (button/card/badge/dialog/input/label/textarea +
  lib/utils.cn + components.json; deps class-variance-authority/clsx/tailwind-merge/lucide-react/
  @radix-ui dialog+label+slot/tw-animate-css) — NOT the interactive CLI (Next 16 + Tailwind-v4 + JS).
  globals.css: ADDED iOS light-purple tokens (brand/brand-pressed/brand-foreground/secondary-2/
  periwinkle/sky/ink-900/600/400/paper/card/card-foreground/lavender/line) + `@import "tw-animate-css"`;
  dark --color-* portal tokens UNCHANGED (verified bg#07090e/navy/primary present; /privacy still dark).
  lib/site.js WEB3FORMS_ACCESS_KEY = real key 58f665d7-...e93f7 (user-supplied). ContactDialog
  (name+email+optional message → POST api.web3forms.com → emails tzheng846@gmail.com); LIVE test submit
  returned success. Hero rebuilt = full-bleed gradient (isolate; fixed a -z-10 behind-bg bug found in
  preview) + sky "analysis." accent + floating SampleChart card (purple line) straddling the fold; Nav
  glass-over-gradient→solid-lavender on scroll (verified both states); Footer light; page.js trimmed to
  Nav+Hero+Footer (Features/HowItWorks/Pricing files kept on disk, imports dropped → restored in 40-02).
  Build green (12 routes). Verified via preview DOM (screenshot tool mis-scaled). Deviation: hand-authored
  shadcn (canonical files) instead of CLI. NOT committed (user runs git). NEXT: /paul:unify to close 40-01.
40-01 PLAN — autonomous:false (human-verify checkpoint). Web marketing redesign to Template B
  (immersive purple gradient). Task 1: shadcn init (tsx:false, Tailwind v4 CSS-first) + ADD iOS
  light-purple tokens to globals.css (namespaced; dark --color-* tokens preserved for the portal) +
  primitives (button/card/badge/dialog/input/label/textarea) + lib/site.js WEB3FORMS_ACCESS_KEY
  (placeholder, USER to supply). Task 2: ContactDialog ("Request a quote" name+email+message →
  Web3Forms POST → emails tzheng846@gmail.com); Hero rebuilt to full-bleed gradient + floating
  SampleChart card (primary CTA = ContactDialog); Nav glass-over-gradient→solid-light on scroll
  (CTA = ContactDialog); SampleChart recolored purple; Footer light; page.js trimmed to the
  redesigned pieces (Features/HowItWorks/Pricing files kept, restored in 40-02). Checkpoint:
  dev-server visual verify + confirm portal untouched + USER creates the Web3Forms key. SCOPE:
  marketing only — DO NOT touch web/app/app/**, web/components/portal/**, report/**, three/**, or
  existing dark tokens. 40-02 (next): Features, HowItWorks, Pricing→"Request a quote" section,
  login restyle, faq/privacy retheme.

## Loop Position (39-05)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [39-05 CLOSED 2026-06-20 — segmentation overlay (Advanced velocity chart); export green; SUMMARY written; device verify DEFERRED]
```
39-05 SHIPPED (code, swimnetics-mobile): (1) VelocityChart.js — `cycleBoundaries` prop (default []),
  `cycle` color in light+dark CHART_COLORS, faint dashed zoom-aware vertical lines drawn between the
  zero-line and the Polyline (under the trace); PanResponder/cursor/marker/zoom untouched.
  (2) ReportCardScreen.js — `cycleBoundaries` from metrics.cycles start/end_idx ÷100 ONLY when
  view==='advanced'; passed to the chart; "Dashed lines = detected stroke cycles. Segmentation is
  experimental." caption (guarded .length>0) + chartCaption style. `npx expo export --platform ios`
  exit 0 (1056 modules). Self-review: Simple/no-cycle → no overlay/caption (AC-2); zoom filter
  tMin/tMax (AC-3). Device checks appended to 39-TEST-PLAN.md. NOT committed (mobile repo local-only,
  no remote; user runs git). SUMMARY: 39-05-SUMMARY.md. Decisions: dashed lines (not shading);
  ReportCard Advanced only (RecordScreen parity = noted follow-up). REMAINING in Phase 39: 39-06 ONLY
  (DU4 flag abnormal + ignore — needs abnormal-definition + ignore-persistence decision before planning).

39-05 PLAN — autonomous:true, 2 auto tasks (mobile repo, front-end only). [DU7]
  Draw the segmenter's cycle boundaries on the session velocity chart from metrics_json.cycles
  (start_idx/end_idx @100Hz → idx/100 = boundary time; verified vs the existing CSV-export reuse +
  `time = i/100`). (1) VelocityChart gains `cycleBoundaries` prop → faint dashed vertical lines
  drawn UNDER the trace, zoom-aware (tMin/tMax filter), new `cycle` color in light+dark
  CHART_COLORS; PanResponder/cursor/marker/zoom untouched. (2) ReportCardScreen computes boundary
  times ONLY when view==='advanced', passes them in, adds an honest "experimental" caption.
  SCOPE LIMITS: ReportCard Advanced ONLY (NOT RecordScreen — fragile 950-line file, note parity
  follow-up); lines only (no shading/labels); NO self-relabel + NO analysis-scope change (deferred
  larger future). Device verify DEFERRED → end-of-phase EAS build (39-TEST-PLAN). After this →
  Phase 39 remaining = 39-06 only (DU4 flag abnormal + ignore; needs abnormal-definition +
  ignore-persistence decision).

## Loop Position (39-04)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [39-04 CLOSED 2026-06-19 — Record tab button (frosted pill + detached circle); export green]
```
39-04 SHIPPED (DU6): TabBar.js rewritten — frosted lavender pill (Dashboard/Team/History) + detached
  purple Record circle (no label; solid pill, NO expo-blur → build-free). Mock-confirmed (purple/no
  label; solid lavender). Nav structure untouched (RootTabs unchanged). export green. Minor polish
  note: AiBubble + Record circle both bottom-right may look stacked. SUMMARY: 39-04-SUMMARY.md.
  REMAINING in Phase 39: 39-05 (DU7 segmentation overlay — confirm scope), 39-06 (DU4 flag/ignore —
  needs decision).

## Loop Position (39-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [39-03 CLOSED 2026-06-19 — pillar explainer + remove impulse + athlete limit + trend relabel; export green; ratings 26]
```
39-03 SHIPPED: DU1 remove impulse (ratings.py PILLARS stroke_length + ReportCard/Record advanced
  grids); DU2 long-press metric explainer (PillarCards Modal: label + explanation + unit); DU3 athlete
  limit "N / {teams.swimmer_limit ?? 20} swimmers" (AthletesScreen, supabase fetch); bug#2 trend chip
  relabeled "Up/Down/Same vs last" (band=absolute vs trend=vs-previous clarity). iOS export green;
  pytest test_ratings 26 passed. ⚠ DEPLOY: ratings.py → Railway (user push) for the pillar-expand
  impulse removal (advanced-grid removal is client-side/immediate). SUMMARY: 39-03-SUMMARY.md.
  BUG #4 (teams RLS) RESOLVED — user ran patch_05 successfully. NEXT: 39-04 (DU6 Record tab button,
  needs mock), 39-05 (DU7 overlay), or 39-06 (DU4 flag/ignore, needs decision).

## Loop Position (39-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [39-02 CLOSED 2026-06-19 — DU5 history star + delete-only-in-session; export green; verify DEFERRED]
```
39-02 SHIPPED (DU5): SessionHistoryScreen — removed SwipeableRow + Animated/PanResponder/Alert/
  TouchableOpacity/useRef imports + handleDelete; each row has a tappable star button (handleStar);
  ReportCardScreen — 🗑 delete button next to star → confirmDelete (Alert) → DELETE /sessions → goBack
  (+ deleteGlyph style). Delete now only inside a session. Export green. SUMMARY: 39-02-SUMMARY.md.
  DU4 (flag abnormal + ignore) split OUT to a new plan (39-06) — needs abnormal-definition + ignore-
  persistence decision. NEXT: pick a plan — 39-03 (DU2 long-press explainer + DU1 remove impulse + DU3
  athlete limit + fold bug #2 trend-chip clarify), 39-04 (DU6 Record tab button, needs mock), 39-05
  (DU7 segmentation overlay), or 39-06 (DU4 flag/ignore, needs decision).

## Current Position (39 — newest)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 39 (Redesign Fixes & UX Iteration) — Planning (39-01 created, awaiting approval; NOT applied)
Plan: 39-01 (4 bug fixes) created 2026-06-19, autonomous:false (band-vs-trend decision). DO NOT APPLY
  until user says so.
Status: Investigated + LOCATED the 4 on-device-test bugs (read-only, no edits):
  • BUG 3 CRASH (biggest): AthleteDetailScreen.js:149 `(p.band && rc[p.band])` — `rc` is undeclared
    (the `const rc = colors` line was dropped in the 38-04 self-review when BAND_COLOR was added; this
    line was missed). ReferenceError when rendering pillars → any TESTED athlete crashes on open
    (untested athletes have no pillars → skip the map → no crash). Metro bundles fine (runtime error).
    Fix: `rc[p.band]` → `BAND_COLOR[p.band]` (map already at line 18).
  • BUG 1 units: PillarCards.js expand view renders /ratings values + units raw (no unit prop, no
    conversion); ReportCardScreen mounts PillarCards without passing `unit`. Fix: pass unit + convert
    m→yd (×1.09361) / m·s→yd·s for distance+velocity metrics; leave spm/%/s.
  • BUG 2 declined-vs-green: ratings.py `_trend` (155) is CORRECT (direction-aware ±5% deadband).
    band=absolute (bar/score), trend=vs-previous (chip) — independent by Phase-36 design. green+declined
    is valid (down vs last, still good). → UI-clarity DECISION (relabel/separate), not a logic fix.
  • BUG 4 team-name not persisting: `teams` RLS = SELECT only (schema.sql ~78); supabase update
    silently blocked. Fix: patch_05 UPDATE policy (USING+WITH CHECK id=current_team_id()), user-applied.
  39-01 = these 4. The 7 DESIGN UPDATES are scoped to 39-02…05 (see ROADMAP Phase 39) with locations:
  DU1 remove impulse (ratings.py PILLARS); DU2 long-press metric explainer (PillarCards; explanation+
  unit already in payload); DU3 athlete-limit display (AthletesScreen; teams.swimmer_limit default 20);
  DU4 flag abnormal in lists + ignore (SessionHistory/AthleteDetail + sessions flag/ignore column);
  DU5 history star-button + delete-only-in-session + confirm (SessionHistory/ReportCard, remove swipe);
  DU6 Record tab button like the iOS-News+ reference image (TabBar — needs mock); DU7 advanced
  segmentation overlay on the velocity chart from metrics_json.cycles (VelocityChart/ReportCard;
  relabel/scope = larger future).
Last activity: 2026-06-19 — Phase 39 opened; 39-01-PLAN created (bugs located, no source edited).

## Loop Position (39-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [39-01 CLOSED 2026-06-19 — crash + units + RLS patch; #2 → 39-03; export green; verify DEFERRED]
```
39-01 SHIPPED: (1) AthleteDetailScreen.js:149 rc→BAND_COLOR (CRASH fixed); (2) PillarCards.js unit
  prop + displayMetric (m→yd / m·s→yd·s) + ReportCard passes unit (pillar expand respects units);
  (3) supabase/patch_05_teams_update_rls.sql (teams UPDATE policy, USER-APPLIED). Bug #2 (band vs
  trend) = correct-by-design → UI clarify folded into 39-03. Export green (3.2MB). SUMMARY +
  39-TEST-PLAN.md written. NEXT: 39-02 (DU5 — history star button + delete-only-in-session + confirm;
  remove swipe).

## Current Position (38 — newest)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 38 (Mobile UI/UX Redesign) — ✅ CODE-COMPLETE (6/6 plans; all export-green; device verify → one EAS build)
Plan: 38-01/02/03/04/05/06 ✅ code-complete. Phase done pending the single end-of-phase EAS build.
38-06 COMPLETE (2026-06-19): VelocityChart THEME-AWARE (dark prop + CHART_COLORS light/dark);
  FINDING A RESOLVED (ReportCard+Record read global m/yd UnitsContext; local toggles retired);
  RecordingConfig rewritten to light + ATHLETE PICKER (seeded from params or pick-from-list when
  cold; Start gated on athlete+connected); RecordScreen DARK/IMMERSIVE (bg=brand text purple, white
  cards float, cyan VelocityChart via dark; BLE/camera logic UNTOUCHED — color-only); VideoOverlay
  restyled light; FINDING B done (Devices + Diagnostics light, verdict colors mapped). Added
  dangerOnDark token. Export green (3.2MB). SUMMARY: 38-06-SUMMARY.md.

PHASE 38 DONE (code): all 6 plans export-green; cross-plan review clean (nav/tokens/contracts);
  Findings A+B resolved. NATIVE DEPS added this phase: @react-navigation/bottom-tabs (38-01) +
  expo-crypto (38-03). NEXT (user-owned): ONE EAS dev build (must include expo-crypto) → run the
  full 38-TEST-PLAN.md checklist; then commit/push (mobile repo has NO remote per prior notes —
  local-only). OPEN FOLLOW-UPS: per-screen StatusBar light on the dark record screen; teams UPDATE
  RLS for Settings team-name persistence; confirm WEB_BASE domain for report links; coach-name
  column (Settings shows email read-only); VelocityChart restyle already done.
38-06 DESIGN LOCKED (2026-06-19, mock+ask): (1) RecordingConfigScreen → light + ADD athlete picker
  (pre-filled from athlete launch; pick-from-list when cold from the Record island) + stroke/device/
  name + "Record with video" toggle; (2) RecordScreen ACTIVE = DARK/IMMERSIVE (timer + rec dot +
  camera preview + live trace + Stop); (3) VideoOverlayScreen restyle; (4) shared VelocityChart
  restyle. PLUS review findings: (A) wire UnitsContext m/yd into Record+ReportCard+VelocityChart
  (replace local metric/imperial toggles; map m↔metric, yd↔imperial); (B) restyle DevicesScreen +
  DiagnosticsScreen. Build as ONE focused pass (units span 3 files; RecordScreen ~950 lines BLE/
  camera = fragile, don't split). After 38-06 → phase CODE-COMPLETE → one EAS build covers all
  38-TEST-PLAN device checks (incl. expo-crypto).
38-05 COMPLETE (2026-06-19): CompareScreen.js (replaced stub) — fetches 2 sessions' meta (supabase)
  + both /sessions/{id}/ratings; orders earlier→later; per-pillar verdict from 0–100 score delta
  (±5 deadband); ADAPTIVE labels (same athlete = Better/No change/Worse; different = Higher/Even/
  Lower); colored chips + tally; tap pillar → expand primary metric A→B; loading/error/unknown
  states. Reuses Phase-36 ratings (no new backend/dep). Entry points wired in 38-04. Export green.
  SUMMARY: 38-05-SUMMARY.md.
38-04 COMPLETE (2026-06-19): SessionHistoryScreen → TEAM-WIDE feed (sessions+athletes(name),
  RLS-scoped; stroke filter chips; swipe star/delete; Compare select-mode → pick 2 → navigate
  Compare; legacy athleteId honored) + PillarCards.js dark→light (theme aliased `ui` to dodge the
  payload-`colors` shadow; marker dark-on-band) + ReportCardScreen chrome restyled dark→light +
  session-anchored AiBubble (on-demand, NO auto card) + "⇄ Compare to previous" (queries prior
  session; hidden on first) + SessionSummaryCard/DataQualityCard → light + CompareScreen STUB on
  root stack (real view = 38-05). Export green (3.2MB). SUMMARY: 38-04-SUMMARY.md.

CROSS-PLAN REVIEW (2026-06-19, user-requested, after 38-04): ✅ all 9 navigate() targets registered
  in RootTabs — no missing routes/name clashes; tokens + API contracts consistent across plans.
  TWO findings folded into 38-06 (must resolve before phase "done"): (A) UNITS CLASH — Settings'
  global m/yd UnitsContext is NOT consumed by ReportCard/Record (they keep local metric/imperial
  state); Settings toggle has no effect there → wire useUnits into Record/ReportCard/VelocityChart.
  (B) RESTYLE COVERAGE GAP — DevicesScreen + DiagnosticsScreen (reached from Settings) + the record
  screens + VelocityChart still render dark → 38-06. Minor: Dashboard band fallback `|| colors`
  (camel) safe-in-practice; relDate/relTested duplicated (cosmetic). Full list in 38-TEST-PLAN.md
  "Cross-plan review". NEXT = 38-05 Compare (mock+ask, then build).
Status (38-03 just shipped): Team tab = labeled pillar TABLE (reads /team/overview; icon-header
  legend; rows = name + last-tested + 4 band dots, never-tested→dashes; (+) add athlete) + NEW
  AthleteDetailScreen full hub (Send report = supabase reports insert + RN Share + /report/{token};
  Record → RecordingConfig preselected; pillar band cards; session list → ReportCard; ⋮ edit
  name+head-waist / delete athlete — all supabase, athletes RLS is FOR ALL). Added WEB_BASE to
  config (⚠ confirm domain) + registered AthleteDetail on root stack. ADDED expo-crypto = FIRST
  NATIVE DEP of the phase → forces the one end-of-phase build (38-03+ won't run on the pre-38-03
  dev client; flagged in 38-TEST-PLAN build reqs). SELF-REVIEW BUG FIXED: snake_case bands
  (needs_work) vs camelCase tokens (needsWork) → added BAND_FALLBACK/BAND_COLOR maps (Team table
  also prefers payload rating_colors). Contracts checked first (reports schema/RLS, token=randomUUID,
  athletes FOR ALL delete, teams SELECT-only confirms 38-02 caveat, REPORT_METRICS keys). SUMMARY:
  38-03-SUMMARY.md; device checks in 38-TEST-PLAN.md.
  NEXT: 38-04 — DESIGN LOCKED 2026-06-19 (mock+ask done): (1) History tab = TEAM-WIDE session feed
  (all athletes newest-first, supabase sessions+athletes(name), RLS team-scoped; stroke filter chips;
  Compare multi-select → pick 2 → Compare) — replaces the per-athlete-only screen (athleteId param
  still honored if passed). (2) Session-details restyle: ReportCardScreen + the RN PillarCards
  component (currently dark-themed #1a1a1a) → light tokens; keep Simple/Advanced. (3) AI = ON-DEMAND
  only (mount AiBubble anchored to the session; NO auto-insight card, no per-open model call). (4)
  "Compare to previous" button → Compare. Register a Compare SCREEN STUB on the root stack (filled by
  38-05). Build directly (no further design pause). NOTE: ReportCard + PillarCards restyle is the
  large piece; expo-crypto already in tree so 38-04 stays build-free re: new native deps.

Prior status (38-02): Dashboard team-health (/team/overview) + Settings + ambient AI
  (today's-focus card daily-cached via SecureStore + floating bubble + CoachChatSheet). Build-free
  (JS-only). Deviations: coach email read-only (coaches has no name col); team-name edit persistence
  pending a teams UPDATE RLS policy; units pref persisted only (chart consumption deferred). New
  files: lib/apiFetch.js, ui/PillarIcons.js, ai/CoachChatSheet.js, ai/AiBubble.js (optionally
  controlled), context/UnitsContext.js, screens/SettingsScreen.js; DashboardScreen rewritten; tokens
  +scrim. SUMMARY: 38-02-SUMMARY.md; device checks in 38-TEST-PLAN.md.
  NEXT: 38-03 Team tab — DESIGN LOCKED 2026-06-19 (mock+ask done): labeled pillar TABLE (icon-header
  legend; rows = name + last-tested + 4 band-dots from /team/overview athletes[]; never-tested
  flagged with dashes) + (+) add athlete + NEW AthleteDetail full-hub screen (Send report button +
  pillar bands + session list → ReportCard + ⋮ overflow edit-fields/delete). Streamlined per-athlete
  parent report = supabase reports row + existing /report/{token} (mailto/copy). BEFORE building:
  contract-check the reports table schema + athlete delete path (DELETE endpoint vs supabase) +
  how web builds the report token. Then write 38-03-PLAN + build (no further design pause).

Prior status (38-01): PLAN was autonomous:false (palette human-verify). Full iOS
  redesign in the swimnetics-mobile repo, driven by the user's wireframe. Mobile-repo-only —
  no backend changes (team-level AI context already exists via Phase 33-02 TEAM_TOOLS; parent
  reports write via supabase-js + existing /report/{token}; compare = client-side pillar diff).
  38-01 = 3 auto tasks + checkpoint: (1) src/theme/tokens.js (LOCKED light palette below) +
  UI primitives (AppText, Screen, Card, Button, SectionHeader); (2) @react-navigation/bottom-tabs
  (JS-only, no native rebuild) + 4 SVG TabIcons + custom TabBar with Record as a detached "island"
  + RootTabs (4 tabs, each a nested native-stack so details push within the tab) + DashboardScreen
  stub + App.js rewire; (3) LoginScreen restyle to tokens. Verify on the EXISTING dev client (no
  paid EAS build needed).
  PALETTE LOCKED (user, 2026-06-19, approved via 2 mockup rounds) — LIGHT theme (flips the current
  dark app), light-only for now: text #2c0735, bg #fbfbfe, surface #fff, surfaceAlt #f4f1fb
  (lavender), border #e8e4f2, primary #4e148c (SOLID-fill buttons), secondary #613dc1, accent
  #97dffc (AI surfaces ONLY — restrained), periwinkle #858ae3, textSecondary #6e5a78, textMuted
  #9b8ba6; bands good/ok/needsWork #2d9e5f/#d4860a/#c0392b (from API payload). ROSTER/ATHLETE-LIST PATTERN
  (carry to 38-02/03): NO avatar icon. TEAM TAB roster = LABELED TABLE (one row per athlete;
  columns = 4 pillars with ICON header = legend; cells = band dots; row tap → athlete detail w/
  full PillarCards + edit + send report; header-tap-sort = nice-to-have). DASHBOARD needs-attention
  = 2-col SUMMARY cards (critical-factors: name + derived overall score + weakest pillar icon+band;
  tap → detail). Pillars labeled by ICONS (Speed=gauge, Length=ruler, Consistency=wave-sine,
  Endurance=battery). Overall score + weakest = CLIENT-derived from /team/overview pillars (no
  backend change). See 38-01-PLAN LOCKED palette section.
  DECISIONS (user, 2026-06-19, AskUserQuestion ×3): team-health Dashboard; AI = inline tip cards
  + global collapsed bubble, daily-cached "today's focus"; compare from BOTH entry points,
  pillar better/no-change/worse (no number dumps); streamlined per-athlete parent reports;
  design-system-first build. Phase scoped into 6 vertical slices (38-01…38-06; see ROADMAP).
  ASSUMPTIONS held: BLE/recording logic unchanged (reskin only); Record-with-Video retained;
  iPhone-only; velocity chart stays on session details.
Last activity: 2026-06-19 — Phase 38 opened; 38-01-PLAN created (after 3 rounds of clarifying Qs).

## Loop Position (38-06)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [38-06 code-complete 2026-06-19 — record flow dark + units + Devices/Diagnostics; export green. PHASE 38 CODE-COMPLETE]
```
(38-06 built from locked design; Findings A+B resolved. SUMMARY: 38-06-SUMMARY.md.)

## Loop Position (38-05)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [38-05 code-complete 2026-06-19 — Compare pillar-delta view; export green; verify DEFERRED]
```

## Loop Position (38-04)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [38-04 code-complete 2026-06-19 — History team-wide + ReportCard restyle + compare entry + AI bubble; export green; verify DEFERRED]
```
(38-04 built directly from locked design; cross-plan review done → findings A/B → 38-06. SUMMARY: 38-04-SUMMARY.md.)

## Loop Position (38-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [38-03 code-complete 2026-06-19 — Team table + athlete hub + reports; export green; verify DEFERRED]
```
(38-03 built directly from locked design — no separate PLAN file; SUMMARY: 38-03-SUMMARY.md.)

## Loop Position (38-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [38-02 code-complete 2026-06-19 — Dashboard+Settings+ambient AI; export green; verify DEFERRED]
```

## Loop Position (38-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [38-01 code-complete 2026-06-19 — export green; device verify DEFERRED to phase end]
```
38-01 SHIPPED (code, swimnetics-mobile): theme/tokens.js (LOCKED light palette) + index.js;
  ui/ AppText, Screen, Card, Button (solid-purple primary; pressed tints in tokens — zero raw
  hex), SectionHeader, TabIcons (SVG), TabBar (Record raised island); navigation/RootTabs.js
  (bottom tabs Dashboard/Team/RecordingConfig=Record island/SessionHistory wrapped in a root
  stack for full-screen details Record/VideoOverlay/ReportCard/Devices/Diagnostics — tab routes
  reuse existing navigate() names so nothing breaks); DashboardScreen stub; App.js rewired
  (SafeAreaProvider + light StatusBar); LoginScreen restyled (auth logic unchanged). Added
  @react-navigation/bottom-tabs (JS-only — no native build). `expo export --platform ios` exits 0
  (1040 modules). SUMMARY: 38-01-SUMMARY.md. Device checks → 38-TEST-PLAN.md. NOT committed (user runs git).

WORKFLOW (user, 2026-06-19): EAS builds expensive → DEFER ALL on-device testing to phase end.
  Per-plan human-verify checkpoints become deferred items in 38-TEST-PLAN.md. Each plan verified
  at code level (expo export green + self-review + cross-plan contract checks). Cadence: build
  plans pausing ONLY for design forks (mock + ask, like the roster table); never stop for testing.
  End-of-phase deliverables: consolidated device test list + cross-plan self-review. NOTE: 38-01
  is JS-only (no new native dep) — flag any later plan that adds native code (forces the build).

## Current Position (37 — newest)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 37 (Team Coach Dashboard) — In progress (1/2 plans done; 37-02 created, awaiting approval)
Plan: 37-02 (WEB UI) created, awaiting approval; 37-01 (BACKEND) ✅ CLOSED 2026-06-18
Status (37-02): PLAN ready for APPLY — autonomous:false (human-verify checkpoint). Rebuild
  web/app/app/page.js from the raw-numbers athlete grid into a 4-section team-health home driven
  by ONE apiFetch("/team/overview") call: TeamPulse (counts + per-pillar band-distribution bars),
  NeedsAttention (reason chips: needs_work/declined/stale/never_tested → links to filtered session
  list), RecentActivity (newest sessions, relative dates → link to report card), color-banded
  RosterBandCard grid (4 pillar band-dots/athlete; no-session → "No sessions yet"). 4 NEW
  presentational components + page rewrite. Colors ALWAYS from payload.rating_colors (PillarCards
  convention). Web-only; no backend/layout/other-page/dep changes; AthleteCard.js becomes unused
  (leave file, drop the import only). Athlete card link stays /app/sessions?athlete= (keep tight,
  no new detail page). VERIFY: endpoint must be reachable — push 37-01 api.py to Railway OR local
  uvicorn + NEXT_PUBLIC_API_URL=localhost (36-02 pattern, revert after). NEXT after approval: APPLY.
Prior status (37-01): PLAN ready for APPLY — autonomous:true, 2 auto tasks. (1) ratings.summarize_team
  pure helper (STALE_DAYS=14; band distribution per PILLARS + needs_attention reasons —
  needs_work/declined from non-provisional pillars, stale via date diff, never_tested; sorted
  reason-count desc/name; takes `today` as a param, never reads the clock) + test_ratings cases.
  (2) GET /team/overview in api.py (auth + coach-scoped like /sessions/{id}/ratings; one athletes +
  one sessions query; rate each athlete's LATEST session via the SAME reuse path — stroke fallback,
  flatten session+data_quality, prior same-stroke → select_baseline "previous" → rate_session —
  projected to compact pillars {key,label,band,trend,score,provisional}; recent[] cap 10 with NO
  per-session verdict to keep compute O(athletes); tested_this_week within 7d; rating_colors from
  source) + test_api TestTeamOverview (401/shape/coach-scope/no-session/DB-fail-5xx). LOCKED payload
  in the plan's DESIGN SPEC (37-02 + iOS build against it). Backend only; ratings PILLARS/THRESHOLDS/
  rate_session/select_baseline + /process + metrics.py + web/** UNTOUCHED. No new dep. NEXT: 37-02
  web dashboard UI (4 sections) reading the endpoint.
Last activity: 2026-06-18 — Phase 37 opened; 37-01-PLAN created.

## Loop Position (37-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ○        ○     [37-02 created, awaiting approval — web dashboard UI, autonomous:false]
```

## Loop Position (37-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [37-01 loop CLOSED 2026-06-18 — summarize_team + GET /team/overview + tests; SUMMARY written]
```
37-01 SHIPPED (code): ratings.summarize_team (pure — STALE_DAYS=14 + _days_since; band
  distribution per PILLARS + needs_attention reasons [needs_work/declined from NON-provisional
  pillars only, stale via injected today, never_tested; clean athletes omitted; sorted
  reason-count desc/name]; takes `today` as a param — clock-free) + GET /team/overview in api.py
  (auth + coach lookup identical to /sessions/{id}/ratings; 1 athletes + 1 sessions query,
  coach-scoped, newest-first; rates each athlete's LATEST session via the SAME reuse path →
  compact pillars {key,label,band,trend,score,provisional}; recent[] cap 10 NO verdict; defense-
  in-depth drop of out-of-roster sessions; tested_this_week within 7d; rating_colors from source)
  + tests (test_ratings +6 TestSummarizeTeam, test_api +4 TestTeamOverview — renamed fake to
  _team_overview_admin to avoid colliding with the chat-team _team_admin). Suite 103 (was 93).
  No new dep; git diff = api.py + ratings.py + 2 test files ONLY (no web/**, no requirements.txt).
  LOCKED payload contract in 37-01-PLAN DESIGN SPEC (37-02 + iOS build against it). NOT committed
  (user runs git). DEPLOY: api.py → Railway auto-deploys on push to main (user-owned) — needed
  before web verifies vs prod, or verify vs local uvicorn (Phase-36 pattern). SUMMARY: 37-01-SUMMARY.md.
  NEXT: 37-02 web dashboard UI (4 sections) reading the endpoint.

## Current Position (36)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 36 (Coach-Friendly Metric Ratings) — Planning (0/2 plans + iOS-later; 36-01 created)
Plan: 36-01 (BACKEND) created, awaiting approval
Status: 36-01 PLAN ready for APPLY — autonomous:true, 3 auto tasks. Build ratings.py (pure:
  4 pillars Speed/Stroke-Length/Consistency/Endurance; primary metric drives an absolute band;
  hybrid + direction-aware trend vs baseline with ±5% deadband; data-quality gating —
  segmentation_reliable=False → provisional, non-breaststroke → band="unknown"/trend-only, kick
  excluded, NaN-safe; pluggable select_baseline mode="previous" w/ recent_avg/first stubs) +
  GET /sessions/{id}/ratings (auth+ownership, baseline=athlete's previous same-stroke session) +
  RATINGS-SPEC.md (artifact iOS implements from) + tests (test_ratings.py + api case). Breaststroke
  bands seeded from app.py:56 _METRIC_RANGES (DRAFT — coach review owed, like drills.py). Backend
  only; /process + metrics.py compute + clients untouched. No new dep. DECISIONS (user, 2026-06-17,
  AskUserQuestion ×2): hybrid band+trend; 4 headline pillars (tempo/glide/start become contributing
  metrics or advanced view); hide numbers, expand → contributing metrics + explanation; trend vs
  last session BUT coded pluggable for future user-chosen scope; backend shared source of truth;
  non-breast = trend-only+provisional. Payload shape locked in the plan's DESIGN SPEC. NEXT: 36-02
  web pillar cards after 36-01 ships the payload; iOS mirrors later (own phase, from RATINGS-SPEC.md).
Last activity: 2026-06-17 — Phase 36 opened; 36-01-PLAN created.

## Loop Position (36-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [36-02 loop CLOSED 2026-06-17 — web pillar cards verified vs local backend; SUMMARY written]
```
36-02 SHIPPED (code): web/components/portal/PillarCards.js (fetches /sessions/{id}/ratings;
  fixed red/amber/green band + marker@score + verdict + trend chip + tap-expand metrics +
  provisional chip; colors from payload, not hard-coded; a11y aria-expanded/controls) +
  sessions/[id]/page.js (Simple=pillars, Advanced=raw MetricGrid+per-cycle). Verified
  end-to-end against a LOCAL uvicorn backend (endpoint not on Railway yet) — real payload,
  no console errors. REVIEW-HARDENING (36-01+02): api.py ratings endpoint .single()+bare-except
  → .limit(1)+data-check + dropped prior-sessions except (DB errors → 5xx, not masked 403/404/
  degraded); +test_backend_failure_surfaces_5xx; PillarCards aria. Suite 93 (was 92). SUMMARY:
  36-02-SUMMARY.md. Phase 36 backend+web COMPLETE (iOS = future own phase).

## Loop Position (36-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [36-01 loop CLOSED 2026-06-17 — ratings.py + endpoint + spec + tests; SUMMARY written]
```
36-01 SHIPPED (code): ratings.py (pure — 4 pillars Speed/Stroke-Length/Consistency/Endurance;
  RATING_COLORS good#2d9e5f/ok#d4860a/needs_work#c0392b; breaststroke DRAFT thresholds w/ score
  anchors; rate_session → band + 0–100 score(higher=better, inverted for lower-better) + direction-
  aware trend(±5%, first_session w/o baseline) + provisional gating + NaN-safe; select_baseline
  previous/first/recent_avg pluggable) + GET /sessions/{id}/ratings (auth+ownership, baseline=prev
  same-stroke session) + RATINGS-SPEC.md (contract for 36-02 web + iOS) + tests (test_ratings.py 24
  + api 5). Suite 92 (was 64). No new dep; /process + metrics.py compute + clients untouched.
  DEVIATIONS: Consistency band = cv_arm_peak_vel only (cv_isi context, no validated ISI threshold);
  select_baseline first/recent_avg fully implemented (plan said stub). DRAFT thresholds — coach
  review owed. DEPLOY: api.py → Railway auto-deploys on push to main (user-owned). NOT committed (user
  runs git). SUMMARY: 36-01-SUMMARY.md. NEXT: 36-02 web pillar cards (reads endpoint); iOS later.

## Loop Position (35-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [35-03 loop CLOSED 2026-06-18 — docs reconciled; Phase 35 COMPLETE; SUMMARY written]
```
35-03 SHIPPED (docs-only): CLAUDE.md (coach.py "only app.py" → shared w/ api.py /coach/chat;
  +/coach/chat +/sessions/{id}/ratings endpoints; +ratings.py/drills.py/roster_metrics.py key-files;
  RATINGS-SPEC pointer) + CODEBASE-AUDIT.md (refresh note; §2 production modules + status fixes; §3
  iOS ratings UI/Diagnostics/Video/PillarCards + iPhone-first; §4.2 +/coach/chat +/ratings, /reports
  flipped ✅; §5.1/§4.5/§8 deploy-drift RESOLVED; NEW Feature Status Ledger WORKING/DEFERRED/DRAFT).
  Grep: 0 false claims left in *.py/*.js (staleness was doc-only). git diff = 2 docs only, no code.
  Phase 35 COMPLETE (35-01 web + 35-02 iOS + 35-03 docs). SUMMARY: 35-03-SUMMARY.md.

## Loop Position (35-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [35-02 loop CLOSED 2026-06-18 — iOS ratings UI + iPad de-scope verified; 2 bugs fixed; recording checks deferred; SUMMARY written]
```
35-02 SHIPPED (code): swimnetics-mobile PillarCards.js (RN mirror of web — band+marker+verdict+
  trend+expand, colors from payload, fetches /sessions/{id}/ratings w/ Bearer) + ReportCardScreen
  Simple/Advanced toggle (Simple=pillars, Advanced=raw cards) + iPad de-scope (app.json
  supportsTablet:false + TARGETED_DEVICE_FAMILY=1 in BOTH pbxproj target configs — authoritative,
  EAS ignores app.json ios block in non-CNG) + version-skew fix (expo install --fix → expo
  ~56.0.12 / expo-video ~56.1.4). VERIFIED on real build+device: launches clean, ratings UI
  (breaststroke) ✓, iPad letterboxed ✓, Diagnostics live ✓. 2 DEVICE BUGS FIXED: (1)
  BleContext.forgetDevice now cancelConnection()+clears state for the connected device (was: only
  dropped from list → LED stayed on); (2) DiagnosticsScreen magnetVerdict flags 0xFF / impossible
  weak+strong combo as "SENSOR NOT RESPONDING" (was: mislabeled unwired AS5600 as "Too weak").
  expo export exit 0 (1013 modules) after every change. GATE 0 (user): PR #5 merged ratings→main,
  Railway live (probe: bogus route 404 vs /ratings 401 = per-route auth, route deployed).
  DEFERRED → post-resolder build (encoder wiring loose): full 34-01 magnet/buffer, 21-02 retrieval,
  26-01 video, 22-02 laptop, + re-verify the 2 fixes — all ONE build. PARITY GAPS (web-only, not
  regressions): AI chat + advanced per-cycle graphs absent on iOS → future iOS-parity phase + 35-03
  note. Mobile repo changes UNCOMMITTED + local-only (no remote). SUMMARY: 35-02-SUMMARY.md.
  NEXT: 35-03 doc reconciliation (no hardware).

## Current Position (35)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 35 (Feature Verification & Doc Reconciliation) — In progress (35-01 ✅ + 35-02 ✅ closed; 35-03 pending)
Plan: 35-01 (WEB) ✅ APPLIED + loop CLOSED 2026-06-17
Status: 35-01 DONE — verified all web features against local dev + prod. ALL WORKING: public
  surfaces (/, /faq, /privacy, /report invalid+valid token), coach portal (login, dashboard 7
  athletes, athletes+Add modal, 20-session list, full session report card w/ data-quality caveats,
  compare mode w/ direction-aware deltas, reports builder+send list), Railway write path (session
  star PATCH→200, reversible), parent report render (count-up deltas + 6 trend charts). 0 web code
  bugs → no web/** changes. ONE issue: prod /coach/chat → 503 "Coaching not configured"
  (ANTHROPIC_API_KEY unset on Railway; api.py:815 guard; frontend handled gracefully) — USER FIXED
  (set key + redeploy + verified). AC-1/2/3/4 all satisfied. Artifacts: 35-01-WEB-FINDINGS.md +
  35-01-SUMMARY.md. 35-02 (iOS device checkpoints, one EAS build) + 35-03 (doc reconciliation)
  deferred to AFTER Phase 36 (the ratings UI change lands in iOS too, so verify iOS after it exists).
Last activity: 2026-06-17 — 35-01 applied + closed; pivoted to Phase 36 (UI ratings) per user.

## Loop Position (35-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [35-01 loop CLOSED 2026-06-17 — all web WORKING; chat config gap fixed by user; SUMMARY written]
```

## Current Position (34)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 34 (Device Diagnostics) — Planning (0/1 plans)
Plan: 34-01 created, awaiting approval
Status: 34-01 PLAN ready for APPLY — surface AS5600/recording/BLE health on-phone so failures
  stop being a black box. Firmware: new STATUS BLE command → 15-byte live packet [0xDD marker,
  status byte, magnet_ok, AGC, raw angle, flags(rec/ready/motor), bufCount, maxSamples]; length
  15 chosen to NOT collide with META(8)/end-marker(1×0xEE)/samples(×7); reuses TX/RX + the
  deferred-flag pattern (no I2C on the BLE task). iOS (separate swimnetics-mobile repo): NEW
  DiagnosticsScreen.js polling STATUS ~2 Hz, plain-English magnet/wiring + record/buffer + link
  cards; entry on DevicesScreen; nav registration in App.js. 2 auto tasks + device human-verify
  checkpoint (autonomous:false — needs paid EAS build + firmware reflash). DECISIONS (user,
  2026-06-16, AskUserQuestion): (1) interface = in-app iOS screen (not desktop tool); (2) scope
  = all three (magnet+wiring, recording/buffer, BLE health). LIKELY ROOT CAUSE already
  identified: magnet not detected (wiring SDA21/SCL22 or magnet alignment); checkpoint step 4
  reproduces & confirms it. Plan: .paul/phases/34-device-diagnostics/34-01-PLAN.md.
Last activity: 2026-06-16 — Phase 34 opened; 34-01-PLAN created.

## Loop Position (34-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [34-01 loop CLOSED 2026-06-16 — STATUS cmd + Diagnostics screen; SUMMARY written. Device checkpoint deferred]
```
34-01 SHIPPED (code): Firmware ESP_32_V5.ino STATUS command — readAgc()/REG_AGC 0x1A,
  STATUS_MARKER 0xDD + STATUS_PACKET_SIZE 15, pendingStatus (RxCallbacks→processPending,
  cleared on disconnect), sendStatus() → 15-byte [0xDD,statusByte,magnet_ok,agc,angle u16,
  flags,bufCount u32,maxSamples u32]; 15 avoids the 8/1/×7 demux. iOS DiagnosticsScreen.js
  (NEW, polls STATUS ~2Hz, parses len==15&&[0]==0xDD only, 3 plain-English cards, freshness,
  unmount cleanup) + DevicesScreen "🔧 Run Diagnostics" + App.js route. Bundle exits 0 (1012
  modules); firmware by structural review (no arduino-cli). PR creation SKIPPED per user
  (PR-TICKETS.md kept). Device checkpoint DEFERRED → later plan.
  GIT (2026-06-16): firmware COMMITTED + PUSHED to origin/main — commit 3bd1d99 "feat: firmware
  STATUS command" (ESP_32_V5.ino only, +58/-1; includes the CW_FORWARD true→false flip). Done
  directly on main (checkout main → ff-pull → add ESP only → push); origin/main...main in sync
  (0 0); verified STATUS code in HEAD:ESP_32_V5.ino. Then switched back to feat/coach-chat-drills
  (so on THAT branch the working firmware shows the pre-STATUS version — STATUS lives on main
  until merged). Still uncommitted (intentional, separate concerns): CLAUDE.md, video_sync.py.
  iOS NOT committed — swimnetics-mobile has NO remote (can't push) + tree mixes Phase 26
  video-overlay WIP; iOS diagnostics will be committed at the deferred EAS device checkpoint.
  SUMMARY: 34-01-SUMMARY.md.
APPLY (2026-06-16): Task 1 — ESP_32_V5.ino: STATUS command. REG_AGC 0x1A + readAgc();
  STATUS_MARKER 0xDD + STATUS_PACKET_SIZE 15; pendingStatus flag (set in RxCallbacks,
  cleared on disconnect, run in processPending); sendStatus() builds+notifies the 15-byte
  packet [0xDD, statusByte, magnet_ok, agc, angle u16, flags(rec/ready/motor), bufCount u32,
  maxSamples u32]; header docs. No arduino-cli locally → structural review (all pieces present,
  ordering OK, no I2C on BLE task). Task 2 — swimnetics-mobile: NEW DiagnosticsScreen.js (polls
  STATUS ~2Hz via 500ms interval, monitors TX, parses only len==15 && [0]==0xDD, magnetVerdict()
  plain-English, 3 cards magnet/buffer/connection, freshness "last status Xs ago", cleanup on
  unmount); DevicesScreen "🔧 Run Diagnostics" button; App.js Diagnostics route. `npx expo export
  --platform ios` exits 0 (1012 modules). Task 4 — PR-TICKETS.md: 2 tickets (A firmware repo w/
  remote, B iOS local-only no-remote), byte-contract table, test steps, copy-paste git/gh cmds,
  EXPLICITLY excludes pre-existing CW_FORWARD/CLAUDE.md/video_sync.py noise from PR A.
  PAUSED at Task 3 human-verify — needs firmware reflash + paid EAS build (EAS-credit gate).
  NOT committed (user runs git; see PR-TICKETS.md). LIKELY DIAGNOSIS for the reported failure:
  magnet not detected at record start (the 10Hz flash→idle path).

## Current Position (33 — active build thread)

Milestone: v0.5 Commercial Foundation (+ go-to-market research)
Phase: 33 (AI Coaching Chat v2) — ✅ COMPLETE (closed 2026-06-16 at 3 plans: 33-01/02/03)
Plan: all three applied + loops closed. Deferred to future (NOT in closed scope): 33-04 semantic
  drill RAG, 33-05 streaming+history+live-verify (carries Phase 31's deferred verify), 33-06 visual
  proof. Code review finding (api.py↔coach.py coupling) verified INVALID + skipped — the coupling is
  the intended shared-prompt design, not a violation; stale CLAUDE.md note already corrected + doc
  now updated with the /coach/chat architecture, roster_metrics.py, drills.py.
Status: 33-02 SHIPPED (code). Team-wide questions answerable: roster_metrics.py (pure:
  latest_per_athlete/rank_athletes/rank_progress/team_summary) + coach.TEAM_TOOLS + 3 coach-scoped
  executors (1 athletes + 1 sessions query/turn, coach_id-filtered, out-of-roster dropped) in the
  shared loop; tools=COACH_TOOLS+TEAM_TOOLS. /coach/chat now returns {reply, data} — structured
  tool results surfaced so a future visual-proof panel/compare deep-link (→ NEW plan 33-05) is
  front-end-only. Kick-ranking declined via guardrail. Suite 54 passed (was 45). No new dep.
  DECISION (user-approved): team tools return athlete NAMES (narrow no-PII exception; coach owns
  roster). DEFERRED: cohort/age/gender + gender schema; dashboard chat entry point; streaming/history (33-04).
  NOT committed yet — user runs git (new branch feat/coach-chat-team-tools).
Prior status note: User wants to improve the AI chatbot; asked about
  LangChain (new to the topic). DECISION (Claude recommendation, user accepted "recommend
  per-feature"): NO LangChain — Anthropic SDK + Supabase cover all four goals; LangChain would
  bury the coach.py prompt for no gain. Phase scoped into 3 plans for all four requested goals
  (user picked all): 33-01 conversational data access via native tool-use (cross-session trends +
  self-serve data access — the keystone); 33-02 coaching knowledge base (prompt-embedded if small,
  Supabase pgvector + Voyage embeddings if large); 33-03 streaming (Anthropic SSE) + persisted
  chat_messages table + web UI + human-verify checkpoint (also covers Phase 31's deferred live
  verify — user chose "build on it, verify together at the end"). 33-01 = 3 auto tasks (coach.py
  tool schemas + prompt hint; api.py bounded tool-use loop with athlete+coach-scoped executors;
  tests). No new dep, no client/iOS change, body contract unchanged. autonomous:true.
Last activity: 2026-06-16 — Phase 33 opened; 33-01-PLAN created.

PRIOR: Phase 32 (SoCal Coach Outreach Research) — ✅ COMPLETE (1/1 plans)
Plan: 32-01 — applied + unified
Status: UNIFY complete. Shipped marketing/socal-coach-outreach.md (4 parts): Part A weighted
  "ideal target club" qualities rubric (8 criteria); Part B scored shortlist of 16 real greater-SoCal
  clubs (OC 4 / LA 4 / SD-Imperial 3(+room) / Inland Empire 4), A/B/C-tiered with coach + contact
  path + why-reach-out; Part C (scope add) club social-presence handles/reach; Part D (scope add)
  media-presence individual coaches — Dave Salo (returning to Irvine Novaquatics 2026) + Mark Schubert
  (The Swim Team, Lake Forest; video-analysis clinic) as SoCal bullseyes, Gary Hall Sr. (The Race Club)
  as out-of-region biomechanics sounding board, Brett Hawke flagged (Enhanced Games reputational
  caution). DECISIONS (user, 2026-06-16): interest-only not selling; all-SoCal-even geo; research +
  rubric only (no email copy — reuse marketing/sales-pitch-email.md later). NOTE: marketing/ is
  gitignored (like sales-pitch-email.md) — local-only, nothing to commit/push. SUMMARY: 32-01-SUMMARY.md.
Last activity: 2026-06-16 — Phase 32 applied + loop closed (PLAN→APPLY→UNIFY). Parts C+D added
  mid-execution per user follow-ups ("social presence", "media-presence coaches").

## Loop Position (33-03)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [33-03 loop CLOSED 2026-06-16 — drill library + tag-matching recommender; 64 tests; SUMMARY written]
```
33-03 SHIPPED (code): drills.py (8 flagship drills + FLAGS taxonomy + flags_from_session +
  match_drills, all pure) + coach.DRILL_TOOLS (recommend_drills) + _exec_recommend_drills in
  the loop (uses in-memory anchor session, no extra query) + _DRILL_HINT guardrail (only-from-
  library, honest "looks solid"). tools = COACH+TEAM+DRILL. Suite 64 (was 54). No new dep.
  DRAFT content — coach review of drill text/thresholds/mapping owed before customer-facing.
  Stacked on feat/coach-chat-team-tools (33-02 NOT merged) → joins that PR. NEXT: 33-04 semantic
  drill RAG (needs embeddings provider/key/cost — user-owned; isolated). Live verify → 33-05.

## Loop Position (33-02)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [33-02 loop CLOSED 2026-06-16 — team tools + visual-proof data hedge; 54 tests; SUMMARY written]
```

## Loop Position (33-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [33-01 loop CLOSED 2026-06-16 — cross-session tool-use shipped, 45 tests; SUMMARY written]
```
APPLY (2026-06-16): Task 1 — coach.py: COACH_TOOLS (list_athlete_sessions, get_session_metrics)
  + _TOOLS_HINT folded into _build_system_prompt (both strokes). Task 2 — api.py: import json,
  MAX_TOOL_ITERS=5, athlete_id added to anchor select, two nested executors scoped to coach_id AND
  athlete_id (foreign session_id → error result, never data), bounded create→tool_use→tool_result
  loop; tools applied in both simple + full branches. Task 3 — tests/test_api.py +5
  (TestCoachChatTools: tool runs+scoped, foreign-session blocked/no-leak, loop terminates under cap,
  backward-compat single call; + test_coach_tools_declared). Full suite 45 passed. No new dep
  (json stdlib; anthropic+supabase present). No web/iOS change; body contract unchanged.
  NOT yet committed — on main; user runs git (branch → commit → PR). Live verify deferred to 33-03.

## Loop Position (32-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [32-01 loop CLOSED 2026-06-16 — marketing/socal-coach-outreach.md shipped]
```
APPLY+UNIFY (2026-06-16): Task 1 — Part A weighted qualities rubric (8 criteria: mid-sized roster,
  national group, open-to-tech, accessible decision-maker, pedigree, year-round gate, reachable
  coach, demo feasibility; A/B/C scoring; key insight = mid-sized > mega-club for a first interest
  email). Task 2 — Part B 16-club shortlist (verified coaches: NCA=Jeff Pease coach-owned, RSD=Joe
  Benjamin national-group lead, Seaport=Paul Folts; rest flagged unverified). Scope adds: Part C
  social handles (Rose Bowl ~2.9k, North Coast ~1.4k, Circle City ~850 strongest); Part D media
  coaches (Salo→NOVA, Schubert). HTTP 403 on swimstandards SI page → pivoted to WebSearch/SwimCloud.
  No code/email sent. marketing/ gitignored (local-only).

PRIOR ACTIVE (parallel, paused): Phase 31 (AI Coaching Chat) — PLAN 31-01 applied.
Status: PLAN created. Add Claude API coaching chat to web + backend (iOS → follow-up 31-02),
  mirroring the Streamlit demo (coach.py) convention. DECISIONS (user, 2026-06-15):
  (1) sequence = backend + web first, iOS later; (2) context source = server fetches by
  session_id (client sends {session_id, messages, simple?}; backend rebuilds the exact
  coach.py prompt from stored metrics_json — no PII, no client-injected data); (3) response =
  non-streaming JSON {reply}; (4) "guardrail" = TOPICAL/SAFETY scoping (what the AI can/can't
  answer), NOT a usage cap — no usage limit for now. New endpoint POST /coach/chat in api.py
  (auth + ownership before any model call); guardrails block added to coach._build_system_prompt
  (shared with Streamlit). anthropic already in requirements.txt (no new Railway dep). Model =
  claude-haiku-4-5 (coach.MODEL). Web CoachChat.js on /app/sessions/[id]. 3 auto tasks +
  human-verify checkpoint (autonomous:false). DEPLOY user-owned: set ANTHROPIC_API_KEY in Railway.
Last activity: 2026-06-15 — Phase 31 PLAN 31-01 created (.paul/phases/31-ai-coaching-chat/31-01-PLAN.md).

## Loop Position (31-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ◐        ○     [31-01 APPLY: Tasks 1-3 done + verified; paused at human-verify checkpoint]
```
APPLY progress (2026-06-15): Task 1 — coach._GUARDRAILS added + folded into _build_system_prompt
  (both strokes); POST /coach/chat in api.py (auth + ownership BEFORE model call; rebuilds prompt
  from stored metrics_json; t_peak_s = peak_idx/100; simple-mode preamble + guardrails;
  non-streaming; 401/400/403/404/503/502 mapped). Task 2 — tests/test_api.py +8 (/coach/chat) +
  guardrail unit test; full suite 40 passed. Task 3 — web/components/portal/CoachChat.js +
  mounted on sessions/[id] (gated isAnalyticsReady, simple follows view toggle); next build green
  (12/12). PAUSED at Task 4 human-verify (needs ANTHROPIC_API_KEY on backend + signed-in coach).

PRIOR: Phase 30 of 30 (Website Copy Polish) — ✅ COMPLETE 2026-06-15 (loop closed, approved)
Plan: 30-01 — applied; human-verify checkpoint approved
Status: UNIFY complete. Marketing site (web/) retuned (CODE; deploy USER-OWNED — Vercel
  auto-deploys on push to main): (1) concise jargon-free copy across Hero/HowItWorks/
  Features/SampleChart/Pricing (no encoder/270/server-side/pipeline); (2) interactive
  chart lifted above the fold + Recharts Tooltip showing m/s on hover + glide marker and
  dead trough code removed (arm-pull kept); (3) sample value on each metric card (34 spm,
  1.6 m, 8%, ±5%, 22%, 6.4 s @ 15 m); (4) WaveMark deleted, text-only "SWIMNETICS"
  wordmark in all 5 sites (Nav/Footer/login/portal/report); (5) contact email → info@
  swimnetics.com (6 spots incl. faq/privacy CONTACT_EMAIL const). CHECKPOINT scope adds
  (user, 2026-06-15): NEW Hero — headline "Stroke-level analysis." + "research-grade lab.
  Record, review, analyze" subtext (eyebrow+CTAs kept); whole Features block moved
  directly under the chart → order Hero → Chart → Features → HowItWorks → Pricing.
  Build green (12/12 static pages); preview verified, zero console errors; hover tooltip
  confirmed ("2.70 s / Speed : 0.99 m/s"). Left as-is per user: SampleChart intro line
  ("dips...coaching conversation starts"). SUMMARY: 30-01-SUMMARY.md.
Last activity: 2026-06-15 — Phase 30 applied + loop closed; checkpoint approved.

## Loop Position (30-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [30-01 loop CLOSED 2026-06-15 — approved; deploy user-owned]
```

PRIOR: Phase 29 of 29 (Marketing Content) — ✅ COMPLETE 2026-06-14 (loop closed, approved)
Plan: 29-01 — applied; checkpoint approved
Status: UNIFY complete. Shipped (CODE; deploy USER-OWNED — Vercel auto-deploys on push to
  main): /faq page (8 Q&As from the 2026-06-14 coach roleplay) + Nav/Footer links;
  Pricing.js → NEW model $300 device + $20/swimmer/mo cloud (supersedes Phase 23 $15);
  privacy/page.js updated to disclose cloud video storage (§2/§4/§6 + date June 14);
  marketing/sales-pitch-email.md (gitignored, local-only); PROJECT.md + web/README.md
  pricing notes. Build green; /faq prerendered; preview verified, no console errors.
  AGE FLOOR (2026-06-14 user decision): privacy §6 retitled "Minors and age requirement"
  — Swimnetics is 13+ for now (avoids COPPA under-13 regime for test demos); "we do not
  knowingly collect data from children under 13"; club collects verifiable parental
  consent at registration for 13–17. Recorded as PROJECT.md constraint.
  ⚠ ATTORNEY REVIEW still owed before paid pilot — policy advertises cloud storage of
  minors' (13–17) VIDEO. ToS still owed. See memory legal_privacy_status. SUMMARY:
  29-01-SUMMARY.md.
Last activity: 2026-06-14 — Phase 29 shipped + loop closed. User decision: keep current
  privacy wording, push to prod (commands provided per user pref — see Session Continuity),
  close loop.

## Loop Position (29-01)
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [29-01 loop CLOSED 2026-06-14 — approved; deploy user-owned]
```

PRIOR: Phase 28 of 28 (Privacy Policy) — ✅ COMPLETE 2026-06-13 (loop closed, approved)
Plan: 28-01 — applied; checkpoint approved
Status: UNIFY complete. /privacy page + footer link shipped (code; NOT deployed —
  Vercel auto-deploys on user push to main). Living document — user noted it WILL
  change; revisit §2 (video), §4 (sub-processors), §6 (children's) on data-practice
  changes + bump "Last updated". Follow-ups (out of scope, before paid pilot w/
  minors): Terms of Service (operative parental-consent clause) + attorney review.
  See memory legal_privacy_status. SUMMARY: 28-01-SUMMARY.md.
Last activity: 2026-06-13 — Phase 28 shipped: web/app/privacy/page.js (10-section
  policy) + Footer link. Verified in preview (all sections, no-video claim, no
  console errors). Prompted by the 2026-06-13 privacy discussion (minors' data,
  COPPA/CCPA).

PRIOR: Phase 27 (Device Model — 3D hero) ✅ COMPLETE 2026-06-12 — checkpoint approved (angled
  3/4 pose). DEPLOY (both auto on git push origin main):
  - Railway backend: GitHub-auto-deploys; verified live after 76c2187 (/reports serving,
    drift resolved).
  - Vercel website: PROJECT EXISTS, linked to web/ root dir with all 3 NEXT_PUBLIC_* env
    vars (user confirmed 2026-06-12); auto-deploys on push. NO CLI/token locally — Vercel
    actions happen via the push, not from this machine.
  Follow-up shipped (11d9a82): fixed placeholder-flash — Suspense fallback was the
  primitive placeholder, visible during the ~8MB GLB load then popping to the real model;
  now fallback=null (placeholder only via ModelBoundary on true load failure) + scale-in
  fade. If load gap ever needs shortening: gltf-transform Draco/meshopt (user declined
  compression in Phase 27 — uncompressed 8.24MB by choice).
Prior plan line (historical):
  Swap the marketing-hero placeholder for the real device_model.glb (8.24 MB, at repo
  root → move to web/public/models/device.glb). Auto-fit (bbox recenter + auto-scale,
  robust to Fusion's arbitrary scale/up-axis); KEEP auto-rotate + cursor-tilt (no drag),
  SHIP uncompressed (both user decisions); placeholder stays as fallback. Web-only —
  no overlap with parked Phase 26. autonomous:false (visual checkpoint for orientation).

PRIOR ACTIVE (now background): Phase 26 (In-App Video Overlay) — Planning
Plan: 26-01 created, awaiting approval. New iOS feature: one-tap "Record with Video" —
  app writes BLE START + starts IN-APP camera together (app-timestamps videoStartPhoneMs
  = Date.now() at recordAsync), then STOP + existing META/DUMP/process; opens a playback
  screen with synced VelocityChart cursor + m/s readout + ±nudge. Sync = sessionStartPhoneMs
  (META) − videoStartPhoneMs. In-app camera keeps Swimnetics foreground so BLE survives;
  buffer-and-dump means BLE not needed during the swim anyway (the native-camera/creationTime
  path was dropped). Reuses RecordScreen's writeCmd/saveCSV/uploadAndProcess — no BLE
  refactor. Adds expo-camera + expo-video (native → EAS build REQUIRED). 2 auto tasks +
  checkpoint; autonomous:false. On-device check also validates BLE+camera concurrency.
  Supersedes 22-02 manual demo. See memory project_video_overlay_sync.
Status: APPLY — Tasks 1+2 code complete; paused at the device checkpoint (EAS build,
  user pays per build). Task 1: expo-camera/expo-video installed, camera+mic usage
  strings in ios/mobile/Info.plist (bare workflow — plist edited directly, app.json
  mirrored), VideoOverlay registered in App.js, RecordScreen gained "Record with Video"
  (START→recordAsync w/ videoStartPhoneMs=Date.now(), stop→STOP→existing retrieval;
  'videoRecording' state excluded from the disconnect watcher so a BLE drop never kills
  the camera) + "View Video Overlay" results button. Task 2: VideoOverlayScreen.js —
  expo-video timeUpdate @20Hz → markerTimeS + interpVelocity readout + ±nudge (clamp 3s);
  interp helper 11/11 unit checks. Metro export (ios) exits 0.
Last activity: 2026-06-12 — first 26-01 EAS build (build 36) CRASHED AT LAUNCH: dyld
  "Symbol missing" — ExpoCamera.framework (precompiled, EXPO_USE_PRECOMPILED_MODULES=1)
  referenced Record.from(dictionary:appContext:) absent from the older ExpoModulesCore
  pinned by expo 56.0.3. FIXED: npx expo install --fix → expo 56.0.11 / expo-modules-core
  56.0.16 / dev-client 56.0.20 / safe-area 5.7.0 / svg 15.15.4; expo-doctor version check
  passes; metro export clean. Awaiting REBUILD + device checkpoint. LESSON: run expo-doctor
  before every paid EAS build — version skew between precompiled expo frameworks = launch
  crash, not build failure.
  Hardening pass (pre-rebuild): fixed maxDuration dead-end (recordAsync self-resolve now
  auto-runs the stop flow), stop-before-recordAsync race (stopRequestedRef re-issues
  stopRecording), writeCmd null-device guard; failsafes: 10s camera-ready timeout, camera
  release on unmount, NaN-origin guard + paused-scrub-safe 20Hz polling in overlay; debug:
  on-screen errorMsg in the error state (console invisible in TestFlight), video-missing
  notice on results, origin/timestamps debug line on overlay. Export clean, interp 6/6.

PARKED: Phase 22-02 (Video Overlay Validation) — APPLY paused; Task 1 done (render
  pipeline dry-run validated, video_sync.py UTF-8 fix). Superseded by Phase 26 for the
  product path; kept as laptop fallback. Phase 16 plan 16-04 (wavelet spike) — PLAN ready
  for APPLY. Phase 25 COMPLETE ✅.

Progress:
- Milestone v0.5: [█████████░] ~92%
- Phase 21: [██████████] 100% (code complete; on-device UAT deferred)
- Phase 22: [████████░░] 80% (22-02 Task 1 done + render pipeline dry-run validated; at device checkpoint)
- Phase 23: [██████████] 100% ✅ (3/3 plans; checkpoint approved 2026-06-11)
- Phase 24: [██████████] 100% ✅ (3/3 plans; checkpoint approved 2026-06-11)
- Phase 25: [██████████] 100% ✅ (1/1 plans; 2026-06-12)

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [28-01 loop CLOSED 2026-06-13 — /privacy page shipped, approved]
```
(16-05 loop CLOSED 2026-06-12 — wavelet shipped to production (placeholder).)
(16-04 loop CLOSED 2026-06-12 — GO verdict; 4 research spikes done.)
16-05 SHIPPED: segment_cycles_wavelet (Morlet CWT ridge) is now the SOLE production
  segmenter for all 4 strokes (metrics.py:441; trough kept, never called).
  segmentation_reliable=False in session + /process data_quality + provisional warning.
  PyWavelets → requirements.txt. Tests 31 passed; freestyle now segments (carlos_fr_1=17,
  carlos_fl_1=8, lucas_fl=3). PLACEHOLDER — known breaststroke regression accepted; tuning
  = future 16-06. See 16-05-SUMMARY.

PHASE 16 TRANSITION #2 (2026-06-12): 5/5 plans summarized. Goal "stroke-agnostic
  segmentation + freestyle metrics" SUBSTANTIALLY SHIPPED at placeholder quality — wavelet
  ridge live for all strokes. NOT fully validated (segmentation_reliable=False); tuning
  deferred to 16-06. ⚠ DEPLOY: real backend code changed (metrics.py/api.py/requirements);
  Railway auto-deploys on push to main — pywt is a NEW Railway build dep. Git commit NOT
  run (user pref — commands provided); on main branch, so branch-first if committing.
(27-01 loop CLOSED 2026-06-12 — SUMMARY written, ROADMAP ✅, shipped 76c2187+11d9a82.
 Phase 26-01 remains ◐ — APPLY paused at its EAS-build/device checkpoint, parallel.)

PHASE 16 TRANSITION (2026-06-12): all 4 plans summarized → phase RESEARCH complete.
  Verdict ladder: 16-01/02/03 shape-matching all CLOSED; 16-04 wavelet ridge = GO.
  Wavelet/CWT ridge is the chosen freestyle-segmentation direction. NOT shipped —
  freestyle metrics + production wiring are a future 16-05 implementation plan
  (rate-accuracy + boundary-placement gaps are the headline open work; see 16-04-SUMMARY).
  No git commit this plan: wavelet_spike.py already tracked/committed + unchanged;
  .paul/ docs are untracked by design.

16-04 result: ran wavelet_spike.py on the 11-session set (8 br + 3 free/fly); all
  rendered. Breaststroke calibration WEAK (3/8 within ±5 SPM; 4 sessions rail the
  120-SPM ceiling) but user eyeballed the scalograms and called GO — wavelet ridge
  is now Phase 16's standing direction (first non-"close" verdict after 3 shape-
  matching spikes). Follow-up impl plan (16-05) must fix rate accuracy + boundary
  placement before trusting freestyle. See 16-04-SUMMARY.md.

## Accumulated Context

### Decisions

| Decision | Phase | Impact |
|----------|-------|--------|
| Trough-only segmentation, FFT removed | Phase 1 | SPM from mean cycle duration |
| BLE recording background thread | Phase 3 | Streamlit app.py pattern |
| FastAPI not serverless | Strategy | Railway $5/mo |
| Breaststroke only for V1 | Strategy | Freestyle in Phase 8 |
| swimnetics-mobile at Desktop/swimnetics-mobile | Phase 5-01 | Separate repo, avoids git root conflict |
| Bundle ID: com.swimnetics.app (ASC: 6772050809) | Phase 5-01 | Registered in App Store Connect |
| iOS native files edited directly | Phase 5-01 | prebuild requires Mac |
| .xcode.env sources nvm | Phase 5-01 | Xcode script phases restricted PATH |
| writeCharacteristicWithResponseForService for NUS RX | Phase 5-02 | RX char is [write-resp] |
| Subscribe BEFORE sending START | Phase 5-02 | Device may stream immediately |
| expo-file-system/legacy import | Phase 5-02 | writeAsStringAsync deprecated SDK 56 |
| isStoppingRef guard + safety reset in startRecording | Phase 5-02/03 | Prevents double-stop |
| Error code 2 suppressed, onData no longer auto-stops | Phase 5-02/03 | Avoids spurious double-stop |
| FileSystem.uploadAsync not fetch+FormData | Phase 5-03 | RN 0.85 rejects FormData pattern |
| Device stays connected between sessions | Phase 5-03 | reset() checks isConnected() → connected state |
| disconnectRef removed before overwriting in startRecording | Phase 5-03 | Prevents leaked idle watcher |
| Railway URL: swimnetics-api-production.up.railway.app | Phase 5-03 | In src/config.js |
| Supabase project: ujrotuijxrbscjhzekjk.supabase.co | Phase 6-01 | Schema applied; SUPABASE_JWT_SECRET in Railway |
| supabase-py auth.get_user() for JWT verification | Phase 6-02 | Replaces python-jose; works with asymmetric Supabase keys |
| Metro CJS redirect for @supabase/supabase-js | Phase 6-02 | Hermes can't handle .mjs dynamic import(variable) |
| /process requires auth (require_auth) | Phase 6-03 | 401 without Bearer token; athlete roster complete |
| RLS WITH CHECK required for INSERT | Phase 6-03 | USING alone ignored by Postgres for INSERT; patch_01 applied |
| detect_initial_phase: first deep trough = boundary | Phase 7-01 | Peaks before trough = dive/pulldown; not counted as strokes |
| athlete_id optional in /process | Phase 7-01 | Existing iOS doesn't send it; backend save skips gracefully until Phase 8 |
| SUPABASE_SERVICE_ROLE_KEY + raw-csvs bucket live | Phase 7-01 | Backend ready to save full sessions the moment Phase 8 sends athlete_id |
| Device auto-registration via chip_id (not QR scan) | Phase 14-01 | /process upserts devices table on upload; iOS just needs to pass device_id form field |
| devices.coach_id has no FK to coaches | Phase 14-01 | FK failed in Supabase SQL editor; ownership enforced at application layer via coach_row_id query |
| Billing tier is "enterprise" (not "pro") | Phase 15-01 | Stripe product named "Enterprise"; env var is STRIPE_ENTERPRISE_PRICE_ID |
| monthly_session_limit=None means unlimited | Phase 15-01 | Paid tiers have null limit; enforcement in 15-02 skips check when None |
| ESP_32_V5 = motor_logger base + buffer-and-dump (fw 1.1.0) | Phase 22-01 | GPIO27/32, DRV8833, chip-ID BLE name; motor_logger_esp32.ino untouched |
| Button: short press = record, long press ≥800ms = motor | Phase 22-01 | Phone-free recording; reel rewind preserved on one button |
| Buffer sized from largest free heap block − 32KB headroom | Phase 22-01 | Fixed 60s malloc failed (fragmentation); ~41s on current board |
| META = 8B [start_us][now_us]; DUMP end marker = 1B 0xEE | Phase 22-01 | Non-multiples of 7 → sample parsers ignore them; basis for 22-02 clock correlation |
| BleContext uses expo-secure-store, not AsyncStorage | Phase 21-01 | Already installed (supabase.js pattern); no new native dep / no EAS rebuild needed |
| 21-02 checkpoint deferred — EAS build credits exhausted | Phase 21-02 | All on-device ACs unverified; run 21-02-PLAN Task 3 procedure when credits renew |
| Live velocity graph removed from RecordScreen | Phase 21-02 | Dump mode has no in-swim data; Phase 13-03 feature retired |
| Public pricing = $15/swimmer/month, informational only | Phase 23 | Website shows it; Stripe checkout NOT exposed on web; supersedes $200/$1,000 display |
| Website = web/ (Next.js 16 + Tailwind v4, Vercel target) | Phase 23-01 | Design tokens in globals.css @theme; AGENTS.md → read bundled Next docs, not training data |
| 3D hero: placeholder primitives + GLB drop-in | Phase 23-01 | Fusion 360 export → web/public/models/device.glb, zero code change |
| Web reads via supabase-js (RLS), writes via Railway API | Phase 23-02 | Same split as iOS; api.py CORS already allowed * — never modified |
| Compare baseline = older session; deltas % from baseline | Phase 23-03 | app.py convention; speed/DPS normal, CV/fatigue inverse, rate/coast neutral |
| Parent reports = tokenized public URLs, no parent accounts | Phase 24 | Served by no-auth GET /reports/{token} (service role); RLS has no anon policy by design |
| Email provider deferred — mailto drafts + copy-link | Phase 24 | Resend slots into ReportSendList actions + sent_at later |
| Report metric preset uses lap_time_s, not time-to-10m | Phase 24 | time-to-X needs full distance_profile per session — too heavy for public payload |
| Report pages show first name only | Phase 24 | Link-leak hygiene; full name stays in the portal |
| CODEBASE-AUDIT.md = cold-start orientation doc | Phase 25 | STATE.md stays the decision log; audit holds the verified connection matrix |
| Deploy drift detected via 404-body-shape probe | Phase 25 | Generic "Not Found" vs route-specific message — unauthenticated, read-only |
| Audit findings documented, not fixed | Phase 25 | All §5 findings routed via Deferred Issues / consider-issues |

### BLE Protocol (locked — buffer-and-dump, firmware 1.1.0 / Phases 22-01 + 21-02)

```
NUS Service:  6E400001-B5A3-F393-E0A9-E50E24DCCA9E
TX (notify):  6E400003-B5A3-F393-E0A9-E50E24DCCA9E
RX (write):   6E400002-B5A3-F393-E0A9-E50E24DCCA9E  [write-resp]
Device name:  "SwimLogger-<chipID>" (6 hex chars; chipId = name suffix)
Samples:      any non-zero multiple of 7 bytes, <IHB per sample
META cmd:     reply = 8 bytes [session_start_us u32 LE][device_now_us u32 LE]; start==0 → none
DUMP cmd:     streams buffer (24 samples/packet), then 1-byte 0xEE end marker; clears on success
Commands:     START\n / STOP\n / META\n / DUMP\n / REEL_ON\n / REEL_OFF\n via writeWithResponse
Clock sync:   sessionStartPhoneMs = phoneNowMs − ((deviceNowUs − sessionStartUs + 2^32) % 2^32)/1000
CSV save:     FileSystem.documentDirectory + 'session_<timestamp>.csv'
Upload:       FileSystem.uploadAsync(Railway/process, path, MULTIPART) + device_id=chipId
```

### Deferred Issues

| Issue | Effort | Revisit |
|-------|--------|---------|
| device_id NULL on all sessions | ✅ Resolved Phase 14 — auto-registers via chip_id on /process | — |
| Raw CSVs accumulate on device | S | v0.3 polish |
| Railway free tier sleeps on inactivity | S | Upgrade to $5/mo Starter before demo |
| App icons are placeholder | S | Before App Store submission |
| Kick detection unreliable | M | When LP filter cutoff tunable |
| Sessions with null coach_id may not appear in history (RLS) | S | v0.3 |
| MetricItem duplicated in RecordScreen + ReportCardScreen | XS | Next polish pass |
| Shape-matching family closed (motifs, chains, CAC, PMP) | Phase 16 | ✅ Superseded — 16-04 wavelet ridge GO 2026-06-12; wavelet is the chosen direction |
| Freestyle segmentation not shipped — wavelet ridge needs impl | Phase 16 | ✅ Shipped 16-05 2026-06-12 — wavelet is the production segmenter (placeholder quality) |
| Wavelet segmentation tuning (rate accuracy, ceiling-railing, boundaries) | Phase 16 | 16-06 (future): close the breaststroke regression + freestyle accuracy; flip segmentation_reliable when validated. Knobs: _PERIOD_MIN/MAX_S, _RIDGE_JUMP_PENALTY, _RIDGE_LOW_BAND_BIAS |
| pywt(PyWavelets) is a new Railway build dep | Phase 16 | ✅ Resolved 2026-06-14 — pushed c34e8fe, Railway deployed; new build booted (probe /health 200 + /process 401). Wavelet live in prod |
| video_sync.py crashes (vs. degrades) when ffmpeg absent | ✅ Resolved 22-02 Task 1 — ffmpeg 8.1.1 installed via winget; mux verified | — |
| EAS build credits exhausted — Phases 12–21 on-device UAT pending | M | 2026-06-12 — user opted to PAY PER BUILD (blocker lifted). Build profile `preview` (store/TestFlight). Run 21-02-PLAN Task 3 retrieval UAT first, then 22-02 demo — same build |
| video_sync.py crashes on success (→/— in print, cp1252 console) | ✅ Fixed 2026-06-12 — forced stdout UTF-8; render now exits 0. Found during 22-02 desktop dry run | — |
| .gitignore excludes production files — both repos | ✅ Resolved 2026-06-12 — commits 0b45ce9/4f152f7 (myswimcoach) + 6abcbaa (mobile). Residual: mobile has NO remote (local-only); .paul/+STRATEGY.md deliberately untracked (public repo) — back up separately | — |
| Committed supabase SQL can't rebuild live DB | ✅ Mitigated 2026-06-12 — patch_04_backfill.sql reconstructs Phase 12/14/15 migrations from code evidence. USER: verify vs dashboard (or replace with supabase db dump) | — |
| GET /sessions/{id}/export has no caller | XS | Suggested: next web phase — "Download CSV" button on portal session page (endpoint kept, tested) |
| firmware_version never sent by iOS — FW characteristic unread | S | Suggested: next iOS build cycle — code change anytime, on-device verify rides the EAS-credits gate with 21-02 UAT |
| DELETE /sessions orphans raw CSV in storage bucket | ✅ Fixed + DEPLOYED 2026-06-12 — Railway redeploy (push 76c2187) shipped it. Pre-fix orphans remain in bucket | — |
| Railway deploy drift (live ran pre-Phase-24 build) | ✅ RESOLVED 2026-06-12 — push 76c2187 auto-triggered Railway rebuild; probe confirms /reports returns route-specific 404 ("Report not found") + /health 200. Parent links now work against prod. Railway IS GitHub-auto-deploy | — |
| Billing checkout/portal unreachable — no client UI | M | When monetization wiring wanted (audit §5.4) |
| MetricItem dedup + on-phone raw CSV cleanup | XS+S | Suggested: bundle into next iOS polish phase (pre-existing rows above, annotated 2026-06-12) |
| Phase 34 Diagnostics device checkpoint unrun | S | ◐ PARTIAL 2026-06-18 (35-02): Diagnostics screen verified live on device; full magnet→buffer flow still deferred — folded into the post-resolder re-verify row below |
| Post-resolder iOS device re-verify (35-02) | S | Deferred 2026-06-18 — encoder wiring loose, no solder station. ONE build covers: full 34-01 (magnet absent→"SENSOR NOT RESPONDING"/NOT DETECTED, align→detected, spin→angle, record→buffer climbs), 21-02 retrieval, 26-01 record-with-video, 22-02 laptop demo, + re-verify the 2 fixes (forget-disconnect, diagnostics verdict). Run 35-02-DEVICE-CHECKLIST.md. No rebuild cost beyond that build |
| iOS ↔ web feature-parity gaps (AI chat + advanced per-cycle graphs) | M | Observed 2026-06-18 (35-02) — web-only, never built for iOS; NOT regressions. Candidate future "iOS parity" phase. Noted for 35-03 docs |

### Blockers/Concerns
None. (pywt/PyWavelets deploy gate CLEARED 2026-06-14 — user confirmed Railway deployed
  c34e8fe; post-deploy probe /health 200 + /process 401 (not 502) = new build booted with
  pywt+metrics imported. Wavelet segmenter is LIVE in prod.)

## Session Continuity

Last session: 2026-06-12
Stopped at: Phase 16-05 UNIFY complete — wavelet ridge SHIPPED to production as the sole
  segmenter for all 4 strokes (placeholder quality). Phase 16 implementation transition
  done (5/5 plans). Earlier same session: 16-04 loop closed, Phase 27 loop closed.
Next action: ✅ Wavelet backend SHIPPED + DEPLOYED 2026-06-14 (c34e8fe → main → Railway live;
  deploy gate cleared). Open threads: (a) Phase 26-01 device checkpoint (EAS build,
  pay-per-build); (b) /paul:plan 16-06 when freestyle data is available to TUNE the wavelet
  (rate accuracy, ceiling-railing) + flip segmentation_reliable; (c) STILL UNCOMMITTED in
  working tree (separate concerns, not pushed): web/app/privacy/page.js + Footer.js
  (Phase 28 → Vercel), video_sync.py (Phase 22), ESP_32_V5/ESP_32_V5.ino (firmware).
Resume file: .paul/phases/16-freestyle-support/16-05-SUMMARY.md

Git (16-05): ✅ committed c34e8fe + pushed to main 2026-06-14 (scoped: metrics.py, api.py,
  requirements.txt, tests/test_metrics.py, CLAUDE.md, .gitignore). Railway deployed; live.

User-owned follow-ups: push api.py to Railway (parent links break without it — probe-
  confirmed 2026-06-12); FIX GIT COVERAGE (un-ignore or force-add firmware/tests/
  supabase/md in myswimcoach; commit untracked src/ in swimnetics-mobile — commands in
  audit §5.3); Vercel deploy + DNS cutover; git commits for Phases 21–25 — commands
  provided, not run (user pref). When email is wanted: Resend account + RESEND_API_KEY,
  wire into ReportSendList send actions.

Also parked (Phase 22): 22-02 APPLY at demo-video checkpoint. Task 1 done: ffmpeg 8.1.1
  installed (winget), ffprobe creation_time verified on AP.mp4, video_sync mux fixed.
  When EAS credits renew — eas build → 21-02-PLAN Task 3 device checkpoint →
  22-02-PLAN checkpoint (demo video) → /paul:unify both remaining steps
Resume context:
- When EAS credits renew: eas build → run 21-02-PLAN Task 3 on-device checkpoint FIRST,
  then the 22-02 demo-video checkpoint (same build)
- Overlay procedure baked into 22-02-PLAN: sessionStartPhoneMs from results screen,
  videoStartPhoneMs from ffprobe creation_time, video_origin_s = diff/1000,
  raw CSV from Supabase raw-csvs bucket → vel_acc_extraction.py → video_sync.py
- Git commits for Phases 21/22 work not yet made (both repos: myswimcoach +
  swimnetics-mobile) — commands suggested to user, not run

iOS project: C:\Users\TonyZheng\Desktop\swimnetics-mobile\
Railway:     https://swimnetics-api-production.up.railway.app
EAS project: @tzheng846/swimnetics (ID: db87ba35-184b-4469-a291-559775c12191)

---
*STATE.md — Updated after every significant action*
