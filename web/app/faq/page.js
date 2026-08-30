import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import ContactDialog from "@/components/marketing/ContactDialog";

export const metadata = {
  title: "FAQ | Swimnetics",
  description:
    "Answers for coaches: what Swimnetics measures, how it fits into practice, durability, pricing, and how swimmer data is protected.",
};

const CONTACT_EMAIL = "info@swimnetics.com";

function Faq({ q, children }) {
  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold text-ink-900">{q}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-ink-600">
        {children}
      </div>
    </section>
  );
}

export default function FAQ() {
  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink-900">
      <Nav />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-5 py-16">
          <h1 className="text-3xl font-bold tracking-tight text-ink-900">
            Frequently asked questions
          </h1>
          <p className="mt-6 text-sm leading-relaxed text-ink-600">
            Straight answers to what coaches ask us most. If yours isn&rsquo;t
            here, email{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-brand transition-colors hover:text-brand-pressed"
            >
              {CONTACT_EMAIL}
            </a>{" "}
            and we&rsquo;ll answer it.
          </p>

          <Faq q="What does Swimnetics measure that a stopwatch doesn't?">
            <p>
              A stopwatch tells you how fast. It doesn&rsquo;t tell you why. Two
              swimmers can post the identical split when one held a steady stroke
              the whole way and the other faded badly in the back half, then made
              it up on a strong finish. Same time, completely different swimmer,
              completely different thing you&rsquo;d coach.
            </p>
            <p>
              Swimnetics gives you the &ldquo;why&rdquo; for every lap. The swim
              comes back split into the start, the underwater and the swimming,
              each part scored on its own: how hard the push off was, what every
              dolphin kick bought, how far each stroke carried, where the speed
              went, and the full velocity profile behind all of it.
            </p>
          </Faq>

          <Faq q="Do I need to understand data analysis to use it?">
            <p>
              No. You won&rsquo;t open a spreadsheet. Results show up on your
              phone in plain English and simple visuals, read the same way you
              read a split. The card opens by telling you how many things moved
              outside this swimmer&rsquo;s usual range and which way they went.
              The device points the flashlight at the right spot; the coaching is
              still yours.
            </p>
          </Faq>

          <Faq q="Does this replace me as a coach?">
            <p>
              No, and it isn&rsquo;t meant to. It&rsquo;s a second set of eyes
              that hands you the numbers you&rsquo;d otherwise have to guess at.
              When the data flags that a stroke broke down, you can review the
              footage and decide for yourself what it means. You make the call;
              you just make it with evidence instead of a hunch.
            </p>
          </Faq>

          <Faq q="How does it fit into practice without eating up pool time?">
            <p>
              Dedicate one lane to testing while your other lanes practice as
              normal, and send swimmers through a few trials each. How often you
              test, per day or per week, is entirely up to you. If you want more
              throughput, a second device doubles it.
            </p>
          </Faq>

          <Faq q="How durable is it? Will it survive a pool deck?">
            <p>
              It is built for a wet deck: sealed to be splashproof, and made to
              live in chlorine and sun without going brittle or fading. It takes
              the knocks that come with being clamped to a starting block all
              season.
            </p>
            <p>
              The tether holds on a breakaway magnet and lets go if it ever
              snags, so the swimmer is never tied to the block. A spare tether
              ships in the box, though you likely won&rsquo;t need it.
            </p>
          </Faq>

          <Faq q="How much does it cost?">
            <p>
              Pricing is tailored to your program. It depends on your roster
              size and whether you want the optional cloud features. One shared
              unit covers a whole lane, so you don&rsquo;t buy one per swimmer.
            </p>
            <p>
              Tell us a bit about your team and we&rsquo;ll put together a quote
              that fits.
            </p>
          </Faq>

          <Faq q="Is my swimmers' data safe, especially for minors?">
            <p>
              Yes. We don&rsquo;t sell personal information or use it for
              advertising. The swim club is our customer and holds the
              relationship with families; coaches manage athlete records on the
              club&rsquo;s behalf, and parental consent is handled through the
              club&rsquo;s normal registration. Full details are in our{" "}
              <Link
                href="/privacy"
                className="text-brand transition-colors hover:text-brand-pressed"
              >
                Privacy Policy
              </Link>
              .
            </p>
          </Faq>

          <section className="mt-12 rounded-2xl border border-line bg-card p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-ink-900">
              Still have questions?
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-600">
              We&rsquo;re onboarding a small number of programs first. Reach out
              and we&rsquo;ll get back to you.
            </p>
            <div className="mt-6">
              <ContactDialog label="Request a quote" size="lg" />
            </div>
          </section>

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
