"use client";

import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

function reportUrl(token) {
  return `${window.location.origin}/report/${token}`;
}

function mailtoHref(report) {
  const a = report.athletes ?? {};
  const firstName = (a.name ?? "your swimmer").split(" ")[0];
  const subject = `${firstName}'s Swim Progress Report`;
  const greeting = a.parent_name ? `Hi ${a.parent_name},` : "Hi,";
  const body = `${greeting}\n\nHere is ${firstName}'s swim progress report:\n${reportUrl(report.token)}\n\nSee you at the pool!`;
  return `mailto:${a.parent_email ?? ""}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export default function ReportSendList({ refreshKey }) {
  const [reports, setReports] = useState(null);
  const [copied, setCopied] = useState(null); // report id or "all"

  const fetchReports = useCallback(async () => {
    const { data } = await supabase
      .from("reports")
      .select("id, token, created_at, sent_at, athletes(name, parent_name, parent_email)")
      .order("created_at", { ascending: false });
    setReports(data ?? []);
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports, refreshKey]);

  async function markSent(report) {
    if (report.sent_at) return;
    const sent_at = new Date().toISOString();
    setReports((prev) =>
      prev.map((r) => (r.id === report.id ? { ...r, sent_at } : r))
    );
    await supabase.from("reports").update({ sent_at }).eq("id", report.id);
  }

  async function copyLink(report) {
    await navigator.clipboard.writeText(reportUrl(report.token));
    setCopied(report.id);
    setTimeout(() => setCopied(null), 1500);
    markSent(report);
  }

  async function copyAll() {
    const lines = (reports ?? []).map((r) => {
      const a = r.athletes ?? {};
      return `${a.name ?? "?"} — ${a.parent_email ?? "no email"} — ${reportUrl(r.token)}`;
    });
    await navigator.clipboard.writeText(lines.join("\n"));
    setCopied("all");
    setTimeout(() => setCopied(null), 1500);
  }

  async function remove(report) {
    const a = report.athletes ?? {};
    if (!window.confirm(`Delete ${a.name ?? "this swimmer"}'s report card? The link will stop working.`))
      return;
    setReports((prev) => prev.filter((r) => r.id !== report.id));
    await supabase.from("reports").delete().eq("id", report.id);
  }

  if (reports === null) return <p className="mt-6 text-muted">Loading reports…</p>;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted">
          Generated Reports
        </p>
        {reports.length > 0 && (
          <button
            onClick={copyAll}
            className="text-xs text-primary hover:underline"
          >
            {copied === "all" ? "Copied ✓" : "Copy all links"}
          </button>
        )}
      </div>

      {reports.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          No reports yet — generate some above.
        </p>
      ) : (
        <div className="mt-3 space-y-2">
          {reports.map((r) => {
            const a = r.athletes ?? {};
            const date = new Date(r.created_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            });
            return (
              <div
                key={r.id}
                className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-navy/50 bg-surface px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">
                    {a.name ?? "Unknown swimmer"}
                    <span className="ml-2 font-normal text-muted">{date}</span>
                    {r.sent_at && (
                      <span className="ml-2 text-xs font-semibold text-success">
                        Sent ✓
                      </span>
                    )}
                  </p>
                  <p className="truncate text-xs">
                    {a.parent_email ? (
                      <span className="text-subtle">
                        {a.parent_name ? `${a.parent_name} · ` : ""}
                        {a.parent_email}
                      </span>
                    ) : (
                      <span className="text-amber">no parent email</span>
                    )}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  <a
                    href={`/report/${r.token}`}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-md border border-surface-3 px-2.5 py-1.5 text-xs text-subtle transition-colors hover:border-primary hover:text-primary"
                  >
                    View
                  </a>
                  <button
                    onClick={() => copyLink(r)}
                    className="rounded-md border border-surface-3 px-2.5 py-1.5 text-xs text-subtle transition-colors hover:border-primary hover:text-primary"
                  >
                    {copied === r.id ? "Copied ✓" : "Copy link"}
                  </button>
                  {a.parent_email && (
                    <a
                      href={mailtoHref(r)}
                      onClick={() => markSent(r)}
                      className="rounded-md bg-primary px-2.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-accent"
                    >
                      Email draft
                    </a>
                  )}
                  <button
                    onClick={() => remove(r)}
                    title="Delete report"
                    className="rounded-md px-2 py-1.5 text-xs text-muted transition-colors hover:text-danger"
                  >
                    ✕
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
