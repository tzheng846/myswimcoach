export default function WaveMark({ width = 90, height = 24, strokeWidth = 3 }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 180 48"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M 10 30 C 28 10, 45 10, 63 30 C 81 50, 98 50, 116 30 C 134 10, 151 10, 170 30"
        stroke="var(--color-wave)"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    </svg>
  );
}
