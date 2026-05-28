import { readText } from "@/lib/dashboard-formatters";

import { StatusBadge } from "./StatusBadge";

function readNumber(source: Record<string, unknown> | null | undefined, key: string): number {
  const value = source?.[key];
  return typeof value === "number" ? value : 0;
}

export function SimulatedPnlPanel({ pnl }: { pnl: Record<string, unknown> | null }) {
  const metrics = [
    ["Realized", readNumber(pnl, "realized_pnl")],
    ["Floating", readNumber(pnl, "floating_pnl")],
    ["Net", readNumber(pnl, "net_pnl")],
  ];

  return (
    <section className="min-w-0 rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-emerald-100/70">Simulated P&L</p>
          <h3 className="mt-1 break-words text-xl font-black text-white">Placeholder Analytics</h3>
        </div>
        <StatusBadge label="No live P&L" tone="good" />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        {metrics.map(([label, value]) => (
          <div className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/35 p-3 text-center" key={label}>
            <strong className="block break-words text-lg text-white">{Number(value).toFixed(2)}</strong>
            <span className="text-[0.65rem] uppercase tracking-[0.12em] text-slate-500">{label}</span>
          </div>
        ))}
      </div>

      <p className="mt-4 break-words text-sm leading-6 text-emerald-50/75">
        {readText(pnl, ["message"], "No live broker P&L is tracked. Simulated P&L will populate from future demo lifecycle analytics.")}
      </p>
    </section>
  );
}
