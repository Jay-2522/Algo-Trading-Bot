import type { AccountAnalyticsSummary } from "@/lib/accountAnalyticsApi";

function money(value: number): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function AccountPerformanceGrid({ accounts }: { accounts: AccountAnalyticsSummary[] }) {
  return (
    <section className="grid gap-3 lg:grid-cols-4">
      {accounts.map((account) => (
        <article className="rounded-2xl border border-white/10 bg-white/[0.04] p-4" key={account.account_id}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-[0.64rem] font-bold uppercase tracking-[0.14em] text-slate-500">{account.account_type}</p>
              <h3 className="mt-1 text-lg font-black text-white">{account.account_name}</h3>
            </div>
            <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[0.56rem] font-black uppercase tracking-[0.1em] text-cyan-100">
              {account.synchronization_status}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {[
              ["Executions", account.total_executions],
              ["Copied", account.total_copied_trades],
              ["Win Rate", `${Number(account.win_rate || 0).toFixed(2)}%`],
              ["Net P&L", money(account.net_pnl)],
              ["Drawdown", money(account.max_drawdown)],
              ["Live", account.live_execution_enabled ? "Enabled" : "Disabled"],
            ].map(([label, value]) => (
              <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3" key={label}>
                <p className="text-[0.6rem] uppercase tracking-[0.11em] text-slate-500">{label}</p>
                <strong className="mt-1 block break-words text-sm text-slate-100">{value}</strong>
              </div>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}
