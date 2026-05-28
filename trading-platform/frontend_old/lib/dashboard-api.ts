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
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchDashboardBundle(): Promise<DashboardBundle> {
  const [status, overview, cards, summary, alerts] = await Promise.allSettled([
    fetchJson<DashboardStatus>("/dashboard/status"),
    fetchJson<DashboardOverview>("/dashboard/overview"),
    fetchJson<DashboardCardData[]>("/dashboard/cards"),
    fetchJson<DashboardSummary>("/dashboard/summary"),
    fetchJson<Array<Record<string, unknown>>>("/monitoring/alerts"),
  ]);

  return {
    status: status.status === "fulfilled" ? status.value : null,
    overview: overview.status === "fulfilled" ? overview.value : null,
    cards: cards.status === "fulfilled" ? cards.value : [],
    summary: summary.status === "fulfilled" ? summary.value : null,
    alerts: alerts.status === "fulfilled" ? alerts.value : [],
  };
}
