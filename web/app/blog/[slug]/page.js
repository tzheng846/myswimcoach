import Link from "next/link";
import { notFound } from "next/navigation";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { posts, getPost } from "@/lib/blog";

export function generateStaticParams() {
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return { title: "Build log — Swimnetics" };
  return { title: `${post.title} — Swimnetics`, description: post.excerpt };
}

export default async function BlogPost({ params }) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink-900">
      <Nav />
      <main className="flex-1">
        <article className="mx-auto w-full max-w-3xl px-5 py-16">
          <span className="text-xs font-semibold uppercase tracking-[0.15em] text-brand">
            {post.kicker}
          </span>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink-900">
            {post.title}
          </h1>

          <div className="mt-8">
            {post.body.map((block, i) =>
              block.h ? (
                <h2
                  key={i}
                  className="mt-8 text-xl font-semibold text-ink-900"
                >
                  {block.h}
                </h2>
              ) : (
                <p
                  key={i}
                  className="mt-4 text-sm leading-relaxed text-ink-600"
                >
                  {block.p}
                </p>
              )
            )}
          </div>

          <p className="mt-12">
            <Link
              href="/blog"
              className="text-sm text-ink-400 transition-colors hover:text-ink-900"
            >
              &larr; Back to the build log
            </Link>
          </p>
        </article>
      </main>
      <Footer />
    </div>
  );
}
