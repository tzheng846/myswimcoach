"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import MetricGrid, { SessionSummaryCard } from "@/components/portal/MetricGrid";
import VelocityChart from "@/components/portal/VelocityChart";
import AccelerationChart from "@/components/portal/AccelerationChart";
import useTracePrefs from "@/lib/useTracePrefs";
import TimeToX from "@/components/portal/TimeToX";
import CycleCharts from "@/components/portal/CycleCharts";
import CoachChat from "@/components/portal/CoachChat";
import PillarCards from "@/components/portal/PillarCards";
import { STROKE_LABELS } from "@/components/portal/SessionCard";
import { dropoutWarning } from "@/lib/dropoutWarning";
import { displayName } from "@/lib/sessionName";

// One chronological neighbour. Rendered as a disabled span at the ends rather than omitted, so
// the header keeps the same shape on the first and last session of an athlete.
function SiblingLink({ id, label, title }) {
  const base = "rounded-md px-2 py-1 text-lg leading-none";
  if (!id) {
    return (
      <span className={`${base} text-muted/30`} aria-hidden="true">
        {label}
      </span>
    );
  }
  return (
    <Link
      href={`/app/sessions/${id}`}
      title={title}
      aria-label={title}
      className={`${base} text-primary hover:bg-surface-2`}
    >
      {label}
    </Link>
  );
}

export default function ReportCardPage({ params }) {
  const { id: sessionId } = use(params);

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [athlete, setAthlete] = useState(null);
  // The athlete's other sessions, newest first — drives prev/next (D12).
  const [siblings, setSiblings] = useState([]);

  const [sessionName, setSessionName] = useState("");
  const [editingName, setEditingName] = useState(false);
  const [isStarred, setIsStarred] = useState(false);
  const [notes, setNotes] = useState("");
  const [unit, setUnit] = useState("metric");
  const [view, setView] = useState("simple");
  const [markerTimeS, setMarkerTimeS] = useState(null);
  const [markerLabel, setMarkerLabel] = useState("");
  const [videoCount, setVideoCount] = useState(null); // Phase 69 rework: report-card "Videos (N)" cue

  // Velocity/acceleration trace display prefs (Phase 64-03), shared with the /video route and
  // persisted. Owned here so the video overlay's toggles and the static charts below stay in sync.
  const tracePrefs = useTracePrefs();

  // 61-03: these used to reset on every prev/next hop. The route remounts per session id, so
  // component state cannot survive it — the coach had to re-pick Advanced and yards on each
  // session while comparing a series, which is exactly when they are comparing them.
  // Persisted rather than URL-encoded because they are a standing preference, not a property of
  // the session being viewed. Read in an effect, not a lazy initializer: localStorage does not
  // exist during SSR and reading it during render would desync hydration.
  useEffect(() => {
    try {
      const v = window.localStorage.getItem("swimnetics.view");
      const u = window.localStorage.getItem("swimnetics.unit");
      if (v === "simple" || v === "advanced") setView(v);
      if (u === "metric" || u === "imperial") setUnit(u);
    } catch {
      // Private mode / storage disabled — defaults are fine.
    }
  }, []);

  const persist = useCallback((key, value) => {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // Non-fatal: the toggle still works for this page view.
    }
  }, []);

  const chooseView = useCallback(
    (v) => {
      setView(v);
      persist("swimnetics.view", v);
    },
    [persist]
  );

  const chooseUnit = useCallback(
    (u) => {
      setUnit(u);
      persist("swimnetics.unit", u);
    },
    [persist]
  );

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
          "metrics_json, velocity_profile, distance_profile, acceleration_profile, name, notes, is_starred, stroke_type, athlete_id, created_at, sample_rate_hz"
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
        // Athlete + sibling session list, fetched together so they cannot disagree about which
        // athlete this session belongs to. Both live inside `load()` deliberately: it already
        // holds the `reqRef` sequence guard, and a separate effect would reintroduce exactly the
        // out-of-order race that guard exists to prevent (61-02 D12).
        const [{ data: ath }, { data: sibs }] = await Promise.all([
          supabase
            .from("athletes")
            .select("name, head_waist_m")
            .eq("id", row.athlete_id)
            .single(),
          supabase
            .from("sessions")
            .select("id, created_at, name")
            .eq("athlete_id", row.athlete_id)
            .order("created_at", { ascending: false }),
        ]);
        if (seq !== reqRef.current) return;
        setAthlete(ath);
        setSiblings(sibs ?? []);
      } else {
        setSiblings([]);
      }
    },
    [sessionId]
  );

  useEffect(() => {
    load({ resetEditable: true });
  }, [load]);

  // Phase 69 rework: a "Videos (N)" cue on the report card so an attached video is visible.
  useEffect(() => {
    let alive = true;
    apiFetch(`/sessions/${sessionId}/videos`)
      .then((r) => {
        if (alive) setVideoCount((r.videos ?? []).length);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [sessionId]);

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
  // Phase 64-03: NULL for sessions predating the 64-02 backfill — the chart/overlay just don't draw.
  const accel = data?.acceleration_profile ?? [];
  // Sessions store their true decimated rate (~89.5 Hz, not 100) since Phase 52;
  // older rows have none, and 100 is what they were always displayed at.
  const fsHz = data?.sample_rate_hz > 0 ? data.sample_rate_hz : 100;
  const time = useMemo(
    () => Array.from({ length: vel.length }, (_, i) => i / fsHz),
    [vel.length, fsHz]
  );

  // Chronological neighbours. `siblings` is newest-first, so the NEWER session is the previous
  // array entry. Either end yields null and the control is disabled rather than hidden, so the
  // controls do not jump around between sessions.
  const { newerId, olderId } = useMemo(() => {
    const i = siblings.findIndex((s) => s.id === sessionId);
    if (i < 0) return { newerId: null, olderId: null };
    return {
      newerId: i > 0 ? siblings[i - 1].id : null,
      olderId: i < siblings.length - 1 ? siblings[i + 1].id : null,
    };
  }, [siblings, sessionId]);

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
  const accelUnit = unit === "imperial" ? "yd/s²" : "m/s²";
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
        {/* Prev/next across THIS athlete's sessions (61-02 D12). Older is to the left of the
            date, newer to the right, so the arrows read chronologically rather than as
            list-order. Disabled (not hidden) at each end so the header doesn't reflow. */}
        <div className="flex items-center gap-2">
          <SiblingLink id={olderId} label="‹" title="Older session" />
          <div className="text-center">
            <p className="font-semibold">{athlete?.name ?? ""}</p>
            <p className="text-xs text-muted">{date}</p>
          </div>
          <SiblingLink id={newerId} label="›" title="Newer session" />
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
          placeholder={displayName({ id: sessionId, created_at: data.created_at })}
          className="mt-3 w-full border-b border-accent bg-transparent pb-1 font-semibold outline-none"
        />
      ) : (
        <button
          onClick={() => setEditingName(true)}
          className="mt-3 flex w-full items-center gap-2 text-left"
        >
          {/* 61-05: an un-renamed session is NOT nameless — it carries its generated name, the
              same one the sessions list and the Compare picker show. Rendering "Add session
              name…" here while every other surface calls it "Lucid Gannet" would make one
              session look like two things. Typing replaces the generated name outright. */}
          <span
            className={
              sessionName ? "font-semibold text-ink" : "font-semibold text-subtle"
            }
          >
            {sessionName || displayName({ id: sessionId, created_at: data.created_at })}
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
                onClick={() => chooseView(v)}
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

        {/* Phase 69: video moved to the dedicated Videos page (report-card declutter). A compact
            link replaces the inline VideoTracePanel; attach/sync/watch all live on /videos now. */}
        <Link
          href={`/app/sessions/${sessionId}/videos`}
          className="flex items-center justify-between rounded-xl border border-navy/50 bg-surface px-4 py-3 hover:border-accent"
        >
          <span className="text-sm font-semibold text-ink">
            Videos{videoCount ? ` (${videoCount})` : ""}
          </span>
          <span className="text-xs text-muted">
            {videoCount
              ? "View and sync camera angles ›"
              : "Attach and sync up to 4 camera angles ›"}
          </span>
        </Link>

        {/* Velocity + acceleration charts (Phase 64-03) + unit toggle. Which traces show is
            controlled from the video panel's toggles above (page-level, so the two surfaces stay
            in sync). Acceleration stacks directly beneath velocity on the same time basis. */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">
              {tracePrefs.showVelocity ? "Velocity" : "Acceleration"}
            </p>
            <div className="flex gap-1.5">
              {["metric", "imperial"].map((u) => (
                <button
                  key={u}
                  onClick={() => chooseUnit(u)}
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
          {tracePrefs.showVelocity && (
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
          )}
          {tracePrefs.showAcceleration && (
            <div className={tracePrefs.showVelocity ? "mt-3" : ""}>
              <AccelerationChart
                time={time}
                acceleration={accel}
                unitFactor={unitFactor}
                unitLabel={accelUnit}
                markerTimeS={markerTimeS}
                markerLabel={markerLabel}
                cycles={metrics.cycles}
                fsHz={fsHz}
                color={tracePrefs.accelColor}
              />
            </div>
          )}
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
            {/* 61-02 D7: every split here is measured FROM this instant, and until now nothing
                said where it came from. The chain is dive_start_s → manual.baseline_end_idx →
                session.baseline_end_s (annotations.py → metrics.py), so an annotated session's
                start IS the coach's own mark. When it is not, the caveat doubles as the fix. */}
            {metrics.session?.baseline_end_s != null && (
              <p className="mt-3 border-t border-navy/30 pt-2.5 text-center text-[11px] leading-relaxed text-muted">
                Start: {metrics.session.baseline_end_s.toFixed(2)} s —{" "}
                {metrics.data_quality?.recomputed_from_annotation ? (
                  "from your annotation"
                ) : (
                  <>
                    auto-detected.{" "}
                    <Link
                      href={`/app/annotate/${sessionId}`}
                      className="font-semibold text-primary"
                    >
                      Set it yourself ›
                    </Link>
                  </>
                )}
              </p>
            )}
          </div>
        )}

        {/* The Data Quality card was retired here (61-02 D4). Dropout is the one stat on it that
            never touched the segmenter — see lib/dropoutWarning.js for why the other three went,
            and why this must never be gated on `warnings.length`. */}
        {dropoutWarning(metrics.data_quality) && (
          <p className="rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-xs leading-relaxed text-warning-2">
            ⚠ {dropoutWarning(metrics.data_quality)}
          </p>
        )}

        {/* Advanced: per-cycle breakdown (Streamlit-demo depth) */}
        {isAnalyticsReady && view === "advanced" && (
          <>
            <p className="pt-2 text-[11px] font-semibold uppercase tracking-widest text-muted">
              Per-Cycle Breakdown
            </p>
            <CycleCharts
              cycles={metrics.cycles}
              session={metrics.session}
              unit={unit}
            />
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
