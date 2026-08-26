// /app/sessions/[id]/phases — the race-phase view is now the PRIMARY session report (Phase 75-07),
// so this once-additive route is redundant. It redirects (server-side, 307) to /app/sessions/[id].
// Kept as a route rather than deleted so any bookmarked /phases link still lands on the report.
// Server component on purpose: redirect() here issues a real 307 rather than a client-side hop.

import { redirect } from "next/navigation";

export default async function PhasesRedirect({ params }) {
  const { id } = await params;
  redirect(`/app/sessions/${id}`);
}
