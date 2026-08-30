// The within-athlete comparison section.
//
// The alert rule this section exists to state: an alert fires ONLY when today falls
// outside the usual range. An in-range row is grey, is labelled Normal, and is NOT
// counted as an alert. The counts below are derived from the table, never typed in.
//
// The table is illustrative, but it is internally coherent and must stay that way: a
// green or red row sits OUTSIDE its band, a grey row sits INSIDE it. A round-2 draft of
// this section shipped a green row sitting inside its own band, which is exactly the
// contradiction the section argues against. scratch/marketing_render_check.mjs asserts
// the rule against the rendered markup, because hand-authored data drifts silently.
const VAL = { good: "#2f9e63", bad: "#c9503f", flat: "#6e5a78" };

//        label                        today  lo  hi  med  valence
const STRIPS = [
  ["Peak speed off the block", 89, 62, 84, 73, "good"],
  ["Underwater kick count", 41, 55, 78, 66, "bad"],
  ["Breakout distance", 63, 52, 76, 64, "flat"],
  ["Distance per stroke", 71, 58, 80, 69, "flat"],
  ["Speed lost across the lap", 88, 44, 70, 57, "bad"],
  ["Coast fraction", 52, 46, 72, 59, "flat"],
];

const nBad = STRIPS.filter((s) => s[5] === "bad").length;
const nGood = STRIPS.filter((s) => s[5] === "good").length;
const nNormal = STRIPS.filter((s) => s[5] === "flat").length;
const nAlerts = nBad + nGood; // normal rows are not alerts

const POINTS = [
  {
    head: "Built from that athlete’s own history",
    body: "The usual range comes from their last five swims in the same stroke, so it moves as they improve. Nothing is scored against a number we invented.",
  },
  {
    head: "Alerts all change",
    body: "Not only the drops. Anything that lands outside the usual range gets flagged, the gains as well as the losses. Anything still inside it is a normal day and stays quiet, so an alert always means something actually moved.",
  },
  {
    head: "Concise summaries",
    body: "The card opens with how many alerts came back and which way they went, so you know whether this swim needs you before you scroll. Clear it once you have looked.",
  },
];

function Strip({ label, today, lo, hi, med, valence }) {
  return (
    <div className="grid grid-cols-[1fr_200px] items-center gap-4 border-b border-line py-2.5 last:border-b-0">
      <div className="text-sm text-ink-900">{label}</div>
      <svg viewBox="0 0 200 18" className="h-[18px] w-[200px]" aria-hidden="true">
        <rect x="0" y="7" width="200" height="4" rx="2" fill="#ece7f5" />
        <rect
          x={lo * 2}
          y="4"
          width={(hi - lo) * 2}
          height="10"
          rx="5"
          fill="#d9d2ec"
        />
        <rect x={med * 2 - 0.6} y="2" width="1.6" height="14" fill="#9b8ba6" />
        <circle cx={today * 2} cy="9" r="5.4" fill={VAL[valence]} />
        <circle
          cx={today * 2}
          cy="9"
          r="5.4"
          fill="none"
          stroke="#ffffff"
          strokeWidth="1.6"
        />
      </svg>
    </div>
  );
}

export default function UsualRange() {
  return (
    <section className="border-t border-line">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-xs font-semibold tracking-[0.3em] text-periwinkle">
          HOW IT IS JUDGED
        </p>
        <h2 className="mt-3 text-3xl font-bold text-ink-900">
          Compare your current against your past.
        </h2>
        <p className="mt-3.5 max-w-[62ch] text-base leading-relaxed text-ink-600">
          There is no national average worth coaching against. A fourteen year
          old breaststroker and a college sprinter do not share a target. Every
          number in the report card is put next to the same swimmer&rsquo;s
          recent swims in the same stroke, so the only thing you are ever
          comparing them to is themselves. Inside the usual range is a normal
          day. Outside it is worth a conversation.
        </p>

        <div className="mt-9 grid items-center gap-7 md:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            {/* Count on its own line, chips beneath: at this column width all four
                cannot share a row without orphaning the last chip. */}
            <div className="rounded-xl border border-line bg-lavender px-4 py-3">
              <span className="block text-[15px] font-bold text-ink-900">
                {nAlerts} alerts today
              </span>
              <span className="mt-2.5 flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-[7px] rounded-full border border-line bg-card px-3 py-1 text-[13px] text-ink-900">
                  <i
                    className="block h-2 w-2 rounded-full"
                    style={{ background: VAL.bad }}
                  />
                  {nBad} worse
                </span>
                <span className="inline-flex items-center gap-[7px] rounded-full border border-line bg-card px-3 py-1 text-[13px] text-ink-900">
                  <i
                    className="block h-2 w-2 rounded-full"
                    style={{ background: VAL.good }}
                  />
                  {nGood} better
                </span>
                <span className="inline-flex items-center rounded-full border border-line bg-card px-3 py-1 text-[13px] text-ink-400">
                  {nNormal} normal
                </span>
              </span>
            </div>

            <p className="mb-3 mt-5 text-[11px] font-bold tracking-[0.3em] text-brand">
              TODAY VS USUAL
            </p>
            {STRIPS.map(([label, today, lo, hi, med, valence]) => (
              <Strip
                key={label}
                label={label}
                today={today}
                lo={lo}
                hi={hi}
                med={med}
                valence={valence}
              />
            ))}

            <div className="mt-4 flex flex-wrap gap-5 text-[12.5px] text-ink-600">
              <span className="inline-flex items-center gap-[7px]">
                <i
                  className="block h-2.5 w-2.5 rounded-full"
                  style={{ background: VAL.good }}
                />
                Better than usual
              </span>
              <span className="inline-flex items-center gap-[7px]">
                <i
                  className="block h-2.5 w-2.5 rounded-full"
                  style={{ background: VAL.bad }}
                />
                Worse than usual
              </span>
              <span className="inline-flex items-center gap-[7px]">
                <i
                  className="block h-2.5 w-2.5 rounded-full"
                  style={{ background: VAL.flat }}
                />
                Normal
              </span>
            </div>
          </div>

          <div className="grid gap-[18px]">
            {POINTS.map((p) => (
              <p key={p.head} className="text-[13px] leading-relaxed text-ink-600">
                <b className="mb-[3px] block text-[15px] font-semibold text-ink-900">
                  {p.head}
                </b>
                {p.body}
              </p>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
