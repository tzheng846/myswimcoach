---
phase: 13-graph-enhancements
plan: 03
status: complete
completed: 2026-05-25
---

# Summary: Live Recording Graph (Plan 13-03)

## What was done

Modified `src/screens/RecordScreen.js` to add a live velocity chart during BLE recording.

### Added before component:
- `WHEEL_CIRC_M = Math.PI * 0.06` — matches vel_acc_extraction.py WHEEL_DIAMETER_M
- `computeVelFromSamples(samples)` — pure function: filters magnet_ok, unwraps angle_counts rollovers, computes Δdist/Δt velocity pairs, applies N=15 rolling mean

### Added inside component:
- `liveVelPts` state — array of `{ t_s, v }` points, capped at 3000 (~30s)
- `lastLiveIdxRef` — tracks how far into `samplesRef.current` has been processed
- `liveIntervalRef` — holds the setInterval handle

### Interval lifecycle:
- **Start**: immediately when `setBleState('recording')` is called in `startRecording`
- **Stop**: at top of `stopRecording` (before any await), clears interval and resets state
- **Unmount cleanup**: interval cleared in the existing unmount useEffect

### Recording UI:
- Live chart appears after 20+ velocity points (~2s) below the sample counter
- Labeled "LIVE" using existing `chartTitle` style
- `interactive={false}` (default) — read-only status indicator, no cursor or zoom
- Stop button positioned below chart

## Files modified
- `src/screens/RecordScreen.js`

## Acceptance criteria
- [x] AC-1: Live chart appears within ~2s of recording start
- [x] AC-2: Chart shows last ~30s (3000-point cap)
- [x] AC-3: Chart cleared and state reset when recording stops
