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

type ReasonRecord = ReasonDiagnostic & {
  adaptive_level?: number | null;
  confirmation_missing?: string[];
  confirmation_passed?: string[];
  confirmation_required?: number | null;
  confirmation_score?: number | null;
  confirmation_total?: number | null;
  decision?: string;
  execution_status?: string;
  id?: string;
  mt5_comment?: string;
  mt5_retcode?: string;
  order_opened?: boolean;
  reason?: string;
  risk_status?: string;
  side?: string;
  signal_hash?: string;
  source?: string;
  status?: string;
  strategy_profile?: string;
  ticket?: string;
  timestamp?: string;
};

const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
const GROQ_MODEL = process.env.GROQ_MODEL || "gemma2-9b-it";
const GROQ_FALLBACK_MODEL = process.env.GROQ_FALLBACK_MODEL || "";
const REASON_STORE_PATH = path.join(process.cwd(), "..", "data", "reason_panel", "reason_messages.json");
const VALIDATION_ROUNDS_DIR = path.join(process.cwd(), "..", "data", "validation_rounds");
const TRADE_JOURNAL_PATH = path.join(process.cwd(), "..", "data", "trade_journal", "trade_journal.json");
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const BUSY_MESSAGE = "The assistant is temporarily busy. Please try again in a few seconds.";
const VALIDATION_SYMBOLS = new Set(["EURUSD", "XAUUSD", "NIFTY50"]);

const SYSTEM_PROMPT = "You are AlgoPilot. Answer briefly using only provided data. Do not invent trades, prices, balances, reasons, candle counts, or timeframes.";
const POSITION_FIELD_MISSING = "That field is not available in the live position data yet.";

const STRATEGY_GLOSSARY: Record<string, string> = {
  "any trigger": "Any trigger means the bot needs at least one live entry confirmation before opening a Level 3 trade: momentum, BOS, liquidity sweep, or pullback/retest. If none of those appear, the setup stays blocked even when HTF bias, RR, and spread are ready.",
  "htf bias": "HTF bias is the higher-timeframe direction read from H1/H4. Balanced Round 3 only allows buys with bullish higher-timeframe bias and sells with bearish higher-timeframe bias.",
  momentum: "Momentum means price is moving with enough displacement in the trade direction to support entry. It is one of the entry triggers and helps avoid slow, low-quality setups.",
  "pullback/retest": "Pullback/retest means price has returned into a valid entry area instead of chasing after an extended move. In Level 3 it can count as the one required trigger.",
  bos: "BOS means break of structure: price has broken a relevant swing level in the intended direction. It is a structure confirmation, not the only way to qualify a trade.",
  "liquidity sweep": "Liquidity sweep means price has taken liquidity beyond a recent high or low and then shown signs of reversing or continuing with intent. It can act as a structure trigger.",
  fvg: "FVG means fair value gap or imbalance zone. A retest of that zone can add structure confirmation for the balanced entry model.",
  rr: "RR is risk/reward. Round 3 requires RR >= 2.0, meaning the planned reward must be at least twice the planned risk before an order can be sent.",
  "spread clean": "Spread clean means the current broker spread is inside the bot's allowed limit. If spread is not clean, the setup is blocked to avoid poor fills.",
  "adaptive level": "Adaptive level is the per-symbol relaxation level. Each symbol has its own level, and the bot can relax only that symbol after inactivity while keeping hard gates like HTF bias, RR, spread, SL/TP, and risk approval.",
  "level 0": "Level 0 is the strict balanced Round 3 mode. It prefers score >= 6 with all hard gates intact.",
  "level 1": "Level 1 is a slightly more active mode for a symbol after inactivity. It can use score >= 5 while keeping all hard safety gates.",
  "level 2": "Level 2 keeps the score >= 5 floor and hard gates, but allows the symbol to remain more active after continued inactivity.",
  "level 3": "Level 3 is the fastest controlled mode. It still requires HTF bias, RR >= 2, clean spread, valid SL/TP, risk approval, and at least one trigger: momentum, BOS, liquidity sweep, or pullback/retest.",
  "scan score": "Scan score is the current checklist score for a symbol. It measures how many active entry conditions are currently passing for that symbol's adaptive level.",
  "final decision": "Final decision is the current Round 3 approval object. Orders may only be sent when the final decision is ACCEPTED for the active round, active session, matching symbol, passing score, and hard gates.",
  "legacy-path loss": "Legacy-path loss means a trade was opened by an older approval path rather than the current final-decision gate. Those losses are tracked separately in autopsy and analytics.",
  "breakeven trigger": "The breakeven trigger is the profit threshold where the bot can move SL to entry. Round 3 uses breakeven only after meaningful favorable movement, currently around +0.8R.",
  "trailing stop": "Trailing stop is protective SL movement after the trade has advanced far enough, currently after about +1.2R. It protects gains without closing on tiny noise.",
  "exit management": "Exit management monitors open MT5 positions for breakeven, trailing stop, max-hold/no-progress, opposite structure, and confirmed SL/TP closure. It must keep running even while the round is waiting for open trades to close.",
};

const STRATEGY_GLOSSARY_ALIASES: Record<string, string> = {
  "what is any trigger": "any trigger",
  "what does any trigger mean": "any trigger",
  "higher timeframe bias": "htf bias",
  "h1/h4": "htf bias",
  "h4/h1": "htf bias",
  "break of structure": "bos",
  "fair value gap": "fvg",
  "risk reward": "rr",
  "risk/reward": "rr",
  spread: "spread clean",
  "adaptive strategy": "adaptive level",
  "strategy level": "adaptive level",
  "level three": "level 3",
  "level zero": "level 0",
  "scan score": "scan score",
  "final decision": "final decision",
  "legacy path": "legacy-path loss",
  breakeven: "breakeven trigger",
  "break even": "breakeven trigger",
  trailing: "trailing stop",
  exits: "exit management",
};

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
    normalized.includes("unknown reason")
  );
}

function cleanText(value: unknown): string {
  const cleaned = text(value).replace(/\s+/g, " ").replace(/\.\.+/g, ".").trim();
  return isBadText(cleaned) ? "" : cleaned;
}

function answerStrategyGlossaryQuestion(question: string): string | null {
  const normalized = question.toLowerCase().replace(/[?!.]/g, " ").replace(/\s+/g, " ").trim();
  const direct = Object.keys(STRATEGY_GLOSSARY).find((term) => normalized === term || normalized.includes(term));
  if (direct) return STRATEGY_GLOSSARY[direct];
  const alias = Object.entries(STRATEGY_GLOSSARY_ALIASES).find(([phrase]) => normalized.includes(phrase));
  if (alias) return STRATEGY_GLOSSARY[alias[1]];
  const isDefinitionQuestion = /\b(what|define|meaning|mean|explain)\b/.test(normalized);
  if (!isDefinitionQuestion) return null;
  const compact = normalized.replace(/\s+/g, "");
  if (compact.includes("bos")) return STRATEGY_GLOSSARY.bos;
  if (compact.includes("fvg")) return STRATEGY_GLOSSARY.fvg;
  if (compact === "rr" || compact.includes("whatisrr") || compact.includes("rrmean")) return STRATEGY_GLOSSARY.rr;
  return null;
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
    data_source: cleanText(readField(record, ["data_source", "dataSource"])),
    rejection_reason: cleanText(readField(record, ["rejection_reason", "rejectionReason"])),
    symbol: text(readField(record, ["symbol"])).toUpperCase(),
    timeframe: text(readField(record, ["timeframe"])).toUpperCase(),
    validation_status: cleanText(readField(record, ["validation_status", "validationStatus"])),
  };
}

function normalizeReasonRecord(record: Record<string, unknown>): ReasonRecord {
  const diagnostic = normalizeReasonDiagnostic(record);
  return {
    ...diagnostic,
    adaptive_level: numberValue(readField(record, ["adaptive_level", "adaptiveLevel", "symbol_adaptive_level", "symbolAdaptiveLevel"])),
    decision: cleanText(readField(record, ["decision"])),
    confirmation_missing: Array.isArray(record.confirmation_missing) ? record.confirmation_missing.map(cleanText).filter(Boolean) : [],
    confirmation_passed: Array.isArray(record.confirmation_passed) ? record.confirmation_passed.map(cleanText).filter(Boolean) : [],
    confirmation_required: numberValue(readField(record, ["confirmation_required", "confirmationRequired"])),
    confirmation_score: numberValue(readField(record, ["confirmation_score", "confirmationScore"])),
    confirmation_total: numberValue(readField(record, ["confirmation_total", "confirmationTotal"])),
    execution_status: cleanText(readField(record, ["execution_status", "executionStatus"])),
    id: text(readField(record, ["id"])),
    mt5_comment: cleanText(readField(record, ["mt5_comment", "mt5Comment"])),
    mt5_retcode: cleanText(readField(record, ["mt5_retcode", "mt5Retcode", "retcode"])),
    order_opened: record.order_opened === true || record.orderOpened === true,
    reason: cleanText(readField(record, ["reason"])),
    risk_status: cleanText(readField(record, ["risk_status", "riskStatus"])),
    side: text(readField(record, ["side", "type", "action"])).toUpperCase(),
    signal_hash: text(readField(record, ["signal_hash", "signalHash"])),
    source: cleanText(readField(record, ["source"])),
    status: cleanText(readField(record, ["status"])),
    strategy_profile: cleanText(readField(record, ["strategy_profile", "strategyProfile"])),
    ticket: cleanText(readField(record, ["ticket", "mt5_ticket", "mt5Ticket"])),
    timestamp: text(readField(record, ["timestamp", "created_at", "createdAt"])),
  };
}

function sortReasonRecords(records: ReasonRecord[]): ReasonRecord[] {
  return [...records].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp || "");
    const rightTime = Date.parse(right.timestamp || "");
    return (Number.isFinite(rightTime) ? rightTime : 0) - (Number.isFinite(leftTime) ? leftTime : 0);
  });
}

async function readReasonRecords(): Promise<ReasonRecord[]> {
  try {
    const raw = await readFile(REASON_STORE_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return sortReasonRecords(parsed.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object")).map(normalizeReasonRecord));
  } catch {
    return [];
  }
}

async function readTradeJournalRecords(): Promise<Record<string, unknown>[]> {
  try {
    const raw = await readFile(TRADE_JOURNAL_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    const trades = asRecord(parsed)?.trades;
    return Array.isArray(trades) ? trades.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object")) : [];
  } catch {
    return [];
  }
}

async function readReasonDiagnostics(): Promise<ReasonDiagnostic[]> {
  try {
    return (await readReasonRecords())
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

function isOpenTradesQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    (normalized.includes("open trade") || normalized.includes("open position") || normalized.includes("active trade") || normalized.includes("active position")) &&
    (normalized.includes("how many") || normalized.includes("count") || normalized.includes("currently") || normalized.includes("active"))
  );
}

function isOpenTicketQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return normalized.includes("ticket") && (normalized.includes("open") || normalized.includes("currently active") || normalized.includes("active"));
}

function isLatestAcceptanceQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("latest") &&
    (normalized.includes("accepted") || normalized.includes("rejected") || normalized.includes("accept") || normalized.includes("reject")) &&
    (normalized.includes("signal") || normalized.includes("eurusd") || normalized.includes("xauusd") || normalized.includes("trade"))
  );
}

function isOpenTradeReasonQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return normalized.includes("why") && normalized.includes("open") && (normalized.includes("trade") || normalized.includes("position"));
}

function isLivePositionQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("tp") ||
    normalized.includes("take profit") ||
    normalized.includes("sl") ||
    normalized.includes("stop loss") ||
    normalized.includes("entry") ||
    normalized.includes("floating") ||
    normalized.includes("p&l") ||
    normalized.includes("pnl") ||
    normalized.includes("profit") ||
    normalized.includes("trade age") ||
    normalized.includes("age") ||
    normalized.includes("position status") ||
    normalized.includes("being monitored") ||
    normalized.includes("monitored") ||
    (normalized.includes("what symbols") && (normalized.includes("open") || normalized.includes("position")))
  );
}

function isClosedTradeQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("closed") ||
    normalized.includes("win") ||
    normalized.includes("loss") ||
    normalized.includes("net p&l") ||
    normalized.includes("net pnl")
  ) && !isLivePositionQuestion(question);
}

function isTradeAutopsyQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("autopsy") ||
    normalized.includes("mfe") ||
    normalized.includes("mae") ||
    normalized.includes("max favorable") ||
    normalized.includes("max adverse") ||
    normalized.includes("move in favor") ||
    normalized.includes("moved in favor") ||
    normalized.includes("first moved") ||
    normalized.includes("entry timing") ||
    normalized.includes("entries early") ||
    normalized.includes("were entries early") ||
    normalized.includes("waiting one candle") ||
    normalized.includes("waited one candle") ||
    normalized.includes("recurring pattern") ||
    normalized.includes("compare all losses") ||
    normalized.includes("all losses") ||
    normalized.includes("losses happened immediately") ||
    normalized.includes("symbol performs better") ||
    normalized.includes("which symbol performs better") ||
    normalized.includes("confirmation is most valuable") ||
    normalized.includes("why did ticket") ||
    normalized.includes("ticket") && normalized.includes("lose") ||
    normalized.includes("latest loss") ||
    normalized.includes("wrong with") ||
    normalized.includes("should the bot have waited") ||
    normalized.includes("should have waited") ||
    normalized.includes("confirmation caused") ||
    normalized.includes("which confirmation") ||
    normalized.includes("causing most losses") ||
    (normalized.includes("loss") && (normalized.includes("confirmation") || normalized.includes("pattern") || normalized.includes("early") || normalized.includes("wait")))
  );
}

function ticketFromQuestion(question: string): string {
  const match = question.match(/\bticket\s*#?\s*(\d{5,})\b/i) || question.match(/\b(\d{8,})\b/);
  return match?.[1] ?? "";
}

function isProgressQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return normalized.includes("validation progress") || normalized.includes("remaining trade") || normalized.includes("current progress") || normalized.includes("progress");
}

function isStrategyRulesQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("round 3 rules") ||
    normalized.includes("entry rules") ||
    normalized.includes("strategy rules") ||
    normalized.includes("validation rules") ||
    (normalized.includes("round 3") && (normalized.includes("require") || normalized.includes("filter"))) ||
    (normalized.includes("what") && normalized.includes("rules") && (normalized.includes("entry") || normalized.includes("strategy") || normalized.includes("validation")))
  );
}

function isValidationHaltedQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return normalized.includes("validation") && (normalized.includes("halted") || normalized.includes("halt") || normalized.includes("stopped by risk") || normalized.includes("risk halt"));
}

async function answerValidationHaltedQuestion(question: string): Promise<string | null> {
  if (!isValidationHaltedQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/status");
  const session = asRecord(status?.session);
  const riskHalt = asRecord(status?.risk_halt) ?? asRecord(session?.risk_halt_diagnostics);
  if (!session) return "Validation status is not available right now.";
  const mode = cleanText(session.status) || cleanText(status?.mode) || "unknown";
  const reason = cleanText(riskHalt?.reason) || cleanText(session.reason_stopped);
  const message = cleanText(riskHalt?.message);
  const closed = numberValue(session.current_closed_trades) ?? numberValue(session.current_session_closed) ?? 0;
  const wins = numberValue(session.wins) ?? 0;
  const losses = numberValue(session.losses) ?? 0;
  const netPnl = numberValue(session.net_pnl) ?? 0;
  const drawdown = numberValue(session.max_drawdown) ?? 0;
  const dailyLimit = numberValue(riskHalt?.max_daily_loss_amount);
  const drawdownLimit = numberValue(riskHalt?.max_total_drawdown_amount);
  if (mode === "HALTED_RISK") {
    return `${message || `Validation is risk halted because ${reason || "a risk protection triggered"}.`} Current active round: ${closed} closed, ${wins} wins, ${losses} losses, net P&L ${formatMoney(netPnl)}, max drawdown ${formatMoney(drawdown)}.${dailyLimit !== null ? ` Daily loss limit: ${formatMoney(dailyLimit)}.` : ""}${drawdownLimit !== null ? ` Drawdown limit: ${formatMoney(drawdownLimit)}.` : ""}`;
  }
  if (cleanText(riskHalt?.status) === "RISK_CLEARED") {
    return `${message || "A stale risk halt was cleared safely."} Validation is paused, not running. Current active round remains ${closed} closed, ${wins} wins, ${losses} losses, net P&L ${formatMoney(netPnl)}.`;
  }
  return `Validation is not currently risk halted. Status is ${mode}. Current active round: ${closed} closed, ${wins} wins, ${losses} losses, net P&L ${formatMoney(netPnl)}.`;
}

function tradePnlValue(trade: Record<string, unknown>): number {
  return numberValue(trade.net_pnl) ?? numberValue(trade.total_pnl) ?? numberValue(trade.profit_loss) ?? numberValue(trade.pnl) ?? 0;
}

function tradeTicketValue(trade: Record<string, unknown>): string {
  return cleanText(trade.mt5_ticket) || cleanText(trade.ticket) || cleanText(trade.trade_id);
}

function tradeAutopsyRecord(trade: Record<string, unknown>): Record<string, unknown> | null {
  return asRecord(trade.autopsy);
}

function autopsyList(autopsy: Record<string, unknown> | null, key: string): string[] {
  const raw = autopsy?.[key];
  return Array.isArray(raw) ? raw.map(cleanText).filter(Boolean) : [];
}

type AutopsyTrade = {
  trade: Record<string, unknown>;
  autopsy: Record<string, unknown>;
};

function autopsyConfidenceScore(items: AutopsyTrade[]): number {
  if (!items.length) return 0;
  const completeness = items.filter(({ autopsy }) => Object.keys(autopsy).length > 0).length / items.length;
  return Math.round(Math.min(0.95, Math.max(0.45, completeness * 0.9 + Math.min(items.length, 10) * 0.005)) * 100);
}

function autopsyConfirmationBucket(value: string): string {
  const normalized = value.toLowerCase();
  if (normalized.includes("bos")) return "BOS missing";
  if (normalized.includes("liquidity") || normalized.includes("sweep")) return "Liquidity sweep missing";
  if (normalized.includes("fvg") || normalized.includes("imbalance")) return "FVG missing";
  if (normalized.includes("momentum") || normalized.includes("displacement")) return "Momentum missing";
  if (normalized.includes("pullback") || normalized.includes("retest")) return "Pullback/retest missing";
  if (normalized.includes("htf") || normalized.includes("h1/h4") || normalized.includes("trend")) return "HTF alignment missing";
  if (normalized.includes("atr") || normalized.includes("volatility")) return "ATR volatility missing";
  if (normalized.includes("spread")) return "Clean spread missing";
  if (normalized.includes("rr")) return "RR >= 2.0 missing";
  return value;
}

function rankedCounts(values: string[], denominator: number): string {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    const label = autopsyConfirmationBucket(value);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  });
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([label, count]) => `${label}: ${count}/${denominator} (${denominator ? Math.round((count / denominator) * 100) : 0}%)`)
    .join("; ");
}

function modeText(values: string[], fallback = "Unavailable"): string {
  const counts = new Map<string, number>();
  values.map(cleanText).filter(Boolean).forEach((value) => counts.set(value, (counts.get(value) ?? 0) + 1));
  const top = [...counts.entries()].sort((left, right) => right[1] - left[1])[0];
  return top ? `${top[0]} (${top[1]})` : fallback;
}

function activeRoundAutopsyTrades(trades: Record<string, unknown>[], activeSessionId: string): AutopsyTrade[] {
  return trades
    .filter((trade) => !activeSessionId || cleanText(trade.validation_session_id) === activeSessionId)
    .filter((trade) => cleanText(trade.status).toUpperCase() === "CLOSED")
    .map((trade) => ({ trade, autopsy: tradeAutopsyRecord(trade) ?? {} }))
    .filter(({ autopsy }) => Object.keys(autopsy).length > 0)
    .sort((left, right) => Date.parse(cleanText(right.trade.closed_at) || cleanText(right.trade.updated_at)) - Date.parse(cleanText(left.trade.closed_at) || cleanText(left.trade.updated_at)));
}

function lossAutopsies(items: AutopsyTrade[]): AutopsyTrade[] {
  return items.filter(({ trade }) => cleanText(trade.result).toUpperCase() === "LOSS" || tradePnlValue(trade) < 0);
}

function winAutopsies(items: AutopsyTrade[]): AutopsyTrade[] {
  return items.filter(({ trade }) => cleanText(trade.result).toUpperCase() === "WIN" || tradePnlValue(trade) > 0);
}

function formatAutopsyAnswer(trade: Record<string, unknown>): string {
  const autopsy = tradeAutopsyRecord(trade);
  const ticket = tradeTicketValue(trade);
  const symbol = cleanText(trade.symbol) || cleanText(autopsy?.symbol) || "Trade";
  const side = cleanText(trade.side) || cleanText(autopsy?.direction) || "trade";
  const pnl = tradePnlValue(trade);
  const score = numberValue(autopsy?.score_at_entry) ?? numberValue(trade.confirmation_score);
  const missing = autopsyList(autopsy, "confirmations_missing");
  const reason = cleanText(autopsy?.reason_for_loss) || cleanText(trade.exit_reason) || "Loss reason is not available yet.";
  const waited = autopsy?.should_have_waited === true ? "Yes, the bot should have waited." : autopsy?.should_have_waited === false ? "No clear wait signal was recorded." : "Wait assessment is not available yet.";
  const fix = cleanText(autopsy?.suggested_rule_fix) || "No rule fix has been generated yet.";
  const entryQuality = cleanText(autopsy?.entry_quality) || "Pending";
  const mfe = numberValue(autopsy?.max_favorable_excursion);
  const mae = numberValue(autopsy?.max_adverse_excursion);
  const movedFirst = autopsy?.did_price_move_in_favor_first === true ? "moved in favor first" : autopsy?.did_price_move_in_favor_first === false ? "moved adverse first" : "first move unavailable";
  return `${symbol} ticket ${ticket} ${side} closed with P&L ${formatMoney(pnl)}. Entry quality: ${entryQuality}.${score !== null ? ` Score at entry: ${score}.` : ""} ${missing.length ? `Missing confirmation: ${missing.join(", ")}.` : "No missing confirmation was recorded."} MFE ${mfe ?? "n/a"}, MAE ${mae ?? "n/a"}; price ${movedFirst}. Why: ${reason} ${waited} Suggested fix: ${fix} Confidence: ${autopsy ? 92 : 45}%.`;
}

async function answerTradeAutopsyQuestion(question: string): Promise<string | null> {
  if (!isTradeAutopsyQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/status");
  const activeSessionId = cleanText(status?.active_session_id) || cleanText(asRecord(status?.session)?.session_id);
  const autopsies = activeRoundAutopsyTrades(await readTradeJournalRecords(), activeSessionId);
  if (!autopsies.length) return "No active-round autopsy objects are available yet.";
  const losses = lossAutopsies(autopsies);
  const wins = winAutopsies(autopsies);
  const normalized = question.toLowerCase();
  const confidence = autopsyConfidenceScore(autopsies);
  if (normalized.includes("which confirmation") && normalized.includes("valuable")) {
    const allBuckets = [...new Set(autopsies.flatMap(({ autopsy }) => autopsyList(autopsy, "confirmations_present").map(autopsyConfirmationBucket)))];
    const rows = allBuckets.map((label) => {
      const scoped = autopsies.filter(({ autopsy }) => autopsyList(autopsy, "confirmations_present").map(autopsyConfirmationBucket).includes(label));
      const scopedWins = winAutopsies(scoped).length;
      return { label, trades: scoped.length, wins: scopedWins, winRate: scoped.length ? (scopedWins / scoped.length) * 100 : 0 };
    }).filter((row) => row.trades > 0).sort((left, right) => right.winRate - left.winRate || right.trades - left.trades);
    if (!rows.length) return `Autopsies exist, but no present-confirmation win-rate contribution is available yet. Confidence: ${confidence}%.`;
    return `Most valuable confirmations by active-round autopsy win rate: ${rows.map((row) => `${row.label}: ${row.wins}/${row.trades} wins (${row.winRate.toFixed(0)}%)`).join("; ")}. Confidence: ${confidence}%.`;
  }
  if (normalized.includes("which confirmation") || normalized.includes("confirmation caused") || normalized.includes("causing most losses")) {
    const missing = losses.flatMap(({ autopsy }) => autopsyList(autopsy, "confirmations_missing"));
    if (!missing.length) return `Loss autopsies exist, but no missing-confirmation counts are available. Confidence: ${confidence}%.`;
    return `Ranked missing confirmations across ${losses.length} active-round losses: ${rankedCounts(missing, losses.length)}. Confidence: ${confidence}%.`;
  }
  if (normalized.includes("move in favor") || normalized.includes("moved in favor") || normalized.includes("mfe") || normalized.includes("mae") || normalized.includes("first moved")) {
    const rows = losses.map(({ trade, autopsy }) => {
      const moved = autopsy.did_price_move_in_favor_first === true ? "yes" : autopsy.did_price_move_in_favor_first === false ? "no" : "unknown";
      return `${tradeTicketValue(trade)}: MFE ${numberValue(autopsy.max_favorable_excursion) ?? "n/a"}, MAE ${numberValue(autopsy.max_adverse_excursion) ?? "n/a"}, moved in favor first: ${moved}`;
    });
    return `Price movement before SL from loss autopsies: ${rows.join("; ")}. Confidence: ${confidence}%.`;
  }
  if (normalized.includes("entries early") || normalized.includes("entry timing") || normalized.includes("should the bot have waited") || normalized.includes("should have waited") || normalized.includes("waiting one candle") || normalized.includes("waited one candle")) {
    const early = losses.filter(({ autopsy }) => autopsy.was_entry_early === true || autopsy.should_have_waited === true);
    const pattern = modeText(early.flatMap(({ autopsy }) => autopsyList(autopsy, "confirmations_missing").map(autopsyConfirmationBucket)), "No repeated timing pattern");
    const answer = early.length > 0 ? "Yes" : "No";
    return `${answer}. ${early.length}/${losses.length} loss autopsies indicate the bot should have waited 1-3 M15 candles. Common timing pattern: ${pattern}. Confidence: ${confidence}%.`;
  }
  if (normalized.includes("compare all losses") || normalized.includes("recurring pattern") || (normalized.includes("all losses") && normalized.includes("pattern"))) {
    const missing = losses.flatMap(({ autopsy }) => autopsyList(autopsy, "confirmations_missing"));
    const levels = losses.map(({ autopsy }) => cleanText(autopsy.adaptive_level));
    const sessions = losses.map(({ trade }) => {
      const metadata = asRecord(trade.strategy_metadata);
      const components = asRecord(metadata?.strategy_components);
      return cleanText(components?.session) || cleanText(asRecord(trade.autopsy)?.session);
    });
    const scores = losses.map(({ autopsy }) => cleanText(autopsy.score_at_entry)).filter(Boolean);
    const weakness = modeText(missing.map(autopsyConfirmationBucket), "No repeated structure weakness");
    const fixes = losses.map(({ autopsy }) => cleanText(autopsy.suggested_rule_fix)).filter(Boolean);
    return `Recurring loss patterns from ${losses.length} autopsies: missing confirmations: ${rankedCounts(missing, losses.length)}. Common adaptive level: ${modeText(levels)}. Common market session: ${modeText(sessions)}. Common score at entry: ${modeText(scores)}. Common structure weakness: ${weakness}. Suggested improvement: ${modeText(fixes)}. Confidence: ${confidence}%.`;
  }
  if (normalized.includes("symbol performs better") || normalized.includes("which symbol performs better")) {
    const bySymbol = ["EURUSD", "XAUUSD"].map((symbol) => {
      const scoped = autopsies.filter(({ trade, autopsy }) => (cleanText(trade.symbol) || cleanText(autopsy.symbol)).toUpperCase() === symbol);
      const pnl = scoped.reduce((sum, item) => sum + tradePnlValue(item.trade), 0);
      const winRate = scoped.length ? (winAutopsies(scoped).length / scoped.length) * 100 : 0;
      return { symbol, trades: scoped.length, pnl, winRate };
    }).sort((left, right) => right.pnl - left.pnl || right.winRate - left.winRate);
    return `${bySymbol[0].symbol} performs better by active-round autopsies: ${bySymbol.map((row) => `${row.symbol}: ${row.trades} trades, ${row.winRate.toFixed(0)}% win rate, ${formatMoney(row.pnl)}`).join("; ")}. Confidence: ${confidence}%.`;
  }
  if (normalized.includes("losses happened immediately")) {
    const immediate = losses.filter(({ trade }) => (numberValue(trade.duration_minutes) ?? 9999) <= 15);
    return `Immediate losses (<=15 minutes): ${immediate.length ? immediate.map(({ trade }) => `${tradeTicketValue(trade)} (${numberValue(trade.duration_minutes)} min)`).join("; ") : "none recorded"}. Confidence: ${confidence}%.`;
  }
  const ticket = ticketFromQuestion(question);
  const trade = ticket ? autopsies.find((item) => tradeTicketValue(item.trade) === ticket)?.trade : losses[0]?.trade;
  if (!trade) return ticket ? `I could not find ticket ${ticket} in the active round trade journal.` : "No current-round loss autopsy is available yet.";
  if (!tradeAutopsyRecord(trade)) return `Ticket ${tradeTicketValue(trade)} does not have an autopsy object yet. Run backend status once to trigger active-round autopsy backfill.`;
  return formatAutopsyAnswer(trade);
}

type ValidationRoundSnapshot = Record<string, unknown> & {
  round_number?: number;
  session_id?: string;
  round_label?: string;
};

function roundNumberFromQuestion(question: string): number | null {
  const match = question.match(/\bround\s*(\d+)\b/i);
  return match ? Number(match[1]) : null;
}

async function readValidationRoundsIndex(): Promise<Record<string, unknown>> {
  try {
    const raw = await readFile(path.join(VALIDATION_ROUNDS_DIR, "rounds_index.json"), "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

async function readValidationRoundBySession(sessionId: string): Promise<ValidationRoundSnapshot | null> {
  if (!sessionId) return null;
  const safe = sessionId.replace(/[^a-zA-Z0-9_-]/g, "_");
  try {
    const raw = await readFile(path.join(VALIDATION_ROUNDS_DIR, `round_${safe}.json`), "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as ValidationRoundSnapshot) : null;
  } catch {
    return null;
  }
}

async function readValidationRoundByNumber(roundNumber: number): Promise<ValidationRoundSnapshot | null> {
  const index = await readValidationRoundsIndex();
  const rounds = Array.isArray(index.rounds) ? index.rounds : [];
  const entry = rounds.find((item): item is Record<string, unknown> => Boolean(item && typeof item === "object" && Number(item.round_number) === roundNumber));
  return readValidationRoundBySession(text(entry?.session_id));
}

function roundSummaryLine(round: ValidationRoundSnapshot): string {
  const number = numberValue(round.round_number) ?? numberValue((round.session as Record<string, unknown> | undefined)?.round_number);
  const label = number ? `Round ${number}` : cleanText(round.round_label) || "That round";
  const closed = numberValue(round.closed_trades) ?? 0;
  const wins = numberValue(round.wins) ?? 0;
  const losses = numberValue(round.losses) ?? 0;
  const winRate = numberValue(round.win_rate) ?? (closed ? (wins / closed) * 100 : 0);
  const pnl = numberValue(round.net_pnl) ?? 0;
  const status = cleanText(round.status) || "archived";
  return `${label} (${status}) used session ${cleanText(round.session_id)}: ${closed} closed, ${wins} wins, ${losses} losses, win rate ${winRate.toFixed(2)}%, net P&L ${formatMoney(pnl)}.`;
}

function roundBestSetup(round: ValidationRoundSnapshot): string {
  const analytics = round.analytics_summary && typeof round.analytics_summary === "object" ? (round.analytics_summary as Record<string, unknown>) : {};
  const best = cleanText(analytics.best_setup_type) || cleanText((round.session as Record<string, unknown> | undefined)?.best_setup_type);
  return best && best !== "Unavailable" ? best : "No best setup is available yet.";
}

function roundLossReason(round: ValidationRoundSnapshot): string {
  const rejectionReasons = Array.isArray(round.rejection_reasons) ? round.rejection_reasons.map(cleanText).filter(Boolean) : [];
  const losses = Array.isArray(round.trades)
    ? round.trades.filter((item) => item && typeof item === "object" && cleanText((item as Record<string, unknown>).result).toUpperCase() === "LOSS")
    : [];
  if (rejectionReasons.length) return `Main recorded blockers: ${rejectionReasons.slice(0, 3).join("; ")}.`;
  if (losses.length) return `It lost money because ${losses.length} closed trades were losses; review the archived trade exit reasons for exact lifecycle causes.`;
  return "No loss diagnostics are available for that round yet.";
}

async function answerRoundArchiveQuestion(question: string): Promise<string | null> {
  const normalized = question.toLowerCase();
  const roundNumber = roundNumberFromQuestion(question);
  const asksRound = roundNumber !== null || /compare round|what changed between round|show round|what happened in round|why did round|best setup in round/i.test(question);
  if (!asksRound) return null;
  if (normalized.includes("compare") || normalized.includes("what changed")) {
    const matches = [...question.matchAll(/\bround\s*(\d+)\b/gi)].map((match) => Number(match[1]));
    if (matches.length < 2) return "Tell me which two rounds to compare, for example: compare Round 3 and Round 4.";
    const rounds = (await Promise.all(matches.slice(0, 2).map(readValidationRoundByNumber))).filter(Boolean) as ValidationRoundSnapshot[];
    if (rounds.length < 2) return "I could not find both archived rounds yet.";
    return `${roundSummaryLine(rounds[0])} ${roundSummaryLine(rounds[1])} Key change: ${cleanText(rounds[0].round_label)} to ${cleanText(rounds[1].round_label)} used separate session IDs and separately archived strategy configs.`;
  }
  if (roundNumber === null) return null;
  const round = await readValidationRoundByNumber(roundNumber);
  if (!round) return `Round ${roundNumber} is not archived yet.`;
  if (normalized.includes("win rate")) return `Round ${roundNumber} win rate was ${(numberValue(round.win_rate) ?? 0).toFixed(2)}%.`;
  if (normalized.includes("best setup")) return `Round ${roundNumber} best setup: ${roundBestSetup(round)}`;
  if (normalized.includes("why") && (normalized.includes("lose") || normalized.includes("lost") || normalized.includes("loss"))) return `Round ${roundNumber}: ${roundLossReason(round)} ${roundSummaryLine(round)}`;
  return roundSummaryLine(round);
}

function answerStrategyRulesQuestion(question: string): string | null {
  if (!isStrategyRulesQuestion(question)) return null;
  return "Round 3 uses edge-score validation: H4/M15 history ready, RR >= 2.0, risk approved, clean spread, valid SL/TP, and higher-timeframe direction bias are safety gates. London/NY is advisory only. Entry is allowed when the score meets the threshold with at least two strong confirmations from BOS, FVG, liquidity sweep, trend alignment, pullback/retest, momentum, volatility, spread, and RR.";
}

function readPositionField(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (value !== null && value !== undefined && cleanText(value)) return cleanText(value);
  }
  return "";
}

function readPositionNumber(record: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = numberValue(record[key]);
    if (value !== null) return value;
  }
  return null;
}

function formatNumber(value: number | null, digits = 5): string {
  if (value === null) return POSITION_FIELD_MISSING;
  return value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: value >= 100 ? 2 : 0 });
}

function formatMoney(value: number | null): string {
  if (value === null) return POSITION_FIELD_MISSING;
  return `$${value.toFixed(2)}`;
}

function formatPositionLine(position: Record<string, unknown>, detail: "levels" | "pnl" | "entry" | "monitoring" | "status"): string {
  const symbol = readPositionField(position, ["symbol"]) || "Position";
  const ticket = readPositionField(position, ["ticket"]) || POSITION_FIELD_MISSING;
  const side = readPositionField(position, ["side", "type"]) || "position";
  if (detail === "levels") {
    const sl = readPositionNumber(position, ["stop_loss", "sl"]);
    const tp = readPositionNumber(position, ["take_profit", "tp"]);
    return `${symbol} ticket ${ticket}: SL ${formatNumber(sl)}, TP ${formatNumber(tp)}.`;
  }
  if (detail === "pnl") {
    const pnl = readPositionNumber(position, ["floating_pnl", "profit"]);
    return `${symbol} ticket ${ticket}: floating P&L ${formatMoney(pnl)}.`;
  }
  if (detail === "entry") {
    const entry = readPositionNumber(position, ["entry_price", "price_open"]);
    return `${symbol} ticket ${ticket}: entry ${formatNumber(entry)}.`;
  }
  if (detail === "status") {
    const status = readPositionField(position, ["lifecycle_status", "status"]) || "OPEN";
    return `${symbol} ticket ${ticket}: ${status}.`;
  }
  return `${symbol} ticket ${ticket}: ${side}, monitored as an open MT5 position.`;
}

async function readLiveOpenPositions(): Promise<Record<string, unknown>[]> {
  try {
    const url = new URL("/mt5-demo/position-monitor/open", API_BASE_URL);
    url.searchParams.set("_ts", String(Date.now()));
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return [];
    const payload = (await response.json()) as Record<string, unknown>;
    const rawPositions = Array.isArray(payload.positions) ? payload.positions : [];
    return rawPositions
      .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
      .filter((position) => VALIDATION_SYMBOLS.has(readPositionField(position, ["symbol"]).toUpperCase()));
  } catch {
    return [];
  }
}

async function readBackendRecord(endpoint: string): Promise<Record<string, unknown> | null> {
  try {
    const url = new URL(endpoint, API_BASE_URL);
    url.searchParams.set("_ts", String(Date.now()));
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return null;
    const payload = (await response.json()) as unknown;
    return payload && typeof payload === "object" && !Array.isArray(payload) ? (payload as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function isHistoryReadinessQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("history ready") ||
    normalized.includes("history sync") ||
    normalized.includes("h4 candle") ||
    normalized.includes("h1 candle") ||
    normalized.includes("m15 candle") ||
    normalized.includes("candles loaded") ||
    normalized.includes("loaded 0") ||
    (normalized.includes("history") && normalized.includes("0"))
  );
}

function isNoTradeOpenedQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("why") &&
    (normalized.includes("no trade") || normalized.includes("zero trade") || normalized.includes("nothing")) &&
    (normalized.includes("open") || normalized.includes("opened") || normalized.includes("opening") || normalized.includes("placed"))
  );
}

function isSymbolNoTradeQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  const symbol = questionSymbol(question);
  return Boolean(symbol && normalized.includes("why") && (normalized.includes("not trade") || normalized.includes("no trade") || normalized.includes("hasn't traded") || normalized.includes("did not trade")));
}

function isCloserToQualifyingQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return normalized.includes("which symbol") && (normalized.includes("closer") || normalized.includes("qualifying") || normalized.includes("qualify") || normalized.includes("trading"));
}

function isLatestScanQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("latest scan") ||
    normalized.includes("scan diagnostic") ||
    normalized.includes("scan diagnostics") ||
    normalized.includes("score component") ||
    normalized.includes("current score") ||
    (normalized.includes("confirmation") && normalized.includes("missing"))
  );
}

function isAdaptiveLevelQuestion(question: string): boolean {
  const normalized = question.toLowerCase();
  return (
    normalized.includes("adaptive level") ||
    normalized.includes("strategy level") ||
    normalized.includes("level change") ||
    normalized.includes("stay strict") ||
    normalized.includes("stayed strict") ||
    normalized.includes("performing better")
  );
}

function adaptiveSymbolState(session: Record<string, unknown>, symbol: string): Record<string, unknown> | null {
  const state = asRecord(session.symbol_adaptive_state);
  return asRecord(state?.[symbol]);
}

function adaptiveLevelLine(symbol: string, state: Record<string, unknown> | null): string {
  if (!state) return `${symbol}: adaptive state is not available yet.`;
  const level = numberValue(state.current_level) ?? 0;
  const open = numberValue(state.open) ?? 0;
  const closed = numberValue(state.closed) ?? 0;
  const wins = numberValue(state.wins) ?? 0;
  const losses = numberValue(state.losses) ?? 0;
  const pnl = numberValue(state.net_pnl) ?? 0;
  const last = cleanText(state.last_activity_time);
  return `${symbol}: Level ${level}, open ${open}, closed ${closed}, wins ${wins}, losses ${losses}, net P&L ${formatMoney(pnl)}${last ? `, last activity ${last}` : ""}.`;
}

function latestAdaptiveHistory(state: Record<string, unknown> | null): Record<string, unknown> | null {
  const history = Array.isArray(state?.history) ? state.history.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object")) : [];
  return history.sort((left, right) => Date.parse(cleanText(right.timestamp)) - Date.parse(cleanText(left.timestamp)))[0] ?? null;
}

async function answerAdaptiveLevelQuestion(question: string): Promise<string | null> {
  if (!isAdaptiveLevelQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/status");
  const session = asRecord(status?.session);
  if (!session) return "Adaptive strategy state is not available right now.";
  const symbol = questionSymbol(question);
  const eurusd = adaptiveSymbolState(session, "EURUSD");
  const xauusd = adaptiveSymbolState(session, "XAUUSD");
  const normalized = question.toLowerCase();
  if (normalized.includes("performing better")) {
    const pairs = [
      { symbol: "EURUSD", state: eurusd },
      { symbol: "XAUUSD", state: xauusd },
    ].filter((item) => item.state);
    if (!pairs.length) return "No symbol performance data is available yet.";
    const ranked = pairs.sort((left, right) => (numberValue(right.state?.net_pnl) ?? 0) - (numberValue(left.state?.net_pnl) ?? 0));
    return `${ranked[0].symbol} is performing better by active-round net P&L. ${ranked.map((item) => adaptiveLevelLine(item.symbol, item.state)).join(" ")}`;
  }
  if (normalized.includes("closer")) {
    return answerSymbolScanQuestion(question);
  }
  if (symbol) {
    const state = adaptiveSymbolState(session, symbol);
    if (normalized.includes("why") && (normalized.includes("change") || normalized.includes("changed"))) {
      const latest = latestAdaptiveHistory(state);
      if (!latest) return `${symbol} has no adaptive level-change history in the current round yet. ${adaptiveLevelLine(symbol, state)}`;
      return `${symbol} changed from Level ${numberValue(latest.from_level) ?? "?"} to Level ${numberValue(latest.to_level) ?? "?"} because ${cleanText(latest.reason) || "its per-symbol inactivity rule triggered"}.`;
    }
    if (normalized.includes("stay strict") || normalized.includes("stayed strict")) {
      const level = numberValue(state?.current_level) ?? 0;
      if (level === 0) return `${symbol} stayed strict because its own inactivity timer has not lowered the threshold yet. ${adaptiveLevelLine(symbol, state)}`;
      return `${symbol} is not strict right now; it is using Level ${level}. ${adaptiveLevelLine(symbol, state)}`;
    }
    return adaptiveLevelLine(symbol, state);
  }
  return `${adaptiveLevelLine("EURUSD", eurusd)} ${adaptiveLevelLine("XAUUSD", xauusd)}`;
}

function scanBlockerLabel(value: string): string {
  const normalized = value.replace(/[_-]/g, " ").trim().toLowerCase();
  if (!normalized) return "";
  if (normalized.includes("htf") || normalized.includes("h1/h4") || normalized.includes("h4/h1") || normalized.includes("higher timeframe") || normalized.includes("trend alignment")) return "HTF alignment";
  if (normalized.includes("momentum") || normalized.includes("pullback") || normalized.includes("retest")) return "momentum/pullback";
  if (normalized.includes("structure") || normalized.includes("bos") || normalized.includes("liquidity") || normalized.includes("fvg")) return "structure confirmation";
  if (normalized.includes("spread")) return "clean spread";
  if (normalized.includes("rr") || normalized.includes("risk reward")) return "RR >= 2.0";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function uniqueScanLabels(values: string[]): string[] {
  const seen = new Set<string>();
  const labels = values.map(scanBlockerLabel).filter((value) => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const rank: Record<string, number> = { "HTF alignment": 0, "momentum/pullback": 1, "structure confirmation": 2 };
  return labels.sort((left, right) => (rank[left] ?? 99) - (rank[right] ?? 99));
}

function joinList(values: string[]): string {
  if (values.length <= 1) return values[0] ?? "";
  if (values.length === 2) return `${values[0]} and ${values[1]}`;
  return `${values.slice(0, -1).join(", ")}, and ${values[values.length - 1]}`;
}

function latestScanRecord(records: ReasonRecord[], symbol?: string | null): ReasonRecord | null {
  return records.find((record) => {
    if (cleanText(record.status).toUpperCase() !== "SCAN_RESULT") return false;
    return symbol ? record.symbol === symbol : true;
  }) ?? null;
}

function scanRecordSummary(record: ReasonRecord): string {
  const score = record.confirmation_score ?? 0;
  const required = record.confirmation_required ?? 5;
  const levelText = record.adaptive_level !== null && record.adaptive_level !== undefined ? ` Level ${record.adaptive_level}` : "";
  const missing = uniqueScanLabels([...(record.confirmation_missing ?? []), record.reason ?? "", record.rejection_reason ?? ""]).filter((label) => !/clean spread|RR/i.test(label));
  const blocked = missing.length ? `blocked by missing ${joinList(missing)}` : cleanText(record.reason) || "blocked by current balanced gates";
  return `${record.symbol}${levelText} latest scan: score ${score}/${required}, ${blocked}.`;
}

function latestScanDiagnosticsFromStatus(status: Record<string, unknown> | null): Record<string, Record<string, unknown>> {
  const root = asRecord(status?.scans) ?? asRecord(status?.canonical_scans) ?? asRecord(asRecord(status?.live_scan_status)?.symbols) ?? asRecord(asRecord(status?.session)?.canonical_scans) ?? {};
  return Object.fromEntries(Object.entries(root).filter((entry): entry is [string, Record<string, unknown>] => Boolean(asRecord(entry[1]))).map(([symbol, value]) => [symbol.toUpperCase(), value as Record<string, unknown>]));
}

function scanDiagnosticSummary(symbol: string, diagnostic: Record<string, unknown>): string {
  const basePassed = numberValue(diagnostic.base_passed) ?? 0;
  const baseTotal = numberValue(diagnostic.base_total) ?? 3;
  const confirmationsPassed = numberValue(diagnostic.confirmations_passed) ?? 0;
  const confirmationsTotal = numberValue(diagnostic.confirmations_total) ?? 5;
  const required = numberValue(diagnostic.required_confirmations) ?? 1;
  const level = numberValue(diagnostic.adaptive_level) ?? 0;
  const decision = cleanText(diagnostic.decision) || "PENDING";
  const missingBase = Array.isArray(diagnostic.missing_base_gates) ? diagnostic.missing_base_gates.map(cleanText).filter(Boolean) : [];
  const missingConfirmations = Array.isArray(diagnostic.missing_confirmations) ? diagnostic.missing_confirmations.map(cleanText).filter(Boolean) : [];
  const missing = [...missingBase, ...missingConfirmations];
  const reason = cleanText(diagnostic.order_block_reason);
  const timing = numberValue(diagnostic.total_scan_ms);
  return `${symbol} latest scan: Level ${level}, base gates ${basePassed}/${baseTotal}, confirmations ${confirmationsPassed}/${confirmationsTotal}, requires ${required}, decision ${decision}. Missing: ${missing.length ? missing.join(", ") : "none"}. ${reason ? `Reason: ${reason}. ` : ""}${timing !== null ? `Scan time ${timing} ms.` : ""}`;
}

async function answerSymbolScanQuestion(question: string): Promise<string | null> {
  if (!isSymbolNoTradeQuestion(question) && !isCloserToQualifyingQuestion(question) && !isLatestScanQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/canonical-scan");
  const diagnostics = latestScanDiagnosticsFromStatus(status);
  if (isCloserToQualifyingQuestion(question)) {
    const scanDiagnostics = ["EURUSD", "XAUUSD"].map((symbol) => ({ symbol, diagnostic: diagnostics[symbol] })).filter((item) => item.diagnostic);
    if (scanDiagnostics.length) {
      const ranked = scanDiagnostics.sort((left, right) => {
        const leftBase = (numberValue(left.diagnostic?.base_passed) ?? 0) - (numberValue(left.diagnostic?.base_total) ?? 3);
        const rightBase = (numberValue(right.diagnostic?.base_passed) ?? 0) - (numberValue(right.diagnostic?.base_total) ?? 3);
        if (rightBase !== leftBase) return rightBase - leftBase;
        const leftConfirmations = (numberValue(left.diagnostic?.confirmations_passed) ?? 0) - (numberValue(left.diagnostic?.required_confirmations) ?? 1);
        const rightConfirmations = (numberValue(right.diagnostic?.confirmations_passed) ?? 0) - (numberValue(right.diagnostic?.required_confirmations) ?? 1);
        return rightConfirmations - leftConfirmations;
      });
      return `${ranked[0].symbol} is closest based on canonical scan diagnostics. ${ranked.map((item) => scanDiagnosticSummary(item.symbol, item.diagnostic as Record<string, unknown>)).join(" ")}`;
    }
    return "No canonical EURUSD/XAUUSD scan diagnostics are available yet.";
  }
  const symbol = questionSymbol(question);
  if (!symbol || !["EURUSD", "XAUUSD"].includes(symbol)) {
    if (isLatestScanQuestion(question) && Object.keys(diagnostics).length) {
      return ["EURUSD", "XAUUSD"].filter((item) => diagnostics[item]).map((item) => scanDiagnosticSummary(item, diagnostics[item])).join(" ");
    }
    return null;
  }
  if (diagnostics[symbol]) return scanDiagnosticSummary(symbol, diagnostics[symbol]);
  return `${symbol} has no canonical scan diagnostic yet.`;
}

function historyWarmupFromStatus(status: Record<string, unknown> | null): Record<string, unknown> | null {
  if (!status) return null;
  return asRecord(status.history_warmup) ?? asRecord(asRecord(status.last_execution_decision)?.history_warmup);
}

function historyDiagnostics(warmup: Record<string, unknown> | null): Record<string, unknown>[] {
  const raw = Array.isArray(warmup?.diagnostics) ? warmup.diagnostics : [];
  return raw.filter((item): item is Record<string, unknown> => Boolean(asRecord(item)));
}

function historyDiagnosticSummary(diagnostic: Record<string, unknown>): string {
  const symbol = cleanText(diagnostic.requested_symbol) || cleanText(diagnostic.symbol) || "EURUSD";
  const resolved = cleanText(diagnostic.resolved_symbol) || symbol;
  const timeframe = cleanText(diagnostic.timeframe) || "H4";
  const loaded = numberValue(diagnostic.candles_loaded) ?? 0;
  const required = numberValue(diagnostic.candles_required) ?? 300;
  return `${symbol} ${timeframe} resolved as ${resolved}: loaded ${loaded} / required ${required} candles`;
}

function historyErrorSummary(diagnostic: Record<string, unknown>): string {
  const error = cleanText(diagnostic.mt5_last_error) || cleanText(diagnostic.symbol_select_error);
  const connection = cleanText(diagnostic.connection_id);
  const process = cleanText(diagnostic.process_id);
  const connectionText = connection ? ` Connection: ${connection}.` : process ? ` Process id: ${process}.` : "";
  return (error ? ` MT5 last_error: ${error}.` : " MT5 did not report a last_error.") + connectionText;
}

function firstPendingHistoryDiagnostic(diagnostics: Record<string, unknown>[]): Record<string, unknown> | null {
  const pending = diagnostics.filter((item) => item.history_ready !== true);
  const rank: Record<string, number> = { H4: 0, M15: 1, H1: 2 };
  return pending.sort((left, right) => (rank[cleanText(left.timeframe).toUpperCase()] ?? 9) - (rank[cleanText(right.timeframe).toUpperCase()] ?? 9))[0] ?? null;
}

async function answerHistoryReadinessQuestion(question: string): Promise<string | null> {
  if (!isHistoryReadinessQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/status");
  const warmup = historyWarmupFromStatus(status);
  const diagnostics = historyDiagnostics(warmup);
  if (!diagnostics.length) return "MT5 history warmup diagnostics have not been recorded yet.";
  const timeframe = questionTimeframe(question);
  const symbol = questionSymbol(question);
  if (timeframe) {
    const match = diagnostics.find((item) => cleanText(item.timeframe).toUpperCase() === timeframe && (!symbol || cleanText(item.symbol).toUpperCase() === symbol));
    if (match) {
      const readyText = match.history_ready === true ? "ready" : "not ready";
      return `${historyDiagnosticSummary(match)}. History is ${readyText}.${historyErrorSummary(match)}`;
    }
  }
  const pending = firstPendingHistoryDiagnostic(diagnostics);
  const normalized = question.toLowerCase();
  if (normalized.includes("loaded 0") || (normalized.includes("history") && normalized.includes("0"))) {
    const zero = diagnostics.find((item) => (numberValue(item.candles_loaded) ?? 0) === 0) ?? pending;
    if (zero) return `History is loaded 0 because MT5 returned no candles for the resolved symbol/timeframe. ${historyDiagnosticSummary(zero)}.${historyErrorSummary(zero)}`;
  }
  if (normalized.includes("why") && normalized.includes("trade")) {
    if (pending) return `No trades are opening because MT5 history sync is still warming. ${historyDiagnosticSummary(pending)}.${historyErrorSummary(pending)}`;
    return "MT5 history is ready. If no trades open, Balanced Round 3 is waiting for the active symbol gates: HTF bias, RR >= 2.0, clean spread, risk approval, valid SL/TP, and the required trigger/score for that symbol's adaptive level.";
  }
  if (normalized.includes("history ready") || normalized.includes("history sync")) {
    if (pending) return `History is not ready. ${historyDiagnosticSummary(pending)}.${historyErrorSummary(pending)}`;
    return "History is ready for Round 3 M15, H1, and H4 validation.";
  }
  return diagnostics.map(historyDiagnosticSummary).join(". ") + ".";
}

async function answerNoTradeOpenedQuestion(question: string): Promise<string | null> {
  if (!isNoTradeOpenedQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/status");
  const trace = asRecord(status?.latest_decision_trace) ?? asRecord(asRecord(status?.session)?.latest_decision_trace);
  if (!trace) return "No decision trace has been recorded yet. Run one validation scan cycle to capture the exact blocker.";
  const level = numberValue(trace.adaptive_level);
  const symbol = cleanText(trace.symbol) || "latest symbol";
  const decision = cleanText(trace.execution_decision) || "not sent";
  const score = numberValue(trace.score);
  const failed = Array.isArray(trace.failed_hard_gates) ? trace.failed_hard_gates.map(cleanText).filter(Boolean) : [];
  const reason = cleanText(trace.why_order_not_sent);
  const scoreText = score !== null ? ` Score ${score}.` : "";
  const failedText = failed.length ? ` Failed gate: ${failed[0].replaceAll("_", " ")}.` : "";
  const reasonText = reason ? ` Reason: ${reason}` : "";
  return `${symbol} has not opened because the latest scan decision was ${decision} at Adaptive Level ${level ?? 0}.${scoreText}${failedText}${reasonText}`;
}

function logOpenPositionsForChat(positions: Record<string, unknown>[]): void {
  console.log(
    "Chat live MT5 open positions:",
    positions.map((position) => ({
      ticket: readPositionField(position, ["ticket"]),
      symbol: readPositionField(position, ["symbol"]),
      volume: readPositionField(position, ["volume", "lot"]),
      open_price: readPositionField(position, ["price_open", "entry_price"]),
    })),
  );
}

async function answerOpenTradesQuestion(question: string): Promise<string | null> {
  if (!isOpenTradesQuestion(question)) return null;
  try {
    const positions = await readLiveOpenPositions();
    logOpenPositionsForChat(positions);
    if (!positions.length) return "There are 0 active open trades from the live MT5 position source.";
    const tickets = positions.map((position) => readPositionField(position, ["ticket"])).filter(Boolean);
    const symbols = positions.reduce<Record<string, number>>((counts, position) => {
      const symbol = readPositionField(position, ["symbol"]).toUpperCase() || "Unlabeled symbol";
      counts[symbol] = (counts[symbol] ?? 0) + 1;
      return counts;
    }, {});
    const symbolText = Object.entries(symbols).map(([symbol, count]) => `${symbol}: ${count}`).join(", ");
    return `There are ${positions.length} active open trades from the live MT5 position source. ${symbolText}.${tickets.length ? ` Tickets: ${tickets.join(", ")}.` : ""}`;
  } catch {
    return "Open trade data could not be read from the live MT5 position source right now.";
  }
}

async function answerLivePositionQuestion(question: string): Promise<string | null> {
  if (!isLivePositionQuestion(question)) return null;
  const positions = await readLiveOpenPositions();
  logOpenPositionsForChat(positions);
  const symbol = questionSymbol(question);
  const scoped = symbol ? positions.filter((position) => readPositionField(position, ["symbol"]).toUpperCase() === symbol) : positions;
  if (!scoped.length) return symbol ? `${symbol} has no active open positions in the live MT5 source.` : "There are no active open positions in the live MT5 source.";
  const normalized = question.toLowerCase();
  if (normalized.includes("what symbols")) {
    const symbols = [...new Set(scoped.map((position) => readPositionField(position, ["symbol"]).toUpperCase()).filter(Boolean))];
    return `Open position symbols: ${symbols.join(", ")}.`;
  }
  if (normalized.includes("tp") || normalized.includes("take profit") || normalized.includes("sl") || normalized.includes("stop loss")) {
    return scoped.map((position) => formatPositionLine(position, "levels")).join(" ");
  }
  if (normalized.includes("floating") || normalized.includes("p&l") || normalized.includes("pnl") || normalized.includes("profit")) {
    const total = scoped.reduce((sum, position) => sum + (readPositionNumber(position, ["floating_pnl", "profit"]) ?? 0), 0);
    return `${scoped.map((position) => formatPositionLine(position, "pnl")).join(" ")} Total floating P&L: ${formatMoney(total)}.`;
  }
  if (normalized.includes("entry")) return scoped.map((position) => formatPositionLine(position, "entry")).join(" ");
  if (normalized.includes("status")) return scoped.map((position) => formatPositionLine(position, "status")).join(" ");
  return scoped.map((position) => formatPositionLine(position, "monitoring")).join(" ");
}

async function answerClosedTradeQuestion(question: string): Promise<string | null> {
  if (!isClosedTradeQuestion(question)) return null;
  const summary = await readBackendRecord("/trade-journal/persistence/summary");
  if (!summary) return "Closed trade data could not be read from the trade journal right now.";
  const closed = numberValue(summary.closed_demo_trades) ?? 0;
  const wins = numberValue(summary.wins) ?? 0;
  const losses = numberValue(summary.losses) ?? 0;
  const netPnl = numberValue(summary.net_pnl) ?? 0;
  return `Closed validation trades recorded in the trade journal: ${closed}. Wins: ${wins}, losses: ${losses}, net P&L: ${formatMoney(netPnl)}.`;
}

async function answerProgressQuestion(question: string): Promise<string | null> {
  if (!isProgressQuestion(question)) return null;
  const status = await readBackendRecord("/auto-validation/status");
  const session = status && typeof status.session === "object" && status.session !== null ? (status.session as Record<string, unknown>) : null;
  if (!session) return "Validation progress could not be read from the auto-validation session right now.";
  const closed = numberValue(session.current_closed_trades) ?? numberValue(session.current_session_closed) ?? 0;
  const target = numberValue(session.target_closed_trades) ?? numberValue(session.target_validation_trades) ?? 30;
  const remaining = numberValue(session.remaining_closed_trades) ?? Math.max(0, target - closed);
  const open = numberValue(session.current_open_trades) ?? numberValue(session.current_session_open_trades) ?? 0;
  const mode = cleanText(session.status) || "not started";
  return `Validation progress: ${closed}/${target} closed trades completed, ${remaining} remaining, ${open} open, status ${mode}.`;
}

function executionAcceptedRecords(records: ReasonRecord[], symbol: string | null = null): ReasonRecord[] {
  return records.filter((record) => {
    const isExecution = record.source === "execution";
    const isAccepted = text(record.status).toUpperCase() === "ACCEPTED";
    const isOpen = record.order_opened === true;
    const symbolMatches = symbol ? record.symbol === symbol : true;
    return isExecution && isAccepted && isOpen && symbolMatches;
  });
}

function matchAcceptedRecordForPosition(records: ReasonRecord[], position: Record<string, unknown>): ReasonRecord | null {
  const ticket = readPositionField(position, ["ticket"]);
  if (ticket) return records.find((record) => record.ticket === ticket) ?? null;
  const symbol = readPositionField(position, ["symbol"]).toUpperCase();
  return records.find((record) => symbol && record.symbol === symbol && record.order_opened === true) ?? null;
}

async function answerOpenTicketQuestion(question: string): Promise<string | null> {
  if (!isOpenTicketQuestion(question)) return null;
  const positions = await readLiveOpenPositions();
  logOpenPositionsForChat(positions);
  if (positions.length) {
    const tickets = positions.map((position) => readPositionField(position, ["ticket"])).filter(Boolean);
    return tickets.length ? `Currently open ticket IDs: ${tickets.join(", ")}.` : POSITION_FIELD_MISSING;
  }
  const records = executionAcceptedRecords(await readReasonRecords());
  const tickets = records.map((record) => record.ticket).filter(Boolean);
  return tickets.length ? `Latest accepted ORDER_SENT ticket IDs: ${tickets.join(", ")}.` : "There are no currently open ticket IDs in the live MT5 position source.";
}

function reasonFallback(record: ReasonRecord): string {
  const symbol = record.symbol || "This signal";
  const status = cleanText(record.status).toUpperCase();
  if (status === "ACCEPTED") {
    const side = cleanText(record.side).toUpperCase();
    const ticket = cleanText(record.ticket);
    const sideText = side && !["TRADE", "POSITION"].includes(side) ? ` as a ${side} trade` : "";
    return `${symbol} was accepted and opened${sideText} because guarded demo validation passed, risk status was approved, and MT5 executed the order successfully.${ticket ? ` Ticket: ${ticket}.` : ""}`;
  }
  if (status === "REJECTED") {
    const blocker = cleanText(record.rejection_reason);
    return blocker ? `${symbol} was rejected because ${blocker.replace(/\.$/, "")}.` : `${symbol} was rejected because the latest validation checks did not pass. No trade was opened for this signal.`;
  }
  if (status === "WAITING") return `${symbol} is waiting for the next valid confirmation before making a trading decision.`;
  return `${symbol} needs attention because validation could not complete cleanly.`;
}

async function answerLatestAcceptanceQuestion(question: string): Promise<string | null> {
  if (!isLatestAcceptanceQuestion(question)) return null;
  const symbol = questionSymbol(question) ?? "EURUSD";
  const positions = await readLiveOpenPositions();
  const records = await readReasonRecords();
  const openPositions = positions.filter((position) => readPositionField(position, ["symbol"]).toUpperCase() === symbol);
  if (openPositions.length) {
    const openTickets = new Set(openPositions.map((position) => readPositionField(position, ["ticket"])).filter(Boolean));
    const accepted = executionAcceptedRecords(records, symbol).find((record) => record.ticket && openTickets.has(record.ticket)) ?? null;
    const fallbackPosition = [...openPositions].sort((left, right) => (numberValue(readPositionField(right, ["ticket"])) ?? 0) - (numberValue(readPositionField(left, ["ticket"])) ?? 0))[0];
    const ticket = accepted?.ticket || readPositionField(fallbackPosition, ["ticket"]);
    const side = accepted?.side || readPositionField(fallbackPosition, ["side", "type"]).toUpperCase();
    const reason = accepted?.reason || `${symbol} was accepted because the guarded demo validation passed and MT5 has an active open ${side || "trade"} position.`;
    return `${symbol} was accepted. ${reason}${ticket && !reason.includes(ticket) ? ` Ticket: ${ticket}.` : ""}`;
  }
  const latest = records.find((record) => !symbol || record.symbol === symbol) ?? null;
  if (!latest) return `I do not have a latest ${symbol} reason record yet.`;
  const latestStatus = cleanText(latest.status).toLowerCase() || "recorded";
  return `${symbol} was ${latestStatus}. ${cleanText(latest.reason) || reasonFallback(latest)}`;
}

async function answerOpenTradeReasonQuestion(question: string): Promise<string | null> {
  if (!isOpenTradeReasonQuestion(question)) return null;
  const symbol = questionSymbol(question);
  const positions = await readLiveOpenPositions();
  const scopedPositions = symbol ? positions.filter((position) => readPositionField(position, ["symbol"]).toUpperCase() === symbol) : positions;
  if (!scopedPositions.length) return symbol ? `${symbol} does not have an active open trade in the live MT5 position source.` : "There are no active open trades in the live MT5 position source.";
  const records = await readReasonRecords();
  const openTickets = new Set(scopedPositions.map((position) => readPositionField(position, ["ticket"])).filter(Boolean));
  const accepted = executionAcceptedRecords(records, symbol).find((record) => record.ticket && openTickets.has(record.ticket)) ?? null;
  if (accepted?.reason) return accepted.reason;
  const position = scopedPositions[0];
  const ticket = readPositionField(position, ["ticket"]);
  const positionSymbol = readPositionField(position, ["symbol"]).toUpperCase();
  const side = readPositionField(position, ["side", "type"]).toUpperCase();
  return `${positionSymbol} has an active open ${side || "trade"} position in MT5.${ticket ? ` Ticket: ${ticket}.` : ` ${POSITION_FIELD_MISSING}`}`;
}

function findDiagnostic(records: ReasonDiagnostic[], symbol: string | null, timeframe: string | null): { exact: ReasonDiagnostic | null; latestForSymbol: ReasonDiagnostic | null; latest: ReasonDiagnostic | null } {
  const latest = records[0] ?? null;
  const symbolMatches = symbol ? records.filter((record) => record.symbol === symbol) : records;
  const latestForSymbol = symbolMatches[0] ?? null;
  const exact = timeframe ? symbolMatches.find((record) => record.timeframe === timeframe) ?? null : latestForSymbol;
  return { exact, latest, latestForSymbol };
}

function diagnosticMissing(): string {
  return "Validator diagnostics have not been recorded for this decision.";
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
      return `I only have latest diagnostics for ${latestForSymbol.symbol} ${latestForSymbol.timeframe || "latest timeframe"}: ${latestForSymbol.candles_loaded} candles loaded, ${latestForSymbol.candles_required} required. ${timeframe} diagnostics have not been recorded for the latest decision.`;
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
    const source = record.data_source ? ` Data source: ${record.data_source}.` : " Data source has not been recorded.";
    return `${candleSummary(record)} loaded ${record.candles_loaded} candles. Minimum required is ${record.candles_required}.${source}`;
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
    const roundArchiveAnswer = await answerRoundArchiveQuestion(question);
    if (roundArchiveAnswer) {
      return NextResponse.json({ reply: roundArchiveAnswer });
    }
    const strategyRulesAnswer = answerStrategyRulesQuestion(question);
    if (strategyRulesAnswer) {
      return NextResponse.json({ reply: strategyRulesAnswer });
    }
    const validationHaltedAnswer = await answerValidationHaltedQuestion(question);
    if (validationHaltedAnswer) {
      return NextResponse.json({ reply: validationHaltedAnswer });
    }
    const tradeAutopsyAnswer = await answerTradeAutopsyQuestion(question);
    if (tradeAutopsyAnswer) {
      return NextResponse.json({ reply: tradeAutopsyAnswer });
    }
    const adaptiveLevelAnswer = await answerAdaptiveLevelQuestion(question);
    if (adaptiveLevelAnswer) {
      return NextResponse.json({ reply: adaptiveLevelAnswer });
    }
    const noTradeOpenedAnswer = await answerNoTradeOpenedQuestion(question);
    if (noTradeOpenedAnswer) {
      return NextResponse.json({ reply: noTradeOpenedAnswer });
    }
    const symbolScanAnswer = await answerSymbolScanQuestion(question);
    if (symbolScanAnswer) {
      return NextResponse.json({ reply: symbolScanAnswer });
    }
    const historyReadinessAnswer = await answerHistoryReadinessQuestion(question);
    if (historyReadinessAnswer) {
      return NextResponse.json({ reply: historyReadinessAnswer });
    }
    const openTicketAnswer = await answerOpenTicketQuestion(question);
    if (openTicketAnswer) {
      return NextResponse.json({ reply: openTicketAnswer });
    }
    const livePositionAnswer = await answerLivePositionQuestion(question);
    if (livePositionAnswer) {
      return NextResponse.json({ reply: livePositionAnswer });
    }
    const latestAcceptanceAnswer = await answerLatestAcceptanceQuestion(question);
    if (latestAcceptanceAnswer) {
      return NextResponse.json({ reply: latestAcceptanceAnswer });
    }
    const openTradeReasonAnswer = await answerOpenTradeReasonQuestion(question);
    if (openTradeReasonAnswer) {
      return NextResponse.json({ reply: openTradeReasonAnswer });
    }
    const openTradesAnswer = await answerOpenTradesQuestion(question);
    if (openTradesAnswer) {
      return NextResponse.json({ reply: openTradesAnswer });
    }
    const closedTradeAnswer = await answerClosedTradeQuestion(question);
    if (closedTradeAnswer) {
      return NextResponse.json({ reply: closedTradeAnswer });
    }
    const progressAnswer = await answerProgressQuestion(question);
    if (progressAnswer) {
      return NextResponse.json({ reply: progressAnswer });
    }
    const diagnosticAnswer = await answerDiagnosticQuestion(question);
    if (diagnosticAnswer) {
      return NextResponse.json({ reply: diagnosticAnswer });
    }
    const glossaryAnswer = answerStrategyGlossaryQuestion(question);
    if (glossaryAnswer) {
      return NextResponse.json({ reply: glossaryAnswer });
    }

    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: BUSY_MESSAGE }, { status: 503 });
    }

    const glossaryContext = Object.entries(STRATEGY_GLOSSARY).map(([term, definition]) => `${term}: ${definition}`).join("\n");
    const context = `${typeof body.context === "string" ? body.context.slice(0, 2000) : ""}\n\nStrategy glossary:\n${glossaryContext}`.slice(0, 6000);
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
