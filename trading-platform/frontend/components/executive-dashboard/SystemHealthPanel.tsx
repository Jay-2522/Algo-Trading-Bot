import type { SystemHealth } from "@/lib/executiveDashboardApi";

export function SystemHealthPanel({ health }: { health: SystemHealth }) {
  const scores = [
    ["Deployment", health.deployment_score],
    ["Monitoring", health.monitoring_score],
    ["Security", health.security_score],
    ["Production", health.production_score],
  ] as const;

  return (
    <section className="rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.055] p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">System Health</p>
      <h3 className="mt-2 text-xl font-black text-white">Derived Operational Scores</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {scores.map(([label, score]) => (
          <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-4" key={label}>
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-bold text-slate-200">{label}</span>
              <strong className="text-lg text-white">{Math.round(score)}%</strong>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full rounded-full bg-cyan-300" style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
