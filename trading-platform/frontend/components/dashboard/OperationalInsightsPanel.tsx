import type { OperationalHealthSummaryData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

export function OperationalInsightsPanel({ summary }: { summary: OperationalHealthSummaryData | null }) {
  const insights = [
    "System monitoring is active across broker, webhook, queue, control, portfolio, and dashboard layers.",
    "Simulation pipeline is ready for client observation and demo walkthroughs.",
    "Broker execution remains disabled across all operational views.",
    "NIFTY50 remains blocked pending Indian broker integration.",
  ];

  return (
    <section className="min-w-0 rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-emerald-100/70">Operational Insights</p>
          <h3 className="mt-1 break-words text-xl font-black text-white">Executive Safety Posture</h3>
        </div>
        <StatusBadge label={summary?.live_execution_enabled ? "Review" : "Live Disabled"} tone={summary?.live_execution_enabled ? "danger" : "good"} />
      </div>
      <ul className="mt-4 space-y-3">
        {insights.map((insight) => (
          <li className="flex min-w-0 gap-3 text-sm leading-6 text-emerald-50/80" key={insight}>
            <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-emerald-300 shadow-lg shadow-emerald-300/30" />
            <span className="break-words">{insight}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
