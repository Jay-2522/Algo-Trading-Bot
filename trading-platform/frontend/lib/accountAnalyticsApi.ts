const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type AccountAnalyticsSummary = {
  account_id: string;
  account_name: string;
  account_type: "MASTER" | "COPIER";
  total_signals: number;
  total_executions: number;
  total_copied_trades: number;
  win_rate: number;
  net_pnl: number;
  max_drawdown: number;
  synchronization_status: "SYNCHRONIZED" | "DEGRADED" | "PENDING" | "UNKNOWN";
  last_sync_time: string | null;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
  timestamp?: string;
};

export type AccountSyncStatus = {
  synchronization_status: "SYNCHRONIZED" | "DEGRADED" | "PENDING" | "UNKNOWN";
  copier_health: string;
  last_sync_time: string | null;
  execution_consistency: string;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
};

export const emptyAccounts: AccountAnalyticsSummary[] = [
  ["MASTER_DEMO", "Master Demo Account", "MASTER"],
  ["STARTRADER_DEMO_1", "STARTRADER Demo Account 1", "COPIER"],
  ["FXPRO_DEMO_1", "FxPro Demo Account 1", "COPIER"],
  ["VANTAGE_DEMO_1", "Vantage Demo Account 1", "COPIER"],
].map(([account_id, account_name, account_type]) => ({
  account_id,
  account_name,
  account_type: account_type as "MASTER" | "COPIER",
  total_signals: 0,
  total_executions: 0,
  total_copied_trades: 0,
  win_rate: 0,
  net_pnl: 0,
  max_drawdown: 0,
  synchronization_status: "PENDING",
  last_sync_time: null,
  simulation_only: true,
  demo_execution: true,
  live_execution_enabled: false,
  broker_execution_enabled: false,
}));

export const emptySyncStatus: AccountSyncStatus = {
  synchronization_status: "PENDING",
  copier_health: "PENDING",
  last_sync_time: null,
  execution_consistency: "NO_COPIER_ACTIVITY",
  simulation_only: true,
  demo_execution: true,
  live_execution_enabled: false,
  broker_execution_enabled: false,
};

function buildUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

async function fetchAccountAnalyticsRequest<T>(endpoint: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(buildUrl(endpoint), { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function fetchAccountAnalyticsAccounts(): Promise<AccountAnalyticsSummary[]> {
  return fetchAccountAnalyticsRequest("/client-analytics/accounts", emptyAccounts);
}

export function fetchMasterAccountAnalytics(): Promise<AccountAnalyticsSummary> {
  return fetchAccountAnalyticsRequest("/client-analytics/accounts/master", emptyAccounts[0]);
}

export function fetchCopierAccountAnalytics(): Promise<AccountAnalyticsSummary[]> {
  return fetchAccountAnalyticsRequest("/client-analytics/accounts/copiers", emptyAccounts.slice(1));
}

export function fetchAccountAnalytics(accountId: string): Promise<AccountAnalyticsSummary | null> {
  return fetchAccountAnalyticsRequest(`/client-analytics/accounts/${accountId}`, null);
}

export function fetchAccountSyncStatus(): Promise<AccountSyncStatus> {
  return fetchAccountAnalyticsRequest("/client-analytics/accounts/sync-status", emptySyncStatus);
}
