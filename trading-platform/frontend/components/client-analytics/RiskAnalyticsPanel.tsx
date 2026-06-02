import type { RiskAnalyticsSummary } from "@/lib/clientAnalyticsApi";

export function RiskAnalyticsPanel({ risk }: { risk: RiskAnalyticsSummary }) {
  const empty = risk.total_risk_checks === 0 && risk.blocked === 0 && risk.news_blocks === 0;
  const metrics = [
    ["Total Risk Checks", risk.total_risk_checks],
    ["Approved", risk.approved],
    ["Blocked", risk.blocked],
    ["News Blocks", risk.news_blocks],
    ["Regime Blocks", risk.regime_blocks],
    ["Risk Engine Blocks", risk.risk_engine_blocks],
  ];

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Risk Analytics</p>
          <h3 className="mt-1 text-xl font-black text-white">Protection Decisions</h3>
        </div>
        <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-[0.6rem] font-black uppercase tracking-[0.12em] text-emerald-100">
          Live Disabled
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {metrics.map(([label, value]) => (
          <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3" key={label}>
            <p className="break-words text-[0.62rem] uppercase tracking-[0.12em] text-slate-500">{label}</p>
            <strong className="mt-1 block break-words text-lg text-white">{value}</strong>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded-xl border border-white/10 bg-slate-950/35 p-3">
        <p className="text-[0.62rem] uppercase tracking-[0.12em] text-slate-500">Most Common Block Reason</p>
        <strong className="mt-1 block break-words text-sm text-slate-100">
          {risk.most_common_block_reason || "No block reason recorded yet"}
        </strong>
      </div>

      {empty ? (
        <p className="mt-3 rounded-xl border border-dashed border-slate-700 bg-white/[0.03] p-3 text-sm leading-6 text-slate-400">
          Risk analytics will populate after strategy and execution activity.
        </p>
      ) : null}
    </section>
  );
}
