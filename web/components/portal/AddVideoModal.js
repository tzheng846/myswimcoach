"use client";

import { useState } from "react";
import { apiUpload } from "@/lib/api";

// Report-card "Add video" popup (Phase 71). Uploads an EXTERNAL angle to session_videos via
// POST /sessions/{id}/videos — the unified GET /videos reader then shows it inline. Mirrors the
// AddAthleteModal shell (fixed overlay, click-outside close). No new dependency.
const MAX_VIDEO_BYTES = 50 * 1024 * 1024; // matches api.py + VideoPane (free-tier ceiling)

export default function AddVideoModal({ sessionId, onClose, onAdded }) {
  const [file, setFile] = useState(null);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleAdd(e) {
    e.preventDefault();
    if (!file) return;
    // Reject over-cap client-side for an instant reason, matching the server 413 + Supabase limit.
    if (file.size > MAX_VIDEO_BYTES) {
      const cap = MAX_VIDEO_BYTES / (1024 * 1024);
      setError(
        `This clip is ${Math.round(file.size / (1024 * 1024))} MB — over the ${cap} MB limit. ` +
          `Compress it (HandBrake / GoPro Quik) to under ${cap} MB, or upgrade to Pro storage.`
      );
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (label.trim()) fd.append("label", label.trim());
      const result = await apiUpload(`/sessions/${sessionId}/videos`, fd);
      onAdded?.(result);
      onClose();
    } catch (err) {
      setError(
        err.status === 409
          ? "Max 3 camera angles per session — delete one on the videos page to add another."
          : err.status === 413
            ? "That clip is over the 50 MB limit. Compress it (HandBrake / GoPro Quik) first."
            : err.message
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-5"
      onClick={onClose}
    >
      <form
        onSubmit={handleAdd}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-2xl border border-navy bg-surface p-6"
      >
        <h2 className="text-lg font-bold">Add video</h2>
        <p className="mt-1 text-xs leading-relaxed text-muted">
          Attach a camera angle to this session. It plays on the report card; line multiple angles
          up on the annotate page. Best results: H.264 .mp4, ≤50 MB.
        </p>
        <input
          type="file"
          accept="video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="mt-4 w-full text-sm text-subtle file:mr-3 file:rounded-lg file:border-0 file:bg-surface-2 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-ink"
        />
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label (optional, e.g. Underwater front)"
          className="mt-3 w-full rounded-lg border border-surface-3 bg-surface-2 px-4 py-3 text-sm outline-none focus:border-primary"
        />
        {error && <p className="mt-3 text-sm text-[#ff5252]">{error}</p>}
        <div className="mt-5 flex gap-3">
          <button
            type="submit"
            disabled={busy || !file}
            className="flex-1 rounded-lg bg-primary py-2.5 font-semibold text-white transition-colors hover:bg-accent disabled:opacity-60"
          >
            {busy ? "Uploading…" : "Add"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-surface-3 py-2.5 text-subtle hover:text-ink"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
