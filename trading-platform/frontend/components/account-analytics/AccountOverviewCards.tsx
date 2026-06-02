import type { AccountAnalyticsSummary, AccountSyncStatus } from "@/lib/accountAnalyticsApi";

function lastSync(value: string | null): string {
  if (!value) return "Pending";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export function AccountOverviewCards({ accounts, sync }: { accounts: AccountAnalyticsSummary[]; sync: AccountSyncStatus }) {
  const activeCopiers = accounts.filter((account) => account.account_type === "COPIER").length;
  const totalExecutions = accounts.reduce((sum, account) => sum + account.total_executions, 0);
  const totalCopiedTrades = accounts.reduce((sum, account) => sum + account.total_copied_trades, 0);
  const cards = [
    ["Total Accounts", accounts.length],
    ["Active Copiers", activeCopiers],
    ["Sync Status", sync.synchronization_status],
    ["Last Sync", lastSync(sync.last_sync_time)],
    ["Total Executions", totalExecutions],
    ["Total Copied Trades", totalCopiedTrades],
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      {cards.map(([label, value]) => (
        <article className="min-h-28 rounded-2xl border border-white/10 bg-slate-950/45 p-4 shadow-xl shadow-black/15" key={label}>
          <p className="text-[0.64rem] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <strong className="mt-3 block break-words text-xl font-black text-white">{value}</strong>
        </article>
      ))}
    </div>
  );
}
