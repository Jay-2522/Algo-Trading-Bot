import type { DashboardCardData } from "@/lib/dashboard-api";
import { DashboardCard } from "./DashboardCard";

export function DashboardStatusGrid({ cards, loading }: { cards: DashboardCardData[]; loading: boolean }) {
  if (loading && cards.length === 0) {
    return (
      <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div
            className="h-40 animate-pulse rounded-3xl border border-white/10 bg-slate-900/55"
            key={index}
          />
        ))}
      </section>
    );
  }

  if (!cards.length) {
    return (
      <section className="rounded-3xl border border-dashed border-slate-700 bg-slate-950/50 p-8 text-center text-slate-400">
        Dashboard cards are waiting for backend data.
      </section>
    );
  }

  return (
    <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4" aria-label="Dashboard status cards">
      {cards.map((card) => (
        <DashboardCard key={card.card_id} card={card} />
      ))}
    </section>
  );
}
