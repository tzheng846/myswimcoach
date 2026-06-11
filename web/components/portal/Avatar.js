// Same color-hash convention as iOS AthletesScreen.js
const AVATAR_COLORS = ["#2563EB", "#7C3AED", "#0891B2", "#059669", "#D97706", "#DC2626"];

export function avatarColor(name) {
  const code = (name?.charCodeAt(0) ?? 65) - 65;
  return AVATAR_COLORS[Math.abs(code) % AVATAR_COLORS.length];
}

export default function Avatar({ name, size = 40 }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full font-bold text-white"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        backgroundColor: avatarColor(name),
      }}
    >
      {name?.[0]?.toUpperCase() ?? "?"}
    </div>
  );
}
