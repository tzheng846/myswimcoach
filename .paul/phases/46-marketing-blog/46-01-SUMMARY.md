---
phase: 46-marketing-blog
plan: 01
subsystem: ui
tags: [nextjs, app-router, marketing, blog, content, static-generation]

requires:
  - phase: 40-website-redesign
    provides: light-purple marketing theme tokens (bg-paper, ink-900/600/400, brand, card, line), Nav (overHero scroll behavior), Footer, /faq static-page pattern
provides:
  - public /blog build-log on the marketing site (index + dynamic post pages)
  - web/lib/blog.js post corpus (5 thematic posts) — extensible for future updates
  - Nav + Footer "Blog" links
affects: [future marketing content, any later blog-post additions]

tech-stack:
  added: []
  patterns:
    - "App-router dynamic content from a plain JS data file (web/lib/blog.js) — no CMS/MDX"
    - "Dynamic segment: generateStaticParams + async params (Next 16) + notFound() for unknown slugs"

key-files:
  created:
    - web/lib/blog.js
    - web/app/blog/page.js
    - web/app/blog/[slug]/page.js
  modified:
    - web/components/Nav.js
    - web/components/Footer.js

key-decisions:
  - "Index + per-post pages (not a single page) — scales for future posts"
  - "Lightly polished candid voice — kept the honesty, dropped the crude lines"
  - "Thematic chunking of ~25 journal entries into 5 posts"
  - "No fabricated dates — topical kickers + newest-first order instead (journal had none)"

patterns-established:
  - "Blog posts are data objects in web/lib/blog.js with { slug, kicker, title, excerpt, body:[{h}|{p}] }; index renders postsNewestFirst, post page resolves via getPost()"

duration: ~35min
started: 2026-06-23T00:00:00Z
completed: 2026-06-23T00:35:00Z
---

# Phase 46 Plan 01: Marketing Blog (build log) Summary

**Shipped a public /blog on the marketing site — a `/blog` index plus statically-generated `/blog/[slug]` post pages, seeded with the founder dev-journal as 5 thematic posts in a lightly-polished-candid voice, linked from Nav + Footer and styled on the existing light `/faq` theme.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min |
| Tasks | 3 auto + 1 human-verify checkpoint (approved) |
| Files modified | 5 (3 created, 2 edited) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Blog index lists the posts | Pass | /blog renders 5 cards (kicker + title + excerpt), newest-first, each → /blog/[slug] |
| AC-2: Post pages render + unknown slugs 404 | Pass | /blog/cutting-the-cord → 200 (title+heading+back-link); /blog/nope-not-real → 404 via notFound() |
| AC-3: Discoverable + on-brand + builds | Pass | "Blog" link in Nav + Footer (2 /blog links on homepage); light /faq tokens; `npm run build` green |
| AC-4: Content scope + voice | Pass | 5 posts cover now / past-struggles / upcoming-features; candid-not-crude; nothing invented; user approved at checkpoint |

## Verification Results

- `npm run build` (Next 16.2.9, Turbopack): compiled successfully; `/blog` prerendered Static, `/blog/[slug]` SSG with all 5 paths prerendered.
- Preview (port 3000): index lists 5 posts newest-first; post 200 with title/heading/back-link; bogus slug 404; homepage has 2 `/blog` links (Nav + Footer); no console errors.

## Accomplishments

- Stood up the site's first app-router dynamic content surface (the first `[slug]` route in the marketing site), with correct Next-16 async `params` + `generateStaticParams` + `generateMetadata` + `notFound()`.
- Turned the ~25-entry dev journal into 5 coherent thematic posts: Cutting the cord (battery/standalone), Laughed off the deck (ASP demo & what broke), The string that wouldn't come back (retraction saga → one-way bearing), Teaching the software to see a stroke (matrix-profile→wavelet), Where Swimnetics is now (current state + roadmap).
- Kept the segmentation post honest about non-breaststroke being experimental (matches `segmentation_reliable=False`), and framed the auto-tracking camera as a future idea, not a promise.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/blog.js` | Created | Post corpus (5 posts) + `getPost` / `postsNewestFirst` helpers (ESM) |
| `web/app/blog/page.js` | Created | Blog index — light theme, Nav+Footer, cards → posts |
| `web/app/blog/[slug]/page.js` | Created | Dynamic post page — SSG + metadata + notFound; renders {h}/{p} body blocks |
| `web/components/Nav.js` | Modified | Added "Blog" → /blog nav link |
| `web/components/Footer.js` | Modified | Added "Blog" → /blog footer link |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Index + per-post pages | User chose; scales for future updates | Established the data-file → dynamic-route pattern |
| Lightly polished candid voice | User chose; buyer-safe but authentic | Dropped crude lines, kept the struggle stories |
| No fabricated dates | Journal had no real dates; no-invention rule | Used topical kickers + newest-first ordering |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** Plan executed as written. One verification-method change (below), no scope change.

### Auto-fixed Issues
None.

### Deferred Items
None.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Plan's Task-1 verify used `require('./lib/blog.js')`, but the project is ESM (`export const`) | Verified the data file via the production build + preview instead (build resolves/imports it; index renders all 5 posts). No code impact. |
| `preview_screenshot` timed out (renderer flake) | Used DOM/HTTP assertions via preview_eval (titles, card hrefs, status codes, link counts) as proof instead — all passed. |

## Next Phase Readiness

**Ready:**
- Blog is live-buildable and on-brand; adding a future post = append one object to `web/lib/blog.js` (no route/page work).
- User runs git commit/push → Vercel auto-deploys.

**Concerns:**
- None. Web-only; portal/report dark theme and tokens untouched.

**Blockers:**
- None.

---
*Phase: 46-marketing-blog, Plan: 01*
*Completed: 2026-06-23*
