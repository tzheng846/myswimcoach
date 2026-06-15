import Link from "next/link";

const links = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#features", label: "Features" },
  { href: "/#pricing", label: "Pricing" },
  { href: "/faq", label: "FAQ" },
];

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-navy/40 bg-bg/80 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Link href="/" className="flex items-center">
          <span className="text-sm font-bold tracking-[0.3em] text-ink">
            SWIMNETICS
          </span>
        </Link>

        <div className="hidden items-center gap-8 sm:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-sm text-subtle transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </div>

        <Link
          href="/login"
          className="rounded-lg border border-navy bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:border-primary hover:text-primary"
        >
          Coach Login
        </Link>
      </nav>
    </header>
  );
}
