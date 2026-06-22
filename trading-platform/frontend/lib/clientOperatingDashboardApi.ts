export type ApiRecord = Record<string, unknown>;

type FetchJsonResult<T> = {
  data: T;
  error: string | null;
  ok: boolean;
};

export type ClientOrderPayload = {
  symbol: "EURUSD" | "XAUUSD";
  action: "BUY" | "SELL";
  lot: 0.01;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward_ratio?: number;
  signal_confidence?: number;
  signal_hash?: string;
  setup_reason?: string;
  signal_timestamp?: string;
  strategy_metadata?: ApiRecord;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

function buildApiUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

function fetchFailureMessage(endpoint: string, error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") return `${endpoint} timed out`;
  if (error instanceof TypeError && error.message.toLowerCase().includes("fetch")) return "Backend unavailable";
  if (error instanceof Error) return error.message;
  return `${endpoint} request failed`;
}

function isFetchJsonResult<T>(value: unknown): value is FetchJsonResult<T> {
  return typeof value === "object" && value !== null && "ok" in value && "data" in value;
}

async function fetchJson<T>(endpoint: string, fallback: T, timeoutMs = 5000): Promise<FetchJsonResult<T>> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(buildApiUrl(endpoint), { cache: "no-store", signal: controller.signal });
    if (!response.ok) {
      return { data: fallback, error: `${endpoint} returned ${response.status}`, ok: false };
    }
    return { data: (await response.json()) as T, error: null, ok: true };
  } catch (error) {
    return { data: fallback, error: fetchFailureMessage(endpoint, error), ok: false };
  } finally {
    clearTimeout(timeout);
  }
}

async function postJson<T>(endpoint: string, payload: ApiRecord = {}, timeoutMs = 10000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(buildApiUrl(endpoint), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`${endpoint} returned ${response.status}`);
    }
    return response.json() as Promise<T>;
  } catch (error) {
    throw new Error(fetchFailureMessage(endpoint, error));
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchClientOperatingDashboard() {
  const requests = {
    account: fetchJson<ApiRecord>("/mt5-demo/account", {}),
    eurusdTick: fetchJson<ApiRecord>("/mt5-demo/market-data/tick/EURUSD", {}),
    xauusdTick: fetchJson<ApiRecord>("/mt5-demo/market-data/tick/XAUUSD", {}),
    niftyTick: fetchJson<ApiRecord>("/mt5-demo/market-data/tick/NIFTY50", {}),
    marketScope: fetchJson<ApiRecord[]>("/market-scope/instruments/status", []),
    clientSignals: fetchJson<ApiRecord>("/client-signals-engine/current", { signals: [] }),
    brokerAccounts: fetchJson<ApiRecord>("/brokers/accounts", { accounts: [] }),
    brokerCopyReadiness: fetchJson<ApiRecord>("/brokers/copy-readiness", { plans: [] }),
    vantageXauusdStatus: fetchJson<ApiRecord>("/mt5-demo/vantage/xauusd/status", {}),
    vantageXauusdPreview: postJson<ApiRecord>("/mt5-demo/vantage/xauusd/test-order/preview", {
      symbol: "XAUUSD",
      side: "BUY",
      lot: 0.01,
      live_execution_enabled: false,
      broker_execution_enabled: false,
    }),
    openPositions: fetchJson<ApiRecord>("/mt5-demo/position-monitor/open", { positions: [] }),
    recentTrades: fetchJson<ApiRecord[]>("/trade-journal/persistence/recent?limit=100", []),
    journalSummary: fetchJson<ApiRecord>("/trade-journal/persistence/summary", {}),
    outcomeSummary: fetchJson<ApiRecord>("/analytics/outcomes/summary", {}),
    guardedStatus: fetchJson<ApiRecord>("/mt5-demo/guarded-demo-order/status", {}),
    executionMode: fetchJson<ApiRecord>("/execution-mode/status", {}),
    autoValidation: fetchJson<ApiRecord>("/auto-validation/status", {}, 2500),
  };

  const entries = await Promise.allSettled(Object.entries(requests).map(async ([key, promise]) => [key, await promise] as const));
  const data: ApiRecord = {};
  const errors: string[] = [];
  for (const entry of entries) {
    if (entry.status === "fulfilled") {
      const [key, result] = entry.value;
      if (isFetchJsonResult<unknown>(result)) {
        if (result.ok) {
          data[key] = result.data;
        } else if (typeof result.error === "string") {
          errors.push(result.error);
        }
      } else {
        data[key] = result;
      }
    } else {
      errors.push(entry.reason instanceof Error ? entry.reason.message : "Dashboard request failed");
    }
  }
  return { data, errors };
}

export async function fetchClientOpenPositions() {
  const result = await fetchJson<ApiRecord>("/mt5-demo/position-monitor/open", { positions: [] }, 3000);
  return {
    positions: Array.isArray(result.data.positions) ? (result.data.positions.filter((item) => typeof item === "object" && item !== null) as ApiRecord[]) : [],
    error: result.error,
    ok: result.ok,
  };
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
  const symbolPath = payload.symbol.toLowerCase();
  return postJson<ApiRecord>(`/mt5-demo/vantage/${symbolPath}/test-order/preview`, guardedPayload(payload));
}

export async function fetchClientMarketPrices() {
  try {
    const [eurusdTick, xauusdTick, niftyTick, marketScope] = await Promise.all([
      fetchJson<ApiRecord>("/mt5-demo/market-data/tick/EURUSD", {}, 1500),
      fetchJson<ApiRecord>("/mt5-demo/market-data/tick/XAUUSD", {}, 1500),
      fetchJson<ApiRecord>("/mt5-demo/market-data/tick/NIFTY50", {}, 1500),
      fetchJson<ApiRecord[]>("/market-scope/instruments/status", [], 1500),
    ]);
    const errors = [eurusdTick.error, xauusdTick.error, niftyTick.error, marketScope.error].filter((error): error is string => Boolean(error));
    return {
      errors,
      eurusdTick: eurusdTick.ok ? eurusdTick.data : null,
      marketScope: marketScope.ok ? marketScope.data : null,
      niftyTick: niftyTick.ok ? niftyTick.data : null,
      ok: errors.length === 0,
      xauusdTick: xauusdTick.ok ? xauusdTick.data : null,
    };
  } catch (error) {
    return { errors: [fetchFailureMessage("/mt5-demo/market-data/tick", error)], eurusdTick: null, marketScope: null, niftyTick: null, ok: false, xauusdTick: null };
  }
}

export async function sendPortalChatMessage(payload: ApiRecord): Promise<{ rateLimited?: boolean; reply: string; retryAfterSeconds?: number }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: controller.signal,
    });
    const data = (await response.json().catch(() => ({}))) as ApiRecord;
    if (!response.ok) {
      const error = new Error("The assistant is temporarily busy. Please try again in a few seconds.") as Error & { rateLimited?: boolean; retryAfterSeconds?: number };
      error.rateLimited = data.rateLimited === true || response.status === 429;
      error.retryAfterSeconds = typeof data.retryAfterSeconds === "number" && Number.isFinite(data.retryAfterSeconds) ? data.retryAfterSeconds : undefined;
      throw error;
    }
    return {
      rateLimited: data.rateLimited === true,
      reply: typeof data.reply === "string" ? data.reply : "I could not produce a response from the trading assistant.",
      retryAfterSeconds: typeof data.retryAfterSeconds === "number" && Number.isFinite(data.retryAfterSeconds) ? data.retryAfterSeconds : undefined,
    };
  } catch (error) {
    if (error instanceof Error && "rateLimited" in error) throw error;
    throw new Error(fetchFailureMessage("/api/chat", error));
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchReasonMessages(): Promise<ApiRecord[]> {
  const response = await fetch("/api/reasons", { cache: "no-store" });
  const data = (await response.json().catch(() => ({}))) as ApiRecord;
  if (!response.ok) return [];
  return Array.isArray(data.messages) ? (data.messages.filter((item) => typeof item === "object" && item !== null) as ApiRecord[]) : [];
}

export async function syncReasonMessages(contexts: ApiRecord[]): Promise<ApiRecord[]> {
  const response = await fetch("/api/reasons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contexts }),
    cache: "no-store",
  });
  const data = (await response.json().catch(() => ({}))) as ApiRecord;
  if (!response.ok) return [];
  return Array.isArray(data.messages) ? (data.messages.filter((item) => typeof item === "object" && item !== null) as ApiRecord[]) : [];
}

export function sendGuardedClientDemoTrade(payload: ClientOrderPayload) {
  const symbolPath = payload.symbol.toLowerCase();
  return postJson<ApiRecord>(`/mt5-demo/vantage/${symbolPath}/test-order`, {
    ...guardedPayload(payload),
    confirm: true,
  });
}

export function syncClientPositionsToJournal() {
  return postJson<ApiRecord>("/mt5-demo/positions/sync-journal");
}

export function syncClientLifecycle() {
  return postJson<ApiRecord>("/mt5-demo/lifecycle/sync");
}

export function syncAutoValidationLifecycle() {
  return postJson<ApiRecord>("/auto-validation/sync-lifecycle");
}

export function runAutoValidationExitManagement() {
  return postJson<ApiRecord>("/auto-validation/run-exit-management");
}

export function syncClientCloseHistory() {
  return postJson<ApiRecord>("/mt5-demo/close-sync/run");
}

export async function fetchClientTradeHistory(limit = 500) {
  const result = await fetchJson<ApiRecord[]>(`/trade-journal/persistence/recent?limit=${Math.max(1, Math.min(limit, 500))}`, []);
  return result.data;
}

export async function fetchClientSignals() {
  try {
    const result = await fetchJson<ApiRecord>("/client-signals-engine/current", { signals: [] }, 5000);
    return { errors: result.error ? [result.error] : [], ok: result.ok, signals: result.ok ? result.data : { signals: [] } };
  } catch (error) {
    return { errors: [fetchFailureMessage("/client-signals-engine/current", error)], ok: false, signals: { signals: [] } };
  }
}

export function refreshClientSignals() {
  return postJson<ApiRecord>("/client-signals-engine/refresh");
}

export function setExecutionMode(executionMode: "AUTO" | "APPROVAL") {
  return postJson<ApiRecord>("/execution-mode/set", { execution_mode: executionMode });
}

export function approveExecutionModeSignal(approvalId: string) {
  return postJson<ApiRecord>("/execution-mode/approve-signal", { approval_id: approvalId });
}

export function rejectExecutionModeSignal(approvalId: string, reason = "Rejected from dashboard.") {
  return postJson<ApiRecord>("/execution-mode/reject-signal", { approval_id: approvalId, reason });
}

export function startAutoValidation(payload: ApiRecord = {}) {
  return postJson<ApiRecord>("/auto-validation/start", payload);
}

export async function fetchAutoValidationStatus() {
  const result = await fetchJson<ApiRecord>("/auto-validation/status", {}, 2500);
  return { errors: result.error ? [result.error] : [], ok: result.ok, status: result.ok ? result.data : null };
}

export async function fetchAutoValidationScanDiagnostics() {
  const result = await fetchJson<ApiRecord>("/auto-validation/scan-diagnostics", {}, 2500);
  return { errors: result.error ? [result.error] : [], ok: result.ok, diagnostics: result.ok ? result.data : null };
}

export function pauseAutoValidation() {
  return postJson<ApiRecord>("/auto-validation/pause");
}

export function resumeAutoValidation() {
  return postJson<ApiRecord>("/auto-validation/resume");
}

export function stopAutoValidation(reason = "Stopped from dashboard.") {
  return postJson<ApiRecord>("/auto-validation/stop", { reason });
}

export function emergencyStopAutoValidation() {
  return postJson<ApiRecord>("/auto-validation/emergency-stop");
}
