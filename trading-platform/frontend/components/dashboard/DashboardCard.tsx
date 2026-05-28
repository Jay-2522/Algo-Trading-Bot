import type { DashboardCardData } from "@/lib/dashboard-api";
import { StatusBadge } from "./StatusBadge";

const severityTone: Record<DashboardCardData["severity"], "good" | "info" | "warning" | "danger" | "muted"> = {
  INFO: "good",
  LOW: "info",
  MEDIUM: "warning",
  HIGH: "danger",
  CRITICAL: "danger",
};

export function DashboardCard({ card }: { card: DashboardCardData }) {
  return (
    <article className="group min-h-44 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/50 p-4 shadow-xl shadow-black/15 backdrop-blur-xl transition duration-200 hover:-translate-y-0.5 hover:border-cyan-200/25 hover:bg-slate-900/60 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-sm font-bold leading-relaxed text-slate-100">{card.title}</p>
          <p className="mt-1 break-words text-[0.65rem] uppercase leading-relaxed tracking-[0.18em] text-slate-500">
            {card.card_id.replaceAll("_", " ")}
          </p>
        </div>
        <StatusBadge label={card.status} tone={severityTone[card.severity] ?? "info"} />
      </div>

      <div className="mt-5 max-w-full break-words text-2xl font-black leading-tight tracking-tight text-white">{card.value}</div>
      <p className="mt-2 text-xs leading-relaxed text-slate-400 sm:text-sm">{card.subtitle}</p>
    </article>
  );
}
