import type { StrategyPerformanceSummary } from "@/lib/strategyAnalyticsApi";

export function StrategyComparisonGrid({ strategies }: { strategies: StrategyPerformanceSummary[] }) {
  return (
    <section className="grid gap-3 lg:grid-cols-3">
      {strategies.map((strategy) => {
        const nifty = strategy.symbol === "NIFTY50";
        return (
          <article className="rounded-2xl border border-white/10 bg-white/[0.04] p-4" key={strategy.symbol}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="text-xl font-black text-white">{strategy.symbol}</h3>
              <span className={`rounded-full border px-2.5 py-1 text-[0.56rem] font-black uppercase tracking-[0.1em] ${nifty ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100" : "border-cyan-300/20 bg-cyan-300/10 text-cyan-100"}`}>
                {nifty ? "SMC INTELLIGENCE READY" : "ACTIVE ANALYTICS"}
              </span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {[
                ["Demo Signals", strategy.total_signals],
                ["Analysis Confidence", strategy.confidence_quality],
                ["Demo Execution", strategy.execution_quality],
                ["Demo Risk", strategy.risk_quality],
                ["Derived Score", Number(strategy.strategy_score || 0).toFixed(2)],
              ].map(([label, value]) => (
                <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3" key={label}>
                  <p className="text-[0.6rem] uppercase tracking-[0.11em] text-slate-500">{label}</p>
                  <strong className="mt-1 block break-words text-sm text-slate-100">{value}</strong>
                </div>
              ))}
            </div>
          </article>
        );
      })}
    </section>
  );
}
