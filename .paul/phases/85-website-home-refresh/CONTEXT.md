# Phase 85 — Marketing Home Page Refresh (icon + race-phase repositioning)

*Created 2026-08-29 via `/paul:discuss`. **Revised 2026-08-29 (rounds 2 and 3)** after the user
reviewed each mockup. Handoff for `/paul:plan`.*

> **Later rounds supersede earlier ones.** Round 2 retired D3, D4 and D7; round 3 retired D11, D14
> and part of D17. Read the highest-numbered decision on any topic as authoritative.
>
> ⚠ **Round 3 surfaced a product-level disagreement about what an alert IS (D24). It is not a copy
> question and it does not stop at the marketing site.** See R7.

## Why now

The marketing site has not been touched since **`17086cb` (2026-06-22, Phase 40 redesign)**. Verified
against `git log -- web/components/marketing web/app/page.js web/app/faq`. Everything the product has
gained in the last ten weeks is invisible to a visiting coach:

| Shipped since 2026-06-22 | On the home page today |
|---|---|
| Race-phase report card, 46 metric specs across Start / Underwater / Swim / Whole (75-01…75-07) | Nothing |
| Within-athlete "usual range" comparison + valence + alert line (75-05) | Nothing |
| Per-cycle / per-kick trace bands + the cycle overlay panel (83-01…83-05) | Nothing |
| Synced multi-camera video, push-off align (67, 69) | Nothing |
| Group compare (73), annotation tool (81), coach chat (33) | Nothing |

The page still sells the Phase-8 product: a flat six-card grid of stroke rate, DPS, fatigue index.

## Goals

1. **Put the Swimnetics mark on the site.** It has never appeared anywhere on the web surface.
2. **Reposition the home page around the race-phase report card**, with the within-athlete comparison
   as the promise rather than the metric count.
3. **Rewrite every word of marketing copy so it does not read as machine-written.** No em dashes, no
   en dashes, none of the usual tells.
4. **Do not regress the coach portal.** It is dark-themed and out of scope.

## Decisions — round 1 (2026-08-29)

| # | Decision | Notes |
|---|---|---|
| D1 | **Mark goes in the nav + footer lockup, and becomes the favicon.** | Not a hero showpiece. Not an OG image (declined this pass). |
| D2 | **The race-phase report card leads the page.** | Metrics become supporting detail underneath it, not the lead. |
| ~~D3~~ | ~~Headline is "Know what changed today."~~ | **SUPERSEDED by D11.** The user rejected it outright: it does not say what the product is. |
| ~~D4~~ | ~~Visual proof is hand-built SVG facsimiles; no real athlete data.~~ | **SUPERSEDED by D12 + D20.** Real trace geometry is now used; the no-names half survives. |
| D5 | **Copy pass covers home + FAQ + nav + footer.** | Blog is explicitly out (deliberate personal-voice founder journal, and two post titles contain em dashes). |
| D6 | **No stroke-validation caveat on the home page**, and the FAQ's "Which strokes are supported?" question is **removed entirely**. | Overrides the honest-tiering answer that has been live since 2026-06-15. See risk R3. |
| ~~D7~~ | ~~METRICS + PLATFORM grids fold into the phase story as bullet lists.~~ | **SUPERSEDED by D14.** The flat grid still goes away, but the bullets become radars. |
| D8 | **CTA stays "Request a quote"** everywhere, unchanged (Web3Forms → tzheng846@gmail.com). | No demo booking, no pricing shown. Consistent with the Phase 40 decision. |
| D9 | **Mockup delivered as standalone HTML in `scratch/`**, same pattern as `report-card-concept-v3.html`. | `web/` is untouched until `/paul:apply`. |

## Decisions — round 2 (2026-08-29, this revision)

| # | Decision | Notes |
|---|---|---|
| D10 | **Hero pill reverts to "Velocity Intelligence."** | Round 1 had changed it to "Race-phase analysis." The live site's wording stays. |
| ~~D11~~ | ~~Headline: "Precision swim performance metrics."~~ | **SUPERSEDED by D21.** |
| D12 | **The floating "REAL DATA" card is DELETED.** | It did not earn its place. Hero now flows straight into the report card, hero bottom padding 172px → 118px since nothing overlaps it any more. |
| D13 | **Report card h2: "One lap, three phases, buried insights brought up."** The round-1 *schematic* banded trace is **CUT**. | The user called the drawn schematic unprofessional. Note D23 brings a banded trace back, but drawn from **real** data. The lede paragraph is kept as-is, it tested well. |
| ~~D14~~ | ~~Each phase card = a real velocity slice + a 4-axis radar.~~ | **SUPERSEDED by D22 + D23:** the per-card slices are gone, the radars grew to 5 axes. |
| D15 | **Radar "today" polygon is real (perturbed) data; the "usual range" ring is DRAWN and deliberately irregular.** | A real ring is impossible here: this athlete has only two other same-stroke swims against the five the product actually uses. An irregular drawn ring is also more honest than a circle, since a real usual-range polygon is not one. |
| D16 | **The site may depict UI the portal does not have (the radar), as an illustration.** No commitment to build it. | Risk accepted, see R5. |
| D17 | **"How it is judged" retitled "Compare your current against your past."** Supporting points become **"Alerts all change"** and **"Concise summaries"**, and an **alert line is rendered on the page**. | No prose summary was invented, because none exists in the product. ⚠ The round-2 version copied `AlertSummary.js` verbatim including "changed (unclear)"; **D24 overrides that**. |
| D18 | **"Every cycle" copy drops the shared-axis mechanism.** | Reader is told they can see a stroke that does not match, not how the axis is built. |
| D19 | **Video keeps the "up to four angles" claim but the four tiles lose their camera-position labels.** No brand names anywhere. | The four-camera capability is real (Phase 69); the labelled footage was not. The build asserts no brand string. |
| D20 | **Source session: Chantee / "100%" / butterfly / `85b18b3f`, recorded 2026-08-20T00:49Z (Aug 19 local).** Trace **geometry is real and unmodified**; every **printed value is deterministically perturbed**; **no athlete name appears**. | Consequence, and it is load bearing: **the page must never carry a "REAL DATA" badge**, because the numbers are not. The build asserts the string is absent. |

## Decisions — round 3 (2026-08-29, this revision)

| # | Decision | Notes |
|---|---|---|
| D21 | **Headline: "Precision performance metrics."** Sub: *"Uncover the hidden inefficiencies of your race. Identify where you can improve."* | "swim" dropped from the headline; the pill above it already says Velocity Intelligence and the whole site is about swimming. Accent stays on `metrics.` |
| D22 | **Radars carry 5 axes, not 4, and the display ranges are widened so the polygons vary in shape.** | Explicitly an aesthetic call: the user wants them to look interesting. Real value ordering is preserved; only the plotted range is chosen for legibility. Radii now span 0.45 to 0.88 within a card instead of clustering near 0.65. The renderer takes the axis count from the data, so 4 or 6 needs no code change. |
| D23 | **One whole-lap chart with the phases highlighted in place, replacing the three per-card slices.** | The user's point: if you are going to highlight parts of the swim, show the swim. Real trace, all 1762 samples, three tinted bands plus a grey post-finish tail. Phase cards keep only their radar. |
| D24 | ⚠ **An alert fires ONLY when today falls outside the usual range.** Inside the band is **"Normal"**, is coloured grey, and is **excluded from the alert count**. | This is a product-semantics correction, not a wording change. It cut the example from "6 changes" to **"3 alerts"** (2 worse, 1 better) with 3 normal rows listed but not counted. See R7, and Q8 for the neutral-valence case this leaves unhandled. |
| D25 | **The device section drops material names.** "PETG casing" and "UHMWPE line" are gone; the tether card becomes **"Safety built in"**, describing a **breakaway magnet**. | Benefits over specifications. Note this also restates the tether as magnetic, where round 1 said only "breakaway". |

## Decisions — round 4 (2026-08-29, closing the open questions)

| # | Decision | Notes |
|---|---|---|
| D26 | **The neutral bucket stays, and its chip is renamed.** "changed (unclear)" becomes **"to review"**. | It is a genuine alert (out of range) with no direction verdict. `DIRECTION_OF_GOOD` keeps abstaining where it honestly should, so 75-05's no-forced-valence decision stands. Resolves Q8. |
| D27 | **Phase 85 is MARKETING ONLY.** The portal chip rename is a follow-up phase. | Resolves Q9. The follow-up is one component (`AlertSummary.js`), because the gate already matches (see the correction below). |
| D28 | **Both purples stay as they are.** The mark keeps `#7200FF`, the site keeps `#4e148c`. | The mark only ever renders white-knocked-out in the nav or small in the footer, so the two never sit side by side. Resolves R1. |
| D29 | **The breakaway magnet is real** and may be stated on the public site. | Resolves Q10 / R8, user-confirmed 2026-08-29. |
| D30 | **Nothing was owed at round 2 item 8 or round 3 item 6.2.** | Resolves Q7. |

### ⚠ CORRECTION to the round-3 analysis: the portal gate was ALREADY right

The round-3 write-up below claimed the portal counts in-range values as changes. **That is false**,
and it was verified wrong by reading the code. `flagVerdict` in
[web/lib/phaseValence.js:81](../../../web/lib/phaseValence.js) already gates on exactly the user's
rule:

```js
const direction = value < lo ? "below" : value > hi ? "above" : null;
if (direction === null) return { flagged: false, direction: null, valence: null };
```

An in-range value is `flagged: false`, `PhaseReportCard` passes only flagged rows to
`AlertSummary`, and that component's own zero state reads *"All in range. Nothing fell outside his
usual this swim."* So the portal and the site **already agree that an alert means out of range**.

**What this changes:** R7 drops from "the site describes alerting the product does not have" to a
one-line wording mismatch on a single bucket. There is **no gate to build**, in either surface. The
D24 work was really a fix to the *mockup*, which had been drawn incoherently (a green row sitting
inside its own band).

## Sections in the approved mockup (round 3)

`scratch/website-home-mockup.html`, built by `scratch/_build_mockup.py` from
`scratch/_mockup_template.html` + `scratch/_home_geom.json`.

1. **Nav** — mark + wordmark lockup; Report card / How it works / Blog / FAQ.
2. **Hero** — pill "Velocity Intelligence", headline + sub per D11, existing two CTAs, existing
   "Onboarding a small number of programs first" line kept.
3. ~~Floating real-data card~~ — **deleted (D12)**.
4. **The report card** — one whole-lap real trace with the three phase windows highlighted in place,
   then three phase cards each carrying a 5-axis radar.
5. **Compare your current against your past** — the alert line (**3 alerts**, chips for worse /
   better / normal), the six usual-range strips, and three supporting points: own history / alerts
   all change / concise summaries.
6. **Every cycle** — the five real stroke cycles on one view, the longest picked out.
7. **Video** — four unlabelled panes on one timeline, push-off align.
8. **The device** — one unit covers the lane; PETG, UHMWPE breakaway tether, Bluetooth, ~30 s.
9. **How it works** — three steps.
10. **Request a quote** — existing gradient panel.
11. **Footer** — mark added to the lockup.

## Facts established across both discussions (carry into the plan)

### The mark
- **The "SVG" icon is not a vector.** `assets/icon/Swimnetics_icon.svg` is a **1004×960 PNG,
  47,974 bytes**, base64-embedded inside an SVG wrapper (64,792 bytes on disk). It cannot be
  recolored by CSS `fill`, will not scale crisply past ~1000 px, and is heavy for a favicon.
- **The mark is flat `#7200FF` on transparent**, with the interior highlight as a transparent hole,
  not white pixels. So `filter: brightness(0) invert(1)` gives a clean white knockout on the dark
  hero nav, verified in the render.
- **`#7200FF` does not match `--color-brand: #4e148c`.** Markedly brighter and bluer. See R1.

### The source session (new in round 2, all verified by probe)
- `85b18b3f-d885-4a14-ba2c-05ad901d266e`, athlete Chantee, name "100%", **butterfly**,
  `recorded_at` 2026-08-20T00:49:01Z, **1762 samples at 89.9928 Hz** (19.6 s).
- **All four phase boundaries are `manual`** — coach-marked ground truth, not detector output:
  dive 2.76 s, underwater 3.32 s, stroke start 10.75 s, finish 16.97 s.
- `schema_version` 4, **15 kick bands**, **5 stroke cycles** (0.98 s to 1.13 s).
- Metric coverage: **Start 9/11** real values (`reaction_time` null, `streamline_drag` planned),
  **Underwater 11/13** (`pulldown_*` null, breaststroke only), **Swim 11/12** (`splits_25m` null,
  which is the waist-tether geometry, not a failure), **Whole 11/11**.
- Underwater accounted for **~52% of the distance**. Real, and the most striking number in the set.
- ⚠ **`kick_count` = 15 is overcounted by up to 2** per STATE item 18: `segment_kick_bands` tiles its
  window, so the first band is the push-off glide and the last is the breakout transition. **Do not
  quote a kick count as a headline number anywhere on the site.** The mockup only uses it as an
  unlabelled radar axis, which is safe.

### ⚠ The alert-semantics divergence (D24) — read before planning

**What the portal does today.** `web/components/portal/phases/AlertSummary.js` buckets flags by
**direction-of-good valence** and renders `N worse / N changed (unclear) / N better`. The grey
`changed (unclear)` bucket means *"this moved outside the usual range, but whether that is good or
bad is a coaching call"* — for example a longer glide, which can be patience or hesitation. It is
**not** "in range". Per 75-05 the valence map is `web/lib/phaseValence.js` (`DIRECTION_OF_GOOD`), and
band membership is computed in `web/lib/phaseBaseline.js` as median ± 1.5·MAD of the last five
same-stroke swims.

**What the user asserted in round 3.** An alert should fire *only* when a value is outside the usual
range. Grey should mean **normal / inside the band** and should **not** be counted as an alert.

**These are two different models, and today the portal implements the first one.** The site now
implements the second. So:

- The mockup shows **3 alerts** where the portal would show **6 changes** for the same session.
- The word "changed" is gone from the site; the portal still uses it.
- The site's grey means "in range"; the portal's grey means "out of range, direction ambiguous".

**Both models are defensible and they are not actually in conflict** once separated, because they
answer different questions: *did it move outside normal?* (alert gate) and *is the move good or bad?*
(valence). The clean synthesis is a **two-step rule** the plan should consider adopting in both
places:

1. **Gate on the band.** Inside the usual range, no alert, render grey/"Normal". This is the user's
   rule and it is the right gate.
2. **Then colour by valence.** Outside the band, colour green or red where `DIRECTION_OF_GOOD` has an
   opinion, and keep a distinct treatment for the out-of-range-but-ambiguous case rather than forcing
   it into better/worse.

The current mockup implements step 1 only, and has no out-of-range-ambiguous row to display, which
is why it looks clean. **That case has not been designed** (Q8).

⚠ **If the site ships D24 and the portal is not changed, the marketing page describes alerting
behaviour the product does not have.** That is a heavier version of R5: R5 is a missing chart, this
is a live surface contradicting the site on the product's central promise.

### Copy and build hygiene
- **Em dash inventory — ⚠ CORRECTED 2026-08-29, the round-1 numbers were wrong.** Measured totals:
  `app/faq/page.js` **12** (2 literal + **10 `&mdash;` entities**), `Features.js` 4 (3 em + 1 en,
  dies with the file), `ContactDialog.js` 3, **`app/layout.js` 2 (MISSED in round 1** — both inside
  `metadata`, i.e. the search result and link preview), `HowItWorks.js` 2, `Nav.js` 1, `Hero.js` 1,
  `SampleChart.js` 1 (dies with the file). `app/page.js`, `Footer.js` and `RequestQuote.js` are
  genuinely clean.
  **The entity finding is the important one:** a check that greps only for the `—` character reports
  the FAQ as nearly clean while the rendered page is full of em dashes. Any check must match
  `&mdash;` / `&ndash;` too.
  Out of scope but noted so nobody trips later: `app/privacy/page.js` 9, `lib/blog.js` 24. The blog
  is excluded by D5; privacy was never ruled on and sits under "out of scope".
- ⚠ **The FAQ's device answer also names PETG and UHMWPE** (`app/faq/page.js:92-98`). D25 removes
  material names from the site, but the discussion only ever covered the device *section*, so the
  FAQ copy has to change too or the hygiene check fails on a file nobody scoped.
- The mockup build **asserts** zero em dashes, zero en dashes, no brand name, no `REAL DATA` string,
  no athlete name, and no `changed (unclear)` string. **Carry all six into the apply step** as a repo
  check over `web/app` + `web/components/marketing`.
- The build also asserts each usual-range strip is **internally coherent**: a green or red row must
  fall outside its band and a grey row must fall inside it. This caught a real defect in the round-2
  mockup, where "Peak speed off the block" was inside its band yet coloured green as "better than
  usual", which is exactly the contradiction D24 exists to remove.

### Rendering gotchas found while building the mockup
- **An SVG with `height:auto` collapses to zero height inside a flex item.** A first attempt at
  `.phase-card{display:flex;flex-direction:column}` (to bottom-align the charts) silently blanked
  every slice and radar. The cards are laid out as blocks with `min-height` reserved on the blurb
  instead. This will bite again in `web/` if the phase cards are built with flex.
- A bare `.phase-card p` selector also matched the chart caption and inherited its `min-height`.
  Scoped to `.phase-card > p`.
- Radar axis labels clip at the card edge unless the viewBox is wider than the plot. It is 300 wide
  for a 108-wide plot centered at x=150.

## Open questions for `/paul:plan`

- **Q1. Favicon pipeline.** The source is raster, so the favicon must be produced by *downscaling*
  the embedded PNG to 32 px and 180 px. Decide whether to commit generated PNGs to `web/app/`
  (Next.js `icon.png` / `apple-icon.png` convention) or keep `favicon.ico`.
- **Q2. Where the mark file lives.** `web/public/swimnetics-mark.svg` (64 KB, served as-is) versus
  extracting the inner PNG to `web/public/mark.png` (48 KB, one fewer layer of wrapping).
- **Q3. Does the nav lockup survive the scroll flip?** The nav goes from transparent-over-gradient to
  solid-on-paper. The mark needs the invert filter in the first state and none in the second.
- **Q4. ~~Are the four metrics named per phase card accurate to the registry?~~ RESOLVED.** Every
  radar axis is now backed by a real spec key read from the live session: Start = `peak_vel`,
  `time_to_peak_vel`, `glide_distance`, `break_into_kick_vel`; Underwater = `kick_count`,
  `kick_tempo`, `dist_per_kick`, `uw_avg_speed`; Swim = `breakout_vel`, `ivv`, `splits_20m`,
  `dead_spot_timing`. Axis captions are the coach-legible paraphrase, not the registry label.
- **Q5. Does the radar ever become real portal UI?** D16 says the site may run ahead. If the answer
  is yes it needs its own phase; if no, the gap between site and product is permanent.
- **Q6. How are the perturbed values regenerated if the source session changes?** `JITTER` in
  `scratch/_home_geom.py` is a hand-written table keyed by metric name, deliberately not an RNG so
  the mockup is reproducible. A different session needs new entries.
- **Q7. Two of the user's feedback lists ended on an empty item** (round 2 item 8, round 3 item 6.2).
  Ask before planning whether something was meant to go in either.
- **Q8. ⭐ How should "outside the usual range, but better-or-worse is a coaching call" be shown?**
  D24 removed the grey `changed (unclear)` bucket, but the underlying case is real and the portal
  ships it today. Options: a fourth colour, an uncoloured-but-counted alert, or forcing every metric
  to have a direction of good (which `DIRECTION_OF_GOOD` deliberately does not do). **This is the
  open half of D24 and it blocks aligning the portal.**
- **Q9. Does the portal change to match D24, and in which phase?** If not, the site and product
  disagree about what an alert is. Touches `AlertSummary.js`, `phaseValence.js` and
  `phaseBaseline.js`. Almost certainly its own phase, not Phase 85.
- **Q10. Is the tether breakaway magnetic?** D25 now says "breakaway magnet" on the public site.
  Round 1 and the legal memory say only "breakaway tether connector". Confirm the mechanism before
  publishing a specific claim about a safety feature.

## Risks

- **R1. Brand color mismatch.** The mark's `#7200FF` against the site's `#4e148c`. Options: leave it
  (the mark only ever appears white-knocked-out or small), restate the site brand purple toward the
  mark, or re-export the mark in the site purple. A brand call, not a code call.
- **R2. ~~Claiming capability the site cannot demonstrate.~~ Partly mitigated.** The traces are now
  real geometry from a coach-marked swim rather than invented shapes, so the phase story, the cycle
  overlay and the kick structure all depict something that actually happened.
- **R3. D6 retires a candid answer.** The FAQ has said since 2026-06-15 that "Breaststroke is fully
  validated today. Freestyle and the other strokes are supported at an early quality level." Removing
  the question means a coach with a fly-heavy squad has nowhere on the site to find that, and the
  underlying fact is unchanged: per PROJECT.md the other strokes borrow the breaststroke threshold
  table and `segmentation_reliable` is still hardcoded `False`. Recorded as the user's call.
- **R4. `web/` is deployed on push to `main`.** Vercel auto-deploys. Any apply lands publicly the
  moment it is committed.
- **R5. The radar does not exist in the product.** A coach who signs up expecting it will not find
  it. Accepted under D16.
- **R7. ~~The site will describe alerting the portal does not implement.~~ DOWNGRADED — see the
  round-4 correction.** The gate already matches on both surfaces. What remains is that the portal
  labels the out-of-range-ambiguous bucket "changed (unclear)" while the site would call it "to
  review" (D26), and the marketing page shows no example of that bucket at all. A wording gap on one
  chip, not a behavioural contradiction. Closed by the D27 follow-up phase.
- **R8. ~~The tether safety claim got more specific.~~ RESOLVED by D29** — the magnet is real,
  user-confirmed. Still worth keeping the claim exactly as narrow as the hardware.
- **R6. The perturbation is a thin anonymisation.** The trace geometry is genuinely this swimmer's,
  and only the printed numbers are shifted. That is enough that no published figure is her real
  measurement, but it is not de-identification in a legal sense. Low stakes for an unnamed 20-second
  velocity curve, and recorded here rather than assumed away.

## Out of scope

Coach portal theme, blog copy, OG/social cards, pricing exposure, demo booking, the `/privacy` page,
and anything under `web/app/app/`.

## Files the plan will touch

```
web/app/page.js                      section order (floating card removed)
web/app/layout.js                    metadata + favicon wiring
web/app/faq/page.js                  em dash pass + remove the strokes question (D6)
web/components/Nav.js                lockup + em dash
web/components/Footer.js             lockup
web/components/marketing/Hero.js     headline, sub, pill; drop the SampleChart overlap
web/components/marketing/Features.js REPLACED by the phase-story section (D14)
web/components/marketing/SampleChart.js  RETIRED from the home page (D12)
web/components/marketing/HowItWorks.js   copy rewrite
web/components/marketing/ContactDialog.js  em dash pass
web/components/marketing/RequestQuote.js   copy tighten
web/public/  (new)                   the mark asset
```

New components implied by the mockup: a phase-story section (slice + radar per phase), a
usual-range/alert section, a cycle overlay section, a video section, a device section. Naming and
file layout is a plan decision. **The radar needs a small reusable renderer** since it appears three
times with different axes.

## Artifacts from this discussion

- `scratch/website-home-mockup.html` — the approved design, self-contained, mark embedded as a data
  URI. Open directly in a browser.
- `scratch/_home_data_probe.py` — read-only Supabase probe that locates the source session and
  dumps it to `scratch/_home_session.json`. Re-runnable.
- `scratch/_home_geom.py` — turns that session into `scratch/_home_geom.json`: phase slices, cycle
  polylines, radar radii, perturbed values. Carries the `JITTER` table and the radar display ranges.
- `scratch/_build_mockup.py`, `scratch/_mockup_template.html`, `scratch/_embed_mark.py` — the build
  chain, re-runnable in that order.
- `scratch/swimnetics-mark.svg`, `scratch/icon_preview.png` — the mark and its decoded raster.
- ⚠ `scratch/_mockup_geom.json` and `scratch/_fix_traces.py` are **round-1 leftovers**, no longer
  read by the build. Delete or ignore.

---
▶ NEXT: `/paul:plan`
