# 3D device model

The marketing hero renders `device.glb` from this folder (present as of
Phase 27 — the real Fusion 360 export). If the file is removed, a stylized
placeholder (`components/three/PlaceholderDevice.js`) renders instead — the
loader falls back automatically, no code change needed.

`DeviceScene.js` **auto-fits** whatever GLB it finds: it computes the bounding
box, recenters to the origin, and uniformly scales the largest dimension to
`TARGET_SIZE` (≈2.6 scene units). So a replacement export does **not** need a
specific scale or origin — only the up-axis may need attention (see below).

## Replacing the model (export from Fusion 360)

1. Export as **glTF binary (.glb)** — a mesh format, not STEP/F3D.
2. **Up-axis:** Fusion commonly exports **+Z-up**; Three.js is **+Y-up**, which
   renders the device lying on its side. If that happens, set `ORIENTATION` in
   `components/three/DeviceScene.js` to `[-Math.PI / 2, 0, 0]` (or the axis that
   stands it upright). Scale and centering are handled automatically.
3. Keep it reasonable: the current file is ~8 MB and ships uncompressed (a
   deliberate call). If load time matters later, compress with `gltf-transform`
   (Draco/meshopt) — out of scope for now.

## Install

Drop the file here as `web/public/models/device.glb` and reload.
