# Phase Context

**Phase:** 67 — External Camera Sync (GoPro / any waterproof camera)
**Discussed:** 2026-08-16 (`/paul:discuss`, 1 round + 2 structural forks)
**Status:** Ready for `/paul:plan`
**Decisions:** 6 (D1–D6) + 3 stated assumptions. **One real robustness risk to resolve in plan (R1, browser playback of GoPro files).**

⚠ **WEB-FIRST, with a near-zero backend tail.** The sync *primitive* already exists
(`POST /sessions/{id}/video` stores a file + an arbitrary `video_origin_s`; the Phase-64 overlay
already plays a video against the velocity trace). What's missing is a **web upload + visual-align
UI**, and dropping the phone-only *derivation* of the origin. iOS in-app camera path is untouched
by construction.

---

## Why now

Today the only video is the phone's in-app camera. Coaches want to shoot with a **GoPro or other
waterproof camera** — which is also the only way to capture the **underwater pulldown**, exactly
where the encoder is weakest and where the uncommitted Phase 65 work is aimed. The user asked to
"add multiple external camera compatibility" and flagged the two field workflows verbatim:

> *"1. user sets the camera on ground and keeps recording multiple session in one take, hits upload,
> needs to match session for session with potential for scrapped/deleted sessions in between.
> 2. user starts and stops the camera for each session, needs to match session for session."*

> *"im thinking using the similar method of time stamp as with the encoder. User's option to
> manually adjust obviously needs to be a feature."*

**Pushback delivered and accepted:** the timestamp method worked for the phone *only because one
device clock timestamped both streams*. An external camera shares **no clock and no start/stop
events** with the encoder, and GoPro clocks are routinely unset/wrong. So a wall-clock match is a
*hint* at best, never the anchor. The reliable anchor is a **physical event in both signals — the
push-off/dive** (a sharp velocity spike AND an unmistakable frame). The user chose visual push-off
align as the primary mechanism.

---

## The precise decomposition

The problem splits along **two orthogonal axes** — the sync math and the storage model — and the
user's two use cases split cleanly on the *storage* axis, not the math:

| | Use case 2 — start/stop per session | Use case 1 — one long take → N sessions |
|---|---|---|
| Files | 1 clip : 1 session | 1 big file : many sessions |
| Fits today's `videos/{session_id}.mp4` (1:1)? | **Yes** | **No** — would store the 20-min file N times |
| Needs | assign clip→session + one offset | shared asset + per-session in-point |
| **V1 scope?** | **YES (D1)** | **Deferred (D1)** |

⚠ **Ordinal matching is a trap for use case 1.** Because sessions get scrapped mid-practice, "3rd
swim in the video = 3rd session row" breaks the instant one is deleted. When use case 1 is built,
every session must be anchored **independently** (its own push-off frame/clock), never by position.
This is the core reason it needs the shared-asset model and is not a trivial extension of V1.

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **V1 SCOPE = use case 2 only (one clip : one session).** Reuse the existing 1:1 `video_path` / `video_origin_s` columns and `videos/{session_id}.mp4` layout as-is. Use case 1 (one long take backing many sessions) is **deferred to a follow-up phase** that introduces a shared video-asset model `(video_asset_id, offset_s)`. User's explicit choice ("Per-session clips first (MVP)"). |
| **D2** | **PRIMARY sync anchor = visual push-off align, done BY THE COACH (a human), NOT computer vision.** "Visual" = align against the *picture*; the actor doing the seeing is the coach, not a CV model. Coach scrubs the external clip to the push-off frame and, in one action, snaps it to the swim-start on the velocity trace → we compute and save `video_origin_s`. Works with any camera, any/no clock, above or below water. Manual ± nudge always available. User's explicit choice ("Visual push-off align (+ clock hint)"). ⚠ **No CV anywhere in V1** — user distrusts CV for underwater tasks (splash/refraction/occlusion), correctly. |
| **D2b** | **Only the VIDEO side needs a human; the SESSION side is automatic and trustworthy.** The push-off on the velocity trace is the encoder's big acceleration spike, already detected (`initial_phase` / `detect_swim_window`) — that half stays on the reliable sensor. The coach only marks the one thing the encoder can't see: the push-off *frame* in raw pixels. This is why the mechanism is both CV-free and low-friction. |
| **D3** | **Clock-based auto-match is a HINT, and is deferred for MVP.** It needs (a) parsing the video file's `creation_time`+duration and (b) a persisted *true* swim-start to compare against — and even then GoPro clocks lie. Push-off align alone is the whole V1 feature. Reconsider a coarse metadata pre-fill only if align proves too fiddly. |
| **D4** | **Upload surface = web coach portal (desktop).** GoPro → SD card → laptop → portal. External footage is not a phone action. The align UI extends the existing web video surfaces (Phase 47 annotate page / Phase 61 `/app/sessions/[id]/video` / Phase 64 overlay). **iOS in-app camera path is untouched.** |
| **D5** | **`video_origin_s` MEANING unchanged; only its DERIVATION changes.** It stays "session-clock time at video t=0" — the exact value the Phase-64 overlay already reads. Phone path keeps computing it end-anchored (`deviceDuration − videoDuration`, 44-03). External clips get it from the align UI instead. Same column, same reader → this is *why* 1:1 reuse works and the backend barely moves. |
| **D6** | **Reuse `POST /sessions/{id}/video` and `GET /video-url` as-is if possible.** The endpoint already accepts `file` + arbitrary `video_origin_s` and upserts `{session_id}.mp4`; ownership/auth are already enforced. Plan confirms whether ANY backend change is needed beyond a possible size/format guard (leaning: near-zero). |

### Stated assumptions (user did not object; correct in plan if wrong)

- **A1 — the snap target is the swim-start shown on the trace.** Use the human annotation's
  `stroke_start_s` if one exists, else the auto-detected start (`initial_phase` / `detect_swim_window`
  `ip_end`). Because the align is manual, the coach can also just eyeball the video push-off against
  the velocity spike; plan decides whether we *programmatically* snap to the detected start or purely
  compute origin from where the coach parks the playhead vs. the trace cursor.
- **A2 — one external video per session in V1** (matches today's 1:1). A second simultaneous camera
  (e.g. deck + underwater on the same swim) is out; note as future alongside use case 1.
- **A3 — external clips are trusted to the coach's own footage.** No transcode pipeline assumed in
  V1; if the browser can't play the uploaded codec, that's a format-guidance problem (R1), not a
  server-side conversion feature — unless plan decides otherwise.

---

## What was verified this session (repo, 2026-08-16)

| Claim | Evidence |
|---|---|
| `POST /sessions/{id}/video` accepts `file` + optional `video_origin_s`, upserts `{session_id}.mp4`, 1:1 | `api.py:971-1026` |
| `video_origin_s` is "session-clock time at video t=0, end-anchored" (44-03) | `api.py:979-981`, `DATA-FLOW.md:124` |
| The endpoint has NO concept of one file ↔ many sessions, nor of deriving an offset for a clockless camera | `api.py:1001` (path is literally `{session_id}.mp4`) |
| `GET /video-url` returns a 3600 s signed URL + `origin_s`; bytes never proxy the API | `api.py:1029-1055` |
| **Server never persists true swim-start.** `recorded_at` is NOT written by `/process` → DB default `now()` = upload/processing time, not push-off time | `api.py:311-325` (insert has no `recorded_at`); `grep recorded_at api.py` → none |
| The phone knows the real start (`sessionStartPhoneMs` in CSV META) but it is dropped at write time | memory `project_video_overlay_sync`; not in `session_row` |
| The web already computes an end-anchored origin when none is stored (Phase 61-03) | `DATA-FLOW.md:393-395` |
| 5 of 62 live sessions have `video_path` set but `video_origin_s` NULL | `DATA-FLOW.md:497,567` |
| A velocity+video overlay that plays the two in sync already exists | Phase 64 (`sessions.acceleration_profile`, SVG overlay, drag-to-scrub) |

---

## The sync model (V1)

```
External clip (any clock)         Encoder session (session clock)
        |                                   |
   [push-off frame] <--- coach aligns ---> [swim-start on velocity trace]
        |                                   |
   video t = t_push                    session t = s_push
        |                                   |
        +----> video_origin_s = s_push − t_push  (session-clock time at video t=0)
                    stored via POST /sessions/{id}/video
                    read by the Phase-64 overlay, unchanged
```

- **Robust** because it depends on a shared physical event, not a shared clock.
- **Minimal** because `video_origin_s` already means exactly this and already has a reader.
- **Manual nudge** = re-POST an adjusted `video_origin_s` (the endpoint already supports origin-only
  updates with no file).

**Friction floor (the user's priority is minimal friction, no CV):** syncing a *clockless* camera
needs exactly one common instant identified. The only ways to supply it are (1) a shared clock —
impossible for an external camera, (2) CV auto-detect — rejected, distrusted underwater, or (3) one
human mark. **The floor is one gesture per clip** (drag to push-off → tap Sync); you cannot go lower
without accepting (1) or (2). In V1 that gesture is *small* because per-session clips are one swim
each, so the push-off sits a second or two from the clip start — a nudge, not a hunt. The
playhead-hunt problem (and thus the clock-hint's payoff) only appears in the deferred long-take case.

---

## Risks and things this will expose

- **R1 — GoPro browser playback is the real robustness gap (bigger than the sync math).** 4K / HEVC
  `.mov` frequently will **not** play in a browser `<video>` element, and GoPro files are large
  (upload timeout on Railway/Supabase, storage cost in the `videos` bucket). V1 needs a stated
  stance: recommended container/codec (H.264 `.mp4`), a size cap, and whether unplayable formats are
  rejected with guidance vs. transcoded (transcode = out of V1 unless plan says otherwise). **This,
  not the offset, is where "how robust is it" actually bites.**
- **R2 — clock hint is weak by construction** (no persisted true swim-start, unreliable camera
  clocks). Fine because align is primary (D2/D3); do not let a future clock-hint tempt anyone into
  making it authoritative.
- **R3 — storage/1:1 reuse means a re-upload replaces `{session_id}.mp4`.** Correct for one clip per
  session; becomes wrong the moment use case 1 arrives (D1 accepts the later migration).
- **R4 — second migration accepted.** If use case 1 is needed sooner than expected, the shared-asset
  model is a separate schema + web change. User chose MVP-first knowingly.

---

## For `/paul:plan` — open design calls

1. **Does the web have ANY video-upload affordance today, or is upload iOS-only?** Phase 61 shipped a
   *read-only* `/app/sessions/[id]/video` route; there may be no web upload UI at all. This sizes the
   web work. (Check `web/` during planning.)
2. **Which web surface hosts the align UI** — extend the read-only `/video` route, the Phase-47
   annotate page (already has synced video), or the Phase-64 overlay on the main session page?
3. **Snap mechanic (A1)** — programmatic "snap to detected swim-start," or pure "coach parks video
   playhead + trace cursor, we compute the delta"? The latter needs no detector and is dead simple.
4. **Format/size policy (R1)** — recommended codec, max size, reject-vs-accept unplayable files.
5. **Backend delta** — confirm `POST /sessions/{id}/video` needs nothing beyond maybe a size guard;
   confirm the web can call it with a coach JWT the same way iOS does.

---

## Files likely in scope

| File | Change |
|---|---|
| `web/` (video/annotate/session page) | External-clip **upload** + **push-off align** scrubber + **manual ± nudge** → POST `video_origin_s`. The bulk of the phase. |
| `api.py` | Likely **none**; confirm the existing `/sessions/{id}/video` endpoint serves a web upload + arbitrary origin. Possible small size/format guard. |
| `DATA-FLOW.md` / `CLAUDE.md` | Document the external-clip origin derivation (visual align) vs. the phone end-anchor; note V1 = 1:1, use case 1 deferred. |
| `tests/test_api.py` | If any endpoint behavior changes (guard/validation); otherwise none. |

Untouched: `metrics.py`, `vel_acc_extraction.py`, `annotations.py`, `supabase/` (no schema change in
V1), and the entire mobile repo.

---

## Carried out (recorded, not scoped here)

- **Use case 1** (one long take → many sessions) and its shared-asset model `(video_asset_id,
  offset_s)` — deferred follow-up phase (D1). Must anchor each session independently, never by
  ordinal (scrapped-session trap).
- **Clock-based auto-match / metadata pre-fill** (D3) — hint layer, revisit post-MVP; needs a
  persisted true swim-start to be worth building.
- **Persisting `sessionStartPhoneMs` as an absolute swim-start** — prerequisite for R2/clock hint,
  out of V1.
- **Multiple simultaneous cameras per session** (deck + underwater) (A2).
- **Server-side transcode** of unplayable GoPro formats (A3/R1) — decide in plan, likely future.
- **iOS external-camera upload** — web-first (D4); revisit only if coaches want to import from the
  phone's camera roll.
- **CV push-off auto-suggest** — a *future, optional* polish that SUGGESTS a candidate frame the coach
  still confirms/overrides; never the sole authority (user distrusts CV underwater — D2). Not V1.

---

## Success criteria

- [ ] From the **web coach portal**, a coach can upload an external clip (e.g. a GoPro `.mp4`) to an
      existing session.
- [ ] The coach can **align to push-off in one action** and the Phase-64 velocity overlay then plays
      in sync; `video_origin_s` is persisted.
- [ ] A **manual ± nudge** adjusts and re-saves the origin (origin-only update, no re-upload).
- [ ] The existing **phone-camera** sync path is unchanged (still end-anchored).
- [ ] A **documented format/size policy** (R1), with browser playback verified for at least the
      recommended format.
- [ ] Use case 1 is **explicitly out**, with the shared-asset follow-up sketched so the later
      migration is a known, not a surprise.
- [ ] Backend delta is confirmed **minimal** (ideally zero code) and any change is tested.
