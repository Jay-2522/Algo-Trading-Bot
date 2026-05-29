export type DashboardCardData = {
  card_id: string;
  title: string;
  status: string;
  value: string;
  subtitle: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  metadata?: Record<string, unknown>;
  timestamp?: string;
};

export type DashboardStatus = {
  status: string;
  mode: string;
  dashboard_ready: boolean;
  simulation_only: boolean;
  live_execution_enabled: boolean;
  timestamp?: string;
};

export type DashboardOverview = {
  overall_status: string;
  cards: DashboardCardData[];
  alerts: Array<Record<string, unknown>>;
  simulation_only: boolean;
  live_execution_enabled: boolean;
};

export type DashboardSummary = {
  headline: string;
  summary: string;
  phase3_status: string;
  safety_status: string;
  next_step: string;
  simulation_only: boolean;
  live_execution_enabled: boolean;
};

export type ExecutiveKpiData = {
  label: string;
  value: string;
  status: string;
  description: string;
};

export type ClientDemoOverviewData = {
  system_status: string;
  client_mvp_status: string;
  supported_markets: string[];
  supported_brokers: string[];
  pipeline_summary: string[];
  safety_summary: string[];
  kpis: ExecutiveKpiData[];
  next_steps: string[];
  simulation_only: boolean;
  live_execution_enabled: boolean;
  timestamp?: string;
};

export type PortfolioAccountSummaryData = {
  account_id: string;
  broker_id: string;
  account_mode: string;
  balance: number;
  equity: number;
  free_margin: number;
  enabled: boolean;
  demo_ready: boolean;
  supported_symbols: string[];
  risk_status: string;
  simulation_only: boolean;
  live_execution_enabled: boolean;
};

export type PortfolioExposureSummaryData = {
  total_accounts: number;
  enabled_accounts: number;
  supported_symbols: string[];
  blocked_symbols: string[];
  total_simulated_balance: number;
  total_simulated_equity: number;
  exposure_by_symbol: Record<string, Record<string, unknown>>;
  risk_summary: Record<string, unknown>;
  simulation_only: boolean;
  live_execution_enabled: boolean;
};

export type PortfolioOverviewData = {
  portfolio_status: string;
  accounts: PortfolioAccountSummaryData[];
  exposure_summary: PortfolioExposureSummaryData;
  pnl_summary: Record<string, unknown>;
  warnings: string[];
  simulation_only: boolean;
  live_execution_enabled: boolean;
  timestamp?: string;
};

export type OperationalModuleStatusData = {
  module_name: string;
  status: string;
  last_check: string;
  message: string;
};

export type WarningSummaryData = {
  warning_id: string;
  category: string;
  severity: string;
  message: string;
  timestamp: string;
};

export type OperationalHealthSummaryData = {
  overall_status: string;
  health_score: number;
  active_warnings: number;
  active_alerts: number;
  monitored_modules: number;
  simulation_only: boolean;
  live_execution_enabled: boolean;
};

export type DashboardBundle = {
  status: DashboardStatus | null;
  overview: DashboardOverview | null;
  cards: DashboardCardData[];
  summary: DashboardSummary | null;
  alerts: Array<Record<string, unknown>>;
  brokerStatus: Record<string, unknown> | null;
  brokerObservationStatus: Record<string, unknown> | null;
  accountStatus: Record<string, unknown> | null;
  allocationStatus: Record<string, unknown> | null;
  executionStatus: Record<string, unknown> | null;
  lifecycleStatus: Record<string, unknown> | null;
  webhookStatus: Record<string, unknown> | null;
  webhookOrchestrationStatus: Record<string, unknown> | null;
  phase3Status: Record<string, unknown> | null;
  webhookEvents: Array<Record<string, unknown>>;
  orchestrationDecisions: Array<Record<string, unknown>>;
  queueItems: Array<Record<string, unknown>>;
  lifecycleAuditEvents: Array<Record<string, unknown>>;
  webhookSecurityEvents: Array<Record<string, unknown>>;
  controlStatus: Record<string, unknown> | null;
  safetyState: Record<string, unknown> | null;
  controlAuditEvents: Array<Record<string, unknown>>;
  demoStatus: Record<string, unknown> | null;
  demoOverview: ClientDemoOverviewData | null;
  demoKpis: ExecutiveKpiData[];
  demoPipelineSummary: Record<string, unknown> | null;
  portfolioStatus: Record<string, unknown> | null;
  portfolioOverview: PortfolioOverviewData | null;
  portfolioAccounts: PortfolioAccountSummaryData[];
  portfolioExposure: PortfolioExposureSummaryData | null;
  portfolioPnlSummary: Record<string, unknown> | null;
  operationalStatus: Record<string, unknown> | null;
  operationalHealthSummary: OperationalHealthSummaryData | null;
  operationalModules: OperationalModuleStatusData[];
  operationalWarnings: WarningSummaryData[];
  operationalHealthScore: Record<string, unknown> | null;
  errors: string[];
};

const endpoints = {
  status: "/dashboard/status",
  overview: "/dashboard/overview",
  cards: "/dashboard/cards",
  summary: "/dashboard/summary",
  alerts: "/monitoring/alerts",
  brokerStatus: "/brokers/status",
  brokerObservationStatus: "/brokers/observation/status",
  accountStatus: "/accounts/status",
  allocationStatus: "/accounts/allocation/status",
  executionStatus: "/execution-queue/status",
  lifecycleStatus: "/execution-queue/lifecycle/status",
  webhookStatus: "/webhooks/status",
  webhookOrchestrationStatus: "/webhooks/orchestration/status",
  phase3Status: "/phase3/status",
  webhookEvents: "/webhooks/events?limit=20",
  orchestrationDecisions: "/webhooks/orchestration/decisions?limit=20",
  queueItems: "/execution-queue/items?limit=20",
  lifecycleAuditEvents: "/execution-queue/lifecycle/audit-events?limit=20",
  webhookSecurityEvents: "/webhooks/security/events?limit=20",
  controlStatus: "/control-center/status",
  safetyState: "/control-center/safety-state",
  controlAuditEvents: "/control-center/audit-events?limit=20",
  demoStatus: "/demo-mode/status",
  demoOverview: "/demo-mode/overview",
  demoKpis: "/demo-mode/kpis",
  demoPipelineSummary: "/demo-mode/pipeline-summary",
  portfolioStatus: "/portfolio/status",
  portfolioOverview: "/portfolio/overview",
  portfolioAccounts: "/portfolio/accounts",
  portfolioExposure: "/portfolio/exposure",
  portfolioPnlSummary: "/portfolio/pnl-summary",
  operationalStatus: "/operational-intelligence/status",
  operationalHealthSummary: "/operational-intelligence/health-summary",
  operationalModules: "/operational-intelligence/modules",
  operationalWarnings: "/operational-intelligence/warnings",
  operationalHealthScore: "/operational-intelligence/health-score",
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

function buildApiUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

async function fetchJson<T>(endpoint: string): Promise<T> {
  const url = buildApiUrl(endpoint);
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(endpoint: string, payload: Record<string, unknown> = {}): Promise<T> {
  const url = buildApiUrl(endpoint);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function errorMessage(key: string, result: PromiseSettledResult<unknown>): string | null {
  if (result.status === "fulfilled") {
    return null;
  }
  return `${key}: ${result.reason instanceof Error ? result.reason.message : "request failed"}`;
}

export async function fetchDashboardBundle(): Promise<DashboardBundle> {
  const results = await Promise.allSettled([
    fetchJson<DashboardStatus>(endpoints.status),
    fetchJson<DashboardOverview>(endpoints.overview),
    fetchJson<DashboardCardData[]>(endpoints.cards),
    fetchJson<DashboardSummary>(endpoints.summary),
    fetchJson<Array<Record<string, unknown>>>(endpoints.alerts),
    fetchJson<Record<string, unknown>>(endpoints.brokerStatus),
    fetchJson<Record<string, unknown>>(endpoints.brokerObservationStatus),
    fetchJson<Record<string, unknown>>(endpoints.accountStatus),
    fetchJson<Record<string, unknown>>(endpoints.allocationStatus),
    fetchJson<Record<string, unknown>>(endpoints.executionStatus),
    fetchJson<Record<string, unknown>>(endpoints.lifecycleStatus),
    fetchJson<Record<string, unknown>>(endpoints.webhookStatus),
    fetchJson<Record<string, unknown>>(endpoints.webhookOrchestrationStatus),
    fetchJson<Record<string, unknown>>(endpoints.phase3Status),
    fetchJson<Array<Record<string, unknown>>>(endpoints.webhookEvents),
    fetchJson<Array<Record<string, unknown>>>(endpoints.orchestrationDecisions),
    fetchJson<Array<Record<string, unknown>>>(endpoints.queueItems),
    fetchJson<Array<Record<string, unknown>>>(endpoints.lifecycleAuditEvents),
    fetchJson<Array<Record<string, unknown>>>(endpoints.webhookSecurityEvents),
    fetchJson<Record<string, unknown>>(endpoints.controlStatus),
    fetchJson<Record<string, unknown>>(endpoints.safetyState),
    fetchJson<Array<Record<string, unknown>>>(endpoints.controlAuditEvents),
    fetchJson<Record<string, unknown>>(endpoints.demoStatus),
    fetchJson<ClientDemoOverviewData>(endpoints.demoOverview),
    fetchJson<ExecutiveKpiData[]>(endpoints.demoKpis),
    fetchJson<Record<string, unknown>>(endpoints.demoPipelineSummary),
    fetchJson<Record<string, unknown>>(endpoints.portfolioStatus),
    fetchJson<PortfolioOverviewData>(endpoints.portfolioOverview),
    fetchJson<PortfolioAccountSummaryData[]>(endpoints.portfolioAccounts),
    fetchJson<PortfolioExposureSummaryData>(endpoints.portfolioExposure),
    fetchJson<Record<string, unknown>>(endpoints.portfolioPnlSummary),
    fetchJson<Record<string, unknown>>(endpoints.operationalStatus),
    fetchJson<OperationalHealthSummaryData>(endpoints.operationalHealthSummary),
    fetchJson<OperationalModuleStatusData[]>(endpoints.operationalModules),
    fetchJson<WarningSummaryData[]>(endpoints.operationalWarnings),
    fetchJson<Record<string, unknown>>(endpoints.operationalHealthScore),
  ]);

  const [
    status,
    overview,
    cards,
    summary,
    alerts,
    brokerStatus,
    brokerObservationStatus,
    accountStatus,
    allocationStatus,
    executionStatus,
    lifecycleStatus,
    webhookStatus,
    webhookOrchestrationStatus,
    phase3Status,
    webhookEvents,
    orchestrationDecisions,
    queueItems,
    lifecycleAuditEvents,
    webhookSecurityEvents,
    controlStatus,
    safetyState,
    controlAuditEvents,
    demoStatus,
    demoOverview,
    demoKpis,
    demoPipelineSummary,
    portfolioStatus,
    portfolioOverview,
    portfolioAccounts,
    portfolioExposure,
    portfolioPnlSummary,
    operationalStatus,
    operationalHealthSummary,
    operationalModules,
    operationalWarnings,
    operationalHealthScore,
  ] = results;
  const errors = results
    .map((result, index) => errorMessage(Object.keys(endpoints)[index], result))
    .filter((message): message is string => Boolean(message));

  return {
    status: status.status === "fulfilled" ? status.value : null,
    overview: overview.status === "fulfilled" ? overview.value : null,
    cards: cards.status === "fulfilled" ? cards.value : [],
    summary: summary.status === "fulfilled" ? summary.value : null,
    alerts: alerts.status === "fulfilled" ? alerts.value : [],
    brokerStatus: brokerStatus.status === "fulfilled" ? brokerStatus.value : null,
    brokerObservationStatus: brokerObservationStatus.status === "fulfilled" ? brokerObservationStatus.value : null,
    accountStatus: accountStatus.status === "fulfilled" ? accountStatus.value : null,
    allocationStatus: allocationStatus.status === "fulfilled" ? allocationStatus.value : null,
    executionStatus: executionStatus.status === "fulfilled" ? executionStatus.value : null,
    lifecycleStatus: lifecycleStatus.status === "fulfilled" ? lifecycleStatus.value : null,
    webhookStatus: webhookStatus.status === "fulfilled" ? webhookStatus.value : null,
    webhookOrchestrationStatus: webhookOrchestrationStatus.status === "fulfilled" ? webhookOrchestrationStatus.value : null,
    phase3Status: phase3Status.status === "fulfilled" ? phase3Status.value : null,
    webhookEvents: webhookEvents.status === "fulfilled" ? webhookEvents.value : [],
    orchestrationDecisions: orchestrationDecisions.status === "fulfilled" ? orchestrationDecisions.value : [],
    queueItems: queueItems.status === "fulfilled" ? queueItems.value : [],
    lifecycleAuditEvents: lifecycleAuditEvents.status === "fulfilled" ? lifecycleAuditEvents.value : [],
    webhookSecurityEvents: webhookSecurityEvents.status === "fulfilled" ? webhookSecurityEvents.value : [],
    controlStatus: controlStatus.status === "fulfilled" ? controlStatus.value : null,
    safetyState: safetyState.status === "fulfilled" ? safetyState.value : null,
    controlAuditEvents: controlAuditEvents.status === "fulfilled" ? controlAuditEvents.value : [],
    demoStatus: demoStatus.status === "fulfilled" ? demoStatus.value : null,
    demoOverview: demoOverview.status === "fulfilled" ? demoOverview.value : null,
    demoKpis: demoKpis.status === "fulfilled" ? demoKpis.value : [],
    demoPipelineSummary: demoPipelineSummary.status === "fulfilled" ? demoPipelineSummary.value : null,
    portfolioStatus: portfolioStatus.status === "fulfilled" ? portfolioStatus.value : null,
    portfolioOverview: portfolioOverview.status === "fulfilled" ? portfolioOverview.value : null,
    portfolioAccounts: portfolioAccounts.status === "fulfilled" ? portfolioAccounts.value : [],
    portfolioExposure: portfolioExposure.status === "fulfilled" ? portfolioExposure.value : null,
    portfolioPnlSummary: portfolioPnlSummary.status === "fulfilled" ? portfolioPnlSummary.value : null,
    operationalStatus: operationalStatus.status === "fulfilled" ? operationalStatus.value : null,
    operationalHealthSummary: operationalHealthSummary.status === "fulfilled" ? operationalHealthSummary.value : null,
    operationalModules: operationalModules.status === "fulfilled" ? operationalModules.value : [],
    operationalWarnings: operationalWarnings.status === "fulfilled" ? operationalWarnings.value : [],
    operationalHealthScore: operationalHealthScore.status === "fulfilled" ? operationalHealthScore.value : null,
    errors,
  };
}

export function pauseSimulationQueue(reason: string) {
  return postJson<Record<string, unknown>>("/control-center/queue/pause", { reason });
}

export function resumeSimulationQueue(reason: string) {
  return postJson<Record<string, unknown>>("/control-center/queue/resume", { reason });
}

export function emergencyStopPlaceholder(reason: string) {
  return postJson<Record<string, unknown>>("/control-center/emergency-stop-placeholder", { reason });
}

export function cancelSimulationQueueItem(queueId: string, reason: string) {
  return postJson<Record<string, unknown>>(`/control-center/queue/${encodeURIComponent(queueId)}/cancel`, { reason });
}

export function acknowledgeMonitoringAlert(alertId: string, reason: string) {
  return postJson<Record<string, unknown>>(`/control-center/alerts/${encodeURIComponent(alertId)}/acknowledge`, { reason });
}
