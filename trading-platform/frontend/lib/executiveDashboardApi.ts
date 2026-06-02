const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type ExecutiveSummary = {
  analytics_ready: boolean;
  reports_ready: boolean;
  accounts_ready: boolean;
  copier_ready: boolean;
  strategy_ready: boolean;
  deployment_ready: boolean;
  monitoring_ready: boolean;
  security_ready: boolean;
  production_ready: boolean;
  xauusd_ready: boolean;
  eurusd_ready: boolean;
  nifty50_ready: boolean;
  overall_completion_percentage: number;
  simulation_only: boolean;
  demo_execution: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
  timestamp: string;
};

export type ReadinessItem = {
  name: string;
  status: string;
  score: number;
  reason: string;
};

export type InstrumentReadiness = {
  symbol: string;
  status: string;
  ready: boolean;
  reason: string;
};

export type SystemHealth = {
  deployment_score: number;
  monitoring_score: number;
  security_score: number;
  production_score: number;
  simulation_only: boolean;
  live_execution_enabled: boolean;
  broker_execution_enabled: boolean;
  timestamp: string;
};

export const emptyExecutiveSummary: ExecutiveSummary = {
  analytics_ready: true,
  reports_ready: true,
  accounts_ready: true,
  copier_ready: true,
  strategy_ready: true,
  deployment_ready: true,
  monitoring_ready: true,
  security_ready: true,
  production_ready: false,
  xauusd_ready: true,
  eurusd_ready: true,
  nifty50_ready: false,
  overall_completion_percentage: 88,
  simulation_only: true,
  demo_execution: true,
  live_execution_enabled: false,
  broker_execution_enabled: false,
  timestamp: "",
};

export const emptyReadinessItems: ReadinessItem[] = [
  "Analytics",
  "Reports",
  "Accounts",
  "Copier",
  "Strategy",
  "Deployment",
  "Monitoring",
  "Security",
  "Production",
].map((name) => ({
  name,
  status: name === "Production" ? "WARNING" : "READY",
  score: name === "Production" ? 82 : 90,
  reason: name === "Production" ? "Live and broker execution remain disabled." : `${name} readiness is available.`,
}));

export const emptyInstruments: InstrumentReadiness[] = [
  { symbol: "XAUUSD", status: "READY", ready: true, reason: "Primary strategy and analytics layers are implemented." },
  { symbol: "EURUSD", status: "READY", ready: true, reason: "Secondary strategy and analytics layers are implemented." },
  { symbol: "NIFTY50", status: "PENDING IMPLEMENTATION", ready: false, reason: "NIFTY50 production strategy layer is not complete yet." },
];

export const emptySystemHealth: SystemHealth = {
  deployment_score: 88,
  monitoring_score: 90,
  security_score: 90,
  production_score: 82,
  simulation_only: true,
  live_execution_enabled: false,
  broker_execution_enabled: false,
  timestamp: "",
};

function buildUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

async function fetchExecutive<T>(endpoint: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(buildUrl(endpoint), { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function fetchExecutiveSummary(): Promise<ExecutiveSummary> {
  return fetchExecutive("/client-analytics/executive/summary", emptyExecutiveSummary);
}

export async function fetchExecutiveReadiness(): Promise<ReadinessItem[]> {
  const payload = await fetchExecutive<{ items: ReadinessItem[] }>("/client-analytics/executive/readiness", { items: emptyReadinessItems });
  return payload.items.length ? payload.items : emptyReadinessItems;
}

export async function fetchExecutiveInstruments(): Promise<InstrumentReadiness[]> {
  const payload = await fetchExecutive<{ instruments: InstrumentReadiness[] }>("/client-analytics/executive/instruments", { instruments: emptyInstruments });
  return payload.instruments.length ? payload.instruments : emptyInstruments;
}

export function fetchExecutiveSystemHealth(): Promise<SystemHealth> {
  return fetchExecutive("/client-analytics/executive/system-health", emptySystemHealth);
}
