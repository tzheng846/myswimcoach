import ContactDialog from "./ContactDialog";

export default function RequestQuote() {
  return (
    <section id="pricing" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <div
          className="relative overflow-hidden rounded-3xl px-8 py-14 text-center text-white shadow-2xl sm:px-12"
          style={{
            background:
              "linear-gradient(135deg,#4e148c 0%,#613dc1 60%,#858ae3 100%)",
          }}
        >
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-white/75">
            Pricing
          </p>
          <h2 className="mx-auto mt-3 max-w-[18ch] text-3xl font-bold sm:text-4xl">
            Built for your program.
          </h2>
          <p className="mx-auto mt-4 max-w-[52ch] text-base leading-relaxed text-white/85 sm:text-lg">
            Every team is different. Tell us your roster and how you want to use
            it, and we&apos;ll put together a quote that fits.
          </p>
          <div className="mt-8 flex justify-center">
            <ContactDialog label="Request a quote" variant="light" size="lg" />
          </div>
        </div>
      </div>
    </section>
  );
}
