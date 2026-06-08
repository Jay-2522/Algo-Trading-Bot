const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type ClientAnalyticsOverview = {
  status: string;
  total_signals: number;
  total_demo_executions: number;
  total_copy_batches: number;
  total_risk_blocks: number;
  total_news_blocks: number;
  active_symbols: string[];
  supported_symbols: string[];
  best_symbol: string | null;
  worst_symbol: string | null;
  win_rate: number;
  net_pnl: number;
  profit_factor: number;
  max_drawdown: number;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
  timestamp?: string;
};

export type SymbolPerformanceSummary = {
  symbol: string;
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  wait_signals: number;
  demo_executions: number;
  wins: number;
  losses: number;
  win_rate: number;
  net_pnl: number;
  avg_confidence: number;
  best_trade: number;
  worst_trade: number;
  timestamp?: string;
};

export type SessionPerformanceSummary = {
  session: string;
  total_signals: number;
  demo_executions: number;
  wins: number;
  losses: number;
  win_rate: number;
  net_pnl: number;
  avg_confidence: number;
  timestamp?: string;
};

export type RiskAnalyticsSummary = {
  total_risk_checks: number;
  approved: number;
  blocked: number;
  news_blocks: number;
  regime_blocks: number;
  risk_engine_blocks: number;
  most_common_block_reason: string | null;
  timestamp?: string;
};

export type DemoPositionsSummary = {
  status: string;
  environment: string;
  open_positions: number;
  total_floating_pnl: number;
  symbols: string[];
  largest_floating_profit: number;
  largest_floating_loss: number;
  lifecycle_open_count: number;
  lifecycle_closed_count: number;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
};

export const emptyAnalyticsOverview: ClientAnalyticsOverview = {
  status: "OPERATIONAL",
  total_signals: 0,
  total_demo_executions: 0,
  total_copy_batches: 0,
  total_risk_blocks: 0,
  total_news_blocks: 0,
  active_symbols: [],
  supported_symbols: ["XAUUSD", "EURUSD", "NIFTY50"],
  best_symbol: null,
  worst_symbol: null,
  win_rate: 0,
  net_pnl: 0,
  profit_factor: 0,
  max_drawdown: 0,
  simulation_only: true,
  demo_execution: true,
  live_execution_enabled: false,
  broker_execution_enabled: false,
};

export const emptyRiskAnalytics: RiskAnalyticsSummary = {
  total_risk_checks: 0,
  approved: 0,
  blocked: 0,
  news_blocks: 0,
  regime_blocks: 0,
  risk_engine_blocks: 0,
  most_common_block_reason: null,
};

export const emptySymbols: SymbolPerformanceSummary[] = ["XAUUSD", "EURUSD", "NIFTY50"].map((symbol) => ({
  symbol,
  total_signals: 0,
  buy_signals: 0,
  sell_signals: 0,
  wait_signals: 0,
  demo_executions: 0,
  wins: 0,
  losses: 0,
  win_rate: 0,
  net_pnl: 0,
  avg_confidence: 0,
  best_trade: 0,
  worst_trade: 0,
}));

export const emptySessions: SessionPerformanceSummary[] = ["ASIAN", "LONDON", "NEW_YORK", "OVERLAP", "UNKNOWN"].map((session) => ({
  session,
  total_signals: 0,
  demo_executions: 0,
  wins: 0,
  losses: 0,
  win_rate: 0,
  net_pnl: 0,
  avg_confidence: 0,
}));

export const emptyDemoPositionsSummary: DemoPositionsSummary = {
  status: "READY",
  environment: "DEMO",
  open_positions: 0,
  total_floating_pnl: 0,
  symbols: [],
  largest_floating_profit: 0,
  largest_floating_loss: 0,
  lifecycle_open_count: 0,
  lifecycle_closed_count: 0,
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

async function fetchAnalytics<T>(endpoint: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(buildUrl(endpoint), { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function fetchClientAnalyticsOverview(): Promise<ClientAnalyticsOverview> {
  return fetchAnalytics("/client-analytics/overview", emptyAnalyticsOverview);
}

export function fetchClientAnalyticsSymbols(): Promise<SymbolPerformanceSummary[]> {
  return fetchAnalytics("/client-analytics/symbols", emptySymbols);
}

export function fetchClientAnalyticsSessions(): Promise<SessionPerformanceSummary[]> {
  return fetchAnalytics("/client-analytics/sessions", emptySessions);
}

export function fetchClientAnalyticsRisk(): Promise<RiskAnalyticsSummary> {
  return fetchAnalytics("/client-analytics/risk", emptyRiskAnalytics);
}

export function fetchClientAnalyticsSnapshot(): Promise<ClientAnalyticsOverview> {
  return fetchAnalytics("/client-analytics/snapshots/latest", emptyAnalyticsOverview);
}

export function fetchDemoPositionsSummary(): Promise<DemoPositionsSummary> {
  return fetchAnalytics("/client-analytics/demo-positions/summary", emptyDemoPositionsSummary);
}
