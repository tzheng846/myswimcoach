"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSignIn(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      router.replace("/app");
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <Link href="/" className="text-2xl font-bold tracking-[0.35em]">
        SWIMNETICS
      </Link>
      <p className="mt-1.5 text-[11px] tracking-[0.3em] text-amber">
        VELOCITY INTELLIGENCE
      </p>

      <form onSubmit={handleSignIn} className="mt-10 w-full max-w-sm">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
          className="mb-3 w-full rounded-lg border border-surface-3 bg-surface px-4 py-3.5 text-ink placeholder-muted outline-none focus:border-primary"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
          className="mb-3 w-full rounded-lg border border-surface-3 bg-surface px-4 py-3.5 text-ink placeholder-muted outline-none focus:border-primary"
        />
        <button
          type="submit"
          disabled={loading}
          className="mt-2 w-full rounded-lg bg-primary py-3.5 font-semibold text-white transition-colors hover:bg-accent disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Sign In"}
        </button>
        {error && (
          <p className="mt-4 text-center text-sm text-[#ff5252]">{error}</p>
        )}
      </form>
    </main>
  );
}
