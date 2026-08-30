// The hardware section. Benefits, not materials: the plastic and the line are named
// nowhere on the site any more. The breakaway magnet is real hardware and the claim
// stays exactly as narrow as the hardware, with no rating or certification implied.
const CARDS = [
  {
    head: "Built for a wet deck",
    body: "Splashproof, and made to live in chlorine and sun without going brittle.",
  },
  {
    head: "Safety built in",
    body: "The tether holds on a breakaway magnet and lets go if it ever snags, so the swimmer is never tied to the block.",
  },
  {
    head: "No laptop on deck",
    body: "Records over Bluetooth straight to an iPhone, standing at the block.",
  },
  {
    head: "Back in about thirty seconds",
    body: "The swim uploads and processes on its own while the next swimmer gets ready.",
  },
];

export default function Device() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
          THE DEVICE
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ink-900">
          One unit covers the lane.
        </h2>
        <p className="mt-3.5 max-w-[62ch] text-base leading-relaxed text-ink-600">
          The encoder clamps to the starting block and tethers to a belt around
          the swimmer&rsquo;s waist. Nothing is worn on the wrist, nothing goes
          in the cap, and nothing has to be charged between swimmers. One athlete
          finishes, hands the belt to the next one, and the set keeps moving. A
          squad of thirty does not need thirty devices.
        </p>

        <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CARDS.map((c) => (
            <div
              key={c.head}
              className="rounded-2xl border border-line bg-card p-5 shadow-sm"
            >
              <p className="text-[13px] leading-relaxed text-ink-600">
                <b className="mb-[3px] block text-[15px] font-semibold text-ink-900">
                  {c.head}
                </b>
                {c.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
