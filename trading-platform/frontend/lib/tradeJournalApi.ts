const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type ExecutionStatus =
  | "WAIT"
  | "QUEUED"
  | "APPROVED"
  | "DEMO_FILLED"
  | "DEMO_REJECTED"
  | "MT5_UNAVAILABLE"
  | "COPIED"
  | "BLOCKED"
  | "FAILED_SAFE"
  | "NOT_AVAILABLE";

export type TradeJournalEntry = {
  trade_id: string;
  time: string | null;
  symbol: string;
  action: string;
  confidence: number;
  status: ExecutionStatus;
  demo_result: string;
  pnl: number | null;
  risk_notes: string[];
  signal_id?: string | null;
  decision_id?: string | null;
  queue_preview_id?: string | null;
  approval_id?: string | null;
  candidate_id?: string | null;
  final_execution_id?: string | null;
  copy_batch_id?: string | null;
  confirmation_id?: string | null;
  rejection_reasons?: string[];
  warnings?: string[];
  simulation_only?: boolean;
  demo_execution?: boolean;
  live_execution_enabled?: boolean;
  broker_execution_enabled?: boolean;
};

export type ExecutionTimelineStep = {
  label: string;
  status: "Complete" | "Pending" | "Blocked" | "Not Available";
  detail: string;
};

export type ExecutionHistory = {
  entries: TradeJournalEntry[];
  timeline: ExecutionTimelineStep[];
  raw: {
    flows: Array<Record<string, unknown>>;
    finalExecutions: Array<Record<string, unknown>>;
    copierResults: Array<Record<string, unknown>>;
    confirmations: Array<Record<string, unknown>>;
  };
};

const lifecycleSteps = [
  "Strategy Signal",
  "Bridge Validation",
  "Risk Check",
  "Queue Preview",
  "Approval",
  "Demo Candidate",
  "Final Demo Execution",
  "Trade Copier",
  "Confirmation",
];

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

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value ? value : fallback;
}

function number(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function arrayText(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function normalizeFinalExecution(execution: Record<string, unknown>): TradeJournalEntry {
  const status = text(execution.execution_status, "NOT_AVAILABLE") as ExecutionStatus;
  const finalExecutionId = text(execution.final_execution_id, "");
  return {
    trade_id: finalExecutionId || text(execution.candidate_id, "unknown_trade"),
    time: text(execution.timestamp, "") || null,
    symbol: text(execution.symbol, "N/A"),
    action: text(execution.action, "N/A"),
    confidence: 0,
    status: status.includes("BLOCKED") ? "BLOCKED" : status,
    demo_result: status,
    pnl: null,
    risk_notes: arrayText(execution.rejection_reasons),
    signal_id: null,
    decision_id: text(execution.decision_id, "") || null,
    queue_preview_id: text(execution.queue_preview_id, "") || null,
    approval_id: text(execution.approval_id, "") || null,
    candidate_id: text(execution.candidate_id, "") || null,
    final_execution_id: finalExecutionId || null,
    copy_batch_id: text(execution.copy_batch_id, "") || null,
    confirmation_id: null,
    rejection_reasons: arrayText(execution.rejection_reasons),
    warnings: [],
    simulation_only: true,
    demo_execution: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
  };
}

function normalizeJournalEntry(entry: Record<string, unknown>): TradeJournalEntry {
  const pnl = entry.pnl === undefined || entry.pnl === null ? null : number(entry.pnl, 0);
  return {
    trade_id: text(entry.journal_id, text(entry.entry_id, "journal_entry")),
    time: text(entry.timestamp, "") || null,
    symbol: text(entry.symbol, "N/A"),
    action: text(entry.side, text(entry.action, "N/A")),
    confidence: number(entry.confidence, 0),
    status: text(entry.outcome, "NOT_AVAILABLE").toUpperCase() as ExecutionStatus,
    demo_result: text(entry.outcome, "Not available"),
    pnl,
    risk_notes: [],
    rejection_reasons: [],
    warnings: [],
    simulation_only: true,
    demo_execution: true,
    live_execution_enabled: false,
    broker_execution_enabled: false,
  };
}

function buildTimeline(entries: TradeJournalEntry[], history: ExecutionHistory["raw"]): ExecutionTimelineStep[] {
  const hasEntry = entries.length > 0;
  const hasFlow = history.flows.length > 0;
  const hasFinal = history.finalExecutions.length > 0;
  const hasCopier = history.copierResults.length > 0;
  const hasConfirmation = history.confirmations.length > 0;
  const blocked = entries.some((entry) => entry.status === "BLOCKED" || entry.status === "FAILED_SAFE" || entry.status === "DEMO_REJECTED");
  const states = [
    hasEntry || hasFlow,
    hasFlow,
    hasEntry,
    hasFlow || hasFinal,
    hasFinal,
    hasFinal,
    hasFinal,
    hasCopier,
    hasConfirmation,
  ];
  return lifecycleSteps.map((label, index) => ({
    label,
    status: blocked && index >= 2 && !states[index] ? "Blocked" : states[index] ? "Complete" : hasEntry ? "Pending" : "Not Available",
    detail: states[index] ? "Recorded from backend audit data." : "No record available yet.",
  }));
}

export async function fetchTradeJournalEntries(): Promise<TradeJournalEntry[]> {
  const [journalEntries, finalExecutions] = await Promise.all([
    fetchSafe<Array<Record<string, unknown>>>("/trade-journal/recent?limit=100", []),
    fetchSafe<Array<Record<string, unknown>>>("/strategy-execution-bridge/final-demo-execution/executions", []),
  ]);
  const normalizedFinal = finalExecutions.map(normalizeFinalExecution);
  const normalizedJournal = journalEntries.map(normalizeJournalEntry);
  return [...normalizedFinal, ...normalizedJournal];
}

export async function fetchExecutionHistory(): Promise<ExecutionHistory> {
  const [entries, flows, finalExecutions, copierResults, confirmations] = await Promise.all([
    fetchTradeJournalEntries(),
    fetchSafe<Array<Record<string, unknown>>>("/strategy-execution-bridge/e2e/flows", []),
    fetchSafe<Array<Record<string, unknown>>>("/strategy-execution-bridge/final-demo-execution/executions", []),
    fetchSafe<Array<Record<string, unknown>>>("/trade-copier/execution-results", []),
    fetchSafe<Array<Record<string, unknown>>>("/execution-confirmation/confirmations", []),
  ]);
  const raw = { flows, finalExecutions, copierResults, confirmations };
  return {
    entries,
    timeline: buildTimeline(entries, raw),
    raw,
  };
}

export async function fetchTradeDetail(tradeId: string): Promise<TradeJournalEntry | null> {
  const entries = await fetchTradeJournalEntries();
  return entries.find((entry) => entry.trade_id === tradeId || entry.final_execution_id === tradeId) ?? null;
}

export const emptyExecutionHistory: ExecutionHistory = {
  entries: [],
  timeline: lifecycleSteps.map((label) => ({
    label,
    status: "Not Available",
    detail: "No record available yet.",
  })),
  raw: {
    flows: [],
    finalExecutions: [],
    copierResults: [],
    confirmations: [],
  },
};
