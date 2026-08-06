---
phase: 40-website-redesign
plan: 02
subsystem: ui
tags: [nextjs, tailwind-v4, shadcn, web3forms, marketing, design-system]

requires:
  - phase: 40-website-redesign (40-01)
    provides: shadcn primitives, iOS light-purple tokens, ContactDialog, scroll-aware Nav
provides:
  - Full marketing site on the Template-B light-purple theme (Features, HowItWorks, login, faq, privacy)
  - RequestQuote section (gradient CTA + ContactDialog) replacing public pricing; Pricing.js removed
  - Pricing removed sitewide (incl. the FAQ cost answer); every CTA routes to the contact dialog
affects: [future web UI work, any new marketing pages]

tech-stack:
  added: []
  patterns:
    - "Nav `overHero` prop: transparent-over-gradient only on pages with a dark hero (homepage); all other pages start solid"
    - "Homepage hero pulled up under the sticky transparent nav via -mt-16 so the gradient sits behind it"

key-files:
  created: [web/components/marketing/RequestQuote.js]
  modified: [web/components/marketing/Features.js, web/components/marketing/HowItWorks.js, web/app/page.js, web/app/login/page.js, web/app/faq/page.js, web/app/privacy/page.js, web/components/Nav.js]

key-decisions:
  - "FAQ 'How much does it cost?' answer scrubbed of $300/$20 (pricing-removal directive) — content exception to retheme-only"
  - "Pricing.js deleted rather than left as dead code (pricing removed sitewide)"

patterns-established:
  - "Marketing pages wrap content in a bg-paper light container; portal stays dark"
  - "Nav overHero distinguishes dark-hero pages from light pages"

duration: ~45min
started: 2026-06-22T05:00:00Z
completed: 2026-06-22T05:50:00Z
---

# Phase 40 Plan 02: Remaining Marketing Sections Summary

**Completed the marketing-site redesign: Features + HowItWorks restyled to the iOS light-purple theme, a "Request a quote" gradient CTA section (reusing 40-01's ContactDialog) replaced public Pricing, login + /faq + /privacy rethemed to light, and pricing was removed sitewide — including the FAQ cost answer.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Tasks | 2 auto + 1 human-verify checkpoint (approved) |
| Files created | 1 |
| Files modified | 7 |
| Files deleted | 1 (Pricing.js) |
| Build | `next build` green (12 routes) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Body sections light + Request-a-quote replaces Pricing | Pass | Homepage = Hero → Features → HowItWorks → RequestQuote (gradient `135deg`, id="pricing", no prices) → Footer; Pricing.js deleted, no import remains; visible text price-free |
| AC-2: Login restyled, auth intact | Pass | Paper bg, periwinkle eyebrow, shadcn Input (`#e8e4f2`) + brand Button (`#4e148c`); supabase signInWithPassword + router.replace untouched |
| AC-3: /faq + /privacy rethemed, content preserved | Pass | Both light; legal copy intact; FAQ cost answer scrubbed of $300/$20 → request-a-quote; bottom CTA → ContactDialog |
| AC-4: Build + no portal regression | Pass | Build green; no portal/report files touched; dark `--color-*` tokens unchanged |
| AC-5: Visual direction confirmed | Pass | Checkpoint approved 2026-06-22 after the nav fixes |

## Accomplishments

- Entire public marketing surface (/, /faq, /privacy, /login) now matches the iOS app's light-purple theme.
- Public pricing removed everywhere; the single Request-a-quote ContactDialog is the only conversion path.
- Two nav-visibility bugs (reported at the checkpoint) found and fixed before approval.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/marketing/Features.js` | Modified | Light token restyle (periwinkle eyebrows, brand metric values, light cards) |
| `web/components/marketing/HowItWorks.js` | Modified | Light restyle; brand number chips |
| `web/components/marketing/RequestQuote.js` | Created | Gradient CTA section + ContactDialog; id="pricing"; no prices |
| `web/components/marketing/Pricing.js` | Deleted | Pricing removed sitewide |
| `web/app/page.js` | Modified | Full section order; `Nav overHero`; `-mt-16` hero overlay |
| `web/app/login/page.js` | Modified | Light restyle + shadcn Input/Button (auth logic untouched) |
| `web/app/faq/page.js` | Modified | Light retheme; cost answer price-scrub; CTA → ContactDialog |
| `web/app/privacy/page.js` | Modified | Light retheme (legal copy untouched) |
| `web/components/Nav.js` | Modified | `overHero` prop (bug fix — nav visibility on light pages) |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Scrub the FAQ cost answer of $300/$20 | "Remove pricing" directive; published prices in the FAQ would contradict it | One content exception to retheme-only; flagged to user, accepted |
| Delete Pricing.js | Pricing removed sitewide; leaving it = stale dead code with old prices | File gone; no import references it |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 2 | Essential nav-visibility fixes |
| Scope additions | 1 | Nav.js added to files_modified (bug fix) |
| Deferred | 0 | — |

**Total impact:** Essential fixes, no scope creep.

### Auto-fixed Issues

**1. [UI] Nav invisible (white-on-light) at top of /faq + /privacy**
- **Found during:** human-verify checkpoint (user-reported)
- **Issue:** Nav's transparent top state assumed a dark hero behind it; on light pages the white links were invisible until scroll flipped it solid.
- **Fix:** added a `overHero` prop to Nav — only the homepage (dark gradient behind) gets transparent-at-top; all other pages start solid.
- **Files:** web/components/Nav.js, web/app/page.js
- **Verification:** /faq nav at scrollY 0 = paper@90% bg + `#2c0735` wordmark.

**2. [UI] Homepage nav on a white strip above the gradient**
- **Found during:** human-verify checkpoint (user screenshot)
- **Issue:** the sticky nav reserves a 64px row, so the hero gradient started below it; the transparent nav rendered on the white page, not over the gradient.
- **Fix:** `-mt-16` on the homepage `<main>` pulls the hero up under the nav so the gradient spans from y≈0 behind the transparent nav.
- **Files:** web/app/page.js
- **Verification:** DOM — heroTop≈1, nav band 0–65 transparent, white wordmark over the gradient; build green.

### Deferred Items

None.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Preview screenshot tool mis-scaled / timed out repeatedly | Used `preview_eval` computed styles + getBoundingClientRect as the authoritative verification |

## Next Phase Readiness

**Ready:**
- Phase 40 complete — the marketing site is fully redesigned and pricing-free.

**Concerns:**
- Web changes are uncommitted; user runs git (see transition for the branch + commit commands).
- Web3Forms may send a one-time verification email on the first lead — user to confirm.
- The coach portal + parent reports remain on the old dark theme (deliberately out of scope; a future phase if a matching portal redesign is wanted).

**Blockers:** None.

---
*Phase: 40-website-redesign, Plan: 02*
*Completed: 2026-06-22*
