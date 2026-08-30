const steps = [
  {
    n: "1",
    title: "Clamp it on",
    body: "The unit clamps to the starting block and the swimmer buckles on the belt. Setup takes about a minute, and you only do it once for the whole session.",
  },
  {
    n: "2",
    title: "Run the set",
    body: "Tap record and coach the lane the way you normally would. The swimmer just swims. Nothing about the set has to change to fit the device.",
  },
  {
    n: "3",
    title: "Read the card",
    body: "The swim uploads on its own and comes back split by phase, with anything that moved already marked at the top.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
          HOW IT WORKS
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ink-900">
          From dive to report card in three steps.
        </h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-3">
          {steps.map((s) => (
            <div
              key={s.n}
              className="rounded-2xl border border-line bg-card p-6 shadow-sm"
            >
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand text-sm font-bold text-white">
                {s.n}
              </span>
              <h3 className="mt-4 font-semibold text-ink-900">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
