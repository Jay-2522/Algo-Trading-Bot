import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ReasonStatus = "Accepted" | "Rejected" | "Waiting" | "Error";
type ApiRecord = Record<string, unknown>;
type ReasonMessage = {
  id: string;
  groqGenerated: true;
  reason: string;
  status: ReasonStatus;
  symbol: string;
  timestamp: string;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = process.env.GROQ_MODEL || "gemma2-9b-it";
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

function stableId(context: ApiRecord): string {
  const raw = JSON.stringify({
    symbol: text(context.symbol).toUpperCase(),
    status: normalizeStatus(context.status),
    timestamp: text(context.timestamp),
    reason: text(context.reason || context.setupReason),
    signalHash: text(context.signalHash),
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

async function readStore(): Promise<ReasonMessage[]> {
  try {
    const raw = await readFile(STORE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed.filter((item) => item && typeof item === "object" && (item as ApiRecord).groqGenerated === true) as ReasonMessage[]) : [];
  } catch {
    return [];
  }
}

async function writeStore(messages: ReasonMessage[]): Promise<void> {
  await mkdir(path.dirname(STORE_PATH), { recursive: true });
  await writeFile(STORE_PATH, JSON.stringify(messages.slice(0, 50), null, 2), "utf-8");
}

function fallbackPromptContext(context: ApiRecord): ApiRecord {
  return {
    symbol: text(context.symbol).toUpperCase(),
    status: normalizeStatus(context.status),
    confidence: numberValue(context.confidence),
    riskReward: numberValue(context.riskReward),
    requiredRR: numberValue(context.requiredRR),
    trendAlignment: context.trendAlignment,
    liquiditySweep: context.liquiditySweep,
    bosConfirmed: context.bosConfirmed,
    orderBlockConfirmed: context.orderBlockConfirmed,
    reason: text(context.reason || context.setupReason),
    blockers: Array.isArray(context.blockers) ? context.blockers.slice(0, 6) : [],
  };
}

async function generateReason(context: ApiRecord): Promise<string | null> {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) return null;
  const response = await fetch(GROQ_CHAT_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      temperature: 0.15,
      max_tokens: 120,
      messages: [
        {
          role: "system",
          content:
            "You explain AlgoPilot validation decisions to traders. The validation engine is source of truth. Do not accept/reject trades, invent trades, invent prices, or mention internal systems. Return one concise explanation answering what happened, why, which rule passed/failed, and what the user should understand.",
        },
        { role: "user", content: JSON.stringify(fallbackPromptContext(context)) },
      ],
    }),
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as ApiRecord;
  if (!response.ok) return null;
  const choices = Array.isArray(payload.choices) ? payload.choices : [];
  const first = choices[0] as ApiRecord | undefined;
  const message = first?.message as ApiRecord | undefined;
  const content = text(message?.content);
  if (!content || NOISY_PATTERNS.some((pattern) => pattern.test(content))) return null;
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
    const byId = new Map(existing.map((message) => [message.id, message]));
    for (const context of contexts.filter(isMeaningfulContext).slice(0, 6)) {
      const id = stableId(context);
      if (byId.has(id)) continue;
      const reason = await generateReason(context);
      if (!reason) continue;
      byId.set(id, {
        id,
        groqGenerated: true,
        reason,
        status: normalizeStatus(context.status),
        symbol: text(context.symbol).toUpperCase(),
        timestamp: text(context.timestamp) || new Date().toISOString(),
      });
    }
    const next = Array.from(byId.values())
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 50);
    await writeStore(next);
    return NextResponse.json({ messages: next });
  } catch {
    return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
  }
}
