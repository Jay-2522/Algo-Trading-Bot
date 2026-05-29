import type { ExecutionDashboardOverview, ExecutionDashboardStatus } from "@/lib/execution-dashboard-api";

import { StatusBadge } from "./StatusBadge";

export function ExecutionReadinessPanel({
  overview,
  status,
}: {
  overview: ExecutionDashboardOverview | null;
  status: ExecutionDashboardStatus | null;
}) {
  const healthScore = overview?.health_score ?? status?.health_score ?? 0;
  const readiness = overview?.execution_readiness ?? status?.execution_readiness ?? "Loading";
  const safetyLocked =
    (overview?.simulation_only ?? status?.simulation_only) === true &&
    (overview?.live_execution_enabled ?? status?.live_execution_enabled) === false &&
    (overview?.broker_execution_enabled ?? status?.broker_execution_enabled) === false;

  return (
    <section className="grid gap-4 lg:grid-cols-[0.75fr_1fr]">
      <div className="rounded-lg border border-emerald-200/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20">
        <p
          className="text-[0.68rem] uppercase leading-relaxed tracking-[0.22em] text-emerald-100/75"
          title="Execution Health uses the shared platform health score from DashboardStateProvider."
        >
          Execution Health Score
        </p>
        <p className="mt-4 break-words text-5xl font-black leading-none text-white">{healthScore}%</p>
        <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-950/70">
          <div className="h-full rounded-full bg-emerald-300" style={{ width: `${Math.max(0, Math.min(100, healthScore))}%` }} />
        </div>
        <p className="mt-4 break-words text-sm leading-6 text-emerald-50/75">
          Composite monitoring score across the execution bridge, routing, copier, confirmations, reconciliation, and risk enforcement.
        </p>
      </div>

      <div className="rounded-lg border border-white/10 bg-slate-950/65 p-5 shadow-2xl shadow-black/20">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[0.68rem] uppercase leading-relaxed tracking-[0.22em] text-slate-500">Client Readiness</p>
            <h3 className="mt-2 break-words text-2xl font-black leading-tight text-white">{readiness}</h3>
          </div>
          <StatusBadge label={safetyLocked ? "Safety Locked" : "Review Safety"} tone={safetyLocked ? "good" : "danger"} />
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          {[
            ["simulation_only", String(overview?.simulation_only ?? status?.simulation_only ?? true)],
            ["live_execution_enabled", String(overview?.live_execution_enabled ?? status?.live_execution_enabled ?? false)],
            ["broker_execution_enabled", String(overview?.broker_execution_enabled ?? status?.broker_execution_enabled ?? false)],
          ].map(([label, value]) => (
            <div className="min-h-20 rounded-lg border border-white/10 bg-white/[0.04] p-3" key={label}>
              <p className="break-words text-[0.68rem] font-semibold uppercase leading-relaxed tracking-[0.12em] text-slate-500">{label}</p>
              <p className="mt-2 break-words text-lg font-black leading-tight text-white">{value}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 break-words text-sm leading-6 text-slate-400">
          Client-facing visibility is enabled for demo execution operations only. No controls here place orders or open a new broker execution path.
        </p>
      </div>
    </section>
  );
}
