const deviceIncluded = [
  "One-time purchase — no subscription required",
  "All core stroke-level metrics and data-quality reporting",
  "iOS recording app + web coach portal",
  "Shared encoder hardware — one device covers the lane",
];

const cloudIncluded = [
  "Video storage synced to each swim",
  "Long-term progress tracking across the season",
  "Full session history and comparison for every athlete",
  "Shareable parent progress reports",
];

function Check() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="mt-0.5 h-4 w-4 shrink-0 stroke-success"
      fill="none"
      strokeWidth="2.5"
      aria-hidden="true"
    >
      <path d="M4 13l5 5L20 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Pricing() {
  return (
    <section id="pricing" className="border-t border-navy/30">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-primary">
          PRICING
        </p>
        <h2 className="mt-3 text-3xl font-bold">
          Buy the device once. Add the cloud if you want it.
        </h2>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-navy bg-surface p-8 shadow-[0_0_60px_rgba(33,150,243,0.08)]">
            <p className="text-xs font-semibold tracking-[0.2em] text-muted">
              DEVICE
            </p>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-5xl font-bold text-ink">$300</span>
              <span className="text-muted">one-time</span>
            </div>
            <p className="mt-2 text-sm text-muted">
              The encoder and core metrics. Yours to keep.
            </p>
            <ul className="mt-8 space-y-3">
              {deviceIncluded.map((item) => (
                <li key={item} className="flex gap-3 text-sm text-subtle">
                  <Check />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-navy bg-surface p-8">
            <p className="text-xs font-semibold tracking-[0.2em] text-primary">
              CLOUD — OPTIONAL
            </p>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-5xl font-bold text-ink">$20</span>
              <span className="text-muted">/ swimmer / month</span>
            </div>
            <p className="mt-2 text-sm text-muted">
              Online history, video, and reports. Billed to the program.
            </p>
            <ul className="mt-8 space-y-3">
              {cloudIncluded.map((item) => (
                <li key={item} className="flex gap-3 text-sm text-subtle">
                  <Check />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mx-auto mt-10 max-w-md text-center">
          <a
            href="mailto:hello@swimnetics.com?subject=Early%20access%20to%20Swimnetics"
            className="block rounded-lg bg-primary px-6 py-3 font-semibold text-white transition-colors hover:bg-accent"
          >
            Get early access
          </a>
          <p className="mt-3 text-xs text-muted">
            We&apos;re onboarding a small number of programs first — reach out
            and we&apos;ll be in touch.
          </p>
        </div>
      </div>
    </section>
  );
}
