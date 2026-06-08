import type { ClientAnalyticsOverview, DemoPositionsSummary } from "@/lib/clientAnalyticsApi";

function formatNumber(value: number): string {
  return Number(value || 0).toLocaleString();
}

function formatPercent(value: number): string {
  return `${Number(value || 0).toFixed(2)}%`;
}

function formatMoney(value: number): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function AnalyticsOverviewCards({ overview, demoPositions }: { overview: ClientAnalyticsOverview; demoPositions: DemoPositionsSummary }) {
  const cards = [
    ["Demo Signals", formatNumber(overview.total_signals), "Source: /client-analytics/overview"],
    ["Demo Executions", formatNumber(overview.total_demo_executions), overview.total_demo_executions ? "Recorded demo activity only" : "No completed demo trades yet"],
    ["Open Demo Positions", formatNumber(demoPositions.open_positions), "Source: /client-analytics/demo-positions/summary"],
    ["Floating Demo P&L", formatMoney(demoPositions.total_floating_pnl), "Real MT5 demo floating P&L only"],
    ["Lifecycle Status", `${demoPositions.lifecycle_open_count} open / ${demoPositions.lifecycle_closed_count} closed`, "Derived from MT5 demo lifecycle journal"],
    ["Demo Copy Batches", formatNumber(overview.total_copy_batches), "Recorded copier batches only"],
    ["Risk Blocks", formatNumber(overview.total_risk_blocks), "Derived risk engine events"],
    ["News Blocks", formatNumber(overview.total_news_blocks), "Derived news filter events"],
    ["Demo Win Rate", formatPercent(overview.win_rate), "Calculated from completed demo P&L only"],
    ["Demo Net P&L", formatMoney(overview.net_pnl), "Recorded demo P&L only"],
    ["Demo Max Drawdown", formatMoney(overview.max_drawdown), "Recorded demo drawdown only"],
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
