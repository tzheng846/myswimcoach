"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import MetricGrid, { SessionSummaryCard } from "@/components/portal/MetricGrid";
import DataQualityCard from "@/components/portal/DataQualityCard";
import VelocityChart from "@/components/portal/VelocityChart";
import TimeToX from "@/components/portal/TimeToX";
import CycleTable from "@/components/portal/CycleTable";
import CycleCharts from "@/components/portal/CycleCharts";
import CoachChat from "@/components/portal/CoachChat";
import PillarCards from "@/components/portal/PillarCards";
import { STROKE_LABELS } from "@/components/portal/SessionCard";

export default function ReportCardPage({ params }) {
  const { id: sessionId } = use(params);

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [athlete, setAthlete] = useState(null);

  const [sessionName, setSessionName] = useState("");
  const [editingName, setEditingName] = useState(false);
  const [isStarred, setIsStarred] = useState(false);
  const [notes, setNotes] = useState("");
  const [unit, setUnit] = useState("metric");
  const [view, setView] = useState("simple");
  const [markerTimeS, setMarkerTimeS] = useState(null);
  const [markerLabel, setMarkerLabel] = useState("");

  // Sequence guard: load() can now be triggered from three places, so a slow earlier
  // response must not overwrite a newer one.
  const reqRef = useRef(0);

  // resetEditable is only true on the initial load. A revalidation must NOT reassign
  // sessionName / notes / isStarred: those are user-owned local state that PATCHes on
  // blur, and clobbering them would silently discard notes typed before an alt-tab.
  const load = useCallback(
    async ({ resetEditable = false } = {}) => {
      const seq = ++reqRef.current;
      const { data: row, error: err } = await supabase
        .from("sessions")
        .select(
          "metrics_json, velocity_profile, distance_profile, name, notes, is_starred, stroke_type, athlete_id, created_at, sample_rate_hz"
        )
        .eq("id", sessionId)
        .single();
      if (seq !== reqRef.current) return; // superseded by a newer load
      if (err) {
        setError("Failed to load session.");
        return;
      }
      setData(row);
      if (resetEditable) {
        setSessionName(row.name ?? "");
        setIsStarred(row.is_starred ?? false);
        setNotes(row.notes ?? "");
      }
      if (row.athlete_id) {
        const { data: ath } = await supabase
          .from("athletes")
          .select("name, head_waist_m")
          .eq("id", row.athlete_id)
          .single();
        if (seq !== reqRef.current) return;
        setAthlete(ath);
      }
    },
    [sessionId]
  );

  useEffect(() => {
    load({ resetEditable: true });
  }, [load]);

  // Revalidate on return, because mounting is the one moment a bfcache restore skips:
  // the browser brings the whole JS heap back, so React never re-runs and `data` keeps
  // whatever it was holding — including auto metrics for a session annotated since.
  // router.refresh() cannot reach this; nothing React-side fires at all on a restore.
  // `focus` covers the ordinary alt-tab case, matching the useFocusEffect convention the
  // mobile tab screens settled on in Phase 55.
  useEffect(() => {
    const onPageShow = (e) => {
      if (e.persisted) load();
    };
    const onFocus = () => load();
    window.addEventListener("pageshow", onPageShow);
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("pageshow", onPageShow);
      window.removeEventListener("focus", onFocus);
    };
  }, [load]);

  const patchSession = useCallback(
    async (updates) => {
      try {
        await apiFetch(`/sessions/${sessionId}`, {
          method: "PATCH",
          body: JSON.stringify(updates),
        });
      } catch {
        // optimistic update already applied — non-fatal
      }
    },
    [sessionId]
  );

  const onMarkerChange = useCallback((tS, lbl) => {
    setMarkerTimeS(tS);
    setMarkerLabel(lbl);
  }, []);

  const vel = data?.velocity_profile ?? [];
  const dist = data?.distance_profile ?? [];
  // Sessions store their true decimated rate (~89.5 Hz, not 100) since Phase 52;
  // older rows have none, and 100 is what they were always displayed at.
  const fsHz = data?.sample_rate_hz > 0 ? data.sample_rate_hz : 100;
  const time = useMemo(
    () => Array.from({ length: vel.length }, (_, i) => i / fsHz),
    [vel.length, fsHz]
  );

  if (error)
    return (
      <p className="mt-10 text-center text-danger">{error}</p>
    );
  if (!data) return <p className="text-muted">Loading…</p>;

  const metrics = data.metrics_json ?? {};
  const strokeType = data.stroke_type;
  // Phase 58-03: every stroke gets full analytics on the web. This was
  //     const isAnalyticsReady = !strokeType || strokeType === "breaststroke";
  // — the web twin of the mobile gate 54-01 removed. Phase 54's audit recorded that the web had
  // no stroke gate, so this copy was missed and the web stayed breaststroke-only for two days
  // after the iOS unlock shipped. Restore by putting that line back; every usage site and the
  // "coming soon" branch below are deliberately kept so it stays a one-line change.
  //
  // ⚠ The bands shown for non-breaststroke are BREASTSTROKE-DERIVED and unvalidated (ratings.py
  // falls back to that table for every stroke). `provisional` is False for all four strokes, so
  // PillarCards' "Provisional" banner does NOT fire — nothing on screen says the bands are
  // borrowed. Whether that caveat should exist is Phase 53's question, not this plan's.
  const isAnalyticsReady = true;
  const unitFactor = unit === "imperial" ? 1.09361 : 1;
  const velUnit = unit === "imperial" ? "yd/s" : "m/s";
  const date = new Date(data.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between">
        <Link
          href={
            data.athlete_id
              ? `/app/sessions?athlete=${data.athlete_id}`
              : "/app/sessions"
          }
          className="text-sm text-primary"
        >
          ‹ Sessions
        </Link>
        <div className="text-center">
          <p className="font-semibold">{athlete?.name ?? ""}</p>
          <p className="text-xs text-muted">{date}</p>
        </div>
        <button
          onClick={() => {
            const next = !isStarred;
            setIsStarred(next);
            patchSession({ is_starred: next });
          }}
          className={`px-2 text-2xl ${isStarred ? "text-warning" : "text-muted"}`}
          title={isStarred ? "Unstar" : "Star"}
        >
          {isStarred ? "★" : "☆"}
        </button>
      </div>

      {/* Editable session name */}
      {editingName ? (
        <input
          value={sessionName}
          onChange={(e) => setSessionName(e.target.value)}
          onBlur={() => {
            setEditingName(false);
            patchSession({ name: sessionName.trim() || null });
          }}
          onKeyDown={(e) => e.key === "Enter" && e.target.blur()}
          autoFocus
          placeholder="Session name…"
          className="mt-3 w-full border-b border-accent bg-transparent pb-1 font-semibold outline-none"
        />
      ) : (
        <button
          onClick={() => setEditingName(true)}
          className="mt-3 flex w-full items-center gap-2 text-left"
        >
          <span
            className={
              sessionName ? "font-semibold text-ink" : "italic text-muted"
            }
          >
            {sessionName || "Add session name…"}
          </span>
          <span className="text-xs text-muted">✎</span>
        </button>
      )}

      {/* Simple / Advanced view toggle + annotation entry */}
      <div className="mt-3 flex items-center justify-between">
        {isAnalyticsReady ? (
          <div className="inline-flex rounded-lg border border-surface-3 bg-surface-2 p-0.5">
            {["simple", "advanced"].map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-md px-3.5 py-1.5 text-xs font-semibold capitalize transition-colors ${
                  view === v ? "bg-accent text-white" : "text-subtle hover:text-ink"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        ) : (
          <span />
        )}
        <Link
          href={`/app/annotate/${sessionId}`}
          className="text-xs font-semibold text-primary"
        >
          Annotate ›
        </Link>
      </div>

      <div className="mt-4 space-y-3">
        <SessionSummaryCard session={metrics.session} unit={unit} />

        {/* Provenance. api.py:899 has always set this flag on a successful recompute and
            nothing has ever rendered it — so a coach could not tell "my annotation had no
            effect" from "it worked and the numbers barely moved". */}
        {metrics.data_quality?.recomputed_from_annotation && (
          <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 rounded-xl border border-accent/40 bg-accent/10 px-3 py-2 text-xs leading-relaxed text-subtle">
            <span aria-hidden="true">✎</span>
            These metrics were recomputed from a hand annotation — not auto-segmentation.
            <Link
              href={`/app/annotate/${sessionId}`}
              className="font-semibold text-primary"
            >
              Review marks ›
            </Link>
          </p>
        )}

        {isAnalyticsReady ? (
          view === "advanced" ? (
            <MetricGrid metrics={metrics} unit={unit} />
          ) : (
            <PillarCards sessionId={sessionId} />
          )
        ) : (
          <div className="rounded-xl border border-navy/50 bg-surface p-6 text-center">
            <p className="font-bold">
              {STROKE_LABELS[strokeType] ?? strokeType} Analytics
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Detailed stroke metrics coming soon. Velocity data is still
              recorded and shown below.
            </p>
          </div>
        )}

        {/* Velocity chart + unit toggle */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">
              Velocity
            </p>
            <div className="flex gap-1.5">
              {["metric", "imperial"].map((u) => (
                <button
                  key={u}
                  onClick={() => setUnit(u)}
                  className={`rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
                    unit === u
                      ? "border-accent bg-accent text-white"
                      : "border-surface-3 bg-surface-2 text-subtle"
                  }`}
                >
                  {u === "metric" ? "m" : "yd"}
                </button>
              ))}
            </div>
          </div>
          <VelocityChart
            time={time}
            velocity={vel}
            unitFactor={unitFactor}
            unitLabel={velUnit}
            markerTimeS={markerTimeS}
            markerLabel={markerLabel}
            cycles={metrics.cycles}
            fsHz={fsHz}
          />
        </div>

        {isAnalyticsReady && (
          <div className="rounded-xl border border-navy/50 bg-surface p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
              Time to Distance
            </p>
            <TimeToX
              timeArr={time}
              distArr={dist}
              baselineEndS={metrics.session?.baseline_end_s}
              headWaistM={athlete?.head_waist_m ?? 0}
              onMarkerChange={onMarkerChange}
              unit={unit}
            />
          </div>
        )}

        <DataQualityCard dataQuality={metrics.data_quality} />

        {/* Advanced: per-cycle breakdown (Streamlit-demo depth) */}
        {isAnalyticsReady && view === "advanced" && (
          <>
            <p className="pt-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
              Per-Cycle Breakdown
            </p>
            <CycleCharts cycles={metrics.cycles} session={metrics.session} />
            <CycleTable cycles={metrics.cycles} />
          </>
        )}

        {/* AI Coach Chat — grounded in this session's metrics (backend rebuilds the prompt) */}
        {isAnalyticsReady && (
          <CoachChat sessionId={sessionId} simple={view === "simple"} />
        )}

        {/* Notes */}
        <div className="rounded-xl border border-navy/50 bg-surface p-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
            Notes
          </p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => patchSession({ notes: notes.trim() || null })}
            placeholder="Add coaching notes…"
            rows={4}
            className="w-full resize-y bg-transparent text-sm leading-relaxed text-ink placeholder-muted outline-none"
          />
        </div>
      </div>
    </div>
  );
}
