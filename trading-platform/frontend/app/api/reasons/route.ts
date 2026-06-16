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
  source?: "groq" | "rule";
  status: ReasonStatus;
  symbol: string;
  timestamp: string;
  timeframe?: string;
  validation_status?: string;
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
    const value = text(record[key]);
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

function validatorDiagnostics(context: ApiRecord): Pick<ReasonMessage, "candles_loaded" | "candles_required" | "data_source" | "rejection_reason" | "timeframe" | "validation_status"> {
  return {
    candles_loaded: firstNumber(context, ["candles_loaded", "candlesLoaded", "loaded_candles", "loadedCandles", "bars_loaded", "barsLoaded", "history_bars", "candle_count"]),
    candles_required: firstNumber(context, ["candles_required", "candlesRequired", "required_candles", "requiredCandles", "minimum_candles", "minimumCandles", "min_bars", "minBars"]),
    data_source: firstText(context, ["data_source", "dataSource", "source", "feed_source", "feedSource"]),
    rejection_reason: firstText(context, ["rejection_reason", "rejectionReason", "final_rejection_reason", "finalRejectionReason", "reason", "setupReason", "whatNeedsToHappenNext"]),
    timeframe: firstText(context, ["timeframe", "tf", "validation_timeframe", "validationTimeframe", "failed_timeframe", "failedTimeframe"]).toUpperCase(),
    validation_status: firstText(context, ["validation_status", "validationStatus", "status", "execution_status", "executionStatus", "status_level", "risk_status"]),
  };
}

async function readStore(): Promise<ReasonMessage[]> {
  try {
    const raw = await readFile(STORE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed)
      ? (parsed.filter((item) => {
          if (!item || typeof item !== "object") return false;
          const record = item as ApiRecord;
          return Boolean(text(record.id) && text(record.reason) && text(record.symbol));
        }) as ReasonMessage[])
      : [];
  } catch {
    return [];
  }
}

async function writeStore(messages: ReasonMessage[]): Promise<void> {
  await mkdir(path.dirname(STORE_PATH), { recursive: true });
  await writeFile(STORE_PATH, JSON.stringify(messages.slice(0, 50), null, 2), "utf-8");
}

function normalizeReasonForDedupe(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").replace(/[.。]+$/g, "").trim();
}

function meaningfulReasonKey(message: ReasonMessage): string {
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
  if (parts.length <= 1) return parts[0] ?? "the validation engine marked the setup accepted";
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

function ruleBasedReason(context: ApiRecord): string {
  const symbol = text(context.symbol).toUpperCase() || "This setup";
  const status = normalizeStatus(context.status);
  const riskReward = numberValue(context.riskReward);
  const requiredRR = numberValue(context.requiredRR) ?? 1.5;
  const bosConfirmed = booleanValue(context.bosConfirmed);
  const liquiditySweep = booleanValue(context.liquiditySweep);
  const trendAlignment = booleanValue(context.trendAlignment);
  const orderBlockConfirmed = booleanValue(context.orderBlockConfirmed);
  const blockers = Array.isArray(context.blockers) ? context.blockers.map(text).filter(Boolean) : [];
  const suppliedReason = text(context.reason || context.setupReason || context.whatNeedsToHappenNext);

  if (riskReward !== null && riskReward < requiredRR) {
    return `${symbol} was rejected because the risk/reward ratio was ${formatNumber(riskReward)}, below the required minimum of ${formatNumber(requiredRR)}.`;
  }
  if (containsBlocker(blockers, [/risk.?reward/i, /\brr\b/i]) && riskReward !== null) {
    return `${symbol} was rejected because the risk/reward ratio was ${formatNumber(riskReward)}, which did not meet the validation requirement.`;
  }
  if (bosConfirmed === false || containsBlocker(blockers, [/\bbos\b/i, /break of structure/i])) {
    return `${symbol} is waiting because BOS confirmation has not appeared yet.`;
  }
  if (liquiditySweep === false || containsBlocker(blockers, [/liquidity/i, /sweep/i])) {
    return `${symbol} is waiting because the liquidity sweep confirmation has not appeared yet.`;
  }
  if (trendAlignment === false || containsBlocker(blockers, [/trend/i, /alignment/i])) {
    return `${symbol} is waiting because trend alignment has not passed yet.`;
  }
  if (orderBlockConfirmed === false || containsBlocker(blockers, [/order block/i, /\bob\b/i])) {
    return `${symbol} is waiting because order block confirmation is still missing.`;
  }
  if (blockers.length > 0) {
    return `${symbol} was ${status === "Rejected" ? "rejected" : "held"} because ${blockers.slice(0, 2).join(" and ")}.`;
  }
  if (status === "Accepted") {
    const passedChecks = [
      trendAlignment === true ? "trend alignment passed" : "",
      liquiditySweep === true ? "liquidity sweep confirmed" : "",
      bosConfirmed === true ? "BOS confirmation appeared" : "",
      orderBlockConfirmed === true ? "order block confirmation passed" : "",
      riskReward !== null && riskReward >= requiredRR ? `risk/reward ratio was ${formatNumber(riskReward)}, meeting the required minimum of ${formatNumber(requiredRR)}` : "",
    ].filter(Boolean);
    if (passedChecks.length > 0) return `${symbol} was accepted because ${joinReasons(passedChecks)}.`;
    return suppliedReason ? `${symbol} was accepted because ${suppliedReason.replace(/\.$/, "")}.` : `${symbol} was accepted because the validation engine marked the setup accepted.`;
  }
  if (status === "Rejected") {
    return suppliedReason ? `${symbol} was rejected because ${suppliedReason.replace(/\.$/, "")}.` : `${symbol} was rejected because one or more validation rules did not pass.`;
  }
  if (status === "Error") {
    return suppliedReason ? `${symbol} needs attention because ${suppliedReason.replace(/\.$/, "")}.` : `${symbol} needs attention because validation could not complete cleanly.`;
  }
  return suppliedReason ? `${symbol} is waiting because ${suppliedReason.replace(/\.$/, "")}.` : `${symbol} is waiting for the validation rules to confirm before any trade can be accepted.`;
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
  if (!content || NOISY_PATTERNS.some((pattern) => pattern.test(content))) return null;
  if (!groqRewriteIsTraceable(content, sourceReason)) return null;
  return content;
}

export async function GET() {
  const messages = await readStore();
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
    const next = dedupeMeaningfully([...newMessages, ...existing]).slice(0, 50);
    await writeStore(next);
    return NextResponse.json({ messages: next });
  } catch {
    return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
  }
}
