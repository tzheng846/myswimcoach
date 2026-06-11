import "./globals.css";

export const metadata = {
  title: "Swimnetics — Biomechanical Swim Coaching",
  description:
    "Biomechanical swim coaching from a tethered magnetic encoder wheel. Stroke-level metrics delivered poolside in seconds — no laptop required.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
