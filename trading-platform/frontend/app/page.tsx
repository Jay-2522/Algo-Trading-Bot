import { HeroBackground } from "@/components/landing/HeroBackground";
import { HeroContent } from "@/components/landing/HeroContent";
import { LandingNavbar } from "@/components/landing/Navbar";

export default function LandingPage() {
  return (
    <main className="landing-page" id="landing-page">
      <HeroBackground />
      <LandingNavbar />
      <HeroContent />
    </main>
  );
}
