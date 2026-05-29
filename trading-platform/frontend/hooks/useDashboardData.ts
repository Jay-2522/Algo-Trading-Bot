"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchDashboardBundle, type DashboardBundle } from "@/lib/dashboard-api";

const emptyBundle: DashboardBundle = {
  status: null,
  overview: null,
  cards: [],
  summary: null,
  alerts: [],
  brokerStatus: null,
  brokerObservationStatus: null,
  accountStatus: null,
  allocationStatus: null,
  executionStatus: null,
  lifecycleStatus: null,
  webhookStatus: null,
  webhookOrchestrationStatus: null,
  phase3Status: null,
  webhookEvents: [],
  orchestrationDecisions: [],
  queueItems: [],
  lifecycleAuditEvents: [],
  webhookSecurityEvents: [],
  controlStatus: null,
  safetyState: null,
  controlAuditEvents: [],
  demoStatus: null,
  demoOverview: null,
  demoKpis: [],
  demoPipelineSummary: null,
  portfolioStatus: null,
  portfolioOverview: null,
  portfolioAccounts: [],
  portfolioExposure: null,
  portfolioPnlSummary: null,
  operationalStatus: null,
  operationalHealthSummary: null,
  operationalModules: [],
  operationalWarnings: [],
  operationalHealthScore: null,
  clientAcceptanceStatus: null,
  deliveryReadiness: null,
  acceptanceChecklist: [],
  remainingDeliveryItems: null,
  executionDashboardStatus: null,
  executionDashboardOverview: null,
  executionDashboardCards: [],
  executionDashboardSummary: null,
  errors: [],
};

export function useDashboardData(refreshIntervalMs = 10000) {
  const [bundle, setBundle] = useState<DashboardBundle>(emptyBundle);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const requestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) {
      return;
    }

    requestInFlight.current = true;
    setLoading(true);
    try {
      const nextBundle = await fetchDashboardBundle();
      setBundle((previous) => ({
        ...previous,
        ...nextBundle,
        cards: nextBundle.cards.length ? nextBundle.cards : previous.cards,
        alerts: nextBundle.alerts.length ? nextBundle.alerts : previous.alerts,
        webhookEvents: nextBundle.webhookEvents.length ? nextBundle.webhookEvents : previous.webhookEvents,
        orchestrationDecisions: nextBundle.orchestrationDecisions.length
          ? nextBundle.orchestrationDecisions
          : previous.orchestrationDecisions,
        queueItems: nextBundle.queueItems.length ? nextBundle.queueItems : previous.queueItems,
        lifecycleAuditEvents: nextBundle.lifecycleAuditEvents.length
          ? nextBundle.lifecycleAuditEvents
          : previous.lifecycleAuditEvents,
        webhookSecurityEvents: nextBundle.webhookSecurityEvents.length
          ? nextBundle.webhookSecurityEvents
          : previous.webhookSecurityEvents,
        controlAuditEvents: nextBundle.controlAuditEvents.length ? nextBundle.controlAuditEvents : previous.controlAuditEvents,
        demoKpis: nextBundle.demoKpis.length ? nextBundle.demoKpis : previous.demoKpis,
        portfolioAccounts: nextBundle.portfolioAccounts.length ? nextBundle.portfolioAccounts : previous.portfolioAccounts,
        operationalModules: nextBundle.operationalModules.length ? nextBundle.operationalModules : previous.operationalModules,
        operationalWarnings: nextBundle.operationalWarnings.length ? nextBundle.operationalWarnings : previous.operationalWarnings,
        acceptanceChecklist: nextBundle.acceptanceChecklist.length ? nextBundle.acceptanceChecklist : previous.acceptanceChecklist,
        executionDashboardCards: nextBundle.executionDashboardCards.length
          ? nextBundle.executionDashboardCards
          : previous.executionDashboardCards,
        errors: nextBundle.errors,
      }));
      setLastError(nextBundle.errors.length ? nextBundle.errors.join("; ") : null);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    } catch (exc) {
      setLastError(exc instanceof Error ? exc.message : "Dashboard refresh failed.");
    } finally {
      requestInFlight.current = false;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(initialRefresh);
  }, [refresh]);

  useEffect(() => {
    if (isPaused) {
      return;
    }

    const interval = window.setInterval(() => void refresh(), refreshIntervalMs);
    return () => window.clearInterval(interval);
  }, [isPaused, refresh, refreshIntervalMs]);

  return {
    bundle,
    loading,
    isPaused,
    lastUpdated,
    lastError,
    refresh,
    pause: () => setIsPaused(true),
    resume: () => setIsPaused(false),
    togglePause: () => setIsPaused((current) => !current),
  };
}
