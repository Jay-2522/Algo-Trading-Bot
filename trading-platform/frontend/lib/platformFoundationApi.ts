const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type PlatformFoundationBundle = {
  journalSummary: Record<string, unknown>;
  strategyOverview: Record<string, unknown>;
  reportsStatus: Record<string, unknown>;
  copierReadiness: Record<string, unknown>;
};

export const emptyPlatformFoundationBundle: PlatformFoundationBundle = {
  journalSummary: {
    total_trades: 0,
    closed_demo_trades: 0,
    win_rate: 0,
    net_pnl: 0,
    message: "No completed demo trades yet.",
    simulation_only: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
  },
  strategyOverview: {
    total_signals: 0,
    approved_demo_trades: 0,
    sent_demo_orders: 0,
    closed_demo_trades: 0,
    win_rate: 0,
    net_pnl: 0,
    message: "No completed demo trades yet.",
    simulation_only: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
  },
  reportsStatus: {
    status: "READY",
    message: "Reports will populate after demo trades are recorded.",
    simulation_only: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
  },
  copierReadiness: {
    status: "FUTURE_EXECUTION_REQUIRED",
    message: "Trade copier is architecture-ready but execution-disabled.",
    simulation_only: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
  },
};

function buildUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

async function fetchSafe<T>(endpoint: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(buildUrl(endpoint), { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function fetchPlatformFoundationBundle(): Promise<PlatformFoundationBundle> {
  const [journalSummary, strategyOverview, reportsStatus, copierReadiness] = await Promise.all([
    fetchSafe<Record<string, unknown>>("/trade-journal/persistence/summary", emptyPlatformFoundationBundle.journalSummary),
    fetchSafe<Record<string, unknown>>("/client-analytics/strategy-dashboard/overview", emptyPlatformFoundationBundle.strategyOverview),
    fetchSafe<Record<string, unknown>>("/client-analytics/reports-v2/status", emptyPlatformFoundationBundle.reportsStatus),
    fetchSafe<Record<string, unknown>>("/trade-copier/readiness", emptyPlatformFoundationBundle.copierReadiness),
  ]);

  return { journalSummary, strategyOverview, reportsStatus, copierReadiness };
}
