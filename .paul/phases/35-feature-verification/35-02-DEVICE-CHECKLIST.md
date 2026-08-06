# 35-02 Device Checklist — iOS one-build verification

The on-device script for the four deferred checkpoints + the new ratings UI + the iPad
de-scope spot-check. Code/config is done (Task 1 + 2); everything below is **user-owned**
(deploy, git, EAS build, firmware reflash). Run the gates **in order**, then the checks.

---

## Gate 0 — Deploy the ratings backend (required, or the iOS ratings UI is dead)

`ratings.py` + `GET /sessions/{id}/ratings` are on `feat/coach-chat-drills` only, NOT on
`origin/main` → Railway hasn't built them. The branch is **2 ahead** (ratings) / **4 behind**
(`origin/main` has firmware STATUS `3bd1d99` + merged PRs). Reconcile, then merge to main.

```bash
cd C:/Users/TonyZheng/Desktop/myswimcoach
# (optional) park the two unrelated working-tree edits so the merge is clean
git stash push CLAUDE.md video_sync.py        # or commit them separately first

git checkout feat/coach-chat-drills
git fetch origin
git merge origin/main            # bring firmware STATUS + merged PRs onto the branch
#   ── OR ── rebase if you prefer linear history:  git rebase origin/main
#   resolve any conflicts (none expected — different files), then:

# open/refresh the PR and merge to main (Railway auto-deploys on push to main):
git push origin feat/coach-chat-drills
gh pr create --base main --head feat/coach-chat-drills --fill   # if no open PR
gh pr merge --merge                                             # or merge in the GitHub UI
```

Verify live before building (signed-in coach JWT in $TOKEN):
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  https://swimnetics-api-production.up.railway.app/sessions/<a-breaststroke-session-id>/ratings | head
# expect a JSON pillar payload (stroke/pillars/rating_colors), NOT 404/503
```

- [ ] ratings endpoint returns a pillar payload on prod

## Gate 1 — Reflash the ESP32 (required for the 34-01 diagnostics check)

Firmware STATUS command is on `origin/main` (`3bd1d99`). Flash `ESP_32_V5/ESP_32_V5.ino`
to the device (Arduino IDE / arduino-cli). Confirms the STATUS BLE packet exists.

- [ ] ESP32 reflashed from main

## Gate 2 — Version skew  ✅ RESOLVED 2026-06-17

`expo-doctor` had flagged a PATCH skew (`expo 56.0.11`→56.0.12, `expo-video 56.1.3`→56.1.4) —
the build-36 dyld-crash class. **Fixed:** ran `npx expo install --fix` → now `expo ~56.0.12`,
`expo-video ~56.1.4`; expo-doctor 20/21 (version check passes), `expo export` exits 0.
`package.json` + `package-lock.json` changed (commit them with the rest at Gate 3).
> The one remaining expo-doctor failure ("app config fields not synced in a non-CNG project")
> is EXPECTED and harmless — because `ios/` exists, EAS ignores `app.json`'s `ios` block.
> That's why the iPad fix was made in `project.pbxproj` (authoritative), not just `app.json`.

- [x] expo-doctor version check green

## Gate 3 — Build + install

```bash
cd C:/Users/TonyZheng/Desktop/swimnetics-mobile
# (recommended) commit the local working tree first so the build is reproducible
#   note: this repo has NO git remote — local commits only
git add -A && git commit -m "feat: ratings UI + iPhone-only device family (35-02)"

eas build -p ios --profile preview
# install the resulting build on the iPhone (TestFlight / direct)
```

- [ ] build succeeded + installed, **app launches** (no dyld crash)

---

## Checks (mark PASS / FAIL / BLOCKED + screenshot/note)

> **Status 2026-06-18:** encoder **wiring came loose** (no soldering station) → all
> recording-dependent checks (A full / B / C / E) are **BLOCKED → DEFERRED** until resolder.
> No new EAS build needed then — the same TestFlight build works. **Testable now without
> recording:** D (ratings UI, via existing DB sessions), F (iPad), the app-launches check,
> and a **partial A** (Diagnostics correctly reporting the loose-wiring fault).

### A. 34-01 — Device diagnostics  (AC-2)  → headline: does magnet-not-detected reproduce the failure?
DevicesScreen → "🔧 Run Diagnostics".
- [ ] **(testable now)** ESP32 powers + advertises BLE → connect → Diagnostics reads magnet **NOT DETECTED** (the diagnostic correctly surfacing the loose-wiring fault — validates detection logic)
- [ ] magnet **aligned** → flips to **DETECTED**  *(DEFERRED — needs resolder)*
- [ ] **spin** the wheel → angle value changes  *(DEFERRED — needs resolder)*
- [ ] **record** → buffer count climbs  *(DEFERRED — needs resolder)*
- Result: ____  Notes: ____

### B. 21-02 — Record → buffer-and-dump retrieval  (AC-3)  *(BLOCKED — needs resolder)*
- [ ] record a short run → STOP → META/DUMP retrieval completes
- [ ] uploads + processes → a real metrics report appears in history
- Result: ____  Notes: ____

### C. 26-01 — In-app record-with-video + concurrency  (AC-3)  *(BLOCKED — needs resolder)*
- [ ] "Record with Video" starts BLE + the in-app camera together
- [ ] **BLE link survives the whole recording** (no disconnect)
- [ ] video saves; overlay screen scrubs the velocity cursor in sync (±nudge works)
- Result: ____  Notes: ____

### D. Ratings UI (Phase 36 on iOS)  (AC-1)
Open a **breaststroke** session → report card.
- [ ] **Simple** view shows 4 pillar cards from the live endpoint (band + score marker + verdict + trend chip)
- [ ] tap a card → expands to explanation + contributing metrics
- [ ] **Advanced** toggle → existing raw metric cards (Start Phase / Session / Efficiency)
- [x] breaststroke pillars + expand + Advanced toggle — **PASS 2026-06-18**
- [ ] **non-breaststroke** "Not enough data" / provisional — **NOT EXERCISED** (no non-breaststroke sessions in DB; covered by backend test_ratings.py + web 36-02 verification — same payload contract → low risk)
- Result: **PASS (breaststroke — the only stroke with data + the product path)**  Notes: non-breast render unverified on iOS, data-limited

### E. 22-02 — Laptop demo-video overlay render  (AC-4)  *(BLOCKED — needs a fresh paired recording+video)*
On the laptop (ffmpeg 8.1.1 present):
```bash
# pull the session's raw CSV from Supabase Storage (raw-csvs bucket), then:
cd C:/Users/TonyZheng/Desktop/myswimcoach
python vel_acc_extraction.py raw/<session>.csv
python video_sync.py <args: processed csv + phone video + video_origin_s>
```
- [ ] overlay video renders to completion (exit 0)
- Result: ____  Notes: ____

### F. iPad de-scope spot-check  (AC-5)  — only if an iPad is handy
- [x] app installs/runs as an **iPhone-compat (letterboxed)** app, NOT a stretched full-width iPad layout — **PASS 2026-06-18**
- Result: **PASS**  Notes: TARGETED_DEVICE_FAMILY=1 confirmed working; proper responsive iPad = deferred future phase

---

## Bugs found on device + FIXED 2026-06-18 (code-only; ride the next build — no extra cost)
1. **"Forget" didn't disconnect BLE** (device LED stayed connected). `BleContext.forgetDevice`
   only dropped the device from the saved list, never `cancelConnection()`. **Fixed:** if the
   forgotten device is the connected one, tear down the link + clear state first.
   → re-check on next build: Forget a connected device → LED goes off, app shows disconnected.
2. **Diagnostics said "Too weak" when the AS5600 was unwired** (misleading — implied a magnet
   position issue). An unresponsive sensor reads `0xFF` → MD+ML+MH all set → fell into the
   "Too weak" branch with a bogus angle/AGC. **Fixed:** `magnetVerdict` now flags `0xFF` / the
   impossible weak+strong combo as **"SENSOR NOT RESPONDING — check wiring."**
   → re-check on next build: unwired AS5600 → reads "SENSOR NOT RESPONDING", not "Too weak".
   (Raw angle/AGC values at time of report: not captured — fix is robust to the 0xFF signature regardless.)

## iOS ↔ web parity gaps (observed 2026-06-18 — NOT regressions, NOT 35-02 scope)
Surfaced while testing; web-only features that were never built for iOS. Log for 35-03 docs +
a possible future "iOS feature parity" phase:
- **AI coaching chat** (web `CoachChat.js`) — not on iOS.
- **Advanced per-cycle graphs/table** (web `CycleCharts`/`CycleTable`) — not on iOS; iOS Advanced
  view = raw metric cards only (velocity chart is shown in both views).

---

When done, paste results back (or "all pass"); I'll record them in 35-02-SUMMARY and close the loop.
Any FAIL → log the likely cause + follow-up; no silent gaps.
