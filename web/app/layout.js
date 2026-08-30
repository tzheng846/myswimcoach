import "./globals.css";

// The mark is wired as the favicon by the Next.js file convention: app/icon.png and
// app/apple-icon.png are picked up automatically, so there is no icon entry here.
export const metadata = {
  title: "Swimnetics | Race-Phase Swim Analysis",
  description:
    "Precision performance metrics from a tethered encoder at the starting block. Every lap comes back split into the start, the underwater and the swimming, each scored against that swimmer's own recent history.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
