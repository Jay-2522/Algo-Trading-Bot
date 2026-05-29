import type { ExecutionDashboardCard } from "@/lib/execution-dashboard-api";

import { StatusBadge } from "./StatusBadge";

function toneFor(status: string): "good" | "info" | "warning" | "danger" | "muted" {
  if (status === "READY") {
    return "good";
  }
  if (status === "REVIEW") {
    return "warning";
  }
  if (status === "BLOCKED") {
    return "danger";
  }
  return "info";
}

export function ExecutionHealthCards({ cards }: { cards: ExecutionDashboardCard[] }) {
  const visibleCards = cards.length
    ? cards
    : [
        { title: "Execution Bridge", value: "Loading", status: "INFO", description: "Awaiting execution dashboard data." },
        { title: "Execution Health Score", value: "Loading", status: "INFO", description: "Composite execution health is loading." },
        { title: "Client Readiness", value: "Loading", status: "INFO", description: "Client readiness is loading." },
      ];

  return (
    <section className="grid auto-rows-fr gap-4 md:grid-cols-2 xl:grid-cols-4">
      {visibleCards.map((card) => (
        <article
          className="flex min-h-44 min-w-0 flex-col justify-between rounded-lg border border-white/10 bg-slate-900/60 p-5 shadow-xl shadow-black/20"
          key={card.title}
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="break-words text-sm font-black uppercase leading-relaxed tracking-[0.16em] text-slate-200">{card.title}</h3>
              <StatusBadge label={card.status} tone={toneFor(card.status)} />
            </div>
            <p className="mt-4 break-words text-2xl font-black leading-tight text-white">{card.value}</p>
          </div>
          <p className="mt-4 break-words text-xs leading-6 text-slate-400">{card.description}</p>
        </article>
      ))}
    </section>
  );
}

