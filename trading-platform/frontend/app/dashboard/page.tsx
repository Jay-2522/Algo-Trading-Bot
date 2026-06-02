import { ClientAnalyticsSection } from "@/components/client-analytics/ClientAnalyticsSection";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { ClientReportsSection } from "@/components/reports/ClientReportsSection";
import { TradeJournalSection } from "@/components/trade-journal/TradeJournalSection";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  return (
    <DashboardShell
      analyticsSection={<ClientAnalyticsSection />}
      reportsSection={<ClientReportsSection />}
      tradeJournalSection={<TradeJournalSection />}
    />
  );
}
