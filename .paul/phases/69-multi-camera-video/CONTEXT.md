# Phase Context

**Phase:** 69 — Multi-Camera Video (up to 4 synced angles per session)
**Discussed:** 2026-08-17 (`/paul:discuss`-style — mockup + 2 forks via AskUserQuestion)
**Status:** Ready for `/paul:plan`
**Decisions:** 8 (D1–D8), 2 user-chosen via AskUserQuestion, 4 recommended calls flagged for confirmation.

⚠ **THIS BREAKS THE 1:1 VIDEO MODEL PHASE 67 SHIPPED.** Phase 67's D1/A2 deliberately scoped V1 to
*one clip per session* and deferred multi-camera. This phase is that deferral coming due — it needs a
real schema change (one session → many videos), so it is a multi-plan **data-model + API + web**
phase, not a UI tweak. The UI sits on top of the schema change.

---

## Why now

The user, after Phase 67 shipped single external-camera sync, asked to go multi-camera. Verbatim:

> *"up to 3 additional external video can be matched to a session, with a total of 4 with the phone
> camera. Similar to how the velocity and acceleration trace are stacked together, I want side by
> side videos playing on the same view window."*

> *"need a dedicated attach files page. Make it look simple and elegant. There's currently a bit too
> much going on in report card page."*

So: (1) up to 4 videos per session (1 phone + 3 external), (2) a synced multi-cam player where all
angles share ONE timeline (the way the stacked traces share an x-axis), and (3) a dedicated page for
attaching/managing videos — pulling that clutter OFF the report card.

A mockup was shown and the two structural forks resolved: **adaptive grid** player, **one dedicated
Videos page** holding manage + player.

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Data model = a `session_videos` child table — ADDITIVE, EXTERNALS ONLY (refined at plan time).** The phone/primary video STAYS in `sessions.video_path`/`video_origin_s` (unchanged); `session_videos` holds the ≤3 EXTERNAL videos, each with `storage_path`, its own `origin_s`, an editable `label`, a `position`, `created_at`. ⚠ Refined from "replaces the 1:1 columns": the web reads `sessions.video_path`/`origin_s` **directly via supabase-js in 5 places** (session-list chip, report card, video route, Compare ×2) + mobile via the API — so moving the source of truth would break all of them. Additive means **no data migration, no reader breaks, mobile untouched by construction.** Total per session = 1 primary (legacy columns) + ≤3 externals (`session_videos`) = 4. The player composes the two. Documented asymmetry; full unification is a future option. |
| **D2** | **Player = adaptive grid on ONE shared timeline (user-chosen).** 1 video → full width, 2 → side-by-side, 3–4 → 2×2. A single play/scrub/speed bar drives every camera at once, each seeking to `sessionTime − its origin_s` — exactly how the stacked velocity/accel traces share an x-axis. The velocity+acceleration strip rides the SAME timeline beneath the grid. |
| **D3** | **One dedicated `/app/sessions/[id]/videos` page (user-chosen).** It owns attach + label + per-camera push-off sync + the synced player. **The report card DROPS its embedded player** and gains a compact "Videos (N)" entry point — this is the declutter the user asked for. |
| **D4** | **Per-camera sync reuses Phase 67-01's push-off align, run per video.** Each external camera scrubs to its own push-off frame → one tap sets THAT camera's `origin_s`. Phone keeps its 44-03 end-anchor. Per-camera sync status is surfaced (synced vs "needs push-off"). |
| **D5** | ⚠ **(recommended, confirm) API stays backward-compatible so the mobile repo is UNTOUCHED.** Keep `POST /sessions/{id}/video` + `GET /sessions/{id}/video-url` working as "the phone/primary slot" (backed by that camera's `session_videos` row), and ADD new multi-video endpoints (list, upload-with-role, delete-one, url-per-video). The separately-owned `swimnetics-mobile` never changes. |
| **D6** | ⚠ **(recommended, confirm) Playback perf model = focused-plays.** 4 simultaneous HD decodes each re-seeked per frame WILL stutter on a laptop. V1: the focused camera plays at full rate (with audio); the others follow on scrub/pause and best-effort during play, with a measured fallback (pause non-focused while playing). Exact model chosen from measurement during build. |
| **D7** | **NO migration (superseded by D1's additive refinement).** Existing videos stay put as the primary in the legacy columns; `session_videos` starts empty and only accretes externals. Zero backfill, zero dual-write sync, zero reader changes. |
| **D8** | **Scope = up to 4 cameras for ONE session (per-session clips).** Still NOT the long-take → many-sessions shared-asset workflow (Phase 67's deferred uc1 stays deferred and separate). Free-tier 50 MB per-clip cap (Phase 67-02) still applies — externals are compressed. |

---

## The design (from the mockup, aligned)

- **Grid tiles:** each camera is a tile with an editable label chip (e.g. "Underwater front", "Side
  deck", "Phone") and a sync-status dot (green synced / amber needs push-off). A dashed "Add camera"
  tile fills empty slots up to 4.
- **One control bar:** play/pause, a single session-clock scrubber, time, speed, fullscreen — drives
  all cameras + the trace. Caption: "one timeline drives all cameras + the trace".
- **Trace strip:** velocity + acceleration on the same timeline beneath the grid (extends Phase 64's
  `VideoTracePanel`).
- **Manage row:** a compact list of the 4 slots — label, role, sync status, per-row actions (sync /
  replace / delete) + an "Attach a video · ≤50 MB" CTA. This IS the "attach files page", folded into
  the one Videos page.

---

## For `/paul:plan` — proposed decomposition (3 plans)

1. **69-01 — data model + API (backend + supabase + tests).** `session_videos` table (patch_12) +
   migrate the existing 1:1 video in; multi-video endpoints (list / upload-with-role+label / delete-
   one / url-per-video / set-origin-per-video); keep `POST /video` + `GET /video-url` back-compatible
   for mobile (D5). Ownership/tier/50 MB guard carried from 67-02. `autonomous:false` (schema
   checkpoint).
2. **69-02 — the Videos page: attach + manage + per-camera sync (web).** New
   `/app/sessions/[id]/videos` route; the adaptive grid; upload/label/replace/delete per slot;
   per-camera "Sync to push-off" reusing 67-01. Refactor/extend `VideoPane` for the multi-video case
   (or a new `MultiCamGrid`). Individual playback first.
3. **69-03 — synced playback + report-card declutter (web).** The one-timeline engine (all cameras +
   trace follow one scrub/playhead, D2/D6 perf model), fullscreen, and the report-card change: drop
   the embedded player, add the compact "Videos (N)" link.

## Open plan-time questions

1. **Exact perf model (D6)** — focused-plays vs all-play-muted vs low-res proxies. Decide from a
   measurement of 4 real clips during 69-03.
2. **Storage key scheme** — `{session_id}/{video_id}.mp4` (folder per session) vs `{session_id}_{n}`.
3. **Is the phone slot special** (fixed role/position 1) or just another row?
4. **Does Compare (two-session) get multi-video?** Almost certainly OUT of V1.
5. **`session_videos` RLS/ownership** — same service-role-through-API model as `videos` today.

## Files likely in scope

| File | Change |
|---|---|
| `supabase/patch_12_session_videos.sql` | New `session_videos` table + migrate existing video in. |
| `api.py` | Multi-video endpoints; keep `/video` + `/video-url` back-compat (D5); 50 MB guard reused. |
| `tests/test_api.py` | Multi-video CRUD + back-compat + size guard. |
| `web/app/app/sessions/[id]/videos/page.js` | **New** — the dedicated Videos page (manage + player). |
| `web/components/portal/VideoPane.js` + new `MultiCamGrid`/synced-player | Multi-video grid + one-timeline sync (extends Phase 64 `VideoTracePanel`). |
| `web/app/app/sessions/[id]/page.js` | Report-card declutter: drop embedded player → "Videos (N)" link. |
| `CLAUDE.md` / `DATA-FLOW.md` | Document the 1:1 → 1:many video model. |

Untouched: `metrics.py`, `vel_acc_extraction.py`, the signal pipeline, and (by D5) the entire mobile repo.

## Success criteria

- [ ] A session can carry up to 4 videos (1 phone + 3 external), each with its own label + sync origin.
- [ ] The dedicated Videos page attaches/labels/syncs/deletes each camera; the report card no longer
      embeds a player (compact "Videos (N)" link instead).
- [ ] The synced player plays the cameras + trace on one timeline; scrubbing moves everything together.
- [ ] Per-camera push-off sync works (each camera its own origin); phone keeps end-anchor.
- [ ] Mobile is untouched — `POST /video` + `GET /video-url` still serve the phone slot (D5).
- [ ] 50 MB free-tier cap + compress guidance carried from 67-02; Python suite green.
