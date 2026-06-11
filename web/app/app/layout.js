"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import WaveMark from "@/components/WaveMark";
import { supabase } from "@/lib/supabase";

const navLinks = [
  { href: "/app", label: "Dashboard" },
  { href: "/app/athletes", label: "Athletes" },
  { href: "/app/sessions", label: "Sessions" },
  { href: "/app/compare", label: "Compare" },
  { href: "/app/reports", label: "Reports" },
];

export default function PortalLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState(undefined); // undefined = loading

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (!session) router.replace("/login");
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (!session) router.replace("/login");
    });
    return () => subscription.unsubscribe();
  }, [router]);

  if (!session) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted">
        {session === undefined ? "Loading…" : "Redirecting…"}
      </div>
    );
  }

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-navy/40 bg-bg/80 backdrop-blur-md">
        <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-5">
          <div className="flex items-center gap-8">
            <Link href="/app" className="flex items-center gap-2.5">
              <WaveMark width={56} height={15} strokeWidth={4} />
              <span className="hidden text-xs font-bold tracking-[0.3em] text-ink sm:inline">
                SWIMNETICS
              </span>
            </Link>
            <div className="flex items-center gap-5">
              {navLinks.map((l) => {
                const active =
                  l.href === "/app"
                    ? pathname === "/app"
                    : pathname.startsWith(l.href);
                return (
                  <Link
                    key={l.href}
                    href={l.href}
                    className={`text-sm transition-colors ${
                      active ? "font-semibold text-primary" : "text-subtle hover:text-ink"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
            </div>
          </div>
          <button
            onClick={async () => {
              await supabase.auth.signOut();
              router.replace("/");
            }}
            className="text-sm text-muted transition-colors hover:text-ink"
          >
            Sign out
          </button>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-8">
        {children}
      </main>
    </>
  );
}
