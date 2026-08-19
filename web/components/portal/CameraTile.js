"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";

const FRAME_S = 1 / 30;
const RATES = [0.25, 0.5, 1];

// One camera on the annotate multi-cam hub (Phase 71). A single <video> with frame-step, speed,
// MANUAL two-point align ("Set sync" → click the trace at the same moment), ±0.1 s nudge, and an
// explicit Save. When `active`, it drives the trace playhead / seek / frame-step for mark placing.
// Externals persist via PATCH /videos/{id}; the phone/primary via the legacy POST /video.
// ⚠ No push-off / dive detection anywhere (removed 71-02, D10) — alignment is coach-controlled.
export default function CameraTile({
  sessionId,
  video,
  active = false,
  aligning = false,
  alignClick, // { time, seq } — bumped by the parent when the coach clicks the trace in align mode
  onArmAlign, // () => void — "Set sync": arm this camera for the next trace click
  onAlignConsumed, // () => void — this camera used the trace click; parent clears align mode
  onMakeActive, // () => void
  onPlayhead, // (sessionTimeS) => void — called only while active
  // ⚠ NO `= null` defaults on the ref props (react-hooks/immutability treats a defaulted prop as a
  // local and flags assigning to `.current`). `undefined` guards identically (`if (!ref) return`).
  seekRef, // ref; assigned only while active
  frameStepRef, // ref; assigned only while active
  onChanged, // () => void — refetch the list after delete (NOT after save/label — avoids url churn)
}) {
  const videoRef = useRef(null);
  const [label, setLabel] = useState(video.label ?? "");
  const [origin, setOrigin] = useState(video.origin_s ?? null); // pending origin
  const [savedOrigin, setSavedOrigin] = useState(video.origin_s ?? null);
  const [rate, setRate] = useState(1);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const isPrimary = video.role === "phone";
  const dirty = origin != null && origin !== savedOrigin;
  const effectiveOrigin = origin ?? savedOrigin;

  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = rate;
  }, [rate, video.url]);

  // sessionTime = origin + videoTime — reported to the parent only while this is the active camera.
  const reportPlayhead = useCallback(() => {
    const v = videoRef.current;
    if (active && v && effectiveOrigin != null) onPlayhead?.(effectiveOrigin + v.currentTime);
  }, [active, effectiveOrigin, onPlayhead]);

  const step = useCallback(
    (frames) => {
      const v = videoRef.current;
      if (!v) return;
      v.pause();
      const d = Number.isFinite(v.duration) ? v.duration : 0;
      const next = v.currentTime + frames * FRAME_S;
      v.currentTime = Math.min(Math.max(next, 0), d || Math.max(next, 0));
      reportPlayhead();
    },
    [reportPlayhead]
  );

  // Marking wiring: while active, this camera answers the chart's Seek tool and keyboard frame-step.
  // No cleanup-null: only the active tile assigns, so the shared ref holds the newest active fn —
  // nulling in cleanup would race across tiles when the active camera switches.
  useEffect(() => {
    if (!active || !seekRef) return;
    seekRef.current = (sessionT) => {
      const v = videoRef.current;
      if (!v || effectiveOrigin == null) return;
      const d = Number.isFinite(v.duration) ? v.duration : 0;
      v.currentTime = Math.min(Math.max(sessionT - effectiveOrigin, 0), d);
      reportPlayhead();
    };
  }, [active, seekRef, effectiveOrigin, reportPlayhead]);

  useEffect(() => {
    if (!active || !frameStepRef) return;
    frameStepRef.current = step;
  }, [active, frameStepRef, step]);

  // Two-point align: when armed (aligning) and the coach clicks the trace, the parent bumps
  // alignClick.seq; map the CURRENT video frame to that trace time → origin = traceTime − videoTime.
  const lastAlignSeq = useRef(0);
  useEffect(() => {
    if (!aligning || !alignClick || alignClick.time == null) return;
    if (alignClick.seq === lastAlignSeq.current) return;
    lastAlignSeq.current = alignClick.seq;
    const v = videoRef.current;
    if (!v) return;
    setOrigin(Math.round((alignClick.time - v.currentTime) * 100) / 100);
    onAlignConsumed?.();
  }, [aligning, alignClick, onAlignConsumed]);

  const nudge = (d) => {
    const base = origin ?? savedOrigin;
    if (base == null) return;
    setOrigin(Math.round((base + d) * 100) / 100);
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
    <div className={`rounded-xl border ${active ? "border-accent" : "border-navy/50"} bg-surface p-3`}>
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
        {active ? (
          <span className="shrink-0 rounded-md bg-accent px-2 py-0.5 text-[11px] font-semibold text-white">
            ● Marking
          </span>
        ) : (
          <button
            onClick={onMakeActive}
            className="shrink-0 rounded-md border border-surface-3 bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-subtle hover:text-ink"
          >
            Mark from this
          </button>
        )}
      </div>

      {video.url ? (
        <video
          ref={videoRef}
          src={video.url}
          controls
          playsInline
          preload="metadata"
          onTimeUpdate={reportPlayhead}
          className="w-full max-h-[clamp(140px,26vh,360px)] rounded-lg bg-black object-contain"
        />
      ) : (
        <p className="py-6 text-center text-xs text-muted">Video unavailable.</p>
      )}

      {/* Frame step + speed + sync status */}
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
        <span className={`ml-auto text-[11px] ${savedOrigin != null ? "text-success" : "text-warning"}`}>
          {savedOrigin != null ? "synced" : "needs sync"}
        </span>
      </div>

      {/* Manual two-point align + nudge + save (no push-off, no dive detection — D10/D11) */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <button
          onClick={onArmAlign}
          className={`rounded-md px-2.5 py-1 font-semibold ${
            aligning ? "border border-accent bg-accent text-white" : "border border-accent text-primary"
          }`}
          title="Scrub to a landmark frame, click this, then click the trace at the same moment"
        >
          {aligning ? "Click the trace…" : "Set sync"}
        </button>
        <button onClick={() => nudge(-0.1)} disabled={effectiveOrigin == null} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">−0.1s</button>
        <span className="w-14 text-center font-mono text-ink">{effectiveOrigin != null ? `${effectiveOrigin.toFixed(2)} s` : "—"}</span>
        <button onClick={() => nudge(0.1)} disabled={effectiveOrigin == null} className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink">+0.1s</button>
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
          {aligning
            ? "Now click the trace at the same moment shown in this video."
            : "Scrub to a landmark, click Set sync, then click the trace at that instant."}
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
