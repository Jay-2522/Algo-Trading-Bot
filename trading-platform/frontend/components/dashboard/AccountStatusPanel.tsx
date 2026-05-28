import { StatusBadge } from "./StatusBadge";

const accounts = [
  { id: "STARTRADER_DEMO_1", broker: "STARTRADER" },
  { id: "FXPRO_DEMO_1", broker: "FXPRO" },
  { id: "VANTAGE_DEMO_1", broker: "VANTAGE" },
];

function readNumber(status: Record<string, unknown> | null, key: string): number | null {
  const value = status?.[key];
  return typeof value === "number" ? value : null;
}

export function AccountStatusPanel({ status }: { status: Record<string, unknown> | null }) {
  const enabledAccounts = readNumber(status, "enabled_accounts");

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Account Routing</p>
          <h2 className="mt-1 text-xl font-bold text-white">Account Status</h2>
        </div>
        <StatusBadge label={`${enabledAccounts ?? 3} enabled`} tone="good" />
      </div>

      <div className="mt-5 grid gap-3">
        {accounts.map((account) => (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" key={account.id}>
            <div className="flex items-center justify-between gap-3">
              <div>
                <strong className="block text-sm text-slate-100">{account.id}</strong>
                <span className="text-xs text-slate-500">{account.broker} / DEMO READ-ONLY</span>
              </div>
              <StatusBadge label="Ready" tone="good" />
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-[0.72rem]">
              <span className="rounded-full bg-slate-800 px-2.5 py-1 text-slate-300">Enabled</span>
              <span className="rounded-full bg-slate-800 px-2.5 py-1 text-slate-300">Allocation ready</span>
              <span className="rounded-full bg-emerald-400/10 px-2.5 py-1 text-emerald-200">Live disabled</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
