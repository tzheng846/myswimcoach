"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import AnnotationChart, { PHASE_META } from "@/components/portal/AnnotationChart";
import AnnotationEditor from "@/components/portal/AnnotationEditor";
import VideoPane from "@/components/portal/VideoPane";

const PHASE_KEYS = PHASE_META.map((m) => m.key);
const UNDO_DEPTH = 50;

function normalizePhases(p) {
  const out = {};
  for (const k of PHASE_KEYS) out[k] = p?.[k] ?? null;
  return out;
}

export default function AnnotatePage({ params }) {
  const { id: sessionId } = use(params);

  const [row, setRow] = useState(null); // sessions row (velocity, stroke_type, …)
  const [ann, setAnn] = useState(null); // GET /annotations payload
  const [loadError, setLoadError] = useState(null);

  // Editor state (single source of truth)
  const [phases, setPhases] = useState(normalizePhases(null));
  const [strokeMarks, setStrokeMarks] = useState([]);
  const [activeTool, setActiveTool] = useState("stroke");
  const [selected, setSelected] = useState(null); // {kind, index} | null
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState([]);
  const [hint, setHint] = useState(null);
  const [savedMsg, setSavedMsg] = useState(null);
  const [hasSaved, setHasSaved] = useState(false);
  const [viewMode, setViewMode] = useState("fit");

  // Undo lives in a ref, not state: ~40 marks per session across 19 sessions means
  // hundreds of snapshots, and putting them in state would re-render the whole chart
  // on every single click. Only the depth (for the button) is state.
  const undoRef = useRef([]);
  const [undoDepth, setUndoDepth] = useState(0);

  // Video sync
  const [video, setVideo] = useState(null); // {path, origin_s} | null
  const [playheadS, setPlayheadS] = useState(null);
  const seekRef = useRef(null);
  const frameStepRef = useRef(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [{ data: sRow, error: sErr }, annRes] = await Promise.all([
        supabase
          .from("sessions")
          .select(
            "velocity_profile, stroke_type, name, athlete_id, created_at, sample_rate_hz"
          )
          .eq("id", sessionId)
          .single(),
        apiFetch(`/sessions/${sessionId}/annotations`).catch((e) => ({
          _error: e,
        })),
      ]);
      if (!alive) return;
      if (sErr) {
        setLoadError("Failed to load session.");
        return;
      }
      if (annRes?._error) {
        setLoadError(`Failed to load annotations: ${annRes._error.message}`);
        return;
      }
      setRow(sRow);
      setAnn(annRes);
      setVideo(annRes.video ?? null);
      // Phase 57 (D6): the editor starts BLANK. `annRes.seed` is still returned by the
      // API and still useful to other callers, but applying it here would seed ground
      // truth from the very segmenter this annotation exists to evaluate — circular,
      // and it anchors the annotator toward the errors 16-06 is meant to find.
      const saved = annRes.annotation ?? null;
      setPhases(normalizePhases(saved?.phases));
      setStrokeMarks([...(saved?.stroke_marks_s ?? [])].sort((a, b) => a - b));
      setHasSaved(!!saved);
      undoRef.current = [];
      setUndoDepth(0);
      setDirty(false);
      setSavedMsg(saved ? "Loaded saved annotation" : "New annotation — nothing marked yet");
    })();
    return () => {
      alive = false;
    };
  }, [sessionId]);

  const vel = row?.velocity_profile ?? [];
  // Must match the rate the API used to build the seed (GET /annotations returns it as
  // sample_rate_hz) — a mismatch puts marks on the wrong x position, and the times this
  // page saves would be re-interpreted against a different clock on recompute.
  const fsHz = row?.sample_rate_hz > 0 ? row.sample_rate_hz : 100;
  const time = useMemo(
    () => Array.from({ length: vel.length }, (_, i) => i / fsHz),
    [vel.length, fsHz]
  );

  // Phase 67 — the align target for VideoPane's "Sync to push-off". Prefer a coach-placed Dive /
  // Underwater marker; fall back to the auto seed's dive (build_seed sets dive_start_s =
  // baseline_end_s). Read-only use of the seed — Phase 57 D6's blank editor start is untouched, so
  // this enables one-tap sync with ZERO marks placed yet follows a placed Dive mark when there is one.
  const pushoffSessionS = useMemo(
    () =>
      phases.dive_start_s ??
      phases.underwater_start_s ??
      ann?.seed?.phases?.dive_start_s ??
      ann?.seed?.phases?.underwater_start_s ??
      null,
    [phases.dive_start_s, phases.underwater_start_s, ann]
  );

  // Snapshot before every mutation so undo can restore it.
  const pushUndo = useCallback(() => {
    undoRef.current.push({ phases, strokeMarks });
    if (undoRef.current.length > UNDO_DEPTH) undoRef.current.shift();
    setUndoDepth(undoRef.current.length);
  }, [phases, strokeMarks]);

  const undo = useCallback(() => {
    const prev = undoRef.current.pop();
    setUndoDepth(undoRef.current.length);
    if (!prev) return;
    setPhases(prev.phases);
    setStrokeMarks(prev.strokeMarks);
    setSelected(null);
    setDirty(true);
    setHint(null);
  }, []);

  // Place one stroke mark. The swim-window guard mirrors the server rule (57-01) so a
  // mark that PUT would reject is never placed in the first place; 422 strings still
  // render below as belt-and-braces. This lives in ONE place and is shared by chart
  // clicks and mark-at-playhead — a second copy is exactly how the client rule drifts
  // from the server's, and the server would then reject a mark the UI accepted.
  const placeStrokeMark = useCallback(
    (t) => {
      const tt = Math.round(t * 100) / 100;
      const lo = phases.stroke_start_s;
      const hi = phases.finish_s;
      if (lo != null && tt < lo) {
        setHint(`Outside the swim: ${tt.toFixed(2)} s is before Stroke (${lo.toFixed(2)} s).`);
        return;
      }
      if (hi != null && tt > hi) {
        setHint(`Outside the swim: ${tt.toFixed(2)} s is after Finish (${hi.toFixed(2)} s).`);
        return;
      }
      pushUndo();
      setHint(null);
      setStrokeMarks((prev) => [...prev, tt].sort((a, b) => a - b));
      setDirty(true);
    },
    [phases, pushUndo]
  );

  const handleChartClick = useCallback(
    (t) => {
      const tt = Math.round(t * 100) / 100;
      if (activeTool === "seek") {
        seekRef.current?.(tt);
        return;
      }
      if (activeTool === "stroke") {
        placeStrokeMark(tt);
        return;
      }
      // Phase tool: place / move that boundary
      pushUndo();
      setHint(null);
      setPhases((prev) => ({ ...prev, [activeTool]: tt }));
      setDirty(true);
    },
    [activeTool, placeStrokeMark, pushUndo]
  );

  // Drag from the chart. Snapshot only on the FIRST move of a gesture, otherwise a
  // single drag would fill the undo stack with one entry per mouse event.
  const draggingRef = useRef(false);
  const handleMarkDrag = useCallback(
    (kind, index, t) => {
      const tt = Math.round(t * 100) / 100;
      if (!draggingRef.current) {
        draggingRef.current = true;
        pushUndo();
      }
      if (kind === "stroke") {
        setStrokeMarks((prev) => prev.map((v, i) => (i === index ? tt : v)));
      } else {
        setPhases((prev) => ({ ...prev, [kind]: tt }));
      }
      setDirty(true);
    },
    [pushUndo]
  );

  useEffect(() => {
    const up = () => {
      if (draggingRef.current) {
        draggingRef.current = false;
        // Marks may have crossed while dragging; keep the array sorted like the server does.
        setStrokeMarks((prev) => [...prev].sort((a, b) => a - b));
      }
    };
    window.addEventListener("mouseup", up);
    return () => window.removeEventListener("mouseup", up);
  }, []);

  const clearPhase = useCallback(
    (key) => {
      pushUndo();
      setPhases((prev) => ({ ...prev, [key]: null }));
      setDirty(true);
    },
    [pushUndo]
  );

  const removeMark = useCallback(
    (i) => {
      pushUndo();
      setStrokeMarks((prev) => prev.filter((_, idx) => idx !== i));
      setSelected(null);
      setDirty(true);
    },
    [pushUndo]
  );

  const clearAllMarks = useCallback(() => {
    pushUndo();
    setStrokeMarks([]);
    setSelected(null);
    setDirty(true);
  }, [pushUndo]);

  // Keyboard. Two modes, switched by whether a mark is selected:
  //   nothing selected → ←/→ step the VIDEO a frame
  //   mark selected    → ←/→ nudge that mark (pre-58 behavior, unchanged)
  // Esc is the way back out of nudge mode; M drops a mark at the video playhead.
  useEffect(() => {
    const onKey = (e) => {
      const tag = e.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || e.target?.isContentEditable) return;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
        return;
      }

      // Mark at the video's current time. Deliberately does NOT select the new mark:
      // selecting it would flip the arrows into nudge mode, so the
      // step → mark → step → mark loop this exists to enable would break on its
      // second iteration.
      if (e.key.toLowerCase() === "m" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        if (playheadS == null) {
          setHint("No video playhead yet — attach a video and scrub it, or click the trace.");
        } else {
          placeStrokeMark(playheadS);
        }
        return;
      }

      if (e.key === "Escape") {
        setSelected(null);
        return;
      }

      const isArrow = e.key === "ArrowLeft" || e.key === "ArrowRight";

      if (!selected) {
        // preventDefault is load-bearing, not hygiene: when the <video controls>
        // element has focus, Chrome's native handler seeks ±5 s on these keys and
        // would fight the frame step.
        if (isArrow) {
          e.preventDefault();
          const dir = e.key === "ArrowLeft" ? -1 : 1;
          frameStepRef.current?.(dir * (e.shiftKey ? 10 : 1));
        }
        return;
      }

      if (isArrow) {
        e.preventDefault();
        const step = (e.shiftKey ? 10 : 1) / fsHz;
        const delta = e.key === "ArrowLeft" ? -step : step;
        pushUndo();
        if (selected.kind === "stroke") {
          setStrokeMarks((prev) =>
            prev.map((v, i) =>
              i === selected.index ? Math.max(0, Math.round((v + delta) * 1000) / 1000) : v
            )
          );
        } else {
          setPhases((prev) => ({
            ...prev,
            [selected.kind]: Math.max(
              0,
              Math.round(((prev[selected.kind] ?? 0) + delta) * 1000) / 1000
            ),
          }));
        }
        setDirty(true);
      } else if (e.key === "Backspace" || e.key === "Delete") {
        e.preventDefault();
        if (selected.kind === "stroke") removeMark(selected.index);
        else clearPhase(selected.kind);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    selected,
    fsHz,
    undo,
    pushUndo,
    removeMark,
    clearPhase,
    placeStrokeMark,
    playheadS,
  ]);

  const save = useCallback(async () => {
    setSaving(true);
    setErrors([]);
    setHint(null);
    try {
      const res = await apiFetch(`/sessions/${sessionId}/annotations`, {
        method: "PUT",
        body: JSON.stringify({
          phases,
          stroke_marks_s: strokeMarks,
          source: "manual",
        }),
      });
      setDirty(false);
      setHasSaved(true);
      const n = res?.cycles_derived;
      if (res?.recompute_error) {
        setSavedMsg("Saved — metrics NOT recomputed.");
        setErrors([`Recompute failed: ${res.recompute_error}`]);
      } else if (res?.recomputed) {
        // A mismatch against the panel's own readout means stroke_type is wrong on the
        // session — and stroke_type is not patchable, so it has to be caught here.
        setSavedMsg(`Saved — ${n} cycle${n === 1 ? "" : "s"} recomputed.`);
      } else {
        setSavedMsg("Saved (needs ≥2 cycle boundaries to recompute metrics).");
      }
    } catch (e) {
      const errList = e.body?.detail?.errors;
      setErrors(Array.isArray(errList) ? errList : [e.message]);
    } finally {
      setSaving(false);
    }
  }, [sessionId, phases, strokeMarks]);

  const discard = useCallback(async () => {
    setSaving(true);
    setErrors([]);
    try {
      const res = await apiFetch(`/sessions/${sessionId}/annotations`, {
        method: "DELETE",
      });
      undoRef.current = [];
      setUndoDepth(0);
      setPhases(normalizePhases(null));
      setStrokeMarks([]);
      setSelected(null);
      setHasSaved(false);
      setDirty(false);
      setSavedMsg(
        res?.metrics_restored
          ? "Annotation discarded — auto metrics restored."
          : "Annotation discarded."
      );
    } catch (e) {
      setErrors([e.message]);
    } finally {
      setSaving(false);
    }
  }, [sessionId]);

  // Fit hides the dead tail AFTER the swim. The lower bound is always 0 — never
  // stroke_start — because that leading region is the reaction-time measurement
  // (Phase 57 D4). With a blank start there is no finish_s yet, so the view opens on
  // the full trace and collapses the moment Finish is placed.
  const fitAvailable = phases.finish_s != null;
  const viewRange = useMemo(() => {
    if (viewMode !== "fit" || !fitAvailable) return null;
    const hi = phases.finish_s + Math.max(1, 0.05 * phases.finish_s);
    return [0, hi];
  }, [viewMode, fitAvailable, phases.finish_s]);

  if (loadError)
    return <p className="mt-10 text-center text-danger">{loadError}</p>;
  if (!row || !ann) return <p className="text-muted">Loading…</p>;

  // max-w-7xl, not 5xl: the chart column goes ~700px → ~980px, and AnnotationChart
  // re-spreads its MAX_POINTS budget across it. Horizontal pixels are the precision
  // budget when placing ~40 marks on a freestyle 25.
  // (Comment lives ABOVE the return: a // comment between `return (` and the JSX makes
  // SWC report a parse error at the closing brace, ~90 lines away.)
  return (
    <div className="mx-auto max-w-7xl">
      <div className="flex items-center justify-between">
        <Link
          href={`/app/sessions/${sessionId}`}
          className="text-sm text-primary"
        >
          ‹ Report card
        </Link>
        <p className="text-xs text-muted">
          {new Date(row.created_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </p>
      </div>
      <h1 className="mt-2 font-semibold text-ink">
        Annotate{row.name ? ` — ${row.name}` : ""}
      </h1>
      <p className="mt-1 text-xs leading-relaxed text-muted">
        Mark the swim phases and each stroke. Nothing is pre-placed — the marks you
        make are the ground truth the segmenter gets measured against.
      </p>

      {/* Sidebar width scales with the viewport (clamped) instead of a fixed 300px, so a
          wide screen gives the trace the extra pixels rather than the control panel. */}
      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_clamp(260px,20vw,360px)]">
        <div className="min-w-0 space-y-3">
          <VideoPane
            sessionId={sessionId}
            video={video}
            onPlayhead={setPlayheadS}
            seekRef={seekRef}
            frameStepRef={frameStepRef}
            onVideoChange={setVideo}
            // 58-04: without this the pane cannot compute an end-anchored origin, and a
            // phone-uploaded video (no stored origin) opens here silently unsynced — which is
            // exactly the case this page exists to serve.
            sessionDurationS={time.length ? time[time.length - 1] : null}
            pushoffSessionS={pushoffSessionS}
          />
          <AnnotationChart
            time={time}
            velocity={vel}
            phases={phases}
            strokeMarks={strokeMarks}
            playheadS={playheadS}
            strokeType={row.stroke_type}
            onChartClick={handleChartClick}
            onMarkDrag={handleMarkDrag}
            onMarkSelect={setSelected}
            selected={selected}
            viewRange={viewRange}
          />
        </div>
        {/* The tools panel is taller than the trace on most screens. Sticking it and
            giving it its own scroll keeps Save/Undo reachable without scrolling the
            chart out of view — the whole point of fitting both on one screen. */}
        <div className="lg:sticky lg:top-4 lg:max-h-[calc(100dvh-2rem)] lg:overflow-y-auto lg:pr-1">
        <AnnotationEditor
          strokeType={row.stroke_type}
          activeTool={activeTool}
          setActiveTool={setActiveTool}
          phases={phases}
          strokeMarks={strokeMarks}
          marksPerCycle={ann.marks_per_cycle ?? 1}
          fsHz={fsHz}
          onClearPhase={clearPhase}
          onRemoveMark={removeMark}
          onClearAllMarks={clearAllMarks}
          onUndo={undo}
          canUndo={undoDepth > 0}
          onDiscard={discard}
          hasSaved={hasSaved}
          dirty={dirty}
          saving={saving}
          errors={errors}
          savedMsg={savedMsg}
          hint={hint}
          viewMode={viewMode}
          setViewMode={setViewMode}
          fitAvailable={fitAvailable}
          onSave={save}
          seekEnabled={!!video?.path}
        />
        </div>
      </div>
    </div>
  );
}
