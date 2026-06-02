const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type StrategyPerformanceSummary = {
  symbol: string;
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  wait_signals: number;
  avg_confidence: number;
  confidence_quality: string;
  execution_rate: number;
  execution_quality: string;
  risk_pass_rate: number;
  risk_quality: string;
  session_efficiency: number;
  strategy_score: number;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
};

export type StrategyOverview = {
  total_strategies: number;
  avg_confidence: number;
  avg_risk_efficiency: number;
  avg_execution_efficiency: number;
  top_ranked_strategy: string | null;
  session_efficiency: number;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
};

export const emptyStrategies: StrategyPerformanceSummary[] = ["XAUUSD", "EURUSD", "NIFTY50"].map((symbol) => ({
  symbol,
  total_signals: 0,
  buy_signals: 0,
  sell_signals: 0,
  wait_signals: 0,
  avg_confidence: 0,
  confidence_quality: symbol === "NIFTY50" ? "PLACEHOLDER" : "NONE",
  execution_rate: 0,
  execution_quality: symbol === "NIFTY50" ? "PLACEHOLDER" : "NONE",
  risk_pass_rate: 0,
  risk_quality: symbol === "NIFTY50" ? "PLACEHOLDER" : "NONE",
  session_efficiency: 0,
  strategy_score: 0,
  simulation_only: true,
  demo_execution: true,
  live_execution_enabled: false,
  broker_execution_enabled: false,
}));

export const emptyOverview: StrategyOverview = {
  total_strategies: 3,
  avg_confidence: 0,
  avg_risk_efficiency: 0,
  avg_execution_efficiency: 0,
  top_ranked_strategy: null,
  session_efficiency: 0,
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

async function fetchStrategy<T>(endpoint: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(buildUrl(endpoint), { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function fetchStrategyOverview(): Promise<StrategyOverview> {
  return fetchStrategy("/client-analytics/strategy/overview", emptyOverview);
}

export function fetchStrategyPerformance(): Promise<StrategyPerformanceSummary[]> {
  return fetchStrategy("/client-analytics/strategy/performance", emptyStrategies);
}

export function fetchStrategyRankings(): Promise<Array<Record<string, unknown>>> {
  return fetchStrategy("/client-analytics/strategy/rankings", []);
}

export function fetchStrategySessionEfficiency(): Promise<Array<Record<string, unknown>>> {
  return fetchStrategy("/client-analytics/strategy/session-efficiency", []);
}

export function fetchStrategyComparison(): Promise<Record<string, unknown>> {
  return fetchStrategy("/client-analytics/strategy/comparison", {});
}
