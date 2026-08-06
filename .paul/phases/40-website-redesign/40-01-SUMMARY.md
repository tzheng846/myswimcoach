---
phase: 40-website-redesign
plan: 01
subsystem: ui
tags: [nextjs, tailwind-v4, shadcn, radix, web3forms, marketing, design-system]

requires:
  - phase: 38-mobile-redesign
    provides: iOS light-purple design tokens (src/theme/tokens.js) mirrored into the web palette
provides:
  - shadcn/ui foundation for web/ in plain JSX (Tailwind v4, no TypeScript)
  - iOS light-purple token set in globals.css (additive; portal dark tokens preserved)
  - reusable ContactDialog (name+email+message → Web3Forms email to tzheng846@gmail.com)
  - immersive gradient landing core (Nav, Hero + floating SampleChart card, Footer)
affects: [40-02 (remaining marketing sections), future web UI work, any shadcn use in web/]

tech-stack:
  added: [class-variance-authority, clsx, tailwind-merge, lucide-react, "@radix-ui/react-dialog", "@radix-ui/react-label", "@radix-ui/react-slot", tw-animate-css]
  patterns:
    - "shadcn components themed via brand-namespaced --color-* tokens (bg-brand etc.) to avoid colliding with the portal's --color-primary/accent/muted"
    - "Marketing pages paint their own light surface (bg-paper wrapper); global body stays dark for the portal"
    - "Single contact config in lib/site.js (WEB3FORMS_ACCESS_KEY); one ContactDialog behind every CTA"

key-files:
  created: [web/components.json, web/lib/utils.js, web/lib/site.js, web/components/ui/button.jsx, web/components/ui/card.jsx, web/components/ui/badge.jsx, web/components/ui/dialog.jsx, web/components/ui/input.jsx, web/components/ui/label.jsx, web/components/ui/textarea.jsx, web/components/marketing/ContactDialog.js]
  modified: [web/app/globals.css, web/components/marketing/Hero.js, web/components/marketing/SampleChart.js, web/components/Nav.js, web/components/Footer.js, web/app/page.js, web/package.json]

key-decisions:
  - "Hand-authored canonical shadcn component files instead of the interactive CLI (Next 16 + Tailwind v4 + JS make the CLI unreliable)"
  - "Themed shadcn to brand-namespaced tokens so the coach portal's --color-primary/accent/muted are untouched"
  - "CTA = ContactDialog form-to-email via Web3Forms (revised from a scheduling link, per user)"

patterns-established:
  - "New marketing tokens are additive in the same @theme block; never recolor the dark portal tokens"
  - "Scroll-aware Nav: transparent-glass over the gradient hero → solid lavender on scroll, with the CTA variant swapping accordingly"

duration: ~50min
started: 2026-06-21T00:00:00Z
completed: 2026-06-21T00:50:00Z
---

# Phase 40 Plan 01: Website Redesign — Landing Core Summary

**Flipped the marketing landing from the dark-blue theme to the iOS immersive purple→periwinkle gradient (Template B) on a new shadcn/ui + Tailwind-v4 foundation, and replaced public pricing with a "Request a quote" contact dialog that emails leads to tzheng846@gmail.com via Web3Forms — all without disturbing the coach portal.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~50 min |
| Tasks | 2 auto + 1 human-verify checkpoint (approved) |
| Files created | 11 |
| Files modified | 7 |
| Build | `next build` green (12 routes) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: shadcn + iOS tokens, portal untouched | Pass | Build green; dark `--color-bg #07090e`/`--color-navy`/`--color-primary` still present; `/privacy` renders dark (`#07090e`/`#f0f2f5`) |
| AC-2: Immersive gradient hero | Pass | Hero bg = `linear-gradient(160deg,#2c0735→#4e148c→#613dc1→#858ae3)`; "analysis." accent `#97dffc`; white 896px chart card straddles the fold |
| AC-3: Nav glass→solid on scroll | Pass | Top: transparent bg, white wordmark, white/10 border. Scrolled: paper@90% bg, `#e8e4f2` border, `#2c0735` wordmark |
| AC-4: Contact form emails the lead | Pass | One ContactDialog (name+email+message) behind both CTAs; **live submit returned success** (email to tzheng846@gmail.com) |
| AC-5: Visual direction confirmed | Pass | Human-verify checkpoint approved 2026-06-21 |

## Verification Results

- `npm run build` → "Compiled successfully", 12 routes (incl. all `/app/*` portal + `/privacy`, `/faq`, `/report/[token]`).
- Preview DOM checks (screenshot tool mis-scaled, so computed styles used as source of truth): hero gradient, sky accent, card geometry, both nav states, footer paper, `/privacy` still dark.
- Live ContactDialog submission → Web3Forms `success` → "Thanks — we'll be in touch" state.
- No console errors.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/utils.js` | Created | `cn()` (clsx + tailwind-merge) |
| `web/components.json` | Created | shadcn config (tsx:false, Tailwind v4, aliases) |
| `web/lib/site.js` | Created | `WEB3FORMS_ACCESS_KEY` (real key) + `CONTACT_EMAIL` |
| `web/components/ui/{button,card,badge,dialog,input,label,textarea}.jsx` | Created | shadcn primitives, brand-themed |
| `web/components/marketing/ContactDialog.js` | Created | Reusable "Request a quote" form → Web3Forms |
| `web/app/globals.css` | Modified | +iOS light-purple tokens, +`tw-animate-css`; dark tokens untouched |
| `web/components/marketing/Hero.js` | Modified | Immersive gradient hero + floating chart card |
| `web/components/marketing/SampleChart.js` | Modified | Recolored purple; section chrome removed (lives in card) |
| `web/components/Nav.js` | Modified | Scroll-aware glass→solid; CTA = ContactDialog |
| `web/components/Footer.js` | Modified | Light theme; email from `lib/site` |
| `web/app/page.js` | Modified | Light wrapper; trimmed to Nav+Hero+Footer (40-02 restores sections) |
| `web/package.json` | Modified | +8 deps |

(Also created during planning: `web/design-mockups/template-a-light-lavender.html`, `template-b-immersive-gradient.html`.)

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Hand-author shadcn files vs CLI | Next 16 + Tailwind v4 + JS make the interactive CLI unreliable | Canonical components in repo; `components.json` still present for future CLI adds |
| Brand-namespaced shadcn tokens | Portal shares the global `@theme`; reusing `primary/accent/muted` would recolor the portal | Portal visually unchanged; AC-1 satisfied |
| Web3Forms form-to-email | User revised the CTA from a scheduling link to name+email capture emailed to their Gmail | No backend/secret; public access key in `lib/site.js` |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Essential — gradient was invisible |
| Scope additions | 0 | — |
| Deferred | 0 | — |

### Auto-fixed Issues

**1. [Layout] Hero gradient hidden behind the page background**
- **Found during:** checkpoint preview verification
- **Issue:** the gradient was an `absolute -z-10` child, which rendered *behind* the `bg-paper` page wrapper → white text on white.
- **Fix:** moved the gradient onto the `<section>` itself with `isolate`; glows/fade as non-negative `absolute` layers, content `relative`.
- **Files:** `web/components/marketing/Hero.js`
- **Verification:** computed `backgroundImage` = the purple gradient; "Stroke-level" white text now legible.

### Deferred Items

None.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Preview screenshot tool mis-scaled the page (content shrank to a corner) | Used `preview_eval` computed styles/geometry as the authoritative verification instead |

## Next Phase Readiness

**Ready:**
- shadcn + iOS purple tokens + ContactDialog are reusable by 40-02 (just import).
- Pattern for additive tokens + portal isolation is established.

**Concerns:**
- The homepage is intentionally short until 40-02 adds Features / HowItWorks / the "Request a quote" section.
- Web3Forms may require a one-time verification email on the first submission before leads flow — user to confirm.

**Blockers:** None.

**Next:** 40-02 — Features + HowItWorks restyle, Pricing→"Request a quote" section (reuse ContactDialog), login page restyle, faq + privacy retheme to the light theme (content untouched).

---
*Phase: 40-website-redesign, Plan: 01*
*Completed: 2026-06-21*
