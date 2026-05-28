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
    errors,
  };
}
