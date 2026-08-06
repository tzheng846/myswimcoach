---
phase: 30-website-copy-polish
plan: 01
subsystem: ui
tags: [nextjs, marketing, recharts, copywriting, branding]

requires:
  - phase: 23-website
    provides: marketing components (Hero, HowItWorks, Features, SampleChart, Pricing), Nav/Footer, WaveMark
  - phase: 29-marketing-content
    provides: Pricing.js $300+$20 model, /faq + /privacy CONTACT_EMAIL consts
provides:
  - Buyer-facing concise marketing copy (jargon removed)
  - Text-only "SWIMNETICS" wordmark sitewide (WaveMark deleted)
  - Interactive chart moved above the fold with hover m/s tooltip; glide marker removed
  - Sample value on each Features metric card
  - New Hero: "Stroke-level analysis." / research-grade-lab tagline
  - Contact email standardized to info@swimnetics.com
affects: [future marketing/web phases]

tech-stack:
  added: []
  patterns: [optional `value` field on metric card data → conditional render]

key-files:
  created: []
  modified:
    - web/components/marketing/Hero.js
    - web/components/marketing/HowItWorks.js
    - web/components/marketing/Features.js
    - web/components/marketing/SampleChart.js
    - web/components/marketing/Pricing.js
    - web/app/page.js
    - web/components/Nav.js
    - web/components/Footer.js
    - web/app/login/page.js
    - web/app/app/layout.js
    - web/app/report/[token]/page.js
    - web/app/faq/page.js
    - web/app/privacy/page.js
  deleted:
    - web/components/WaveMark.js

key-decisions:
  - "Mid-flight scope add (user): new Hero headline/subtext + move whole Features block directly under the chart"
  - "Logo removed everywhere (all 5 render sites), not just chrome — user choice"
  - "Email swap touched legal pages (faq/privacy CONTACT_EMAIL const) as an explicit email-only exception"

patterns-established:
  - "Metric card data carries an optional `value`; Card renders it only when present (platform cards omit it)"

duration: ~35min
started: 2026-06-15T00:00:00Z
completed: 2026-06-15T00:35:00Z
---

# Phase 30 Plan 01: Website Copy Polish Summary

**Marketing site retuned for buyers: concise jargon-free copy, text-only wordmark sitewide, the velocity chart lifted above the fold with a hover m/s tooltip and the glide marker removed, sample values on every metric card, a new "Stroke-level analysis." hero, and a standardized info@ contact email.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~35 min |
| Tasks | 4 auto + 1 human-verify checkpoint (approved) |
| Files modified | 13 (+1 deleted) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Concise, jargon-free copy | Pass | grep clean for encoder/270/server-side/pipeline across marketing components (incl. a follow-up fix of one "server-side" in a PLATFORM card) |
| AC-2: Interactive chart moved up | Pass | Chart now directly after Hero; later refined to Hero → Chart → Features → HowItWorks → Pricing per user |
| AC-3: Hover y-value, glide gone | Pass | Recharts `Tooltip` shows "X.XX m/s" (verified via simulated hover → "2.70 s / Speed : 0.99 m/s"); glide ReferenceDot + dead trough code removed; "arm pull" kept |
| AC-4: Sample value per metric card | Pass | 34 spm, 1.6 m, 8%, ±5%, 22%, 6.4 s @ 15 m — bold blue above each explanation; PLATFORM cards unaffected |
| AC-5: Wave logo removed everywhere | Pass | All 5 render sites → text "SWIMNETICS"; WaveMark.js deleted; `grep WaveMark` empty; build green |
| AC-6: Contact email updated | Pass | All 6 occurrences → info@swimnetics.com; `grep hello@swimnetics.com` empty |

## Verification Results

- `npm run build` (web/): ✓ compiled, TypeScript clean, 12/12 static pages generated
- `grep WaveMark` / `grep hello@swimnetics.com` in app+components: no matches
- Preview (localhost:3000): zero console errors; snapshot confirmed section order, hero copy, metric values, text wordmark; hover tooltip returned m/s value

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/components/marketing/Hero.js` | Modified | New "Stroke-level analysis." headline + research-grade-lab subtext; email → info@ |
| `web/components/marketing/HowItWorks.js` | Modified | Step bodies de-jargoned (no encoder/270 Hz/server-side) |
| `web/components/marketing/Features.js` | Modified | `value` per metric + conditional render; tightened bodies; PLATFORM "server-side" removed |
| `web/components/marketing/SampleChart.js` | Modified | Added Tooltip (m/s), removed glide ReferenceDot + dead trough code, de-jargoned copy |
| `web/components/marketing/Pricing.js` | Modified | "encoder" removed from copy/bullet; email → info@ |
| `web/app/page.js` | Modified | Section reorder → Hero → Chart → Features → HowItWorks → Pricing |
| `web/components/Nav.js` | Modified | WaveMark removed → text wordmark |
| `web/components/Footer.js` | Modified | WaveMark removed; email → info@ |
| `web/app/login/page.js` | Modified | WaveMark removed; brand is now the SWIMNETICS link |
| `web/app/app/layout.js` | Modified | WaveMark removed; brand span always visible |
| `web/app/report/[token]/page.js` | Modified | WaveMark removed → text wordmark |
| `web/app/faq/page.js` | Modified | CONTACT_EMAIL → info@ |
| `web/app/privacy/page.js` | Modified | CONTACT_EMAIL → info@ |
| `web/components/WaveMark.js` | Deleted | Wave logo retired |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | One stray "server-side" in a PLATFORM card (AC-1 scope) |
| Scope additions | 2 | User-requested at the checkpoint; verified in preview |
| Deferred | 0 | — |

**Total impact:** Polish only, no scope creep beyond the user's own additions.

### Scope additions (user, at checkpoint)
1. **New Hero copy** — headline → "Stroke-level analysis.", subtext → "Turn your lane into a research-grade lab. Record, review, and analyze every swimmer — right from your iPhone, no laptop on deck." (eyebrow + CTAs kept).
2. **Metrics under the graph** — moved the whole Features block (METRICS + PLATFORM) to sit directly under the chart.

### Auto-fixed
**1. [Copy] "server-side" in PLATFORM card** — Found during verification grep; body rewritten to "Each swim uploads and turns into metrics the moment it ends." Satisfies AC-1.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `.claude/launch.json` "missing" but Write blocked | A `web` config already existed (cwd: web); used it as-is, no edit |

## Next Phase Readiness

**Ready:** Marketing site is buyer-facing and consistent; build green; no deploy performed (user-owned — Vercel auto-deploys on push to main).

**Concerns:**
- SampleChart intro line ("the dips between them are where the coaching conversation starts") still reads as a chart→metrics segue; left intact per user (flagged, no change requested).
- Sample card values are illustrative, not guarantees (noted in copy intent).

**Blockers:** None.

---
*Phase: 30-website-copy-polish, Plan: 01*
*Completed: 2026-06-15*
