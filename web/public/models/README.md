# 3D device model drop-in

The marketing hero renders `device.glb` from this folder. Until that file
exists, a stylized placeholder (built from primitives in
`components/three/PlaceholderDevice.js`) renders instead — no code change is
needed when the real model arrives.

## Exporting from Fusion 360

1. Export as **glTF binary (.glb)** — a mesh format, not STEP/F3D.
   (Fusion 360: File → Export → choose GLB, or use the "Share → GLB" option;
   if unavailable, export OBJ and convert with any glTF converter.)
2. Orientation: **+Y up**, encoder wheel axis along **Z** (wheel face toward
   the camera).
3. Scale: the scene expects the wheel to be roughly **1 unit in radius**
   (~2 units across). Scale in Fusion before export, or note the factor and
   adjust the `<primitive>` scale in `components/three/DeviceScene.js`.
4. Keep it light: < 5 MB, merged bodies, no embedded textures over 2048px.

## Install

Drop the file here as:

```
web/public/models/device.glb
```

Reload the page — the GLB loads in place of the placeholder.
