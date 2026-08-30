// Multi-camera video on one timeline.
//
// The four-angle claim is real (Phase 69). The panes carry NO camera-position labels and
// no brand name: the capability shipped, the labelled footage did not.
const PANES = [
  "linear-gradient(135deg,#2c0735,#4e148c)",
  "linear-gradient(135deg,#4e148c,#613dc1)",
  "linear-gradient(135deg,#613dc1,#858ae3)",
  "linear-gradient(135deg,#858ae3,#97dffc)",
];

export default function VideoSync() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
          VIDEO
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ink-900">
          Up to four angles on one timeline.
        </h2>
        <p className="mt-3.5 max-w-[62ch] text-base leading-relaxed text-ink-600">
          Add as many views of the swim as you filmed. Scrub any one clip to the
          push off and click once, and from then on every camera and the speed
          graph move together on a single timeline. Drag anywhere and all of them
          land on the same moment, so what you are watching and what the trace
          says are never a guess apart.
        </p>

        <div className="mt-7 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {PANES.map((background) => (
            <div
              key={background}
              className="rounded-2xl border border-line bg-card p-5 shadow-sm"
            >
              <div
                className="rounded-[10px]"
                style={{ aspectRatio: "16 / 10", background }}
              />
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-2xl border border-line bg-card p-5 shadow-sm">
          <svg viewBox="0 0 900 60" className="h-11 w-full" aria-hidden="true">
            <rect x="0" y="26" width="900" height="8" rx="4" fill="#ece7f5" />
            <rect x="0" y="26" width="330" height="8" rx="4" fill="#613dc1" />
            <circle
              cx="330"
              cy="30"
              r="9"
              fill="#4e148c"
              stroke="#ffffff"
              strokeWidth="3"
            />
            <g fill="#9b8ba6" fontSize="12">
              <text x="0" y="54">
                0:00
              </text>
              <text x="858" y="54">
                0:24
              </text>
            </g>
          </svg>
        </div>
      </div>
    </section>
  );
}
