const steps = [
  {
    n: "1",
    title: "Clip it on",
    body: "Attach the encoder to the block, tether to the swimmer. No pool modification, nothing worn in the water.",
  },
  {
    n: "2",
    title: "Swim the set",
    body: "Record from the app — the device samples swim velocity at ~270 Hz while the swimmer just swims.",
  },
  {
    n: "3",
    title: "See it instantly",
    body: "Velocity, stroke rate, fatigue, consistency — processed server-side and back on the phone in seconds.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-navy/30">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-primary">
          HOW IT WORKS
        </p>
        <h2 className="mt-3 text-3xl font-bold">
          From dive to data in three steps
        </h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-3">
          {steps.map((s) => (
            <div
              key={s.n}
              className="rounded-xl border border-navy/50 bg-surface p-6"
            >
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-navy text-sm font-bold text-ink">
                {s.n}
              </span>
              <h3 className="mt-4 font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
