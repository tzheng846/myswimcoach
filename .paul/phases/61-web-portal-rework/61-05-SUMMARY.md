---
phase: 61-web-portal-rework
plan: 05
subsystem: ui
tags: [nextjs, react, compare, video, naming]

requires:
  - phase: 61-03
    provides: VideoPane with the end-anchored origin (58-04), reused verbatim
  - phase: 61-04
    provides: the Compare layout, exported colours, and the mnemonic generator
provides:
  - video on Compare, toggleable, colour-paired to its trace
  - a single session-name model used across the whole portal
  - stroke tags on Compare labels
affects: [61-06 synced playback (future, unplanned)]

tech-stack:
  added: []
  patterns:
    - "One display name per session, derived — never a concatenation, never written"

key-files:
  created: []
  modified: [web/app/app/compare/page.js, web/lib/sessionName.js, web/components/portal/SessionCard.js, web/app/app/sessions/[id]/page.js, web/components/portal/RecentActivity.js]

key-decisions:
  - "Video on Compare is opt-in and remembered, not permanent"
  - "displayName = typed name OR mnemonic; one name, still never written to sessions.name"
  - "Synced playback deferred as a TODO, not planned"

patterns-established:
  - "A session is never nameless: the mnemonic IS its name until a coach types one"

duration: ~30min including one checkpoint revision
started: 2026-08-11
completed: 2026-08-11
---

# 61-05 SUMMARY — Video on Compare + one session-name model

**Compare shows each session's footage beside its own trace, on demand — and a session is no
longer nameless anywhere in the portal.** Closes Phase 61.

## Performance

| Metric | Value |
|---|---|
| Tasks | 2 auto + 1 checkpoint (1 revision round, 4 items) |
| Files | 5 modified, 0 created |
| Python | **0** — suite held at 274 |
| Build | clean at every task boundary |

## Acceptance criteria

| AC | Status | Notes |
|---|---|---|
| AC-1 video beside its own trace | **Pass** — amended | Now **toggleable**, off by default (checkpoint) |
| AC-2 video optional per side | **Pass** | Mixed pairs render upload on one side, video on the other |
| AC-3 end-anchored origin here too | **Pass** | Inherited from 61-03 with no new code |
| AC-4 nothing else regresses | **Pass** | Build clean, suite 274 |

⭐ **The pairing check earned its place.** Panels order by *date* but video state is keyed to the
*fetch slot*, so picking a newer session on the left swaps base/new — and the naive wiring would
have shown one session's video against the other's trace. Verified across both orderings × three
video-presence combinations: **0 mispaired**.

## The checkpoint asked for four things; three shipped, one deferred

**1. Video toggleable, not permanent.** Off by default, remembered per browser via `localStorage`
(same pattern as the report card's view/unit). `▶ Show video` / `Hide video` sits on the align row.

**2. Spacing fixed at the cause, not with padding.** The right column now only *exists* when video
is on, so with it off the traces reclaim the full width — which matters, because horizontal
resolution is what makes two velocity curves comparable. When on, the column is `sticky` so the
panes track the traces instead of trailing below them, which is what the screenshot showed.

⚠ **This resolves both costs the plan flagged as accepted-but-unverified.** The density question
("two full VideoPanes is a lot of chrome") was answered by making video opt-in rather than by a
`compact` prop; the width question is moot whenever video is off. Neither was answered on its own
terms — the user changed the question, and that was the better answer.

**3. ⚠ SYNCED PLAYBACK DEFERRED — recorded as a TODO, deliberately NOT planned** (user: *"note
synced playback as a future todo, don't plan it yet"*). It is not a checkpoint tweak:
- `VideoPane` exposes only `seekRef` and `frameStepRef` — **no play/pause API**. A master clock
  needs one, and `VideoPane` was on this plan's DO-NOT-CHANGE list because 61-03 had just
  stabilised it around 58-04.
- `CompareChart` has no per-panel playhead marker.
- It forces a design decision this phase deliberately excluded: **should the D9 align offset also
  shift video B?** For "sync all 4 by the aligned tracing" the answer is presumably yes, but that
  is a call to make explicitly, not to infer.

**4. Naming became a portal-wide model, not a Compare label.** The user's correction: *"the naming
convention was supposed to be for actual session names, not just used for compare… generated name
to just one name."*
- `displayName(session)` = typed name **or** mnemonic. **One name, never a concatenation** — the
  previous form showed `typed · mnemonic · time`.
- Applied to the sessions list, the report card, recent activity and Compare, so a session is
  called the same thing everywhere.
- The report card no longer says "Add session name…" for an un-renamed session — it shows the
  generated name, because such a session is not nameless.
- Stroke tags added to Compare labels: `Amber Albatross · fly · 9:45 AM`.

⚠ **STILL DERIVED, NEVER WRITTEN to `sessions.name`.** That column keeps meaning "what the coach
typed", so a generated name can never be mistaken for a deliberate one, an edit can never be
clobbered, and all 62 stored sessions gain names with no migration. **If names should instead be
PERSISTED at record time, that is a `/process` backend change and a different decision** — raised,
not taken.

Verified on all 62 real sessions: typed names **never decorated** (`"Free 3"` stays `"Free 3"`),
**no session nameless**, labels still 62/62 distinct with the stroke tag added.

## Deviations

**1. Scope grew well past the plan at the checkpoint.** `files_modified` named one file
(`compare/page.js`); the naming model reached four more — `sessionName.js`, `SessionCard.js`,
`sessions/[id]/page.js`, `RecentActivity.js`. All user-directed, none speculative, but the plan did
not anticipate a portal-wide change and it is worth recording that a checkpoint turned a one-file
layout plan into a cross-surface one.

**2. AC-1 was amended, not merely met.** The plan said video sits beside the trace; it now does so
only when toggled on. The AC's intent survives; its literal wording does not.

**3. Removed `formatTime` from `SessionCard.js`** — orphaned by the naming change, so cleaned up
per the "remove what your change made unused" rule. `STROKE_LABELS` was left alone: the report card
still imports it.

## Files

| File | Change |
|---|---|
| `web/app/app/compare/page.js` | Video panes, toggle, sticky column, stroke tags, `stroke_type` in queries |
| `web/lib/sessionName.js` | `displayName`, `strokeTag`; `sessionLabel` collapsed to one name |
| `web/components/portal/SessionCard.js` | Uses `displayName`; orphaned `formatTime` removed |
| `web/app/app/sessions/[id]/page.js` | Shows the generated name instead of "Add session name…" |
| `web/components/portal/RecentActivity.js` | Uses `displayName` |

Skill audit: no `.paul/SPECIAL-FLOWS.md` — step skipped.

## Next phase readiness

**Ready:** Phase 61 is complete. All five of the user's original asks are shipped.

**Concerns**
- ⚠ **Synced playback (TODO, unplanned)** — needs a `VideoPane` play/pause API, per-panel
  playheads in `CompareChart`, a master clock, and the offset-moves-video decision.
- ⚠ **Generated names are derived, not persisted.** If a coach expects the name to be stable across
  a future id change, or wants it visible outside the web, that is a backend decision.
- ⚠ The mobile D5c comment fix from 61-02 is still uncommitted in `swimnetics-mobile`.

**Blockers:** None.

---
*Phase: 61-web-portal-rework, Plan: 05*
*Completed: 2026-08-11*
