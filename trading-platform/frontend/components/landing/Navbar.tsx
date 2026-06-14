"use client";

import { useEffect, useState } from "react";

export function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header className={`landing-nav ${scrolled ? "scrolled" : ""}`}>
      <div className="landing-nav-inner" />
    </header>
  );
}
