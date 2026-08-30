import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import Hero from "@/components/marketing/Hero";
import PhaseStory from "@/components/marketing/PhaseStory";
import UsualRange from "@/components/marketing/UsualRange";
import CyclePack from "@/components/marketing/CyclePack";
import VideoSync from "@/components/marketing/VideoSync";
import Device from "@/components/marketing/Device";
import HowItWorks from "@/components/marketing/HowItWorks";
import RequestQuote from "@/components/marketing/RequestQuote";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink-900">
      <Nav overHero />
      {/* Pull the hero up under the transparent sticky nav so the gradient
          sits behind it (nav height = h-16 = 64px). */}
      <main className="-mt-16 flex-1">
        <Hero />
        <PhaseStory />
        <UsualRange />
        <CyclePack />
        <VideoSync />
        <Device />
        <HowItWorks />
        <RequestQuote />
      </main>
      <Footer />
    </div>
  );
}
