import type { DeliveryReadinessData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

export function ReadinessScoreCard({ readiness }: { readiness: DeliveryReadinessData | null }) {
  const score = Math.max(0, Math.min(100, readiness?.overall_score ?? 0));
  const circumference = 2 * Math.PI * 42;
  const offset = circumference - (score / 100) * circumference;

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p
            className="text-[0.68rem] uppercase tracking-[0.22em] text-cyan-100/70"
            title="Client Readiness is a delivery checklist metric from the shared dashboard readiness state."
          >
            Client Readiness
          </p>
          <h3 className="mt-1 text-xl font-black text-white">Client Acceptance</h3>
        </div>
        <StatusBadge label={score >= 85 ? "Demo Ready" : "Review"} tone={score >= 85 ? "good" : "warning"} />
      </div>
      <div className="mt-6 flex items-center justify-center">
        <div className="relative h-36 w-36">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" fill="none" r="42" stroke="rgba(148,163,184,0.18)" strokeWidth="10" />
            <circle
              cx="60"
              cy="60"
              fill="none"
              r="42"
              stroke="url(#readinessGradient)"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              strokeWidth="10"
            />
            <defs>
              <linearGradient id="readinessGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#2dd4bf" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <strong className="text-4xl font-black text-white">{score}</strong>
            <span className="text-[0.65rem] uppercase tracking-[0.18em] text-slate-400">Percent</span>
          </div>
        </div>
      </div>
    </section>
  );
}
