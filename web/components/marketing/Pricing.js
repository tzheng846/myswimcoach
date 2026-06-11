const included = [
  "Unlimited recorded sessions",
  "All stroke-level metrics and data-quality reporting",
  "iOS recording app + web coach portal",
  "Shared encoder hardware — one device covers the lane",
  "Session history and comparison for every athlete",
];

export default function Pricing() {
  return (
    <section id="pricing" className="border-t border-navy/30">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-primary">
          PRICING
        </p>
        <h2 className="mt-3 text-3xl font-bold">Simple, per-swimmer pricing</h2>

        <div className="mx-auto mt-10 max-w-md rounded-2xl border border-navy bg-surface p-8 text-center shadow-[0_0_60px_rgba(33,150,243,0.08)]">
          <div className="flex items-baseline justify-center gap-2">
            <span className="text-5xl font-bold text-ink">$15</span>
            <span className="text-muted">/ swimmer / month</span>
          </div>
          <p className="mt-2 text-sm text-muted">
            Per active swimmer, billed to the program.
          </p>

          <ul className="mt-8 space-y-3 text-left">
            {included.map((item) => (
              <li key={item} className="flex gap-3 text-sm text-subtle">
                <svg
                  viewBox="0 0 24 24"
                  className="mt-0.5 h-4 w-4 shrink-0 stroke-success"
                  fill="none"
                  strokeWidth="2.5"
                  aria-hidden="true"
                >
                  <path d="M4 13l5 5L20 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {item}
              </li>
            ))}
          </ul>

          <a
            href="mailto:hello@swimnetics.com?subject=Early%20access%20to%20Swimnetics"
            className="mt-8 block rounded-lg bg-primary px-6 py-3 font-semibold text-white transition-colors hover:bg-accent"
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
