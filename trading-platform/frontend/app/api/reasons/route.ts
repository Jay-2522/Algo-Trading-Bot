import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ReasonStatus = "Accepted" | "Rejected" | "Waiting" | "Error";
type ApiRecord = Record<string, unknown>;
type ReasonMessage = {
  candles_loaded?: number | null;
  candles_required?: number | null;
  data_source?: string;
  id: string;
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
  passed_rules?: string[];
  failed_rules?: string[];
  advisory_warnings?: string[];
  RR?: number | null;
  required_rr?: number | null;
  bos_status?: string;
  fvg_status?: string;
  h4_history_status?: string;
  m15_history_status?: string;
  history_ready?: boolean | null;
  requested_symbol?: string;
  resolved_symbol?: string;
  mt5_last_error?: string;
  process_id?: string;
  connection_id?: string;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = process.env.GROQ_MODEL || "gemma2-9b-it";
const GROQ_FALLBACK_MODEL = process.env.GROQ_FALLBACK_MODEL || "";
const STORE_PATH = path.join(process.cwd(), "..", "data", "reason_panel", "reason_messages.json");
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

function stableId(context: ApiRecord): string {
  const raw = JSON.stringify({
    symbol: text(context.symbol).toUpperCase(),
    status: normalizeStatus(context.status),
    timestamp: text(context.timestamp),
    reason: text(context.reason || context.setupReason),
    signalHash: text(context.signalHash),
    timeframe: text(context.timeframe),
    candlesLoaded: text(context.candles_loaded),
    rejectionReason: text(context.rejection_reason),
  });
  let hash = 0;
  for (let index = 0; index < raw.length; index += 1) {
    hash = (hash * 31 + raw.charCodeAt(index)) >>> 0;
  }
  return `reason-${hash.toString(16)}`;
}

function normalizeStatus(value: unknown): ReasonStatus {
  const status = text(value).toUpperCase();
  if (status.includes("APPROVED") || status.includes("ACCEPT") || status.includes("READY") || status.includes("WIN")) return "Accepted";
  if (status.includes("REJECT") || status.includes("BLOCK") || status.includes("DENIED") || status.includes("LOSS")) return "Rejected";
  if (status.includes("ERROR") || status.includes("FAIL") || status.includes("DISCONNECT")) return "Error";
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

function validatorDiagnostics(context: ApiRecord): Pick<ReasonMessage, "candles_loaded" | "candles_required" | "data_source" | "rejection_reason" | "timeframe" | "validation_status" | "history_ready" | "requested_symbol" | "resolved_symbol" | "mt5_last_error" | "process_id" | "connection_id"> {
  return {
    candles_loaded: firstNumber(context, ["candles_loaded", "candlesLoaded", "loaded_candles", "loadedCandles", "bars_loaded", "barsLoaded", "history_bars", "candle_count"]),
    candles_required: firstNumber(context, ["candles_required", "candlesRequired", "required_candles", "requiredCandles", "minimum_candles", "minimumCandles", "min_bars", "minBars"]),
    data_source: firstText(context, ["data_source", "dataSource", "source", "feed_source", "feedSource"]),
    rejection_reason: firstText(context, ["rejection_reason", "rejectionReason", "final_rejection_reason", "finalRejectionReason", "reason", "setupReason", "whatNeedsToHappenNext"]),
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
    return messages.map(sanitizeReasonMessage);
  } catch {
    return [];
  }
}

async function writeStore(messages: ReasonMessage[]): Promise<void> {
  await mkdir(path.dirname(STORE_PATH), { recursive: true });
  await writeFile(STORE_PATH, JSON.stringify(sortNewestFirst(messages.map(sanitizeReasonMessage)).slice(0, 50), null, 2), "utf-8");
}

function timestampValue(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function sortNewestFirst(messages: ReasonMessage[]): ReasonMessage[] {
  return [...messages].sort((left, right) => timestampValue(text(right.timestamp)) - timestampValue(text(left.timestamp)));
}

function acceptedExecutionFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "This signal";
  const side = cleanDisplayText(message.side).toUpperCase();
  const ticket = cleanDisplayText(message.ticket);
  const sideText = side && !["TRADE", "POSITION"].includes(side) ? ` as a ${side} trade` : "";
  return `${symbol} was accepted and opened${sideText} because guarded demo validation passed, risk status was approved, and MT5 executed the order successfully.${ticket ? ` Ticket: ${ticket}.` : ""}`;
}

function rejectedFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "This signal";
  const finalReason = cleanDisplayText(message.final_decision_reason);
  if (finalReason) return finalReason;
  const diagnostic = cleanDisplayText(message.rejection_reason);
  if (diagnostic) return `${symbol} was rejected because ${diagnostic.replace(/\.$/, "")}.`;
  return `${symbol} rejected because a required Round 3 entry rule failed.`;
}

function waitingFallback(message: ReasonMessage): string {
  const symbol = text(message.symbol).toUpperCase() || "This signal";
  return `${symbol} is waiting for BOS and FVG confirmation before entry.`;
}

function sanitizeReasonMessage(message: ReasonMessage): ReasonMessage {
  const status = normalizeStatus(message.status);
  let reason = cleanDisplayText(message.reason);
  const rejectionReason = cleanDisplayText(message.rejection_reason);
  if (!reason) {
    if (status === "Accepted") reason = acceptedExecutionFallback(message);
    else if (status === "Rejected") reason = rejectedFallback({ ...message, rejection_reason: rejectionReason });
    else if (status === "Waiting") reason = waitingFallback(message);
    else reason = `${text(message.symbol).toUpperCase() || "This signal"} needs attention because validation could not complete cleanly.`;
  }
  return {
    ...message,
    data_source: cleanDisplayText(message.data_source),
    mt5_comment: cleanDisplayText(message.mt5_comment),
    mt5_retcode: cleanDisplayText(message.mt5_retcode),
    reason,
    rejection_reason: rejectionReason,
    final_decision_reason: cleanDisplayText(message.final_decision_reason),
    side: cleanDisplayText(message.side).toUpperCase(),
    signal_hash: cleanDisplayText(message.signal_hash),
    source: message.source,
    status,
    strategy_profile: cleanDisplayText(message.strategy_profile),
    symbol: text(message.symbol).toUpperCase(),
    ticket: cleanDisplayText(message.ticket),
    timeframe: cleanDisplayText(message.timeframe).toUpperCase(),
    validation_status: cleanDisplayText(message.validation_status),
    history_ready: booleanValue(message.history_ready),
    requested_symbol: cleanDisplayText(message.requested_symbol),
    resolved_symbol: cleanDisplayText(message.resolved_symbol),
    mt5_last_error: cleanDisplayText(message.mt5_last_error),
    process_id: cleanDisplayText(message.process_id),
    connection_id: cleanDisplayText(message.connection_id),
  };
}

function normalizeReasonForDedupe(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").replace(/[.。]+$/g, "").trim();
}

function meaningfulReasonKey(message: ReasonMessage): string {
  const ticket = text(message.ticket);
  const signalHash = text(message.signal_hash);
  if (ticket) return [text(message.symbol).toUpperCase(), message.status, "ticket", ticket].join("|");
  if (text(message.source) === "execution" && signalHash) return [text(message.symbol).toUpperCase(), message.status, "signal", signalHash].join("|");
  return [text(message.symbol).toUpperCase(), message.status, normalizeReasonForDedupe(text(message.reason))].join("|");
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
  if (parts.length <= 1) return parts[0] ?? "the Round 3 entry rules passed";
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

function ruleBasedReason(context: ApiRecord): string {
  const symbol = text(context.symbol).toUpperCase() || "This setup";
  const status = normalizeStatus(context.status);
  const finalDecisionReason = cleanDisplayText(context.final_decision_reason);
  if (finalDecisionReason) return finalDecisionReason;
  const riskReward = numberValue(context.riskReward);
  const requiredRR = numberValue(context.requiredRR) ?? 2.0;
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
  const suppliedReason = text(context.reason || context.setupReason || context.whatNeedsToHappenNext);
  const cleanSuppliedReason = cleanDisplayText(suppliedReason);

  if (historyReady === false && historyTimeframe && candlesLoaded !== null && candlesRequired !== null) {
    return `Waiting for MT5 ${historyTimeframe} history sync: ${requestedSymbol} resolved as ${resolvedSymbol}, loaded ${formatNumber(candlesLoaded)} / required ${formatNumber(candlesRequired)} candles.`;
  }
  if (riskReward !== null && riskReward < requiredRR) {
    return `${symbol} rejected because RR ${formatNumber(riskReward)} was below required ${formatNumber(requiredRR)}.`;
  }
  if (containsBlocker(blockers, [/risk.?reward/i, /\brr\b/i]) && riskReward !== null) {
    return `${symbol} rejected because RR ${formatNumber(riskReward)} was below required ${formatNumber(requiredRR)}.`;
  }
  if (bosConfirmed === false || containsBlocker(blockers, [/\bbos\b/i, /break of structure/i])) {
    return status === "Rejected" ? `${symbol} rejected because BOS was missing.` : `${symbol} is waiting for BOS and FVG confirmation before entry.`;
  }
  if (fvgConfirmed === false || containsBlocker(blockers, [/\bfvg\b/i, /fair value gap/i])) {
    return status === "Rejected" ? `${symbol} rejected because FVG was missing.` : `${symbol} is waiting for BOS and FVG confirmation before entry.`;
  }
  if (sessionValid === false || containsBlocker(blockers, [/session/i, /london/i, /new york/i])) {
    return `${symbol} rejected because session was outside London/NY.`;
  }
  if (h4HistoryValid === false || containsBlocker(blockers, [/h4.*history/i])) {
    return `${symbol} rejected because H4 history was insufficient.`;
  }
  if (m15HistoryValid === false || containsBlocker(blockers, [/m15.*history/i])) {
    return `${symbol} rejected because M15 history was insufficient.`;
  }
  if (liquiditySweep === false || trendAlignment === false) {
    // Round 3 treats these as advisory confidence boosters only.
    return cleanSuppliedReason || `${symbol} is waiting for BOS and FVG confirmation before entry.`;
  }
  if (orderBlockConfirmed === false || containsBlocker(blockers, [/order block/i, /\bob\b/i])) {
    return `${symbol} is waiting because order block confirmation is still missing.`;
  }
  if (blockers.length > 0) {
    return `${symbol} was ${status === "Rejected" ? "rejected" : "held"} because ${blockers.slice(0, 2).join(" and ")}.`;
  }
  if (status === "Accepted") {
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
      orderBlockConfirmed === true ? "order block confirmation passed" : "",
      fvgConfirmed === true ? "FVG passed" : "",
      sessionValid === true ? "London/NY session passed" : "",
      h4HistoryValid === true && m15HistoryValid === true ? "valid H4/M15 history passed" : "",
      riskReward !== null && riskReward >= requiredRR ? `RR ${formatNumber(riskReward)} passed` : "",
    ].filter(Boolean);
    if (passedChecks.length > 0) return `${symbol} was accepted because ${joinReasons(passedChecks)}.`;
    return cleanSuppliedReason ? `${symbol} was accepted because ${cleanSuppliedReason.replace(/\.$/, "")}.` : `${symbol} accepted because the Round 3 entry rules passed.`;
  }
  if (status === "Rejected") {
    return cleanSuppliedReason ? `${symbol} was rejected because ${cleanSuppliedReason.replace(/\.$/, "")}.` : `${symbol} rejected because a required Round 3 entry rule failed.`;
  }
  if (status === "Error") {
    return cleanSuppliedReason ? `${symbol} needs attention because ${cleanSuppliedReason.replace(/\.$/, "")}.` : `${symbol} needs attention because validation could not complete cleanly.`;
  }
  return cleanSuppliedReason ? `${symbol} is waiting because ${cleanSuppliedReason.replace(/\.$/, "")}.` : `${symbol} is waiting for BOS and FVG confirmation before entry.`;
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
  const messages = sortNewestFirst(await readStore());
  return NextResponse.json({ messages: messages.slice(0, 50) });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as ApiRecord;
    const contexts = Array.isArray(body.contexts) ? (body.contexts.filter((item) => item && typeof item === "object") as ApiRecord[]) : [];
    const existing = await readStore();
    const existingIds = new Set(existing.map((message) => message.id));
    const existingReasonKeys = new Set(existing.map(meaningfulReasonKey));
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
        groqGenerated: Boolean(groqReason),
        reason,
        source: groqReason ? "groq" : "rule",
        status: normalizeStatus(context.status),
        symbol: text(context.symbol).toUpperCase(),
        timestamp: text(context.timestamp) || new Date().toISOString(),
      };
      const reasonKey = meaningfulReasonKey(message);
      if (existingReasonKeys.has(reasonKey) || newMessages.some((item) => meaningfulReasonKey(item) === reasonKey)) continue;
      newMessages.push(message);
      existingIds.add(id);
      existingReasonKeys.add(reasonKey);
    }
    const next = sortNewestFirst(dedupeMeaningfully([...newMessages, ...existing])).slice(0, 50);
    await writeStore(next);
    return NextResponse.json({ messages: next });
  } catch {
    return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
  }
}
