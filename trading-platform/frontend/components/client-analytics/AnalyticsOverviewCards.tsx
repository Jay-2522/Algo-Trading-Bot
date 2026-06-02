import type { ClientAnalyticsOverview } from "@/lib/clientAnalyticsApi";

function formatNumber(value: number): string {
  return Number(value || 0).toLocaleString();
}

function formatPercent(value: number): string {
  return `${Number(value || 0).toFixed(2)}%`;
}

function formatMoney(value: number): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function AnalyticsOverviewCards({ overview }: { overview: ClientAnalyticsOverview }) {
  const cards = [
    ["Total Signals", formatNumber(overview.total_signals), "Strategy ideas observed"],
    ["Demo Executions", formatNumber(overview.total_demo_executions), overview.total_demo_executions ? "Demo activity only" : "No completed demo trades yet"],
    ["Copy Batches", formatNumber(overview.total_copy_batches), "Trade copier batches"],
    ["Risk Blocks", formatNumber(overview.total_risk_blocks), "Capital protection events"],
    ["News Blocks", formatNumber(overview.total_news_blocks), "News filter blocks"],
    ["Win Rate", formatPercent(overview.win_rate), "Calculated from real PnL only"],
    ["Net P&L", formatMoney(overview.net_pnl), "No fake profit display"],
    ["Max Drawdown", formatMoney(overview.max_drawdown), "Observed drawdown"],
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(([label, value, detail]) => (
        <article
          className="min-h-32 rounded-2xl border border-white/10 bg-slate-950/45 p-4 shadow-xl shadow-black/15 transition hover:border-cyan-200/25 hover:bg-cyan-300/[0.055]"
          key={label}
        >
          <p className="break-words text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
          <strong className="mt-3 block break-words text-2xl font-black leading-tight text-white">{value}</strong>
          <p className="mt-2 break-words text-xs leading-5 text-slate-400">{detail}</p>
        </article>
      ))}
    </div>
  );
}
