import type { AccountAnalyticsSummary, AccountSyncStatus } from "@/lib/accountAnalyticsApi";

export function CopierSyncPanel({ accounts, sync }: { accounts: AccountAnalyticsSummary[]; sync: AccountSyncStatus }) {
  const copiers = accounts.filter((account) => account.account_type === "COPIER");
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Copier Sync</p>
          <h3 className="mt-1 text-xl font-black text-white">Synchronization Monitoring</h3>
        </div>
        <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[0.6rem] font-black uppercase tracking-[0.12em] text-cyan-100">
          {sync.synchronization_status}
        </span>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {copiers.map((account) => (
          <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3" key={account.account_id}>
            <strong className="block text-sm text-white">{account.account_name}</strong>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              Health: {account.synchronization_status} / copied {account.total_copied_trades} / executions {account.total_executions}
            </p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-400">
        Execution consistency: {sync.execution_consistency}. Account metrics remain zero until real demo copier records exist.
      </p>
    </section>
  );
}
