# Phase Context

**Phase:** 71 — Video Surface Rework (modal-add + inline watch + annotate is the align surface)
**Discussed:** 2026-08-18 (`/paul:discuss`, 2 forks via AskUserQuestion)
**Status:** Ready for `/paul:plan`
**Decisions:** 9 (D1–D9). UAT-driven rework of Phase 69 + fixes the store/reader split that made a web-uploaded video "vanish."

⚠ **NUMBERING:** taken as 71 (no `71-*` dir existed). Phase 70's CONTEXT informally reserved 71 for
a free/back-breakout TODO from a concurrent Phase-65 session — nothing is built for it. If that lands
first, renumber this to 72.

---

## Why now

UAT on Phase 69 (shipped 2026-08-17, built blind with no live video/auth). The user recorded a session
with **no phone video**, then uploaded an **external** clip on the web expecting the report card to
look like a phone-recorded session (inline video + velocity overlay). Instead the report card showed
only a "Videos (1)" link bar, and the annotate page said **"no video attached."** The user suspected a
failed upload / backend error.

**It is neither.** The upload succeeded — the clip plays on the Videos page (image 3, `1/4 cameras`,
`synced`). The problem is a **store/reader split** baked into Phase 69's additive data model:

| Store | Written by | Holds |
|---|---|---|
| `sessions.video_path` / `video_origin_s` (legacy) | iOS phone upload **only** | the phone/primary video |
| `session_videos` table (Phase 69, patch_12) | web `POST /sessions/{id}/videos` | every web upload (role=`external`) |

Read surfaces disagree about which store they consult:

| Surface | Reads | Sees a web-uploaded external? |
|---|---|---|
| Report-card **inline player** | `video_path` only (`page.js:131`, `:414`) | ❌ → falls back to the "Videos (N)" link bar (image 1) |
| **Annotate** page | `video_path` only (`GET /annotations`, `api.py:797/811`) | ❌ → "no video attached" |
| Report-card **"Videos (N)" count** | unified `GET /videos` (`page.js:173`) | ✅ counts it (the "1") |
| **Videos** page | unified `GET /videos` | ✅ plays it (image 3) |

Net: **from the web, every upload becomes an "external," so the inline/annotate experience is
effectively phone-only.** Unifying the readers fixes the bug and the user's redesign at once.

The user's redesign, verbatim: *"add video should not be a new page. Upon clicking add video it should
give popup asking for file. Then it loads it however you like on the report page. Then the user can go
into annotation page to line up the multiple videos."* (The user referred to the Videos page as "the
annotation page" — they want the two merged, the clunky standalone page gone.)

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Root cause is a store/reader split, not a failed upload.** The fix is reader-side: every video read surface consults the unified `GET /sessions/{id}/videos` list. The user's already-uploaded external then reappears with **no data migration**. |
| **D2** | **"Add video" is a MODAL on the report card** (file picker popup) — no navigation to a separate page. (User.) |
| **D3** | **Report card plays ONE angle inline** with the velocity overlay (watch-only), restoring the image-2 experience: phone video if present, else the first uploaded angle. (User: *"one angle + trace for now."*) |
| **D4** | **Keep the door open for "all angles" soon.** Report-card inline must be built on the unified data flow + a panel seam so a multi-camera synced player can replace the single-angle view without a rewrite. (User: *"keep open for support for all angles soon."*) |
| **D5** | **The annotate page becomes the alignment surface and shows ALL cameras at once** — each alignable to push-off (the Phase 69 `CameraTile` workflow folded in). (User chose "All cameras at once.") |
| **D6** | **The standalone `/app/sessions/[id]/videos` page is DELETED.** Its three jobs relocate: add → report-card modal (D2); view → report-card inline (D3); align → annotate (D5). |
| **D7** | **Data model unchanged** (Phase 69's additive model stays). Web uploads remain externals in `session_videos`; `video_path` stays the phone's slot. The fix is READER-side (unify on `GET /videos`), not a schema change or backfill. |
| **D8** | **Marking workflow preserved on the annotate page.** One "active" camera (default: phone, else first) drives the existing playhead / seek / M-key / frame-step marking wiring; the other cameras render as alignable tiles. The ground-truth marking + recompute path (Phase 47/57) is untouched in behaviour. |
| **D9** | **Untouched:** mobile (separate repo; the phone path is already first-class), the read-only `/app/sessions/[id]/video` fullscreen route, the signal pipeline / `metrics.py`, and Phase 70's video↔session matching UI (complementary — both build on `session_videos`; keep them from colliding). |

---

## Scope

- **In:** report-card add-video modal; report-card inline one-angle watch panel reading the unified
  list; annotate page hosts + aligns all of a session's cameras; delete the Videos page/route; unify
  every video read surface on `GET /videos`.
- **Out (this phase):** the multi-camera synced player *on the report card* (designed-for, not built —
  D4); any mobile change; Phase 70's batch matching; data migration (unnecessary — D1/D7).

---

## For `/paul:plan` — open design calls

1. **Report-card modal upload target.** Simplest that satisfies D1/D3/D7: keep posting to
   `POST /videos` (external) and make the inline panel + annotate read `GET /videos`. Alternative:
   promote a lone web upload to the primary slot when the session has none. Recommend the former (one
   reader change fixes every surface, including the already-orphaned external).
2. **Inline watch-only panel over the unified list.** `VideoTracePanel`/`VideoPane` currently fetch
   the signed URL via `GET /video-url` (legacy). The unified `GET /videos` already returns a per-camera
   `url` + `origin_s`; generalize the watch-only inline path to play the chosen camera from that list
   (it already takes a `{…, origin_s}` shape; readOnly means no origin-save path is needed there).
3. **Annotate multi-cam layout.** How the camera tiles coexist with the marking chart + tools without
   bloating an already-dense page; which camera is "active" for marking (D8) and whether the coach can
   switch it. Reuse `CameraTile` vs. a tighter layout.
4. **Preserve a synced-player path for D4.** Verify what remains of Phase 69-03's one-timeline synced
   player after the "annotate-style tiles" rework, so the report card can adopt it later for "all
   angles."
5. **Add-more-angles from the report card.** Whether the modal only seeds the first angle (further
   angles added/aligned on annotate) or can add up to the 4-camera max; keep the report-card VIEW at
   one angle regardless (D3).

## Files likely in scope

| File | Change |
|---|---|
| `web/app/app/sessions/[id]/page.js` | Add-video modal; inline one-angle panel reading `GET /videos`; drop the "Videos (N)" link bar / "Manage videos" flow. |
| `web/app/app/annotate/[id]/page.js` | Host + align all cameras (multi-cam); read the unified list; preserve marking wiring on an active camera (D8). |
| `web/app/app/sessions/[id]/videos/page.js` | **Delete** (route removed, D6). |
| `web/components/portal/VideoPane.js`, `VideoTracePanel.js`, `CameraTile.js` | Reuse/adapt for the modal, the unified-list watch panel, and the annotate multi-cam grid. |
| `web/components/portal/AddVideoModal.js` (likely new) | The report-card file-picker popup. |
| `api.py` | `GET /annotations` (or the annotate page) must surface externals — likely have annotate read `GET /videos` directly; **no schema change expected**. |

Untouched: `metrics.py`, `vel_acc_extraction.py`, mobile repo, `/app/sessions/[id]/video` (read-only).

## Success criteria

- [ ] A **web-uploaded video shows inline on the report card** (one angle + velocity overlay) and
      **appears on the annotate page** — the exact thing that failed in UAT.
- [ ] **"Add video" opens a modal** on the report card; there is no separate add-video page.
- [ ] The **annotate page shows and aligns every camera** on the session (push-off align each).
- [ ] The **standalone Videos page/route is gone** and nothing links to it.
- [ ] The user's **existing orphaned external reappears** with no manual migration.
- [ ] Inline panel is built so an "all angles synced" upgrade is a drop-in later (D4).
- [ ] **No mobile change, no pipeline/metrics change**; test suite green.

---

## 71-02 scope refinement (UAT on 71-01, 2026-08-18)

71-01 (report card) verified on localhost. Two UAT findings reshape 71-02:

| # | Decision |
|---|---|
| **D10** | **Remove "Sync to push-off" ENTIRELY** — `VideoPane.alignToPushoff` + its button, and `CameraTile.syncToPushoff` + its button. User verbatim: *"I don't like the sync to pushoff. I don't even trust that the code can detect pushoff accurately."* The encoder dive → `baseline_end_s` align target is gone as a video-alignment mechanism. (⚠ Does NOT touch Time-to-Distance, which uses `baseline_end_s` separately — out of scope.) |
| **D11** | **Manual alignment = "point to the same moment" (two-point).** Coach scrubs the (active) camera to a clear instant (e.g. the push-off), then clicks that SAME instant on the trace themselves → `origin = clickedTraceTime − videoCurrentTime`; ±nudge fine-tunes. No auto-detection — the coach decides where the landmark is on the trace. Needs an explicit "align/set-sync" mode per camera, distinct from the existing stroke/seek/phase click tools (clicking the trace normally places a mark). |
| **D12** | **Annotate is the FULL video hub.** It reads the unified `GET /videos` (fixes "annotate has no video" — the external appears), hosts ALL cameras (attach more, view, two-point align, label, delete), and one "active" camera (default phone else first) drives the marking playhead/seek/M-key/frame-step. **DELETE `/app/sessions/[id]/videos` (route + page) AND the report-card "Manage / align" link that 71-01 added.** |
| **D13** | **Report card KEEPS its quick "Add video" modal + inline one-angle view** (and the existing "Annotate ›" link). It only loses the "Manage / align" link (D12). User chose "Keep both." |

⚠ **This supersedes the earlier D5/D8 push-off-align assumption for 71-02** — the annotate multi-cam
still uses `CameraTile`-style tiles, but push-off align is replaced by the D11 two-point flow, and
`CameraTile`/`VideoPane` lose their push-off code rather than gaining marking-only wiring.

---

## Follow-on surfaced 2026-08-18 (NOT this phase)

During re-discussion the user flagged *"hard to see everything with a small screen"* → clarified as
**tablet at poolside**. This is a **tablet-responsive layout** concern, not a video-data concern, and
71-02 makes it worse: D5/D12 turn the annotate page into a camera **grid** + trace + marking tools on
one page, densest exactly where the coach uses a tablet to sync/mark poolside. Neither Phase 70
(matching) nor 71 (this) targets tablet width.

**Deferred to its own phase** (candidate 72, once 71 ships and the 70/71/72 numbering contention is
resolved). Likely scope: responsive breakpoints for the annotate hub (stack/collapse camera tiles vs.
trace on ≤tablet), and a pass over the report card. Formalize via `/paul:discuss` when 71 is shipped.

⚠ **Sequencing decision (2026-08-18):** ship 71 first (verify → commit → push), THEN Phase 70
matching (its CONTEXT is ready), THEN the tablet layout above. 71 is already code-complete in the
working tree (build green, Videos route gone) — only UAT + commit remain.
