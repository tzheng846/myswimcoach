# Phase 39 — Device Test Plan (deferred to phase end, per user)

Same posture as Phase 38: code-level verify each plan (`expo export` green + self-review); batch
on-device testing into the end-of-phase build. expo-crypto already in the tree (38-03) — still
requires the EAS build to run 38-03+/39 on device.

## 39-01 — Redesign bug fixes (code-complete; export green)
- [ ] **Crash fix:** Team → tap ANY tested athlete → AthleteDetail opens (no redbox); pillar cards
      show correct band colors (good=green / ok=amber / needs_work=red).
- [ ] **Pillar units:** open a session, set Units=yd in Settings, expand a pillar → distance metrics
      show yd, velocity shows yd/s; toggle back to m → reverts; spm/%/s unchanged.
- [ ] **Team-name RLS:** after applying `supabase/patch_05_teams_update_rls.sql` in the Supabase SQL
      editor → Settings edit team name → reload app → name persists. (Without the patch it silently
      reverts — that confirms the policy is the fix.)
- [ ] Band-vs-trend clarity (deferred to 39-03): a good+declined pillar reads sensibly once 39-03
      relabels the trend chip.

## 39-02 — History star button + delete-only-in-session (DU5) (code-complete; export green)
- [ ] History: rows no longer swipe; a star button toggles starred (filled/outline) without opening the session; tapping the row body opens the report.
- [ ] No delete action in the history list.
- [ ] Inside a session: a trash button sits next to the star; tap -> confirm dialog -> Delete -> returns to History and the session is gone.
- [ ] Compare select-mode still works (checkboxes; star hidden while selecting).

## 39-03 — Pillar explainer + remove impulse + athlete limit + trend relabel (code-complete; export green; ratings 26 passed)
- [ ] Advanced Efficiency grid (ReportCard + Record results) no longer shows "Impulse".
- [ ] After Railway redeploys ratings.py: expanding the Stroke-length pillar no longer lists "Impulse per stroke".
- [ ] Long-press any metric in an expanded pillar -> raised card with name + what-it-means + unit; tap outside closes it.
- [ ] Team header shows "N / 20 swimmers" (or the team swimmer_limit).
- [ ] Pillar trend chip reads "Up/Down/Same vs last" (not bare Improved/Declined); a good band + "Down vs last" no longer looks contradictory.

## 39-04 — Record tab button redesign (DU6) (code-complete; export green)
- [ ] Bottom bar = frosted lavender pill with Dashboard / Team / History (icon+label, active=purple) + a SEPARATE purple circular Record button on the right.
- [ ] Tapping the Record circle opens the record config; the three pill tabs switch screens; active tab tinted purple.
- [ ] Screen content is not hidden behind the bar; detail screens still cover it.
- [ ] (polish watch) AiBubble vs the Record circle at bottom-right do not look cluttered.

## 39-05 — Segmentation overlay on velocity chart (DU7) (code-complete; export green)
- [ ] Open a breaststroke session → switch to Advanced view → velocity chart shows faint dashed
      vertical lines at each detected stroke cycle; the solid velocity trace stays clearly on top.
- [ ] A caption under the chart reads "Dashed lines = detected stroke cycles. Segmentation is experimental."
- [ ] Switch back to Simple view → no dashed lines and no caption (chart looks as before).
- [ ] A session with no cycles (or non-breaststroke = Advanced hidden) → no overlay/caption.
- [ ] Pinch-zoom / pan the chart in Advanced → only boundaries inside the visible window draw;
      none clipped outside the plot or at a wrong x; cursor + marker + reset-zoom still work.
- [ ] (parity follow-up, not built) RecordScreen just-recorded results does NOT yet show the overlay.
