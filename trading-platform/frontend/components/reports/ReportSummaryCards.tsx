import type { ClientReport } from "@/lib/clientReportsApi";

function numberValue(value: unknown): string {
  return Number(value || 0).toLocaleString();
}

function money(value: unknown): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function ReportSummaryCards({ report }: { report: ClientReport }) {
  const cards = [
    ["Daily Report", numberValue(report.summary.total_signals), "Signals in current report"],
    ["Weekly Report", numberValue(report.summary.total_demo_executions), "Demo executions recorded"],
    ["Symbol Report", money(report.summary.net_pnl), "Real P&L only"],
    ["Risk Report", numberValue(report.risk_summary.blocked), "Risk blocks recorded"],
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(([label, value, detail]) => (
        <article className="rounded-2xl border border-white/10 bg-slate-950/45 p-4 shadow-xl shadow-black/15" key={label}>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
          <strong className="mt-3 block break-words text-2xl font-black text-white">{value}</strong>
          <p className="mt-2 text-xs leading-5 text-slate-400">{detail}</p>
        </article>
      ))}
    </div>
  );
}
