"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";

// Session video: signed-URL playback synced to the velocity trace.
// sessionTime = originS + videoTime (44-03 end-anchor convention).
// No video attached → an upload input (velocity-only annotation stays fully usable).
export default function VideoPane({
  sessionId,
  video, // {path, origin_s} | null
  onPlayhead, // (sessionTimeS | null) => void
  seekRef, // ref; pane assigns seekRef.current = (sessionTimeS) => void
  onVideoChange, // ({path, origin_s}) => void
}) {
  const videoRef = useRef(null);
  const [url, setUrl] = useState(null);
  const [originS, setOriginS] = useState(video?.origin_s ?? 0);
  const [savedOrigin, setSavedOrigin] = useState(video?.origin_s ?? 0);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  // Signed URL expires (3600 s) — always refetched on mount, never persisted.
  useEffect(() => {
    if (!video?.path) {
      setUrl(null);
      return;
    }
    let alive = true;
    (async () => {
      try {
        const r = await apiFetch(`/sessions/${sessionId}/video-url`);
        if (!alive) return;
        setUrl(r.url);
        if (r.origin_s != null) {
          setOriginS(r.origin_s);
          setSavedOrigin(r.origin_s);
        }
      } catch (e) {
        if (alive) setMsg(`Could not load video: ${e.message}`);
      }
    })();
    return () => {
      alive = false;
    };
  }, [sessionId, video?.path]);

  // Expose seek to the page (Seek tool routes chart clicks here).
  useEffect(() => {
    if (!seekRef) return;
    seekRef.current = (sessionT) => {
      const v = videoRef.current;
      if (!v) return;
      const dur = Number.isFinite(v.duration) ? v.duration : 0;
      v.currentTime = Math.min(Math.max(sessionT - originS, 0), dur);
      onPlayhead?.(originS + v.currentTime);
    };
    return () => {
      seekRef.current = null;
    };
  }, [seekRef, originS, url, onPlayhead]);

  const nudge = (d) => {
    const next = Math.round((originS + d) * 100) / 100;
    setOriginS(next);
    const v = videoRef.current;
    if (v) onPlayhead?.(next + v.currentTime);
  };

  const saveSync = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("video_origin_s", String(originS));
      await apiUpload(`/sessions/${sessionId}/video`, fd);
      setSavedOrigin(originS);
      onVideoChange?.({ path: video.path, origin_s: originS });
      setMsg("Sync saved.");
    } catch (e) {
      setMsg(`Save failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const attach = async (file) => {
    if (!file) return;
    setBusy(true);
    setMsg("Uploading video…");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await apiUpload(`/sessions/${sessionId}/video`, fd);
      setMsg(null);
      onVideoChange?.({
        path: r.video_path,
        origin_s: r.video_origin_s ?? 0,
      });
    } catch (e) {
      setMsg(`Upload failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  if (!video?.path) {
    return (
      <div className="rounded-xl border border-navy/50 bg-surface p-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Video
        </p>
        <p className="mb-3 text-xs leading-relaxed text-muted">
          No video attached — annotation works on the velocity trace alone.
          Attach one to review side-by-side.
        </p>
        <label className="inline-block cursor-pointer rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm font-semibold text-subtle hover:text-ink">
          {busy ? "Uploading…" : "Attach video"}
          <input
            type="file"
            accept="video/*"
            className="hidden"
            disabled={busy}
            onChange={(e) => attach(e.target.files?.[0])}
          />
        </label>
        {msg && <p className="mt-2 text-xs text-warning">{msg}</p>}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Video
      </p>
      {url ? (
        <video
          ref={videoRef}
          src={url}
          controls
          playsInline
          className="w-full rounded-lg bg-black"
          onTimeUpdate={() => {
            const v = videoRef.current;
            if (v) onPlayhead?.(originS + v.currentTime);
          }}
        />
      ) : (
        <p className="py-6 text-center text-xs text-muted">Loading video…</p>
      )}
      {/* Sync: sessionTime = origin + videoTime */}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted">Sync offset</span>
        <button
          onClick={() => nudge(-0.1)}
          className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
        >
          −0.1s
        </button>
        <span className="w-16 text-center font-mono text-ink">
          {originS.toFixed(2)} s
        </span>
        <button
          onClick={() => nudge(0.1)}
          className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
        >
          +0.1s
        </button>
        <button
          onClick={saveSync}
          disabled={busy || originS === savedOrigin}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            originS !== savedOrigin
              ? "bg-accent text-white"
              : "bg-surface-2 text-muted"
          }`}
        >
          {busy ? "…" : "Save sync"}
        </button>
      </div>
      {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
    </div>
  );
}
