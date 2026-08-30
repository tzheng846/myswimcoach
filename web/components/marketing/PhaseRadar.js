// One phase's radar. Presentational only: it takes the axes it is given and reads the
// axis count from them, so 4 or 6 axes need no change here.
//
// Geometry is ported from radar_svg() in scratch/_build_mockup.py. Two details are
// load bearing and easy to lose:
//   - The viewBox is much wider than the plot (300 for a 132 wide plot centred at
//     x=150). That margin is the only thing keeping the left and right axis labels
//     from clipping at the card edge. Do not tighten it.
//   - Label anchoring is computed from the axis angle, never hardcoded per index,
//     because the index that sits on the right edge changes with the axis count.
//
// Colours are literal hex rather than theme var() reads. These are raw SVG paint
// attributes, and Tailwind v4 tree-shakes theme tokens that no utility class
// references (the 83-01 bug: stroke silently resolved to none).
const CY = 108;
const CX = 150;
const R = 66;
const WEB = "#e8e4f2";
const BAND = "#9b8ba6";
const PAPER = "#fbfbfe";
const LABEL = "#6e5a78";
const HALF = 0.085; // half width of the drawn usual-range ring

export default function PhaseRadar({ axes, color }) {
  const n = axes.length;
  const angles = axes.map((_, i) => -90 + i * (360 / n));
  const pt = (i, r) => {
    const a = (angles[i] * Math.PI) / 180;
    return [CX + Math.cos(a) * R * r, CY + Math.sin(a) * R * r];
  };
  const poly = (radii) =>
    radii.map((r, i) => pt(i, r).map((v) => v.toFixed(1)).join(",")).join(" ");

  const outer = poly(axes.map((a) => a.ring + HALF));
  const inner = poly(axes.map((a) => Math.max(0.05, a.ring - HALF)));
  const today = poly(axes.map((a) => a.r));

  return (
    <svg
      viewBox="0 0 300 214"
      className="block h-auto w-full"
      aria-hidden="true"
    >
      {[0.35, 0.7, 1].map((ring) => (
        <polygon
          key={ring}
          points={poly(axes.map(() => ring))}
          fill="none"
          stroke={WEB}
          strokeWidth="1"
        />
      ))}
      {axes.map((a, i) => {
        const [x, y] = pt(i, 1);
        return (
          <line
            key={a.label}
            x1={CX}
            y1={CY}
            x2={x.toFixed(1)}
            y2={y.toFixed(1)}
            stroke={WEB}
            strokeWidth="1"
          />
        );
      })}

      {/* The usual range: a band, drawn as an outer ring with the inner one punched
          back out in paper so the fill reads as a ring rather than a blob. */}
      <polygon points={outer} fill={BAND} opacity="0.16" />
      <polygon points={inner} fill={PAPER} />
      <polygon
        points={outer}
        fill="none"
        stroke={BAND}
        strokeWidth="1"
        strokeDasharray="3 3"
      />

      <polygon
        points={today}
        fill={color}
        opacity="0.24"
        stroke={color}
        strokeWidth="2.4"
        strokeLinejoin="round"
      />
      {axes.map((a, i) => {
        const [x, y] = pt(i, a.r);
        return (
          <circle
            key={a.label}
            cx={x.toFixed(1)}
            cy={y.toFixed(1)}
            r="3.4"
            fill={color}
            stroke="#ffffff"
            strokeWidth="1.2"
          />
        );
      })}

      {axes.map((a, i) => {
        const rad = (angles[i] * Math.PI) / 180;
        const dx = Math.cos(rad);
        const dy = Math.sin(rad);
        const [x, y] = pt(i, 1);
        const anchor =
          Math.abs(dx) < 0.25 ? "middle" : dx > 0 ? "start" : "end";
        return (
          <text
            key={a.label}
            x={(x + 8 * dx).toFixed(1)}
            y={(y + 13 * dy + (Math.abs(dy) < 0.25 ? 0 : 3)).toFixed(1)}
            fill={LABEL}
            fontSize="10.5"
            textAnchor={anchor}
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}
