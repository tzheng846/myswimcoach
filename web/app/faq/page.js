import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

export const metadata = {
  title: "FAQ — Swimnetics",
  description:
    "Answers for coaches: what Swimnetics measures, how it fits into practice, durability, supported strokes, pricing, and how swimmer data is protected.",
};

const CONTACT_EMAIL = "hello@swimnetics.com";

function Faq({ q, children }) {
  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold text-ink">{q}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-subtle">
        {children}
      </div>
    </section>
  );
}

export default function FAQ() {
  return (
    <>
      <Nav />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-5 py-16">
          <h1 className="text-3xl font-bold tracking-tight text-ink">
            Frequently asked questions
          </h1>
          <p className="mt-6 text-sm leading-relaxed text-subtle">
            Straight answers to what coaches ask us most. If yours isn&rsquo;t
            here, email{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-primary transition-colors hover:text-wave"
            >
              {CONTACT_EMAIL}
            </a>{" "}
            and we&rsquo;ll answer it.
          </p>

          <Faq q="What does Swimnetics measure that a stopwatch doesn't?">
            <p>
              A stopwatch tells you how fast. It doesn&rsquo;t tell you why. Two
              swimmers can post the identical split &mdash; one held a steady
              stroke the whole way, the other faded badly in the back half and
              made it up on a strong finish. Same time, completely different
              swimmer, completely different thing you&rsquo;d coach.
            </p>
            <p>
              Swimnetics gives you the &ldquo;why&rdquo; for every lap: stroke
              rate, a fatigue index showing exactly when and how much a swimmer
              slows, stroke-to-stroke consistency, distance-per-stroke, and the
              full velocity profile of each stroke &mdash; not just the final
              time.
            </p>
          </Faq>

          <Faq q="Do I need to understand data analysis to use it?">
            <p>
              No. You won&rsquo;t open a spreadsheet. Results show up on your
              phone in plain English and simple visuals &mdash; you read them
              the same way you read a split. The device points the flashlight at
              the right spot; the coaching is still yours.
            </p>
          </Faq>

          <Faq q="Does this replace me as a coach?">
            <p>
              No &mdash; and it isn&rsquo;t meant to. It&rsquo;s a second set of
              eyes that hands you the numbers you&rsquo;d otherwise have to
              guess at. When the data flags that a stroke broke down, you can
              review the footage and decide for yourself what it means. You make
              the call; you just make it with evidence instead of a hunch.
            </p>
          </Faq>

          <Faq q="How does it fit into practice without eating up pool time?">
            <p>
              Dedicate one lane to testing while your other lanes practice as
              normal, and send swimmers through a few trials each. How often you
              test &mdash; per day or per week &mdash; is entirely up to you. If
              you want more throughput, a second device doubles it.
            </p>
          </Faq>

          <Faq q="How durable is it? Will it survive a pool deck?">
            <p>
              The casing is PETG &mdash; resistant to pool chemicals, UV, and
              physical knocks &mdash; and sealed to be splashproof. The tether is
              UHMWPE, roughly 15&times; stronger than steel by weight, with a
              breakaway mechanism in case it ever snags. A spare tether ships in
              the box, though you likely won&rsquo;t need it.
            </p>
          </Faq>

          <Faq q="Which strokes are supported?">
            <p>
              Breaststroke is fully validated today. Freestyle and the other
              strokes are supported at an early quality level and are actively
              improving &mdash; we&rsquo;ll tell you plainly when a metric
              isn&rsquo;t yet reliable for a given stroke rather than dress it up
              as something it isn&rsquo;t.
            </p>
          </Faq>

          <Faq q="How much does it cost?">
            <p>
              <span className="text-ink">$300 one-time for the device</span>,
              which gives you the core stroke-level metrics. One shared unit
              covers a whole lane &mdash; you don&rsquo;t buy one per swimmer.
            </p>
            <p>
              An optional{" "}
              <span className="text-ink">$20 / swimmer / month cloud tier</span>{" "}
              adds video storage, long-term progress tracking, full session
              history, and shareable parent progress reports. The device&rsquo;s
              core metrics work without it.
            </p>
          </Faq>

          <Faq q="Is my swimmers' data safe — especially for minors?">
            <p>
              Yes. We don&rsquo;t sell personal information or use it for
              advertising. The swim club is our customer and holds the
              relationship with families; coaches manage athlete records on the
              club&rsquo;s behalf, and parental consent is handled through the
              club&rsquo;s normal registration. Full details are in our{" "}
              <Link
                href="/privacy"
                className="text-primary transition-colors hover:text-wave"
              >
                Privacy Policy
              </Link>
              .
            </p>
          </Faq>

          <section className="mt-12 rounded-2xl border border-navy bg-surface p-8">
            <h2 className="text-xl font-semibold text-ink">
              Still have questions?
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-subtle">
              We&rsquo;re onboarding a small number of programs first. Reach out
              and we&rsquo;ll get back to you.
            </p>
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=Early%20access%20to%20Swimnetics`}
              className="mt-6 inline-block rounded-lg bg-primary px-6 py-3 font-semibold text-white transition-colors hover:bg-accent"
            >
              Get early access
            </a>
          </section>

          <p className="mt-10">
            <Link
              href="/"
              className="text-sm text-muted transition-colors hover:text-ink"
            >
              &larr; Back to home
            </Link>
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
