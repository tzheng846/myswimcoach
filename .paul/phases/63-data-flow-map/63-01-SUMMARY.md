# 63-01 SUMMARY — Data Flow Map, reference half

**Applied:** 2026-08-13 · **Tasks:** 3/3 · **Checkpoint:** approved
**Suite:** 274 → 274 · **Python product code touched:** none

## What shipped

| File | What |
|---|---|
| `DATA-FLOW.md` (new) | §1–6, 10, 11 — stores, field dictionary, 24 endpoints × callers, two-doors, master diagram, dated snapshot |
| `tools/dataflow_probe.py` (new) | read-only live probe; GET only, no PII printed |
| `.gitignore` (+1 line) | **deviation** — see below |

## Verifications

- Route completeness **24/24** (scripted cross-check of `@app.*` decorators against the doc)
- Probe grep-clean of `.insert/.update/.upsert/.delete` and storage writes
- No TODO/TBD markers; mermaid fences balanced
- `pytest tests/` 274 before and after

## Deviation

**`.gitignore` edited, one line, not in `files_modified`.** `DATA-FLOW.md` never appeared in
`git status`: `.gitignore:16` is a repo-wide `*.md` rule and only `CLAUDE.md` +
`CODEBASE-AUDIT.md` were re-included. D4 chose repo markdown *so the doc is committed and
diffable*; an untrackable file fails that decision outright. Added `!DATA-FLOW.md`. Flagged at
the checkpoint and approved.

## Corrected during apply

The two-doors rule as stated at discussion time was too generous. Verified against source:
**`sessions` writes go through the API; `reports`, `athletes` edits and `teams` do not.**
Athlete *delete* exists on mobile only and bypasses the API entirely. Six exceptions total,
enumerated in §6.

## Findings recorded (documented, not fixed — D8)

Carried into 63-02 §9 as F-a … F-i. Two matter beyond documentation:

- **F-f** — the newest stored session still carries `cycles[].phase`, which 61-01 stopped
  emitting. Either nothing recorded since, or **Railway has not taken the 61-01 deploy.**
- **`API-AUDIT.md`, `GLOSSARY.md`, `STRATEGY.md` are all gitignored** — never in version
  control. 63-02 stale-stamps a file git has never seen; it decides whether to un-ignore.

Also found: `CLAUDE.md`'s session-key list names 19 of the live 24 (F-g); six of 24 endpoints
have no product caller (F-h); `devices` has no `id` column, which 400'd the probe's first
draft (F-i).

## Not done here

§7 (lifecycle walkthroughs), §8 (why each thing exists), §9 (findings), and the stale-stamps —
all 63-02.
