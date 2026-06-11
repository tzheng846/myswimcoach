"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function AddAthleteModal({ onClose, onAdded }) {
  const [name, setName] = useState("");
  const [hw, setHW] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleAdd(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const inserted = await apiFetch("/athletes", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          stroke_type: "breaststroke",
          head_waist_m: hw.trim() !== "" ? parseFloat(hw) : null,
        }),
      });
      onAdded(inserted);
    } catch (err) {
      setError(
        err.status === 402
          ? `${err.message} — upgrade your plan to add more athletes.`
          : err.message
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-5"
      onClick={onClose}
    >
      <form
        onSubmit={handleAdd}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-2xl border border-navy bg-surface p-6"
      >
        <h2 className="text-lg font-bold">Add athlete</h2>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Athlete name"
          autoFocus
          required
          className="mt-4 w-full rounded-lg border border-surface-3 bg-surface-2 px-4 py-3 outline-none focus:border-primary"
        />
        <input
          value={hw}
          onChange={(e) => setHW(e.target.value)}
          placeholder="Head–waist distance (m), e.g. 0.35"
          inputMode="decimal"
          className="mt-3 w-full rounded-lg border border-surface-3 bg-surface-2 px-4 py-3 outline-none focus:border-primary"
        />
        {error && <p className="mt-3 text-sm text-[#ff5252]">{error}</p>}
        <div className="mt-5 flex gap-3">
          <button
            type="submit"
            disabled={saving || !name.trim()}
            className="flex-1 rounded-lg bg-primary py-2.5 font-semibold text-white transition-colors hover:bg-accent disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-surface-3 py-2.5 text-subtle hover:text-ink"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
