import Link from "next/link";
import { CONTACT_EMAIL } from "@/lib/site";

export default function Footer() {
  return (
    <footer className="border-t border-line bg-paper">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-12 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="text-xs font-extrabold tracking-[0.3em] text-ink-900">
            SWIMNETICS
          </span>
          <p className="mt-3 text-sm text-ink-400">
            Built for swim academies and competitive programs.
          </p>
        </div>
        <div className="text-sm text-ink-400">
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="text-ink-600 transition-colors hover:text-brand"
          >
            {CONTACT_EMAIL}
          </a>
          <p className="mt-2">
            <Link href="/faq" className="text-ink-600 transition-colors hover:text-brand">
              FAQ
            </Link>
          </p>
          <p className="mt-2">
            <Link
              href="/privacy"
              className="text-ink-600 transition-colors hover:text-brand"
            >
              Privacy Policy
            </Link>
          </p>
          <p className="mt-2">© {new Date().getFullYear()} Swimnetics</p>
        </div>
      </div>
    </footer>
  );
}
