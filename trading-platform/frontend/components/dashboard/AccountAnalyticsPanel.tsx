import type { PortfolioAccountSummaryData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

function tone(account: PortfolioAccountSummaryData): "good" | "warning" | "muted" {
  if (!account.enabled) return "muted";
  if (account.risk_status === "READY") return "good";
  return "warning";
}

function formatMoney(value: number): string {
  return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function AccountAnalyticsPanel({ accounts }: { accounts: PortfolioAccountSummaryData[] }) {
  return (
    <section className="min-w-0 rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Account Analytics</p>
          <h3 className="mt-1 break-words text-xl font-black text-white">Simulated Account Cards</h3>
        </div>
        <StatusBadge label={`${accounts.filter((account) => account.enabled).length} enabled`} tone="good" />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
        {accounts.length ? (
          accounts.map((account) => (
            <div className="min-w-0 rounded-3xl border border-white/10 bg-white/[0.035] p-4" key={account.account_id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <strong className="block truncate text-sm text-white" title={account.account_id}>
                    {account.account_id}
                  </strong>
                  <p className="mt-1 break-words text-xs leading-5 text-slate-500">{account.broker_id} / {account.account_mode}</p>
                </div>
                <StatusBadge label={account.enabled ? account.risk_status : "COMING SOON"} tone={tone(account)} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3">
                  <p className="text-[0.65rem] uppercase tracking-[0.14em] text-slate-500">Simulated Balance</p>
                  <strong className="mt-1 block text-sm text-white">{formatMoney(account.balance)}</strong>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3">
                  <p className="text-[0.65rem] uppercase tracking-[0.14em] text-slate-500">Simulated Equity</p>
                  <strong className="mt-1 block text-sm text-white">{formatMoney(account.equity)}</strong>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {account.supported_symbols.map((symbol) => (
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-1 text-[0.65rem] font-bold text-slate-300" key={symbol}>
                    {symbol}
                  </span>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
            Account analytics are loading.
          </div>
        )}
      </div>
    </section>
  );
}
