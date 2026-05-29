import type { ExecutionDashboardSummary } from "@/lib/execution-dashboard-api";

const metrics = [
  ["Demo Executions", "total_demo_executions"],
  ["Confirmations", "total_confirmations"],
  ["Reconciliations", "total_reconciliations"],
  ["Risk Decisions", "total_risk_decisions"],
  ["Copy Batches", "total_copy_batches"],
  ["Routing Batches", "total_multi_account_batches"],
  ["Blocked Attempts", "blocked_attempts"],
] as const;

export function ExecutionSummaryPanel({ summary }: { summary: ExecutionDashboardSummary | null }) {
  return (
    <section className="rounded-lg border border-white/10 bg-slate-950/65 p-5 shadow-2xl shadow-black/20">
      <p className="text-[0.68rem] uppercase leading-relaxed tracking-[0.22em] text-slate-500">Execution Audit Summary</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {metrics.map(([label, key]) => (
          <div className="min-h-20 rounded-lg border border-white/10 bg-white/[0.04] p-4" key={key}>
            <p className="break-words text-xs font-semibold uppercase leading-relaxed tracking-[0.14em] text-slate-500">{label}</p>
            <p className="mt-2 break-words text-2xl font-black leading-tight text-white">{summary?.[key] ?? 0}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-lg border border-amber-200/15 bg-amber-200/[0.06] p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-amber-100/80">Risk & Audit Notes</p>
        <ul className="mt-3 space-y-2">
          {(summary?.warnings.length ? summary.warnings : ["Dashboard is read-only. Live and broker execution remain disabled."]).map((warning) => (
            <li className="break-words text-xs leading-6 text-amber-50/75" key={warning}>
              {warning}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

