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
  errors: string[];
};

const endpoints = {
  status: "/dashboard/status",
  overview: "/dashboard/overview",
  cards: "/dashboard/cards",
  summary: "/dashboard/summary",
  alerts: "/monitoring/alerts",
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
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
  ]);

  const [status, overview, cards, summary, alerts] = results;
  const errors = results
    .map((result, index) => errorMessage(Object.keys(endpoints)[index], result))
    .filter((message): message is string => Boolean(message));

  return {
    status: status.status === "fulfilled" ? status.value : null,
    overview: overview.status === "fulfilled" ? overview.value : null,
    cards: cards.status === "fulfilled" ? cards.value : [],
    summary: summary.status === "fulfilled" ? summary.value : null,
    alerts: alerts.status === "fulfilled" ? alerts.value : [],
    errors,
  };
}
