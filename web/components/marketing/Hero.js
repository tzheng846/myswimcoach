import DeviceCanvas from "../three/DeviceCanvas";

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_70%_20%,rgba(30,58,95,0.35),transparent_60%)]" />
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 pb-20 pt-16 lg:grid-cols-2 lg:pb-28 lg:pt-24">
        <div className="relative z-10 min-w-0">
          <p className="mb-4 text-xs font-semibold tracking-[0.3em] text-amber">
            VELOCITY INTELLIGENCE
          </p>
          <h1 className="max-w-[18ch] text-4xl font-bold leading-tight sm:text-5xl">
            Stroke-level feedback, delivered poolside —{" "}
            <span className="text-primary">in seconds.</span>
          </h1>
          <p className="mt-6 max-w-[52ch] text-lg text-subtle">
            A tethered encoder wheel clips to the diving block and rides
            alongside the swimmer. Record a set from an iPhone, and the
            pipeline turns raw motion into stroke-level metrics — no laptop,
            no manual review, no waiting until practice is over.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href="mailto:hello@swimnetics.com?subject=Early%20access%20to%20Swimnetics"
              className="rounded-lg bg-primary px-6 py-3 font-semibold text-white transition-colors hover:bg-accent"
            >
              Get early access
            </a>
            <a
              href="#how-it-works"
              className="rounded-lg border border-navy px-6 py-3 font-medium text-subtle transition-colors hover:border-primary hover:text-ink"
            >
              See how it works
            </a>
          </div>
          <p className="mt-4 text-sm text-muted">
            Onboarding a small number of programs first.
          </p>
        </div>

        <div className="relative h-[320px] w-full min-w-0 overflow-hidden sm:h-[400px] lg:h-[460px]">
          <DeviceCanvas />
        </div>
      </div>
    </section>
  );
}
