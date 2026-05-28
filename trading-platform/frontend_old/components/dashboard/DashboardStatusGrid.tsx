import type { DashboardCardData } from "../../lib/dashboard-api";
import { DashboardCard } from "./DashboardCard";

export function DashboardStatusGrid({ cards }: { cards: DashboardCardData[] }) {
  if (!cards.length) {
    return <div className="emptyPanel">Dashboard cards are waiting for backend data.</div>;
  }

  return (
    <section className="cardGrid" aria-label="Dashboard status cards">
      {cards.map((card) => (
        <DashboardCard key={card.card_id} card={card} />
      ))}
    </section>
  );
}
