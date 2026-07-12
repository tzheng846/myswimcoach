"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import AnnotationChart, { PHASE_META } from "@/components/portal/AnnotationChart";
import AnnotationEditor from "@/components/portal/AnnotationEditor";
import VideoPane from "@/components/portal/VideoPane";

const PHASE_KEYS = PHASE_META.map((m) => m.key);

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
  const [activeTool, setActiveTool] = useState("stroke_start_s");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState([]);
  const [savedMsg, setSavedMsg] = useState(null);

  // Video sync
  const [video, setVideo] = useState(null); // {path, origin_s} | null
  const [playheadS, setPlayheadS] = useState(null);
  const seekRef = useRef(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [{ data: sRow, error: sErr }, annRes] = await Promise.all([
        supabase
          .from("sessions")
          .select("velocity_profile, stroke_type, name, athlete_id, created_at")
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
      const src = annRes.annotation ?? annRes.seed;
      setPhases(normalizePhases(src?.phases));
      setStrokeMarks([...(src?.stroke_marks_s ?? [])].sort((a, b) => a - b));
      setDirty(false);
      setSavedMsg(annRes.annotation ? "Loaded saved annotation" : "Auto-seeded draft");
    })();
    return () => {
      alive = false;
    };
  }, [sessionId]);

  const handleChartClick = useCallback(
    (t) => {
      const tt = Math.round(t * 100) / 100;
      if (activeTool === "seek") {
        seekRef.current?.(tt);
        return;
      }
      if (activeTool === "stroke") {
        setStrokeMarks((prev) => [...prev, tt].sort((a, b) => a - b));
        setDirty(true);
        return;
      }
      // Phase tool: place / move that boundary
      setPhases((prev) => ({ ...prev, [activeTool]: tt }));
      setDirty(true);
    },
    [activeTool]
  );

  const clearPhase = useCallback((key) => {
    setPhases((prev) => ({ ...prev, [key]: null }));
    setDirty(true);
  }, []);

  const removeMark = useCallback((i) => {
    setStrokeMarks((prev) => prev.filter((_, idx) => idx !== i));
    setDirty(true);
  }, []);

  const clearAllMarks = useCallback(() => {
    setStrokeMarks([]);
    setDirty(true);
  }, []);

  const resetToSeed = useCallback(() => {
    if (!ann?.seed) return;
    setPhases(normalizePhases(ann.seed.phases));
    setStrokeMarks([...(ann.seed.stroke_marks_s ?? [])].sort((a, b) => a - b));
    setErrors([]);
    setDirty(true);
    setSavedMsg(null);
  }, [ann]);

  const save = useCallback(async () => {
    setSaving(true);
    setErrors([]);
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
      if (res?.recompute_error) {
        setSavedMsg("Saved — metrics NOT recomputed.");
        setErrors([`Recompute failed: ${res.recompute_error}`]);
      } else if (res?.recomputed) {
        setSavedMsg("Saved — metrics recomputed.");
      } else {
        setSavedMsg("Saved (add ≥2 stroke boundaries to recompute metrics).");
      }
    } catch (e) {
      const errList = e.body?.detail?.errors;
      setErrors(Array.isArray(errList) ? errList : [e.message]);
    } finally {
      setSaving(false);
    }
  }, [sessionId, phases, strokeMarks]);

  const vel = row?.velocity_profile ?? [];
  const time = useMemo(
    () => Array.from({ length: vel.length }, (_, i) => i / 100),
    [vel.length]
  );

  if (loadError)
    return <p className="mt-10 text-center text-danger">{loadError}</p>;
  if (!row || !ann) return <p className="text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-5xl">
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
        Mark the swim phases and each stroke. Marks are pre-seeded from the
        auto-segmenter — click with a tool to place or move them.
      </p>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_300px]">
        <div className="min-w-0 space-y-3">
          <VideoPane
            sessionId={sessionId}
            video={video}
            onPlayhead={setPlayheadS}
            seekRef={seekRef}
            onVideoChange={setVideo}
          />
          <AnnotationChart
            time={time}
            velocity={vel}
            phases={phases}
            strokeMarks={strokeMarks}
            playheadS={playheadS}
            strokeType={row.stroke_type}
            onChartClick={handleChartClick}
          />
        </div>
        <AnnotationEditor
          strokeType={row.stroke_type}
          activeTool={activeTool}
          setActiveTool={setActiveTool}
          phases={phases}
          strokeMarks={strokeMarks}
          onClearPhase={clearPhase}
          onRemoveMark={removeMark}
          onClearAllMarks={clearAllMarks}
          dirty={dirty}
          saving={saving}
          errors={errors}
          savedMsg={savedMsg}
          onSave={save}
          onReset={resetToSeed}
          seekEnabled={!!video?.path}
        />
      </div>
    </div>
  );
}
