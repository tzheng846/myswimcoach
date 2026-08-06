# 29-01 SUMMARY — Marketing Content (FAQ + sales email)

**Status:** ✅ Complete — checkpoint approved 2026-06-14. Loop closed.

## What was built

- **`web/app/faq/page.js`** (new) — FAQ page mirroring the `privacy/page.js` pattern
  (Nav + Footer, dark tokens, max-w-3xl). 8 Q&As derived from the 2026-06-14 coach
  sales roleplay: value vs. stopwatch, ease of use, coach-not-replaced, pool-time/
  throughput, durability (PETG/UHMWPE/breakaway), supported strokes (honest —
  breaststroke validated, others "early quality"), pricing, data safety (links /privacy).
  Early-access CTA block.
- **`web/components/Nav.js`** — added `{ href: "/faq", label: "FAQ" }`.
- **`web/components/Footer.js`** — added FAQ link above Privacy Policy.
- **`web/components/marketing/Pricing.js`** — replaced the single $15/swimmer/month card
  with a two-card model: **$300 one-time device** (basic metrics) + **$20/swimmer/month
  optional cloud tier** (video storage, long-term tracking, history, parent reports).
- **`web/app/privacy/page.js`** — updated for the cloud video tier: §2 now discloses
  optional cloud video storage (and that video stays on-device without the tier), §4
  Supabase bullet covers video, §6 children's section notes stored video may show a
  minor under the same club-consent model. LAST_UPDATED → June 14, 2026.
- **`marketing/sales-pitch-email.md`** (new, gitignored) — copy-paste cold-outreach email,
  consistent with the FAQ + site (pricing, early-access CTA).
- **`.paul/PROJECT.md`** + stale `web/README.md` pricing line updated to the new model.

## Key decisions (2026-06-14)

- **New pricing model** ($300 device + $20/swimmer/mo cloud) supersedes the Phase 23
  $15/swimmer/month presentation. Drove the Pricing.js + privacy + README ripple.
- **Cloud tier stores video** — user chose to advertise it AND update the live Privacy
  Policy to match (rather than soften/defer), keeping the site truthful.
- **CTA** = early-access reach-out (match existing site posture), not a free-trial promise.
- **COPPA / age floor:** user asked whether a 13+ requirement reduces legal overhead.
  Conclusion: a real, enforced 13+ floor removes COPPA's under-13 regime, but doesn't
  cover state minor-protections or the sensitivity of storing minors' video; the B2B
  club-collects-verifiable-consent model is still needed for 13–17. **Final decision
  (2026-06-14): adopt 13+ "for now" for test demos.** privacy/page.js §6 retitled
  "Minors and age requirement" — states 13+ floor + "we do not knowingly collect data
  from children under 13" + club collects verifiable parental consent at registration.
  §1 cross-ref updated. Recorded as a PROJECT.md constraint. (Attorney review still owed.)

## Verification

- `npm run build` (web/) compiles clean; `/faq` prerendered as static.
- Preview: `/faq` renders with FAQ in Nav; homepage `#pricing` shows the two-card
  $300/$20 model; footer shows FAQ + Privacy Policy. No console errors.
- No `$15` left anywhere under `web/`.

## Follow-ups / open items

- ⚠ **Attorney review still owed** before a paid pilot with minors — now elevated because
  the policy advertises cloud storage of minors' video (COPPA-sensitive). See memory
  legal_privacy_status; ToS with operative parental-consent clause also still owed.
- **Deploy is user-owned.** Push to `main` → Vercel auto-deploys web/. This push ALSO
  ships the Phase 28 privacy page to prod for the first time (was untracked).
- Scope note: `ESP_32_V5/ESP_32_V5.ino` + `video_sync.py` were already modified in the
  tree (unrelated to this phase) — excluded from the Phase 29 commit.
- `marketing/sales-pitch-email.md` is gitignored (`*.md`, line 16) — local-only artifact.
