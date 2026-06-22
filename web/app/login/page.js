"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

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
    <main className="flex min-h-screen flex-1 flex-col items-center justify-center bg-paper px-6 py-16 text-ink-900">
      <Link
        href="/"
        className="text-2xl font-extrabold tracking-[0.3em] text-ink-900"
      >
        SWIMNETICS
      </Link>
      <p className="mt-1.5 text-[11px] font-semibold tracking-[0.3em] text-periwinkle">
        VELOCITY INTELLIGENCE
      </p>

      <form onSubmit={handleSignIn} className="mt-10 w-full max-w-sm">
        <Input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
          className="mb-3 h-12"
        />
        <Input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
          className="mb-3 h-12"
        />
        <Button type="submit" disabled={loading} className="mt-2 h-12 w-full">
          {loading ? "Signing in…" : "Sign In"}
        </Button>
        {error && (
          <p className="mt-4 text-center text-sm text-[#c0392b]">{error}</p>
        )}
      </form>
    </main>
  );
}
