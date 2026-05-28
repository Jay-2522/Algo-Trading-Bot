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
    <section className="rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Live Monitoring</p>
          <h2 className="mt-1 text-lg font-bold text-white">Readiness & Alerts</h2>
        </div>
        <StatusBadge label={phaseStatus} tone={phaseStatus === "READY" ? "good" : "warning"} />
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <p className="text-xs text-slate-500">Active / recent alerts</p>
        <strong className="mt-1 block text-2xl text-white">{alerts.length}</strong>
        <p className="mt-2 text-xs leading-5 text-slate-400">
          {alerts.length ? "Review monitoring alerts below." : "No active alerts. Safety status is quiet."}
        </p>
      </div>
    </section>
  );
}
