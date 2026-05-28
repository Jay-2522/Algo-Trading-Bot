import { StatusBadge } from "./StatusBadge";

export function LiveMonitoringPanel({
  phase3Status,
  alerts,
}: {
  phase3Status: Record<string, unknown> | null;
  alerts: Array<Record<string, unknown>>;
}) {
  const phaseStatus = String(phase3Status?.overall_status ?? "loading");

  return (
    <section className="min-h-64 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Live Monitoring</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">Readiness & Alerts</h2>
        </div>
        <StatusBadge label={phaseStatus} tone={phaseStatus === "READY" ? "good" : "warning"} />
      </div>
      <div className="mt-4 min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <p className="break-words text-xs leading-relaxed text-slate-500">Active / recent alerts</p>
        <strong className="mt-1 block break-words text-2xl leading-tight text-white">{alerts.length}</strong>
        <p className="mt-2 break-words text-xs leading-relaxed text-slate-400">
          {alerts.length ? "Review monitoring alerts below." : "No active alerts. Safety status is quiet."}
        </p>
      </div>
    </section>
  );
}
