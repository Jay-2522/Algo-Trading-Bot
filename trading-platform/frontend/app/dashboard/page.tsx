import { AccountAnalyticsSection } from "@/components/account-analytics/AccountAnalyticsSection";
import { ClientAnalyticsSection } from "@/components/client-analytics/ClientAnalyticsSection";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { ClientReportsSection } from "@/components/reports/ClientReportsSection";
import { StrategyIntelligenceSection } from "@/components/strategy-intelligence/StrategyIntelligenceSection";
import { TradeJournalSection } from "@/components/trade-journal/TradeJournalSection";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  return (
    <DashboardShell
      accountAnalyticsSection={<AccountAnalyticsSection />}
      analyticsSection={<ClientAnalyticsSection />}
      reportsSection={<ClientReportsSection />}
      strategyIntelligenceSection={<StrategyIntelligenceSection />}
      tradeJournalSection={<TradeJournalSection />}
    />
  );
}
