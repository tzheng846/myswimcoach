"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import VelocityChart from "@/components/portal/VelocityChart";
import AccelerationChart from "@/components/portal/AccelerationChart";
import VideoTracePanel from "@/components/portal/VideoTracePanel";
import useTracePrefs from "@/lib/useTracePrefs";
import SplitPicker from "@/components/portal/SplitPicker";
import CoachChat from "@/components/portal/CoachChat";
import PhaseReportCard from "@/components/portal/phases/PhaseReportCard";
import { fetchPhaseBaseline } from "@/lib/phaseBaseline";
import { STROKE_LABELS } from "@/components/portal/SessionCard";
import { dropoutWarning } from "@/lib/dropoutWarning";
import { displayName } from "@/lib/sessionName";
import AddVideoModal from "@/components/portal/AddVideoModal";

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

// Phase 75-07: the session report card is now the race-phase view. The classic analytics body
// (SessionSummaryCard / PillarCards / MetricGrid + the Simple/Advanced toggle) was removed; the
// phase surface (PhaseReportCard) is the body, with the still-essential cards — velocity,
// Time-to-Distance, video — threaded through it via `middleSlot`. The pillars relocate to a future
// roster surface; their component files remain, just no longer rendered here.
export default function ReportCardPage({ params }) {
  const { id: sessionId } = use(params);
  const router = useRouter();

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [athlete, setAthlete] = useState(null);
  // The athlete's other sessions, newest first — drives prev/next (D12).
  const [siblings, setSiblings] = useState([]);
  // The athlete's last-5 same-stroke swims, reduced to per-metric usual-range bands (Phase 75-05).
  const [baseline, setBaseline] = useState({});

  const [sessionName, setSessionName] = useState("");
  const [editingName, setEditingName] = useState(false);
  const [isStarred, setIsStarred] = useState(false);
  const [notes, setNotes] = useState("");
  const [unit, setUnit] = useState("metric");
  // 88-04: the Segment splits picker's selected window, shaded on both traces. This replaced the
  // Time-to-Distance marker state (removed with that card at the 88-04 verify) — the charts still
  // ACCEPT markerTimeS/markerLabel, but nothing on either route passes them any more.
  const [spanS, setSpanS] = useState(null);
  const [spanLabel, setSpanLabel] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  // Phase 71: the inline watch player + the Add/Manage cues are sourced from the unified camera
  // list (GET /videos: phone primary from the legacy columns + externals from session_videos). This
  // is what makes a web-uploaded external — previously invisible here — play inline like a phone one.
  const [videos, setVideos] = useState(null); // null = not loaded yet; [] = loaded, none
  const [showAddVideo, setShowAddVideo] = useState(false);

  // Velocity/acceleration trace display prefs (Phase 64-03), shared with the /video route and
  // persisted. Owned here so the video overlay's toggles and the static charts below stay in sync.
  const tracePrefs = useTracePrefs();

  // 61-03: unit used to reset on every prev/next hop. The route remounts per session id, so
  // component state cannot survive it — the coach had to re-pick yards on each session while
  // comparing a series, which is exactly when they are comparing them. Persisted rather than
  // URL-encoded because it is a standing preference, not a property of the session being viewed.
  // Read in an effect, not a lazy initializer: localStorage does not exist during SSR and reading
  // it during render would desync hydration.
  useEffect(() => {
    try {
      const u = window.localStorage.getItem("swimnetics.unit");
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
        // Athlete + sibling session list + phase baseline, fetched together so they cannot disagree
        // about which athlete this session belongs to. All live inside `load()` deliberately: it
        // already holds the `reqRef` sequence guard, and a separate effect would reintroduce exactly
        // the out-of-order race that guard exists to prevent (61-02 D12). The baseline is the
        // athlete's prior same-stroke swims, so it hangs off this same row (mirrors phases/page.js).
        const [{ data: ath }, { data: sibs }, base] = await Promise.all([
          supabase
            .from("athletes")
            .select("name")
            .eq("id", row.athlete_id)
            .single(),
          supabase
            .from("sessions")
            .select("id, created_at, name")
            .eq("athlete_id", row.athlete_id)
            .order("created_at", { ascending: false }),
          fetchPhaseBaseline({
            athleteId: row.athlete_id,
            strokeType: row.stroke_type,
            beforeCreatedAt: row.created_at,
          }),
        ]);
        if (seq !== reqRef.current) return;
        setAthlete(ath);
        setSiblings(sibs ?? []);
        setBaseline(base ?? {});
      } else {
        setSiblings([]);
        setBaseline({});
      }
    },
    [sessionId]
  );

  useEffect(() => {
    load({ resetEditable: true });
  }, [load]);

  // Phase 71: the unified camera list drives the inline watch player + the Add/Manage cues.
  // A callback so the Add-video modal (and a phone-video origin auto-save) can refresh it.
  const loadVideos = useCallback(async () => {
    try {
      const r = await apiFetch(`/sessions/${sessionId}/videos`);
      setVideos(r.videos ?? []);
    } catch {
      setVideos((prev) => (prev == null ? [] : prev));
    }
  }, [sessionId]);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

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

  // Close the ⋯ overflow menu on any click outside its group.
  const menuRef = useRef(null);
  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menuOpen]);

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

  // Delete lives in the header ⋯ overflow (Phase 75-07) — the list page's handleDelete, plus a
  // redirect back to the athlete's session list on success.
  const handleDelete = useCallback(async () => {
    const label = sessionName ? ` "${sessionName}"` : "";
    if (!window.confirm(`Delete this session${label}? This cannot be undone.`)) return;
    try {
      await apiFetch(`/sessions/${sessionId}`, { method: "DELETE" });
      router.push(
        data?.athlete_id ? `/app/sessions?athlete=${data.athlete_id}` : "/app/sessions"
      );
    } catch {
      // Deletion failed server-side; stay on the page rather than pretend it worked.
    }
  }, [sessionId, sessionName, data, router]);

  const onSpanChange = useCallback((span, lbl) => {
    setSpanS(span);
    setSpanLabel(lbl);
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

  if (error) return <p className="mt-10 text-center text-danger">{error}</p>;
  if (!data) return <p className="text-muted">Loading…</p>;

  const metrics = data.metrics_json ?? {};
  const phases = metrics.phases ?? null;
  // Phase 71: one angle shows inline (phone if present, else the first uploaded external).
  const primaryCam =
    (videos ?? []).find((v) => v.role === "phone") ?? (videos ?? [])[0] ?? null;
  const strokeType = data.stroke_type;
  const strokeLabel = STROKE_LABELS[strokeType] ?? strokeType;
  const durationS = time.length ? time[time.length - 1] : null;
  const unitFactor = unit === "imperial" ? 1.09361 : 1;
  const velUnit = unit === "imperial" ? "yd/s" : "m/s";
  const accelUnit = unit === "imperial" ? "yd/s²" : "m/s²";
  const date = new Date(data.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  // 88-02 D6/D7: dive_start_s (raw) is now the single anchor for every distance-origin number on
  // this page — Time-to-Distance, the Swimming section's splits, and 88-04's picker. Collapses
  // what used to be three separate "0 m" instants (CONTEXT F5: up to 12.4 s apart on 27 of 99
  // stored sessions). Falls back to the old baseline_end_s, and "none", only when dive_start_s
  // itself never resolved (D9) — all 99 stored sessions currently have one, so this is
  // theoretical today, not a live path.
  const anchorS = phases?.boundaries?.dive_start_s ?? metrics.session?.baseline_end_s ?? null;
  const anchorSource = phases?.boundaries?.sources?.dive_start_s ?? "none";

  // Velocity / Time-to-Distance / video — the still-essential non-phase cards, threaded between the
  // phase timeline and the phase strip sections (mockup order). Kept as the interim classic charts
  // (VelocityChart + AccelerationChart); the unified phase-tinted interactive trace is Phase 75-09.
  const middleSlot = (
    <>
      {/* Velocity + acceleration (Phase 64-03) + unit toggle. Which traces show is controlled from
          the video panel's toggles below (page-level, so the two surfaces stay in sync). */}
      <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
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
        {/* 88-05: the trend window. Sits inside the showVelocity branch so it disappears with the
            chart it controls rather than hanging orphaned above the acceleration trace. It is a
            y-domain control, not a second x-windowing slider — the boundary AccelerationChart.js:21-24
            records is respected, not bent (D5). */}
        {tracePrefs.showVelocity && (
          <div className="mb-2 flex items-center gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-muted">
              Trend window
            </span>
            <input
              type="range"
              min="0"
              max="3"
              step="0.05"
              value={tracePrefs.smoothWindowS}
              onChange={(e) =>
                tracePrefs.setSmoothWindowS(Number.parseFloat(e.target.value))
              }
              className="h-1 flex-1 cursor-pointer accent-accent"
              aria-label="Velocity trend averaging window in seconds"
            />
            <span className="w-12 text-right font-mono text-[11px] text-subtle">
              {tracePrefs.smoothWindowS > 0
                ? `${tracePrefs.smoothWindowS.toFixed(2)} s`
                : "off"}
            </span>
          </div>
        )}
        {tracePrefs.showVelocity && (
          <VelocityChart
            time={time}
            velocity={vel}
            unitFactor={unitFactor}
            unitLabel={velUnit}
            spanS={spanS}
            spanLabel={spanLabel}
            smoothWindowS={tracePrefs.smoothWindowS}
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
              spanS={spanS}
              spanLabel={spanLabel}
              cycles={metrics.cycles}
              fsHz={fsHz}
              color={tracePrefs.accelColor}
            />
          </div>
        )}
      </section>

      {/* Segment splits (Phase 88-04). Time-to-Distance stood here until the 88-04 verify, when the
          user removed it as redundant: an arbitrary contiguous window subsumes five fixed targets.
          This card inherits its slot, its chrome AND its anchor caveat below. */}
      <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
          Segment splits
        </p>
        <SplitPicker
          timeArr={time}
          distArr={dist}
          anchorS={anchorS}
          finishS={phases?.boundaries?.finish_s ?? durationS}
          fsHz={fsHz}
          unit={unit}
          onSpanChange={onSpanChange}
        />
        {/* 61-02 D7, extended by 88-02 D6/D7: every distance-anchored number on this page is now
            measured from this one instant, and this line is its single statement — for the splits
            and 88-04's picker as well as for this card. anchorSource reads
            boundaries.sources.dive_start_s (phase_metrics.resolve_boundaries' per-BOUNDARY
            provenance), not data_quality.recomputed_from_annotation, which says the SESSION was
            recomputed, not that dive_start_s itself came from a mark (D8) — a boundary can be
            "detected" on an otherwise-annotated session.
            ⚠ It stays HERE, in page.js, rather than moving inside SplitPicker: page.js owns the
            anchor, and scratch/anchor_check.mjs check 5 is a source-text assertion against this
            file. Pushing the provenance wording into the card would put a second copy of the
            anchor-source rule in the one place nobody looks — the defect 88-02 removed. */}
        {anchorS != null && (
          <p className="mt-3 border-t border-navy/30 pt-2.5 text-center text-[11px] leading-relaxed text-muted">
            Start: {anchorS.toFixed(2)} s —{" "}
            {anchorSource === "none" ? (
              "no dive detected on this session — measured from the older start estimate."
            ) : anchorSource === "manual" ? (
              "from your marks."
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
      </section>

      {/* Video overlay (Phase 71) — sourced from the unified camera list, watch-only (video + trace,
          no attach card, no manual sync). "Add video" is a modal. VideoTracePanel is reused as-is. */}
      <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="font-semibold text-ink">Videos</h2>
          <button
            onClick={() => setShowAddVideo(true)}
            className="text-xs font-semibold text-primary"
          >
            + Add video
          </button>
        </div>
        {primaryCam ? (
          <VideoTracePanel
            readOnly
            sessionId={sessionId}
            velocity={vel}
            acceleration={accel}
            fsHz={fsHz}
            cycles={metrics.cycles ?? []}
            sessionDurationS={durationS}
            video={primaryCam}
            showVelocity={tracePrefs.showVelocity}
            showAcceleration={tracePrefs.showAcceleration}
            velColor={tracePrefs.velColor}
            accelColor={tracePrefs.accelColor}
            onToggleVelocity={tracePrefs.setShowVelocity}
            onToggleAcceleration={tracePrefs.setShowAcceleration}
            onVelColor={tracePrefs.setVelColor}
            onAccelColor={tracePrefs.setAccelColor}
          />
        ) : (
          <p className="text-sm text-muted">No video attached yet.</p>
        )}
      </section>
    </>
  );

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
        {/* star + ⋯ overflow (Delete) */}
        <div ref={menuRef} className="relative flex items-center gap-0.5">
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
          <button
            onClick={() => setMenuOpen((o) => !o)}
            aria-haspopup="true"
            aria-expanded={menuOpen}
            title="More"
            className="rounded-md px-2 py-1 text-xl leading-none text-muted hover:bg-surface-2 hover:text-ink"
          >
            ⋯
          </button>
          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-9 z-[90] min-w-[186px] rounded-xl border border-navy/50 bg-surface p-1.5 shadow-2xl"
            >
              <button
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  handleDelete();
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[13px] text-danger hover:bg-surface-2"
              >
                🗑 Delete session
              </button>
            </div>
          )}
        </div>
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

      {/* Identity meta — stroke · duration (no standalone distance, no "vs last N") + Annotate */}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
        {strokeLabel && <span className="font-medium text-ink">{strokeLabel}</span>}
        {durationS != null && (
          <>
            <span className="h-1 w-1 rounded-full bg-muted/60" aria-hidden="true" />
            <span>{durationS.toFixed(1)}s</span>
          </>
        )}
        <Link
          href={`/app/annotate/${sessionId}`}
          className="ml-auto text-xs font-semibold text-primary"
        >
          Annotate ›
        </Link>
      </div>

      {/* Provenance. api.py:899 sets this on a successful recompute; without it a coach could not
          tell "my annotation had no effect" from "it worked and the numbers barely moved". */}
      {metrics.data_quality?.recomputed_from_annotation && (
        <p className="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-1 rounded-xl border border-accent/40 bg-accent/10 px-3 py-2 text-xs leading-relaxed text-subtle">
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

      {/* The Data Quality card was retired here (61-02 D4). Dropout is the one stat on it that
          never touched the segmenter — see lib/dropoutWarning.js for why the other three went,
          and why this must never be gated on `warnings.length`. */}
      {dropoutWarning(metrics.data_quality) && (
        <p className="mt-3 rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-xs leading-relaxed text-warning-2">
          ⚠ {dropoutWarning(metrics.data_quality)}
        </p>
      )}

      {/* The phase surface is the report body. It renders the alert + timeline (or an empty state
          for legacy sessions), then middleSlot (velocity / Time-to-Distance / video), then the
          phase strip sections + Swimming per-cycle.
          `segmentationReliable` (83-01) is the provenance behind the Swimming inset's cycle-band
          badge — passed explicitly rather than inferred, because it is true only when the metrics
          were recomputed from the coach's own marks. */}
      <div className="mt-5">
        <PhaseReportCard
          phases={phases}
          velocity={vel}
          distProfile={dist}
          fsHz={fsHz}
          baseline={baseline}
          strokeType={strokeType}
          sessionId={sessionId}
          cycles={metrics.cycles}
          strokes={metrics.strokes}
          session={metrics.session}
          segmentationReliable={metrics.data_quality?.segmentation_reliable === true}
          unit={unit}
          middleSlot={middleSlot}
        />

        {/* Notes */}
        <section className="mb-5 rounded-2xl border border-navy/50 bg-surface p-5 shadow-sm">
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
        </section>
      </div>

      {/* AI Coach Chat — floating blob, grounded in this session's metrics (backend rebuilds the
          prompt). Mounted once; fixed-position, so its place in the tree does not matter. */}
      <CoachChat sessionId={sessionId} />

      {showAddVideo && (
        <AddVideoModal
          sessionId={sessionId}
          onClose={() => setShowAddVideo(false)}
          onAdded={() => loadVideos()}
        />
      )}
    </div>
  );
}
