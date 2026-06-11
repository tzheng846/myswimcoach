const icon = {
  pulse: (
    <path d="M2 12h4l3-8 4 16 3-8h6" strokeLinecap="round" strokeLinejoin="round" />
  ),
  ruler: (
    <path d="M3 17L17 3l4 4L7 21l-4-4zm5-1l1.5 1.5M11 13l1.5 1.5M14 10l1.5 1.5M17 7l1.5 1.5" strokeLinecap="round" strokeLinejoin="round" />
  ),
  trend: (
    <path d="M3 5v14h18M7 15l4-6 3 3 5-7" strokeLinecap="round" strokeLinejoin="round" />
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="0.5" />
    </>
  ),
  glide: (
    <path d="M2 14c4 0 4-4 8-4s4 4 8 4 3-2 4-3M4 19h16" strokeLinecap="round" strokeLinejoin="round" />
  ),
  timer: (
    <>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l3 2M9 2h6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  ),
  shield: (
    <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3zm-3 9l2.5 2.5L16 10" strokeLinecap="round" strokeLinejoin="round" />
  ),
  phone: (
    <>
      <rect x="7" y="2" width="10" height="20" rx="2" />
      <path d="M11 18h2" strokeLinecap="round" />
    </>
  ),
  bolt: (
    <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" strokeLinejoin="round" />
  ),
  history: (
    <path d="M4 9a8 8 0 1 1-1 5M3 4v5h5M12 8v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
  ),
};

const metrics = [
  {
    icon: icon.pulse,
    name: "Stroke rate",
    body: "Strokes per minute from real cycle boundaries — not tap counting.",
  },
  {
    icon: icon.ruler,
    name: "Distance per stroke",
    body: "How far each cycle actually carries the swimmer down the lane.",
  },
  {
    icon: icon.trend,
    name: "Fatigue index",
    body: "Velocity decay across the swim — see exactly where technique breaks down.",
  },
  {
    icon: icon.target,
    name: "Consistency",
    body: "Cycle-to-cycle variation in peak velocity and stroke timing.",
  },
  {
    icon: icon.glide,
    name: "Coast fraction",
    body: "Time spent gliding versus producing propulsion, every cycle.",
  },
  {
    icon: icon.timer,
    name: "Time to distance",
    body: "Splits to any mark from 1–25 m, adjusted per swimmer.",
  },
];

const platform = [
  {
    icon: icon.phone,
    name: "Record from an iPhone",
    body: "Bluetooth recording at the block. No laptop on deck, ever.",
  },
  {
    icon: icon.bolt,
    name: "Processed in ~30 seconds",
    body: "Sessions upload and process server-side the moment the swim ends.",
  },
  {
    icon: icon.history,
    name: "History per athlete",
    body: "Every session stored to the swimmer's profile — compare across weeks.",
  },
  {
    icon: icon.shield,
    name: "Data quality flags",
    body: "Sensor dropout and outlier cycles surfaced, so you know when to trust a session.",
  },
];

function Card({ f }) {
  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-5 transition-colors hover:border-navy">
      <svg
        viewBox="0 0 24 24"
        className="h-6 w-6 stroke-primary"
        fill="none"
        strokeWidth="1.6"
        aria-hidden="true"
      >
        {f.icon}
      </svg>
      <h3 className="mt-3 text-sm font-semibold">{f.name}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted">{f.body}</p>
    </div>
  );
}

export default function Features() {
  return (
    <section id="features" className="border-t border-navy/30">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-primary">
          METRICS
        </p>
        <h2 className="mt-3 max-w-[24ch] text-3xl font-bold">
          Objective biomechanics for every swimmer in the lane
        </h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metrics.map((f) => (
            <Card key={f.name} f={f} />
          ))}
        </div>

        <p className="mt-16 text-xs font-semibold tracking-[0.3em] text-primary">
          PLATFORM
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {platform.map((f) => (
            <Card key={f.name} f={f} />
          ))}
        </div>
      </div>
    </section>
  );
}
