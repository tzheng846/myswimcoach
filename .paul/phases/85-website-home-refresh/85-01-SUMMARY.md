---
phase: 85-website-home-refresh
plan: 01
subsystem: ui
tags: [nextjs, tailwind, marketing, svg, react-dom-server, metadata]

requires:
  - phase: 75-report-card-phase-model
    provides: the race-phase report card the page is now organised around, plus the
      within-athlete usual-range model (phaseBaseline / phaseValence) the alert section describes
  - phase: 83-per-cycle-trace-coloring
    provides: the cycle/kick overlay the CyclePack section depicts, and the headless
      render-check pattern (scratch/overlay_render_check.mjs) this plan reuses
  - phase: 69-multi-camera-video
    provides: the four-camera capability the video section claims
provides:
  - marketing home page rebuilt around the race-phase report card
  - the Swimnetics mark on the web surface (nav lockup, footer lockup, favicon)
  - web/lib/marketingGeom.js, build-time-baked trace geometry (no Supabase on a public page)
  - a repo copy-hygiene + render check for the marketing surface
affects: [portal alert chip rename (D27 follow-up), any future marketing edit, OG/social cards]

tech-stack:
  added: []
  patterns:
    - "Author-time baked geometry module: a public page renders real trace shapes with no runtime data call"
    - "Copy hygiene as an executable check, matching BOTH literal dashes and HTML entities"
    - "Headless server-render assertions (83-05 pattern) applied to marketing components"

key-files:
  created:
    - web/components/Brand.js
    - web/components/marketing/PhaseRadar.js
    - web/components/marketing/PhaseStory.js
    - web/components/marketing/UsualRange.js
    - web/components/marketing/CyclePack.js
    - web/components/marketing/VideoSync.js
    - web/components/marketing/Device.js
    - web/lib/marketingGeom.js
    - scratch/_export_marketing_geom.py
    - scratch/marketing_render_check.mjs
  modified:
    - web/app/page.js
    - web/app/layout.js
    - web/app/faq/page.js
    - web/components/Nav.js
    - web/components/Footer.js

key-decisions:
  - "Copy check scoped to the marketing surface, not all of web/components: the portal legitimately violates every rule the check enforces"
  - "Phase cards align their radars with a per-card CSS grid row, not the mockup's reserved min-height"
  - "Brand uses next/image because @next/next/no-img-element IS enabled in this config"
  - "scratch/_home_session.json stays out of git: the raw probe dump carries the source athlete"

patterns-established:
  - "Generated modules carry the provenance rules in their header, because that header is the only place a future reader learns them"
  - "Measure a claimed build number (page count) before asserting it in an AC"

duration: ~95min
started: 2026-08-29T17:45:00-07:00
completed: 2026-08-29T18:40:00-07:00
---

# Phase 85 Plan 01: Marketing Home Page Refresh Summary

**The marketing site, untouched since 2026-06-22, now leads with the race-phase report card drawn
from one real coach-marked butterfly 25 baked into a static module, wears the Swimnetics mark for
the first time, and has its copy rules enforced by a 45-check harness rather than by eye.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~95 min |
| Started | 2026-08-29T17:45-07:00 |
| Completed | 2026-08-29T18:40-07:00 |
| Tasks | 9 of 9 completed (8 auto + 1 checkpoint) |
| Files changed | 36 (`a75c373`), +3,203 / -377 |
| Commits | `a75c373` (code + docs), `fbc9d80` (hash recorded) |

## Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| AC-1: Mark in all three placements, both nav states | **Pass** | Live DOM: at scrollY 0 `filter: brightness(0) invert(1)` + white wordmark over the transparent hero; past 24 px `filter: none` + ink wordmark on `bg-paper/90`; `/faq` solid from the first paint; footer uninverted on every page. Head carries `<link rel=icon href=/icon.png>` + `apple-touch-icon`, and `favicon.ico` is gone. |
| AC-2: Hero | **Pass** | Pill "Velocity Intelligence", headline "Precision performance **metrics.**" with the accent on `metrics.`, sub per D21, both CTAs and the onboarding line unchanged, no chart card (`SampleChart` deleted, `pb-40` → `pb-24`). |
| AC-3: Report card section | **Pass** | Whole lap with three tinted windows, a grey post-finish tail, a boundary tick per phase start (3 `stroke-width="1.2"` lines). Three radars: 15/15 dots, 15/15 axis labels, **0 clipped** at 1280 / 880 / 700 px, three distinct polygons, radars on **one baseline at every width** (svgTop 168/168/168 at 1280, 214×3 at 880, 259×3 at 700). |
| AC-4: Usual-range section states the alert rule correctly | **Pass** | Heading exact; "3 alerts today" with chips 2 worse / 1 better / 3 normal, all derived from the table; exactly six strips; **6/6 coherent** (coloured dot outside its band, grey inside) asserted both headlessly and against the live DOM; legend third entry "Normal"; `changed (unclear)` absent from the whole marketing surface. |
| AC-5: Cycle pack, video, device | **Pass** | Five real traces, exactly one in brand purple and four muted; copy describes the odd stroke, not the axis. Four video panes, zero text labels, no brand name, heading keeps the four-angle claim. Four device cards with the required heads; safety card names the breakaway magnet; no PETG / UHMWPE anywhere. |
| AC-6: Copy hygiene enforced by a check | **Pass, with a scope deviation** | `scratch/marketing_render_check.mjs` counts literal `—` `–` **and** `&mdash;` `&ndash;`, plus GoPro / PETG / UHMWPE / REAL DATA / changed (unclear) / the athlete name, over 17 files; exits non-zero (verified by reintroducing one entity and reverting). ⚠ Scope is the marketing surface, not all of `web/components` — see Deviation 1. |
| AC-7: Nothing else regresses | **Pass except the page count** | `next build` clean; `web/components/portal/**`, `phaseValence.js`, `phaseBaseline.js` absent from `git diff`; no product Python touched; **pytest 497 passed**; `/faq` `/privacy` `/blog` all render; zero Supabase references on the marketing surface. ⚠ **20 static pages, not 19** — see Deviation 2. |
| AC-8: Human verify on the running site | **Pass** | Approved by the user on http://localhost:3000, 2026-08-29. |

## Accomplishments

- **The page finally shows the product.** Hero → report card → usual range → cycle pack → video →
  device → how it works → quote. `Features.js` (the flat six-card metric grid that had sold the
  Phase-8 product since June) and `SampleChart.js` are both retired.
- **Real geometry on a public page with no data call.** `scratch/_export_marketing_geom.py` bakes
  `scratch/_home_geom.json` into `web/lib/marketingGeom.js`: the whole-lap polyline decimated
  1762 → 882 points (10 KB), the five cycle traces left whole, radar radii and rings as authored.
  The module header carries the provenance rules (geometry real, printed values perturbed, rings
  drawn) because that header is the only place a future reader will find them.
- **The mark is on the web surface for the first time.** One `Brand` lockup owns both states, so
  Nav and Footer never restate them; the inner PNG was lifted out of its SVG wrapper (63.3 → 46.8 KB)
  and downscaled to the Next.js `icon.png` / `apple-icon.png` file conventions.
- **Copy rules became executable.** The pre-existing FAQ was 10 `&mdash;` entities to 2 literal
  characters, so every character-only grep had been reporting it as nearly clean. The check now
  matches both forms and gates future edits.
- **The render half caught the class of bug builds are blind to**, following 83-05: no
  `stroke: none`, no empty `points`, no `var()` reaching a paint attribute, and the usual-range
  coherence rule that a green or red strip sits outside its band while a grey one sits inside it.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `web/lib/marketingGeom.js` | Created (161) | Baked geometry, frozen, generated |
| `web/components/Brand.js` | Created (34) | Mark + wordmark lockup, owns the inverted state |
| `web/components/marketing/PhaseRadar.js` | Created (125) | N-axis radar, axis count read from data |
| `web/components/marketing/PhaseStory.js` | Created (174) | Whole-lap chart + three phase cards |
| `web/components/marketing/UsualRange.js` | Created (175) | Alert line, six strips, three supporting points |
| `web/components/marketing/CyclePack.js` | Created (72) | Five real cycles, odd one picked out |
| `web/components/marketing/VideoSync.js` | Created (69) | Four unlabelled panes + synced scrub bar |
| `web/components/marketing/Device.js` | Created (59) | Four benefit cards, no material names |
| `web/public/swimnetics-mark.png` | Created | The mark, wrapper dropped |
| `web/app/icon.png`, `web/app/apple-icon.png` | Created | 32 px / 180 px, Next.js file convention |
| `web/app/favicon.ico` | **Deleted** | Replaced by the two icon conventions |
| `web/components/marketing/Features.js` | **Deleted** | Flat metric grid, replaced by the phase story |
| `web/components/marketing/SampleChart.js` | **Deleted** | Orphaned by the hero card removal |
| `web/app/page.js` | Modified | New section order, `id="report-card"` |
| `web/app/layout.js` | Modified | Metadata rewritten (dash-free, new positioning) |
| `web/app/faq/page.js` | Modified | 12 dashes out, strokes question removed (D6), device answer rewritten (D25/D29) |
| `web/components/Nav.js` | Modified | Lockup + retargeted links |
| `web/components/Footer.js` | Modified | Lockup |
| `web/components/marketing/{Hero,HowItWorks,RequestQuote,ContactDialog}.js` | Modified | Copy pass |
| `scratch/_export_marketing_geom.py` | Created (145) | The bake: geometry + mark extraction |
| `scratch/marketing_render_check.mjs` | Created (235) | 45 checks, copy + render |
| `assets/icon/Swimnetics_icon.svg` | Committed | The exporter's source, previously untracked |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Copy check scoped to the marketing surface | The portal carries ~285 comment dashes, says "GoPro" legitimately in its upload help, and holds `changed (unclear)` in the `AlertSummary.js` that **D27 forbids this plan to touch** | A green, therefore readable, gate. The portal needs its own pass if that is ever wanted |
| Per-card CSS grid rows instead of reserved blurb heights | A fixed `min-height` held at 1280 px but broke at 880 px, where the underwater blurb wraps to a fifth line | Radars align at every width the cards share a row, with no magic numbers to retune when copy changes |
| `next/image` for the mark | `@next/next/no-img-element` **is** enabled here; a raw `<img>` added a new lint warning | Lint stayed exactly at its 22-error / 3-warning baseline |
| Phase-slice geometry not exported | D23 replaced the three per-card slices with the single whole-lap chart, so nothing reads them | Smaller module, no dead data to mislead a future editor |
| `scratch/_home_session.json` excluded from git | The raw probe dump carries the source athlete's session | Only anonymised geometry is in the repo, consistent with R6 |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Forced by a contradiction in the plan | 2 | Both documented, neither changes what a visitor sees |
| Implementation improvements | 2 | Both fix a defect the plan's approach would have shipped |
| Copy written beyond "remove the dash" | 2 | Inside files the plan told me to edit |

**Total impact:** no scope creep; two of the six are corrections to the plan's own arithmetic and CSS.

### 1. AC-6's check scope narrowed (forced)

- **Found during:** Task 8
- **Issue:** The plan says scan `web/components/**`. Measured, the portal holds **285** dashes across
  35 files, four files say "GoPro" in genuine coach-facing upload help, and
  `components/portal/phases/AlertSummary.js:38` contains the literal `changed (unclear)` — the exact
  file **D27 defers to a follow-up phase and this plan is forbidden to touch.** The check as written
  could never pass without violating the plan's own boundary.
- **Fix:** scoped to `app/page.js`, `app/layout.js`, `app/faq/**`, `components/*.js`,
  `components/marketing/**`, `lib/marketingGeom.js` — 17 files. The plan makes this same argument
  itself about `/privacy` and `/blog`: "a broader glob makes the check permanently red and it will be
  ignored within a week."
- **Verification:** 45/45 green; reintroducing one `&mdash;` exits 1.

### 2. AC-7's "still 19 pages" is now 20 (arithmetically forced)

- **Found during:** Task 7 verification
- **Issue:** Task 1 mandates `app/icon.png` and `app/apple-icon.png` and the deletion of
  `favicon.ico`. Each icon file convention is its own route; favicon was worth one static page.
- **Fix:** none needed, but measured rather than assumed — builds with favicon restored emit **21**,
  without it **20**, so the pre-plan baseline was exactly the AC's 19. 19 − 1 + 2 = 20.
- **Verification:** two extra builds, one with `favicon.ico` restored from git.

### 3. Phase cards use a CSS grid row, not a reserved `min-height`

- **Found during:** Task 9 verification, before handing the page over
- **Issue:** the mockup's `min-height: 5.1em` on the blurb holds at 1280 px, but at 880 px the
  underwater blurb wraps to a fifth line (114 px against the others' 91 px) and pushed its radar
  **21 px** below the other two, failing AC-3's baseline requirement while the cards were still in a row.
- **Fix:** each card is its own `grid grid-rows-[auto_auto_1fr_auto]`; the blurb row takes the slack so
  the radar always occupies the last row. **Still never a flex column** — the collapse trap the plan
  warns about is untouched.
- **Verification:** radar SVG measures 227 / 159 / 119 px at 1280 / 880 / 700, so nothing collapsed;
  `svgTop` identical across the three cards at all three widths.

### 4. `Brand` renders `next/image`

- **Issue:** the plan implies a plain `<img>`; `@next/next/no-img-element` is active in this config and
  a raw `<img>` produced a new eslint warning.
- **Fix:** static import + `next/image`, `width`/`height` matched to the intrinsic ratio so Next's
  aspect-ratio console warning does not fire either.
- **Verification:** eslint back to the exact baseline, 22 errors / 3 warnings, all pre-existing.

### 5. Two FAQ answers were rewritten, not just de-dashed

- `Q1` paragraph 2 listed the retired flat metric set (stroke rate, fatigue index, consistency); it now
  describes the race-phase split. `Q2` gained one sentence about the alert line. Both files were in
  `files_modified` and both changes serve the plan's stated goal of a page that reflects the product.

### 6. Root metadata rewritten rather than only de-dashed

- `app/layout.js`'s title and description are what a search result and a link preview show, and they
  still sold the June product. Now "Swimnetics | Race-Phase Swim Analysis" plus a description of the
  phase split and the within-athlete comparison.

### Deferred Items

- **`web/src/data/sample-session.json` is now an orphan** — `SampleChart.js` was its only reader.
  Left in place: it is outside `files_modified`, and this repo's guidelines say to mention unrelated
  dead code rather than delete it.
- **`/privacy` (9 dashes) and `lib/blog.js` (24)** keep theirs by D5, **including in their `<title>`**,
  so a search result for either page still shows an em dash. A deliberate scope line, not an oversight.
- **`scratch/_mockup_template.html` is not in git** — `*.html` is gitignored repo-wide, so the mockup
  build chain is committed only as far as its Python. `_build_mockup.py` cannot be re-run from a fresh
  clone without that template.
- **D27's portal chip rename** (`changed (unclear)` → "to review") remains a separate phase, untouched.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Browser-pane screenshots returned solid black once scrolled | The pane reports itself hidden, so nothing composites. Verified every scrolled claim through `read_page` / computed styles / measured geometry instead, which is stronger evidence than a screenshot anyway |
| `window.scrollTo` refused to move the page while the pane was hidden | Re-navigated to reset scroll to 0 for the over-hero state, and used the `computer` scroll gesture for the scrolled state |
| First DOM probe read the wordmark colour as ink over the hero | Probe bug, not a page bug: `textContent === "SWIMNETICS"` also matches the lockup's outer wrapper span. Re-queried the leaf span, which is white as intended |

## Skill Audit

No `.paul/SPECIAL-FLOWS.md` in this project, so no required-skill audit applies.

## Next Phase Readiness

**Ready:**
- The marketing surface now has a gate (`scratch/marketing_render_check.mjs`) that any future edit
  can be run against, including the two silent-failure classes 83-01 paid for.
- `PhaseRadar` takes its axis count from the data, so 4 or 6 axes need no code change if the radar is
  ever ported into the portal (D16/R5 says it may never be).
- The bake chain is re-runnable end to end from `_home_geom.json` if the source session changes.

**Concerns:**
- **The radar does not exist in the product** (D16/R5). A coach who signs up expecting it will not
  find it. Accepted deliberately, and it is now public.
- **The site and portal still word one bucket differently** (D26/D27): the site has no
  "out of range, direction ambiguous" example while the portal labels it `changed (unclear)`. One
  chip, one follow-up phase.
- **R3 stands and is now live:** the FAQ no longer tells a coach that breaststroke is the validated
  stroke. The underlying fact is unchanged, so a fly-heavy or backstroke squad has nowhere on the site
  to learn it.
- **R6 stands:** trace geometry is genuinely the source swimmer's; only printed values are shifted.
  This is why nothing on the page may ever claim measured data, and why the check enforces it.

**Blockers:** None.

---
*Phase: 85-website-home-refresh, Plan: 01*
*Completed: 2026-08-29*
