# 38-05 SUMMARY — Compare (pillar better/no-change/worse)

**Status:** Code-complete; device verification DEFERRED (38-TEST-PLAN.md). `npx expo export
--platform ios` exits 0 (3.2MB). Built from the design locked 2026-06-19 (mock+ask). No new dep.

## What shipped
- `src/screens/CompareScreen.js` — replaced the 38-04 stub with the real view:
  - Reads `route.params.sessionIds` (2), fetches both sessions' meta (supabase: created_at,
    athlete_id, `athletes(name)`) + both `/sessions/{id}/ratings`.
  - Orders earlier → later by `created_at`; detects same vs different athlete.
  - Per pillar (matched by key): verdict from the 0–100 **score** delta with a ±5 deadband.
  - **Adaptive labels:** same athlete → Better / No change / Worse; different athletes →
    Higher / Even / Lower (no improvement implication).
  - Colored chips (good/needsWork/surfaceAlt from tokens) + a summary tally line.
  - **Tap a pillar** → expands its primary metric A→B (label + value + unit from the ratings payload).
  - Loading / error / unknown-pillar ("—") states.

## Notes
- Reuses the Phase-36 ratings endpoint as the single source of truth (no new backend; scores are
  already higher=better there, so the delta needs no per-metric direction handling).
- Entry points (both wired in 38-04): History multi-select and ReportCard "⇄ Compare to previous".
- Contract `{ sessionIds: [a, b] }` consistent with both callers.

## Verified at code level
- export green; tokens only (no raw hex); ratings pillar shape (score + primary{label,value,unit})
  matches PillarCards usage.
