# Phase Context

**Phase:** 81 — Annotation Video Marking: play-and-tap marker entry + on-video trace overlay
**Generated:** 2026-08-24 (`/paul:discuss` + AskUserQuestion ×4)
**Status:** Ready for planning
**Enables:** STATE item 9 (annotate the ~20-session backlog) and Phase 80's labeling push — this is
the tool that makes cheap count/rough-timing labels fast to produce.
**Not to be confused with:** Phase 80 (cycle-segmentation *measurement/tuning*). This phase does not
touch any detector or metric definition — it changes how a coach ENTERS ground truth, plus one new
ground-truth field (underwater kicks) and its recompute path.

---

## Why now

Dropping annotation labels is cumbersome: every marker requires clicking the *precise* point on the
recharts velocity trace ([AnnotationChart.js](../../../web/components/portal/AnnotationChart.js)).
The labeling backlog that Phases 78/80 depend on (37/92 sessions annotated; ~20 real-swimmer sessions
unscored; back n=0, breast thin) will not get labeled at click-per-mark speed. The user wants to
**watch the video and tap number keys** to drop markers at the current playback time instead.

Phase 80 established that the new count/cadence metric **tolerates imprecise placement** ("count +
rough timing is enough — no 0.15 s-precise marks needed"), so frame-precision play-and-tap is an
acceptable trade for throughput. That reframe is what makes this phase worth building now.

## What already exists (grounded, 2026-08-24) — reuse, do not rebuild

The plumbing is ~70% there; this phase mostly re-wires and extends it.

- **Video playhead is already tracked.** [annotate/[id]/page.js](../../../web/app/app/annotate/[id]/page.js)
  holds `playheadS = activeCamera.origin_s + video.currentTime`, fed by the ACTIVE camera in the
  multi-cam hub ([CameraTile.js](../../../web/components/portal/CameraTile.js): `reportPlayhead`). The
  trace already draws a playhead line for it (`AnnotationChart` `playheadS` prop, [AnnotationChart.js:313](../../../web/components/portal/AnnotationChart.js#L313)).
- **Drop-at-playhead is already proven for ONE marker.** The `M` hotkey drops a stroke mark at
  `playheadS` ([page.js:298](../../../web/app/app/annotate/[id]/page.js#L298)). This phase generalizes
  that one key to 1–5, and re-uses the swim-window guard in `placeStrokeMark`.
- **The report-card on-video trace overlay is a finished, high-perf component.**
  [TraceOverlay.js](../../../web/components/portal/TraceOverlay.js) +
  [VideoTracePanel.js](../../../web/components/portal/VideoTracePanel.js) (Phase 64): rAF-driven
  rolling window, imperative `viewBox` pan (no React re-render per frame), playhead, drag-scrub-to-seek,
  `readOnly` mode, stacked velocity/accel bands. It currently renders only cycle-start triangles.
- **Marker contract** ([annotations.py](../../../annotations.py)): 4 phase boundaries
  (`dive_start_s`, `underwater_start_s`, `stroke_start_s`, `finish_s`) + `stroke_marks_s` (one mark =
  one ARM ENTRY; free/back pair k=2, fly/breast k=1). **No breakout marker** (removed Phase 58 — matches
  the user's "no breakouts"). **No individual-underwater-kick marker** — genuinely new.
- **The 7 underwater-kick metrics** live in [phase_metrics.py](../../../phase_metrics.py) and all ride
  on `_kick_analysis(ctx)` → `metrics.detect_underwater_kicks(t, vel, uw_start, uw_end)` over the
  `[underwater_start_s, stroke_start_s]` window. Boundaries already honor manual overrides via
  `resolve_boundaries`, **but the individual kick PEAKS are always auto-detected** — there is no manual
  kick channel today. `kick_metrics_reliable` is hardcoded `False` on every auto session (like
  `segmentation_reliable`).
- **⚠ Recompute gap (load-bearing):** `PUT /sessions/{id}/annotations`
  ([api.py:849](../../../api.py#L849)) recomputes CYCLE metrics via
  `compute_session_metrics(manual=...)` but **carries `phases`/`initial_phase` over from the old auto
  result unchanged — it never calls `_rebuild_phases`.** `_rebuild_phases`
  ([api.py:999](../../../api.py#L999)) — which rebuilds `metrics_json.phases` (incl. kick metrics) from
  stored profiles + the annotation's boundaries — is only wired to `POST /recompute` and
  `PUT /go-signal`. So saving an annotation does NOT currently refresh kick metrics at all.

## Decisions (user, AskUserQuestion 2026-08-24)

**D1 — Add the on-video trace overlay; KEEP the clickable chart.** The active camera gets a
report-card-style rolling velocity overlay for fast keyboard marking. The existing
`AnnotationChart` stays below for precise click/drag correction and for sessions with no video.
(Lower-regret superset — not a replacement.)

**D2 — Key 3 (individual underwater kicks) is a NEW ground-truth field that ALSO drives recompute.**
Store + validate `kick_marks_s`, AND feed them through the pipeline so the session's 7
underwater-kick metrics recompute from the coach's marks (not just export as ground truth). This is
the heavier of the two offered options and pulls in `metrics`/`phase_metrics` + the api recompute
seam (see the recompute-gap note above).

**D3 — Key 5 places one ARM ENTRY (today's `stroke_marks_s`), unchanged.** "Individual cycle of
stroke" was loose wording; the arm-entry convention (Phase 57/58) stands, so cycle recompute and
segmenter ground truth are byte-identical to now. No stroke-contract change.

**D4 — Primary goal = labeling THROUGHPUT.** Success = sessions labeled per minute goes way up.
Frame-precision play-and-tap is acceptable; click-to-correct (D1's retained chart, arrow-nudge,
click-drag) is the FALLBACK for the boundaries that want precision — not the primary path.

### Key map (from the user's spec)
| key | marker | field | cardinality | on repeat |
|---|---|---|---|---|
| 1 | Dive / push-off | `dive_start_s` | single | overwrite (move to playhead) |
| 2 | Underwater start | `underwater_start_s` | single | overwrite |
| 3 | **Individual underwater kick** (NEW) | `kick_marks_s[]` | append | append |
| 4 | Stroke start (breakout) | `stroke_start_s` | single | overwrite |
| 5 | Individual stroke (arm entry) | `stroke_marks_s[]` | append | append |
| — | (no breakout marker) | — | — | — |

Overwrite-on-repeat for the single boundaries mirrors the existing phase-tool click behavior;
append for 3/5 mirrors `M` today. (Confirm at plan time; see Q4.)

## Approach (synthesis — mine, confirm at plan time)

Natural split into a **web-first throughput slice** then a **backend kick-recompute slice**, because
D4's value (faster labeling) lands entirely in the first, and D2's recompute is additive:

- **Step 1 — web play-and-tap + on-video overlay (the throughput win).**
  - Mount an annotate-flavored trace overlay on the ACTIVE camera. Either extend `TraceOverlay` to
    render the 4 phase lines + `kick_marks_s` + `stroke_marks_s` (and accept keyboard placement), or a
    thin annotate sibling that reuses its rAF/viewBox engine. Decide reuse-vs-fork at plan time (R1).
  - Number-key handler 1–5 dropping markers at `playheadS`, reusing `placeStrokeMark`'s swim-window
    guard and the undo stack. Keep `AnnotationChart` for click/drag correction; keep arrow frame-step
    + nudge.
  - Add a `kick_marks_s` list + "clear kicks" to `AnnotationEditor`, alongside the stroke-mark list.
- **Step 2 — `kick_marks_s` contract + kick recompute (D2).**
  - `annotations.py`: add `kick_marks_s` (numeric, sorted, within `[underwater_start_s, stroke_start_s]`
    when both bounds present); `validate_annotation`; `annotation_to_overrides` → manual kick indices.
  - `phase_metrics.py`: a manual-kick channel on `PhaseContext`; `_kick_analysis` uses the coach's kick
    peaks (+ their velocities/intervals/window distance) instead of `detect_underwater_kicks` when
    present; flip `kick_metrics_reliable=True` when manual (mirror of `segmentation_reliable`).
  - `api.py`: persist `kick_marks_s`; make `PUT /annotations` **rebuild phases** with the manual
    boundaries + manual kicks (closes the recompute gap), and back up `metrics_json_auto` even for a
    kick-only annotation (no cycle bounds). `DELETE /annotations` restore already covers phases via the
    whole-`metrics_json` backup — verify.

Steps could be two plans under one phase, or one plan — the planner decides. Step 1 alone delivers D4.

## Open questions for planning

- **Q1 — Overlay: extend `TraceOverlay` or fork an annotate sibling?** It is `readOnly`-shaped and
  renders only cycle triangles today; adding phase lines + two mark arrays + keyboard placement without
  regressing the report-card/compare callers is the main design call. (R1.)
- **Q2 — Kick recompute wiring.** Confirm the manual-kick channel rides on the annotation already in
  `ctx` (as boundaries do), and that `PUT /annotations` should now always call the phases-rebuild.
  Confirm `kick_metrics_reliable` flips True on manual kicks.
- **Q3 — Seed for kicks.** The page starts BLANK by design (57 D6 — never seed GT from the segmenter
  it measures). Should key-3 kicks also start blank (yes, for consistency), with `detect_underwater_kicks`
  offered only as an optional "prefill" button? Default: blank.
- **Q4 — Key ergonomics.** Confirm overwrite-on-repeat for 1/2/4 and append for 3/5. Does key 5
  retire the `M` alias or keep both? Should marking be allowed while the video is *playing* (real-time
  tap, ~200 ms reaction lag — acceptable under D4) as well as paused/stepped? (User's phrasing implies
  play-and-tap = yes.)
- **Q5 — Comparability / backfill.** If manual kick marks change a session's stored kick metrics,
  that is a per-session recompute on save (not a library-wide break) — but confirm no dry-run/backfill
  is owed the way boundary redefs were (79/57 precedent). Likely none: it only changes sessions a coach
  actively annotates.

## Risks

- **R1 — Overlay reuse vs regression.** `TraceOverlay`/`VideoTracePanel` are load-bearing on the
  report card and compare. Extending them for annotate must not regress those; a fork duplicates the
  tricky rAF/viewBox engine. This is the biggest build decision.
- **R2 — Frame-precision on the boundaries.** Play-and-tap at ~30 fps + reaction lag is coarse for
  `dive_start`/`underwater_start`/`stroke_start`, which historically wanted sub-0.5 s accuracy. D4
  accepts this for throughput and D1 keeps click-to-correct — but the UI must make correcting a
  boundary obvious, or precision silently degrades on the very markers that feed cycle/phase recompute.
- **R3 — Kick window dependency.** `kick_marks_s` are only meaningful/validatable once
  `underwater_start_s` and `stroke_start_s` exist. The UI/validation must degrade gracefully when the
  window isn't marked yet (place-anyway then validate on save, or gate key 3).
- **R4 — Recompute-gap change is behavioral.** Making `PUT /annotations` rebuild phases changes what a
  save does for EVERY annotated session (not just kicks) — a boundary-only annotation would now also
  refresh kick metrics from the new window. Intended, but must be stated so it isn't a surprise.

## Out of scope

- Any detector or metric-definition change (this is entry + one new GT field + its recompute, not
  Phase 80's tuning).
- The `stroke_marks_s` arm-entry contract (D3 — unchanged).
- A breakout marker (removed Phase 58; user confirmed none).
- iOS annotate (web portal only).
- Library-wide backfill of kick metrics (per-session on save only, pending Q5).

---
*File/line refs are to the tree at generation time; re-verify at plan time. Numbers/behaviors above
are grounded in the current code, not cited from memory.*
