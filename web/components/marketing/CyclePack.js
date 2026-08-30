import G from "@/lib/marketingGeom";

// Every stroke cycle of the swim drawn together, the odd one picked out.
//
// Named for the pack of traces, deliberately NOT CycleOverlay: the portal already has
// components/portal/phases/CycleOverlay.js, and one name across marketing and portal is
// a trap. Traces are real geometry from the baked module; the longest cycle sets the x
// extent so the durations stay honest against each other.
const ODD = "#4e148c";
const REST = "#b9aecf";

export default function CyclePack() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <div className="grid items-center gap-7 md:grid-cols-[1.05fr_0.95fr]">
          <div>
            <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
              EVERY CYCLE
            </p>
            <h2 className="mt-3 text-3xl font-bold text-ink-900">
              Find the one stroke that was different.
            </h2>
            <p className="mt-3.5 max-w-[62ch] text-base leading-relaxed text-ink-600">
              Averages hide the stroke you actually needed to see. Swimnetics
              draws every cycle of the swim together, so a stroke that does not
              match the ones around it stands out on sight. You do not need to
              read a number to know something was off, and you can tell straight
              away which stroke of the lap it was.
            </p>
            <p className="mt-3.5 max-w-[62ch] text-base leading-relaxed text-ink-600">
              The same view works underwater, one line per dolphin kick, which is
              how you tell a pullout that faded from one that was short to begin
              with.
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            <p className="text-[11px] font-bold tracking-[0.3em] text-brand">
              {G.cycles.length} CYCLES, ONE VIEW
            </p>
            <svg
              viewBox="0 0 320 130"
              className="mt-3.5 block h-auto w-full"
              aria-hidden="true"
            >
              {G.cycles.map((c) => {
                const odd = c.n === G.oddCycle;
                return (
                  <polyline
                    key={c.n}
                    points={c.poly}
                    fill="none"
                    stroke={odd ? ODD : REST}
                    strokeWidth={odd ? 2.2 : 1.3}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    opacity={odd ? 1 : 0.75}
                  />
                );
              })}
            </svg>
            <p className="mt-3 text-[13px] text-ink-600">
              Cycle {G.oddCycle} runs longer and flatter than the ones around it.
              That is the one to ask about.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
