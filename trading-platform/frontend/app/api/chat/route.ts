import { NextResponse } from "next/server";

export const runtime = "nodejs";

type ChatMessage = {
  role: "user" | "assistant" | "system";
  content?: string;
  text?: string;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const DEFAULT_GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.1-8b-instant";

const SYSTEM_PROMPT = `You are AlgoPilot's client trading assistant.
Speak clearly to non-technical traders while staying professional.
Use only provided project data when discussing balances, prices, brokers, trades, validation, accepted or rejected trades, reasons, MT5 status, and account status.
If data is missing, say that data is not available yet. Do not invent trade results, broker balances, prices, or strategy outcomes.
You understand these project areas: Dashboard, MT5 live prices, EURUSD, XAUUSD, NIFTY50, StarTrader, Vantage, FXPro, position size calculator, account balance, trade history, validation rounds, accepted/rejected trades, Reason panel, Test Environment, Forex sessions, risk management, and strategy rule checks.`;

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

export async function POST(request: Request) {
  console.log("Groq key loaded:", Boolean(process.env.GROQ_API_KEY));
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: "Groq API key is not configured. Add GROQ_API_KEY to the server environment." }, { status: 503 });
  }

  try {
    const body = (await request.json()) as Record<string, unknown>;
    const question = typeof body.question === "string" ? body.question.trim() : "";
    if (!question) {
      return NextResponse.json({ error: "Message is required." }, { status: 400 });
    }

    const context = typeof body.context === "string" ? body.context.slice(0, 12000) : "";
    const history = normalizeMessages(body.messages).slice(-12);
    const groqResponse = await fetch(GROQ_CHAT_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: DEFAULT_GROQ_MODEL,
        temperature: 0.25,
        max_tokens: 700,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "system", content: `Current project data snapshot:\n${context || "No dashboard data snapshot was supplied."}` },
          ...history.map((message) => ({ role: message.role, content: message.content })),
          { role: "user", content: question },
        ],
      }),
      cache: "no-store",
    });

    const payload = (await groqResponse.json().catch(() => ({}))) as Record<string, unknown>;
    if (!groqResponse.ok) {
      const error = typeof payload.error === "object" && payload.error !== null && "message" in payload.error ? String((payload.error as Record<string, unknown>).message) : `Groq returned ${groqResponse.status}`;
      return NextResponse.json({ error }, { status: 502 });
    }

    const choices = Array.isArray(payload.choices) ? payload.choices : [];
    const first = choices[0] as Record<string, unknown> | undefined;
    const message = first?.message as Record<string, unknown> | undefined;
    const reply = typeof message?.content === "string" ? message.content.trim() : "";
    return NextResponse.json({ reply: reply || "I could not produce a response from the trading assistant." });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Groq chat request failed." }, { status: 500 });
  }
}
