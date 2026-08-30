import G from "@/lib/marketingGeom";
import PhaseRadar from "./PhaseRadar";

// The report card section: one real lap with its three phase windows highlighted in
// place, then a card per phase carrying that phase's radar.
//
// Geometry comes from the baked module, so this page never touches Supabase.
// Colours are literal hex for the same reason as PhaseRadar: raw SVG paint attributes
// cannot rely on Tailwind theme tokens surviving tree-shaking.
const COLOR = { start: "#f2b134", uw: "#2196f3", swim: "#a970ff" };
const TRACE = "#2c0735";
const AXIS = "#9b8ba6";
const LABEL = "#6e5a78";

const PHASES = [
  {
    key: "start",
    tag: "The start",
    title: "Off the block and into the water",
    body: "How hard the push was, how long the streamline held, and how much speed the entry gave back before the first kick.",
  },
  {
    key: "uw",
    tag: "The underwater",
    title: "Every kick, counted",
    body: "The pullout is the part of the race almost nobody has numbers for. Swimnetics finds each downkick in the speed trace and measures what it bought.",
  },
  {
    key: "swim",
    tag: "The swimming",
    title: "Stroke by stroke to the touch",
    body: "Every cycle from the breakout to the wall, measured against the ones on either side of it rather than against an average.",
  },
];

const BAND_NAME = { start: "START", uw: "UNDERWATER", swim: "SWIMMING" };

function WholeLap() {
  const w = G.whole;
  const keys = ["start", "uw", "swim"];
  return (
    <svg viewBox="0 0 900 250" className="block h-auto w-full" aria-hidden="true">
      {keys.map((k) => (
        <rect
          key={k}
          x={w.bands[k].x}
          y="0"
          width={w.bands[k].w}
          height="250"
          fill={COLOR[k]}
          opacity="0.15"
        />
      ))}
      <rect
        x={w.tail.x}
        y="0"
        width={w.tail.w}
        height="250"
        fill="#9b8ba6"
        opacity="0.07"
      />
      {keys.map((k) => (
        <line
          key={k}
          x1={w.bands[k].x}
          y1="0"
          x2={w.bands[k].x}
          y2="250"
          stroke={COLOR[k]}
          strokeWidth="1.2"
          opacity="0.55"
        />
      ))}
      <polyline
        points={w.poly}
        fill="none"
        stroke={TRACE}
        strokeWidth="1.9"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* The Start window is about 0.6 s of a 20 s lap, so its band is far narrower
          than the word START. Shrink the label rather than let it spill across the
          neighbouring phases. */}
      <g fontWeight="700" fill={LABEL}>
        {keys.map((k) => {
          const narrow = w.bands[k].w < 70;
          return (
            <text
              key={k}
              x={w.bands[k].mid}
              y="20"
              textAnchor="middle"
              fontSize={narrow ? 9 : 11.5}
              letterSpacing={narrow ? 0.4 : 1.5}
            >
              {BAND_NAME[k]}
            </text>
          );
        })}
      </g>
      <text x="4" y="20" fill={AXIS} fontSize="11">
        m/s
      </text>
      {/* End time sits top right: the trace tail is low there and the two collided
          when this label was at the bottom. */}
      <text x="896" y="20" fill={AXIS} fontSize="11" textAnchor="end">
        {w.end} s
      </text>
    </svg>
  );
}

export default function PhaseStory() {
  return (
    <section id="report-card">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
          THE REPORT CARD
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ink-900">
          One lap, three phases, buried insights brought up.
        </h2>
        <p className="mt-3.5 max-w-[62ch] text-base leading-relaxed text-ink-600">
          A stopwatch gives you one number for the whole swim. Two swimmers can
          post that same number off completely different races, one on a strong
          start, the other on a strong back half. Swimnetics splits the swim
          where the race actually changes and scores each part on its own.
        </p>

        <div className="mt-8 rounded-2xl border border-line bg-card p-5 shadow-sm">
          <WholeLap />
          <p className="mt-2.5 text-center text-xs text-ink-400">
            One lap, start to touch. The race splits itself into three parts, and
            each one is scored on its own.
          </p>
        </div>

        {/* Never a flex column here: an SVG with height:auto collapses to zero height
            inside a flex item, which silently blanks every radar and neither the build
            nor the linter says a word. Each card is its own grid instead, with the
            blurb row taking the slack (1fr) so the radar always sits in the last row.
            That keeps the three radars on one baseline at every width the cards share
            a row, which a fixed min-height on the blurb does not: the underwater blurb
            wraps to a fifth line once the column narrows. */}
        <div className="mt-9 grid gap-4 sm:grid-cols-3">
          {PHASES.map((p) => (
            <div
              key={p.key}
              className="grid grid-rows-[auto_auto_1fr_auto] rounded-2xl border border-line bg-card p-5 shadow-sm"
            >
              <span className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.16em] text-ink-400">
                <i
                  className="block h-2.5 w-2.5 rounded-[3px]"
                  style={{ background: COLOR[p.key] }}
                />
                {p.tag}
              </span>
              <h3 className="mt-3.5 text-[17px] font-bold leading-tight text-ink-900">
                {p.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">
                {p.body}
              </p>
              <div className="mt-2.5 border-t border-line pt-2">
                <PhaseRadar axes={G.radars[p.key]} color={COLOR[p.key]} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
