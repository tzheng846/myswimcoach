# Phase Context

**Phase:** 70 — Video-Session Matching (manual-default + optional QR slate)
**Discussed:** 2026-08-17 (`/paul:discuss`, 2 forks via AskUserQuestion)
**Status:** Ready for `/paul:plan`
**Decisions:** 9 (D1–D9). Core is web-only + robust; QR is a designed opt-in follow-on gated on a mobile build.

⚠ **NUMBERING:** taken as Phase 70. A concurrent Phase-65 session logged an informal "TODO #69 →
should renumber to #70" (free/back breakout, Mode-A residual) — that is NOT this phase; this phase
owns 70 (dir + CONTEXT exist). The 65-session's TODO should take 71.

---

## Why now

Matching external-camera clips to sessions is the live annoyance. The user, verbatim:

> *"it's super annoying trying to pick what video matches with what session."*

The first instinct — auto-match by clip **creation-time + duration** — was **explored and rejected by
the user**, correctly:

> *"the external camera may not be a gopro. It could be dji or some off brand camera. Who's to say
> that date of creation is accurate? … there's no guarantee that the duration would match. the user
> might accidentally record too much or too little."*

So metadata heuristics are OUT as a decision-maker. The user then scoped the real answer:

> *"qr is meant to be a nice to have feature, if the coach wants to utilize it. Manual matching is
> the default. the logic should be robust to any setups. … cameras usually don't see the phone if
> they're underwater. but for over the water cameras coaches should be able to easily set up qr code
> scans."*

**The reframe that settles it:** an external camera has no data link and (per the user) untrustworthy
metadata, so its only honest input is *what it filmed*. Any *deterministic* auto-match must therefore
present the session's identity to the camera at capture time — a capture-time action is inherent to
reliable auto-matching, not a QR quirk. QR is simply the most robust such token (a **fiducial** —
reliable machine-read even skewed/glared, categorically unlike the semantic underwater CV the user
distrusts). But since it needs a deliberate setup, it is an **assist**, not the default.

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Manual matching is the DEFAULT and must be robust to ANY setup** — no camera, off-brand camera, underwater camera, wrong clocks, sloppy durations. It never depends on a camera existing or on metadata being trustworthy. (User: *"Manual matching is the default. the logic should be robust to any setups."*) |
| **D2** | **Robust manual = match by CONTENT, not filename or metadata.** Show a **thumbnail / preview frame** of each clip so the coach recognizes the swim. Time/duration may be *displayed* as a clearly-optional soft hint, but **metadata never auto-decides** anything (the user showed creation-time + duration can't be trusted). |
| **D3** | **Likely a batch assignment UI** — upload/point at multiple clips, see them as thumbnails, assign each to a session — since the pain is pairing many opaquely-named files across sessions, not the single per-session add that Phase 69 already has. Exact UX is a plan call. |
| **D4** | **QR is OPT-IN and strictly an accelerator.** It pre-fills the match when present and **always degrades to D1** when absent (no QR / off-brand / underwater / coach forgot). Never a hard dependency. |
| **D5** | **QR decode runs CLIENT-SIDE in the browser** (jsQR on sampled frames of the uploaded clip) — **no server CV dependency**, nothing heavy on Railway. |
| **D6** | **QR token = a phone-generated recording token stored on the session** (new `sessions.recording_token` or reuse of the dropped CSV-META start-stamp). QR encodes it; match = find the session with that token. **Scrapped sessions match nothing → stay manual/unmatched** — which correctly handles the scrapped-swim case raised back in Phase 67. |
| **D7** | **QR needs a MOBILE change** (the phone displays the QR at record start) — separate repo, paid EAS build. QR is **useless until BOTH the mobile display and the web decode exist**, so building web-decode first has no value. Sequencing: ship the robust manual UI first (immediate, web-only); QR is a follow-on (mobile + web + token together) built when a mobile build is worth it — possibly its own phase. |
| **D8** | **Sync is unchanged** (push-off align, Phase 67). QR does **matching only**; a coarse-sync bonus from the QR frame is optional/later, not V1. |
| **D9** | **Underwater cameras: QR is not expected to work** (they can't see a hand-held phone) — accepted; those clips use manual (D1). QR targets over-water cameras the coach can point at. |

---

## Scope

- **Committed core (this phase, web-only):** content-driven **manual matching** — thumbnails/preview so
  clips are paired by recognition; batch assignment across sessions; soft (non-deciding) metadata hints.
  Builds on Phase 69's `session_videos` + `POST /videos`. Immediate value, no mobile, no CV, no camera
  assumptions.
- **Designed opt-in follow-on (gated on a mobile build):** the **QR slate** — mobile QR display +
  recording token (`sessions.recording_token`) + client-side browser decode (jsQR) that pre-fills the
  match. Captured here; sequenced after the manual core, likely a separate mobile-touching plan/phase.

---

## For `/paul:plan` — open design calls

1. **Manual UX shape:** a dedicated batch "match videos" page (dump clips → thumbnails → assign each to
   a session) vs an enhanced per-session picker that previews the selected clip before attaching. The
   pain (pairing many opaque files) argues for batch.
2. **Thumbnail generation:** client-side (draw a `<video>` frame to canvas at/after upload) vs stored.
   Client-side keeps it server-light and needs no schema.
3. **QR (follow-on):** `sessions.recording_token` column; jsQR frame-sampling strategy (how many early
   frames, at what interval); the match endpoint/lookup; the mobile QR-display plan.
4. **Coarse sync from QR?** Whether the QR frame also seeds a rough `origin_s` (push-off align still
   refines). Default: no, matching only.

## Files likely in scope

| File | Change |
|---|---|
| `web/` (new matching UI + thumbnails) | The robust manual matching surface (batch assign / content preview). |
| `web/components/portal/*` | Thumbnail/preview helpers; reuse the Phase-69 attach + `GET /videos`. |
| `api.py` | Possibly none for the manual core; QR follow-on adds a token store + match-by-token lookup. |
| `supabase/patch_13_*` | QR follow-on only — `sessions.recording_token`. |
| mobile repo (separate) | QR follow-on only — display the token QR at record start (EAS build). |

Untouched by the core: the signal pipeline, `metrics.py`, mobile (until the QR follow-on).

## Success criteria

- [ ] Manual matching works for **any** setup and is fast — clips are recognized by **content**
      (thumbnail/preview), paired across sessions without trusting filenames or metadata.
- [ ] Metadata (time/duration) is at most a **soft, ignorable hint** — it never makes an automatic match.
- [ ] QR (once the mobile half exists) **pre-fills** the match for slated over-water clips and
      **degrades cleanly to manual** when absent; scrapped swims stay unmatched.
- [ ] No server-side CV dependency (QR decode is client-side); no camera-brand or clock assumptions.
