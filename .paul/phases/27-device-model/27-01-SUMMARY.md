---
phase: 27-device-model
plan: 01
subsystem: ui
tags: [threejs, react-three-fiber, glb, marketing]
completed: 2026-06-12
---

# Phase 27 Plan 01: Device Model (3D hero) — Summary

**Real `device_model.glb` (8.24 MB Fusion export) replaces the primitive placeholder in the marketing hero, auto-fitted and posed as an angled 3/4 rotating view.**

## Acceptance Criteria Results

| AC | Status | Notes |
|----|--------|-------|
| AC-1 real model, framed | Pass | GLB at web/public/models/device.glb serves 200 (model/gltf-binary); auto-fit centers + scales; build exit 0 |
| AC-2 interactivity preserved | Pass | Idle spin + cursor parallax + reduced-motion intact (Rig untouched in contract) |
| AC-3 robustness + build | Pass | npm run build exit 0; ModelBoundary→PlaceholderDevice fallback intact |
| checkpoint:human-verify | **Approved** | 2026-06-12 — orientation/3-4 angle confirmed by user after one adjustment round |

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `web/public/models/device.glb` | Created (moved from repo root) | The real model the loader serves |
| `web/components/three/DeviceScene.js` | Modified | Auto-fit loader (bbox recenter + scale to TARGET_SIZE), ORIENTATION stand-up, Rig 3/4 tilt |
| `web/public/models/README.md` | Modified | Documents auto-fit + up-axis correction for future replacements |
| `device_model.glb` (repo root) | Deleted | Redundant after move |

## Key Decisions / Geometry

- GLB native dims X≈11.1, Y≈10.78, **Z≈21.30** (long axis = Z), origin at a corner
  (center (5.55, 5.39, −10.35)). Auto-fit recenters + uniformly scales largest dim → 2.2.
- User chose: **angled 3/4 hero view, spin through model center**, keep auto-rotate
  (no drag), ship uncompressed (no Draco/meshopt).
- Pose: `ORIENTATION = [-Math.PI/2, 0, 0]` stands the long axis up (→ the vertical spin
  axis, no precession); Rig outer group `rotation={[0.3, 0, 0.12]}` tilts the whole
  turntable ~17° back + slight roll for the 3/4 look. `TARGET_SIZE` 2.6 → 2.2 for framing.

## Deviations

- Plan anticipated a possible single-axis orientation fix; actual fix combined ORIENTATION
  stand-up + a Rig tilt to satisfy the "3/4 angled" choice made at the checkpoint. Minor,
  within the plan's checkpoint-driven tuning intent.
- `preview_screenshot` could not capture the continuously-animating heavy-WebGL canvas
  (timed out); verified via build + GLB HTTP probe + console-clean + the human checkpoint.

## Next Phase Readiness

**Ready:** Hero ships the real device. Deploy pending (Vercel first-time link + Railway push).
**Concerns:** 8.24 MB uncompressed GLB adds hero first-load weight (accepted; gltf-transform later if needed).
**Blockers:** None.

---
*Phase: 27-device-model, Plan: 01 — Completed: 2026-06-12*
