import type { OperationalHealthSummaryData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

export function SystemHealthScore({ summary }: { summary: OperationalHealthSummaryData | null }) {
  const score = Math.max(0, Math.min(100, summary?.health_score ?? 0));
  const circumference = 2 * Math.PI * 44;
  const offset = circumference - (score / 100) * circumference;

  return (
    <section className="min-w-0 rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p
            className="text-[0.68rem] uppercase tracking-[0.22em] text-cyan-100/70"
            title="Operational Health uses the shared platform health score from DashboardStateProvider."
          >
            Operational Health
          </p>
          <h3 className="mt-1 break-words text-xl font-black text-white">Operational Status</h3>
        </div>
        <StatusBadge label={summary?.overall_status ?? "Loading"} tone={score >= 90 ? "good" : score >= 70 ? "warning" : "danger"} />
      </div>

      <div className="mt-6 flex items-center justify-center">
        <div className="relative h-36 w-36">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
            <circle cx="60" cy="60" fill="none" r="44" stroke="rgba(148,163,184,0.18)" strokeWidth="10" />
            <circle
              cx="60"
              cy="60"
              fill="none"
              r="44"
              stroke="url(#healthGradient)"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              strokeWidth="10"
            />
            <defs>
              <linearGradient id="healthGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <strong className="text-4xl font-black text-white">{score}</strong>
            <span className="text-[0.65rem] uppercase tracking-[0.18em] text-slate-400">Score</span>
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2 text-center">
        {[
          ["Modules", summary?.monitored_modules ?? 0],
          ["Warnings", summary?.active_warnings ?? 0],
          ["Alerts", summary?.active_alerts ?? 0],
        ].map(([label, value]) => (
          <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3" key={label}>
            <strong className="block text-lg text-white">{value}</strong>
            <span className="text-[0.65rem] uppercase tracking-[0.12em] text-slate-500">{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
