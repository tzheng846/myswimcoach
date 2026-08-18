"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";

const FRAME_S = 1 / 30;
const RATES = [0.25, 0.5, 1];

// One camera, annotate-page style (Phase 69, reworked per UAT): a SINGLE video with frame-step,
// speed, one-tap push-off sync, ±0.1 s nudge, and an explicit Save — the same workflow as
// /app/annotate/[id], so there is one video per camera (no separate synced player). Externals
// persist via PATCH /videos/{id}; the phone/primary via the legacy POST /video.
export default function CameraTile({ sessionId, video, pushoffSessionS, onChanged }) {
  const videoRef = useRef(null);
  const [label, setLabel] = useState(video.label ?? "");
  const [origin, setOrigin] = useState(video.origin_s ?? null); // pending origin
  const [savedOrigin, setSavedOrigin] = useState(video.origin_s ?? null);
  const [rate, setRate] = useState(1);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const isPrimary = video.role === "phone";
  const dirty = origin != null && origin !== savedOrigin;

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = rate;
  }, [rate, video.url]);

  const step = (frames) => {
    const v = videoRef.current;
    if (!v) return;
    v.pause();
    const d = Number.isFinite(v.duration) ? v.duration : 0;
    const next = v.currentTime + frames * FRAME_S;
    v.currentTime = Math.min(Math.max(next, 0), d || Math.max(next, 0));
  };

  const syncToPushoff = () => {
    const v = videoRef.current;
    if (!v || pushoffSessionS == null) return;
    setOrigin(Math.round((pushoffSessionS - v.currentTime) * 100) / 100);
  };

  const nudge = (d) => {
    if (origin == null) return;
    setOrigin(Math.round((origin + d) * 100) / 100);
  };

  const saveSync = async () => {
    if (origin == null) return;
    setBusy(true);
    setMsg(null);
    try {
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
      setSavedOrigin(origin);
      setMsg("Saved ✓");
      onChanged?.();
    } catch (e) {
      setMsg(`Save failed: ${e.message}`);
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
        <span className={`shrink-0 text-[11px] ${savedOrigin != null ? "text-success" : "text-warning"}`}>
          {savedOrigin != null ? "synced" : "needs sync"}
        </span>
      </div>

      {video.url ? (
        <video
          ref={videoRef}
          src={video.url}
          controls
          playsInline
          preload="metadata"
          className="w-full max-h-[clamp(140px,26vh,360px)] rounded-lg bg-black object-contain"
        />
      ) : (
        <p className="py-6 text-center text-xs text-muted">Video unavailable.</p>
      )}

      {/* Frame step + speed — same as the annotate page */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <button onClick={() => step(-1)} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">−1 frame</button>
        <button onClick={() => step(1)} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">+1 frame</button>
        <span className="ml-1 text-muted">Speed</span>
        {RATES.map((r) => (
          <button
            key={r}
            onClick={() => setRate(r)}
            className={`rounded-md border px-2 py-1 font-semibold ${
              rate === r ? "border-accent bg-accent text-white" : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
            }`}
          >
            {r}×
          </button>
        ))}
      </div>

      {/* Push-off sync + nudge + save — same workflow as the annotate page */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <button
          onClick={syncToPushoff}
          disabled={pushoffSessionS == null}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            pushoffSessionS != null ? "border border-accent bg-accent text-white" : "border border-surface-3 bg-surface-2 text-muted"
          }`}
          title="Scrub the video to the push-off frame, then sync"
        >
          Sync to push-off
        </button>
        <button onClick={() => nudge(-0.1)} disabled={origin == null} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">−0.1s</button>
        <span className="w-14 text-center font-mono text-ink">{origin != null ? `${origin.toFixed(2)} s` : "—"}</span>
        <button onClick={() => nudge(0.1)} disabled={origin == null} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">+0.1s</button>
        <button
          onClick={saveSync}
          disabled={busy || !dirty}
          className={`rounded-md px-2.5 py-1 font-semibold ${dirty ? "bg-accent text-white" : "bg-surface-2 text-muted"}`}
        >
          {busy ? "…" : "Save"}
        </button>
      </div>

      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-[11px] text-muted">
          {pushoffSessionS == null
            ? "Set the dive on the annotate page to enable one-tap sync."
            : "Scrub to the push-off frame, then Sync → Save."}
        </p>
        {!isPrimary && (
          <button onClick={remove} disabled={busy} className="shrink-0 text-[11px] font-semibold text-subtle hover:text-danger">
            Delete
          </button>
        )}
      </div>
      {msg && (
        <p className={`mt-1 text-[11px] ${/fail/i.test(msg) ? "text-danger" : "text-success"}`}>{msg}</p>
      )}
    </div>
  );
}
