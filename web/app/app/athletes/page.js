"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import Avatar from "@/components/portal/Avatar";
import AddAthleteModal from "@/components/portal/AddAthleteModal";

function EditPanel({ athlete, onSaved, onCancel }) {
  const [parentName, setParentName] = useState(athlete.parent_name ?? "");
  const [parentEmail, setParentEmail] = useState(athlete.parent_email ?? "");
  const [hw, setHW] = useState(
    athlete.head_waist_m != null ? String(athlete.head_waist_m) : ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function save(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const updates = {
      parent_name: parentName.trim() || null,
      parent_email: parentEmail.trim() || null,
      head_waist_m: hw.trim() !== "" ? parseFloat(hw) : null,
    };
    const { error } = await supabase
      .from("athletes")
      .update(updates)
      .eq("id", athlete.id);
    setSaving(false);
    if (error) {
      setError(error.message);
    } else {
      onSaved(updates);
    }
  }

  return (
    <form onSubmit={save} className="mt-3 space-y-2 border-t border-navy/30 pt-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          value={parentName}
          onChange={(e) => setParentName(e.target.value)}
          placeholder="Parent name"
          className="rounded-md border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
        />
        <input
          type="email"
          value={parentEmail}
          onChange={(e) => setParentEmail(e.target.value)}
          placeholder="Parent email"
          className="rounded-md border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
        />
      </div>
      <input
        value={hw}
        onChange={(e) => setHW(e.target.value)}
        placeholder="Head–waist distance (m), e.g. 0.35"
        inputMode="decimal"
        className="w-full rounded-md border border-surface-3 bg-surface-2 px-3 py-2 text-sm outline-none focus:border-primary"
      />
      {error && <p className="text-sm text-[#ff5252]">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-primary px-4 py-1.5 text-sm font-semibold text-white hover:bg-accent disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-surface-3 px-4 py-1.5 text-sm text-subtle hover:text-ink"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function AthletesPage() {
  const [athletes, setAthletes] = useState(null);
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    supabase
      .from("athletes")
      .select("id, name, stroke_type, head_waist_m, parent_name, parent_email")
      .order("name")
      .then(({ data }) => setAthletes(data ?? []));
  }, []);

  function onAdded(inserted) {
    setAthletes((prev) =>
      [...prev, inserted].sort((a, b) => a.name.localeCompare(b.name))
    );
    setAdding(false);
  }

  if (athletes === null) return <p className="text-muted">Loading…</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Athletes</h1>
          <p className="mt-1 text-sm text-muted">{athletes.length} on roster</p>
        </div>
        <button
          onClick={() => setAdding(true)}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent"
        >
          + Add Athlete
        </button>
      </div>

      <div className="mt-6 space-y-3">
        {athletes.length === 0 && (
          <p className="py-10 text-center text-muted">
            No athletes yet. Add one to get started.
          </p>
        )}
        {athletes.map((a) => (
          <div
            key={a.id}
            className="rounded-xl border border-navy/50 bg-surface p-4"
          >
            <div className="flex items-center gap-3">
              <Avatar name={a.name} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{a.name}</p>
                <p className="text-xs capitalize text-muted">
                  {a.stroke_type || "breaststroke"}
                  {a.head_waist_m != null ? ` · head–waist ${a.head_waist_m} m` : ""}
                </p>
                <p className="mt-0.5 text-xs">
                  {a.parent_email ? (
                    <span className="text-subtle">
                      Parent: {a.parent_name ? `${a.parent_name} · ` : ""}
                      {a.parent_email}
                    </span>
                  ) : (
                    <span className="text-amber">No parent email</span>
                  )}
                </p>
              </div>
              {editingId !== a.id && (
                <button
                  onClick={() => setEditingId(a.id)}
                  className="text-sm text-subtle transition-colors hover:text-primary"
                >
                  Edit ✎
                </button>
              )}
            </div>
            {editingId === a.id && (
              <EditPanel
                athlete={a}
                onCancel={() => setEditingId(null)}
                onSaved={(updates) => {
                  setAthletes((prev) =>
                    prev.map((x) => (x.id === a.id ? { ...x, ...updates } : x))
                  );
                  setEditingId(null);
                }}
              />
            )}
          </div>
        ))}
      </div>

      {adding && (
        <AddAthleteModal onClose={() => setAdding(false)} onAdded={onAdded} />
      )}
    </div>
  );
}
