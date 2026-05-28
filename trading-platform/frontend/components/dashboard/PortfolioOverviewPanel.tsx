import type { PortfolioOverviewData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

function formatMoney(value: number | undefined): string {
  return `$${Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function PortfolioOverviewPanel({ overview }: { overview: PortfolioOverviewData | null }) {
  const exposure = overview?.exposure_summary;
  const metrics = [
    ["Simulated Balance", formatMoney(exposure?.total_simulated_balance)],
    ["Simulated Equity", formatMoney(exposure?.total_simulated_equity)],
    ["Enabled Accounts", String(exposure?.enabled_accounts ?? 0)],
    ["Supported Symbols", String(exposure?.supported_symbols?.length ?? 0)],
  ];

  return (
    <section className="min-w-0 overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/60 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-teal-100/70">Portfolio & Account Analytics</p>
          <h2 className="mt-2 break-words text-3xl font-black leading-tight text-white">Simulated Portfolio Overview</h2>
          <p className="mt-3 max-w-4xl break-words text-sm leading-7 text-slate-300">
            Account readiness, simulated balances, exposure limits, and placeholder P&L are displayed for client review only.
          </p>
        </div>
        <StatusBadge label={overview?.portfolio_status ?? "Loading"} tone="good" />
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.045] p-4" key={label}>
            <p className="break-words text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <strong className="mt-2 block break-words text-2xl font-black leading-tight text-white">{value}</strong>
          </div>
        ))}
      </div>

      {overview?.warnings?.length ? (
        <div className="mt-4 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-3 text-sm leading-6 text-amber-100">
          {overview.warnings.join(" ")}
        </div>
      ) : null}
    </section>
  );
}
