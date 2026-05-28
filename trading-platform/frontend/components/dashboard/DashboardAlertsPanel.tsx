function readText(alert: Record<string, unknown>, key: string, fallback: string): string {
  const value = alert[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function DashboardAlertsPanel({ alerts }: { alerts: Array<Record<string, unknown>> }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Monitoring</p>
          <h2 className="mt-1 text-2xl font-bold text-white">Alerts Panel</h2>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-semibold text-slate-300">
          {alerts.length} active / recent
        </span>
      </div>

      {alerts.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-emerald-400/15 bg-emerald-400/10 p-5 text-sm text-emerald-100">
          No monitoring alerts are currently reported. The dashboard will show new operational alerts here.
        </div>
      ) : (
        <div className="mt-5 grid gap-3">
          {alerts.slice(0, 6).map((alert, index) => (
            <div
              className="rounded-2xl border border-amber-300/15 bg-amber-300/10 p-4"
              key={readText(alert, "alert_id", String(index))}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <strong className="text-sm text-amber-100">
                  {readText(alert, "title", readText(alert, "severity", "Alert"))}
                </strong>
                <span className="text-xs uppercase tracking-[0.2em] text-amber-200/70">
                  {readText(alert, "source", "monitoring")}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-amber-50/75">
                {readText(alert, "message", "Monitoring event detected.")}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
