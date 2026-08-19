"use client";

// Phase 70 — Video↔Session Matching (manual core).
// A batch surface: the coach dumps many opaque external clips (GX010042.MP4…), sees a CONTENT
// thumbnail of each (recognize the swim — filenames/metadata are untrustworthy, D2), and assigns
// each to a session by reusing Phase-69 `POST /sessions/{id}/videos`. Staging is entirely
// client-side; thumbnails are canvas frame-grabs (no server, no schema). QR slate is a deferred
// follow-on (CONTEXT D4–D9).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { supabase } from "@/lib/supabase";
import { apiUpload } from "@/lib/api";
import { sessionLabel } from "@/lib/sessionName";

const MAX_VIDEO_BYTES = 50 * 1024 * 1024; // matches api.py + AddVideoModal (free-tier ceiling)

function fmtDuration(s) {
  if (s == null || !isFinite(s)) return "—";
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}
function fmtSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function fmtDate(ms) {
  if (!ms) return "";
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
function baseName(name) {
  return String(name).replace(/\.[^/.]+$/, "");
}

// Grab a preview frame + duration from a same-origin object URL, entirely in the browser.
// Same-origin blob → no canvas taint, so toDataURL is allowed. Resolves {dataUrl, durationS};
// rejects on any failure so the caller can show a "no preview" placeholder (never blocks the card).
function grabThumb(url) {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.muted = true;
    video.playsInline = true;
    video.src = url;

    let settled = false;
    const finish = (fn) => (arg) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      video.src = "";
      fn(arg);
    };
    const ok = finish(resolve);
    const fail = finish(reject);
    // Guard against browsers that never fire `seeked` (e.g. seek to 0).
    const timer = setTimeout(() => fail(new Error("thumb timeout")), 8000);

    const draw = () => {
      try {
        const w = 320;
        const scale = video.videoWidth ? w / video.videoWidth : 1;
        const h = Math.max(1, Math.round((video.videoHeight || 180) * scale));
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        canvas.getContext("2d").drawImage(video, 0, 0, w, h);
        ok({ dataUrl: canvas.toDataURL("image/jpeg", 0.7), durationS: video.duration });
      } catch (e) {
        fail(e);
      }
    };

    video.addEventListener("error", () => fail(new Error("video load failed")), { once: true });
    video.addEventListener("loadedmetadata", () => {
      video.addEventListener("seeked", draw, { once: true });
      // ~10% in (capped at 1s) — past any black lead-in, before the swim usually ends.
      try {
        video.currentTime = Math.min(1, (video.duration || 0) * 0.1);
      } catch {
        draw();
      }
    }, { once: true });
  });
}

export default function MatchPage() {
  const [clips, setClips] = useState([]);
  const [athletes, setAthletes] = useState([]);
  const [sessions, setSessions] = useState(null); // null = loading
  const [athleteFilter, setAthleteFilter] = useState("all");
  const idRef = useRef(0);
  const fileInputRef = useRef(null);

  // Read athletes + sessions via supabase-js (RLS), mirroring the Sessions page. We fetch every
  // session once and narrow the pickers client-side by athlete. NOTE: session_videos is
  // service-role-only (RLS denies anon), so we do NOT query it here — a full session is caught by
  // the 409 on assign.
  useEffect(() => {
    supabase
      .from("athletes")
      .select("id, name")
      .order("name")
      .then(({ data }) => setAthletes(data ?? []));
    supabase
      .from("sessions")
      .select("id, created_at, name, stroke_type, athlete_id, video_path")
      .order("created_at", { ascending: false })
      .then(({ data }) => setSessions(data ?? []));
  }, []);

  const patchClip = useCallback((id, patch) => {
    setClips((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...(typeof patch === "function" ? patch(c) : patch) } : c))
    );
  }, []);

  const handleFiles = useCallback(
    (fileList) => {
      const files = Array.from(fileList || []);
      if (!files.length) return;
      const staged = files.map((file) => {
        const id = ++idRef.current;
        const url = URL.createObjectURL(file);
        return {
          id,
          file,
          url,
          thumb: null,
          thumbFailed: false,
          durationS: null,
          overCap: file.size > MAX_VIDEO_BYTES,
          status: "staged", // staged | uploading | done | error
          error: null,
          sessionId: "",
        };
      });
      setClips((prev) => [...prev, ...staged]);
      // Kick off thumbnail generation per clip (fire-and-forget; updates state when ready).
      staged.forEach((clip) => {
        grabThumb(clip.url)
          .then(({ dataUrl, durationS }) => patchClip(clip.id, { thumb: dataUrl, durationS }))
          .catch(() => patchClip(clip.id, { thumbFailed: true }));
      });
      // Allow re-picking the same file(s) later.
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [patchClip]
  );

  const removeClip = useCallback((id) => {
    setClips((prev) => {
      const target = prev.find((c) => c.id === id);
      if (target) URL.revokeObjectURL(target.url);
      return prev.filter((c) => c.id !== id);
    });
  }, []);

  // Revoke every object URL on unmount (avoid leaks). clipsRef tracks the latest without
  // re-running the cleanup effect.
  const clipsRef = useRef(clips);
  clipsRef.current = clips;
  useEffect(
    () => () => clipsRef.current.forEach((c) => URL.revokeObjectURL(c.url)),
    []
  );

  const sessionById = useMemo(
    () => new Map((sessions ?? []).map((s) => [s.id, s])),
    [sessions]
  );

  const pickerSessions = useMemo(() => {
    const list = sessions ?? [];
    return athleteFilter === "all"
      ? list
      : list.filter((s) => s.athlete_id === athleteFilter);
  }, [sessions, athleteFilter]);

  const assignClip = useCallback(
    async (id) => {
      // Read the freshest clip from state.
      let clip;
      setClips((prev) => {
        clip = prev.find((c) => c.id === id);
        return prev;
      });
      if (!clip || !clip.sessionId || clip.status === "uploading" || clip.status === "done") return;
      patchClip(id, { status: "uploading", error: null });
      try {
        const fd = new FormData();
        fd.append("file", clip.file);
        fd.append("label", baseName(clip.file.name)); // so the attached angle is recognizable later
        await apiUpload(`/sessions/${clip.sessionId}/videos`, fd);
        patchClip(id, { status: "done" });
      } catch (err) {
        // Mirror AddVideoModal's mapping exactly.
        const msg =
          err.status === 409
            ? "That session already has 3 camera angles — pick another, or remove one on its annotate page."
            : err.status === 413
              ? "Over the 50 MB limit. Compress it (HandBrake / GoPro Quik) first."
              : err.message;
        patchClip(id, { status: "error", error: msg });
      }
    },
    [patchClip]
  );

  const assignAll = useCallback(async () => {
    // Snapshot the ids to assign; upload sequentially so errors stay attributable per-clip.
    const ids = clipsRef.current
      .filter((c) => c.sessionId && c.status !== "done" && c.status !== "uploading")
      .map((c) => c.id);
    for (const id of ids) {
      // eslint-disable-next-line no-await-in-loop
      await assignClip(id);
    }
  }, [assignClip]);

  const anyAssignable = clips.some(
    (c) => c.sessionId && c.status !== "done" && c.status !== "uploading"
  );

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Match videos</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Drop in your external clips, recognize each swim by its preview, and attach it to the right
            session. Filenames and timestamps aren&apos;t trusted — you decide the match.
          </p>
        </div>
        <button
          onClick={assignAll}
          disabled={!anyAssignable}
          className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent disabled:opacity-50"
        >
          Assign all matched
        </button>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <label className="cursor-pointer rounded-lg border border-surface-3 bg-surface px-4 py-2.5 text-sm font-semibold text-ink transition-colors hover:border-primary">
          + Add clips
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            multiple
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
        </label>
        <select
          value={athleteFilter}
          onChange={(e) => setAthleteFilter(e.target.value)}
          className="rounded-lg border border-surface-3 bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
        >
          <option value="all">All athletes</option>
          {athletes.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        {sessions === null && <span className="text-sm text-muted">Loading sessions…</span>}
      </div>

      {clips.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-surface-3 py-16 text-center text-muted">
          No clips yet. Click <span className="font-semibold text-subtle">+ Add clips</span> to stage
          your external footage.
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clips.map((clip) => {
            const chosen = clip.sessionId ? sessionById.get(clip.sessionId) : null;
            return (
              <div
                key={clip.id}
                className={`overflow-hidden rounded-2xl border bg-surface ${
                  clip.status === "done" ? "border-primary/50 opacity-70" : "border-surface-3"
                }`}
              >
                <div className="relative aspect-video w-full bg-surface-2">
                  {clip.thumb ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={clip.thumb} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xs text-muted">
                      {clip.thumbFailed ? "No preview" : "Generating preview…"}
                    </div>
                  )}
                  <button
                    onClick={() => removeClip(clip.id)}
                    className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white hover:bg-black/80"
                    aria-label="Remove clip"
                  >
                    ✕
                  </button>
                </div>

                <div className="p-4">
                  <p className="truncate text-sm font-semibold text-ink" title={clip.file.name}>
                    {clip.file.name}
                  </p>
                  {/* Soft hints only — never used to auto-decide the match (D2). */}
                  <p className="mt-1 text-xs text-muted">
                    {fmtDuration(clip.durationS)} ·{" "}
                    <span className={clip.overCap ? "text-[#ff5252]" : ""}>{fmtSize(clip.file.size)}</span>
                    {fmtDate(clip.file.lastModified) ? ` · ${fmtDate(clip.file.lastModified)}` : ""}
                  </p>
                  {clip.overCap && (
                    <p className="mt-1 text-xs text-[#ff5252]">
                      Over 50 MB — compress before assigning.
                    </p>
                  )}

                  <select
                    value={clip.sessionId}
                    onChange={(e) => patchClip(clip.id, { sessionId: e.target.value, error: null })}
                    disabled={clip.status === "done" || clip.status === "uploading"}
                    className="mt-3 w-full rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-60"
                  >
                    <option value="">Choose session…</option>
                    {pickerSessions.map((s) => (
                      <option key={s.id} value={s.id}>
                        {sessionLabel(s, { withStroke: true })}
                        {s.video_path ? " · 📹" : ""}
                      </option>
                    ))}
                  </select>

                  <div className="mt-3 min-h-[2.25rem]">
                    {clip.status === "done" ? (
                      <p className="text-sm font-medium text-primary">
                        ✓ Attached{chosen ? ` to ${sessionLabel(chosen)}` : ""}
                      </p>
                    ) : (
                      <button
                        onClick={() => assignClip(clip.id)}
                        disabled={!clip.sessionId || clip.status === "uploading"}
                        className="w-full rounded-lg bg-primary py-2 text-sm font-semibold text-white transition-colors hover:bg-accent disabled:opacity-50"
                      >
                        {clip.status === "uploading" ? "Uploading…" : "Assign"}
                      </button>
                    )}
                    {clip.error && <p className="mt-2 text-sm text-[#ff5252]">{clip.error}</p>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
