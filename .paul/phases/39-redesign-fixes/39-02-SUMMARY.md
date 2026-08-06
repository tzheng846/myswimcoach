# 39-02 SUMMARY — History star button + delete-only-in-session (DU5)

**Status:** Code-complete; device verify DEFERRED (39-TEST-PLAN.md). `npx expo export --platform ios`
exits 0 (3.2MB). Built directly from the DU5 spec (fully specified, no design fork) — no separate PLAN.

## What shipped (swimnetics-mobile)
- `src/screens/SessionHistoryScreen.js`:
  - **Removed the swipe** — deleted the `SwipeableRow` component + `Animated`/`PanResponder`/`Alert`/
    `TouchableOpacity`/`useRef` imports + `ACTION_WIDTH`/`SWIPE_THRESHOLD` + the `sr` StyleSheet +
    `handleDelete` (no list-delete anymore).
  - Each row now has a **tappable star button** (filled ★ ok-color when starred, outline ☆ when not)
    calling the existing `handleStar` (optimistic + PATCH /sessions). Row body still taps → ReportCard;
    star is a separate Pressable (`hitSlop`) so it doesn't trigger navigation. Compare select-mode
    unchanged (checkbox, star hidden).
- `src/screens/ReportCardScreen.js`:
  - Added a **🗑 delete button next to the star** in the header → `confirmDelete()` (Alert confirm) →
    `DELETE /sessions/{id}` → `navigation.goBack()`. History refetches on focus, so the deleted
    session drops out. New `deleteGlyph` style (needsWork color).

## Result
Delete is now reachable ONLY from inside a session (with confirmation), per DU5. Starring is a button
in both the list and the session.

## Verified at code level
- export green; no dangling references to the removed swipe code; star button doesn't fire row nav.
