# Phase 50 — Demo Team & Synthetic History

**Status:** Discussed 2026-07-27, ready for planning
**Type:** Dev tooling (seeder script). No product code changes, no schema changes.

---

## Problem

The demo can't show off the product's strongest claim — long-term athlete tracking — because
no long-term history exists. Trend chips, pillar trajectories, the team-pulse strip, the
needs-attention list, and compare mode all need months of sessions per athlete to mean
anything. Today a prospect sees empty states or a handful of scattered test recordings.

## Goal

A re-runnable seeder that populates a dedicated demo coach account with a believable
6-month, 12-athlete training history, so every data-tracking surface of the **web coach
portal** demos with full, correct, story-carrying data.

Success = open the portal on the demo account and every section (dashboard team pulse,
needs-attention, recent activity, roster grid, per-athlete history, session report cards,
compare) is populated with plausible data, and a prospect can be walked through specific
narrative beats without hitting a visibly broken metric.

---

## Approach

**Replay + perturb through the real pipeline.** Do NOT fabricate `metrics_json` by hand.

1. Use real raw encoder CSVs in `raw/` as per-athlete archetypes (signature stroke).
2. Generate each derived session by applying an **invertible** perturbation to the raw
   `angle_counts` stream — time-warp (changes stroke rate) + count-scale (changes
   velocity / DPS) — following a scripted per-athlete trajectory.
3. Run each derived CSV through the **real** `vel_acc_extraction.run_pipeline()` +
   `metrics.compute_session_metrics()`.
4. Insert rows shaped exactly like `api.py`'s `/process` `session_row`
   ([api.py:280](api.py:280)), with **backdated `created_at`**, via the service-role client.

Why replay beats fabrication: every downstream consumer (ratings pillars, `/team/overview`,
compare, per-cycle advanced view, parent reports, AI coach chat, annotate page) reads the
shape `metrics.py` emits. Replayed data is indistinguishable from real. Hand-fabricating
means re-implementing that contract by hand and breaking on the first surface forgotten.

### Annotation propagation (the key cost saver)

Requirement from the user: no visibly wrong segmentation anywhere in the demo. The wavelet
segmenter ships at placeholder quality (`segmentation_reliable=False`, ridges can rail the
120 SPM ceiling), so generated sessions need human-quality boundaries.

Hand-annotating all ~144 sessions = 7–14 hours. Avoided by propagation:

- Hand-annotate only the **~12 archetype sessions** (~1 hour) in the existing Phase-47
  annotate tool at `/app/annotate/[id]`.
- The seeder chose the time-warp, so a stroke mark at `t` in the archetype maps to a
  computable `t'` in every derivative — exactly.
- Seeder writes the mapped `session_annotations` row and passes `manual=` overrides into
  `compute_session_metrics` (Phase 47 contract, `annotations.annotation_to_overrides`).
- Result: `segmentation_reliable=True` and correct cycle counts on every generated session.

**Constraint this imposes:** perturbations must stay invertible. Time-warp + amplitude
scale only — no heavy random jitter that would shift peaks off the mapped marks.

### Two-stage sequence (forced by the above)

```
Stage 0  User signs up a demo coach account, hands over email / team_id
Stage 1  Seeder uploads the ~12 archetype raw CSVs as real sessions in the demo team
Stage 2  User hand-annotates those 12 in /app/annotate/[id]        ← ~1 hour, human gate
Stage 3  Seeder generates the derived history, propagates annotations, backdates, inserts
Stage 4  Tuning loop — adjust perturbation ranges until band/trend mix looks believable
```

Archetypes stay in the demo team as each athlete's **earliest** session — genuinely real
recordings anchoring the fabricated timeline, no wasted work.

---

## Decisions (user, 2026-07-27, AskUserQuestion ×3 rounds)

| Decision | Choice |
|---|---|
| Data home | Dedicated demo coach account in the **live** Supabase project (RLS-isolated from the real team) |
| Demo surface | **Web coach portal** only (not iOS, not parent report pages) |
| Scale | ~12 athletes × ~12 sessions over **6 months** (~144 sessions) |
| Narrative | **Scripted story beats** — assigned arcs (standout improver, plateau, needs-attention, regression-then-recovery) |
| Strokes | **Breaststroke + freestyle only** (revised from "all four" — no backstroke raw data exists; fly dropped with it) |
| Raw CSVs | **Upload to Storage** — keeps annotate-recompute and `/export` functional on demo sessions |
| Reusability | **Config-driven and re-runnable** — `--wipe` / `--seed`, editable roster + trajectory config, dates refreshable before a pitch |
| Extras | **Session names + notes** only (no parent contacts, no fake device, no starred sessions) |
| Annotation | **Annotate ~12 archetypes, propagate** (not all 144, not skipped) |
| Labeling | **Obviously-demo team name + fictional athlete names** |
| Demo account | **User signs up normally** and hands over email / team_id — no credential handling in the script |
| Archetype placement | **Kept in the demo team** as the earliest session per athlete |

---

## Constraints & known landmines

- **No backstroke raw data.** `raw/` has breaststroke (leo, lucas, itay, kenneth), two
  freestyle (`carlos_fr_1`, `lucas_fr_1`), two fly (`carlos_fl_1`, `lucas_fl_1`), and some
  underwater clips. Roster is br + fr; suggested split ~8 br / ~4 fr (4 freestyle athletes
  can derive from 2 source CSVs under different warps).
- **Everything sorts on `created_at`, not `recorded_at`** — verified across `api.py`
  (`.order("created_at")` ×6) and the whole web portal. The seeder MUST set `created_at`
  explicitly; the column default would collapse the whole timeline to seed-day.
- **Ratings thresholds are DRAFT breaststroke** ([ratings.py](ratings.py)) and unvalidated
  for freestyle. Perturbation ranges must land in bands producing a believable *mix* of
  good/ok/needs-work. This tuning is the real cost, roughly equal to the code.
- **Plausibility gate needed** — reject and regenerate any session whose `data_quality`
  comes back poor, so nothing broken reaches a prospect's screen.
- ~~**Two live bugs are bypassed, not blockers**: Phase 48 (`POST /athletes` 500s) and
  Phase 45 (`sessions.device_id` UUID→TEXT) both sit on API paths the seeder skips by
  writing direct with the service role.~~ **RESOLVED 2026-07-30** — both are fixed and
  deployed (48 pushed to Railway; 45's patch_06 applied live, column verified TEXT).
  Neither is a constraint any more. In particular, `device_id` being NULL in the seeder is
  now just a roster choice, **not** a schema requirement — do not re-derive a 22P02 risk
  from this line.
- **The landing surface already exists.** 37-02 (team dashboard web UI) shipped
  (committed `62a6f4f`, live on Vercel), so the team pulse / needs-attention / recent
  activity / banded roster grid this phase exists to populate are built and waiting. The
  seeded data has somewhere to land the moment it's written.
- **Honesty boundary (flagged, user-accepted):** this is sample/reference data. Fine to
  demo as "what six months of tracking looks like"; not to be presented as a real club's
  track record. The obviously-demo naming enforces this.
- Tier limits (`swimmer_limit` 20, `monthly_session_limit`) are enforced in `/process` and
  `POST /athletes` — the seeder's direct writes bypass them. 12 athletes is under the limit
  regardless.

## Out of scope

- iOS app demo data (portal only this phase)
- Parent report card / `/report/{token}` seeding
- Fake device rows, starred sessions, parent contact fields
- Any product code, API, or schema change
- Backstroke and butterfly athletes
- 16-06 segmenter tuning (the 12 archetype annotations do feed the ground-truth export as
  a side benefit, but tuning is a separate future phase)

---

## Open questions for planning

1. Exact roster: 12 names, stroke assignment, and which archetype CSV each maps to.
2. The scripted arcs — how many beats, and which athlete carries which (needs a pass over
   what actually reads well on the dashboard's needs-attention list).
3. Session cadence within the 6 months — even 2-week spacing vs clustered "test weeks"
   with gaps (clustering is more realistic for a club that tests periodically).
4. Whether `--wipe` should also clear Storage objects and `session_annotations` rows, or
   rely on `ON DELETE CASCADE` from the team row.
5. Whether the seeder lives at repo root next to `fetch_sessions.py` / `fetch_annotations.py`
   and gets committed, or stays local-only.
6. How Stage 1 uploads archetypes without the iOS app — likely a direct call into the same
   `run_pipeline` + insert path the seeder already needs, so probably free.

---

*Created: 2026-07-27 via /paul:discuss*
