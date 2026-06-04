import type { StrategyOverview } from "@/lib/strategyAnalyticsApi";

export function StrategyOverviewCards({ overview }: { overview: StrategyOverview }) {
  const cards = [
    ["Total Strategies", overview.total_strategies],
    ["Avg Analysis Confidence", `${Number(overview.avg_confidence || 0).toFixed(2)}%`],
    ["Avg Demo Risk Efficiency", `${Number(overview.avg_risk_efficiency || 0).toFixed(2)}%`],
    ["Avg Demo Execution Efficiency", `${Number(overview.avg_execution_efficiency || 0).toFixed(2)}%`],
    ["Top Ranked Strategy", overview.top_ranked_strategy || "Pending"],
    ["Demo Session Efficiency", `${Number(overview.session_efficiency || 0).toFixed(2)}%`],
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      {cards.map(([label, value]) => (
        <article className="min-h-28 rounded-2xl border border-white/10 bg-slate-950/45 p-4 shadow-xl shadow-black/15" key={label}>
          <p className="text-[0.64rem] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <strong className="mt-3 block break-words text-xl font-black text-white">{value}</strong>
          <p className="mt-2 break-words text-xs leading-5 text-slate-400">Source: /client-analytics/strategy/overview</p>
        </article>
      ))}
    </div>
  );
}
