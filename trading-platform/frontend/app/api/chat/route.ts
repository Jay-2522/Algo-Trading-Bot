import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ChatMessage = {
  role: "user" | "assistant" | "system";
  content?: string;
  text?: string;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = process.env.GROQ_MODEL || "gemma2-9b-it";
const BUSY_MESSAGE = "The assistant is temporarily busy. Please try again in a few seconds.";

const SYSTEM_PROMPT = "You are AlgoPilot. Answer briefly using only provided data. If data is missing, say it is not available yet. Do not invent trades, prices, balances, or reasons.";

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

export async function POST(request: Request) {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
  }

  try {
    const body = (await request.json()) as Record<string, unknown>;
    const question = typeof body.question === "string" ? body.question.trim() : "";
    if (!question) {
      return NextResponse.json({ error: "Message is required." }, { status: 400 });
    }

    console.log("Groq model:", GROQ_MODEL);

    const context = typeof body.context === "string" ? body.context.slice(0, 2000) : "";
    const history = normalizeMessages(body.messages).slice(-3);
    const groqResponse = await fetch(GROQ_CHAT_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: GROQ_MODEL,
        temperature: 0.3,
        max_tokens: 150,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          ...(context ? [{ role: "system", content: `Data:\n${context}` }] : []),
          ...history.map((message) => ({ role: message.role, content: message.content })),
          { role: "user", content: question },
        ],
      }),
      cache: "no-store",
    });

    const payload = (await groqResponse.json().catch(() => ({}))) as Record<string, unknown>;
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
