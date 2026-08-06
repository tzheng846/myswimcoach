# Plan 23-01 Summary — Scaffold + Marketing Site

**Status:** Complete (2026-06-10). All ACs verified.

## What was built

- `web/` — Next.js **16.2.9** (Turbopack), JavaScript, App Router, **Tailwind v4**
  (CSS-based config — design tokens live in `@theme` in `app/globals.css`, NOT a
  tailwind.config file). Deps added: recharts, three, @react-three/fiber, @react-three/drei.
- Marketing landing at `/`: Hero (3D device + copy from landing/index.html), HowItWorks,
  Features (6 metric cards + 4 platform cards, inline SVG icons), SampleChart, Pricing
  ($15/swimmer/month informational, mailto CTA), shared Nav/Footer with the iOS wave mark
  (`components/WaveMark.js`, path + #5b8def from LoginScreen.js).
- Three.js hero: `components/three/DeviceCanvas.js` (client wrapper, `dynamic` ssr:false)
  → `DeviceScene.js` (Canvas, lights, Rig with idle Y-rotation + pointer parallax,
  reduced-motion respected) → GLB at `/models/device.glb` via useGLTF inside
  ErrorBoundary+Suspense, falling back to `PlaceholderDevice.js` (wheel/housing/tether
  primitives). `web/public/models/README.md` documents the Fusion 360 export drop-in.
- Sample chart data: `web/src/data/sample-session.json` — 281 pts from
  `processed/connor_br_3.csv`, t∈[7.2,12.8] steady-state window (~8 clean cycles).
  swim_lucas_br_2 was tried first and is visually noisy — connor_br_* are the clean demos.

## Decisions / gotchas for later plans

- **Read `web/AGENTS.md`**: version-matched Next docs at `web/node_modules/next/dist/docs/` —
  training data is stale for Next 16. `params` is async (Promise) in dynamic routes.
- Tailwind token names: bg, surface, surface-2/3, primary, accent, navy, wave, ink,
  subtle, muted, success, amber, warning, warning-2, danger (use as `bg-surface`,
  `text-ink`, `border-navy` etc.). Font = system stack.
- `next.config.mjs` pins `turbopack.root` (stray lockfile in user home confused root detection).
- Recharts `ResponsiveContainer` needs `initialDimension` to avoid SSR width warning.
- **Canvas-in-grid blowout**: r3f canvas doesn't shrink on viewport resize — grid items
  need `min-w-0` and the canvas wrapper `overflow-hidden` (fixed in Hero; reuse pattern).
- Dev-overlay "1 Issue" badge = expected device.glb 404 (boundary fallback) + THREE.Clock
  deprecation warnings from fiber internals. Zero console errors.
- Preview: `.claude/launch.json` has a `web` config (npm run dev, port 3000, cwd web).

## Verification

- `npm run build` exit 0 (static prerender of `/`)
- Desktop 1366 + mobile 390 screenshots reviewed; no console errors
- GLB-absent fallback exercised live (404 → placeholder)
- grep: no $200/$1,000 references
