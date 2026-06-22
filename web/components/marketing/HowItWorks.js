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
    <section id="how-it-works" className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
          HOW IT WORKS
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ink-900">
          From dive to data in three steps
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
