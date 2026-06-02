import type { ExecutiveSummary } from "@/lib/executiveDashboardApi";

export function ProductionReadinessPanel({ summary }: { summary: ExecutiveSummary }) {
  const flags = [
    ["simulation_only", summary.simulation_only],
    ["demo_execution", summary.demo_execution],
    ["live_execution_enabled", summary.live_execution_enabled],
    ["broker_execution_enabled", summary.broker_execution_enabled],
  ] as const;

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/45 p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">Production Readiness</p>
      <h3 className="mt-2 text-xl font-black text-white">Execution Safety State</h3>
      <div className="mt-4 grid gap-3">
        {flags.map(([label, value]) => (
          <div className="flex min-w-0 items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={label}>
            <span className="break-words text-sm font-bold text-slate-200">{label}</span>
            <span className={value ? "rounded-full bg-cyan-300/10 px-3 py-1 text-xs font-black text-cyan-100" : "rounded-full bg-amber-300/10 px-3 py-1 text-xs font-black text-amber-100"}>
              {String(value)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
