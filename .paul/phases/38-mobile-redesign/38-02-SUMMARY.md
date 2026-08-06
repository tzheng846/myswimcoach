# 38-02 SUMMARY — Dashboard + Settings + ambient AI

**Status:** Code-complete; device verification DEFERRED (38-TEST-PLAN.md). `npx expo export
--platform ios` exits 0. No new native dependency (JS-only; reuses expo-secure-store).

## What shipped (swimnetics-mobile)
- `src/lib/apiFetch.js` — authed JSON fetch helper (Bearer + detail-on-error).
- `src/components/ui/PillarIcons.js` — gauge/ruler/wave/battery, mapped by pillar key
  (speed/stroke_length/consistency/endurance, verified vs ratings.PILLARS) + `<PillarIcon>`.
- `src/screens/DashboardScreen.js` — real team-health home from `GET /team/overview`: greeting +
  team name, counts-only pulse, needs-attention 2-col summary cards (name + derived overall score +
  primary-reason chip with pillar icon; stale/never_tested chips), recent-activity feed → ReportCard.
  Loading/error/empty states. Band colors from payload.rating_colors.
- `src/screens/SettingsScreen.js` — Account (team name inline-edit → teams.update; coach email
  read-only), Device (Manage devices → Devices, Diagnostics → Diagnostics), Preferences (m/yd units),
  Sign out.
- `src/context/UnitsContext.js` — m/yd pref persisted in SecureStore; provider added to App.js.
- `src/components/ai/CoachChatSheet.js` — compact bottom-sheet chat → POST /coach/chat
  {session_id, messages}; graceful on 503/empty; session-anchored (team tools answer team Qs).
- `src/components/ai/AiBubble.js` — floating bubble (absolute, not fixed) + sheet; optionally
  controlled (open/onOpenChange) so the tip card and bubble share one sheet.
- DashboardScreen "today's focus" tip — generated via /coach/chat (anchored to most recent team
  session), cached once/day/team in SecureStore; tapping opens the chat; hidden when no sessions.
- `RootTabs.js` — Settings registered on the root stack; `theme/tokens.js` — added `scrim` token.

## Deviations / limitations (carry to test + later plans)
- **Coach name not editable** — `coaches` table has no name column; Settings shows the coach email
  read-only. Editable coach name = a deferred backend change (out of this mobile-only phase).
- **Team-name edit persistence** depends on an UPDATE RLS policy on `teams` (athletes update works;
  teams unverified). Flagged in 38-TEST-PLAN; if it doesn't persist, needs a backend policy.
- **Units pref persisted only** — charts/readouts don't consume the unit yet (deferred polish).
- Needs-attention card shows the severity-ranked primary reason (needs_work > declined > stale >
  never_tested) rather than always a numeric "weakest pillar" — faithful to the /team/overview
  needs_attention payload; score still shown when pillars exist.
- AiBubble reusable for 38-04/05 (session/compare) — there it's used uncontrolled.

## Verified at code level
- export green; Dashboard reads only documented /team/overview fields; pillar keys match;
  no raw hex/rgba in new components (scrim moved to token); no /coach/chat call without session_id.
