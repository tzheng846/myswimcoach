"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

const SUGGESTED = [
  "How was my consistency?",
  "What should I work on next?",
  "Where did I fatigue?",
];

// AI coaching chat for one saved session, presented as a floating bottom-right blob (Phase 75-07):
// a circular FAB toggles a standard chat panel. The backend (/coach/chat) rebuilds the prompt from
// the stored metrics — this component only sends {session_id, messages, simple}. The send logic is
// unchanged from the inline card it replaced; only the shell (FAB + fixed panel) is new.
export default function CoachChat({ sessionId, simple = false }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Focus the input when the panel opens (keyboard access).
  useEffect(() => {
    if (open) requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  // Esc closes the panel — only while open, so it never swallows Esc elsewhere on the page.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  async function send(text) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const res = await apiFetch("/coach/chat", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, messages: next, simple }),
      });
      setMessages([...next, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
      requestAnimationFrame(() => {
        if (scrollRef.current)
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      });
    }
  }

  return (
    <>
      {/* Floating action button — z above page content; the hover-explain scrim is z-40 and its
          popover z-[70], so the blob (z-[80]) stays reachable and never hides behind the scrim. */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close AI coach chat" : "Open AI coach chat"}
        aria-expanded={open}
        className="fixed bottom-6 right-6 z-[80] flex h-14 w-14 items-center justify-center rounded-full bg-accent text-2xl shadow-2xl transition-transform hover:scale-105 motion-reduce:transition-none"
      >
        💬
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="AI coach chat"
          className="fixed bottom-24 right-6 z-[80] flex h-[520px] max-h-[calc(100vh-8rem)] w-[370px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-navy/50 bg-surface shadow-2xl"
        >
          <div className="flex items-center gap-2.5 border-b border-navy/50 px-4 py-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-sm text-white">
              ✦
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-semibold text-ink">AI Coach</p>
              <p className="text-[11px] text-muted">grounded in this session</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close"
              className="rounded-md px-1.5 py-0.5 text-lg leading-none text-muted hover:bg-surface-2 hover:text-ink"
            >
              ×
            </button>
          </div>

          <div
            ref={scrollRef}
            className="flex-1 space-y-2.5 overflow-y-auto px-4 py-3.5"
          >
            {messages.length === 0 && !loading && (
              <p className="text-sm leading-relaxed text-muted">
                Ask about this swim — I answer from its stored metrics.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                <p
                  className={`max-w-[82%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-[13px] leading-relaxed ${
                    m.role === "user"
                      ? "rounded-br-sm bg-accent text-white"
                      : "rounded-bl-sm border border-navy/50 bg-surface-2 text-ink"
                  }`}
                >
                  {m.content}
                </p>
              </div>
            ))}
            {loading && (
              <p className="px-1 text-xs italic text-muted">Coach is thinking…</p>
            )}
            {error && (
              <p className="rounded-md bg-danger/10 px-3 py-2 text-xs text-danger">
                {error}
              </p>
            )}
          </div>

          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2 px-4 pb-2.5">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  disabled={loading}
                  className="rounded-full border border-surface-3 bg-surface-2 px-2.5 py-1.5 text-[11px] text-subtle transition-colors hover:text-ink disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2 border-t border-navy/50 px-3 py-2.5">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={loading}
              rows={1}
              placeholder="Ask about this swim…"
              className="max-h-24 flex-1 resize-none rounded-xl border border-surface-3 bg-surface-2 px-3 py-2 text-[13px] text-ink placeholder-muted outline-none focus:border-accent disabled:opacity-50"
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              aria-label="Send"
              className="flex h-9 w-9 flex-none items-center justify-center rounded-xl bg-accent text-white transition-opacity disabled:opacity-50"
            >
              ↑
            </button>
          </div>
        </div>
      )}
    </>
  );
}
