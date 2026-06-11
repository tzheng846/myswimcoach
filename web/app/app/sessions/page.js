"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import SessionCard from "@/components/portal/SessionCard";

const STROKES = [
  { key: "all", label: "All" },
  { key: "breaststroke", label: "Breaststroke" },
  { key: "freestyle", label: "Freestyle" },
  { key: "backstroke", label: "Backstroke" },
  { key: "butterfly", label: "Butterfly" },
  { key: "im", label: "Individual Medley" },
  { key: "udk", label: "Underwater Dolphin Kick" },
];

function SessionsView() {
  const router = useRouter();
  const params = useSearchParams();
  const athleteFilter = params.get("athlete") || "all";

  const [athletes, setAthletes] = useState([]);
  const [sessions, setSessions] = useState(null);
  const [strokeFilter, setStrokeFilter] = useState("all");

  useEffect(() => {
    supabase
      .from("athletes")
      .select("id, name")
      .order("name")
      .then(({ data }) => setAthletes(data ?? []));
  }, []);

  const fetchSessions = useCallback(async () => {
    let q = supabase
      .from("sessions")
      .select(
        "id, created_at, name, is_starred, stroke_type, athlete_id, session:metrics_json->session"
      )
      .order("created_at", { ascending: false });
    if (athleteFilter !== "all") q = q.eq("athlete_id", athleteFilter);
    const { data } = await q;
    setSessions(data ?? []);
  }, [athleteFilter]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Only show chips for strokes that actually have sessions (iOS Phase 17 behavior)
  const presentStrokeKeys = useMemo(
    () => new Set((sessions ?? []).map((s) => s.stroke_type).filter(Boolean)),
    [sessions]
  );
  const visibleStrokes = useMemo(
    () => STROKES.filter((s) => s.key === "all" || presentStrokeKeys.has(s.key)),
    [presentStrokeKeys]
  );
  useEffect(() => {
    if (sessions && strokeFilter !== "all" && !presentStrokeKeys.has(strokeFilter)) {
      setStrokeFilter("all");
    }
  }, [sessions, presentStrokeKeys, strokeFilter]);

  async function handleStar(item) {
    const newVal = !item.is_starred;
    setSessions((prev) =>
      prev.map((s) => (s.id === item.id ? { ...s, is_starred: newVal } : s))
    );
    try {
      await apiFetch(`/sessions/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_starred: newVal }),
      });
    } catch {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === item.id ? { ...s, is_starred: item.is_starred } : s
        )
      );
    }
  }

  async function handleDelete(item) {
    const label = item.name ? ` "${item.name}"` : "";
    if (!window.confirm(`Delete this session${label}? This cannot be undone.`))
      return;
    setSessions((prev) => prev.filter((s) => s.id !== item.id));
    try {
      await apiFetch(`/sessions/${item.id}`, { method: "DELETE" });
    } catch {
      fetchSessions();
    }
  }

  const displayed =
    strokeFilter === "all"
      ? sessions ?? []
      : (sessions ?? []).filter((s) => s.stroke_type === strokeFilter);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <select
          value={athleteFilter}
          onChange={(e) =>
            router.replace(
              e.target.value === "all"
                ? "/app/sessions"
                : `/app/sessions?athlete=${e.target.value}`
            )
          }
          className="rounded-lg border border-surface-3 bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
        >
          <option value="all">All athletes</option>
          {athletes.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {visibleStrokes.map((s) => (
          <button
            key={s.key}
            onClick={() => setStrokeFilter(s.key)}
            className={`rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-colors ${
              strokeFilter === s.key
                ? "border-primary bg-primary text-white"
                : "border-surface-3 bg-surface text-subtle hover:text-ink"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {sessions === null ? (
        <p className="mt-10 text-muted">Loading…</p>
      ) : displayed.length === 0 ? (
        <p className="mt-10 text-center text-muted">
          {strokeFilter === "all"
            ? "No sessions recorded yet."
            : `No ${STROKES.find((s) => s.key === strokeFilter)?.label} sessions.`}
        </p>
      ) : (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {displayed.map((item) => (
            <SessionCard
              key={item.id}
              session={item}
              onStar={() => handleStar(item)}
              onDelete={() => handleDelete(item)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SessionsPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading…</p>}>
      <SessionsView />
    </Suspense>
  );
}
