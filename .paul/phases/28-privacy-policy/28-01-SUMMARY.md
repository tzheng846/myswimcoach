---
phase: 28-privacy-policy
plan: 01
status: complete
completed: 2026-06-13
autonomous: false
files_modified: [web/app/privacy/page.js, web/components/Footer.js]
---

# 28-01 SUMMARY — Privacy Policy

## What shipped
- **`web/app/privacy/page.js`** (new) — static server-component Privacy Policy page
  at `/privacy`. Dark-theme site tokens, `metadata` export, "Last updated:
  June 13, 2026". Ten sections: (1) operator vs. club/coach relationship,
  (2) information collected, (3) narrow use + no-sale/no-ads/no-profiling,
  (4) named sub-processors (Supabase, Railway, Stripe, with policy links),
  (5) tokenized parent reports, (6) children's privacy / COPPA (club obtains
  parental consent; parent contact path for review/deletion), (7) retention &
  deletion (session delete removes record + raw CSV), (8) security, (9) CA /
  CCPA rights, (10) changes + contact.
- **`web/components/Footer.js`** — added a "Privacy Policy" `Link` to `/privacy`
  (next/link, muted→primary hover). Surgical; added the `Link` import.

## Verification (preview, port 3000)
- `/privacy` renders; all 10 `<h2>` present; h1 = "Privacy Policy".
- "We do not collect video" claim present (matches reality — video stays
  on-device, not uploaded).
- Footer `a[href="/privacy"]` present.
- No console errors; screenshot confirmed styling consistent with the site.

## Key content decisions
- **No video claim** — policy explicitly states video is not collected/stored
  server-side. MUST be revisited if Phase 26 video is ever uploaded to cloud
  storage (see the 2026-06-13 storage discussion — leaning toward cloud later).
- **Stripe named** as a sub-processor though no client UI calls billing yet
  (it exists in the backend). Drop if billing naming is premature.
- **Contact = hello@swimnetics.com** (reused footer address; no privacy@ alias).

## Boundaries honored
- Privacy Policy ONLY. No backend changes. Footer touched only to add the link.

## Required follow-ups (OUT OF SCOPE here — do before any PAID pilot with minors)
1. **Terms of Service** — holds the *operative* "club obtains verifiable parental
   consent" clause; the privacy page only *describes* it. This is the document
   that most needs drafting next.
2. **Attorney review** of the children's-data / COPPA section before relying on it
   commercially. The page is template-grade, self-drafted, NOT attorney-reviewed.
3. **Deploy is user-owned** — Vercel auto-deploys on push to main (no local CLI/token).

## Living document
User note (2026-06-13): this policy WILL change over time — update the
"Last updated" date and revisit §2 (video), §4 (sub-processors), and §6
(children's) whenever data practices change. See memory `legal_privacy_status`.
