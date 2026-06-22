"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ContactDialog from "@/components/marketing/ContactDialog";

const links = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#features", label: "Features" },
  { href: "/faq", label: "FAQ" },
];

export default function Nav({ overHero = false }) {
  // overHero=false (default): always solid (pages with a light background at the
  // top — /faq, /privacy). overHero=true: transparent glass over the dark gradient
  // hero, flipping to solid on scroll (homepage only).
  const [scrolled, setScrolled] = useState(!overHero);

  useEffect(() => {
    if (!overHero) return;
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [overHero]);

  const linkColor = scrolled
    ? "text-ink-600 hover:text-brand"
    : "text-white/85 hover:text-white";

  return (
    <header
      className={`sticky top-0 z-50 transition-colors ${
        scrolled
          ? "border-b border-line bg-paper/90 backdrop-blur-md"
          : "border-b border-white/10"
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Link
          href="/"
          className={`text-sm font-extrabold tracking-[0.3em] transition-colors ${
            scrolled ? "text-ink-900" : "text-white"
          }`}
        >
          SWIMNETICS
        </Link>

        <div className="hidden items-center gap-8 sm:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`text-sm font-medium transition-colors ${linkColor}`}
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className={`hidden rounded-lg px-4 py-2 text-sm font-medium transition-colors sm:inline-block ${
              scrolled
                ? "text-ink-900 hover:bg-lavender"
                : "text-white hover:bg-white/10"
            }`}
          >
            Coach login
          </Link>
          <ContactDialog
            label="Request a quote"
            size="sm"
            variant={scrolled ? "default" : "light"}
          />
        </div>
      </nav>
    </header>
  );
}
