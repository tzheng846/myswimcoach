# Phase Context

**Phase:** 63 — Data Flow Map
**Discussed:** 2026-08-12 (`/paul:discuss`, 2 rounds, 8 questions)
**Status:** Ready for `/paul:plan`
**Decisions:** 8 (D1–D8) + 2 stated assumptions. **Zero open blocking questions.**

⚠ **DOC-ONLY PHASE.** No product code changes, no schema changes, no deploy. The only edits
outside the new document are stale-stamps in two existing docs and one pointer line in the
mobile repo. Anything found broken becomes a numbered finding, not a fix (D8).

---

## Why now

The user asked to understand the system's data flow — what lives in the online database, what
lives locally, what APIs exist and where they are called — with a high-level visual diagram.
The stated motivation is the important part:

> *"There are a lot where I just kind of skimmed over while shipping features without
> understanding why. One such example is ramp up."*

This is a **comprehension debt** phase, not a feature phase. 61 phases have shipped; the system
map exists only in the user's head, in two partly-stale audit docs, and in a 1,945-line ROADMAP.

⭐ **THE CITED EXAMPLE IS ALREADY CLOSED, AND ITS HISTORY IS THE TEMPLATE FOR THIS DOC.**
`ramp_up` was removed by Phase 61-01. It was never ramp-up: it gated on `arm_peak < 0.50 × p75`,
a velocity test, and in practice marked **the swimmer decelerating into the wall** — median
excluded-cycle position **0.91** on the live DB, 59% in the final 20% of the swim; 0 of 13
affected `raw/` sessions had a leading run. It survived four phases because nothing in the
system ever asked what it was actually selecting. The doc's "why each thing exists" sections
exist to make that class of drift visible before it costs another four phases.

---

## Decisions

| # | Decision |
|---|---|
| **D1** | **Map + why each thing exists.** Descriptive topology plus a short "what decision created this" note per piece, sourced from the repo and the phase record. **NOT** an investigative hunt for the next `ramp_up` — that needs measurement runs and is recorded as a separate future phase (see Carried out). |
| **D2** | **New `DATA-FLOW.md` at repo root OWNS data flow.** Then stale-stamp the overlapping sections — `CODEBASE-AUDIT.md` §4 (connection matrix) and `API-AUDIT.md`'s endpoint inventory — to point at it rather than restate it. A third independent copy of the connection matrix is the exact drift this repo already has between its two audit docs. |
| **D3** | **Breadth: the whole product path.** Firmware/BLE → mobile → `/process` → pipeline → Supabase → web portal → parent reports → annotation loop → coach chat → billing. Dev and experimental surfaces (`app.py`, `tools/*.py`, `seed_demo_team.py`, `pose/`, `merge_streams.py`, `vel_acc_extraction_test*.py`, legacy firmware dirs, `raw/`+`processed/`+`output/`) get **one line each** saying they exist and are not in the product path. |
| **D4** | **Repo markdown + Mermaid.** Committed, diffable, renders in GitHub, readable by future AI sessions. No Artifact page — it would drift invisibly. |
| **D5** | **Verify live, read-only.** Use `SUPABASE_SERVICE_ROLE_KEY` from `.env` to turn "the code implies X" into "X is true of N rows". Counts recorded as a **dated snapshot** that the doc explicitly says will go stale. Read-only — no writes of any kind. |
| **D6** | **Full field dictionary for every jsonb payload:** `metrics_json` (session / cycles / data_quality / initial_phase), `metrics_json_auto`, `velocity_profile`, `distance_profile`, `session_annotations.phases` + `.stroke_marks_s`, `reports.config_json`. Writer attribution is not in this section — it falls out of the call-graph section instead (D-note: nothing is lost, it moves). |
| **D7** | **One pointer line in `swimnetics-mobile/CLAUDE.md`** naming the doc and its path. No copy — two system maps guarantee divergence. This directly targets the Phase 60 failure mode: a `myswimcoach` commit whose lesson never reached the mobile repo, leaving a −10% error live for two months. |
| **D8** | **Document only.** Live defects found during mapping become numbered findings with `file:line` and a proposed fix, routed to a ROADMAP TODO row or a later phase. No behavior changes — this pipeline already carries four comparability breaks and changing anything here would need its own measurement work. |

### Stated assumptions (user did not object)

- **A1 — the doc describes the system AS IT IS, warts included.** A "known inconsistencies /
  open contradictions" section is in scope, as pointers, not re-litigation.
- **A2 — layered diagrams.** One high-level master diagram plus per-flow drill-downs. A single
  Mermaid graph spanning firmware to parent reports would be unreadable.

---

## What was verified (2026-08-12, this session)

### Repo-verified topology

**Four data stores, not two:**

| Store | Holds | Authoritative for |
|---|---|---|
| Supabase Postgres | 7 tables | everything the product reads |
| Supabase Storage | `raw-csvs`, `videos` (private, signed URLs) | source bytes |
| Phone local | raw CSV in `FileSystem.documentDirectory` (`RecordScreen.js:228`), video file until the FIFO queue drains | nothing — transient staging |
| Laptop local | `raw/`, `processed/`, `output/`, `annotations_export.json` | nothing — dev only |

**No AsyncStorage session cache on mobile.** Every mobile screen reads Supabase live. The phone
is not an offline store today, despite "offline-safe recording" sitting unchecked in
PROJECT.md's Must Have list.

**Two doors into the same data — this is the part that needs the diagram most.** Reads mostly
go **direct to Supabase via supabase-js under RLS** (21 `.from(...)` sites on web, 22 on
mobile); writes mostly go **through the Railway API**. The exceptions are the interesting part:
`reports` rows are inserted directly by **both** clients, and mobile deletes athletes directly
via supabase-js rather than through the API.

**24 endpoints** in `api.py` (`grep` of the route decorators), against a caller inventory that
already has known holes (`GET /sessions/{id}/export` and four billing endpoints have no caller
anywhere).

### Live-DB probe (read-only, 2026-08-12) — **dated snapshot, will go stale**

```
sessions 62 · session_annotations 24 · reports 5
athletes 3 · coaches 1 · teams 1 · devices 2
```

`sessions` column population across all 62 rows:

| column | non-null | reads as |
|---|---|---|
| `raw_csv_path` | 62/62 | every session's source CSV is in Storage |
| `athlete_id`, `stroke_type` | 62/62 | always set |
| `device_id` | 57/62 | 5 sessions recorded with no device attributed |
| `sample_rate_hz` | 56/62 | **6 NULL** — pre-Phase-52, readers fall back to 100 |
| `video_path` | 29/62 | |
| `video_origin_s` | 24/62 | ⚠ **5 sessions have video and NO origin** |
| `metrics_json_auto` | 24/62 | exactly matches the 24 annotation rows |
| `name` | 10/62 | why Phase 61-04 needed generated mnemonics |
| `notes` | 2/62 | |

- `upload_status` is `'complete'` for **all 62** — the column has never carried information.
- Stroke mix: freestyle 31, breaststroke 15, butterfly 15, **backstroke 1**.
- ⭐ **The 5 video-without-origin rows are the 58-04 defect's data footprint.** Phase 61-03
  closed the code path; it was forward-looking and did not backfill. Those sessions are still
  silently unsynced on the web.
- Every one of the 24 annotated sessions had its `metrics_json` **overwritten** by human marks,
  with the auto result preserved once in `metrics_json_auto`. That two-writer relationship on
  the single most-read column is a top candidate for the diagram.

---

## Findings seeded so far (D8 — document, do not fix)

Verified this session:

- **F-a** `fetch_sessions.py:30` — `FS = 100.0  # velocity/distance profiles stored at 100 Hz`.
  False since Phase 52; the true rate is per-session in `sessions.sample_rate_hz`.
- **F-b** 5 live sessions carry `video_path` with NULL `video_origin_s` (58-04 footprint, no backfill).
- **F-c** `sessions.upload_status` is `'complete'` on 62/62 rows — a column that has never
  discriminated anything.
- **F-d** `reports` rows are written directly via supabase-js from both clients, bypassing the
  API that owns every other write.
- **F-e** `CODEBASE-AUDIT.md` is dated 2026-06-18 and predates Phases 47, 51, 52, 57, 58, 59,
  60, 61 — its §4 connection matrix is the section this phase supersedes.

Inherited from prior audits, to be **re-checked rather than copied** during mapping:
`GET /sessions/{id}/export` has no caller (API-AUDIT F9); four billing endpoints have no client
caller (F10); billing state duplicated across `coaches` and `teams` (F7); `teams` is read by
iOS but never by `api.py` (51-01).

---

## Proposed document structure

`DATA-FLOW.md`, repo root:

1. **Read this first** — what this doc owns, what it does not, how it goes stale
2. **Master diagram** (Mermaid) — the whole product path, one screen
3. **The four data stores** — and which is authoritative for what
4. **Field dictionary** — 7 tables, every column, every jsonb payload expanded (D6)
5. **API surface** — 24 endpoints × caller (mobile / web / none), auth, ownership rule
6. **The direct-Supabase path** — what bypasses the API, and why RLS makes that legitimate
7. **Lifecycle walkthroughs**, one drill-down diagram each:
   record → process → store → display · annotate → recompute → overwrite ·
   video capture → upload → origin → sync · parent report · coach chat
8. **Why each thing exists** — per-piece rationale, phase-cited, with "undocumented / inferred"
   marked as such rather than invented
9. **Known inconsistencies** — the F-list, as pointers
10. **Not in the product path** — dev/experimental surfaces, one line each (D3)
11. **Dated snapshot** — the live counts, stamped

---

## Files in scope

**New:** `DATA-FLOW.md`
**Modified (stale-stamp only):** `CODEBASE-AUDIT.md` §4, `API-AUDIT.md` endpoint inventory,
`CLAUDE.md` (pointer)
**Modified (mobile repo, one line):** `swimnetics-mobile/CLAUDE.md`
**Untouched:** all product code, all tests, schema, deploys

---

## Carried out (recorded, not scoped here)

⚠ **"Find the next `ramp_up`" is a separate future phase.** The user chose the descriptive map
now (D1). The investigative version — measurement runs against the live corpus to test whether
other load-bearing concepts are mislabeled, the way Phase 61's grilling took 4 runs to prove
`ramp_up` was mis-named — needs its own scope and its own plan. Do not fold it into this phase.

---

## Success criteria

- [ ] A reader who has never seen this project can answer "where does this byte live and who
      put it there" for every field in the 7 tables and 2 buckets
- [ ] Every API endpoint is listed with its actual callers, including the ones with none
- [ ] The two-doors pattern (direct supabase-js reads vs API writes) is explicit and diagrammed,
      including every exception
- [ ] `metrics_json`'s two writers — `/process` and `PUT /annotations` — are unmissable
- [ ] Every "why" is either phase-cited or explicitly marked as inferred; none invented
- [ ] Live counts are present and stamped with the date they were taken
- [ ] `CODEBASE-AUDIT.md` §4 and `API-AUDIT.md`'s inventory point here instead of contradicting it
- [ ] A cold session in `swimnetics-mobile` can find this doc from that repo's `CLAUDE.md`
- [ ] Zero product code changed; findings routed, not fixed
