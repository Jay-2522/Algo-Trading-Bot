export type ApiRecord = Record<string, unknown>;

export type ClientOrderPayload = {
  symbol: "EURUSD";
  action: "BUY" | "SELL";
  lot: 0.01;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

function buildApiUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(buildApiUrl(endpoint), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(endpoint: string, payload: ApiRecord = {}): Promise<T> {
  const response = await fetch(buildApiUrl(endpoint), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchClientOperatingDashboard() {
  const requests = {
    account: fetchJson<ApiRecord>("/mt5-demo/account"),
    eurusdTick: fetchJson<ApiRecord>("/mt5-demo/market-data/tick/EURUSD"),
    xauusdTick: fetchJson<ApiRecord>("/mt5-demo/market-data/tick/XAUUSD"),
    openPositions: fetchJson<ApiRecord>("/mt5-demo/position-monitor/open"),
    recentTrades: fetchJson<ApiRecord[]>("/trade-journal/persistence/recent?limit=20"),
    journalSummary: fetchJson<ApiRecord>("/trade-journal/persistence/summary"),
    outcomeSummary: fetchJson<ApiRecord>("/analytics/outcomes/summary"),
    guardedStatus: fetchJson<ApiRecord>("/mt5-demo/guarded-demo-order/status"),
  };

  const entries = await Promise.allSettled(Object.entries(requests).map(async ([key, promise]) => [key, await promise] as const));
  const data: ApiRecord = {};
  const errors: string[] = [];
  for (const entry of entries) {
    if (entry.status === "fulfilled") {
      const [key, value] = entry.value;
      data[key] = value;
    } else {
      errors.push(entry.reason instanceof Error ? entry.reason.message : "Dashboard request failed");
    }
  }
  return { data, errors };
}

function guardedPayload(payload: ClientOrderPayload): ApiRecord {
  return {
    ...payload,
    environment: "DEMO",
    manual_confirmation: true,
    acknowledge_demo_only: true,
    acknowledge_no_live_trading: true,
    acknowledge_no_order_placement_today: true,
    acknowledge_single_trade_only: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
    execution_allowed: false,
  };
}

export function previewClientDemoTrade(payload: ClientOrderPayload) {
  return postJson<ApiRecord>("/mt5-demo/demo-approval-workflow/run", guardedPayload(payload));
}

export function sendGuardedClientDemoTrade(payload: ClientOrderPayload) {
  return postJson<ApiRecord>("/mt5-demo/guarded-demo-order/send", {
    ...guardedPayload(payload),
    execute_single_demo_order_now: true,
  });
}

export function syncClientPositionsToJournal() {
  return postJson<ApiRecord>("/mt5-demo/positions/sync-journal");
}

export function syncClientLifecycle() {
  return postJson<ApiRecord>("/mt5-demo/lifecycle/sync");
}

export function syncClientCloseHistory() {
  return postJson<ApiRecord>("/mt5-demo/close-sync/run");
}
