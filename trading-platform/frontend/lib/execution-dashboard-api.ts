export type ExecutionDashboardOverview = {
  execution_bridge_status: string;
  routing_status: string;
  copier_status: string;
  confirmation_status: string;
  reconciliation_status: string;
  risk_status: string;
  health_score: number;
  execution_readiness: string;
  simulation_only: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
  timestamp?: string;
};

export type ExecutionDashboardCard = {
  title: string;
  value: string;
  status: string;
  description: string;
};

export type ExecutionDashboardSummary = {
  total_demo_executions: number;
  total_confirmations: number;
  total_reconciliations: number;
  total_risk_decisions: number;
  total_copy_batches: number;
  total_multi_account_batches: number;
  blocked_attempts: number;
  warnings: string[];
  timestamp?: string;
};

export type ExecutionDashboardStatus = {
  status: string;
  mode: string;
  dashboard_ready: boolean;
  execution_readiness: string;
  health_score: number;
  monitored_demo_executions: number;
  monitored_confirmations: number;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
  timestamp?: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

function buildExecutionDashboardUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

export async function fetchExecutionDashboardJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(buildExecutionDashboardUrl(endpoint), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

