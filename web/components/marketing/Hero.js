import ContactDialog from "./ContactDialog";
import SampleChart from "./SampleChart";

export default function Hero() {
  return (
    <>
      <section
        className="relative isolate overflow-hidden text-white"
        style={{
          background:
            "linear-gradient(160deg,#2c0735 0%,#4e148c 32%,#613dc1 64%,#858ae3 100%)",
        }}
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(circle at 80% 12%, rgba(151,223,252,0.45), transparent 42%), radial-gradient(circle at 8% 88%, rgba(133,138,227,0.5), transparent 45%)",
          }}
        />
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-24"
          style={{
            background: "linear-gradient(to bottom, transparent, var(--color-paper))",
          }}
        />

        <div className="relative mx-auto max-w-5xl px-5 pb-40 pt-24 text-center sm:pt-28">
          <span className="inline-block rounded-full border border-white/25 bg-white/15 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] backdrop-blur-sm">
            Velocity Intelligence
          </span>
          <h1 className="mx-auto mt-6 max-w-[16ch] text-5xl font-extrabold leading-[1.04] tracking-tight sm:text-6xl">
            Stroke-level <span className="text-sky">analysis.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-[54ch] text-lg leading-relaxed text-white/85">
            Turn your lane into a research-grade lab. Record, review, and analyze
            every swimmer — right from your iPhone, no laptop on deck.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <ContactDialog label="Request a quote" variant="light" size="lg" />
            <a
              href="#how-it-works"
              className="inline-flex h-12 items-center rounded-lg border border-white/40 px-7 text-base font-semibold text-white transition-colors hover:border-white hover:bg-white/10"
            >
              See how it works
            </a>
          </div>
          <p className="mt-4 text-sm text-white/70">
            Onboarding a small number of programs first.
          </p>
        </div>
      </section>

      <div className="relative z-10 -mt-28 px-5">
        <div className="mx-auto max-w-4xl rounded-3xl border border-line bg-card p-5 shadow-2xl sm:p-6">
          <SampleChart />
        </div>
      </div>
    </>
  );
}
