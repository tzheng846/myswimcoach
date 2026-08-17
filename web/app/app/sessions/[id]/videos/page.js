"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch, apiUpload } from "@/lib/api";
import CameraTile from "@/components/portal/CameraTile";

// Dedicated Videos page (Phase 69). One place to attach up to 4 camera angles (phone + 3 external),
// label + sync each to its push-off, and (69-03) watch them on one shared timeline. Pulls video
// management OFF the report card. The phone/primary comes from the legacy sessions columns; externals
// live in session_videos — the GET /videos endpoint unifies them.
const MAX_VIDEO_BYTES = 50 * 1024 * 1024; // matches api.py + patch_11 (free-tier ceiling)
const MAX_EXTERNAL = 3;

export default function SessionVideosPage({ params }) {
  const { id: sessionId } = use(params);

  const [row, setRow] = useState(null);
  const [athlete, setAthlete] = useState(null);
  const [videos, setVideos] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const loadVideos = useCallback(async () => {
    try {
      const r = await apiFetch(`/sessions/${sessionId}/videos`);
      setVideos(r.videos ?? []);
    } catch (e) {
      setMsg(`Could not load videos: ${e.message}`);
    }
  }, [sessionId]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const { data, error: err } = await supabase
        .from("sessions")
        .select("velocity_profile, sample_rate_hz, name, created_at, athlete_id, metrics_json")
        .eq("id", sessionId)
        .single();
      if (!alive) return;
      if (err) {
        setError("Failed to load session.");
        return;
      }
      setRow(data);
      if (data.athlete_id) {
        const { data: ath } = await supabase
          .from("athletes")
          .select("name")
          .eq("id", data.athlete_id)
          .single();
        if (alive) setAthlete(ath);
      }
      await loadVideos();
    })();
    return () => {
      alive = false;
    };
  }, [sessionId, loadVideos]);

  // Push-off (dive) session time = when swim motion begins (baseline_end_s) — the Phase 67-01 align
  // target. Each camera scrubs to its own push-off frame and snaps to this one session-clock instant.
  const pushoffSessionS = row?.metrics_json?.session?.baseline_end_s ?? null;

  const externalCount = useMemo(
    () => videos.filter((v) => v.role === "external").length,
    [videos]
  );

  const attach = async (file) => {
    if (!file) return;
    if (file.size > MAX_VIDEO_BYTES) {
      const cap = MAX_VIDEO_BYTES / (1024 * 1024);
      setMsg(
        `This clip is ${Math.round(file.size / (1024 * 1024))} MB — over the ${cap} MB limit. ` +
          `Compress it (HandBrake / GoPro Quik) to under ${cap} MB, or upgrade to Pro storage.`
      );
      return;
    }
    setBusy(true);
    setMsg("Uploading video…");
    try {
      const fd = new FormData();
      fd.append("file", file);
      await apiUpload(`/sessions/${sessionId}/videos`, fd);
      setMsg(null);
      await loadVideos();
    } catch (e) {
      setMsg(`Upload failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  if (error) return <p className="mt-10 text-center text-danger">{error}</p>;
  if (!row) return <p className="text-muted">Loading…</p>;

  const date = new Date(row.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const canAdd = externalCount < MAX_EXTERNAL;
  const gridCols = videos.length <= 1 ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2";

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex items-center justify-between">
        <Link href={`/app/sessions/${sessionId}`} className="text-sm text-primary">
          ‹ Report card
        </Link>
        <div className="text-center">
          <p className="font-semibold">{athlete?.name ?? ""}</p>
          <p className="text-xs text-muted">{date}</p>
        </div>
        <span className="text-xs text-muted">{videos.length}/4 cameras</span>
      </div>

      <h1 className="mt-2 font-semibold text-ink">Videos{row.name ? ` — ${row.name}` : ""}</h1>
      <p className="mt-1 text-xs leading-relaxed text-muted">
        Up to 4 angles (phone + 3 external). Scrub each to the push-off frame and tap Sync to push-off
        so every camera lines up with the swim. External clips: H.264 .mp4, ≤50 MB.
      </p>

      <div className={`mt-4 grid gap-3 ${gridCols}`}>
        {videos.map((v) => (
          <CameraTile
            key={v.id}
            sessionId={sessionId}
            video={v}
            pushoffSessionS={pushoffSessionS}
            onChanged={loadVideos}
          />
        ))}

        {canAdd && (
          <label className="flex min-h-[180px] cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-subtle/40 bg-surface/50 text-muted hover:text-ink">
            <span className="text-2xl leading-none">+</span>
            <span className="text-sm font-semibold">{busy ? "Uploading…" : "Add camera"}</span>
            <span className="text-[11px]">{externalCount + 1} of 4 · ≤50 MB</span>
            <input
              type="file"
              accept="video/*"
              className="hidden"
              disabled={busy}
              onChange={(e) => attach(e.target.files?.[0])}
            />
          </label>
        )}
      </div>

      {msg && <p className="mt-3 text-xs text-warning">{msg}</p>}
    </div>
  );
}
