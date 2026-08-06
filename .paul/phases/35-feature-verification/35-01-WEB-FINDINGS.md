# 35-01 Web Verification Findings

Verification of every web-facing Swimnetics feature. Local dev (`next dev`, Turbopack,
Next 16.2.9, port 3000) first; prod spot-check (Vercel + Railway) appended in Task 3.
Local `.env.local` points at the LIVE prod Supabase + Railway, so portal/report data is real.

Status legend: **WORKING** / **BROKEN** / **DEFERRED** (out of this plan's scope or blocked).

---

## Task 1 — Public surfaces (local) ✅

| Surface | Status | Evidence |
|---------|--------|----------|
| `/` Hero | WORKING | Eyebrow "VELOCITY INTELLIGENCE", H1 "Stroke-level analysis.", research-grade-lab subtext, Get early access / See how it works CTAs (screenshot). |
| `/` 3D device model | WORKING | `/models/device.glb → 200`; real GLB paints (encoder housing + tethered spool in screenshot), not the placeholder. THREE.Clock deprecation **warning** only (non-blocking). |
| `/` Sample velocity chart | WORKING | Renders with axes (0–5.6s, 0–2.2 m/s) + "arm pull" marker; **glide marker absent** (Phase 30 change confirmed). Hover tooltip fires: `"2.70 s | Speed : 0.99 m/s"`. |
| `/` Metrics cards | WORKING | All six with sample values: 34 spm, 1.6 m, 8%, ±5%, 22%, 6.4 s @ 15 m. |
| `/` section order | WORKING | Hero → Chart (REAL DATA) → Features (METRICS + PLATFORM) → How it works → Pricing. |
| `/` Pricing | WORKING | Current model: DEVICE $300 one-time + CLOUD $20/swimmer/month (optional). No Stripe wiring (by design). |
| Nav / Footer wordmark | WORKING | Text "SWIMNETICS" in Nav + Footer; no WaveMark (Phase 30). Footer contact `info@swimnetics.com`; FAQ + Privacy links present. |
| `/faq` | WORKING | Title "FAQ — Swimnetics", H1 "Frequently asked questions", 8+ Q&A headings, no console errors. |
| `/privacy` | WORKING | Title + H1 "Privacy Policy", 10 sections, cloud-video disclosure present, "Last updated: June 14, 2026", no console errors. |
| `/report/[token]` invalid token | WORKING | Junk token → handled "This report isn't available" message, no crash; network shows `GET <railway>/reports/<junk> → 404` (clean, route-specific). |
| `/report/[token]` valid token | WORKING | Real token from reports list → "Sid's Progress Report" (first-name only, Phase 24), ImprovementHero count-up deltas (Avg Speed +7.9%, Top Speed +25%, Stroke Rate +1.3%, DPS +11%, Lap Time +7.9% faster, Consistency −17%) + 6 "Session by session" MetricTrend charts; no console errors. |

**Console/network across /, /faq, /privacy, /report:** zero uncaught errors; zero failed
requests except the intended 404 on the junk report token. Only non-error: THREE.Clock
deprecation warning on the home 3D scene.

---

## Task 2 — Authenticated coach portal (local, live data) ✅

Signed in as the test coach (tzheng846@gmail.com) against live Supabase + Railway.

| View | Status | Evidence |
|------|--------|----------|
| `/login` | WORKING | Email/password form; valid creds → Supabase `auth/v1/token` 200 → redirect to `/app`. |
| Dashboard `/app` | WORKING | 7 athletes with latest-session key metrics (e.g. Connor 0.96 m/s / 23.4 spm / 2.45 DPS; Sid Kao 1.25 / 44.3 / 1.78) or "No sessions yet". |
| Athletes `/app/athletes` | WORKING | 7 on roster (stroke, head–waist, parent-email status, Edit). Add Athlete modal opens with name + head–waist fields + Save/Cancel (not submitted — avoided data pollution). |
| Sessions list `/app/sessions` | WORKING | 20 session cards (date, stroke, rate/speed/dist) from live data. |
| Session report card `/app/sessions/[id]` | WORKING | Full card: session metrics, start-phase (dive/pulldown), efficiency block (DPS/impulse/coast/ISI CV/arm-peak CV/fatigue), velocity chart (m/yd), time-to-distance presets (5.75 s @ 10 m), data-quality card (cycles/outliers/implausible/dropout) **with both caveats** (implausible-duration warning + kick-unreliable note). Simple/Advanced toggle, star, name edit, notes. No console errors. |
| Railway write path (PATCH /sessions) | WORKING | Toggled session star ☆→★ → `PATCH <railway>/sessions/{id} → 200`; toggled back ★→☆ to restore. End-to-end `apiFetch` → Railway write confirmed; **no data left changed**. |
| Compare `/app/compare` | WORKING | A/B athlete+session selectors; two Sid Kao sessions → overlaid velocity chart (aligned at t=0) + MetricDeltaTable with direction-aware Δ (Avg Speed +7.9%, Max +24.6%, DPS +11.0%, Glide −55.9%, Fatigue +1794% on a noisy baseline). |
| Reports `/app/reports` | WORKING | ReportBuilder (swimmer multi-select + Select all, From/To range, 6 metric checkboxes incl. Lap Time per Phase 24, parent note, Generate). ReportSendList shows 4 existing reports with Copy link / Copy all links / delete. Did not generate a new report (used an existing token for the /report render). |

**Console across all portal views:** zero uncaught errors.

**Minor (non-blocking) observations:**
- Dashboard shows "Lucas · May 23 — No sessions yet" (a date alongside "no sessions"); cosmetic — latest-session metric likely null. Logged, not a defect.
- Junk test sessions exist (Test2 118.7 spm / 0.03 m/s) — expected wavelet ceiling-railing on bad data (`segmentation_reliable=False`), not a web bug.

---

## Task 3 — Live /coach/chat + prod spot-check

### AI coaching chat — ✅ RESOLVED (was a prod config gap, now fixed)
**Update 2026-06-17:** User set `ANTHROPIC_API_KEY` on Railway, redeployed, and verified the
chat working. AC-3 satisfied. Original finding retained below for the record.


- On the Sid Kao session, sent "In this session, how consistent was my stroke-to-stroke
  speed?" → `POST <railway>/coach/chat → 503`, body `{"detail":"Coaching not configured"}`.
- Root cause: `api.py:815` returns 503 when `ANTHROPIC_API_KEY` is unset on the backend.
  **The key is NOT set on live Railway** — contradicts the pre-verify assumption that it was.
  The endpoint code is deployed (it returns the specific guard message + enforces auth first:
  unauth `POST /coach/chat → 401`), only the env var is missing.
- Frontend behavior: **WORKING / graceful** — CoachChat shows the question then "Coaching
  not configured" inline; no hang, no crash.
- **Status: DEFERRED (user action).** Set `ANTHROPIC_API_KEY` in Railway → then re-verify the
  tool-use loop (single-session, cross-session trend, team-wide "who's lagging", drill request,
  off-topic guardrail) + the structured `data` payload. **AC-3 unverified until the key is set.**

### Prod spot-check (deployed Vercel + Railway) ✅
| Probe | Result |
|-------|--------|
| `GET <railway>/health` | 200 `{"status":"ok"}` |
| `GET <railway>/reports/{valid token}` | 200 (parent links work in prod) |
| `GET <railway>/reports/{junk}` | 404 `{"detail":"Report not found"}` (route-specific; drift resolved) |
| `POST <railway>/coach/chat` unauth | 401 (auth enforced before the key check — correct ordering) |
| `https://swimnetics.com` | 200 — SWIMNETICS wordmark, "Stroke-level" hero, "early access" CTA |
| Prod pricing | New model present (one-time device + "/ month" + "swimmer" + info@swimnetics); no stale $15 flat. Matches local. |

Local↔prod divergence: none on web content. Only divergence is the **chat config gap** (above),
which is environment, not code.

---

## Summary

| Area | Verdict |
|------|---------|
| Public marketing + report surfaces (local + prod) | **WORKING** |
| Authenticated coach portal (all views + reversible write) | **WORKING** |
| Parent report render (valid + invalid token) | **WORKING** |
| AI coaching chat — frontend | **WORKING** (graceful error handling) |
| AI coaching chat — backend live | **WORKING** — `ANTHROPIC_API_KEY` set on Railway + redeployed + user-verified 2026-06-17 (AC-3 satisfied) |

**Web code bugs found: 0** → no `web/**` fixes made (boundary respected). The single broken
behavior is a prod environment-config gap (chat key), owned by the user; everything the code
controls works against live data.
