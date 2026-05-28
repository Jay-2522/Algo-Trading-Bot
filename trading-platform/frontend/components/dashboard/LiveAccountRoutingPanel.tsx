import { StatusBadge } from "./StatusBadge";

function numberValue(source: Record<string, unknown> | null, key: string, fallback = 0): number {
  const value = source?.[key];
  return typeof value === "number" ? value : fallback;
}

export function LiveAccountRoutingPanel({
  accountStatus,
  allocationStatus,
}: {
  accountStatus: Record<string, unknown> | null;
  allocationStatus: Record<string, unknown> | null;
}) {
  const enabledAccounts = numberValue(accountStatus, "enabled_accounts", 3);
  const profiles = numberValue(allocationStatus, "profiles", enabledAccounts);

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Live Account Routing</p>
          <h2 className="mt-1 text-lg font-bold text-white">Routing & Allocation</h2>
        </div>
        <StatusBadge label="Preview Only" tone="good" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-xs text-slate-500">Enabled accounts</p>
          <strong className="mt-1 block text-2xl text-white">{enabledAccounts}</strong>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-xs text-slate-500">Risk profiles</p>
          <strong className="mt-1 block text-2xl text-white">{profiles}</strong>
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-amber-100/80">NIFTY50 remains conservative until Indian broker integration is active.</p>
    </section>
  );
}
