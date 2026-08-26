"use client";

// AlertSummary — the deterministic alert line at the top of the report card (Phase 75-05). A big
// count of active (non-dismissed) flags and a valence breakdown ("N worse / N changed / N better",
// zero chips omitted). NO LLM, no verdict prose — a pure count of what fell outside his usual, and
// the coach can dismiss any flag they disagree with (the × lives on each row; this line offers the
// bulk "restore"). Ported from the v3 concept mockup (report-card-concept-v3.html).

export default function AlertSummary({ flags = [], dismissedCount = 0, onRestore, baselineNote }) {
  const bad = flags.filter((f) => f.valence === "bad").length;
  const good = flags.filter((f) => f.valence === "good").length;
  const neu = flags.filter((f) => f.valence === "neutral").length;
  const total = flags.length;

  const restore =
    dismissedCount > 0 ? (
      <button onClick={onRestore} className="text-accent underline">
        restore {dismissedCount}
      </button>
    ) : null;

  if (total === 0) {
    return (
      <section className="mb-5 flex items-center gap-5 rounded-2xl border border-navy/50 bg-surface px-5 py-4 shadow-sm">
        <div className="min-w-[44px] text-center font-mono text-[34px] font-semibold leading-none text-good">
          0
        </div>
        <div className="min-w-0 text-sm text-ink">
          <b className="font-semibold">All in range.</b> Nothing fell outside his usual this swim.
        </div>
        {restore && <div className="ml-auto whitespace-nowrap text-right text-[11px] text-muted">{restore}</div>}
      </section>
    );
  }

  const chips = [
    bad > 0 && { cls: "border-bad/40 text-ink", dot: "bg-bad", n: bad, word: "worse" },
    neu > 0 && { cls: "border-navy text-ink", dot: "bg-neutral", n: neu, word: "changed (unclear)" },
    good > 0 && { cls: "border-good/40 text-ink", dot: "bg-good", n: good, word: "better" },
  ].filter(Boolean);

  return (
    <section className="mb-5 flex items-center gap-5 rounded-2xl border border-navy/50 bg-surface px-5 py-4 shadow-sm">
      <div className="min-w-[44px] text-center font-mono text-[34px] font-semibold leading-none text-ink">
        {total}
      </div>
      <div className="min-w-0">
        <div className="text-sm text-ink">
          <b className="font-semibold">
            {total} metric{total > 1 ? "s" : ""} differ from his usual
          </b>
          {baselineNote ? ` — ${baselineNote}.` : "."}
        </div>
        <div className="mt-1.5 flex flex-wrap gap-2">
          {chips.map((c) => (
            <span
              key={c.word}
              className={`inline-flex items-center gap-1.5 rounded-full border bg-surface-2 px-2.5 py-0.5 text-[11px] text-subtle ${c.cls}`}
            >
              <span className={`h-2 w-2 rounded-full ${c.dot}`} />
              <b className="font-semibold text-ink">{c.n}</b> {c.word}
            </span>
          ))}
        </div>
      </div>
      <div className="ml-auto whitespace-nowrap text-right text-[11px] text-muted">
        × each to dismiss
        {restore && (
          <>
            <br />
            {restore}
          </>
        )}
      </div>
    </section>
  );
}
