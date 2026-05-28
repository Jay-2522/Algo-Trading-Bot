import type { DashboardCardData } from "@/lib/dashboard-api";

const severityStyles: Record<DashboardCardData["severity"], string> = {
  INFO: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  LOW: "border-sky-400/20 bg-sky-400/10 text-sky-200",
  MEDIUM: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  HIGH: "border-rose-400/25 bg-rose-400/10 text-rose-200",
  CRITICAL: "border-red-400/30 bg-red-400/10 text-red-200",
};

export function DashboardCard({ card }: { card: DashboardCardData }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl transition hover:border-sky-300/30 hover:bg-slate-900/70">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-200">{card.title}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.22em] text-slate-500">
            {card.card_id.replaceAll("_", " ")}
          </p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wide ${
            severityStyles[card.severity] ?? severityStyles.INFO
          }`}
        >
          {card.status}
        </span>
      </div>

      <div className="mt-7 text-3xl font-black tracking-tight text-white">{card.value}</div>
      <p className="mt-3 min-h-10 text-sm leading-6 text-slate-400">{card.subtitle}</p>
    </article>
  );
}
