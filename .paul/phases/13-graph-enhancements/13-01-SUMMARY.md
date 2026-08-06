---
phase: 13-graph-enhancements
plan: 01
status: complete
completed: 2026-05-25
---

# Summary: Shared VelocityChart + Time Markers + Units Toggle (Plan 13-01)

## What was done

### Extracted shared VelocityChart component
- Created `src/components/VelocityChart.js` with props: `time`, `velocity`, `markerTimeS`, `markerLabel`, `unitFactor`, `unitLabel`
- Removed local VelocityChart copies from RecordScreen and ReportCardScreen
- Both screens import from `../components/VelocityChart`

### Time marker on chart
- `markerTimeS` prop: absolute chart timestamp (seconds) of the distance crossing
- Orange vertical line rendered at `px(markerTimeS)` with small label above
- `markerAbsoluteTimeS` useMemo in TimeToX returns `timeArr[crossIdx]` (absolute timestamp, not duration)
- Fixed bug: original `timeToX` was a duration; marker must use the absolute chart timestamp

### Meters/yards toggle
- `[m] / [yd]` toggle above VelocityChart in both screens
- `unitFactor`, `distUnit`, `velUnit` derived from `unit` state
- Metric values (Distance, Speed, Dist/Stroke, Impulse, Pulldown Peak) converted with `fmtDist`/`fmtVel`

### TimeToX native-unit presets
- `ALL_PRESETS = [5, 10, 15, 20, 25]` — same values in both modes
- `YARD_TO_M = 0.9144` — yards presets converted to meters for internal computation
- Imperial preset filter uses `maxM / YARD_TO_M` (yards reachable from meters available)
- Button labels: `5yd`, `10yd` etc. in yards mode; `5m`, `10m` in metric mode
- Applied to both RecordScreen.js and ReportCardScreen.js

## Files modified
- `src/components/VelocityChart.js` — new shared component
- `src/screens/RecordScreen.js` — removed local VelocityChart, wired marker/toggle/TimeToX
- `src/screens/ReportCardScreen.js` — same

## Acceptance criteria
- [x] AC-1: Selecting distance preset shows orange vertical line at correct chart position
- [x] AC-2: Toggling yd/m converts all distance + velocity labels; TimeToX presets stay as native values
- [x] AC-3: Chart works identically in RecordScreen results and ReportCardScreen
