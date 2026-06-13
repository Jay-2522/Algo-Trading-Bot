"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const stats = [
  { label: "Active Traders", value: "10K+" },
  { label: "Volume Traded", value: "$2.4B+" },
  { label: "Uptime", value: "99.9%" },
];

export function HeroContent() {
  const router = useRouter();
  const [exiting, setExiting] = useState(false);

  const navigateToDashboard = () => {
    setExiting(true);
    window.setTimeout(() => router.push("/dashboard"), 300);
  };

  return (
    <section className={`hero-content ${exiting ? "page-exit" : ""}`}>
      <div className="eyebrow-badge anim-fade-down" style={{ animationDelay: "200ms" }}>
        <span aria-hidden="true" className="badge-icon">
          ⚡
        </span>
        <span>AI-Powered Trading</span>
      </div>

      <h1 className="hero-headline anim-fade-up" style={{ animationDelay: "400ms" }}>
        AlgoPilot
        <br />
        Trade Intelligence
      </h1>

      <p className="hero-sub anim-fade" style={{ animationDelay: "600ms" }}>
        Deploy guarded AI strategies across forex, metals, and index markets with a dashboard built for real execution oversight.
        Track signals, risk, and approvals in one calm control center.
      </p>

      <button className="cta-primary anim-scale-in" onClick={navigateToDashboard} style={{ animationDelay: "800ms" }} type="button">
        Get Started <span className="cta-arrow">→</span>
      </button>

      <div className="hero-stats anim-fade" style={{ animationDelay: "1000ms" }}>
        {stats.map((stat, index) => (
          <div className="stat-cluster" key={stat.label}>
            {index > 0 ? <div className="stat-divider" /> : null}
            <div className="stat">
              <span className="stat-value">{stat.value}</span>
              <span className="stat-label">{stat.label}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
