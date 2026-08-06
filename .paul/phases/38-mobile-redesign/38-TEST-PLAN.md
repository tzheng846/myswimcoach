# Phase 38 — End-of-Phase Device Test Plan

Device/EAS verification is **deferred to the end of the phase** (user decision 2026-06-19 —
EAS builds are expensive; batch all on-device testing). Each plan is verified at the code level
as it lands (`npx expo export --platform ios` green + self-review + cross-plan contract checks);
its device checks are appended here.

## Build requirements (what the end-of-phase build must cover)
- **38-01** — JS-only (`@react-navigation/bottom-tabs`). Runs on the EXISTING dev client; no new
  native build needed on its own.
- **38-02** — JS-only (reuses `expo-secure-store`, already native-present). No new native dep.
- **38-03** — ⚠ adds **`expo-crypto`** (NATIVE, for report-token UUIDs) → the end-of-phase EAS/dev
  build MUST include it; 38-03+ cannot run on the pre-38-03 dev client.
- **38-04** — JS-only (no new native dep).
- _(later plans appended; any NEW native dependency flagged here so the single end build covers it)_

---

## 38-01 — Design system + nav skeleton + Login  (code-complete; export green)
- [ ] App launches signed-out → restyled light Login (solid-purple "Sign in", `swimnetics`
      wordmark, periwinkle eyebrow, lavender inputs); no console errors.
- [ ] Sign in with a real coach → lands on the **Dashboard** tab (stub card renders).
- [ ] Tab bar: Dashboard / Team / History grouped, **Record** a raised purple island in the
      middle; 4 distinct icons; active tab tinted purple; tapping each switches screens.
- [ ] Push depth (detail opens full-screen over the tab bar, back returns to the right tab):
      Team → an athlete → RecordingConfig / SessionHistory; Record island → config;
      History/Team → a session → ReportCard.
- [ ] Devices + Diagnostics reachable (Team → gear → Devices → Diagnostics) and render.
- [ ] On-device palette matches the approved mockup; no contrast/readability issues (esp.
      accent only on AI surfaces — none yet in 38-01).
- [ ] Existing flows unchanged (recording config, report card content, devices) — restyle of
      those screens is later plans; here they should still mount and function.

**Known stub behaviors (not bugs):**
- History tab opened directly shows empty (still expects a per-athlete filter param) — the
  team-wide History list is Plan 38-04.
- Dashboard is a placeholder card — real team-health content is Plan 38-02.
- Settings gear on Dashboard is inert — wired in Plan 38-02.

---

## 38-02 — Dashboard + Settings + ambient AI  (code-complete; export green)
Dashboard
- [ ] Loads `/team/overview`: greeting + team name; pulse tiles (swimmers=athlete_count,
      tested=tested_this_week, flagged=needs_attention count) match the team.
- [ ] Needs-attention: 2-col cards, NO avatars; each = name + overall score (right) + a band-colored
      chip with pillar icon (needs-work/declined) OR "Stale Nd" / "Never tested" chip.
- [ ] Recent activity: rows (name · stroke, relative date); tap → correct session's ReportCard.
- [ ] Band colors come from payload.rating_colors (not hard-coded).
- [ ] Empty states: no athletes → 0 counts + "Everyone's tracking well" / "No sessions yet"; no crash.
- [ ] Loading spinner then content; error card has "Tap to retry".

Settings (gear top-right → full-screen over tabs)
- [ ] Team name inline-edit → **persists after app reload** (⚠ depends on an UPDATE RLS policy on
      `teams`; athletes update works, teams may not — if it doesn't persist, needs a backend policy).
- [ ] Coach row shows the signed-in email (read-only — `coaches` has no name column; editable coach
      name is a deferred backend change).
- [ ] "Manage devices" → Devices; "Diagnostics" → Diagnostics.
- [ ] Units m/yd toggle persists across app restart (SecureStore). NOTE: charts don't consume the
      unit yet (pref stored only — wiring deferred to a later polish plan).
- [ ] Sign out → returns to Login.

Ambient AI (needs ANTHROPIC_API_KEY set on Railway)
- [ ] Floating purple bubble sits above the tab bar on Dashboard; tap → compact chat sheet; ask a
      question → reply. Sheet is a bottom sheet, not full-screen.
- [ ] "Today's focus" card appears when the team has sessions; tapping it opens the same chat sheet.
- [ ] Tip is cached per day (reopen Dashboard same day → no new model call / no spinner).
- [ ] No sessions → tip card hidden; bubble sheet says "Record a session to unlock AI coaching".
- [ ] ANTHROPIC unset (503) → dashboard still renders; tip card simply absent; chat shows a graceful
      message (no crash).

---

## 38-03 — Team table + athlete hub + parent reports  (code-complete; export green)
Team tab (labeled pillar table)
- [ ] Loads `/team/overview`; header "Team" + swimmer count; icon header row (gauge/ruler/wave/battery)
      acts as the legend; bottom legend (good/ok/needs work) shows correct colors.
- [ ] Each row: name + last-tested (relative; "never tested" in red) + 4 band dots aligned under the
      icon columns; never-tested rows show dashes. **Verify a needs_work pillar dot is RED** (the
      snake_case band-color fix) — not grey.
- [ ] (+) toggles an add form (name + optional head-waist) → POST /athletes → row appears; 402 →
      "Athlete limit reached" alert.
- [ ] Tap a row → AthleteDetail.

Athlete detail (full hub)
- [ ] Header: back + name + ⋯ menu; subtitle stroke · last tested.
- [ ] "Send report" → creates a report + opens the share sheet with a `${WEB_BASE}/report/{token}`
      link; after sharing, the report is marked sent. ⚠ Confirm WEB_BASE (swimnetics.com) matches the
      deployed site so the link resolves.
- [ ] "Record" → RecordingConfig with this athlete preselected.
- [ ] Pillars (latest): 4 band-colored cards from the athlete summary (icon + label + band word);
      "No sessions yet" when untested.
- [ ] Sessions list (newest first) → tap → that session's ReportCard.
- [ ] ⋯ → Edit fields (name + head-waist, saves) and Delete athlete (confirm → removed → back).

Native build note: 38-03 added expo-crypto → must be in the end-of-phase build before any of the
above can run on device.

---

## 38-04 (partial) — History team-wide + Compare entry + PillarCards light  (code-complete; export green)
History tab
- [ ] Team-wide feed: all athletes, newest first, athlete name shown; stroke filter chips (only present strokes); tap row -> ReportCard.
- [ ] Swipe a row left -> Star / Delete (PATCH/DELETE) work when NOT in compare mode.
- [ ] "Compare" -> select mode: checkboxes, pick exactly 2 (cap enforced) -> bottom bar enables -> opens Compare; "Cancel" exits.
- [ ] Reached with an athleteId param (legacy) -> filters to that athlete.
PillarCards (ReportCard Simple view) renders on LIGHT theme (band meter/marker/verdict/trend/expand); marker visible (dark on band).
Compare screen = stub placeholder ("N session(s) selected") -> real view = 38-05.

### 38-04 second half — DONE (code-complete; export green)
- [ ] ReportCardScreen renders LIGHT (header/back/section cards/Simple-Advanced toggle/name edit/
      Time-to-X/notes); SessionSummaryCard + DataQualityCard light; PillarCards light.
- [ ] Session-anchored AI bubble floats bottom-right; tap → chat about this swim.
- [ ] "⇄ Compare to previous" appears only when an earlier session exists → opens Compare with
      [previous, this]; absent on an athlete's first session.
- [ ] VelocityChart still renders dark-on-light here (restyle deferred to 38-06 — shared w/ record).

---

## 38-05 — Compare (pillar better/no-change/worse)  (code-complete; export green)
- [ ] From History: select 2 → Compare opens; from a session: "⇄ Compare to previous" → Compare.
- [ ] Two session chips ordered earlier → later (by created_at); each shows athlete name + date.
- [ ] Summary line counts (e.g. "3 better · 1 no change · 0 worse").
- [ ] 4 pillar rows, each a colored chip: green ↑ / grey → / red ↓; verdict from the 0–100 score
      delta (±5 deadband).
- [ ] SAME athlete → "Better / No change / Worse"; DIFFERENT athletes → "Higher / Even / Lower".
- [ ] Tap a pillar → expands its primary metric A→B (e.g. "arm-peak CV 18% → 12%").
- [ ] Unknown/unrated pillar → "—"; bad/missing session → error card.

---

## 38-06 — Record flow + Finding A/B  (code-complete; export green)
RecordingConfig (Record island)
- [ ] Cold from Record tab → athlete picker shows "Choose an athlete"; tap → list → select; Start
      stays disabled until an athlete is picked AND a device is connected.
- [ ] Launched from an athlete's "Record" → athlete pre-filled, stroke defaulted from the athlete.
- [ ] Device/stroke/name/notes + "Start recording" work; light theme.
Active recording (dark/immersive)
- [ ] Screen is dark purple; timer + "Recording on device" + Stop in light text; status-bar icons
      legible (⚠ NOTE: App.js sets StatusBar dark globally — confirm icons readable on the dark
      screen; if not, a small per-screen StatusBar light is a follow-up).
- [ ] Record-with-Video: camera preview renders; BLE+camera still work (logic unchanged).
- [ ] Results view: white metric cards float on dark; VelocityChart uses the DARK palette (cyan
      line); Time-to-X + DataQualityCard render; "Record Again" works.
Units (Finding A)
- [ ] Set m or yd in Settings → ReportCard AND Record results reflect it (the in-screen m/yd toggle
      now drives the same global pref; no divergence).
Devices / Diagnostics (Finding B)
- [ ] Both render in the light theme (cards, text, connect/forget colors); Diagnostics verdict
      colors map correctly (NOT DETECTED red, Too weak/strong amber, Detected green).
Shared
- [ ] VelocityChart: light on ReportCard/VideoOverlay, dark on the active record screen.

---

## Cross-plan review (2026-06-19, after 38-04)
Navigation: all 9 navigate() targets (Settings/ReportCard/AthleteDetail/RecordingConfig/Diagnostics/Record/Devices/Compare/VideoOverlay) are registered in RootTabs — no missing routes or name clashes. Tab routes reuse existing names (RecordingConfig/SessionHistory) so cross-screen navigation resolves.

FINDINGS (carry into 38-05/38-06):
- A. UNITS CLASH: Settings exposes a global m/yd pref (UnitsContext, SecureStore) but ReportCardScreen + RecordScreen use their OWN local unit state ("metric"/"imperial") and ignore it — toggling units in Settings has no effect on those screens. FIX in 38-06: wire useUnits() into Record/ReportCard/VelocityChart (map m<->metric, yd<->imperial), drop the per-screen toggles or bind them to the context.
- B. RESTYLE COVERAGE GAP: DevicesScreen + DiagnosticsScreen are reachable from Settings but are NOT in any planned restyle scope — they still render dark amid the light app. Fold into 38-06 or a dedicated polish pass. (RecordScreen/RecordingConfig/VideoOverlay/VelocityChart are already 38-06 scope.)
- C. MINOR: DashboardScreen needs-attention falls back to `|| colors` (camelCase) if rating_colors is absent; safe in practice (payload always present when those cards render). Optional: align with the BAND_FALLBACK map used in Athletes/AthleteDetail.
- D. COSMETIC: small relDate/relTested helpers duplicated across Dashboard/History/AthleteDetail — could centralize, not a bug.

No functional clashes between shipped plans (tokens, nav, API contracts consistent). A + B are the items that must be resolved before the phase is "done".
