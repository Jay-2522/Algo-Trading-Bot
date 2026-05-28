import type { ExecutiveKpiData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

function toneForStatus(status: string): "good" | "info" | "warning" | "danger" | "muted" {
  const normalized = status.toUpperCase();
  if (normalized.includes("DISABLED")) return "good";
  if (normalized.includes("READY") || normalized.includes("ACTIVE")) return "good";
  if (normalized.includes("CONDITIONAL")) return "warning";
  if (normalized.includes("PLANNED")) return "info";
  return "muted";
}

export function ClientKpiGrid({ kpis }: { kpis: ExecutiveKpiData[] }) {
  const fallbackKpis: ExecutiveKpiData[] = [
    {
      label: "Backend Ready",
      value: "Loading",
      status: "PLANNED",
      description: "Fetching executive demo readiness from the backend.",
    },
    {
      label: "Webhook Ready",
      value: "TradingView",
      status: "PLANNED",
      description: "TradingView intake readiness is loading.",
    },
    {
      label: "Broker Mapping Ready",
      value: "STARTRADER / FxPro / Vantage",
      status: "PLANNED",
      description: "Broker compatibility summary is loading.",
    },
    {
      label: "Account Routing Ready",
      value: "Preview",
      status: "PLANNED",
      description: "Account routing readiness is loading.",
    },
    {
      label: "Simulation Queue Ready",
      value: "Non-Executing",
      status: "PLANNED",
      description: "Simulation queue status is loading.",
    },
    {
      label: "Live Trading Disabled",
      value: "Disabled",
      status: "DISABLED",
      description: "Live execution remains disabled while demo data loads.",
    },
  ];
  const visibleKpis = kpis.length ? kpis : fallbackKpis;

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {visibleKpis.map((kpi) => (
        <div
          className="group min-h-36 min-w-0 rounded-3xl border border-white/10 bg-white/[0.045] p-4 shadow-xl shadow-black/10 transition hover:border-cyan-300/25 hover:bg-cyan-300/[0.06]"
          key={`${kpi.label}-${kpi.value}`}
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="min-w-0 flex-1 break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.18em] text-slate-500">
              {kpi.label}
            </p>
            <StatusBadge label={kpi.status} tone={toneForStatus(kpi.status)} />
          </div>
          <strong className="mt-3 block break-words text-2xl font-black leading-tight text-white">{kpi.value}</strong>
          <p className="mt-2 break-words text-xs leading-6 text-slate-400">{kpi.description}</p>
        </div>
      ))}
    </div>
  );
}
