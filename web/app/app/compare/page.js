"use client";

import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import CompareChart, { COLOR_A, COLOR_B } from "@/components/portal/CompareChart";
import VideoPane from "@/components/portal/VideoPane";
import CompareCycleCharts from "@/components/portal/CompareCycleCharts";
import { sessionLabel, sessionDate } from "@/lib/sessionName";

function SessionPicker({ side, athletes, value, onChange }) {
  const [athleteId, setAthleteId] = useState("");
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    if (!athleteId) {
      setSessions([]);
      return;
    }
    supabase
      .from("sessions")
      .select("id, created_at, name, athlete_id, stroke_type")
      .eq("athlete_id", athleteId)
      .order("created_at", { ascending: false })
      .then(({ data }) => setSessions(data ?? []));
  }, [athleteId]);

  return (
    <div className="flex-1 rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Session {side}
      </p>
      <select
        value={athleteId}
        onChange={(e) => {
          setAthleteId(e.target.value);
          onChange(null);
        }}
        className="w-full rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
      >
        <option value="">Select athlete…</option>
        {athletes.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={!athleteId}
        className="mt-2 w-full rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary disabled:opacity-50"
      >
        <option value="">Select session…</option>
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {sessionLabel(s, { withStroke: true })}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function ComparePage() {
  const [athletes, setAthletes] = useState([]);
  const [idA, setIdA] = useState(null);
  const [idB, setIdB] = useState(null);
  const [rowA, setRowA] = useState(null);
  const [rowB, setRowB] = useState(null);
  const [videoA, setVideoA] = useState(null); // {path, origin_s} | null
  const [videoB, setVideoB] = useState(null);

  useEffect(() => {
    supabase
      .from("athletes")
      .select("id, name")
      .order("name")
      .then(({ data }) => setAthletes(data ?? []));
  }, []);

  useEffect(() => {
    if (!idA) {
      setRowA(null);
      return;
    }
    supabase
      .from("sessions")
      .select(
        "id, created_at, name, stroke_type, velocity_profile, sample_rate_hz, video_path, video_origin_s, session:metrics_json->session, cycles:metrics_json->cycles"
      )
      .eq("id", idA)
      .single()
      .then(({ data }) => {
        setRowA(data);
        // ⚠ origin_s passes through as NULL, never 0. 61-03 found this exact `?? 0` defect at two
        // sites inside VideoPane; a third here would silently un-sync every phone-uploaded video
        // on this page, because the pane could no longer tell "never stored" from "stored as 0".
        setVideoA(
          data?.video_path
            ? { path: data.video_path, origin_s: data.video_origin_s ?? null }
            : null
        );
      });
  }, [idA]);

  useEffect(() => {
    if (!idB) {
      setRowB(null);
      return;
    }
    supabase
      .from("sessions")
      .select(
        "id, created_at, name, stroke_type, velocity_profile, sample_rate_hz, video_path, video_origin_s, session:metrics_json->session, cycles:metrics_json->cycles"
      )
      .eq("id", idB)
      .single()
      .then(({ data }) => {
        setRowB(data);
        setVideoB(
          data?.video_path
            ? { path: data.video_path, origin_s: data.video_origin_s ?? null }
            : null
        );
      });
  }, [idB]);

  // Alignment nudge (D9). Shifts B relative to A so the coach can line the two swims up by eye.
  // ⚠ IN-MEMORY ONLY — never persisted, matching the mobile start-marker precedent. It is a
  // viewing aid, not a property of either session.
  const [offsetS, setOffsetS] = useState(0);

  // Video is OFF by default and remembered (61-05 checkpoint: "make the video togglable instead
  // of permanently there"). Two panes are a lot of vertical weight to impose on a coach who came
  // here to compare traces; they are now opt-in per browser.
  const [showVideo, setShowVideo] = useState(false);
  useEffect(() => {
    try {
      if (window.localStorage.getItem("swimnetics.compareVideo") === "1") setShowVideo(true);
    } catch {
      // storage unavailable — default off is fine
    }
  }, []);
  const toggleVideo = useCallback(() => {
    setShowVideo((v) => {
      try {
        window.localStorage.setItem("swimnetics.compareVideo", v ? "0" : "1");
      } catch {
        // non-fatal
      }
      return !v;
    });
  }, []);

  const ready = rowA && rowB;
  // Baseline = older session (app.py convention: delta = % change from baseline)
  let baseRow = rowA;
  let newRow = rowB;
  if (ready && new Date(rowA.created_at) > new Date(rowB.created_at)) {
    baseRow = rowB;
    newRow = rowA;
  }
  // The panels are ordered by DATE, but the video state is keyed to the fetch slot — follow the
  // swap so a video is never shown against the other session's trace.
  const baseIsA = baseRow === rowA;
  const baseVideo = baseIsA ? videoA : videoB;
  const newVideo = baseIsA ? videoB : videoA;
  const setBaseVideo = baseIsA ? setVideoA : setVideoB;
  const setNewVideo = baseIsA ? setVideoB : setVideoA;

  // Each session's own trace duration, on its own recorded rate — VideoPane needs it to compute
  // the end-anchored origin (58-04). ⚠ Omitting it is a SILENT no-op: the pane simply falls back
  // to the stored origin, which for these sessions is exactly what is missing.
  const durationOf = (row) => {
    const n = row?.velocity_profile?.length ?? 0;
    if (!n) return null;
    const fs = row.sample_rate_hz > 0 ? row.sample_rate_hz : 100;
    return (n - 1) / fs;
  };

  return (
    <div>
      <h1 className="text-2xl font-bold">Compare</h1>
      <p className="mt-1 text-sm text-muted">
        Pick two sessions — each trace is drawn on its own recorded sample rate, and deltas are
        % change from the older (baseline) session.
      </p>

      <div className="mt-5 flex flex-col gap-4 sm:flex-row">
        <SessionPicker side="A" athletes={athletes} value={idA} onChange={setIdA} />
        <SessionPicker side="B" athletes={athletes} value={idB} onChange={setIdB} />
      </div>

      {ready ? (
        <div className="mt-5 space-y-4">
          {/* 61-05 D10: traces left, videos right, same order. Pairing is carried THREE ways at
              once — colour, label and vertical order — because any single one is ambiguous once
              two swims look alike.
              ⚠ ACCEPTED COST: the right column takes horizontal pixels from the traces, and
              horizontal resolution is what makes two velocity curves comparable. If they read
              worse, the remedy is videos above/below rather than beside. */}
          {/* The right column only exists when video is on. With it off the traces get the whole
              width back — which is the point, since horizontal resolution is what makes two
              velocity curves comparable. */}
          <div
            className={
              showVideo
                ? "grid gap-4 lg:grid-cols-[minmax(0,1fr)_clamp(280px,26vw,380px)]"
                : ""
            }
          >
            <div className="min-w-0 space-y-3">
          <CompareChart
            velA={baseRow.velocity_profile}
            velB={newRow.velocity_profile}
            // Never hardcode 100 — read each session's own recorded rate, falling back only when
            // it is NULL (pre-Phase-52 rows), exactly as sessions/[id]/page.js does.
            fsA={baseRow.sample_rate_hz > 0 ? baseRow.sample_rate_hz : 100}
            fsB={newRow.sample_rate_hz > 0 ? newRow.sample_rate_hz : 100}
            labelA={`${sessionLabel(baseRow, { withStroke: true })} (baseline)`}
            labelB={sessionLabel(newRow, { withStroke: true })}
            offsetS={offsetS}
          />

          <div className="flex flex-wrap items-center justify-center gap-2 rounded-xl border border-navy/50 bg-surface px-3 py-2 text-xs">
            <span className="text-muted">Align second trace</span>
            {[-1, -0.1].map((d) => (
              <button
                key={d}
                onClick={() => setOffsetS((o) => Math.round((o + d) * 100) / 100)}
                className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
              >
                {d}s
              </button>
            ))}
            <span className="w-16 text-center font-mono text-ink">
              {offsetS >= 0 ? "+" : ""}
              {offsetS.toFixed(2)} s
            </span>
            {[0.1, 1].map((d) => (
              <button
                key={d}
                onClick={() => setOffsetS((o) => Math.round((o + d) * 100) / 100)}
                className="rounded-md border border-surface-3 bg-surface-2 px-2 py-1 font-semibold text-subtle hover:text-ink"
              >
                +{d}s
              </button>
            ))}
            <button
              onClick={() => setOffsetS(0)}
              disabled={offsetS === 0}
              className={`rounded-md px-2.5 py-1 font-semibold ${
                offsetS !== 0 ? "bg-accent text-white" : "bg-surface-2 text-muted"
              }`}
            >
              Reset
            </button>
            <span className="text-muted">not saved</span>
            <button
              onClick={toggleVideo}
              className={`ml-auto rounded-md border px-2.5 py-1 font-semibold ${
                showVideo
                  ? "border-accent bg-accent text-white"
                  : "border-surface-3 bg-surface-2 text-subtle hover:text-ink"
              }`}
            >
              {showVideo ? "Hide video" : "▶ Show video"}
            </button>
          </div>
            </div>

            {/* Sticky so the two panes track the traces instead of trailing far below them —
                the column is taller than the chart column and used to hang off the bottom. */}
            <div className="space-y-3 lg:sticky lg:top-4 lg:self-start">
              {showVideo &&
                [
                { row: baseRow, video: baseVideo, setVideo: setBaseVideo, color: COLOR_A },
                { row: newRow, video: newVideo, setVideo: setNewVideo, color: COLOR_B },
              ].map(({ row, video, setVideo, color }) => (
                <div
                  key={row.id}
                  className="rounded-xl border-l-2 pl-2"
                  style={{ borderLeftColor: color }}
                >
                  <p
                    className="mb-1 truncate px-1 text-[11px] font-semibold"
                    style={{ color }}
                    title={sessionLabel(row, { withStroke: true })}
                  >
                    {sessionLabel(row, { withStroke: true })}
                  </p>
                  <VideoPane
                    sessionId={row.id}
                    video={video}
                    onVideoChange={setVideo}
                    sessionDurationS={durationOf(row)}
                  />
                </div>
              ))}
            </div>
          </div>

          <CompareCycleCharts
            cyclesA={baseRow.cycles}
            cyclesB={newRow.cycles}
            sessionA={baseRow.session}
            sessionB={newRow.session}
            labelA={sessionLabel(baseRow, { withStroke: true })}
            labelB={sessionLabel(newRow, { withStroke: true })}
          />
        </div>
      ) : (
        <p className="mt-10 text-center text-sm text-muted">
          Select two sessions to compare.
        </p>
      )}
    </div>
  );
}
