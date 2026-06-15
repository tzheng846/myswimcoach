import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

export const metadata = {
  title: "Privacy Policy — Swimnetics",
  description:
    "How Swimnetics collects, uses, stores, and protects swim performance data — including data about minors — and the rights of coaches, swimmers, and parents.",
};

const LAST_UPDATED = "June 14, 2026";
const CONTACT_EMAIL = "info@swimnetics.com";

function Section({ id, title, children }) {
  return (
    <section id={id} className="mt-10 scroll-mt-24">
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-subtle">
        {children}
      </div>
    </section>
  );
}

function Ext({ href, children }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary transition-colors hover:text-wave"
    >
      {children}
    </a>
  );
}

export default function PrivacyPolicy() {
  return (
    <>
      <Nav />
      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-5 py-16">
          <h1 className="text-3xl font-bold tracking-tight text-ink">
            Privacy Policy
          </h1>
          <p className="mt-3 text-sm text-muted">Last updated: {LAST_UPDATED}</p>

          <p className="mt-6 text-sm leading-relaxed text-subtle">
            This policy explains what information Swimnetics collects, how we use
            it, and the choices and rights available to coaches, swimmers, and
            parents. Swimnetics provides biomechanical swim-coaching tools: a
            tethered magnetic encoder measures a swimmer&rsquo;s velocity, and our
            software turns that signal into stroke-level performance metrics for
            coaches.
          </p>

          <Section id="who-we-are" title="1. Who we are and who controls the data">
            <p>
              Swimnetics (&ldquo;we,&rdquo; &ldquo;us&rdquo;) is the operator of
              the Swimnetics app, website, and backend services. Our customer is
              the swim club, academy, or program (the &ldquo;club&rdquo;) and the
              coaches who hold accounts with us.
            </p>
            <p>
              Coaches create and manage athlete records on behalf of their club.
              Swimmers (athletes) are recorded in the system by their coach and
              generally do not create their own logins or interact with Swimnetics
              directly. Because athletes are often minors, the relationship
              between the club and the swimmer&rsquo;s family is central to how
              consent works &mdash; see the Minors section below.
            </p>
          </Section>

          <Section id="what-we-collect" title="2. Information we collect">
            <p>We collect only what we need to provide the service:</p>
            <ul className="ml-5 list-disc space-y-2">
              <li>
                <span className="text-ink">Account information.</span> The
                coach&rsquo;s or club&rsquo;s email address and name, used to
                create and secure the account (managed through our authentication
                provider).
              </li>
              <li>
                <span className="text-ink">Athlete records.</span> Information a
                coach enters about a swimmer: name, optional age or date of birth,
                a body-measurement value used to calibrate distance
                (head-to-waist length), and the swimmer&rsquo;s stroke type.
              </li>
              <li>
                <span className="text-ink">Performance data.</span> Metrics
                derived from a recorded swim, such as velocity, acceleration,
                stroke rate, distance-per-stroke, and per-cycle breakdowns.
              </li>
              <li>
                <span className="text-ink">Raw sensor data.</span> The raw
                measurement file produced by the encoder during a session, stored
                so sessions can be reprocessed.
              </li>
              <li>
                <span className="text-ink">Device data.</span> A hardware
                identifier for the encoder unit and session timestamps, used to
                associate sessions with the device that produced them.
              </li>
              <li>
                <span className="text-ink">Video (optional cloud tier only).</span>{" "}
                If a coach uses our optional cloud subscription, video a coach
                records of a swim can be uploaded and stored so it can be played
                back alongside the swim&rsquo;s metrics. Without the cloud tier,
                any video stays on the coach&rsquo;s own device and is not
                uploaded to or stored on our servers.
              </li>
            </ul>
          </Section>

          <Section id="how-we-use" title="3. How and why we use information">
            <p>
              We use the information above only to provide and improve the
              coaching service: processing recorded swims into metrics, showing
              results and history to the coach, and generating progress reports
              that a coach may choose to share with a swimmer&rsquo;s parents.
            </p>
            <p>
              <span className="text-ink">
                We do not sell personal information, we do not use it for
                advertising, and we do not build behavioral or marketing profiles
                of swimmers.
              </span>
            </p>
          </Section>

          <Section id="service-providers" title="4. Service providers">
            <p>
              We rely on a small number of infrastructure providers who process
              or store data on our behalf, under their own privacy commitments:
            </p>
            <ul className="ml-5 list-disc space-y-2">
              <li>
                <Ext href="https://supabase.com/privacy">Supabase</Ext> &mdash;
                database and file storage (account, athlete, session, and raw
                sensor data, and swim video where the optional cloud tier is
                used).
              </li>
              <li>
                <Ext href="https://railway.com/legal/privacy">Railway</Ext>{" "}
                &mdash; hosting for our processing API.
              </li>
              <li>
                <Ext href="https://stripe.com/privacy">Stripe</Ext> &mdash;
                payment and subscription processing, where billing is used.
              </li>
            </ul>
            <p>
              We share personal information with these providers only as needed to
              run the service, and not for their own independent purposes.
            </p>
          </Section>

          <Section id="parent-reports" title="5. Parent progress reports">
            <p>
              A coach can generate a swimmer progress report and share it with the
              swimmer&rsquo;s parent through a private link. These report pages do
              not require the parent to create an account, show the swimmer&rsquo;s
              first name only, and are not indexed by search engines. Reports are
              shared at the coach&rsquo;s direction.
            </p>
          </Section>

          <Section id="childrens-privacy" title="6. Minors and age requirement">
            <p>
              Swimnetics is currently intended for swimmers who are{" "}
              <span className="text-ink">13 years of age or older</span>. We do
              not knowingly collect personal information from children under 13.
              If we learn that a child under 13 has been added to the service, we
              will work with the relevant club to delete that information.
            </p>
            <p>
              Many swimmers are still minors (ages 13&ndash;17). The club and its
              coaches, as our customers and the parties with the direct
              relationship to families, are responsible for obtaining verifiable
              parental consent before adding a swimmer&rsquo;s information to
              Swimnetics &mdash; typically as part of the club&rsquo;s normal
              registration process. Where a club uses the optional cloud tier,
              the stored swim video may show a minor; that video is handled under
              the same club-consent model and the same protections as other
              athlete data.
            </p>
            <p>
              A parent or guardian may contact us at{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="text-primary transition-colors hover:text-wave"
              >
                {CONTACT_EMAIL}
              </a>{" "}
              to review the information we hold about their child, or to request
              that it be deleted. We will work with the relevant club to honor
              such requests.
            </p>
          </Section>

          <Section id="retention" title="7. Data retention and deletion">
            <p>
              We retain a swimmer&rsquo;s sessions for as long as the coaching
              relationship is active, so that progress can be tracked over time.
            </p>
            <p>
              When a coach deletes a session, both the stored session record and
              the associated raw sensor file are removed. A club or parent may
              also request deletion of an athlete&rsquo;s data by contacting us,
              after which we will delete it within a reasonable period unless we
              are required to retain it by law.
            </p>
          </Section>

          <Section id="security" title="8. Security">
            <p>
              We protect data in transit and at rest using industry-standard
              encryption, restrict access to authenticated accounts using
              token-based authentication, and use row-level security so each
              account can only access its own data. No system is perfectly secure,
              but we take reasonable measures appropriate to the sensitivity of the
              information.
            </p>
          </Section>

          <Section id="your-rights" title="9. Your privacy rights (California)">
            <p>
              California residents have the right to know what personal
              information we hold, to request access to it, to request its
              deletion, and to request that it be corrected. We do not sell or
              share personal information for cross-context behavioral advertising,
              and we do not discriminate against anyone for exercising their
              rights.
            </p>
            <p>
              To exercise any of these rights, contact us at{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="text-primary transition-colors hover:text-wave"
              >
                {CONTACT_EMAIL}
              </a>
              .
            </p>
          </Section>

          <Section id="changes" title="10. Changes and contact">
            <p>
              We may update this policy as the service evolves. When we do, we will
              revise the &ldquo;Last updated&rdquo; date above, and significant
              changes will be communicated to account holders.
            </p>
            <p>
              Questions about this policy or your data can be sent to{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="text-primary transition-colors hover:text-wave"
              >
                {CONTACT_EMAIL}
              </a>
              .
            </p>
            <p className="pt-2">
              <Link
                href="/"
                className="text-sm text-muted transition-colors hover:text-ink"
              >
                &larr; Back to home
              </Link>
            </p>
          </Section>
        </div>
      </main>
      <Footer />
    </>
  );
}
