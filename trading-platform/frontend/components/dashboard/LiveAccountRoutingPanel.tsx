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
    <section className="min-h-64 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Live Account Routing</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">Routing & Allocation</h2>
        </div>
        <StatusBadge label="Preview Only" tone="good" />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="break-words text-xs leading-relaxed text-slate-500">Enabled accounts</p>
          <strong className="mt-1 block break-words text-2xl leading-tight text-white">{enabledAccounts}</strong>
        </div>
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="break-words text-xs leading-relaxed text-slate-500">Risk profiles</p>
          <strong className="mt-1 block break-words text-2xl leading-tight text-white">{profiles}</strong>
        </div>
      </div>
      <p className="mt-3 break-words text-xs leading-relaxed text-amber-100/80">NIFTY50 remains conservative until Indian broker integration is active.</p>
    </section>
  );
}
