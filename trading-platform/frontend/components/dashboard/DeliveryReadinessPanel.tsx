import type { AcceptanceChecklistItemData, DeliveryReadinessData } from "@/lib/dashboard-api";

import { AcceptanceChecklist } from "./AcceptanceChecklist";
import { ReadinessScoreCard } from "./ReadinessScoreCard";
import { RemainingWorkPanel } from "./RemainingWorkPanel";
import { StatusBadge } from "./StatusBadge";

function readinessRows(readiness: DeliveryReadinessData | null) {
  return [
    ["Dashboard", readiness?.dashboard_ready ?? true],
    ["Orchestration", readiness?.orchestration_ready ?? true],
    ["Monitoring", readiness?.monitoring_ready ?? true],
    ["Broker Mapping", readiness?.broker_ready ?? true],
    ["Portfolio", readiness?.portfolio_ready ?? true],
    ["Control Center", readiness?.control_center_ready ?? true],
    ["Simulation", readiness?.simulation_ready ?? true],
    ["Deployment", readiness?.deployment_ready ?? false],
    ["Client Demo", readiness?.client_demo_ready ?? true],
  ];
}

export function DeliveryReadinessPanel({
  readiness,
  checklist,
}: {
  readiness: DeliveryReadinessData | null;
  checklist: AcceptanceChecklistItemData[];
}) {
  return (
    <section className="space-y-4">
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-cyan-100/70">Client Delivery Readiness</p>
            <h2 className="mt-2 break-words text-3xl font-black leading-tight text-white">Acceptance & Delivery Layer</h2>
            <p className="mt-3 max-w-4xl break-words text-sm leading-7 text-slate-300">
              Final delivery view for client acceptance: readiness score, completed systems, remaining work, deployment posture, demo readiness, and safety confirmation.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={readiness?.client_demo_ready ? "Demo Ready" : "Review"} tone="good" />
            <StatusBadge label={readiness?.live_execution_enabled ? "Live Enabled" : "Live Disabled"} tone="good" />
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.8fr_1.3fr]">
        <ReadinessScoreCard readiness={readiness} />
        <section className="rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-emerald-100/70">Readiness Badges</p>
          <h3 className="mt-1 text-xl font-black text-white">Deployment & Demo Posture</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {readinessRows(readiness).map(([label, ready]) => (
              <div className="flex min-w-0 items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-950/35 p-3" key={String(label)}>
                <span className="break-words text-sm font-bold text-slate-200">{label}</span>
                <StatusBadge label={ready ? "Ready" : "Pending"} tone={ready ? "good" : "warning"} />
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-2xl border border-emerald-300/15 bg-emerald-300/10 p-3 text-sm leading-6 text-emerald-100">
            Safety confirmation: simulation-only mode is active, broker execution is disabled, and no live orders are placed.
          </div>
        </section>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.25fr_0.85fr]">
        <AcceptanceChecklist checklist={checklist} />
        <RemainingWorkPanel items={readiness?.remaining_items ?? []} />
      </section>
    </section>
  );
}
