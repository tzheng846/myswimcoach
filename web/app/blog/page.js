import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { postsNewestFirst } from "@/lib/blog";

export const metadata = {
  title: "Build log — Swimnetics",
  description:
    "The real story behind the device — where Swimnetics is, what broke along the way, and where it's headed.",
};

export default function Blog() {
  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink-900">
      <Nav />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-5 py-16">
          <h1 className="text-3xl font-bold tracking-tight text-ink-900">
            Build log
          </h1>
          <p className="mt-6 text-sm leading-relaxed text-ink-600">
            The real story behind the device &mdash; where it is, what broke
            along the way, and where it&rsquo;s headed.
          </p>

          <div className="mt-10 space-y-5">
            {postsNewestFirst.map((post) => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="block rounded-2xl border border-line bg-card p-6 shadow-sm transition-colors hover:border-brand"
              >
                <span className="text-xs font-semibold uppercase tracking-[0.15em] text-brand">
                  {post.kicker}
                </span>
                <h2 className="mt-2 text-xl font-semibold text-ink-900">
                  {post.title}
                </h2>
                <p className="mt-3 text-sm leading-relaxed text-ink-600">
                  {post.excerpt}
                </p>
              </Link>
            ))}
          </div>

          <p className="mt-10">
            <Link
              href="/"
              className="text-sm text-ink-400 transition-colors hover:text-ink-900"
            >
              &larr; Back to home
            </Link>
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
