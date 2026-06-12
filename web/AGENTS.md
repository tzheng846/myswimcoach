<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Project context

Coach portal + marketing site for Swimnetics. Data flow: reads `athletes`/`sessions`/`reports` via supabase-js with RLS (`lib/supabase.js`); writes go through the Railway FastAPI (`lib/api.js` — `apiFetch`), except `reports` rows which are written directly via supabase-js. Public parent pages (`app/report/[token]`) fetch the no-auth `GET /reports/{token}` endpoint. Full system map and connection matrix: `../CODEBASE-AUDIT.md` (2026-06-12).
