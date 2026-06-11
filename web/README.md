# Swimnetics Website

Next.js app: public marketing site (`/`) + authenticated coach portal (`/app`).
Built in Phase 23 — see `.paul/phases/23-website/` for plans and summaries.

## Local development

```bash
npm install
cp .env.local.example .env.local   # fill in values (see below)
npm run dev                        # http://localhost:3000
```

## Environment variables

| Var | Value |
|-----|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://ujrotuijxrbscjhzekjk.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | publishable key — mirror `swimnetics-mobile/src/config.js` |
| `NEXT_PUBLIC_API_URL` | `https://swimnetics-api-production.up.railway.app` |

All three are public-safe (anon key is the publishable key; RLS guards data).

## Deploying to Vercel

1. Push this repo to GitHub (the `web/` folder lives inside `myswimcoach`).
2. Vercel → New Project → import the repo.
3. **Root Directory: `web`** (Settings → General → Root Directory).
4. Framework preset: Next.js (auto-detected). No vercel.json needed.
5. Add the three env vars above (Production + Preview).
6. Deploy. Then point DNS: `swimnetics.com` → Vercel (replaces the static
   `landing/index.html` hosting; no code change needed there — just retire it).

### Backend CORS

`api.py` currently allows all origins (`allow_origins=["*"]`), so the portal
works immediately. To lock it down later, restrict to
`https://swimnetics.com` + `http://localhost:3000` via an env-driven list.

## 3D device model

The marketing hero renders a placeholder device until a real model is dropped
at `public/models/device.glb`. Export from Fusion 360 as GLB — full
instructions in [public/models/README.md](public/models/README.md).

## Structure

```
app/
  page.js              marketing landing (hero/3D, how-it-works, features,
                       sample chart, pricing — $15/swimmer/month)
  login/               coach login (Supabase email/password)
  app/                 auth-guarded portal
    page.js            dashboard (latest metrics per athlete)
    athletes/          roster + head–waist offsets
    sessions/          history (filter/star/rename/notes/delete)
    sessions/[id]/     report card (metrics, chart, time-to-X, data quality,
                       Simple/Advanced per-cycle view)
    compare/           two-session overlay + metric deltas
components/            marketing/, portal/, three/ (DeviceScene + placeholder)
lib/                   supabase.js (client), api.js (Railway fetch w/ JWT)
src/data/              sample-session.json (from processed/connor_br_3.csv)
```

Reads go straight to Supabase (RLS-scoped to the signed-in coach); writes go
through the Railway FastAPI (`PATCH/DELETE /sessions/:id`, `POST /athletes`).
Recording stays on the iOS app — the web is view/analyze only.
