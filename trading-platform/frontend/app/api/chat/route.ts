import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ChatMessage = {
  role: "user" | "assistant" | "system";
  content?: string;
  text?: string;
};

type ReasonDiagnostic = {
  candles_loaded?: number | null;
  candles_required?: number | null;
  data_source?: string;
  diagnostics?: Record<string, unknown>;
  rejection_reason?: string;
  symbol?: string;
  timeframe?: string;
  validation_status?: string;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = process.env.GROQ_MODEL || "gemma2-9b-it";
const GROQ_FALLBACK_MODEL = process.env.GROQ_FALLBACK_MODEL || "";
const REASON_STORE_PATH = path.join(process.cwd(), "..", "data", "reason_panel", "reason_messages.json");
const BUSY_MESSAGE = "The assistant is temporarily busy. Please try again in a few seconds.";

const SYSTEM_PROMPT = 'You are AlgoPilot. Answer briefly using only provided data. Do not invent trades, prices, balances, reasons, candle counts, or timeframes. If validator diagnostics are unavailable, say "Validator diagnostics are not available for this decision."';

function normalizeMessages(value: unknown): ChatMessage[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const record = item as Record<string, unknown>;
      const role = record.role === "assistant" || record.role === "user" ? record.role : null;
      const content = typeof record.content === "string" ? record.content : typeof record.text === "string" ? record.text : "";
      return role && content.trim() ? { role, content: content.trim() } : null;
    })
    .filter(Boolean) as ChatMessage[];
}

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

function readField(record: Record<string, unknown>, keys: string[]): unknown {
  const nested = record.diagnostics && typeof record.diagnostics === "object" ? (record.diagnostics as Record<string, unknown>) : {};
  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null && text(record[key])) return record[key];
    if (nested[key] !== undefined && nested[key] !== null && text(nested[key])) return nested[key];
  }
  return undefined;
}

function normalizeReasonDiagnostic(record: Record<string, unknown>): ReasonDiagnostic {
  return {
    candles_loaded: numberValue(readField(record, ["candles_loaded", "candlesLoaded"])),
    candles_required: numberValue(readField(record, ["candles_required", "candlesRequired"])),
    data_source: text(readField(record, ["data_source", "dataSource"])),
    rejection_reason: text(readField(record, ["rejection_reason", "rejectionReason"])),
    symbol: text(readField(record, ["symbol"])).toUpperCase(),
    timeframe: text(readField(record, ["timeframe"])).toUpperCase(),
    validation_status: text(readField(record, ["validation_status", "validationStatus"])),
  };
}

async function readReasonDiagnostics(): Promise<ReasonDiagnostic[]> {
  try {
    const raw = await readFile(REASON_STORE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
      .map(normalizeReasonDiagnostic)
      .filter((item) => Boolean(item.symbol || item.timeframe || item.candles_loaded !== null || item.candles_required !== null || item.rejection_reason));
  } catch {
    return [];
  }
}

function questionSymbol(question: string): string | null {
  const upper = question.toUpperCase();
  if (upper.includes("EURUSD")) return "EURUSD";
  if (upper.includes("XAUUSD")) return "XAUUSD";
  if (upper.includes("NIFTY50") || upper.includes("NIFTY 50")) return "NIFTY50";
  return null;
}

function questionTimeframe(question: string): string | null {
  const match = question.toUpperCase().match(/\b(M1|M5|M15|M30|H1|H4|D1)\b/);
  return match?.[1] ?? null;
}

function isDiagnosticQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("candle") ||
    normalized.includes("minimum required") ||
    normalized.includes("minimum candle") ||
    normalized.includes("timeframe failed") ||
    normalized.includes("which timeframe") ||
    (normalized.includes("why") && normalized.includes("reject"))
  );
}

function findDiagnostic(records: ReasonDiagnostic[], symbol: string | null, timeframe: string | null): { exact: ReasonDiagnostic | null; latestForSymbol: ReasonDiagnostic | null; latest: ReasonDiagnostic | null } {
  const latest = records[0] ?? null;
  const symbolMatches = symbol ? records.filter((record) => record.symbol === symbol) : records;
  const latestForSymbol = symbolMatches[0] ?? null;
  const exact = timeframe ? symbolMatches.find((record) => record.timeframe === timeframe) ?? null : latestForSymbol;
  return { exact, latest, latestForSymbol };
}

function diagnosticMissing(): string {
  return "Validator diagnostics are not available for this decision.";
}

function candleSummary(record: ReasonDiagnostic): string {
  return `${record.symbol || "Latest decision"} ${record.timeframe || ""}`.trim();
}

async function answerDiagnosticQuestion(question: string): Promise<string | null> {
  if (!isDiagnosticQuestion(question)) return null;
  const records = await readReasonDiagnostics();
  const latest = records[0] ?? null;
  console.log("Chat reason records loaded:", records.length);
  console.log("Chat latest reason symbol/timeframe:", `${latest?.symbol || "none"}/${latest?.timeframe || "none"}`);
  console.log("Chat latest reason candles:", `${latest?.candles_loaded ?? "none"}/${latest?.candles_required ?? "none"}`);

  const symbol = questionSymbol(question);
  const timeframe = questionTimeframe(question);
  const { exact, latestForSymbol } = findDiagnostic(records, symbol, timeframe);
  const normalized = question.toLowerCase();
  if (timeframe && latestForSymbol && !exact) {
    if (latestForSymbol.candles_loaded !== null && latestForSymbol.candles_required !== null) {
      return `I only have latest diagnostics for ${latestForSymbol.symbol} ${latestForSymbol.timeframe || "unknown timeframe"}: ${latestForSymbol.candles_loaded} candles loaded, ${latestForSymbol.candles_required} required. ${timeframe} diagnostics are not available for the latest decision.`;
    }
    return diagnosticMissing();
  }
  const record = exact;
  if (!record) return diagnosticMissing();
  if (normalized.includes("minimum required") || normalized.includes("minimum candle")) {
    if (record.candles_required === null || record.candles_required === undefined) return diagnosticMissing();
    return `For the latest validation decision, the minimum required candle count is ${record.candles_required}.`;
  }
  if (normalized.includes("timeframe failed") || normalized.includes("which timeframe")) {
    if (record.candles_loaded === null || record.candles_loaded === undefined || record.candles_required === null || record.candles_required === undefined) return diagnosticMissing();
    if (record.candles_loaded >= record.candles_required) return `No timeframe failed from the latest stored diagnostics. ${candleSummary(record)} loaded ${record.candles_loaded} candles, required ${record.candles_required}.`;
    return `${candleSummary(record)} failed because it loaded ${record.candles_loaded} candles, but required ${record.candles_required}.`;
  }
  if (normalized.includes("candle")) {
    if (record.candles_loaded === null || record.candles_loaded === undefined || record.candles_required === null || record.candles_required === undefined) return diagnosticMissing();
    return `${candleSummary(record)} loaded ${record.candles_loaded} candles. Minimum required is ${record.candles_required}. Data source: ${record.data_source || "not available"}.`;
  }
  if (normalized.includes("why") && normalized.includes("reject")) {
    if (!record.rejection_reason) return diagnosticMissing();
    return `${record.symbol || "This decision"} was rejected because ${record.rejection_reason.replace(/\.$/, "")}.`;
  }
  return diagnosticMissing();
}

function parseRetryAfter(value: string | null, milliseconds = false): number | null {
  if (!value) return null;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return Math.max(1, Math.ceil(milliseconds ? numeric / 1000 : numeric));
  const dateMs = Date.parse(value);
  if (Number.isFinite(dateMs)) return Math.max(1, Math.ceil((dateMs - Date.now()) / 1000));
  const match = value.match(/(\d+(?:\.\d+)?)\s*(ms|s|m)?/i);
  if (!match) return null;
  const amount = Number(match[1]);
  if (!Number.isFinite(amount)) return null;
  const unit = match[2]?.toLowerCase();
  if (unit === "ms") return Math.max(1, Math.ceil(amount / 1000));
  if (unit === "m") return Math.max(1, Math.ceil(amount * 60));
  return Math.max(1, Math.ceil(amount));
}

function retryAfterSeconds(response: Response): number {
  const retryAfter = parseRetryAfter(response.headers.get("retry-after"));
  if (retryAfter) return retryAfter;
  const retryAfterMs = parseRetryAfter(response.headers.get("retry-after-ms"), true);
  if (retryAfterMs) return retryAfterMs;
  const tokenReset = parseRetryAfter(response.headers.get("x-ratelimit-reset-tokens"));
  if (tokenReset) return tokenReset;
  const requestReset = parseRetryAfter(response.headers.get("x-ratelimit-reset-requests"));
  if (requestReset) return requestReset;
  return 10;
}

function textFromPayload(value: unknown): string {
  if (!value || typeof value !== "object") return "";
  const record = value as Record<string, unknown>;
  const error = typeof record.error === "object" && record.error !== null ? (record.error as Record<string, unknown>) : record;
  return [error.message, error.code, error.type]
    .filter((item): item is string => typeof item === "string")
    .join(" ")
    .toLowerCase();
}

function isModelAvailabilityError(response: Response, payload: Record<string, unknown>): boolean {
  if (response.status !== 400 && response.status !== 404) return false;
  const errorText = textFromPayload(payload);
  return errorText.includes("model") && /(not found|not_found|unavailable|decommissioned|deprecated|does not exist|not supported)/i.test(errorText);
}

function shouldRetryWithFallback(response: Response, payload: Record<string, unknown>): boolean {
  if (isModelAvailabilityError(response, payload)) return true;
  return response.status === 429 || response.status === 503 || response.status === 500 || response.status === 502 || response.status === 504;
}

function buildGroqRequestBody(model: string, context: string, history: ChatMessage[], question: string) {
  return JSON.stringify({
    model,
    temperature: 0.3,
    max_tokens: 150,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      ...(context ? [{ role: "system", content: `Data:\n${context}` }] : []),
      ...history.map((message) => ({ role: message.role, content: message.content })),
      { role: "user", content: question },
    ],
  });
}

async function requestGroq(apiKey: string, model: string, context: string, history: ChatMessage[], question: string) {
  const response = await fetch(GROQ_CHAT_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: buildGroqRequestBody(model, context, history, question),
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  return { payload, response };
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const question = typeof body.question === "string" ? body.question.trim() : "";
    if (!question) {
      return NextResponse.json({ error: "Message is required." }, { status: 400 });
    }
    const diagnosticAnswer = await answerDiagnosticQuestion(question);
    if (diagnosticAnswer) {
      return NextResponse.json({ reply: diagnosticAnswer });
    }

    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
    }

    const context = typeof body.context === "string" ? body.context.slice(0, 2000) : "";
    const history = normalizeMessages(body.messages).slice(-3);
    console.log("Groq primary model:", GROQ_MODEL);
    console.log("Groq fallback model:", GROQ_FALLBACK_MODEL || "not configured");

    let fallbackUsed = false;
    let groqResponse: Response;
    let payload: Record<string, unknown>;
    try {
      const primary = await requestGroq(apiKey, GROQ_MODEL, context, history, question);
      payload = primary.payload;
      groqResponse = primary.response;
      console.log("Groq primary status:", groqResponse.status);
    } catch (error) {
      if (!GROQ_FALLBACK_MODEL || GROQ_FALLBACK_MODEL === GROQ_MODEL) throw error;
      fallbackUsed = true;
      const fallback = await requestGroq(apiKey, GROQ_FALLBACK_MODEL, context, history, question);
      payload = fallback.payload;
      groqResponse = fallback.response;
      console.log("Groq fallback status:", groqResponse.status);
    }

    if (!groqResponse.ok && GROQ_FALLBACK_MODEL && GROQ_FALLBACK_MODEL !== GROQ_MODEL && shouldRetryWithFallback(groqResponse, payload)) {
      fallbackUsed = true;
      const fallback = await requestGroq(apiKey, GROQ_FALLBACK_MODEL, context, history, question);
      payload = fallback.payload;
      groqResponse = fallback.response;
      console.log("Groq fallback status:", groqResponse.status);
    }
    console.log("Groq fallback used:", fallbackUsed);

    if (!groqResponse.ok) {
      if (groqResponse.status === 429) {
        return NextResponse.json({ error: BUSY_MESSAGE, rateLimited: true, retryAfterSeconds: retryAfterSeconds(groqResponse) }, { status: 429 });
      }
      return NextResponse.json({ error: BUSY_MESSAGE, rateLimited: false }, { status: 502 });
    }

    const choices = Array.isArray(payload.choices) ? payload.choices : [];
    const first = choices[0] as Record<string, unknown> | undefined;
    const message = first?.message as Record<string, unknown> | undefined;
    const reply = typeof message?.content === "string" ? message.content.trim() : "";
    return NextResponse.json({ reply: reply || "I could not produce a response from the trading assistant." });
  } catch (error) {
    return NextResponse.json({ error: BUSY_MESSAGE }, { status: 500 });
  }
}
