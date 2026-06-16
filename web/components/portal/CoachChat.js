"use client";

import { useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

const SUGGESTED = [
  "How was my consistency?",
  "What should I work on next?",
  "Where did I fatigue?",
];

// AI coaching chat for one saved session. The backend (/coach/chat) rebuilds the
// prompt from the stored metrics — this component only sends {session_id, messages, simple}.
export default function CoachChat({ sessionId, simple = false }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

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
    <div className="rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
        Coach Chat
      </p>

      {messages.length > 0 && (
        <div
          ref={scrollRef}
          className="mb-3 max-h-80 space-y-2 overflow-y-auto"
        >
          {messages.map((m, i) => (
            <div
              key={i}
              className={
                m.role === "user" ? "flex justify-end" : "flex justify-start"
              }
            >
              <p
                className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-accent text-white"
                    : "bg-surface-2 text-ink"
                }`}
              >
                {m.content}
              </p>
            </div>
          ))}
          {loading && (
            <p className="px-1 text-xs italic text-muted">Coach is thinking…</p>
          )}
        </div>
      )}

      {error && (
        <p className="mb-2 rounded-md bg-danger/10 px-3 py-2 text-xs text-danger">
          {error}
        </p>
      )}

      {messages.length === 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGGESTED.map((q) => (
            <button
              key={q}
              onClick={() => send(q)}
              disabled={loading}
              className="rounded-full border border-surface-3 bg-surface-2 px-3 py-1.5 text-xs text-subtle transition-colors hover:text-ink disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={loading}
          placeholder="Ask your coach…"
          className="flex-1 rounded-lg border border-surface-3 bg-surface-2 px-3 py-2 text-sm text-ink placeholder-muted outline-none focus:border-accent disabled:opacity-50"
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
