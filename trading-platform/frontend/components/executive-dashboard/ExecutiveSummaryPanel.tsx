import type { ExecutiveSummary } from "@/lib/executiveDashboardApi";

export function ExecutiveSummaryPanel({ summary }: { summary: ExecutiveSummary }) {
  const completed = [
    "Analytics Layer",
    "Reporting Layer",
    "Trade Journal",
    "Account Analytics",
    "Strategy Intelligence",
    "Deployment Readiness",
    "Monitoring",
    "Security",
  ];
  const pending = ["NIFTY50 Production Layer", "Demo Broker Validation", "VPS Deployment", "Extended Stability Testing"];

  return (
    <section className="rounded-2xl border border-emerald-300/15 bg-emerald-300/[0.06] p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-emerald-100/70">Executive Summary</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <h3 className="text-xl font-black text-white">Client Acceptance View</h3>
        <div className="text-right">
          <strong className="block text-3xl font-black text-emerald-100">{Math.round(summary.overall_completion_percentage)}%</strong>
          <span className="text-xs uppercase tracking-[0.16em] text-emerald-100/60">Derived readiness score</span>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-100/70">Completed</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-200">
            {completed.map((item) => <li key={item}>Done - {item}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-amber-100/70">Pending</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-200">
            {pending.map((item) => <li key={item}>Pending - {item}</li>)}
          </ul>
        </div>
      </div>
    </section>
  );
}
