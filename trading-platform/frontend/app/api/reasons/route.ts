import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ReasonStatus = "Accepted" | "Rejected" | "Waiting" | "SCAN_RESULT" | "OPEN_CONFIRMED" | "CLOSED" | "CLOSED_WIN" | "CLOSED_LOSS" | "RISK_HALTED" | "RISK_CLEARED" | "Error";
type ApiRecord = Record<string, unknown>;
type ReasonMessage = {
  candles_loaded?: number | null;
  candles_required?: number | null;
  data_source?: string;
  id: string;
  event_id?: string;
  groqGenerated: boolean;
  reason: string;
  rejection_reason?: string;
  ticket?: string;
  signal_hash?: string;
  side?: string;
  strategy_profile?: string;
  decision?: string;
  risk_status?: string;
  execution_status?: string;
  order_opened?: boolean;
  mt5_retcode?: string;
  mt5_comment?: string;
  source?: "groq" | "rule" | "execution";
  status: ReasonStatus;
  symbol: string;
  timestamp: string;
  timeframe?: string;
  validation_status?: string;
  final_decision_reason?: string;
  decision_reason?: string;
  passed_rules?: string[];
  failed_rules?: string[];
  advisory_warnings?: string[];
  RR?: number | null;
  required_rr?: number | null;
  confirmation_score?: number | null;
  confirmation_required?: number | null;
  confirmation_total?: number | null;
  confirmation_passed?: string[];
  confirmation_missing?: string[];
  bos_status?: string;
  fvg_status?: string;
  h4_history_status?: string;
  m15_history_status?: string;
  liquidity_sweep_status?: string;
  trend_alignment_status?: string;
  history_ready?: boolean | null;
  requested_symbol?: string;
  resolved_symbol?: string;
  mt5_last_error?: string;
  process_id?: string;
  connection_id?: string;
  validation_session_id?: string;
  round_id?: string;
  round_number?: number | null;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = process.env.GROQ_MODEL || "gemma2-9b-it";
const GROQ_FALLBACK_MODEL = process.env.GROQ_FALLBACK_MODEL || "";
const STORE_PATH = path.join(process.cwd(), "..", "data", "reason_panel", "reason_messages.json");
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const MAX_STORED_REASONS = 1000;
const BUSY_MESSAGE = "The assistant is temporarily busy. Please try again in a few seconds.";
const NOISY_PATTERNS = [
  /indian market integration pending/i,
  /integration pending/i,
  /backend status/i,
  /system debug/i,
  /unsupported client dashboard symbol/i,
  /generic project/i,
];

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : value === null || value === undefined ? "" : String(value).trim();
}

function isBadText(value: unknown): boolean {
  const normalized = text(value).toLowerCase();
  return (
    !normalized ||
    normalized === "unknown" ||
    normalized === "null" ||
    normalized === "undefined" ||
    normalized === "[object object]" ||
    normalized.includes("unspecified reason") ||
    normalized.includes("because unknown") ||
    normalized.includes("accepted because unknown") ||
    normalized.includes("rejected because unknown") ||
    normalized.includes("unknown reason") ||
    normalized.includes("trade trade")
  );
}

function cleanDisplayText(value: unknown): string {
  const cleaned = text(value).replace(/\s+/g, " ").replace(/\.\.+/g, ".").trim();
  return isBadText(cleaned) ? "" : cleaned;
}

function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.replace(/,/g, ""));
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function firstText(record: ApiRecord, keys: string[]): string {
  for (const key of keys) {
    const value = cleanDisplayText(record[key]);
    if (value) return value;
  }
  return "";
}

function firstNumber(record: ApiRecord, keys: string[]): number | null {
  for (const key of keys) {
    const value = numberValue(record[key]);
    if (value !== null) return value;
  }
  return null;
}

function booleanValue(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  const normalized = text(value).toLowerCase();
  if (["true", "yes", "passed", "pass", "confirmed", "ready"].includes(normalized)) return true;
  if (["false", "no", "failed", "fail", "missing", "waiting", "pending"].includes(normalized)) return false;
  return null;
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
}

function firstKnownBoolean(record: ApiRecord | ReasonMessage, keys: string[]): boolean | null {
  for (const key of keys) {
    const value = booleanValue((record as ApiRecord)[key]);
    if (value !== null) return value;
  }
  return null;
}

function includesText(values: unknown, pattern: RegExp): boolean {
  return arrayText(values).some((value) => pattern.test(value));
}

function round3Label(value: string): string {
  const normalized = value.replace(/_/g, " ").trim().toLowerCase();
  if (normalized.includes("bos")) return "BOS";
  if (normalized.includes("fvg")) return "FVG";
  if (normalized.includes("liquidity")) return "Liquidity sweep";
  if (normalized.includes("trend")) return "Trend alignment";
  if (normalized.includes("h4")) return "H4 history";
  if (normalized.includes("m15")) return "M15 history";
  if (normalized.includes("session")) return "London/NY session";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function uniqueLabels(values: string[]): string[] {
  const seen = new Set<string>();
  return values.map(round3Label).filter((value) => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function round3ConfirmationLabels(record: ApiRecord | ReasonMessage, kind: "present" | "missing"): string[] {
  const explicit = uniqueLabels(arrayText((record as ApiRecord)[kind === "present" ? "confirmation_passed" : "confirmation_missing"]));
  if (explicit.length) return explicit;
  const states = [
    ["BOS", firstKnownBoolean(record, ["bosConfirmed"]) ?? (text((record as ApiRecord).bos_status).toUpperCase() === "PRESENT" ? true : text((record as ApiRecord).bos_status).toUpperCase() === "MISSING" ? false : null)],
    ["FVG", firstKnownBoolean(record, ["fvgConfirmed"]) ?? (text((record as ApiRecord).fvg_status).toUpperCase() === "PRESENT" ? true : text((record as ApiRecord).fvg_status).toUpperCase() === "MISSING" ? false : null)],
    ["Liquidity sweep", firstKnownBoolean(record, ["liquiditySweep"]) ?? (text((record as ApiRecord).liquidity_sweep_status).toUpperCase() === "PRESENT" ? true : text((record as ApiRecord).liquidity_sweep_status).toUpperCase() === "MISSING" ? false : null)],
    ["Trend alignment", firstKnownBoolean(record, ["trendAlignment"]) ?? (text((record as ApiRecord).trend_alignment_status).toUpperCase() === "ALIGNED" ? true : text((record as ApiRecord).trend_alignment_status).toUpperCase() === "NOT_ALIGNED" ? false : null)],
  ] as const;
  return states.filter(([, state]) => state === (kind === "present")).map(([label]) => label);
}

function round3DecisionBlock(record: ApiRecord | ReasonMessage, status: ReasonStatus): string | null {
  const symbol = text((record as ApiRecord).symbol).toUpperCase() || "This setup";
  const score = firstNumber(record as ApiRecord, ["confirmation_score", "confirmationScore"]);
  const required = firstNumber(record as ApiRecord, ["confirmation_required", "confirmationRequired"]) ?? 2;
  const total = firstNumber(record as ApiRecord, ["confirmation_total", "confirmationTotal"]) ?? 4;
  const rr = firstNumber(record as ApiRecord, ["RR", "risk_reward", "riskReward", "rr"]);
  const requiredRr = firstNumber(record as ApiRecord, ["required_rr", "requiredRR", "minimum_rr", "minimumRR"]) ?? 2;
  const ticket = firstText(record as ApiRecord, ["ticket", "mt5_ticket", "mt5Ticket"]);
  const failedRules = arrayText((record as ApiRecord).failed_rules);
  const blockers = [...arrayText((record as ApiRecord).blockers), ...failedRules];
  const h4 = firstKnownBoolean(record, ["h4HistoryValid"]) ?? (text((record as ApiRecord).h4_history_status).toUpperCase() === "AVAILABLE" ? true : text((record as ApiRecord).h4_history_status).toUpperCase() === "INSUFFICIENT" ? false : null);
  const m15 = firstKnownBoolean(record, ["m15HistoryValid"]) ?? (text((record as ApiRecord).m15_history_status).toUpperCase() === "AVAILABLE" ? true : text((record as ApiRecord).m15_history_status).toUpperCase() === "INSUFFICIENT" ? false : null);
  const session = firstKnownBoolean(record, ["sessionValid"]) ?? (includesText((record as ApiRecord).passed_rules, /SESSION_LONDON_NY/i) ? true : includesText(failedRules, /SESSION_OUTSIDE/i) ? false : null);

  if (status === "Rejected" && rr !== null && rr < requiredRr) return `RR ${formatNumber(rr)} below required ${formatNumber(requiredRr)}`;
  if (status === "Rejected" && blockers.some((item) => /SPREAD/i.test(item))) return "Spread too high";
  if (status === "Rejected" && session === false) return "No session bonus";

  const present = [
    h4 === true ? "H4 history" : "",
    m15 === true ? "M15 history" : "",
    session === true ? "London/NY session" : "",
    ...round3ConfirmationLabels(record, "present"),
  ].filter(Boolean);
  const missing = score !== null && score >= required ? [] : [
    h4 === false ? "H4 history" : "",
    m15 === false ? "M15 history" : "",
    session === false ? "London/NY session" : "",
    ...round3ConfirmationLabels(record, "missing"),
  ].filter(Boolean);

  if (status === "Accepted") {
    const lines = [`${symbol} trade opened successfully.`, `Score ${formatNumber(score ?? present.length)}/${formatNumber(total)}`];
    for (const item of uniqueLabels(present).filter((item) => !/history|session/i.test(item))) lines.push(`${item} ✓`);
    if (rr !== null) lines.push(`RR ${formatNumber(rr)}`);
    if (ticket) lines.push(`Ticket ${ticket}`);
    return lines.join("\n");
  }

  if (score !== null || present.length || missing.length) {
    const lines = [`Score ${formatNumber(score ?? present.length)}/${formatNumber(required)}`];
    if (present.length) {
      lines.push("Present:");
      for (const item of uniqueLabels(present)) lines.push(`- ${item} ✓`);
    }
    if (missing.length) {
      lines.push("Missing:");
      for (const item of uniqueLabels(missing)) lines.push(`- ${item} ✗`);
    }
    return lines.join("\n");
  }
  return null;
}

function stableId(context: ApiRecord): string {
  const existingId = text(context.id);
  if (existingId) return existingId;
  const symbol = text(context.symbol).toUpperCase();
  const status = normalizedDecisionStatus(context);
  const timestamp = text(context.timestamp);
  const ticket = firstText(context, ["ticket", "mt5_ticket", "mt5Ticket", "order_ticket", "orderTicket"]);
  if (ticket) return ["reason", symbol, status, "ticket", ticket].filter(Boolean).join("-");
  const signalHash = text(context.signalHash || context.signal_hash);
  if (signalHash) return ["reason", symbol, status, "signal", signalHash, timestamp].filter(Boolean).join("-");
  const raw = JSON.stringify({
    symbol,
    status,
    timestamp,
    reason: text(context.reason || context.setupReason || context.whatNeedsToHappenNext),
    timeframe: text(context.timeframe),
  });
  let hash = 0;
  for (let index = 0; index < raw.length; index += 1) {
    hash = (hash * 31 + raw.charCodeAt(index)) >>> 0;
  }
  return `reason-${hash.toString(16)}`;
}

function normalizeStatus(value: unknown): ReasonStatus {
  const status = text(value).toUpperCase();
  if (status.includes("RISK_HALTED")) return "RISK_HALTED";
  if (status.includes("RISK_CLEARED")) return "RISK_CLEARED";
  if (status.includes("SCAN_RESULT")) return "SCAN_RESULT";
  if (status.includes("OPEN_CONFIRMED")) return "OPEN_CONFIRMED";
  if (status.includes("CLOSED_WIN")) return "CLOSED_WIN";
  if (status.includes("CLOSED_LOSS")) return "CLOSED_LOSS";
  if (status.includes("CLOSED")) return "CLOSED";
  if (status.includes("APPROVED") || status.includes("ACCEPT") || status.includes("READY") || status.includes("WIN")) return "Accepted";
  if (status.includes("REJECT") || status.includes("BLOCK") || status.includes("DENIED") || status.includes("LOSS")) return "Rejected";
  if (status.includes("ERROR") || status.includes("FAIL") || status.includes("DISCONNECT")) return "Error";
  return "Waiting";
}

function arrayText(value: unknown): string[] {
  return Array.isArray(value) ? value.map(text).filter(Boolean) : [];
}

function hasExecutionTicket(record: ApiRecord | ReasonMessage): boolean {
  const ticket = firstText(record as ApiRecord, ["ticket", "mt5_ticket", "mt5Ticket", "order_ticket", "orderTicket"]);
  return Boolean(ticket && ticket !== "0");
}

function isExecutionAccepted(record: ApiRecord | ReasonMessage): boolean {
  if (!hasExecutionTicket(record)) return false;
  const source = text((record as ReasonMessage).source).toLowerCase();
  const status = firstText(record as ApiRecord, ["status", "execution_status", "executionStatus", "validation_status", "validationStatus"]).toUpperCase();
  return (
    (record as ReasonMessage).order_opened === true ||
    (record as ApiRecord).mt5_order_sent === true ||
    source === "execution" ||
    status.includes("ORDER_SENT") ||
    status.includes("DEMO_ORDER_SENT")
  );
}

function hasHardRejection(record: ApiRecord | ReasonMessage): boolean {
  const combined = [
    firstText(record as ApiRecord, ["reason", "setupReason", "whatNeedsToHappenNext", "rejection_reason", "final_decision_reason"]),
    firstText(record as ApiRecord, ["status", "execution_status", "executionStatus", "validation_status", "validationStatus", "risk_status", "riskStatus"]),
    ...arrayText((record as ApiRecord).blockers),
    ...arrayText((record as ApiRecord).failed_rules),
  ]
    .join(" ")
    .toUpperCase();
  return /RR[^A-Z0-9]*(?:BELOW|LOW|<)|RISK_REWARD[^A-Z0-9]*(?:BELOW|LOW)|SPREAD[^A-Z0-9]*(?:TOO_HIGH|TOO HIGH|HIGH|UNAVAILABLE)|RISK[^A-Z0-9]*(?:REJECT|DENIED|FAILED)|SL_TP|HISTORY[^A-Z0-9]*(?:INSUFFICIENT|UNAVAILABLE|MISSING)|INSUFFICIENT[^A-Z0-9]*(?:H4|M15|HISTORY)|OUTSIDE[^A-Z0-9]*(?:LONDON|NY|NEW YORK|SESSION)|SESSION_OUTSIDE|GUARDED_SENDER_REJECTED|LIVE_ACCOUNT|DEMO_ACCOUNT|MT5_DISCONNECTED/.test(combined);
}

function hasWaitingIncomplete(record: ApiRecord | ReasonMessage): boolean {
  const combined = [
    firstText(record as ApiRecord, ["reason", "setupReason", "whatNeedsToHappenNext", "rejection_reason", "final_decision_reason"]),
    firstText(record as ApiRecord, ["status", "execution_status", "executionStatus", "validation_status", "validationStatus", "risk_status", "riskStatus"]),
    ...arrayText((record as ApiRecord).blockers),
    ...arrayText((record as ApiRecord).failed_rules),
  ]
    .join(" ")
    .toUpperCase();
  return /CONFIRMATION_SCORE|CONFIDENCE|MISSING[^A-Z0-9]*(?:BOS|FVG|LIQUIDITY|TREND)|(?:BOS|FVG|LIQUIDITY|TREND)[^A-Z0-9]*(?:MISSING|WAITING|PENDING)|NO_READY_APPROVED_SIGNAL|SESSION[^A-Z0-9]*(?:OPENING|PENDING)/.test(combined);
}

function normalizedDecisionStatus(record: ApiRecord | ReasonMessage): ReasonStatus {
  const rawStatus = normalizeStatus((record as ReasonMessage).status);
  const combined = [record.reason, (record as ReasonMessage).final_decision_reason, (record as ReasonMessage).decision_reason].map(text).join(" ");
  if (rawStatus === "RISK_HALTED" || rawStatus === "RISK_CLEARED") return rawStatus;
  if (/CLOSED_LOSS|Result:\s*LOSS|closed\./i.test(combined)) return "CLOSED_LOSS";
  if (/CLOSED_WIN|Result:\s*WIN/i.test(combined)) return "CLOSED_WIN";
  if (rawStatus === "SCAN_RESULT") return "SCAN_RESULT";
  if (rawStatus === "OPEN_CONFIRMED") return "OPEN_CONFIRMED";
  if (rawStatus === "CLOSED_LOSS" || rawStatus === "CLOSED_WIN" || rawStatus === "CLOSED") return rawStatus;
  if (isExecutionAccepted(record)) return "Accepted";
  if (rawStatus === "Error") return "Error";
  if (hasHardRejection(record)) return "Rejected";
  if (hasWaitingIncomplete(record)) return "Waiting";
  if (rawStatus === "Rejected") return "Rejected";
  return "Waiting";
}

function isMeaningfulContext(context: ApiRecord): boolean {
  const symbol = text(context.symbol).toUpperCase();
  if (!["EURUSD", "XAUUSD", "NIFTY50"].includes(symbol)) return false;
  if (symbol === "NIFTY50" && context.niftyConnected !== true) return false;
  const reason = text(context.reason || context.setupReason || context.whatNeedsToHappenNext);
  if (NOISY_PATTERNS.some((pattern) => pattern.test(reason))) return false;
  return Boolean(symbol && (reason || text(context.status) || text(context.signalHash) || text(context.ticket)));
}

function validatorDiagnostics(context: ApiRecord): Pick<ReasonMessage, "advisory_warnings" | "candles_loaded" | "candles_required" | "confirmation_missing" | "confirmation_passed" | "confirmation_required" | "confirmation_score" | "confirmation_total" | "data_source" | "decision_reason" | "failed_rules" | "final_decision_reason" | "passed_rules" | "rejection_reason" | "required_rr" | "RR" | "timeframe" | "validation_status" | "history_ready" | "requested_symbol" | "resolved_symbol" | "mt5_last_error" | "process_id" | "connection_id"> {
  return {
    candles_loaded: firstNumber(context, ["candles_loaded", "candlesLoaded", "loaded_candles", "loadedCandles", "bars_loaded", "barsLoaded", "history_bars", "candle_count"]),
    candles_required: firstNumber(context, ["candles_required", "candlesRequired", "required_candles", "requiredCandles", "minimum_candles", "minimumCandles", "min_bars", "minBars"]),
    data_source: firstText(context, ["data_source", "dataSource", "source", "feed_source", "feedSource"]),
    rejection_reason: firstText(context, ["rejection_reason", "rejectionReason", "final_rejection_reason", "finalRejectionReason", "reason", "setupReason", "whatNeedsToHappenNext"]),
    decision_reason: firstText(context, ["decision_reason", "decisionReason"]),
    final_decision_reason: firstText(context, ["final_decision_reason", "finalDecisionReason"]),
    passed_rules: arrayText(context.passed_rules),
    failed_rules: arrayText(context.failed_rules),
    advisory_warnings: arrayText(context.advisory_warnings),
    RR: firstNumber(context, ["RR", "risk_reward", "riskReward", "rr"]),
    required_rr: firstNumber(context, ["required_rr", "requiredRR", "minimum_rr", "minimumRR"]),
    confirmation_score: firstNumber(context, ["confirmation_score", "confirmationScore"]),
    confirmation_required: firstNumber(context, ["confirmation_required", "confirmationRequired"]),
    confirmation_total: firstNumber(context, ["confirmation_total", "confirmationTotal"]),
    confirmation_passed: arrayText(context.confirmation_passed),
    confirmation_missing: arrayText(context.confirmation_missing),
    timeframe: firstText(context, ["timeframe", "tf", "validation_timeframe", "validationTimeframe", "failed_timeframe", "failedTimeframe"]).toUpperCase(),
    validation_status: firstText(context, ["validation_status", "validationStatus", "status", "execution_status", "executionStatus", "status_level", "risk_status"]),
    history_ready: booleanValue(context.history_ready ?? context.historyReady),
    requested_symbol: firstText(context, ["requested_symbol", "requestedSymbol"]),
    resolved_symbol: firstText(context, ["resolved_symbol", "resolvedSymbol"]),
    mt5_last_error: firstText(context, ["mt5_last_error", "mt5LastError"]),
    process_id: firstText(context, ["process_id", "processId"]),
    connection_id: firstText(context, ["connection_id", "connectionId"]),
  };
}

async function readStore(): Promise<ReasonMessage[]> {
  try {
    const raw = await readFile(STORE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    const messages = Array.isArray(parsed)
      ? (parsed.filter((item) => {
          if (!item || typeof item !== "object") return false;
          const record = item as ApiRecord;
          return Boolean(text(record.id) && text(record.reason) && text(record.symbol));
        }) as ReasonMessage[])
      : [];
    return dedupeMeaningfully(sortNewestFirst(messages.map(sanitizeReasonMessage).filter((message) => !isLegacyReasonMessage(message))));
  } catch {
    return [];
  }
}

async function writeStore(messages: ReasonMessage[]): Promise<void> {
  await mkdir(path.dirname(STORE_PATH), { recursive: true });
  await writeFile(STORE_PATH, JSON.stringify(dedupeMeaningfully(sortNewestFirst(messages.map(sanitizeReasonMessage).filter((message) => !isLegacyReasonMessage(message)))).slice(0, MAX_STORED_REASONS), null, 2), "utf-8");
}

async function activeRoundScope(): Promise<{ sessionId: string; roundId: string; roundNumber: number | null }> {
  try {
    const url = new URL("/auto-validation/status", API_BASE_URL);
    url.searchParams.set("_ts", String(Date.now()));
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return { sessionId: "", roundId: "", roundNumber: null };
    const payload = (await response.json()) as ApiRecord;
    const session = payload.session && typeof payload.session === "object" && !Array.isArray(payload.session) ? (payload.session as ApiRecord) : {};
    const sessionId = text(payload.active_session_id || session.session_id || session.validation_session_id);
    return {
      sessionId,
      roundId: sessionId,
      roundNumber: numberValue(session.round_number),
    };
  } catch {
    return { sessionId: "", roundId: "", roundNumber: null };
  }
}

function timestampValue(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function sortNewestFirst(messages: ReasonMessage[]): ReasonMessage[] {
  return [...messages].sort((left, right) => {
    const timestampDelta = timestampValue(text(right.timestamp)) - timestampValue(text(left.timestamp));
    if (timestampDelta !== 0) return timestampDelta;
    return text(right.event_id || right.id).localeCompare(text(left.event_id || left.id));
  });
}

function acceptedExecutionFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "This signal";
  const side = cleanDisplayText(message.side).toUpperCase();
  const ticket = cleanDisplayText(message.ticket);
  const score = message.confirmation_score ?? null;
  const total = message.confirmation_total ?? 4;
  const rr = message.RR ?? message.required_rr ?? null;
  if (ticket && score !== null) return `${symbol} trade opened successfully. Ticket: ${ticket}. Score ${formatNumber(score)}/${formatNumber(total)}. RR ${rr !== null ? formatNumber(rr) : "2.0"}. Risk approved.`;
  const sideText = side && !["TRADE", "POSITION"].includes(side) ? ` as a ${side} trade` : "";
  return `${symbol} was accepted and opened${sideText} because guarded demo validation passed, risk status was approved, and MT5 executed the order successfully.${ticket ? ` Ticket: ${ticket}.` : ""}`;
}

function openConfirmedFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "EURUSD";
  const side = cleanDisplayText(message.side).toUpperCase() || "TRADE";
  const ticket = cleanDisplayText(message.ticket);
  const adaptiveLevel = cleanDisplayText((message as ApiRecord).adaptive_level) || "0";
  return [
    "OPEN_CONFIRMED",
    `Symbol: ${symbol}`,
    `Direction: ${side}`,
    `Ticket: ${ticket || "Unavailable"}`,
    `Entry: ${cleanDisplayText((message as ApiRecord).entry) || "Unavailable"}`,
    `Current price: ${cleanDisplayText((message as ApiRecord).current_price) || "Unavailable"}`,
    `SL: ${cleanDisplayText((message as ApiRecord).sl) || "Unavailable"}`,
    `TP: ${cleanDisplayText((message as ApiRecord).tp) || "Unavailable"}`,
    `Floating P&L: ${cleanDisplayText((message as ApiRecord).floating_pnl) || "0"}`,
    `Adaptive level: ${adaptiveLevel}`,
  ].join("\n");
}

function closedConfirmedFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "EURUSD";
  const side = cleanDisplayText(message.side).toUpperCase() || "TRADE";
  const ticket = cleanDisplayText(message.ticket) || cleanDisplayText(message.reason).match(/Ticket:\s*([0-9]+)/i)?.[1] || "Unavailable";
  const status = normalizedDecisionStatus(message);
  const pnl = cleanDisplayText((message as ApiRecord).pnl) || cleanDisplayText((message as ApiRecord).net_pnl) || cleanDisplayText((message as ApiRecord).profit_loss) || cleanDisplayText(message.reason).match(/P&L:\s*([^.\n]+)/i)?.[1] || "0";
  const exitReason = cleanDisplayText((message as ApiRecord).exit_reason) || cleanDisplayText(message.reason).match(/Exit:\s*([^.\n]+)/i)?.[1] || "MT5 history confirmed close";
  return [
    status,
    `Symbol: ${symbol}`,
    `Direction: ${side}`,
    `Ticket: ${ticket}`,
    `P&L: ${pnl}`,
    `Exit reason: ${exitReason}`,
  ].join("\n");
}

function rejectedFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "This signal";
  const decisionReason = cleanDisplayText(message.decision_reason);
  if (decisionReason && !isLegacyStrategyDiagnostic(decisionReason) && !/required round 3|rule failed/i.test(decisionReason)) return decisionReason;
  const finalReason = cleanDisplayText(message.final_decision_reason);
  if (finalReason) return finalReason;
  const failed = Array.isArray(message.failed_rules) ? message.failed_rules : [];
  if (failed.includes("RR_BELOW_2_0")) return `Rejected: RR ${formatNumber(message.RR ?? 0)} below required ${formatNumber(message.required_rr ?? 2)}.`;
  if (failed.some((item) => /SPREAD/i.test(item))) return "Rejected: spread too high.";
  if (failed.includes("CONFIRMATION_SCORE_BELOW_2")) {
    const missing = Array.isArray(message.confirmation_missing) && message.confirmation_missing.length ? ` Missing ${message.confirmation_missing.join(", ")}.` : "";
    return `Rejected: Score ${formatNumber(message.confirmation_score ?? 0)}/${formatNumber(message.confirmation_required ?? 2)}.${missing}`;
  }
  const diagnostic = cleanDisplayText(message.rejection_reason);
  if (diagnostic) return `${symbol} was rejected because ${diagnostic.replace(/\.$/, "")}.`;
  return `${symbol} rejected: no qualified Round 3 signal was ready.`;
}

function waitingFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "This signal";
  const canonical = round3DecisionBlock(message, "Waiting");
  return canonical || `${symbol} waiting:\nScore 0/2\nMissing:\n- BOS ✗\n- FVG ✗\n- Liquidity sweep ✗\n- Trend alignment ✗`;
}

function isLegacyStrategyDiagnostic(value: string): boolean {
  const diagnostic = value.toLowerCase();
  const legacyConfidenceGate = diagnostic.includes("confidence") && (diagnostic.includes("75") || diagnostic.includes("threshold") || diagnostic.includes("needs"));
  const hardSessionGate = diagnostic.includes("outside") && (diagnostic.includes("london") || diagnostic.includes("new york") || diagnostic.includes("ny"));
  const hardOrderBlockGate = diagnostic.includes("order block") && diagnostic.includes("not confirmed");
  return legacyConfidenceGate || hardSessionGate || hardOrderBlockGate;
}

function isLegacyReasonMessage(message: ReasonMessage): boolean {
  const combined = [
    message.reason,
    message.rejection_reason,
    message.decision_reason,
    message.final_decision_reason,
    message.validation_status,
    ...(Array.isArray(message.failed_rules) ? message.failed_rules : []),
  ]
    .map(text)
    .join(" ");
  return (
    isLegacyStrategyDiagnostic(combined) ||
    /outside\s+(?:london|new york|ny)|outside\s+.*session/i.test(combined) ||
    /confidence\s*(?:threshold|needs|below|62|75)|threshold\s*75/i.test(combined) ||
    /\bwatchlist\b/i.test(combined) ||
    /old round 3 rule failed|required round 3 rule failed|rule failed/i.test(combined)
  );
}

function sanitizeReasonMessage(message: ReasonMessage): ReasonMessage {
  const status = normalizedDecisionStatus(message);
  let reason = cleanDisplayText(message.reason);
  const rejectionReason = cleanDisplayText(message.rejection_reason);
  const canonicalRound3Reason = round3DecisionBlock(message, status);
  const extractedTicket = cleanDisplayText(message.ticket) || (reason.match(/Ticket:\s*([0-9]+)/i)?.[1] ?? "");
  if (status === "OPEN_CONFIRMED") {
    reason = /^OPEN_CONFIRMED\b/i.test(reason) ? reason : openConfirmedFallback(message);
  }
  if ((status === "CLOSED_LOSS" || status === "CLOSED_WIN" || status === "CLOSED") && (/waiting/i.test(reason) || !/^CLOSED/i.test(reason))) {
    reason = closedConfirmedFallback({ ...message, ticket: extractedTicket });
  }
  if (canonicalRound3Reason && (isLegacyStrategyDiagnostic(reason) || /required round 3|rule failed|confirmation score 0\/2/i.test(reason) || status !== "Error")) {
    reason = canonicalRound3Reason;
  } else if (isLegacyStrategyDiagnostic(reason) || /required round 3|rule failed|confirmation score 0\/2/i.test(reason)) {
    reason = "";
  }
  if (status === "Waiting" && /^accepted\b/i.test(reason)) {
    reason = "";
  }
  if (status === "Waiting" && /halted/i.test(reason) && /BOS|FVG|liquidity|trend|confirmation|confidence/i.test(reason)) {
    const symbol = text(message.symbol).toUpperCase() || "This setup";
    reason = reason.replace(/\bTrade was halted due to\b/i, `${symbol} waiting:`).replace(/\bTrade halted due to\b/i, `${symbol} waiting:`);
  }
  if (!reason) {
    if (status === "Accepted") reason = acceptedExecutionFallback(message);
    else if (status === "Rejected") reason = rejectedFallback({ ...message, rejection_reason: rejectionReason });
    else if (status === "Waiting") reason = waitingFallback(message);
    else reason = `${text(message.symbol).toUpperCase() || "This signal"} needs attention because validation could not complete cleanly.`;
  }
  return {
    ...message,
    event_id: cleanDisplayText(message.event_id) || cleanDisplayText(message.id),
    id: cleanDisplayText(message.id),
    data_source: cleanDisplayText(message.data_source),
    mt5_comment: cleanDisplayText(message.mt5_comment),
    mt5_retcode: cleanDisplayText(message.mt5_retcode),
    reason,
    rejection_reason: rejectionReason,
    decision_reason: cleanDisplayText(message.decision_reason),
    final_decision_reason: cleanDisplayText(message.final_decision_reason),
    passed_rules: Array.isArray(message.passed_rules) ? message.passed_rules.map(cleanDisplayText).filter(Boolean) : [],
    failed_rules: Array.isArray(message.failed_rules) ? message.failed_rules.map(cleanDisplayText).filter(Boolean) : [],
    advisory_warnings: Array.isArray(message.advisory_warnings) ? message.advisory_warnings.map(cleanDisplayText).filter(Boolean) : [],
    RR: message.RR ?? null,
    required_rr: message.required_rr ?? null,
    confirmation_score: message.confirmation_score ?? null,
    confirmation_required: message.confirmation_required ?? null,
    confirmation_total: message.confirmation_total ?? null,
    confirmation_passed: Array.isArray(message.confirmation_passed) ? message.confirmation_passed.map(cleanDisplayText).filter(Boolean) : [],
    confirmation_missing: Array.isArray(message.confirmation_missing) ? message.confirmation_missing.map(cleanDisplayText).filter(Boolean) : [],
    side: cleanDisplayText(message.side).toUpperCase(),
    signal_hash: cleanDisplayText(message.signal_hash),
    source: message.source,
    status,
    strategy_profile: cleanDisplayText(message.strategy_profile),
    symbol: text(message.symbol).toUpperCase(),
    ticket: extractedTicket,
    timeframe: cleanDisplayText(message.timeframe).toUpperCase(),
    validation_status: cleanDisplayText(message.validation_status),
    history_ready: booleanValue(message.history_ready),
    requested_symbol: cleanDisplayText(message.requested_symbol),
    resolved_symbol: cleanDisplayText(message.resolved_symbol),
    mt5_last_error: cleanDisplayText(message.mt5_last_error),
    process_id: cleanDisplayText(message.process_id),
    connection_id: cleanDisplayText(message.connection_id),
    validation_session_id: cleanDisplayText(message.validation_session_id),
    round_id: cleanDisplayText(message.round_id),
    round_number: numberValue(message.round_number),
  };
}

function normalizeReasonForDedupe(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").replace(/[.。]+$/g, "").trim();
}

function meaningfulReasonKey(message: ReasonMessage): string {
  const sessionId = text(message.validation_session_id || message.round_id) || "NO_SESSION";
  const ticket = text(message.ticket);
  const signalHash = text(message.signal_hash);
  if (ticket) return [sessionId, text(message.symbol).toUpperCase(), message.status, "ticket", ticket].join("|");
  if (text(message.source) === "execution" && signalHash) return [sessionId, text(message.symbol).toUpperCase(), message.status, "signal", signalHash].join("|");
  return [sessionId, text(message.symbol).toUpperCase(), message.status, normalizeReasonForDedupe(text(message.reason))].join("|");
}

function dedupeMeaningfully(messages: ReasonMessage[]): ReasonMessage[] {
  const seenIds = new Set<string>();
  const seenReasons = new Set<string>();
  return messages.filter((message) => {
    const id = text(message.id);
    const reasonKey = meaningfulReasonKey(message);
    if (!id || !text(message.reason) || seenIds.has(id) || seenReasons.has(reasonKey)) return false;
    seenIds.add(id);
    seenReasons.add(reasonKey);
    return true;
  });
}

function containsBlocker(blockers: string[], patterns: RegExp[]): boolean {
  return blockers.some((blocker) => patterns.some((pattern) => pattern.test(blocker)));
}

function joinReasons(parts: string[]): string {
  if (parts.length <= 1) return parts[0] ?? "risk approved";
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

function ruleBasedReason(context: ApiRecord): string {
  const symbol = text(context.symbol).toUpperCase() || "This setup";
  const status = normalizedDecisionStatus(context);
  const finalDecisionReason = cleanDisplayText(context.final_decision_reason);
  const decisionReason = cleanDisplayText(context.decision_reason);
  const riskReward = numberValue(context.riskReward);
  const requiredRR = numberValue(context.requiredRR) ?? 2.0;
  const confirmationScore = firstNumber(context, ["confirmation_score", "confirmationScore"]);
  const bosConfirmed = booleanValue(context.bosConfirmed);
  const fvgConfirmed = booleanValue(context.fvgConfirmed);
  const liquiditySweep = booleanValue(context.liquiditySweep);
  const trendAlignment = booleanValue(context.trendAlignment);
  const sessionValid = booleanValue(context.sessionValid);
  const h4HistoryValid = booleanValue(context.h4HistoryValid);
  const m15HistoryValid = booleanValue(context.m15HistoryValid);
  const historyReady = booleanValue(context.history_ready ?? context.historyReady);
  const historyTimeframe = firstText(context, ["timeframe", "tf", "validation_timeframe", "validationTimeframe", "failed_timeframe", "failedTimeframe"]).toUpperCase();
  const requestedSymbol = firstText(context, ["requested_symbol", "requestedSymbol"]) || symbol;
  const resolvedSymbol = firstText(context, ["resolved_symbol", "resolvedSymbol"]) || requestedSymbol;
  const candlesLoaded = firstNumber(context, ["candles_loaded", "candlesLoaded", "loaded_candles", "loadedCandles", "bars_loaded", "barsLoaded", "history_bars", "candle_count"]);
  const candlesRequired = firstNumber(context, ["candles_required", "candlesRequired", "required_candles", "requiredCandles", "minimum_candles", "minimumCandles", "min_bars", "minBars"]);
  const orderBlockConfirmed = booleanValue(context.orderBlockConfirmed);
  const blockers = Array.isArray(context.blockers) ? context.blockers.map(text).filter(Boolean) : [];
  const failedRules = arrayText(context.failed_rules);
  const missingConfirmations = arrayText(context.confirmation_missing);
  const suppliedReason = text(context.reason || context.setupReason || context.whatNeedsToHappenNext);
  const cleanSuppliedReason = cleanDisplayText(suppliedReason);

  if (decisionReason) return decisionReason;
  if (historyReady === false && historyTimeframe && candlesLoaded !== null && candlesRequired !== null) {
    return `Waiting for MT5 ${historyTimeframe} history sync: ${requestedSymbol} resolved as ${resolvedSymbol}, loaded ${formatNumber(candlesLoaded)} / required ${formatNumber(candlesRequired)} candles.`;
  }
  const canonicalRound3Reason = round3DecisionBlock(context, status);
  if (canonicalRound3Reason) return canonicalRound3Reason;
  if (finalDecisionReason && !(status !== "Accepted" && /^accepted:/i.test(finalDecisionReason))) return finalDecisionReason;
  if (finalDecisionReason && status !== "Accepted" && /^accepted:/i.test(finalDecisionReason)) {
    return `${symbol} waiting: setup passed; waiting for MT5 order execution.`;
  }
  if (containsBlocker([...blockers, ...failedRules], [/spread/i])) {
    return "Rejected: spread too high.";
  }
  if (containsBlocker([...blockers, ...failedRules], [/SL_TP_REQUIRED/i, /risk/i])) {
    return "Rejected: risk validation failed.";
  }
  if (riskReward !== null && riskReward < requiredRR) {
    return `Rejected: RR ${formatNumber(riskReward)} below required ${formatNumber(requiredRR)}.`;
  }
  if (containsBlocker([...blockers, ...failedRules], [/risk.?reward/i, /\brr\b/i]) && riskReward !== null) {
    return `Rejected: RR ${formatNumber(riskReward)} below required ${formatNumber(requiredRR)}.`;
  }
  if (sessionValid === false || containsBlocker([...blockers, ...failedRules], [/session/i, /london/i, /new york/i])) {
    return "Rejected: outside London/NY session.";
  }
  if ((confirmationScore !== null && confirmationScore < 2) || containsBlocker([...blockers, ...failedRules], [/confirmation.*score/i, /CONFIRMATION_SCORE_BELOW_2/i])) {
    const missing = missingConfirmations.length ? ` Missing ${missingConfirmations.join(", ")}.` : " Missing one more from BOS, FVG, liquidity sweep, or trend alignment.";
    return `${status === "Rejected" ? "Rejected" : "Waiting"}: Score ${formatNumber(confirmationScore ?? 0)}/2.${missing}`;
  }
  if (h4HistoryValid === false || containsBlocker(blockers, [/h4.*history/i])) {
    return `${symbol} rejected because H4 history was insufficient.`;
  }
  if (m15HistoryValid === false || containsBlocker(blockers, [/m15.*history/i])) {
    return `${symbol} rejected because M15 history was insufficient.`;
  }
  void bosConfirmed;
  void fvgConfirmed;
  void liquiditySweep;
  void trendAlignment;
  if (orderBlockConfirmed === false || containsBlocker(blockers, [/order block/i, /\bob\b/i])) {
    return `${symbol} is waiting because order block confirmation is still missing.`;
  }
  if (blockers.length > 0) {
    return `${symbol} was ${status === "Rejected" ? "rejected" : "held"} because ${blockers.slice(0, 2).join(" and ")}.`;
  }
  if (status === "Accepted") {
    const ticket = firstText(context, ["ticket", "mt5_ticket", "mt5Ticket"]);
    if (ticket && confirmationScore !== null) {
      return `${symbol} trade opened successfully. Ticket: ${ticket}. Score ${formatNumber(confirmationScore)}/${formatNumber(firstNumber(context, ["confirmation_total", "confirmationTotal"]) ?? 4)}. RR ${riskReward !== null ? formatNumber(riskReward) : "2.0"}. Risk approved.`;
    }
    if (isBadText(suppliedReason) && text(context.ticket)) {
      return acceptedExecutionFallback({
        id: "",
        groqGenerated: false,
        reason: "",
        status,
        symbol,
        timestamp: "",
        side: firstText(context, ["side", "action", "type"]),
        ticket: firstText(context, ["ticket", "mt5_ticket", "mt5Ticket"]),
      });
    }
    const passedChecks = [
      trendAlignment === true ? "trend alignment passed" : "",
      liquiditySweep === true ? "liquidity sweep confirmed" : "",
      bosConfirmed === true ? "BOS confirmation appeared" : "",
      fvgConfirmed === true ? "FVG passed" : "",
      sessionValid === true ? "major-session bonus passed" : "",
      h4HistoryValid === true && m15HistoryValid === true ? "valid H4/M15 history passed" : "",
      riskReward !== null && riskReward >= requiredRR ? `RR ${formatNumber(riskReward)} passed` : "",
    ].filter(Boolean);
    if (passedChecks.length > 0) return `${symbol} was accepted because ${joinReasons(passedChecks)}.`;
    return cleanSuppliedReason ? `${symbol} was accepted because ${cleanSuppliedReason.replace(/\.$/, "")}.` : acceptedExecutionFallback({ id: "", groqGenerated: false, reason: "", status, symbol, timestamp: "", ticket: firstText(context, ["ticket", "mt5_ticket", "mt5Ticket"]), confirmation_score: confirmationScore, confirmation_total: firstNumber(context, ["confirmation_total", "confirmationTotal"]), RR: riskReward });
  }
  if (status === "Rejected") {
    return cleanSuppliedReason ? `${symbol} was rejected because ${cleanSuppliedReason.replace(/\.$/, "")}.` : rejectedFallback({ id: "", groqGenerated: false, reason: "", status, symbol, timestamp: "", failed_rules: failedRules, confirmation_missing: missingConfirmations, confirmation_score: confirmationScore, confirmation_required: 2, RR: riskReward, required_rr: requiredRR });
  }
  if (status === "Error") {
    return cleanSuppliedReason ? `${symbol} needs attention because ${cleanSuppliedReason.replace(/\.$/, "")}.` : `${symbol} needs attention because validation could not complete cleanly.`;
  }
  if (cleanSuppliedReason && (isLegacyStrategyDiagnostic(cleanSuppliedReason) || /required round 3|rule failed/i.test(cleanSuppliedReason))) {
    return `${symbol} waiting:\nScore 0/2\nMissing:\n- BOS ✗\n- FVG ✗\n- Liquidity sweep ✗\n- Trend alignment ✗`;
  }
  if (cleanSuppliedReason && /halted/i.test(cleanSuppliedReason) && /BOS|FVG|liquidity|trend|confirmation|confidence/i.test(cleanSuppliedReason)) {
    return `${symbol} waiting: ${cleanSuppliedReason.replace(/trade (was )?halted due to/i, "").replace(/\.$/, "").trim() || "confirmation is incomplete"}.`;
  }
  return cleanSuppliedReason ? `${symbol} is waiting because ${cleanSuppliedReason.replace(/\.$/, "")}.` : `${symbol} waiting:\nScore 0/2\nMissing:\n- BOS ✗\n- FVG ✗\n- Liquidity sweep ✗\n- Trend alignment ✗`;
}

function groqRewriteIsTraceable(rewrite: string, sourceReason: string): boolean {
  const output = rewrite.toLowerCase();
  const source = sourceReason.toLowerCase();
  const unsupportedPatterns = [
    /news|headline|cpi|fomc|interest rate|inflation|fed|central bank/,
    /sentiment|market mood|risk-on|risk off/,
    /institutional|smart money|bank flow|order flow/,
    /whale|manipulation|accumulation|distribution/,
    /support|resistance|moving average|rsi|macd|volume/,
    /bullish|bearish|momentum|breakout|reversal/,
  ];
  if (unsupportedPatterns.some((pattern) => pattern.test(output) && !pattern.test(source))) return false;
  const sourcedTerms = [
    "risk/reward",
    "risk reward",
    "bos",
    "break of structure",
    "liquidity sweep",
    "trend alignment",
    "order block",
    "blocker",
    "validation engine",
  ];
  return sourcedTerms.every((term) => !output.includes(term) || source.includes(term));
}

async function generateReason(sourceReason: string): Promise<string | null> {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) return null;
  const models = [GROQ_MODEL, GROQ_FALLBACK_MODEL].filter((model, index, modelsList) => model && modelsList.indexOf(model) === index);
  let payload: ApiRecord = {};
  let response: Response | null = null;
  for (const model of models) {
    try {
      response = await fetch(GROQ_CHAT_URL, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          temperature: 0.15,
          max_tokens: 120,
          messages: [
            {
              role: "system",
              content: "Rewrite only the supplied validation explanation for readability. Do not add facts, conditions, market rationale, sentiment, news, or analysis. One concise sentence.",
            },
            { role: "user", content: sourceReason },
          ],
        }),
        cache: "no-store",
      });
      payload = (await response.json().catch(() => ({}))) as ApiRecord;
      if (response.ok) break;
    } catch {
      response = null;
      payload = {};
    }
  }
  if (!response?.ok) return null;
  const choices = Array.isArray(payload.choices) ? payload.choices : [];
  const first = choices[0] as ApiRecord | undefined;
  const message = first?.message as ApiRecord | undefined;
  const content = text(message?.content);
  if (!content || isBadText(content) || NOISY_PATTERNS.some((pattern) => pattern.test(content))) return null;
  if (!groqRewriteIsTraceable(content, sourceReason)) return null;
  return content;
}

export async function GET() {
  const scope = await activeRoundScope();
  const messages = sortNewestFirst(await readStore());
  const scoped = scope.sessionId ? messages.filter((message) => text(message.validation_session_id || message.round_id) === scope.sessionId && !isLegacyReasonMessage(message)) : [];
  return NextResponse.json({ active_session_id: scope.sessionId, messages: scoped.slice(0, 50) });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as ApiRecord;
    const contexts = Array.isArray(body.contexts) ? (body.contexts.filter((item) => item && typeof item === "object") as ApiRecord[]) : [];
    const scope = await activeRoundScope();
    const existing = await readStore();
    const existingIds = new Set(existing.map((message) => message.id));
    const newMessages: ReasonMessage[] = [];
    for (const context of contexts.filter(isMeaningfulContext).slice(0, 6)) {
      const id = stableId(context);
      if (existingIds.has(id)) continue;
      const fallbackReason = ruleBasedReason(context);
      const groqReason = await generateReason(fallbackReason);
      const reason = groqReason || fallbackReason;
      const diagnostics = validatorDiagnostics(context);
      const message: ReasonMessage = {
        ...diagnostics,
        id,
        event_id: id,
        groqGenerated: Boolean(groqReason),
        reason,
        source: groqReason ? "groq" : "rule",
        status: normalizedDecisionStatus(context),
        symbol: text(context.symbol).toUpperCase(),
        timestamp: text(context.timestamp) || new Date().toISOString(),
        validation_session_id: text(context.validation_session_id || context.session_id || context.auto_validation_session_id) || scope.sessionId,
        round_id: text(context.round_id) || scope.roundId || scope.sessionId,
        round_number: numberValue(context.round_number) ?? scope.roundNumber,
      };
      const reasonKey = meaningfulReasonKey(message);
      const duplicateNewIndex = newMessages.findIndex((item) => meaningfulReasonKey(item) === reasonKey);
      if (duplicateNewIndex >= 0) {
        newMessages.splice(duplicateNewIndex, 1);
      }
      newMessages.push(message);
      existingIds.add(id);
    }
    const replacementKeys = new Set(newMessages.map(meaningfulReasonKey));
    const next = sortNewestFirst(dedupeMeaningfully([...newMessages, ...existing.filter((message) => !replacementKeys.has(meaningfulReasonKey(message)))])).slice(0, MAX_STORED_REASONS);
    await writeStore(next);
    const scoped = scope.sessionId ? next.filter((message) => text(message.validation_session_id || message.round_id) === scope.sessionId && !isLegacyReasonMessage(message)) : next.filter((message) => !isLegacyReasonMessage(message));
    return NextResponse.json({ active_session_id: scope.sessionId, messages: scoped.slice(0, 50) });
  } catch {
    return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
  }
}
