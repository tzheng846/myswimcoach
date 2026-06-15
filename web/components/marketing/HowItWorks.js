const steps = [
  {
    n: "1",
    title: "Clip it on",
    body: "It clips to the starting block and tethers to the swimmer. Nothing to install, nothing worn in the water.",
  },
  {
    n: "2",
    title: "Swim the set",
    body: "Tap record in the app. The swimmer just swims — no wearables, no change to the set.",
  },
  {
    n: "3",
    title: "See it instantly",
    body: "Speed, stroke rate, fatigue, and consistency — back on your phone seconds after the swim.",
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
