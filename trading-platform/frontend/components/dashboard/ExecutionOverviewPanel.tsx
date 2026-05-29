import type { ExecutionDashboardOverview } from "@/lib/execution-dashboard-api";

import { StatusBadge } from "./StatusBadge";

function toneFor(value: string): "good" | "info" | "warning" | "danger" | "muted" {
  if (["OPERATIONAL", "DEMO_EXECUTION_READY", "CLIENT_DEMO_READY", "CONFIRMED"].includes(value)) {
    return "good";
  }
  if (["PENDING", "REVIEW_REQUIRED"].includes(value)) {
    return "warning";
  }
  if (["DEMO_EXECUTION_BLOCKED", "BLOCKED"].includes(value)) {
    return "danger";
  }
  return "info";
}

export function ExecutionOverviewPanel({ overview }: { overview: ExecutionDashboardOverview | null }) {
  const readiness = overview?.execution_readiness ?? "Loading";

  return (
    <section className="overflow-hidden rounded-lg border border-cyan-100/15 bg-slate-950/70 p-6 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.24em] text-cyan-100/70">
            Execution Operations Center
          </p>
          <h2 className="mt-2 break-words text-3xl font-black leading-tight text-white">Unified Execution Monitoring</h2>
          <p className="mt-3 max-w-4xl break-words text-sm leading-7 text-slate-300">
            Demo execution bridge, account routing, copier synchronization, confirmations, reconciliation, and risk enforcement in one read-only operating view.
          </p>
        </div>
        <StatusBadge label={readiness} tone={toneFor(readiness)} />
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {[
          ["Execution Bridge", overview?.execution_bridge_status ?? "Loading"],
          ["Multi-Account Routing", overview?.routing_status ?? "Loading"],
          ["Trade Copier", overview?.copier_status ?? "Loading"],
          ["Confirmations", overview?.confirmation_status ?? "Loading"],
          ["Reconciliation", overview?.reconciliation_status ?? "Loading"],
          ["Risk Enforcement", overview?.risk_status ?? "Loading"],
        ].map(([label, value]) => (
          <div className="min-h-24 rounded-lg border border-white/10 bg-white/[0.045] p-4" key={label}>
            <p className="break-words text-xs font-semibold uppercase leading-relaxed tracking-[0.16em] text-slate-500">{label}</p>
            <div className="mt-3">
              <StatusBadge label={value} tone={toneFor(value)} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

