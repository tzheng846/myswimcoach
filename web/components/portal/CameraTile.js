"use client";

import { useCallback, useRef, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";

// One camera in the multi-cam grid (Phase 69-02). Native-controls playback for setup, a one-tap
// push-off sync (the Phase 67-01 mechanic, run per camera), an editable label, and delete. The
// synced-timeline player (69-03) drives all tiles together; here each plays individually so the
// coach can scrub it to its own push-off frame.
//
// Persist path differs by role: the phone/primary origin goes through the legacy POST /video
// (unchanged, mobile-shared); an external's origin/label go through PATCH /sessions/{id}/videos/{id}.
export default function CameraTile({ sessionId, video, pushoffSessionS, onChanged }) {
  const videoRef = useRef(null);
  const [label, setLabel] = useState(video.label ?? "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const isPrimary = video.role === "phone";
  const synced = video.origin_s != null;

  const persistOrigin = useCallback(
    async (origin) => {
      if (isPrimary) {
        const fd = new FormData();
        fd.append("video_origin_s", String(origin));
        await apiUpload(`/sessions/${sessionId}/video`, fd);
      } else {
        await apiFetch(`/sessions/${sessionId}/videos/${video.id}`, {
          method: "PATCH",
          body: JSON.stringify({ origin_s: origin }),
        });
      }
    },
    [isPrimary, sessionId, video.id]
  );

  const syncToPushoff = async () => {
    const v = videoRef.current;
    if (!v || pushoffSessionS == null) return;
    const origin = Math.round((pushoffSessionS - v.currentTime) * 100) / 100;
    setBusy(true);
    setMsg(null);
    try {
      await persistOrigin(origin);
      setMsg("Synced.");
      onChanged?.();
    } catch (e) {
      setMsg(`Sync failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const saveLabel = async () => {
    if (isPrimary || label === (video.label ?? "")) return;
    setBusy(true);
    try {
      await apiFetch(`/sessions/${sessionId}/videos/${video.id}`, {
        method: "PATCH",
        body: JSON.stringify({ label }),
      });
      onChanged?.();
    } catch (e) {
      setMsg(`Rename failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (isPrimary) return;
    setBusy(true);
    try {
      await apiFetch(`/sessions/${sessionId}/videos/${video.id}`, { method: "DELETE" });
      onChanged?.();
    } catch (e) {
      setMsg(`Delete failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        {isPrimary ? (
          <span className="text-sm font-semibold text-ink">Phone</span>
        ) : (
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={saveLabel}
            placeholder="Label (e.g. Underwater front)"
            className="min-w-0 flex-1 rounded-md border border-surface-3 bg-surface-2 px-2 py-1 text-sm text-ink placeholder:text-muted"
          />
        )}
        <span className={`shrink-0 text-[11px] ${synced ? "text-success" : "text-warning"}`}>
          {synced ? "synced" : "needs sync"}
        </span>
      </div>

      {video.url ? (
        <video
          ref={videoRef}
          src={video.url}
          controls
          playsInline
          className="w-full max-h-[clamp(140px,26vh,360px)] rounded-lg bg-black object-contain"
        />
      ) : (
        <p className="py-6 text-center text-xs text-muted">Video unavailable.</p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <button
          onClick={syncToPushoff}
          disabled={busy || pushoffSessionS == null}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            pushoffSessionS != null
              ? "border border-accent bg-accent text-white"
              : "border border-surface-3 bg-surface-2 text-muted"
          }`}
          title="Scrub the video to the push-off frame, then sync"
        >
          Sync to push-off
        </button>
        {!isPrimary && (
          <button
            onClick={remove}
            disabled={busy}
            className="ml-auto rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-danger"
          >
            Delete
          </button>
        )}
      </div>

      {pushoffSessionS == null ? (
        <p className="mt-1 text-[11px] text-muted">
          No push-off detected — set the dive on the annotate page to enable one-tap sync.
        </p>
      ) : (
        <p className="mt-1 text-[11px] text-muted">Scrub to the push-off frame, then Sync to push-off.</p>
      )}
      {msg && <p className="mt-1 text-[11px] text-subtle">{msg}</p>}
    </div>
  );
}
