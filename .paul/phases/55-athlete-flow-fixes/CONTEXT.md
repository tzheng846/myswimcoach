# Phase Context

**Phase:** 55 — Athlete Flow Fixes (mobile)
**Generated:** 2026-08-05
**Status:** Ready for planning

---

## Where this came from

Found during live verification of the 51-02 checkpoint. Adding an athlete **works now** — the
phantom-`coach_id` 500 is gone (AC-1 passed). Exercising the app immediately afterward surfaced two
navigation/refresh defects in the flow the fix unblocked: you can create an athlete, but you then
can't reach the record screen with them.

Both are in **`swimnetics-mobile`** (separate repo, `Desktop/swimnetics-mobile`). Neither touches
this repo. Neither is related to the Phase-51 backend work — they predate it and were simply
invisible while athlete creation was broken.

---

## The two bugs

### B1 — The record screen's roster is frozen at app launch

**Symptom (both directions, confirmed 2026-08-05):**
- **Add** an athlete on the Team tab → go to the record / new-session screen → absent. Restart and
  it appears.
- **Delete** an athlete → go to the record screen → the deleted athlete is **still listed**. Restart
  and it's gone.

Originally reported as an add-only problem; the delete case was found later the same day and has the
identical cause. One fix covers both — this is not two bugs.

**Cause:** `src/screens/RecordingConfigScreen.js:42` loads the roster in `useEffect(..., [])` —
mount-only.

```js
useEffect(() => {
  supabase.from('athletes').select('id, name, stroke_type, head_waist_m').order('name')
    .then(({ data }) => setAthletes(data ?? []));
}, []);
```

`RecordingConfig` is a **tab screen** (`src/navigation/RootTabs.js:29`). Tab screens mount once and
stay mounted, so that effect runs exactly once per app launch. Switching tabs is not a remount —
which is why only a restart fixes it.

**Precedent to copy, not invent:** the three other data-bearing tab screens already solve this with
`useFocusEffect` — `DashboardScreen` (3 uses), `AthletesScreen` (2), `SessionHistoryScreen`.
`RecordingConfigScreen` is the only one that was missed. `SessionHistoryScreen` has no direct
supabase read, so this is the last gap.

### B2 — "Record" button on the athlete screen does nothing

**Symptom:** open an athlete from the Team tab, press Record, no reaction at all.

**Cause:** a navigator-scope mismatch introduced when Phase 38-03 moved `AthleteDetail` onto the
Root stack.

| Screen | Navigator | Reference |
|---|---|---|
| `AthleteDetail` | **Root stack** | `RootTabs.js:46` |
| `RecordingConfig` | **Tab** (child of `Tabs`) | `RootTabs.js:29` |

`AthleteDetailScreen.js:137` calls `navigation.navigate('RecordingConfig', {...})`. React Navigation
resolves an unknown route name by bubbling **up** through parent navigators — it never searches
**down** into a child navigator. `AthleteDetail`'s parent is the Root stack, which has no
`RecordingConfig` route, and Root has no parent. Nothing handles the action, so it is a silent
no-op (dev builds log "not handled by any navigator").

The nested form is required: `navigate('Tabs', { screen: 'RecordingConfig', params: {...} })`.

**Stale comment to fix in the same pass** — `RootTabs.js:21-23` currently asserts the opposite of
reality:

> Route names match existing navigate() targets so cross-screen navigation keeps working:
> "RecordingConfig" (Record island) and "SessionHistory" ... are reached by name from AthletesScreen.

True for `AthletesScreen` (a tab sibling). False for `AthleteDetail` since 38-03.

**Scope check:** `AthleteDetailScreen.js:137` is the **only** Root→Tab navigate call in the app
(checked across all 8 Root-stack screens). Not a class of bug.

---

### B3 — Freestyle analytics still blocked on the phone (no new code; commit + build)

**Symptom:** freestyle report cards still show the "Coming Soon" block on the iPhone app.
**iPhone only** — user confirmed they did not see this on the web portal.

**Not a bug.** The backend half is already live: `ratings.py`'s threshold fallback shipped in
`dedac17` (Phase 54-01's T2 rode along with the 51-02 commit), so the API now returns real freestyle
bands. The app's own gate is what's still blocking, and 54-01's fix for it has never been built:

```
myswimcoach       HEAD dedac17  ratings.py thr_table fallback  → DEPLOYED
swimnetics-mobile HEAD 1296494  ReportCardScreen.js:169
                                isAnalyticsReady = !strokeType || strokeType === 'breaststroke'
swimnetics-mobile working tree  ReportCardScreen.js:195
                                isAnalyticsReady = true        → UNCOMMITTED, never built
```

**User decision 2026-08-05: fold into 55-01.** The plan commits the existing working-tree change
alongside the two fixes so one paid EAS build carries everything. No new code is written for this —
the task is "commit what 54-01 already wrote, then verify it on the build."

---

## Explicitly out of scope

**Delete athlete — NO CHANGE (user decision, 2026-08-05).** Initially reported as missing. It
exists at `AthleteDetailScreen.js:96`, behind a `⋯` glyph in the top-right
(`accessibilityLabel="Athlete options"` → Alert with Edit fields / Delete athlete / Cancel). User
had never noticed the glyph, tested it during this discussion, and judged it fine as-is.

Recorded for a future UX pass, deliberately **not** acted on here:
- The Team **list** has no delete affordance at all. Sessions have swipe-to-delete
  (Phases 12-03 / 19-01); athletes do not. The inconsistency is what sent the search to the wrong
  screen.
- Delete writes **directly via supabase-js on RLS** (`supabase.from('athletes').delete()`), not
  through the API. There is no `DELETE /athletes` endpoint. This drifts from CLAUDE.md's
  "writes via this API" rule (reports are the documented exception; this is an undocumented second
  one). Notable given Phase 51 just spent a plan on athlete ownership scoping.
- The dialog promises "This also removes their sessions." Consistent with committed schema —
  `sessions.athlete_id ... ON DELETE CASCADE` (schema.sql:55), same for reports (patch_03:13).
  **Unverified against the live DB:** schema.sql is known-stale, and `supabase/live_schema.json`
  records columns but not constraints.

**Also declined:** a dev-time guard to make unhandled `navigate()` calls fail loudly. Offered given
B2 failed silently; user chose the two bug fixes only.

---

## Goals

1. Adding an athlete and then recording with them works in one continuous flow, no app restart.
2. The Record button on the athlete screen reaches the record screen with the athlete pre-selected.
3. No change to delete-athlete behavior.

---

## Approach notes

- **Mobile repo only.** No backend, no schema, no web. Nothing in `myswimcoach/` changes.
- **Follow the existing `useFocusEffect` pattern** from the three sibling tab screens rather than
  introducing a new refetch mechanism or a state library.
- **Preserve the params contract.** `AthleteDetailScreen.js:137` already passes
  `athleteId` / `athleteName` / `defaultStrokeType`; `RecordingConfigScreen` reads them for
  pre-selection. The nested-navigate rewrite must deliver the same params to the same screen — the
  bug is the envelope, not the payload.
- **Surgical.** RecordScreen's BLE/camera logic is fragile (~950 lines, noted in 38-06) and is not
  touched. Two screens plus one comment.

---

## Verification

**User decision: a new EAS build, run immediately after apply.** Not hot-reload — the user is on an
installed build.

Plan should gate on `npx expo export --platform ios` exit 0 (the established green-gate for this
repo's mobile plans), then a device checkpoint after the build lands.

⚠ **This build is worth batching.** Several iOS checks have been deferred waiting on exactly one
EAS build. Whoever plans this should list them in the checkpoint so a paid build clears the backlog
in one pass:

| Deferred check | From |
|---|---|
| `isAnalyticsReady = true` → freestyle report cards render analytics | 54-01 T3 |
| Background video upload queue + toast + retry chip | 47-03 |
| Race-start sequence (countdown, hold, blare) | 41-01 |
| Core-flow failsafes (pairing / recording / results) | 42-01 |
| Encoder warmup floor + end-anchored overlay sync | 44-03 |
| Buffer-and-dump recording UAT, diagnostics screen | 21-02 / 34-01 |

---

## Open questions for planning

- Does `RecordingConfigScreen` need the athlete **pre-selected** when arriving from AthleteDetail,
  or only present in the list? The params imply pre-selection; worth confirming the screen actually
  applies `athleteId` on arrival, since that path has never once executed successfully.
- `useFocusEffect` will refetch on every tab focus. Fine at current roster sizes; note it rather
  than pre-optimizing.

---

## Related state

- **51-02 is committed and deployed** — `dedac17 "Scope athletes by team_id (Phase 51-02)"`, pushed
  by the user 2026-08-05, Railway auto-deployed. AC-1 confirmed live (adding an athlete works). The
  commit also carried 54-01's backend half (`ratings.py`, `tests/test_ratings.py`), which is why the
  freestyle unlock is live server-side. AC-3 (team-wide coach chat) and AC-4 (`/billing/status`
  athlete_count) remain unverified.
- Phase 55 is otherwise independent: different repo, no shared files.

---

## Recorded, not scoped here: coach chat answers about the wrong athlete

Reported 2026-08-05, **documentation only by user decision — do not fix in this phase.** Recorded in
STATE open threads + a ROADMAP row.

Asking the AI coach "give me info on Sid specifically" returned another athlete's history under
Sid's name — it claimed a most-recent swim of Aug 5 when Sid has only two swims, both in May.

**Root cause:** `list_athlete_sessions` has no athlete parameter — its schema is `limit` + `stroke`
only (`coach.py:141-142`). The executor is bound to the athlete of the session the chat was opened
from (`api.py:1494`, `.eq("athlete_id", athlete_id)` where `athlete_id` is a closure over the
request's anchor session). Naming a different athlete therefore **cannot** re-scope the tool; the
model receives the anchor athlete's sessions and attributes them to whoever was named. Aug 5 is
today's date, consistent with the anchor athlete having a session recorded that day.

**Severity note (my assessment, not the user's):** this is cross-athlete data attribution — one
swimmer's performance data presented as another's — not merely an inaccurate answer.

**Not caused by 51-02.** That path filters on `athlete_id` + `coach_id`, neither of which the
plan touched. 51-02 did repair the *team* tools (`rank_athletes` / `team_summary` / `rank_progress`,
broken since 33-02), so the chat is newly able to answer roster questions — which plausibly makes
its wrong athlete-specific answers sound more authoritative than before.
