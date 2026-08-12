"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import VideoPane from "@/components/portal/VideoPane";
import VelocityChart from "@/components/portal/VelocityChart";

// Read-only video + velocity view (61-03 D1). Deliberately NOT the annotate page: no marks, no
// phase boundaries, no Save. The user's ask was to reach synced video "without it being hidden
// behind annotations", so this page carries playback and nothing else.

// ⚠ The 1s/2s/5s/All span presets were REMOVED at the 61-03 checkpoint (user: "redundant when
// they can manually adjust the window"). This withdraws CONTEXT D16 and, with it, the chart's
// auto-follow: the brush is now the only window control and does not track the playhead.
// Removing them also deleted the controlled-window machinery from VelocityChart, which is back
// to its pre-61-03 form plus an onClick handler.

export default function SessionVideoPage({ params }) {
  const { id: sessionId } = use(params);

  const [row, setRow] = useState(null);
  const [athlete, setAthlete] = useState(null);
  const [error, setError] = useState(null);
  const [video, setVideo] = useState(null); // {path, origin_s} | null
  const [playheadS, setPlayheadS] = useState(null);
  const seekRef = useRef(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const { data, error: err } = await supabase
        .from("sessions")
        .select(
          "velocity_profile, sample_rate_hz, name, created_at, athlete_id, video_path, video_origin_s"
        )
        .eq("id", sessionId)
        .single();
      if (!alive) return;
      if (err) {
        setError("Failed to load session.");
        return;
      }
      setRow(data);
      // ⚠ origin_s passes through as NULL when unset — VideoPane must be able to tell "never
      // stored" from "stored as 0", which is the whole of 58-04.
      setVideo(
        data.video_path
          ? { path: data.video_path, origin_s: data.video_origin_s ?? null }
          : null
      );
      if (data.athlete_id) {
        const { data: ath } = await supabase
          .from("athletes")
          .select("name")
          .eq("id", data.athlete_id)
          .single();
        if (alive) setAthlete(ath);
      }
    })();
    return () => {
      alive = false;
    };
  }, [sessionId]);

  const vel = row?.velocity_profile ?? [];
  // Same derivation as sessions/[id]/page.js:120. Never hardcode 100 — that is the defect
  // Phase 52 fixed on the web and Phase 60-01 fixed on mobile.
  const fsHz = row?.sample_rate_hz > 0 ? row.sample_rate_hz : 100;
  const time = useMemo(
    () => Array.from({ length: vel.length }, (_, i) => i / fsHz),
    [vel.length, fsHz]
  );
  const sessionDurationS = time.length ? time[time.length - 1] : null;


  // Clicking the trace seeks the video. VideoPane already exposes seekRef; the annotate page
  // drives it the same way.
  const onChartClick = useCallback((e) => {
    const t = e?.activeLabel;
    if (typeof t === "number") seekRef.current?.(t);
  }, []);

  if (error) return <p className="mt-10 text-center text-danger">{error}</p>;
  if (!row) return <p className="text-muted">Loading…</p>;

  const date = new Date(row.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex items-center justify-between">
        <Link
          href={`/app/sessions/${sessionId}`}
          className="text-sm text-primary"
        >
          ‹ Report card
        </Link>
        <div className="text-center">
          <p className="font-semibold">{athlete?.name ?? ""}</p>
          <p className="text-xs text-muted">{date}</p>
        </div>
        <Link
          href={`/app/annotate/${sessionId}`}
          className="text-xs font-semibold text-primary"
        >
          Annotate ›
        </Link>
      </div>

      <h1 className="mt-2 font-semibold text-ink">
        Video + Velocity{row.name ? ` — ${row.name}` : ""}
      </h1>

      <div className="mt-4 space-y-3">
        <VideoPane
          sessionId={sessionId}
          video={video}
          onPlayhead={setPlayheadS}
          seekRef={seekRef}
          onVideoChange={setVideo}
          sessionDurationS={sessionDurationS}
        />

        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
            Velocity
          </p>
          <VelocityChart
            time={time}
            velocity={vel}
            markerTimeS={playheadS}
            markerLabel="▶"
            fsHz={fsHz}
            onClick={onChartClick}
          />
          <p className="mt-1.5 px-1 text-[11px] text-muted">
            Click the trace to seek the video. Drag the bar below it to narrow the view.
          </p>
        </div>
      </div>
    </div>
  );
}
