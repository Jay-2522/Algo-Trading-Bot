const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type ClientReport = {
  report_id: string;
  report_type: string;
  period: string;
  generated_at: string;
  summary: Record<string, unknown>;
  symbol_performance: Array<Record<string, unknown>>;
  session_performance: Array<Record<string, unknown>>;
  risk_summary: Record<string, unknown>;
  trade_journal_summary: Record<string, unknown>;
  execution_summary: Record<string, unknown>;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
};

export const emptyClientReport: ClientReport = {
  report_id: "empty_report",
  report_type: "DAILY",
  period: "TODAY",
  generated_at: "",
  summary: {
    total_signals: 0,
    total_demo_executions: 0,
    win_rate: 0,
    net_pnl: 0,
    empty_report: true,
  },
  symbol_performance: [],
  session_performance: [],
  risk_summary: {},
  trade_journal_summary: {},
  execution_summary: {},
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

async function fetchReport<T>(endpoint: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(buildUrl(endpoint), { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function fetchDailyReport(): Promise<ClientReport> {
  return fetchReport("/client-analytics/reports/daily", emptyClientReport);
}

export function fetchWeeklyReport(): Promise<ClientReport> {
  return fetchReport("/client-analytics/reports/weekly", { ...emptyClientReport, report_type: "WEEKLY", period: "CURRENT_WEEK" });
}

export function fetchSymbolReport(symbol: string): Promise<ClientReport> {
  return fetchReport(`/client-analytics/reports/symbol/${symbol}`, { ...emptyClientReport, report_type: "SYMBOL", period: symbol });
}

export function fetchRiskReport(): Promise<ClientReport> {
  return fetchReport("/client-analytics/reports/risk", { ...emptyClientReport, report_type: "RISK", period: "CURRENT" });
}

export async function fetchReportJsonExport(): Promise<Record<string, unknown>> {
  return fetchReport("/client-analytics/reports/export/json", emptyClientReport);
}

export async function fetchReportCsvExport(): Promise<string> {
  try {
    const response = await fetch(buildUrl("/client-analytics/reports/export/csv"), { cache: "no-store" });
    if (!response.ok) return "report_id,report_type,period,symbol,total_signals,demo_executions,win_rate,net_pnl\n";
    return await response.text();
  } catch {
    return "report_id,report_type,period,symbol,total_signals,demo_executions,win_rate,net_pnl\n";
  }
}
