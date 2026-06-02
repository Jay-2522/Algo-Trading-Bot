import type { ClientReport } from "@/lib/clientReportsApi";

import { ReportEmptyState } from "./ReportEmptyState";

export function ReportPreview({ report }: { report: ClientReport }) {
  const empty = Boolean(report.summary.empty_report);
  const metrics: Array<[string, string | number]> = [
    ["Signals", Number(report.summary.total_signals || 0)],
    ["Demo Executions", Number(report.summary.total_demo_executions || 0)],
    ["Win Rate", `${Number(report.summary.win_rate || 0).toFixed(2)}%`],
    ["Net P&L", `$${Number(report.summary.net_pnl || 0).toFixed(2)}`],
  ];
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Printable Report View</p>
          <h3 className="mt-1 text-xl font-black text-white">{report.report_type.replaceAll("_", " ")} / {report.period}</h3>
        </div>
        <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[0.6rem] font-black uppercase tracking-[0.12em] text-cyan-100">
          Printable
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div className="rounded-xl border border-white/10 bg-white/[0.035] p-3" key={label}>
            <p className="text-[0.62rem] uppercase tracking-[0.12em] text-slate-500">{label}</p>
            <strong className="mt-1 block break-words text-slate-100">{value}</strong>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/35 p-3">
        <p className="text-[0.62rem] uppercase tracking-[0.12em] text-slate-500">Safety Flags</p>
        <div className="mt-2 grid gap-2 text-xs text-slate-300 sm:grid-cols-2 xl:grid-cols-4">
          <div>simulation_only = {String(report.simulation_only)}</div>
          <div>demo_execution = {String(report.demo_execution)}</div>
          <div>live_execution_enabled = {String(report.live_execution_enabled)}</div>
          <div>broker_execution_enabled = {String(report.broker_execution_enabled)}</div>
        </div>
      </div>

      {empty ? <div className="mt-4"><ReportEmptyState /></div> : null}
    </section>
  );
}
