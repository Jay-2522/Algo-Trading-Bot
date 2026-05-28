import type { DashboardCardData } from "../../lib/dashboard-api";

const severityClass: Record<string, string> = {
  INFO: "badgeInfo",
  LOW: "badgeInfo",
  MEDIUM: "badgeWarning",
  HIGH: "badgeDanger",
  CRITICAL: "badgeDanger",
};

export function DashboardCard({ card }: { card: DashboardCardData }) {
  return (
    <article className="dashboardCard">
      <div className="cardTopline">
        <span className="cardTitle">{card.title}</span>
        <span className={`statusBadge ${severityClass[card.severity] ?? "badgeInfo"}`}>
          {card.status}
        </span>
      </div>
      <div className="cardValue">{card.value}</div>
      <p className="cardSubtitle">{card.subtitle}</p>
    </article>
  );
}
