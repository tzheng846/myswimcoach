import Link from "next/link";
import WaveMark from "./WaveMark";

export default function Footer() {
  return (
    <footer className="border-t border-navy/40">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-12 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <WaveMark width={56} height={15} strokeWidth={4} />
            <span className="text-xs font-bold tracking-[0.3em] text-ink">
              SWIMNETICS
            </span>
          </div>
          <p className="mt-3 text-sm text-muted">
            Built for swim academies and competitive programs.
          </p>
        </div>
        <div className="text-sm text-muted">
          <a
            href="mailto:hello@swimnetics.com"
            className="text-subtle transition-colors hover:text-primary"
          >
            hello@swimnetics.com
          </a>
          <p className="mt-2">
            <Link
              href="/faq"
              className="text-subtle transition-colors hover:text-primary"
            >
              FAQ
            </Link>
          </p>
          <p className="mt-2">
            <Link
              href="/privacy"
              className="text-subtle transition-colors hover:text-primary"
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
