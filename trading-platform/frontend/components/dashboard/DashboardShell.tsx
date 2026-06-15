"use client";

import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ForexMapMarker } from "./ForexSessionsMap";

import {
  fetchClientOperatingDashboard,
  fetchClientMarketPrices,
  fetchClientSignals,
  approveExecutionModeSignal,
  emergencyStopAutoValidation,
  fetchAutoValidationStatus,
  previewClientDemoTrade,
  pauseAutoValidation,
  rejectExecutionModeSignal,
  resumeAutoValidation,
  runAutoValidationExitManagement,
  sendGuardedClientDemoTrade,
  setExecutionMode,
  startAutoValidation,
  stopAutoValidation,
  syncAutoValidationLifecycle,
  syncClientLifecycle,
  syncClientPositionsToJournal,
  type ApiRecord,
  type ClientOrderPayload,
} from "@/lib/clientOperatingDashboardApi";
import { readNumber, readText } from "@/lib/dashboard-formatters";
import { useLivePrice, type LivePricePoint, type LivePriceState } from "@/hooks/useLivePrice";

type DashboardData = {
  account: ApiRecord | null;
  eurusdTick: ApiRecord | null;
  xauusdTick: ApiRecord | null;
  marketScope: ApiRecord[];
  clientSignals: ApiRecord[];
  brokerAccounts: ApiRecord[];
  brokerCopyPlans: ApiRecord[];
  currentTerminalAccount: ApiRecord | null;
  vantageXauusdStatus: ApiRecord | null;
  vantageXauusdPreview: ApiRecord | null;
  openPositions: ApiRecord[];
  recentTrades: ApiRecord[];
  journalSummary: ApiRecord | null;
  outcomeSummary: ApiRecord | null;
  guardedStatus: ApiRecord | null;
  executionMode: ApiRecord | null;
  autoValidation: ApiRecord | null;
};

type ScopedSymbol = "EURUSD" | "XAUUSD" | "NIFTY50";
type HeldSignals = Partial<Record<ScopedSymbol, ApiRecord>>;
type BrokerView = "startrader" | "vantage" | "fxpro";
type PortalView = "portal" | "traderProfile" | "testEnvironment" | BrokerView | "chat";
type ToastState = { id: number; tone: "loading" | "success" | "error"; message: string };

const READY_SIGNAL_HOLD_SECONDS = 30;
const DASHBOARD_CACHE_KEY = "client-dashboard-last-successful-snapshot-v2";
const BALANCE_HISTORY_KEY = "algopilot_balance_history";
const INITIAL_ACCOUNT_BALANCE = 100000;
const CHAT_STORAGE_KEY = "algopilot_portal_chat_messages";
const REASON_MESSAGES_KEY = "algopilot_validation_reason_messages";
const ForexSessionsMap = dynamic(() => import("./ForexSessionsMap").then((mod) => mod.ForexSessionsMap), {
  loading: () => <div className="forex-leaflet-map-loading" />,
  ssr: false,
});
const ROUND_2_NOTE = "Round 2: EURUSD-only validation. No manual intervention. Client dashboard shows Round 2 only.";
const ROUND_2_START_PAYLOAD: ApiRecord = {
  confirm_fresh_start: true,
  session_started_by: "user_click",
  strategy_profile: "DEMO_COLLECTION",
  allowed_symbols: ["EURUSD"],
  target_validation_trades: 30,
  target_closed_trades: 30,
  round_label: "ROUND_2",
  session_note: ROUND_2_NOTE,
  client_dashboard_scope: "CURRENT_SESSION_ONLY",
};
const EURUSD_TEST_RESULTS_KEY = "algopilot_eurusd_test_results";
const FOREX_DISPLAY_TIME_ZONE = "Asia/Kolkata";
const FOREX_SESSIONS = {
  tokyo: {
    name: "Tokyo",
    flag: "JP",
    color: "#255EDC",
    openUTC: { h: 0, m: 0 },
    closeUTC: { h: 9, m: 0 },
  },
  sydney: {
    name: "Sydney",
    flag: "AU",
    color: "#1B4EB8",
    openUTC: { h: 22, m: 0 },
    closeUTC: { h: 7, m: 0 },
  },
  london: {
    name: "London",
    flag: "GB",
    color: "#3F7CFF",
    openUTC: { h: 8, m: 0 },
    closeUTC: { h: 17, m: 0 },
  },
  newyork: {
    name: "New York",
    flag: "US",
    color: "#173A8A",
    openUTC: { h: 13, m: 0 },
    closeUTC: { h: 22, m: 0 },
  },
} as const;

const emptyData: DashboardData = {
  account: null,
  eurusdTick: null,
  xauusdTick: null,
  marketScope: [],
  clientSignals: [],
  brokerAccounts: [],
  brokerCopyPlans: [],
  currentTerminalAccount: null,
  vantageXauusdStatus: null,
  vantageXauusdPreview: null,
  openPositions: [],
  recentTrades: [],
  journalSummary: null,
  outcomeSummary: null,
  guardedStatus: null,
  executionMode: null,
  autoValidation: null,
};

function readCachedDashboardData(): DashboardData {
  if (typeof window === "undefined") return emptyData;
  try {
    const raw = window.localStorage.getItem(DASHBOARD_CACHE_KEY);
    if (!raw) return emptyData;
    const parsed = JSON.parse(raw) as Partial<DashboardData>;
    return {
      ...emptyData,
      ...parsed,
      marketScope: Array.isArray(parsed.marketScope) ? parsed.marketScope : [],
      clientSignals: Array.isArray(parsed.clientSignals) ? parsed.clientSignals : [],
      brokerAccounts: Array.isArray(parsed.brokerAccounts) ? parsed.brokerAccounts : [],
      brokerCopyPlans: Array.isArray(parsed.brokerCopyPlans) ? parsed.brokerCopyPlans : [],
      openPositions: Array.isArray(parsed.openPositions) ? parsed.openPositions : [],
      recentTrades: Array.isArray(parsed.recentTrades) ? parsed.recentTrades : [],
    };
  } catch {
    return emptyData;
  }
}

function writeCachedDashboardData(data: DashboardData): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(data));
  } catch {
    // Storage can be unavailable in private or restricted browser contexts.
  }
}

function hasDashboardSnapshot(data: DashboardData): boolean {
  return Boolean(
    data.account ||
      data.autoValidation ||
      data.journalSummary ||
      data.openPositions.length ||
      data.recentTrades.length ||
      data.clientSignals.length,
  );
}

function asRecord(value: unknown): ApiRecord | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as ApiRecord) : null;
}

function recordsFrom(value: unknown, key: string): ApiRecord[] {
  const record = asRecord(value);
  const items = record?.[key];
  return Array.isArray(items) ? (items.filter((item) => asRecord(item)) as ApiRecord[]) : [];
}

function money(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Unavailable";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function percent(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "Unavailable";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}%`;
}

function numeric(record: ApiRecord | null | undefined, keys: string[], fallback = Number.NaN): number {
  for (const key of keys) {
    const value = record?.[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return fallback;
}

function marketNumber(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "Unavailable";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function marketPriceText(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "-";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function signed(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

function pointsToCoordinates(points: LivePricePoint[], width: number, height: number, padding: number): { x: number; y: number }[] {
  const recent = points.slice(-80).filter((point) => Number.isFinite(point.value));
  if (recent.length < 2) return [];
  const values = recent.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return recent.map((point, index) => ({
    x: recent.length === 1 ? 0 : (index / (recent.length - 1)) * width,
    y: padding + ((max - point.value) / range) * (height - padding * 2),
  }));
}

function pointsToPath(points: LivePricePoint[], width: number, height: number, padding: number): string {
  return pointsToCoordinates(points, width, height, padding)
    .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(1)} ${point.y.toFixed(1)}`)
    .join(" ");
}

function getSessionStatus(session: (typeof FOREX_SESSIONS)[keyof typeof FOREX_SESSIONS], now = new Date(), localTimes = "Loading local time"): {
  closeAt: Date;
  color: string;
  countdown: string;
  countdownMinutes: number;
  flag: string;
  isOpen: boolean;
  istTimes: string;
  localTimes: string;
  name: string;
  openAt: Date;
  stateLabel: string;
  statusText: string;
} {
  const currentWindow = findCurrentSessionWindow(session, now);
  if (currentWindow) {
    const minsLeft = minutesBetween(now, currentWindow.closeAt);
    return {
      closeAt: currentWindow.closeAt,
      color: session.color,
      countdown: `Closes in ${formatMins(minsLeft)}`,
      countdownMinutes: minsLeft,
      flag: session.flag,
      isOpen: true,
      istTimes: localTimes,
      localTimes,
      name: session.name,
      openAt: currentWindow.openAt,
      stateLabel: "Closes in",
      statusText: "Open",
    };
  }
  const nextWindow = findNextSessionWindow(session, now);
  const minsToOpen = minutesBetween(now, nextWindow.openAt);
  return {
    closeAt: nextWindow.closeAt,
    color: session.color,
    countdown: `Opens in ${formatMins(minsToOpen)}`,
    countdownMinutes: minsToOpen,
    flag: session.flag,
    isOpen: false,
    istTimes: localTimes,
    localTimes,
    name: session.name,
    openAt: nextWindow.openAt,
    stateLabel: "Opens in",
    statusText: "Closed",
  };
}

function isForexGloballyOpen(now = new Date()): boolean {
  const day = now.getUTCDay();
  const totalMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
  if (day === 6) return false;
  if (day === 0 && totalMinutes < 22 * 60) return false;
  if (day === 5 && totalMinutes >= 22 * 60) return false;
  return true;
}

function buildSessionWindow(session: (typeof FOREX_SESSIONS)[keyof typeof FOREX_SESSIONS], now: Date, dayOffset: number) {
  const openAt = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + dayOffset, session.openUTC.h, session.openUTC.m, 0, 0));
  const closeAt = new Date(Date.UTC(openAt.getUTCFullYear(), openAt.getUTCMonth(), openAt.getUTCDate(), session.closeUTC.h, session.closeUTC.m, 0, 0));
  if (closeAt.getTime() <= openAt.getTime()) closeAt.setUTCDate(closeAt.getUTCDate() + 1);
  return { openAt, closeAt };
}

function findCurrentSessionWindow(session: (typeof FOREX_SESSIONS)[keyof typeof FOREX_SESSIONS], now: Date) {
  if (!isForexGloballyOpen(now)) return null;
  for (const dayOffset of [-1, 0]) {
    const window = buildSessionWindow(session, now, dayOffset);
    if (now.getTime() >= window.openAt.getTime() && now.getTime() < window.closeAt.getTime()) return window;
  }
  return null;
}

function findNextSessionWindow(session: (typeof FOREX_SESSIONS)[keyof typeof FOREX_SESSIONS], now: Date) {
  for (let dayOffset = 0; dayOffset <= 7; dayOffset += 1) {
    const window = buildSessionWindow(session, now, dayOffset);
    if (window.openAt.getTime() > now.getTime() && isForexGloballyOpen(window.openAt)) return window;
  }
  return buildSessionWindow(session, now, 1);
}

function minutesBetween(from: Date, to: Date): number {
  return Math.max(0, Math.ceil((to.getTime() - from.getTime()) / 60000));
}

function formatMins(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function sessionTimesInLocalTZ(session: (typeof FOREX_SESSIONS)[keyof typeof FOREX_SESSIONS], timeZone: string): string {
  const openDate = new Date();
  openDate.setUTCHours(session.openUTC.h, session.openUTC.m, 0, 0);
  const closeDate = new Date();
  closeDate.setUTCHours(session.closeUTC.h, session.closeUTC.m, 0, 0);
  const fmt = (date: Date) => date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true, timeZone });
  return `${fmt(openDate)} - ${fmt(closeDate)} local`;
}

function formatInTimeZone(date: Date, timeZone: string): string {
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
    timeZone,
  });
}

function isMarketOpen(tick: ApiRecord | null): boolean {
  return readText(tick, ["market_status", "status"], "").toUpperCase() === "MARKET_READY" || (readText(tick, ["status"], "").toUpperCase() === "OK" && readText(tick, ["freshness"], "").toUpperCase() === "READY");
}

function marketLabel(tick: ApiRecord | null): string {
  const status = readText(tick, ["market_status", "status"], "").toUpperCase();
  if (status === "SYMBOL_NOT_AVAILABLE" || status === "SYMBOL_UNAVAILABLE") return "Symbol Not Available";
  if (status === "STALE_TICK") return "Stale Tick";
  if (status === "SYMBOL_TICK_UNAVAILABLE") return "Tick Unavailable";
  if (status === "FEED_OFFLINE") return "Feed Offline";
  if (status === "MARKET_CLOSED") return "Market Closed";
  return isMarketOpen(tick) ? "Market Ready" : "Tick Pending";
}

function xauusdReadinessLabel(tick: ApiRecord | null, signal: ApiRecord | null): string {
  const status = readText(tick, ["market_status", "status"], "").toUpperCase();
  if (status === "SYMBOL_NOT_AVAILABLE" || status === "SYMBOL_UNAVAILABLE") return "Symbol Not Available";
  if (status === "STALE_TICK") return "Stale Tick";
  if (status === "SYMBOL_TICK_UNAVAILABLE") return "Tick Unavailable";
  if (status === "FEED_OFFLINE") return "Feed Offline";
  if (status === "MARKET_CLOSED") return "Market Closed";
  if (!isMarketOpen(tick)) return "Tick Pending";
  const action = readText(signal, ["signal"], "WAIT").toUpperCase();
  if (action === "BUY" || action === "SELL") return "Ready for Future Demo Test";
  return "Waiting for Strategy Setup";
}

function statusTone(status: string): string {
  const text = status.toUpperCase();
  if (text.includes("OPEN") || text.includes("CONNECTED") || text.includes("READY") || text.includes("DEMO")) return "text-emerald-300 border-emerald-400/30 bg-emerald-400/10";
  if (text.includes("STALE") || text.includes("PENDING") || text.includes("UNAVAILABLE")) return "text-amber-200 border-amber-400/30 bg-amber-400/10";
  if (text.includes("CLOSED") || text.includes("OFFLINE") || text.includes("BLOCK") || text.includes("ERROR")) return "text-rose-300 border-rose-400/30 bg-rose-400/10";
  return "text-sky-200 border-sky-400/30 bg-sky-400/10";
}

function pnlClass(value: number): string {
  if (value > 0) return "text-emerald-300";
  if (value < 0) return "text-rose-300";
  return "text-slate-100";
}

function formatDuration(value: unknown): string {
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number) || number <= 0) return "Unavailable";
  if (number < 60) return `${number.toFixed(0)}m`;
  return `${(number / 60).toFixed(1)}h`;
}

function formatTradeTime(value: unknown): string {
  if (!value) return "Unavailable";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "Unavailable";
  const datePart = date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
  const timePart = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: true, timeZone: "UTC" });
  return `${datePart}\n${timePart} UTC`;
}

function sessionOpen(session: "Sydney" | "Tokyo" | "London" | "New York", now = new Date()): boolean {
  const hour = now.getUTCHours();
  if (session === "Sydney") return hour >= 21 || hour < 6;
  if (session === "Tokyo") return hour >= 0 && hour < 9;
  if (session === "London") return hour >= 7 && hour < 16;
  return hour >= 12 && hour < 21;
}

function todayPnl(closedTrades: ApiRecord[]): number {
  const today = new Date().toDateString();
  return closedTrades.reduce((sum, trade) => {
    const closedAt = readText(trade, ["closed_at", "close_time"], "");
    if (!closedAt || new Date(closedAt).toDateString() !== today) return sum;
    return sum + readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl"], 0);
  }, 0);
}

function floatingPnl(positions: ApiRecord[]): number {
  return positions.reduce((sum, position) => sum + readNumber(position, ["floating_pnl", "profit"], 0), 0);
}

function currentValidationSessionId(autoValidation: ApiRecord | null): string {
  const session = asRecord(autoValidation?.session);
  return readText(session, ["session_id", "id", "validation_session_id"], "");
}

function recordBelongsToSession(record: ApiRecord, sessionId: string): boolean {
  if (!sessionId) return false;
  return readText(record, ["validation_session_id", "session_id", "auto_validation_session_id"], "") === sessionId;
}

function sessionScopedRecords(records: ApiRecord[], sessionId: string): ApiRecord[] {
  return sessionId ? records.filter((record) => recordBelongsToSession(record, sessionId)) : [];
}

function rrFrom(entry: number, action: "BUY" | "SELL", stopLoss: number, takeProfit: number): number | null {
  if (entry <= 0 || stopLoss <= 0 || takeProfit <= 0) return null;
  const risk = action === "BUY" ? entry - stopLoss : stopLoss - entry;
  const reward = action === "BUY" ? takeProfit - entry : entry - takeProfit;
  if (risk <= 0 || reward <= 0) return null;
  return Number((reward / risk).toFixed(2));
}

function cleanBlockers(blockers: unknown): string[] {
  if (!Array.isArray(blockers)) return [];
  return blockers.map((item) => {
    const record = asRecord(item);
    const value = record ? readText(record, ["label", "reason", "code", "message"], JSON.stringify(record)) : String(item);
    return value.replaceAll("_", " ").toLowerCase();
  }).slice(0, 6);
}

function blockersFromPreview(preview: ApiRecord | null): string[] {
  if (!preview) return [];
  const blockedReasons = Array.isArray(preview.blocked_reasons) ? preview.blocked_reasons : preview.blockers;
  return cleanBlockers(blockedReasons);
}

function readySignal(signal: ApiRecord | null): boolean {
  return readText(signal, ["execution_status"], "") === "READY_FOR_PREVIEW" && readText(signal, ["risk_status"], "") === "APPROVED";
}

function watchlistSignal(signal: ApiRecord | null): boolean {
  return readText(signal, ["status_level"], "").toUpperCase() === "WATCHLIST";
}

function signalHoldRemaining(signal: ApiRecord | null, nowMs: number): number {
  const expiresAt = readNumber(signal, ["hold_expires_at_ms"], Number.NaN);
  if (!Number.isFinite(expiresAt)) return 0;
  return Math.max(0, Math.ceil((expiresAt - nowMs) / 1000));
}

function staleSignalBlockers(blockers: string[]): boolean {
  return blockers.some((blocker) => blocker.includes("signal expired") || blocker.includes("signal no longer") || blocker.includes("signal hash changed") || blocker.includes("signal timestamp"));
}

function lastCandleTimestamp(signal: ApiRecord | null): string {
  const source = asRecord(signal?.candle_source);
  const timeframes = asRecord(source?.timeframes);
  const m15 = asRecord(timeframes?.M15);
  const h1 = asRecord(timeframes?.H1);
  const h4 = asRecord(timeframes?.H4);
  return readText(m15, ["last_candle_timestamp"], readText(h1, ["last_candle_timestamp"], readText(h4, ["last_candle_timestamp"], "")));
}

function tradeStatusMessages(marketOpen: boolean, openTradeExists: boolean, signal: ApiRecord | null, formValid: boolean): { ok: boolean; text: string }[] {
  const symbol = readText(signal, ["symbol"], "");
  if (!marketOpen) return [{ ok: false, text: symbol === "XAUUSD" ? "XAUUSD Future Demo Test Only" : "Market Closed" }];
  const messages: { ok: boolean; text: string }[] = [{ ok: true, text: "Market Ready" }];
  if (!signal) messages.push({ ok: false, text: "Select AI Signal" });
  if (readText(signal, ["signal"], "WAIT").toUpperCase() === "WAIT") messages.push({ ok: false, text: "No Confirmed Signal" });
  if (!numeric(signal, ["stop_loss"])) messages.push({ ok: false, text: "Stop Loss Required" });
  if (!numeric(signal, ["take_profit"])) messages.push({ ok: false, text: "Take Profit Required" });
  if (openTradeExists) messages.push({ ok: false, text: "Existing Demo Position Active" });
  if (signal && !["EURUSD", "XAUUSD"].includes(readText(signal, ["symbol"], ""))) messages.push({ ok: false, text: "Vantage EURUSD/XAUUSD Demo Only" });
  if (signal && !formValid) messages.push({ ok: false, text: "Check SL / TP Placement" });
  if (messages.length === 1) messages.push({ ok: true, text: "Trade Ready" });
  return messages;
}

export function DashboardShell(_: {
  executiveDashboardSection?: React.ReactNode;
  analyticsSection?: React.ReactNode;
  accountAnalyticsSection?: React.ReactNode;
  platformFoundationSection?: React.ReactNode;
  strategyIntelligenceSection?: React.ReactNode;
  tradeJournalSection?: React.ReactNode;
  reportsSection?: React.ReactNode;
}) {
  const [data, setData] = useState<DashboardData>(emptyData);
  const [errors, setErrors] = useState<string[]>([]);
  const [panelErrors, setPanelErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<ScopedSymbol>("EURUSD");
  const [preview, setPreview] = useState<ApiRecord | null>(null);
  const [previewSignal, setPreviewSignal] = useState<ApiRecord | null>(null);
  const [sendResult, setSendResult] = useState<ApiRecord | null>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [positionsSyncState, setPositionsSyncState] = useState<{ loading: boolean; message: string; error: string }>({ loading: false, message: "", error: "" });
  const [lifecycleSyncState, setLifecycleSyncState] = useState<{ loading: boolean; message: string; error: string }>({ loading: false, message: "", error: "" });
  const [exitManagementState, setExitManagementState] = useState<{ loading: boolean; message: string; error: string }>({ loading: false, message: "", error: "" });
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [workingAction, setWorkingAction] = useState<string | null>(null);
  const [heldReadySignals, setHeldReadySignals] = useState<HeldSignals>({});
  const [nowMs, setNowMs] = useState(0);
  const [activePortalView, setActivePortalView] = useState<PortalView>("portal");
  const [toast, setToast] = useState<ToastState | null>(null);
  const [lastSuccessfulSync, setLastSuccessfulSync] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState(true);
  const [clientReady, setClientReady] = useState(false);
  const [calculatorResetToken, setCalculatorResetToken] = useState(0);
  const requestInFlight = useRef(false);
  const priceRequestInFlight = useRef(false);
  const signalRequestInFlight = useRef(false);
  const autoValidationRequestInFlight = useRef(false);

  const showToast = useCallback((tone: ToastState["tone"], message: string) => {
    setToast({ id: Date.now(), tone, message });
  }, []);

  useEffect(() => {
    if (!toast || toast.tone === "loading") return;
    const timeout = window.setTimeout(() => setToast((current) => (current?.id === toast.id ? null : current)), 4000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    const cached = readCachedDashboardData();
    if (hasDashboardSnapshot(cached)) {
      setData(cached);
    }
    setNowMs(Date.now());
    setClientReady(true);
  }, []);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return true;
    requestInFlight.current = true;
    setLoading(true);
    try {
      const result = await fetchClientOperatingDashboard();
      const payload = result.data;
      const fullSuccess = result.errors.length === 0;
      setBackendConnected(true);
      setData((current) => {
        const brokerAccounts = "brokerAccounts" in payload ? asRecord(payload.brokerAccounts) : null;
        const next = {
          account: "account" in payload ? recordOrPrevious(payload.account, current.account) : current.account,
          eurusdTick: "eurusdTick" in payload ? recordOrPrevious(payload.eurusdTick, current.eurusdTick) : current.eurusdTick,
          xauusdTick: "xauusdTick" in payload ? recordOrPrevious(payload.xauusdTick, current.xauusdTick) : current.xauusdTick,
          marketScope: "marketScope" in payload ? arrayRecordsOrPrevious(payload.marketScope, current.marketScope, fullSuccess) : current.marketScope,
          clientSignals: "clientSignals" in payload ? recordsOrPrevious(payload.clientSignals, "signals", current.clientSignals, fullSuccess) : current.clientSignals,
          brokerAccounts: "brokerAccounts" in payload ? recordsOrPrevious(payload.brokerAccounts, "accounts", current.brokerAccounts, fullSuccess) : current.brokerAccounts,
          brokerCopyPlans: "brokerCopyReadiness" in payload ? recordsOrPrevious(payload.brokerCopyReadiness, "plans", current.brokerCopyPlans, fullSuccess) : current.brokerCopyPlans,
          currentTerminalAccount: brokerAccounts ? recordOrPrevious(brokerAccounts.current_terminal_account, current.currentTerminalAccount) : current.currentTerminalAccount,
          vantageXauusdStatus: "vantageXauusdStatus" in payload ? recordOrPrevious(payload.vantageXauusdStatus, current.vantageXauusdStatus) : current.vantageXauusdStatus,
          vantageXauusdPreview: "vantageXauusdPreview" in payload ? recordOrPrevious(payload.vantageXauusdPreview, current.vantageXauusdPreview) : current.vantageXauusdPreview,
          openPositions: "openPositions" in payload ? recordsOrPrevious(payload.openPositions, "positions", current.openPositions, fullSuccess) : current.openPositions,
          recentTrades: "recentTrades" in payload ? arrayRecordsOrPrevious(payload.recentTrades, current.recentTrades, fullSuccess) : current.recentTrades,
          journalSummary: "journalSummary" in payload ? recordOrPrevious(payload.journalSummary, current.journalSummary) : current.journalSummary,
          outcomeSummary: "outcomeSummary" in payload ? recordOrPrevious(payload.outcomeSummary, current.outcomeSummary) : current.outcomeSummary,
          guardedStatus: "guardedStatus" in payload ? recordOrPrevious(payload.guardedStatus, current.guardedStatus) : current.guardedStatus,
          executionMode: "executionMode" in payload ? recordOrPrevious(payload.executionMode, current.executionMode) : current.executionMode,
          autoValidation: "autoValidation" in payload ? recordOrPrevious(payload.autoValidation, current.autoValidation) : current.autoValidation,
        };
        writeCachedDashboardData(next);
        return next;
      });
      setErrors(result.errors);
      setPanelErrors((current) => ({ ...current, dashboard: result.errors[0] ?? "" }));
      const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      setLastUpdated(timestamp);
      setLastSuccessfulSync(timestamp);
      return true;
    } catch (error) {
      setBackendConnected(false);
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
      setPanelErrors((current) => ({ ...current, dashboard: error instanceof Error ? error.message : "Backend unavailable" }));
      return false;
    } finally {
      setLoading(false);
      requestInFlight.current = false;
    }
  }, []);

  const refreshPrices = useCallback(async () => {
    if (priceRequestInFlight.current) return;
    priceRequestInFlight.current = true;
    try {
      const prices = await fetchClientMarketPrices();
      if (prices.ok) {
        setData((current) => {
          const next = {
            ...current,
            eurusdTick: asRecord(prices.eurusdTick),
            xauusdTick: asRecord(prices.xauusdTick),
          };
          writeCachedDashboardData(next);
          return next;
        });
      }
      setErrors(prices.errors);
      setPanelErrors((current) => ({ ...current, prices: prices.errors[0] ?? "" }));
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
      setPanelErrors((current) => ({ ...current, prices: error instanceof Error ? error.message : "Backend unavailable" }));
    } finally {
      priceRequestInFlight.current = false;
    }
  }, []);

  const refreshSignals = useCallback(async () => {
    if (signalRequestInFlight.current) return;
    signalRequestInFlight.current = true;
    try {
      const signals = await fetchClientSignals();
      if (signals.ok) {
        setData((current) => {
          const next = {
            ...current,
            clientSignals: recordsOrPrevious(signals.signals, "signals", current.clientSignals, true),
          };
          writeCachedDashboardData(next);
          return next;
        });
      }
      setErrors(signals.errors);
      setPanelErrors((current) => ({ ...current, signals: signals.errors[0] ?? "" }));
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
      setPanelErrors((current) => ({ ...current, signals: error instanceof Error ? error.message : "Backend unavailable" }));
    } finally {
      signalRequestInFlight.current = false;
    }
  }, []);

  const refreshAutoValidation = useCallback(async () => {
    if (autoValidationRequestInFlight.current) return;
    autoValidationRequestInFlight.current = true;
    try {
      const result = await fetchAutoValidationStatus();
      if (result.ok) {
        setData((current) => {
          const next = { ...current, autoValidation: recordOrPrevious(result.status, current.autoValidation) };
          writeCachedDashboardData(next);
          return next;
        });
      }
      if (result.errors.length > 0) {
        setErrors(result.errors);
      }
      setPanelErrors((current) => ({ ...current, autoValidation: result.errors[0] ?? "" }));
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
      setPanelErrors((current) => ({ ...current, autoValidation: error instanceof Error ? error.message : "Backend unavailable" }));
    } finally {
      autoValidationRequestInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const interval = window.setInterval(() => void refresh(), 10000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    const interval = window.setInterval(() => void refreshPrices(), 1000);
    return () => window.clearInterval(interval);
  }, [refreshPrices]);

  useEffect(() => {
    const interval = window.setInterval(() => void refreshSignals(), 5000);
    return () => window.clearInterval(interval);
  }, [refreshSignals]);

  useEffect(() => {
    const interval = window.setInterval(() => void refreshAutoValidation(), 3000);
    return () => window.clearInterval(interval);
  }, [refreshAutoValidation]);

  useEffect(() => {
    if (!data.clientSignals.some((signal) => watchlistSignal(signal))) return;
    const interval = window.setInterval(() => void refreshSignals(), 2000);
    return () => window.clearInterval(interval);
  }, [data.clientSignals, refreshSignals]);

  useEffect(() => {
    const interval = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    setHeldReadySignals((current) => {
      const next: HeldSignals = { ...current };
      const now = Date.now();
      for (const symbol of ["EURUSD", "XAUUSD"] as const) {
        const live = data.clientSignals.find((signal) => readText(signal, ["symbol"], "") === symbol) ?? null;
        const existing = next[symbol] ?? null;
        const existingHash = readText(existing, ["signal_hash"], "");
        const liveHash = readText(live, ["signal_hash"], "");
        const existingRemaining = signalHoldRemaining(existing, now);
        if (readySignal(live) && (existingRemaining <= 0 || existingHash !== liveHash)) {
          next[symbol] = {
            ...live,
            hold_started_at_ms: now,
            hold_expires_at_ms: now + READY_SIGNAL_HOLD_SECONDS * 1000,
          };
        } else if (existing && existingRemaining <= 0) {
          delete next[symbol];
        }
      }
      return next;
    });
  }, [data.clientSignals]);

  useEffect(() => {
    setPreview(null);
    setPreviewSignal(null);
    setSendResult(null);
    setTradeError(null);
  }, [selectedSymbol]);

  const displayedSignals = useMemo(() => {
    return data.clientSignals.map((signal) => {
      const symbol = readText(signal, ["symbol"], "") as ScopedSymbol;
      const held = heldReadySignals[symbol] ?? null;
      return held && signalHoldRemaining(held, nowMs) > 0 ? held : signal;
    });
  }, [data.clientSignals, heldReadySignals, nowMs]);
  const closedTrades = useMemo(() => data.recentTrades.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED"), [data.recentTrades]);
  const activeSessionId = currentValidationSessionId(data.autoValidation);
  const clientClosedTrades = useMemo(() => sessionScopedRecords(closedTrades, activeSessionId), [closedTrades, activeSessionId]);
  const clientOpenPositions = useMemo(() => sessionScopedRecords(data.openPositions, activeSessionId), [data.openPositions, activeSessionId]);
  const marketOpen = isMarketOpen(data.eurusdTick);
  const openTradeExists = data.openPositions.length > 0 || readNumber(data.journalSummary, ["open_demo_trades"], 0) > 0;
  const approvalReady = preview?.approved_for_future_demo_order === true || readText(preview, ["readiness_decision"], "") === "READY_FOR_GUARDED_DEMO_TEST";
  const selectedSignal = displayedSignals.find((signal) => readText(signal, ["symbol"], "") === selectedSymbol) ?? null;
  const signalAction = readText(selectedSignal, ["signal"], "WAIT").toUpperCase();
  const signalEntry = readNumber(selectedSignal, ["entry"], Number.NaN);
  const stopLoss = readNumber(selectedSignal, ["stop_loss"], Number.NaN);
  const takeProfit = readNumber(selectedSignal, ["take_profit"], Number.NaN);
  const rr = readNumber(selectedSignal, ["risk_reward"], Number.NaN);
  const signalReadyForPreview = readText(selectedSignal, ["execution_status"], "") === "READY_FOR_PREVIEW";
  const selectedMarketOpen = selectedSymbol === "EURUSD" ? marketOpen : isMarketOpen(data.xauusdTick);
  const signalExecutable = (selectedSymbol === "EURUSD" || selectedSymbol === "XAUUSD") && (signalAction === "BUY" || signalAction === "SELL");
  const formValid = signalReadyForPreview && signalExecutable && Number.isFinite(signalEntry) && signalEntry > 0 && Number.isFinite(stopLoss) && stopLoss > 0 && Number.isFinite(takeProfit) && takeProfit > 0 && Number.isFinite(rr) && rr >= 1.5;
  const canPreview = selectedMarketOpen && !openTradeExists && formValid && !workingAction;
  const previewBlockers = blockersFromPreview(preview);
  const previewSource = asRecord(previewSignal?.candle_source);
  const canSend =
    approvalReady &&
    readySignal(previewSignal) &&
    signalHoldRemaining(previewSignal, nowMs) > 0 &&
    readText(previewSource, ["broker_source", "source"], readText(preview, ["broker_source", "source"], "")) === "VANTAGE_DEMO" &&
    readText(previewSource, ["account_type"], readText(preview, ["account_type"], "")) === "DEMO" &&
    previewBlockers.length === 0 &&
    readText(preview, ["duplicate_protection_status"], "BLOCKED") === "PASSED" &&
    !workingAction;
  const totalTrades = readNumber(data.journalSummary, ["total_trades"], 0);
  const closedCount = readNumber(data.journalSummary, ["closed_demo_trades"], 0);
  const winRate = readNumber(data.journalSummary, ["win_rate"], 0);
  const netPnl = readNumber(data.journalSummary, ["net_pnl"], 0);
  const avgRr = readNumber(data.journalSummary, ["avg_rr"], readNumber(data.outcomeSummary, ["avg_rr"], 0));
  const bestTrade = asRecord(data.outcomeSummary?.best_trade);
  const worstTrade = asRecord(data.outcomeSummary?.worst_trade);
  const openFloatingPnl = floatingPnl(data.openPositions);
  const lastTrade = closedTrades[0] ?? null;
  const tradeStatus = tradeStatusMessages(selectedMarketOpen, openTradeExists, selectedSignal, formValid);
  const eurusdLive = useLivePrice("EURUSD");
  const xauusdLive = useLivePrice("XAUUSD");

  const orderPayload = (signal: ApiRecord | null = selectedSignal): ClientOrderPayload => ({
    symbol: readText(signal, ["symbol"], selectedSymbol) === "XAUUSD" ? "XAUUSD" : "EURUSD",
    action: readText(signal, ["signal"], signalAction).toUpperCase() as "BUY" | "SELL",
    lot: 0.01,
    entry_price: readNumber(signal, ["entry"], signalEntry),
    stop_loss: readNumber(signal, ["stop_loss"], stopLoss),
    take_profit: readNumber(signal, ["take_profit"], takeProfit),
    risk_reward_ratio: readNumber(signal, ["risk_reward"], rr),
    signal_confidence: readNumber(signal, ["confidence"], Number.NaN),
    signal_hash: readText(signal, ["signal_hash"], ""),
    signal_timestamp: readText(signal, ["timestamp"], ""),
    setup_reason: readText(signal, ["setup_reason", "reason"], ""),
    strategy_metadata: {
      market_structure_state: asRecord(signal?.market_structure_state) ?? {},
      strategy_components: asRecord(signal?.strategy_components) ?? {},
      quality_score: asRecord(signal?.quality_score) ?? {},
      approval_audit: asRecord(signal?.approval_audit) ?? {},
      candle_source: asRecord(signal?.candle_source) ?? {},
    },
  });

  function canPreviewSignal(signal: ApiRecord | null): boolean {
    const symbol = readText(signal, ["symbol"], "");
    const tick = symbol === "XAUUSD" ? data.xauusdTick : data.eurusdTick;
    const entry = readNumber(signal, ["entry"], Number.NaN);
    const sl = readNumber(signal, ["stop_loss"], Number.NaN);
    const tp = readNumber(signal, ["take_profit"], Number.NaN);
    const signalRr = readNumber(signal, ["risk_reward"], Number.NaN);
    return (
      ["EURUSD", "XAUUSD"].includes(symbol) &&
      readySignal(signal) &&
      signalHoldRemaining(signal, nowMs) > 0 &&
      Number.isFinite(entry) &&
      entry > 0 &&
      Number.isFinite(sl) &&
      sl > 0 &&
      Number.isFinite(tp) &&
      tp > 0 &&
      Number.isFinite(signalRr) &&
      signalRr >= 1.5 &&
      isMarketOpen(tick) &&
      !openTradeExists &&
      !workingAction
    );
  }

  async function handlePreview(signal: ApiRecord | null = selectedSignal) {
    setTradeError(null);
    setSendResult(null);
    if (!canPreviewSignal(signal)) {
      setTradeError("Preview is blocked until an AI signal is ready, the market is open, SL/TP are valid, and no demo position is open.");
      return;
    }
    setSelectedSymbol(readText(signal, ["symbol"], selectedSymbol) as ScopedSymbol);
    setWorkingAction("preview");
    try {
      const result = await previewClientDemoTrade(orderPayload(signal));
      setPreview(result);
      setPreviewSignal(signal);
      const blockers = blockersFromPreview(result);
      if (staleSignalBlockers(blockers)) {
        setTradeError("Signal expired or changed. Refreshed the signal before preview.");
        await refreshSignals();
      }
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : "Preview failed.");
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleConfirmSend() {
    setTradeError(null);
    setWorkingAction("send");
    try {
      const result = await sendGuardedClientDemoTrade(orderPayload(previewSignal ?? selectedSignal));
      setSendResult(result);
      setConfirmOpen(false);
      if (staleSignalBlockers(blockersFromPreview(result))) {
        setTradeError("Signal expired or changed before confirm. Refreshed the signal.");
        await refreshSignals();
        return;
      }
      if (readText(result, ["status"], "") === "DEMO_ORDER_SENT") {
        await syncClientPositionsToJournal();
        await syncClientLifecycle();
      }
      await refresh();
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : "Demo order send failed.");
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleSync(action: "positions" | "lifecycle" | "exit-management") {
    if (workingAction !== null) return;
    setWorkingAction(action);
    setTradeError(null);
    const setState = action === "positions" ? setPositionsSyncState : action === "lifecycle" ? setLifecycleSyncState : setExitManagementState;
    setState({ loading: true, message: "", error: "" });
    showToast("loading", action === "lifecycle" ? "Syncing lifecycle..." : action === "exit-management" ? "Running exit management..." : "Refreshing positions...");
    try {
      if (action === "positions") {
        await syncClientPositionsToJournal();
        setState({ loading: false, message: "Positions refreshed.", error: "" });
        showToast("success", "Positions refreshed successfully");
      } else if (action === "lifecycle") {
        const result = await syncAutoValidationLifecycle();
        setData((current) => {
          const next = {
            ...current,
            autoValidation: {
              ...(current.autoValidation ?? {}),
              session: asRecord(result.session) ?? asRecord(current.autoValidation?.session),
              lifecycle_sync: asRecord(result.lifecycle_sync),
              open_position_sync: asRecord(result.open_position_sync),
            },
          };
          writeCachedDashboardData(next);
          return next;
        });
        setState({ loading: false, message: readText(result, ["message"], "AUTO lifecycle synchronized."), error: "" });
        showToast("success", "Lifecycle sync complete");
      } else {
        const result = await runAutoValidationExitManagement();
        setData((current) => {
          const next = {
            ...current,
            autoValidation: {
              ...(current.autoValidation ?? {}),
              session: asRecord(result.session) ?? asRecord(current.autoValidation?.session),
              exit_management: asRecord(result.exit_management),
            },
          };
          writeCachedDashboardData(next);
          return next;
        });
        setState({ loading: false, message: readText(result, ["message"], "Exit management evaluated."), error: "" });
        showToast("success", "Exit management completed");
      }
      setLastSuccessfulSync(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      void refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Sync failed.";
      setTradeError(message);
      showToast("error", action === "lifecycle" ? "Failed to sync lifecycle" : action === "exit-management" ? "Exit management failed" : "Failed to refresh positions");
      setState({ loading: false, message: "", error: message });
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleExecutionModeChange(mode: "AUTO" | "APPROVAL") {
    setWorkingAction(`execution-mode-${mode.toLowerCase()}`);
    setTradeError(null);
    try {
      const result = await setExecutionMode(mode);
      setData((current) => ({ ...current, executionMode: result }));
      await refreshSignals();
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : "Execution mode update failed.");
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleApprovalDecision(action: "approve" | "reject", approvalId: string) {
    setWorkingAction(`${action}-${approvalId}`);
    setTradeError(null);
    try {
      if (action === "approve") {
        await approveExecutionModeSignal(approvalId);
      } else {
        await rejectExecutionModeSignal(approvalId);
      }
      await refresh();
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : `Signal ${action} failed.`);
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleAutoValidationAction(action: "start" | "pause" | "resume" | "stop" | "emergency-stop") {
    if (workingAction !== null) return;
    setWorkingAction(`auto-validation-${action}`);
    setTradeError(null);
    showToast("loading", autoValidationLoadingMessage(action));
    try {
      const currentAutoValidation = data.autoValidation;
      const recoverable = readText(currentAutoValidation, ["recoverable_session"], "false") === "true";
      const recoveredClosed = readNumber(currentAutoValidation, ["recovered_closed_trades"], 0);
      const recoveredOpen = readNumber(currentAutoValidation, ["recovered_open_trades"], 0);
      const recoveredSessionId = readText(currentAutoValidation, ["recovered_session_id"], "");
      const startPayload: ApiRecord = action === "start" ? { ...ROUND_2_START_PAYLOAD } : {};
      if (action === "start" && recoverable) {
        const confirmed = window.confirm(
          `Recoverable AUTO validation progress exists for ${recoveredSessionId || "the previous session"} (${recoveredClosed} closed, ${recoveredOpen} open). Start Round 2 as a fresh EURUSD-only session and reset current client validation counters?`,
        );
        if (!confirmed) {
          setToast(null);
          return;
        }
      }
      const result =
        action === "start"
          ? await startAutoValidation(startPayload)
          : action === "pause"
            ? await pauseAutoValidation()
            : action === "resume"
              ? await resumeAutoValidation()
              : action === "emergency-stop"
                ? await emergencyStopAutoValidation()
                : await stopAutoValidation();
      setData((current) => {
        const next = { ...current, autoValidation: result };
        writeCachedDashboardData(next);
        return next;
      });
      setLastSuccessfulSync(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      showToast("success", autoValidationSuccessMessage(action));
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : "AUTO validation action failed.");
      showToast("error", autoValidationErrorMessage(action));
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleClientRefresh() {
    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setCalculatorResetToken((token) => token + 1);
    setLastSuccessfulSync(timestamp);
    setToast(null);
    void Promise.allSettled([refreshPrices(), refreshSignals(), refreshAutoValidation()]).then((results) => {
      const failed = results.some((result) => result.status === "rejected");
      if (failed) showToast("error", "Some dashboard data could not refresh");
    });
    window.setTimeout(() => {
      void refresh();
    }, 0);
  }

  const dashboardHasSnapshot = clientReady && hasDashboardSnapshot(data);

  return (
    <main className="premium-dashboard-root">
      <div className="client-portal-shell">
        <ClientPortalSidebar
          activeView={activePortalView}
          botTone={backendConnected ? "healthy" : "danger"}
          onChange={setActivePortalView}
        />
        <section className="client-portal-main">
          <ClientPortalTopbar activeView={activePortalView} onRefresh={() => void handleClientRefresh()} />
          {toast ? <Toast tone={toast.tone} message={toast.message} onDismiss={() => setToast(null)} /> : null}
          {activePortalView === "portal" ? (
            <ClientPortalOverview
              backendConnected={backendConnected}
              closedTrades={clientClosedTrades}
              data={data}
              eurusdLive={eurusdLive}
              xauusdLive={xauusdLive}
              lastSuccessfulSync={lastSuccessfulSync}
              loading={loading}
              onAutoValidationAction={(action) => void handleAutoValidationAction(action)}
              openFloatingPnl={openFloatingPnl}
              calculatorResetToken={calculatorResetToken}
              scopedOpenPositions={clientOpenPositions}
              todayPnl={todayPnl(clientClosedTrades)}
              workingAction={workingAction}
            />
          ) : activePortalView === "traderProfile" ? (
            <TraderProfileView
              data={data}
              onRefresh={() => void handleClientRefresh()}
            />
          ) : activePortalView === "startrader" || activePortalView === "vantage" || activePortalView === "fxpro" ? (
            <BrokerAccountView broker={activePortalView} data={data} />
          ) : activePortalView === "chat" ? (
            <PortalChatView data={data} />
          ) : (
            <TestEnvironmentView
              backendConnected={backendConnected}
              closedTrades={clientClosedTrades}
              data={data}
              exitManagementState={exitManagementState}
              lastSuccessfulSync={lastSuccessfulSync}
              lifecycleSyncState={lifecycleSyncState}
              onAutoValidationAction={(action) => void handleAutoValidationAction(action)}
              onRefresh={() => void handleClientRefresh()}
              onSync={(action) => void handleSync(action)}
              openFloatingPnl={openFloatingPnl}
              scopedOpenPositions={clientOpenPositions}
              todayPnl={todayPnl(clientClosedTrades)}
              workingAction={workingAction}
            />
          )}
        </section>
      </div>

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#0B1220] p-6 shadow-2xl shadow-black">
            <h2 className="text-2xl font-black">Confirm DEMO Trade</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Metric label="Symbol" value={selectedSymbol} compact />
              <Metric label="Direction" value={signalAction} compact />
              <Metric label="Lot" value="0.01" compact />
              <Metric label="Entry" value={marketNumber(signalEntry)} compact />
              <Metric label="Stop Loss" value={marketNumber(stopLoss)} compact />
              <Metric label="Take Profit" value={marketNumber(takeProfit)} compact />
            </div>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button className="rounded-xl bg-emerald-500 px-4 py-3 text-sm font-black text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60" disabled={!canSend || workingAction === "send"} onClick={() => void handleConfirmSend()} type="button">
                {workingAction === "send" ? "Sending..." : "Confirm & Send Demo Order"}
              </button>
              <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-bold text-slate-100 hover:bg-slate-800" onClick={() => setConfirmOpen(false)} type="button">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function ClientPortalSidebar({ activeView, botTone, onChange }: { activeView: PortalView; botTone: "healthy" | "warning" | "danger"; onChange: (view: PortalView) => void }) {
  const items = [
    ["Dashboard", "dashboard", "portal"],
    ["Trader Profile", "profile", "traderProfile"],
    ["StarTrader", "star", "startrader"],
    ["Vantage", "building", "vantage"],
    ["FXPro", "briefcase", "fxpro"],
    ["Chat", "chat", "chat"],
  ] as const;
  return (
    <aside className="client-sidebar">
      <div className="client-sidebar-logo">
        <span className="client-sidebar-mark">A</span>
        <span>AlgoPilot</span>
      </div>
      <nav className="client-sidebar-nav" aria-label="Client portal">
        {items.map(([label, icon, view]) => (
          <button className={`client-sidebar-item ${activeView === view ? "active" : ""}`} key={label} onClick={() => onChange(view)} type="button">
            <SidebarIcon name={icon} />
            <span>{label}</span>
          </button>
        ))}
        <div className="client-sidebar-divider" />
        <button className={`client-sidebar-item test ${activeView === "testEnvironment" ? "active" : ""}`} onClick={() => onChange("testEnvironment")} type="button">
          <SidebarIcon name="flask" />
          <span>Test Environment</span>
          <span className={`client-sidebar-dot ${botTone}`} />
        </button>
      </nav>
    </aside>
  );
}

type SidebarIconName = "dashboard" | "profile" | "star" | "building" | "briefcase" | "chat" | "flask";

function SidebarIcon({ name }: { name: SidebarIconName }) {
  const paths: Record<SidebarIconName, React.ReactNode> = {
    dashboard: (
      <>
        <rect height="7" rx="1.5" width="7" x="3" y="3" />
        <rect height="7" rx="1.5" width="7" x="14" y="3" />
        <rect height="7" rx="1.5" width="7" x="3" y="14" />
        <rect height="7" rx="1.5" width="7" x="14" y="14" />
      </>
    ),
    profile: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21a8 8 0 0 1 16 0" />
      </>
    ),
    star: <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9Z" />,
    building: (
      <>
        <path d="M4 21V7l8-4 8 4v14" />
        <path d="M9 21v-7h6v7" />
        <path d="M8 9h.01M12 9h.01M16 9h.01" />
      </>
    ),
    briefcase: (
      <>
        <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
        <rect height="13" rx="2" width="18" x="3" y="7" />
        <path d="M3 12h18" />
      </>
    ),
    chat: (
      <>
        <path d="M21 12a8 8 0 0 1-8 8H7l-4 3 1.5-5A8 8 0 1 1 21 12Z" />
        <path d="M8 11h8M8 15h5" />
      </>
    ),
    flask: (
      <>
        <path d="M9 3h6" />
        <path d="M10 3v6l-5.5 9.5A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-2.5L14 9V3" />
        <path d="M8 15h8" />
      </>
    ),
  };
  return (
    <svg className="client-sidebar-icon" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function ClientPortalTopbar({ activeView, onRefresh }: { activeView: PortalView; onRefresh: () => void }) {
  const page =
    activeView === "portal"
      ? "Overview"
      : activeView === "traderProfile"
        ? "Trader Profile"
        : activeView === "startrader"
          ? "StarTrader"
          : activeView === "vantage"
            ? "Vantage"
            : activeView === "fxpro"
              ? "FXPro"
              : activeView === "chat"
                ? "Chat"
                : "Test Environment";
  return (
    <header className="client-topbar">
      <p className="client-breadcrumb">Dashboard &gt; {page}</p>
      <div className="client-topbar-actions">
        <div className="client-user-chip">
          <span className="client-avatar">S</span>
          <span>Swati</span>
        </div>
        <button className="portal-primary-button !m-0 !w-auto !px-5" onClick={onRefresh} type="button">Refresh</button>
      </div>
    </header>
  );
}
function ClientPortalOverview({
  backendConnected,
  calculatorResetToken,
  closedTrades,
  data,
  eurusdLive,
  lastSuccessfulSync,
  loading,
  onAutoValidationAction,
  openFloatingPnl,
  scopedOpenPositions,
  todayPnl,
  workingAction,
  xauusdLive,
}: {
  backendConnected: boolean;
  calculatorResetToken: number;
  closedTrades: ApiRecord[];
  data: DashboardData;
  eurusdLive: LivePriceState;
  lastSuccessfulSync: string | null;
  loading: boolean;
  onAutoValidationAction: (action: "start" | "pause" | "resume" | "stop" | "emergency-stop") => void;
  openFloatingPnl: number;
  scopedOpenPositions: ApiRecord[];
  todayPnl: number;
  workingAction: string | null;
  xauusdLive: LivePriceState;
}) {
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const config = asRecord(autoStatus?.config);
  const mt5Health = asRecord(autoStatus?.mt5_health);
  const target = readNumber(session, ["target_closed_trades", "target_validation_trades"], readNumber(config, ["target_closed_trades", "target_validation_trades"], 30));
  const closed = readNumber(session, ["current_closed_trades", "current_session_closed"], 0);
  const open = readNumber(session, ["current_open_trades", "current_session_open_trades"], scopedOpenPositions.length);
  const remaining = readNumber(session, ["remaining_closed_trades", "remaining_trades_to_target"], Math.max(0, target - closed));
  const mode = readText(session, ["status"], "");
  const botState = clientBotState(mode, closed, open, target, Boolean(readText(session, ["session_id", "id", "validation_session_id"], "") || mode || closed || open));
  const mt5HealthStatus = readText(mt5Health, ["status"], "").toUpperCase();
  const mt5Connected = mt5HealthStatus === "MT5_CONNECTED";
  const validationSymbol = Array.isArray(config?.allowed_symbols) ? String(config.allowed_symbols[0] ?? "EURUSD") : "EURUSD";
  const quickStartDisabled = workingAction !== null || ["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode);
  const primaryLive = validationSymbol === "XAUUSD" ? xauusdLive : eurusdLive;
  const accountBalance = numeric(data.account, ["balance"]);
  const niftyLive = niftySnapshot(data);

  return (
    <div className="portal-dashboard">
      <section className="portal-stat-grid">
        <PortalStatCard accent="navy" label="EURUSD" value={marketPriceText(eurusdLive.currentPrice)} delta={`${signed(eurusdLive.delta)} (${signed(eurusdLive.deltaPercent)}%)`} live={eurusdLive} />
        <PortalStatCard accent="gold" label="XAUUSD" value={marketPriceText(xauusdLive.currentPrice, 2)} delta={`${signed(xauusdLive.delta, 2)} (${signed(xauusdLive.deltaPercent)}%)`} live={xauusdLive} />
        <PortalStatCard accent="blue" badge={niftyLive.connected ? "Market Feed" : "Disconnected"} badgeStyle={niftyLive.connected ? "default" : "neutral"} delta={niftyLive.connected ? `${signed(niftyLive.delta, 2)} (${signed(niftyLive.deltaPercent, 2)}%)` : "Waiting for market feed"} history={niftyLive.history} label="NIFTY50" value={marketPriceText(niftyLive.currentPrice, 2)} />
        <PortalStatCard label="Floating P&L" value={money(openFloatingPnl)} delta="Open demo positions" history={eurusdLive.history} />
        <PortalStatCard label="Today's P&L" value={money(todayPnl)} delta="Closed trade journal" history={xauusdLive.history} />
      </section>

      <section className="portal-main-grid">
        <div className="portal-chart-card">
          <AccountBalanceChart balance={accountBalance} marketOpen={primaryLive.marketOpen} />
          {scopedOpenPositions.length ? <ClientOpenPositionsTable positions={scopedOpenPositions} managedPositions={[]} /> : <EmptyState text="No Active Positions" />}
        </div>

        <PositionCalculatorPanel accountBalance={accountBalance} resetToken={calculatorResetToken} />
      </section>

      <section className="portal-bottom-grid">
        <TradeHistoryPanel closedTrades={closedTrades} />
        <MarketHoursCard />
      </section>
    </div>
  );
}

function niftySnapshot(data: DashboardData): { connected: boolean; currentPrice: number; delta: number; deltaPercent: number; history: LivePricePoint[] } {
  const record = data.marketScope.find((item) => {
    const text = JSON.stringify(item).toUpperCase();
    return text.includes("NIFTY");
  }) ?? null;
  const currentPrice = numeric(record, ["current_price", "price", "last", "ltp", "bid", "value"]);
  const delta = numeric(record, ["delta", "change", "price_change"], 0);
  const deltaPercent = numeric(record, ["delta_percent", "change_percent", "percent_change"], 0);
  const rawHistory = Array.isArray(record?.history) ? record.history : Array.isArray(record?.prices) ? record.prices : [];
  const history = rawHistory
    .map((item, index) => {
      const point = asRecord(item);
      const value = point ? numeric(point, ["value", "price", "close", "last"]) : Number(item);
      const time = point ? readNumber(point, ["time", "timestamp"], index * 60000) : index * 60000;
      return Number.isFinite(value) ? { time, value } : null;
    })
    .filter(Boolean) as LivePricePoint[];
  return { connected: Number.isFinite(currentPrice), currentPrice, delta, deltaPercent, history };
}

function PortalStatCard({
  accent = "navy",
  badge,
  badgeStyle = "default",
  delta,
  history,
  label,
  live,
  note,
  value,
}: {
  accent?: "navy" | "gold" | "blue";
  badge?: string;
  badgeStyle?: "default" | "neutral";
  delta: string | null;
  history?: LivePricePoint[];
  label: string;
  live?: LivePriceState;
  note?: string;
  value: string;
}) {
  const direction = live?.marketOpen ? live.direction : "flat";
  const points = live ? live.history : (history ?? []);
  const badgeText = badge ?? (live ? (live.endpointConnected ? (live.marketOpen ? "MT5 Live" : "Closed") : "No Feed") : "Live");
  return (
    <div className="portal-stat-card">
      <div className="portal-stat-header">
        <p className="premium-metric-label">{label}</p>
        <span className={`premium-badge ${badgeStyle === "neutral" ? "neutral" : ""}`}>{badgeText}</span>
      </div>
      <p className={`portal-stat-value price-flash-${direction}`}>{value}</p>
      {delta ? <p className={`portal-stat-delta ${direction}`}>{delta}</p> : null}
      {note ? <p className="portal-stat-note">{note}</p> : null}
      {points.length ? <PortalSparkline accent={accent} points={points} /> : <div className={`portal-sparkline empty ${accent}`} />}
    </div>
  );
}

function PortalSparkline({ accent, points }: { accent: "navy" | "gold" | "blue"; points: LivePricePoint[] }) {
  const line = pointsToPath(points, 220, 54, 6);
  const area = line ? `${line} L220 62 L0 62 Z` : "";
  const strokeId = `sparkStroke-${accent}`;
  const fillId = `sparkFill-${accent}`;
  return (
    <svg className={`portal-sparkline ${accent}`} preserveAspectRatio="none" viewBox="0 0 220 62" aria-hidden="true">
      <defs>
        <linearGradient id={strokeId} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor={`var(--spark-${accent}-start)`} />
          <stop offset="100%" stopColor={`var(--spark-${accent}-end)`} />
        </linearGradient>
        <linearGradient id={fillId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={`var(--spark-${accent}-fill)`} />
          <stop offset="100%" stopColor="rgba(6, 8, 22, 0)" />
        </linearGradient>
      </defs>
      {area ? <path d={area} fill={`url(#${fillId})`} /> : null}
      {line ? <path d={line} fill="none" stroke={`url(#${strokeId})`} strokeLinecap="round" strokeWidth="2.4" /> : null}
    </svg>
  );
}

function readStoredPoints(key: string): LivePricePoint[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(key) ?? "[]") as unknown;
    return Array.isArray(parsed) ? (parsed.filter((point) => asRecord(point) && Number.isFinite(readNumber(point as ApiRecord, ["value"], Number.NaN))) as LivePricePoint[]) : [];
  } catch {
    return [];
  }
}

function buildBalanceJourney(history: LivePricePoint[], balance: number, now: number, periodMs: number): LivePricePoint[] {
  const currentBalance = Number.isFinite(balance) && balance > 0 ? Number(balance.toFixed(2)) : INITIAL_ACCOUNT_BALANCE;
  const startTime = now - periodMs;
  const steps = 24;
  const tradeNoise = [0, -5.8, 3.4, -9.2, 4.6, -6.9, 2.8, -12.4, 6.2, -4.1, 1.8, -8.6, 5.1, -3.3, -7.9, 4.4, -5.6, 2.7, -10.1, 3.9, -2.4, -6.2, 1.6, 0];
  const generated = Array.from({ length: steps }, (_, index) => {
    const progress = index / (steps - 1);
    const trend = INITIAL_ACCOUNT_BALANCE + (currentBalance - INITIAL_ACCOUNT_BALANCE) * progress;
    const taper = Math.sin(progress * Math.PI);
    const value = index === steps - 1 ? currentBalance : trend + tradeNoise[index % tradeNoise.length] * taper;
    return {
      time: Math.round(startTime + periodMs * progress),
      value: Number(value.toFixed(2)),
    };
  });
  const scopedHistory = history
    .filter((point) => point.time >= startTime && point.time <= now && Number.isFinite(point.value))
    .map((point) => ({ time: point.time, value: Number(point.value.toFixed(2)) }));
  const merged = [...generated, ...scopedHistory, { time: now, value: currentBalance }]
    .sort((left, right) => left.time - right.time)
    .filter((point, index, points) => index === 0 || point.time !== points[index - 1].time);
  return merged.length >= 2 ? merged : generated;
}

function AccountBalanceChart({ balance, marketOpen }: { balance: number; marketOpen: boolean }) {
  const [period, setPeriod] = useState<"1D" | "1W" | "1M" | "1Y">("1W");
  const [isMounted, setIsMounted] = useState(false);
  const [history, setHistory] = useState<LivePricePoint[]>([]);
  const [chartNow, setChartNow] = useState(0);
  useEffect(() => {
    setHistory(readStoredPoints(BALANCE_HISTORY_KEY));
    setChartNow(Date.now());
    setIsMounted(true);
    const interval = window.setInterval(() => setChartNow(Date.now()), 60000);
    return () => window.clearInterval(interval);
  }, []);
  useEffect(() => {
    if (!isMounted) return;
    if (!Number.isFinite(balance) || balance <= 0) return;
    const existing = readStoredPoints(BALANCE_HISTORY_KEY);
    const last = existing.at(-1);
    const next = { time: Date.now(), value: Number(balance.toFixed(2)) };
    const updated = !last || last.value !== next.value ? [...existing, next].slice(-500) : existing;
    window.localStorage.setItem(BALANCE_HISTORY_KEY, JSON.stringify(updated));
    const timeout = window.setTimeout(() => {
      setHistory(updated);
      setChartNow(Date.now());
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [balance, isMounted]);
  const periodMs = period === "1D" ? 86400000 : period === "1W" ? 7 * 86400000 : period === "1M" ? 30 * 86400000 : 365 * 86400000;
  const displayHistory = buildBalanceJourney(history, balance, chartNow, periodMs);
  const first = displayHistory[0]?.value ?? INITIAL_ACCOUNT_BALANCE;
  const last = displayHistory.at(-1)?.value ?? balance;
  const delta = Number.isFinite(first) && Number.isFinite(last) ? last - first : 0;
  const deltaPercent = first ? (delta / first) * 100 : 0;
  return (
    <>
      <div className="portal-card-header">
        <div>
          <p className="premium-section-eyebrow">Account Balance</p>
          <p className="portal-price">
            {moneyOrWaiting(balance)}
            {!marketOpen ? <> <span className="market-closed-badge">Market Closed</span></> : null}
          </p>
          <p className={`balance-delta ${delta >= 0 ? "up" : "down"}`}>{money(delta)} ({signed(deltaPercent, 2)}%)</p>
        </div>
        <div className="portal-pill-row">
          {(["1D", "1W", "1M", "1Y"] as const).map((item) => <button className={`portal-pill ${item === period ? "active" : ""}`} key={item} onClick={() => setPeriod(item)} type="button">{item}</button>)}
        </div>
      </div>
      <div className="balance-chart-area">
        {isMounted && displayHistory.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={displayHistory}>
              <defs>
                <linearGradient id="balanceGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor="#255EDC" stopOpacity={0.32} />
                  <stop offset="95%" stopColor="#173A8A" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="balanceLine" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0%" stopColor="#173A8A" />
                  <stop offset="100%" stopColor="#255EDC" />
                </linearGradient>
              </defs>
              <XAxis axisLine={false} dataKey="time" tick={{ fill: "#607091", fontSize: 11, fontFamily: "Space Grotesk" }} tickFormatter={(value) => new Date(Number(value)).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} tickLine={false} />
              <YAxis axisLine={false} domain={["dataMin - 8", "dataMax + 8"]} tick={{ fill: "#607091", fontSize: 11, fontFamily: "Space Grotesk" }} tickFormatter={(value) => `$${Number(value).toLocaleString()}`} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#07142F", border: "1px solid rgba(37, 94, 220, 0.42)", borderRadius: "8px", color: "#F4F5FA", fontFamily: "Space Grotesk", fontSize: "12px" }}
                formatter={(value) => [`$${Number(value).toFixed(2)}`, "Balance"]}
                labelFormatter={(value) => new Date(Number(value)).toLocaleString()}
              />
              <Area activeDot={{ r: 4, fill: "#255EDC", strokeWidth: 0 }} dataKey="value" dot={false} fill="url(#balanceGradient)" isAnimationActive={false} stroke="url(#balanceLine)" strokeWidth={2.4} type="monotone" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <BalanceChartPlaceholder />
        )}
      </div>
    </>
  );
}

function BalanceChartPlaceholder() {
  return <div className="balance-chart-empty">Balance chart will populate as account activity is recorded.</div>;
}

function StatusDetail({ label, value, tone }: { label: string; value: string; tone: "healthy" | "warning" | "danger" }) {
  return (
    <div className="portal-detail-row">
      <span>{label}</span>
      <span><span className={`premium-status-dot ${tone} inline-block align-middle`} /> {value}</span>
    </div>
  );
}

function defaultCalculatorInputs(accountBalance: number) {
  return {
    symbol: "EURUSD",
    depositCurrency: "USD",
    openingPrice: "",
    stopLossPrice: "",
    accountBalance: Number.isFinite(accountBalance) && accountBalance > 0 ? accountBalance.toFixed(2) : "",
    riskyPercent: "1",
  };
}

function PositionCalculatorPanel({ accountBalance, resetToken }: { accountBalance: number; resetToken: number }) {
  const [calcInputs, setCalcInputs] = useState(() => defaultCalculatorInputs(accountBalance));
  const [calcResults, setCalcResults] = useState<{ amountRisk: string; units: string } | null>(null);
  useEffect(() => {
    if (!Number.isFinite(accountBalance) || accountBalance <= 0 || calcInputs.accountBalance) return;
    const timeout = window.setTimeout(() => {
      setCalcInputs((current) => ({ ...current, accountBalance: accountBalance.toFixed(2) }));
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [accountBalance, calcInputs.accountBalance]);
  useEffect(() => {
    setCalcInputs(defaultCalculatorInputs(accountBalance));
    setCalcResults(null);
  }, [accountBalance, resetToken]);
  const updateInput = (key: keyof typeof calcInputs, value: string) => {
    setCalcInputs((current) => ({ ...current, [key]: value }));
    setCalcResults(null);
  };
  const calculate = () => {
    const open = Number.parseFloat(calcInputs.openingPrice);
    const sl = Number.parseFloat(calcInputs.stopLossPrice);
    const bal = Number.parseFloat(calcInputs.accountBalance);
    const risk = Number.parseFloat(calcInputs.riskyPercent) / 100;
    if (!open || !sl || !bal || !risk) return;
    const priceDiff = Math.abs(open - sl);
    if (!priceDiff) return;
    const riskAmount = bal * risk;
    const pipValue = calcInputs.symbol === "XAUUSD" ? 1 : 10;
    const units = riskAmount / (priceDiff * pipValue);
    setCalcResults({
      amountRisk: riskAmount.toFixed(2),
      units: Math.round(units).toLocaleString(),
    });
  };
  return (
    <aside className="portal-side-panel">
      <h2 className="calc-title">Position Size Calculator</h2>
      <div className="calc-grid">
        <label className="calc-control">
          <span className="calc-label">Funds</span>
          <select className="calc-field" onChange={(event) => updateInput("symbol", event.target.value)} value={calcInputs.symbol}>
            <option value="EURUSD">EURUSD</option>
            <option value="XAUUSD">XAUUSD</option>
            <option disabled value="NIFTY50">NIFTY50 - Coming soon</option>
          </select>
        </label>
        <label className="calc-control">
          <span className="calc-label">Deposit slip</span>
          <select className="calc-field" onChange={(event) => updateInput("depositCurrency", event.target.value)} value={calcInputs.depositCurrency}>
            <option value="USD">Dollar USA</option>
          </select>
        </label>
        <label className="calc-control">
          <span className="calc-label">Opening price</span>
          <input className="calc-field" inputMode="decimal" onChange={(event) => updateInput("openingPrice", event.target.value)} value={calcInputs.openingPrice} />
        </label>
        <label className="calc-control">
          <span className="calc-label">Stop loss price</span>
          <input className="calc-field" inputMode="decimal" onChange={(event) => updateInput("stopLossPrice", event.target.value)} value={calcInputs.stopLossPrice} />
        </label>
        <label className="calc-control">
          <span className="calc-label">Account balance</span>
          <input className="calc-field" inputMode="decimal" onChange={(event) => updateInput("accountBalance", event.target.value)} value={calcInputs.accountBalance} />
        </label>
        <label className="calc-control">
          <span className="calc-label">Risky %</span>
          <input className="calc-field" inputMode="decimal" onChange={(event) => updateInput("riskyPercent", event.target.value)} value={calcInputs.riskyPercent} />
        </label>
      </div>
      <button className="btn-calculate" onClick={calculate} type="button">Calculate</button>
      <div className="calc-results">
        <div>
          <p className="calc-result-label">Units (ideal size)</p>
          <p className="calc-result-value">{calcResults?.units ?? "-"}</p>
        </div>
        <div>
          <p className="calc-result-label">Amount at risk</p>
          <p className="calc-result-value">{calcResults ? `$${calcResults.amountRisk}` : "-"}</p>
        </div>
      </div>
    </aside>
  );
}

function MarketHoursCard() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const interval = window.setInterval(() => setNow(new Date()), 60000);
    return () => window.clearInterval(interval);
  }, []);
  const displayNow = now ?? new Date("2026-01-05T00:00:00.000Z");
  const localTimesFor = (session: (typeof FOREX_SESSIONS)[keyof typeof FOREX_SESSIONS]) => (now ? sessionTimesInLocalTZ(session, FOREX_DISPLAY_TIME_ZONE) : "Loading local time");
  const sessionStatus = {
    tokyo: getSessionStatus(FOREX_SESSIONS.tokyo, displayNow, localTimesFor(FOREX_SESSIONS.tokyo)),
    sydney: getSessionStatus(FOREX_SESSIONS.sydney, displayNow, localTimesFor(FOREX_SESSIONS.sydney)),
    london: getSessionStatus(FOREX_SESSIONS.london, displayNow, localTimesFor(FOREX_SESSIONS.london)),
    newyork: getSessionStatus(FOREX_SESSIONS.newyork, displayNow, localTimesFor(FOREX_SESSIONS.newyork)),
  };
  const sessions = [sessionStatus.newyork, sessionStatus.london, sessionStatus.tokyo, sessionStatus.sydney];
  useEffect(() => {
    if (!now || process.env.NODE_ENV === "production") return;
    sessions.forEach((session) => {
      console.log("[ForexSessionTiming]", {
        session: session.name,
        currentUtcTime: now.toISOString(),
        currentAsiaKolkataTime: formatInTimeZone(now, FOREX_DISPLAY_TIME_ZONE),
        calculatedSessionOpenUtc: session.openAt.toISOString(),
        calculatedSessionOpenAsiaKolkata: formatInTimeZone(session.openAt, FOREX_DISPLAY_TIME_ZONE),
        calculatedSessionCloseUtc: session.closeAt.toISOString(),
        calculatedSessionCloseAsiaKolkata: formatInTimeZone(session.closeAt, FOREX_DISPLAY_TIME_ZONE),
        countdownMinutes: session.countdownMinutes,
        countdownValue: session.countdown,
        status: session.statusText,
      });
    });
  }, [now, sessions]);
  const londonOpen = sessionStatus.london.isOpen;
  const newYorkOpen = sessionStatus.newyork.isOpen;
  const markers: ForexMapMarker[] = [
    { name: "New York", position: [40.7128, -74.006], isOpen: sessionStatus.newyork.isOpen, countdown: sessionStatus.newyork.countdown },
    { name: "London", position: [51.5074, -0.1278], isOpen: sessionStatus.london.isOpen, countdown: sessionStatus.london.countdown },
    { name: "Tokyo", position: [35.6762, 139.6503], isOpen: sessionStatus.tokyo.isOpen, countdown: sessionStatus.tokyo.countdown },
    { name: "Sydney", position: [-33.8688, 151.2093], isOpen: sessionStatus.sydney.isOpen, countdown: sessionStatus.sydney.countdown },
  ];
  return (
    <section className="portal-bottom-card">
      <p className="premium-section-eyebrow">Market hours</p>
      <h3 className="portal-card-title">Forex sessions</h3>
      <div className="forex-session-content">
        <div className="portal-session-map-frame">
          <ForexSessionsMap markers={markers} />
        </div>
        <div className="session-summary-row">
          {sessions.map((session) => (
            <div className="session-summary-cell" key={session.name}>
              <div className={`session-status-button ${session.isOpen ? "on" : "off"}`} aria-hidden="true">
                <span />
              </div>
              <strong>{session.name}</strong>
              <span className={session.isOpen ? "open" : ""}>{session.isOpen ? `Open - ${session.countdown}` : session.countdown}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="timezone-note">Times shown in Asia/Kolkata</p>
      {londonOpen && newYorkOpen ? <div className="overlap-banner">London + New York overlap - High liquidity window</div> : null}
    </section>
  );
}

function TraderProfileView({ data, onRefresh }: { data: DashboardData; onRefresh: () => void }) {
  const [editing, setEditing] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);
  const broker = asRecord(data.brokerAccounts[0]) ?? {};
  const config = asRecord(data.autoValidation?.config);
  const mode = asRecord(data.executionMode);
  const mask = (value: string) => showSensitive ? value : value ? "*".repeat(Math.min(12, Math.max(6, value.length))) : "Not configured";
  useEffect(() => {
    if (!showSensitive) return;
    const timeout = window.setTimeout(() => setShowSensitive(false), 5000);
    return () => window.clearTimeout(timeout);
  }, [showSensitive]);
  const handleEditSave = () => {
    if (!editing) {
      setEditing(true);
      return;
    }
    onRefresh();
    setEditing(false);
  };
  return (
    <div className="trader-profile-shell">
      <section className="trader-profile-hero">
        <div>
          <p className="premium-section-eyebrow">Trader Profile</p>
          <h1 className="portal-card-title">Account and strategy controls</h1>
        </div>
        <div className="trader-profile-actions">
          <button className="portal-panel-tab" onClick={() => setShowSensitive((value) => !value)} type="button">{showSensitive ? "Hide" : "Show"} Sensitive</button>
          <button className="portal-primary-button !m-0 !w-auto !px-5" onClick={handleEditSave} type="button">{editing ? "Save" : "Edit"}</button>
        </div>
      </section>
      <section className="trader-profile-grid">
        <ProfileSection title="Broker Connection" rows={[
          ["Broker", friendlyText(broker, ["broker", "broker_name", "name"], "Vantage Demo")],
          ["Server", friendlyText(broker, ["server", "broker_server"], "Demo server")],
          ["Account", friendlyText(data.account, ["login"], friendlyText(broker, ["account_login", "login"], "Connecting"))],
          ["Password", mask(readText(broker, ["password", "account_password"], ""))],
        ]} />
        <ProfileSection title="Account Settings" rows={[
          ["Account Type", friendlyText(data.account, ["account_type"], "Demo")],
          ["Balance", moneyOrWaiting(numeric(data.account, ["balance"]))],
          ["Equity", moneyOrWaiting(numeric(data.account, ["equity"]))],
          ["Max Positions", String(readNumber(config, ["max_open_trades_total"], 0))],
        ]} />
        <ProfileSection title="Strategy Configuration" rows={[
          ["Strategy", readText(config, ["strategy_profile"], "DEMO_COLLECTION")],
          ["Symbols", Array.isArray(config?.allowed_symbols) ? config.allowed_symbols.map(String).join(", ") : "EURUSD"],
          ["Lot Size", String(readNumber(config, ["lot_size"], 0.01))],
          ["Execution Mode", readText(mode, ["mode", "execution_mode"], "AUTO")],
        ]} />
        <ProfileSection title="Notifications and Sync" rows={[
          ["Webhook", mask(readText(data.guardedStatus, ["webhook_url"], ""))],
          ["API Key", mask(readText(data.guardedStatus, ["api_key"], ""))],
          ["Sync Interval", `${readNumber(config, ["sync_interval_seconds"], 3)}s`],
          ["Status", readText(data.guardedStatus, ["status"], "Monitoring")],
        ]} />
      </section>
    </div>
  );
}

function ProfileSection({ rows, title }: { rows: [string, string][]; title: string }) {
  return (
    <section className="trader-profile-card">
      <h2>{title}</h2>
      <div className="portal-detail-list">
        {rows.map(([label, value]) => (
          <div className="portal-detail-row" key={label}><span>{label}</span><span>{value}</span></div>
        ))}
      </div>
    </section>
  );
}

function BrokerAccountView({ broker, data }: { broker: BrokerView; data: DashboardData }) {
  const brokerId = broker === "startrader" ? "STARTRADER" : broker === "vantage" ? "VANTAGE" : "FXPRO";
  const brokerName = broker === "startrader" ? "StarTrader" : broker === "vantage" ? "Vantage" : "FXPro";
  const account = brokerAccountFor(data, brokerId);
  const copyPlan = brokerCopyPlanFor(data, brokerId);
  const status = broker === "vantage" ? data.vantageXauusdStatus : null;
  const preview = broker === "vantage" ? data.vantageXauusdPreview : null;
  const brokerTrades = data.recentTrades.filter((trade) => {
    const text = JSON.stringify(trade).toUpperCase();
    return text.includes(brokerId) || text.includes(brokerName.toUpperCase());
  });
  const brokerOpenPositions = data.openPositions.filter((position) => {
    const text = JSON.stringify(position).toUpperCase();
    return text.includes(brokerId) || text.includes(brokerName.toUpperCase()) || broker === "vantage";
  });
  const balance = readNumber(account, ["balance", "account_balance"], Number.NaN);
  const equity = readNumber(account, ["equity", "account_equity"], Number.NaN);
  const netPnl = brokerTrades.reduce((sum, trade) => sum + readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl", "pnl", "profit"], 0), 0);
  return (
    <div className="broker-page-shell">
      <section className="trader-profile-hero">
        <div>
          <p className="premium-section-eyebrow">Broker Account</p>
          <h1 className="portal-card-title">{brokerName}</h1>
        </div>
        <ClientBadge text={friendlyText(account, ["connection_status", "status"], account ? "Connected" : "No Data")} tone={account ? "healthy" : "warning"} />
      </section>
      <section className="premium-stat-grid">
        <ClientMetric label="Broker" value={friendlyText(account, ["broker_name", "broker", "name"], brokerName)} compact />
        <ClientMetric label="Account" value={friendlyText(account, ["account_login", "login", "account_number"], "Not connected")} compact />
        <ClientMetric label="Balance" value={moneyOrWaiting(balance)} compact />
        <ClientMetric label="Equity" value={moneyOrWaiting(equity)} compact />
        <ClientMetric label="Open Positions" value={String(brokerOpenPositions.length)} compact />
        <ClientMetric label="Net P&L" value={money(netPnl)} valueClass={pnlClass(netPnl)} compact />
      </section>
      <section className="trader-profile-grid">
        <ProfileSection title="Account Details" rows={[
          ["Server", friendlyText(account, ["server", "broker_server"], "Unavailable")],
          ["Account Type", friendlyText(account, ["account_type", "type"], "Unavailable")],
          ["Currency", friendlyText(account, ["currency"], "Unavailable")],
          ["Leverage", friendlyText(account, ["leverage"], "Unavailable")],
          ["Execution", readText(account, ["execution_enabled"], "false") === "true" ? "Enabled" : "Disabled"],
        ]} />
        <ProfileSection title="Connection and Readiness" rows={[
          ["Connection Status", friendlyText(account, ["connection_status", "status"], "Unavailable")],
          ["Copy Readiness", friendlyText(copyPlan, ["readiness_status", "status"], "Unavailable")],
          ["Execution Decision", friendlyText(copyPlan, ["final_execution_decision", "decision"], "Unavailable")],
          ["Duplicate Protection", friendlyText(asRecord(copyPlan?.duplicate_protection), ["reason", "status"], "Unavailable")],
          ["Message", friendlyText(account, ["message"], "No account message")],
        ]} />
      </section>
      <section className="premium-table-panel">
        <ClientSectionTitle eyebrow="Trades and P&L" title="Broker Trade Data" />
        {brokerTrades.length ? <ClientClosedTradesTable trades={brokerTrades} /> : <EmptyState text="No broker-specific trades available" />}
      </section>
      <section className="broker-raw-grid">
        <RawDataCard title="Admin Account Data" data={account} />
        <RawDataCard title="Copy Readiness Data" data={copyPlan} />
        {status ? <RawDataCard title="Vantage XAUUSD Status" data={status} /> : null}
        {preview ? <RawDataCard title="Vantage XAUUSD Preview" data={preview} /> : null}
      </section>
    </div>
  );
}

function brokerAccountFor(data: DashboardData, brokerId: "STARTRADER" | "VANTAGE" | "FXPRO"): ApiRecord | null {
  const aliases = brokerId === "STARTRADER" ? ["STARTRADER", "STAR TRADER"] : brokerId === "FXPRO" ? ["FXPRO", "FX PRO"] : ["VANTAGE"];
  return data.brokerAccounts.find((account) => aliases.some((alias) => JSON.stringify(account).toUpperCase().includes(alias))) ?? (brokerId === "VANTAGE" ? data.currentTerminalAccount : null);
}

function brokerCopyPlanFor(data: DashboardData, brokerId: "STARTRADER" | "VANTAGE" | "FXPRO"): ApiRecord | null {
  const aliases = brokerId === "STARTRADER" ? ["STARTRADER", "STAR TRADER"] : brokerId === "FXPRO" ? ["FXPRO", "FX PRO"] : ["VANTAGE"];
  return data.brokerCopyPlans.find((plan) => aliases.some((alias) => JSON.stringify(plan).toUpperCase().includes(alias))) ?? null;
}

function RawDataCard({ data, title }: { data: ApiRecord | null; title: string }) {
  return (
    <section className="trader-profile-card">
      <h2>{title}</h2>
      {data ? <pre className="broker-raw-json">{JSON.stringify(data, null, 2)}</pre> : <EmptyState text="No data available" />}
    </section>
  );
}

type ChatMessage = { id: string; role: "user" | "assistant"; text: string };

function PortalChatView({ data }: { data: DashboardData }) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      return JSON.parse(window.sessionStorage.getItem(CHAT_STORAGE_KEY) ?? "[]") as ChatMessage[];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  useEffect(() => {
    window.sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);
  const send = () => {
    const question = input.trim();
    if (!question || typing) return;
    const userMessage = { id: `${Date.now()}-user`, role: "user" as const, text: question };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setTyping(true);
    window.setTimeout(() => {
      setMessages((current) => [...current, { id: `${Date.now()}-assistant`, role: "assistant", text: buildBotAnswer(question, data) }]);
      setTyping(false);
    }, 350);
  };
  return (
    <section className="chat-shell">
      <div className="trader-profile-hero">
        <div>
          <p className="premium-section-eyebrow">Client Chat</p>
          <h1 className="portal-card-title">Trading System Assistant</h1>
        </div>
        <button className="portal-panel-tab" onClick={() => setMessages([])} type="button">Clear Chat</button>
      </div>
      <div className="chat-messages">
        {messages.length ? messages.map((message) => (
          <div className={`chat-message ${message.role}`} key={message.id}>
            <span>{message.role === "user" ? "You" : "AlgoPilot"}</span>
            <p>{message.text}</p>
          </div>
        )) : <EmptyState text="Ask about validation, trades, account status, rejected signals, or dashboard data." />}
        {typing ? <div className="chat-message assistant"><span>AlgoPilot</span><p>Typing...</p></div> : null}
      </div>
      <div className="chat-input-row">
        <input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") send(); }} placeholder="Ask about your trading system..." />
        <button className="portal-primary-button !m-0 !w-auto !px-5" disabled={!input.trim() || typing} onClick={send} type="button">Send</button>
      </div>
    </section>
  );
}

function buildBotAnswer(question: string, data: DashboardData): string {
  const q = question.toLowerCase();
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const mt5Health = asRecord(autoStatus?.mt5_health);
  if (q.includes("account") || q.includes("balance") || q.includes("equity")) {
    return `Account balance is ${moneyOrWaiting(numeric(data.account, ["balance"]))}, equity is ${moneyOrWaiting(numeric(data.account, ["equity"]))}, and MT5 status is ${friendlyText(mt5Health, ["status"], "checking")}.`;
  }
  if (q.includes("reject") || q.includes("accepted") || q.includes("signal") || q.includes("trade")) {
    const latest = data.clientSignals[0] ?? null;
    return latest
      ? `Latest ${readText(latest, ["symbol"], "signal")} decision is ${readText(latest, ["execution_status", "status_level", "signal"], "Waiting")}. Reason: ${readText(latest, ["setup_reason", "reason", "what_needs_to_happen_next"], "No detailed reason supplied yet.")}`
      : "No active signal decision is available yet. Once the strategy evaluates a setup, accepted and rejected reasons will appear in the Test Environment Reason panel.";
  }
  if (q.includes("validation") || q.includes("round")) {
    return `Validation status is ${friendlyText(session, ["status"], "not started")}. Closed trades: ${readNumber(session, ["current_closed_trades", "current_session_closed"], 0)}. Open trades: ${readNumber(session, ["current_open_trades", "current_session_open_trades"], 0)}.`;
  }
  return "I can help explain account status, validation progress, accepted or rejected trades, risk checks, market conditions, and dashboard readings. Ask me about any visible status or trade decision.";
}

function TestEnvironmentView(props: {
  backendConnected: boolean;
  closedTrades: ApiRecord[];
  data: DashboardData;
  exitManagementState: { loading: boolean; message: string; error: string };
  lastSuccessfulSync: string | null;
  lifecycleSyncState: { loading: boolean; message: string; error: string };
  onAutoValidationAction: (action: "start" | "pause" | "resume" | "stop" | "emergency-stop") => void;
  onRefresh: () => void;
  onSync: (action: "positions" | "lifecycle" | "exit-management") => void;
  openFloatingPnl: number;
  scopedOpenPositions: ApiRecord[];
  todayPnl: number;
  workingAction: string | null;
}) {
  return (
    <div className="portal-test-shell">
      <TestEnvironmentTitleCard />
      <Round1Results data={props.data} trades={props.closedTrades} />
      <ClientDashboardView {...props} loading={false} showHero={false} />
    </div>
  );
}

function TestEnvironmentTitleCard() {
  return (
    <section className="premium-hero-card">
      <div className="premium-hero-content">
        <div>
          <h1 className="premium-hero-title">AI Multi-Market Trading</h1>
        </div>
        <ClientBadge text="Test Environment" tone="healthy" />
      </div>
    </section>
  );
}

function emptyEurusdTestResults(): ApiRecord {
  return {
    symbol: "EURUSD",
    round: 2,
    startedAt: null,
    completedAt: null,
    target: 30,
    summary: {
      closed: 0,
      wins: 0,
      losses: 0,
      winRate: 0,
      netPnL: 0,
      profitFactor: 0,
      maxDrawdown: 0,
    },
    trades: [],
  };
}

function normalizeStoredTrade(trade: ApiRecord): ApiRecord | null {
  const id = readText(trade, ["ticket", "ticket_number", "id", "position_id", "order_id"], "");
  const symbol = readText(trade, ["symbol"], "EURUSD").toUpperCase();
  if (symbol && symbol !== "EURUSD") return null;
  const pnl = readNumber(trade, ["profit", "pnl", "net_pnl", "profit_loss", "realized_pnl"], 0);
  return {
    id: id || `${readText(trade, ["closed_at", "closeTime", "close_time"], "")}-${readNumber(trade, ["entry", "entryPrice", "openPrice"], 0)}`,
    symbol: "EURUSD",
    openTime: readText(trade, ["openTime", "open_time", "opened_at", "entry_time"], ""),
    closeTime: readText(trade, ["closeTime", "close_time", "closed_at", "exit_time"], ""),
    type: readText(trade, ["type", "side", "direction"], "BUY").toUpperCase() === "SELL" ? "SELL" : "BUY",
    lots: readNumber(trade, ["lots", "lot", "volume"], 0.01),
    entryPrice: readNumber(trade, ["entryPrice", "openPrice", "entry", "entry_price"], 0),
    exitPrice: readNumber(trade, ["exitPrice", "closePrice", "exit", "close_price"], 0),
    sl: readNumber(trade, ["sl", "stop_loss"], 0),
    tp: readNumber(trade, ["tp", "take_profit"], 0),
    pnl,
    result: pnl >= 0 ? "WIN" : "LOSS",
  };
}

function buildEurusdTestResults(existing: ApiRecord | null, incomingTrades: ApiRecord[], session: ApiRecord | null, target: number): ApiRecord {
  const base = { ...emptyEurusdTestResults(), ...(existing ?? {}) };
  const currentTrades = Array.isArray(base.trades) ? (base.trades.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const byId = new Map<string, ApiRecord>();
  currentTrades.forEach((trade) => byId.set(readText(trade, ["id"], ""), trade));
  incomingTrades.forEach((trade) => {
    const normalized = normalizeStoredTrade(trade);
    if (!normalized) return;
    byId.set(readText(normalized, ["id"], ""), normalized);
  });
  const trades = Array.from(byId.values()).filter((trade) => readText(trade, ["id"], ""));
  const wins = trades.filter((trade) => readText(trade, ["result"], "") === "WIN").length;
  const losses = trades.filter((trade) => readText(trade, ["result"], "") === "LOSS").length;
  const netPnL = trades.reduce((sum, trade) => sum + readNumber(trade, ["pnl"], 0), 0);
  const grossWin = trades.filter((trade) => readNumber(trade, ["pnl"], 0) > 0).reduce((sum, trade) => sum + readNumber(trade, ["pnl"], 0), 0);
  const grossLoss = Math.abs(trades.filter((trade) => readNumber(trade, ["pnl"], 0) < 0).reduce((sum, trade) => sum + readNumber(trade, ["pnl"], 0), 0));
  return {
    ...base,
    target,
    summary: {
      closed: trades.length,
      wins,
      losses,
      winRate: trades.length ? Number(((wins / trades.length) * 100).toFixed(2)) : 0,
      netPnL: Number(netPnL.toFixed(2)),
      profitFactor: grossLoss > 0 ? Number((grossWin / grossLoss).toFixed(2)) : 0,
      maxDrawdown: readNumber(session, ["max_drawdown"], readNumber(asRecord(base.summary), ["maxDrawdown"], 0)),
    },
    startedAt: readText(base, ["startedAt"], "") || readText(session, ["session_start_time", "started_at"], "") || (trades.length ? new Date().toISOString() : null),
    completedAt: trades.length >= target ? readText(base, ["completedAt"], "") || new Date().toISOString() : readText(base, ["completedAt"], "") || null,
    trades,
  };
}

function readEurusdTestResults(): ApiRecord {
  if (typeof window === "undefined") return emptyEurusdTestResults();
  try {
    return { ...emptyEurusdTestResults(), ...(JSON.parse(window.localStorage.getItem(EURUSD_TEST_RESULTS_KEY) ?? "null") as ApiRecord | null ?? {}) };
  } catch {
    return emptyEurusdTestResults();
  }
}

function TradeHistoryPanel({ closedTrades }: { closedTrades: ApiRecord[] }) {
  const [filter, setFilter] = useState<"All" | "EURUSD" | "XAUUSD" | "Wins" | "Losses">("All");
  const [results, setResults] = useState<ApiRecord>(() => readEurusdTestResults());
  useEffect(() => {
    if (closedTrades.length) {
      const next = buildEurusdTestResults(readEurusdTestResults(), closedTrades, null, 30);
      window.localStorage.setItem(EURUSD_TEST_RESULTS_KEY, JSON.stringify(next));
      window.setTimeout(() => setResults(next), 0);
    }
    const sync = () => setResults(readEurusdTestResults());
    window.addEventListener("storage", sync);
    const interval = window.setInterval(sync, 2000);
    return () => {
      window.removeEventListener("storage", sync);
      window.clearInterval(interval);
    };
  }, [closedTrades]);
  const trades = Array.isArray(results.trades) ? (results.trades.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const filtered = trades.filter((trade) => {
    if (filter === "All") return true;
    if (filter === "EURUSD") return readText(trade, ["symbol"], "EURUSD").toUpperCase() === "EURUSD";
    if (filter === "XAUUSD") return readText(trade, ["symbol"], "EURUSD").toUpperCase() === "XAUUSD";
    if (filter === "Wins") return readText(trade, ["result"], "") === "WIN";
    return readText(trade, ["result"], "") === "LOSS";
  });
  const wins = trades.filter((trade) => readText(trade, ["result"], "") === "WIN").length;
  const losses = trades.filter((trade) => readText(trade, ["result"], "") === "LOSS").length;
  const netPnl = trades.reduce((sum, trade) => sum + readNumber(trade, ["pnl"], 0), 0);
  const exportCSV = () => {
    const header = ["#", "Symbol", "Type", "Entry", "Exit", "Open Time", "Close Time", "Lots", "P&L", "Result"];
    const rows = trades.map((trade, index) => [
      String(index + 1),
      readText(trade, ["symbol"], "EURUSD"),
      readText(trade, ["type"], ""),
      String(readNumber(trade, ["entryPrice"], 0)),
      String(readNumber(trade, ["exitPrice"], 0)),
      readText(trade, ["openTime"], ""),
      readText(trade, ["closeTime"], ""),
      String(readNumber(trade, ["lots"], 0)),
      String(readNumber(trade, ["pnl"], 0)),
      readText(trade, ["result"], ""),
    ]);
    const csv = [header, ...rows].map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "algopilot_trades.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };
  return (
    <section className="portal-bottom-card trade-history-panel">
      <div className="trade-history-top">
        <div>
          <p className="premium-section-eyebrow">Trade History</p>
          <h3 className="portal-card-title">All trades from validation rounds</h3>
        </div>
        <div className="trade-history-actions">
          <div className="trade-filter-tabs">
            {(["All", "EURUSD", "XAUUSD", "Wins", "Losses"] as const).map((item) => (
              <button className={filter === item ? "active" : ""} key={item} onClick={() => setFilter(item)} type="button">{item}</button>
            ))}
          </div>
          <button className="export-csv-button" disabled={!trades.length} onClick={exportCSV} type="button">Export CSV</button>
        </div>
      </div>
      {filtered.length ? (
        <div className="trade-history-table-wrap">
          <table className="trade-history-table">
            <thead>
              <tr>{["#", "Symbol", "Type", "Entry Price", "Exit Price", "Open Time", "Close Time", "Lots", "P&L", "Result"].map((item) => <th key={item}>{item}</th>)}</tr>
            </thead>
            <tbody>
              {filtered.map((trade, index) => {
                const type = readText(trade, ["type"], "BUY");
                const result = readText(trade, ["result"], "");
                const pnl = readNumber(trade, ["pnl"], 0);
                return (
                  <tr key={readText(trade, ["id"], String(index))}>
                    <td>{index + 1}</td>
                    <td>{readText(trade, ["symbol"], "EURUSD")}</td>
                    <td><span className={`trade-type-pill ${type === "SELL" ? "sell" : "buy"}`}>{type}</span></td>
                    <td>{marketPriceText(readNumber(trade, ["entryPrice"], 0))}</td>
                    <td>{marketPriceText(readNumber(trade, ["exitPrice"], 0))}</td>
                    <td>{formatTradeTime(readText(trade, ["openTime"], ""))}</td>
                    <td>{formatTradeTime(readText(trade, ["closeTime"], ""))}</td>
                    <td>{readNumber(trade, ["lots"], 0).toFixed(2)}</td>
                    <td className={pnlClass(pnl)}>{money(pnl)}</td>
                    <td><span className={`result-pill ${result === "LOSS" ? "loss" : "win"}`}>{result || "WIN"}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="trade-history-empty">
          <strong>No trades recorded yet.</strong>
          <span>Trades will appear here automatically as validation closes positions.</span>
        </div>
      )}
      <div className="trade-history-summary">
        <span>Total Trades: {trades.length}</span>
        <span>Wins: {wins}</span>
        <span>Losses: {losses}</span>
        <span>Win Rate: {trades.length ? `${((wins / trades.length) * 100).toFixed(2)}%` : "-%"}</span>
        <span>Net P&L: {money(netPnl)}</span>
      </div>
    </section>
  );
}

function Round1Results({ data, trades }: { data: DashboardData; trades: ApiRecord[] }) {
  const [expanded, setExpanded] = useState(false);
  const [stored, setStored] = useState<ApiRecord | null>(() => {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(EURUSD_TEST_RESULTS_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as ApiRecord;
    } catch {
      return null;
    }
  });
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const config = asRecord(autoStatus?.config);
  const target = readNumber(session, ["target_closed_trades", "target_validation_trades"], readNumber(config, ["target_closed_trades", "target_validation_trades"], 30));
  const storedSummary = asRecord(stored?.summary);
  const storedTrades = Array.isArray(stored?.trades) ? (stored.trades.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const hasTrades = storedTrades.length > 0;
  useEffect(() => {
    if (!trades.length) return;
    const raw = window.localStorage.getItem(EURUSD_TEST_RESULTS_KEY);
    let existing: ApiRecord | null = null;
    if (raw) {
      try {
        existing = JSON.parse(raw) as ApiRecord;
      } catch {
        existing = null;
      }
    }
    const next = buildEurusdTestResults(existing, trades, session, target);
    window.localStorage.setItem(EURUSD_TEST_RESULTS_KEY, JSON.stringify(next));
    const timeout = window.setTimeout(() => setStored(next), 0);
    return () => window.clearTimeout(timeout);
  }, [session, target, trades]);
  return (
    <section className="round1-card">
      <div className="premium-test-header">
        <div>
          <p className="premium-section-eyebrow">EURUSD Test Results</p>
          <h2 className="premium-section-title">{hasTrades ? `${readNumber(storedSummary, ["closed"], 0)} closed trades captured` : "EURUSD test results"}</h2>
          {!hasTrades ? <p className="test-results-empty">Results are stored permanently and persist after page refresh.</p> : null}
        </div>
        <button className="portal-panel-tab" disabled={!hasTrades} onClick={() => setExpanded((value) => !value)} type="button">{hasTrades ? (expanded ? "Hide Trades" : "View Trades") : "No trades yet"}</button>
      </div>
      <div className="premium-stat-grid">
        <ClientMetric label="Target" value={hasTrades ? String(readNumber(stored, ["target"], target)) : "-"} compact />
        <ClientMetric label="Closed" value={hasTrades ? String(readNumber(storedSummary, ["closed"], 0)) : "-"} compact />
        <ClientMetric label="Win Rate" value={hasTrades ? `${readNumber(storedSummary, ["winRate"], 0).toFixed(2)}%` : "-"} compact />
        <ClientMetric label="Net P&L" value={hasTrades ? money(readNumber(storedSummary, ["netPnL"], 0)) : "-"} compact />
      </div>
      {expanded ? <EurusdTradeHistory trades={storedTrades} onClose={() => setExpanded(false)} /> : null}
    </section>
  );
}

function EurusdTradeHistory({ trades, onClose }: { trades: ApiRecord[]; onClose: () => void }) {
  return (
    <div className="test-trade-history">
      <div className="test-trade-history-header">
        <h3>Trade History - EURUSD</h3>
        <button onClick={onClose} type="button">Close x</button>
      </div>
      {trades.length ? (
        <div className="test-trade-table-wrap">
          <table className="test-trade-table">
            <thead>
              <tr>{["#", "Type", "Open", "Close", "Lots", "Entry", "Exit", "P&L"].map((item) => <th key={item}>{item}</th>)}</tr>
            </thead>
            <tbody>
              {trades.map((trade, index) => {
                const type = readText(trade, ["type"], "BUY");
                const pnl = readNumber(trade, ["pnl"], 0);
                return (
                  <tr key={readText(trade, ["id"], String(index))}>
                    <td>{index + 1}</td>
                    <td><span className={`trade-type-pill ${type === "SELL" ? "sell" : "buy"}`}>{type}</span></td>
                    <td>{formatTradeTime(readText(trade, ["openTime"], ""))}</td>
                    <td>{formatTradeTime(readText(trade, ["closeTime"], ""))}</td>
                    <td>{readNumber(trade, ["lots"], 0).toFixed(2)}</td>
                    <td>{marketPriceText(readNumber(trade, ["entryPrice"], 0))}</td>
                    <td>{marketPriceText(readNumber(trade, ["exitPrice"], 0))}</td>
                    <td className={pnlClass(pnl)}>{money(pnl)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="test-results-empty">No trades recorded yet</p>
      )}
    </div>
  );
}

function ClientDashboardLoadingView() {
  return (
    <div className="premium-dashboard-grid">
      <section className="premium-hero-card">
        <div className="premium-hero-content">
          <div>
            <h1 className="premium-hero-title">AI Multi-Market Trading</h1>
          </div>
          <ClientBadge text="Loading latest dashboard data" tone="warning" />
        </div>
      </section>
      <section className="premium-status-grid">
        {["Backend Status", "MT5 Status", "Validation Status", "Last Successful Sync"].map((label) => (
          <div className="premium-status-card" key={label}>
            <p className="premium-status-label">{label}</p>
            <div className="mt-4 h-4 animate-pulse rounded-full bg-blue-950/60" />
          </div>
        ))}
      </section>
      <section className="premium-test-environment">
        <div className="premium-test-header">
          <div>
            <p className="premium-section-eyebrow">Test Environment</p>
            <h2 className="premium-section-title">Preparing validation workspace</h2>
            <p className="premium-test-note">Round 2 controls and verification data will appear when the latest dashboard snapshot is ready.</p>
          </div>
          <strong className="premium-test-progress">--</strong>
        </div>
        <div className="premium-progress-track">
          <div className="premium-progress-fill" style={{ width: "0%" }} />
        </div>
      </section>
    </div>
  );
}

function Toast({ tone, message, onDismiss }: { tone: ToastState["tone"]; message: string; onDismiss: () => void }) {
  const icon = tone === "success" ? "✓" : tone === "error" ? "⚠" : "";
  const classes =
    tone === "success"
      ? "border-emerald-300/30 bg-emerald-400/15 text-emerald-50"
      : tone === "error"
        ? "border-rose-300/30 bg-rose-500/15 text-rose-50"
        : "border-blue-300/30 bg-blue-500/15 text-blue-50";
  return (
    <div className={`fixed left-4 right-4 top-20 z-50 mx-auto flex max-w-md items-center justify-between gap-4 rounded-2xl border px-4 py-3 text-sm font-black shadow-2xl backdrop-blur sm:left-auto sm:right-4 sm:mx-0 ${classes}`} role="status">
      <div className="flex min-w-0 items-center gap-3">
        {tone === "loading" ? <Spinner /> : <span className="shrink-0 text-base">{icon}</span>}
        <span className="min-w-0 break-words">{message}</span>
      </div>
      <button aria-label="Dismiss notification" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-blue-800/40 text-base leading-none text-blue-100/75 hover:bg-blue-900/35" onClick={onDismiss} type="button">
        ×
      </button>
    </div>
  );
}

function ClientDashboardView({
  backendConnected,
  data,
  closedTrades,
  exitManagementState,
  lastSuccessfulSync,
  lifecycleSyncState,
  loading,
  onAutoValidationAction,
  onRefresh,
  onSync,
  openFloatingPnl,
  scopedOpenPositions,
  showHero = true,
  todayPnl,
  workingAction,
}: {
  backendConnected: boolean;
  data: DashboardData;
  closedTrades: ApiRecord[];
  exitManagementState: { loading: boolean; message: string; error: string };
  lastSuccessfulSync: string | null;
  lifecycleSyncState: { loading: boolean; message: string; error: string };
  loading: boolean;
  onAutoValidationAction: (action: "start" | "pause" | "resume" | "stop" | "emergency-stop") => void;
  onRefresh: () => void;
  onSync: (action: "positions" | "lifecycle" | "exit-management") => void;
  openFloatingPnl: number;
  scopedOpenPositions: ApiRecord[];
  showHero?: boolean;
  todayPnl: number;
  workingAction: string | null;
}) {
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const config = asRecord(autoStatus?.config);
  const mt5Health = asRecord(autoStatus?.mt5_health);
  const exitManagement = asRecord(autoStatus?.exit_management);
  const target = readNumber(session, ["target_closed_trades", "target_validation_trades"], readNumber(config, ["target_closed_trades", "target_validation_trades"], 30));
  const closed = readNumber(session, ["current_closed_trades", "current_session_closed"], 0);
  const open = readNumber(session, ["current_open_trades", "current_session_open_trades"], scopedOpenPositions.length);
  const remaining = readNumber(session, ["remaining_closed_trades", "remaining_trades_to_target"], Math.max(0, target - closed));
  const progress = target > 0 ? Math.min(100, Math.round((closed / target) * 100)) : 0;
  const mode = readText(session, ["status"], "");
  const sessionNote = readText(session, ["session_note"], "");
  const allowedSymbols = Array.isArray(config?.allowed_symbols) ? config.allowed_symbols.map(String).join(", ") : "EURUSD";
  const sessionId = readText(session, ["session_id", "id", "validation_session_id"], "");
  const hasValidationSession = Boolean(sessionId || mode || closed > 0 || open > 0);
  const botState = clientBotState(mode, closed, open, target, hasValidationSession);
  const mt5HealthStatus = readText(mt5Health, ["status"], "").toUpperCase();
  const mt5Connected = mt5HealthStatus === "MT5_CONNECTED";
  const mt5ActuallyDisconnected = ["MT5_DISCONNECTED", "DISCONNECTED", "CONNECTION_FAILED", "WAITING_FOR_MT5_RECONNECT"].includes(mt5HealthStatus);
  const closeReports = Array.isArray(autoStatus?.validation_close_reports) ? (autoStatus.validation_close_reports.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const recentClosed = mergeClosedTrades(closedTrades, closeReports).slice(0, 5);
  const reasonRecords = useMemo(() => buildReasonMessages(data), [data]);
  const controlsDisabled = workingAction !== null;

  return (
    <div className="premium-dashboard-grid">
      {showHero ? <section className="premium-hero-card">
        <div className="premium-hero-content">
          <div>
            <h1 className="premium-hero-title">AI Multi-Market Trading</h1>
          </div>
          <div className="premium-badge-row">
            <ClientBadge text="Demo Mode" tone="healthy" />
            <ClientBadge text="Live Trading Disabled" tone="healthy" />
            <ClientBadge text={mt5Connected ? "MT5 Connected" : mt5ActuallyDisconnected ? "MT5 Disconnected" : "MT5 Checking"} tone={mt5Connected ? "healthy" : mt5ActuallyDisconnected ? "danger" : "warning"} />
            <ClientBadge text={`Bot ${botState.label}`} tone={botState.tone} />
          </div>
        </div>
      </section> : null}

      <section className="premium-status-grid">
        <StatusStripItem label="Backend Status" value={backendConnected ? "Connected" : "Reconnecting"} tone={backendConnected ? "healthy" : "warning"} />
        <StatusStripItem label="MT5 Status" value={mt5Connected ? "Connected" : mt5ActuallyDisconnected ? "Disconnected" : "Checking"} tone={mt5Connected ? "healthy" : mt5ActuallyDisconnected ? "danger" : "warning"} />
        <StatusStripItem label="Validation Status" value={botState.statusText} tone={botState.tone} />
        <StatusStripItem label="Last Successful Sync" value={lastSuccessfulSync ?? "Waiting for first sync"} tone={lastSuccessfulSync ? "healthy" : "warning"} />
      </section>

      <section className="premium-stat-grid">
        <ClientMetric label="Account Number" value={friendlyText(data.account, ["login"], "Connecting to MT5")} />
        <ClientMetric label="Balance" value={moneyOrWaiting(numeric(data.account, ["balance"]))} />
        <ClientMetric label="Equity" value={moneyOrWaiting(numeric(data.account, ["equity"]))} />
        <ClientMetric label="Floating P&L" value={money(openFloatingPnl)} valueClass={pnlClass(openFloatingPnl)} />
        <ClientMetric label="Open Positions" value={String(open)} />
        <ClientMetric label="Today's P&L" value={money(todayPnl)} valueClass={pnlClass(todayPnl)} />
      </section>

      <section className="premium-test-environment">
        <div className="premium-test-header">
          <div>
            <p className="premium-section-eyebrow">Test Environment</p>
            <h2 className="premium-section-title">{botState.statusText}</h2>
            <p className="premium-test-note">{closed} of {target} closed trades completed.</p>
            <p className="premium-test-note">{sessionNote || ROUND_2_NOTE}</p>
          </div>
          <strong className="premium-test-progress">{progress}%</strong>
        </div>
        <div className="premium-progress-track">
          <div className="premium-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="premium-sub-grid">
          <div className="premium-sub-card">
            <p className="premium-section-eyebrow">Round 2 validation</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <ClientMetric label="Target Closed Trades" value={String(target)} compact />
              <ClientMetric label="Closed Trades" value={String(closed)} compact />
              <ClientMetric label="Remaining Trades" value={String(remaining)} compact />
              <ClientMetric label="Open Trades" value={String(open)} compact />
              <ClientMetric label="Validation Symbols" value={allowedSymbols} compact />
            </div>
          </div>
          <div className="premium-sub-card">
            <ClientSectionTitle eyebrow="Controls" title="Validation actions" />
            <div className="premium-control-grid mt-5">
              <ClientButton disabled={controlsDisabled || ["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode)} loading={workingAction === "auto-validation-start"} onClick={() => onAutoValidationAction("start")}>Start Validation</ClientButton>
              <ClientButton disabled={controlsDisabled || !["PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} loading={workingAction === "auto-validation-resume"} onClick={() => onAutoValidationAction("resume")}>Resume Validation</ClientButton>
              <ClientButton disabled={controlsDisabled || !["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode)} loading={workingAction === "auto-validation-pause"} onClick={() => onAutoValidationAction("pause")}>Pause</ClientButton>
              <ClientButton disabled={controlsDisabled || !["RUNNING", "PAUSED", "WAITING_FOR_MT5_RECONNECT", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} loading={workingAction === "auto-validation-stop"} onClick={() => onAutoValidationAction("stop")}>Stop</ClientButton>
              <ClientButton danger disabled={controlsDisabled || !["RUNNING", "PAUSED", "WAITING_FOR_MT5_RECONNECT", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} loading={workingAction === "auto-validation-emergency-stop"} onClick={() => onAutoValidationAction("emergency-stop")}>Emergency Stop</ClientButton>
              <ClientButton disabled={controlsDisabled} loading={workingAction === "dashboard-refresh"} onClick={onRefresh}>Refresh</ClientButton>
              <ClientButton disabled={controlsDisabled || lifecycleSyncState.loading} loading={lifecycleSyncState.loading} onClick={() => onSync("lifecycle")}>Sync Lifecycle</ClientButton>
              <ClientButton disabled={controlsDisabled || exitManagementState.loading} loading={exitManagementState.loading} onClick={() => onSync("exit-management")}>Run Exit Management</ClientButton>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
        <div className="premium-panel">
          <p className="premium-section-eyebrow">Performance summary</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <ClientMetric label="Wins" value={String(readNumber(session, ["wins"], 0))} valueClass="text-emerald-200" compact />
            <ClientMetric label="Losses" value={String(readNumber(session, ["losses"], 0))} valueClass="text-rose-200" compact />
            <ClientMetric label="Win Rate" value={`${readNumber(session, ["win_rate"], 0).toFixed(2)}%`} compact />
            <ClientMetric label="Net P&L" value={money(readNumber(session, ["net_pnl"], 0))} valueClass={pnlClass(readNumber(session, ["net_pnl"], 0))} compact />
            <ClientMetric label="Profit Factor" value={readNumber(session, ["profit_factor"], 0).toFixed(2)} compact />
            <ClientMetric label="Max Drawdown" value={money(readNumber(session, ["max_drawdown"], 0))} compact />
          </div>
        </div>
        <ValidationReasonPanel messages={reasonRecords} />
      </section>

      <section className="premium-table-panel">
        <ClientSectionTitle eyebrow="Active Positions" title="Open Demo Trades" />
        {scopedOpenPositions.length ? <ClientOpenPositionsTable positions={scopedOpenPositions} managedPositions={Array.isArray(exitManagement?.managed_positions) ? (exitManagement.managed_positions.filter((item) => asRecord(item)) as ApiRecord[]) : []} /> : <EmptyState text="No Active Positions" />}
      </section>

      <section className="premium-table-panel">
        <ClientSectionTitle eyebrow="Recent Closed Trades" title="Latest 5 Outcomes" />
        {recentClosed.length ? <ClientClosedTradesTable trades={recentClosed} /> : <EmptyState text={hasValidationSession ? "No Closed Trades Yet" : "Validation Not Started"} />}
      </section>

      {mt5ActuallyDisconnected ? (
        <div className="rounded-2xl border border-amber-300/25 bg-amber-400/10 p-4 text-sm font-bold text-amber-100">MT5 is disconnected. Last successful dashboard data remains visible.</div>
      ) : null}
    </div>
  );
}

function ClientBadge({ text, tone }: { text: string; tone: "healthy" | "warning" | "danger" }) {
  return <span className={`premium-badge ${tone}`}>{text}</span>;
}

function StatusStripItem({ label, value, tone }: { label: string; value: string; tone: "healthy" | "warning" | "danger" }) {
  return (
    <div className="premium-status-card">
      <p className="premium-status-label">{label}</p>
      <div className="premium-status-value">
        <span className={`premium-status-dot ${tone}`} />
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function ClientMetric({ label, value, valueClass = "text-white", compact = false }: { label: string; value: string; valueClass?: string; compact?: boolean }) {
  return (
    <div className={`premium-metric-card ${compact ? "compact" : ""}`}>
      <p className="premium-metric-label">{label}</p>
      <strong className={`premium-metric-value ${valueClass}`}>{value}</strong>
    </div>
  );
}

function ClientSectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="premium-section-eyebrow">{eyebrow}</p>
      <h2 className="premium-section-title">{title}</h2>
    </div>
  );
}

function ClientButton({ children, danger = false, disabled, loading, onClick }: { children: React.ReactNode; danger?: boolean; disabled?: boolean; loading?: boolean; onClick: () => void }) {
  return (
    <button className={`premium-button ${danger ? "danger" : ""}`} disabled={disabled || loading} onClick={onClick} type="button">
      {loading ? <Spinner /> : null}
      <span>{loading ? "Working..." : children}</span>
    </button>
  );
}

function Spinner() {
  return <span aria-hidden="true" className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent" />;
}

function ActionState({ label, state }: { label: string; state: { loading: boolean; message: string; error: string } }) {
  const text = state.loading ? "In Progress" : state.error || state.message || "Ready";
  return <p className={state.error ? "text-rose-200" : state.message ? "text-emerald-200" : "text-slate-400"}>{label}: {text}</p>;
}

function ClientOpenPositionsTable({ positions, managedPositions }: { positions: ApiRecord[]; managedPositions: ApiRecord[] }) {
  return (
    <div className="premium-table-wrap">
      <table className="premium-table">
        <thead>
          <tr>{["Symbol", "Direction", "Entry Price", "Current Price", "P&L", "Stop Loss", "Take Profit", "Trade Age", "Exit Status"].map((item) => <th className="px-4 py-2" key={item}>{item}</th>)}</tr>
        </thead>
        <tbody>
          {positions.map((position, index) => {
            const ticket = readText(position, ["ticket"], "");
            const managed = managedPositions.find((item) => readText(item, ["ticket"], "") === ticket) ?? null;
            const pnl = readNumber(position, ["floating_pnl", "profit"], 0);
            return (
              <tr key={`${ticket || index}-${index}`}>
                <td>{friendlyText(position, ["symbol"], "Waiting for Data")}</td>
                <td>{friendlyText(position, ["side", "type"], "Waiting")}</td>
                <td>{marketNumber(readNumber(position, ["entry_price", "price_open"], Number.NaN))}</td>
                <td>{marketNumber(readNumber(position, ["current_price", "price_current"], Number.NaN))}</td>
                <td className={pnlClass(pnl)}>{money(pnl)}</td>
                <td>{marketNumber(readNumber(position, ["stop_loss", "sl"], Number.NaN))}</td>
                <td>{marketNumber(readNumber(position, ["take_profit", "tp"], Number.NaN))}</td>
                <td>{formatDuration(readNumber(managed, ["age_minutes"], readNumber(position, ["age_minutes"], Number.NaN)))}</td>
                <td>{friendlyText(managed, ["exit_reason", "action"], "Monitoring")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ClientClosedTradesTable({ trades }: { trades: ApiRecord[] }) {
  return (
    <div className="premium-table-wrap">
      <table className="premium-table">
        <thead>
          <tr>{["Symbol", "Direction", "Result", "P&L", "Exit Reason", "Closed Time"].map((item) => <th className="px-4 py-2" key={item}>{item}</th>)}</tr>
        </thead>
        <tbody>
          {trades.map((trade, index) => {
            const pnl = readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl", "pnl"], 0);
            return (
              <tr key={`${readText(trade, ["trade_id", "mt5_ticket", "ticket"], String(index))}-${index}`}>
                <td>{friendlyText(trade, ["symbol"], "Waiting")}</td>
                <td>{friendlyText(trade, ["side"], "Waiting")}</td>
                <td>{friendlyText(trade, ["result"], "Closed")}</td>
                <td className={pnlClass(pnl)}>{money(pnl)}</td>
                <td>{friendlyText(trade, ["exit_reason"], "Closed")}</td>
                <td>{formatTradeTime(readText(trade, ["closed_at", "close_time"], ""))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function friendlyText(record: ApiRecord | null, paths: string[], fallback: string): string {
  const value = readText(record, paths, "");
  return value && value !== "Unavailable" ? value : fallback;
}

function recordOrPrevious(value: unknown, previous: ApiRecord | null): ApiRecord | null {
  const next = asRecord(value);
  return next && Object.keys(next).length > 0 ? next : previous;
}

function recordsOrPrevious(value: unknown, key: string, previous: ApiRecord[], fullSuccess: boolean): ApiRecord[] {
  const next = recordsFrom(value, key);
  return next.length || fullSuccess || previous.length === 0 ? next : previous;
}

function arrayRecordsOrPrevious(value: unknown, previous: ApiRecord[], fullSuccess: boolean): ApiRecord[] {
  const next = Array.isArray(value) ? (value.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  return next.length || fullSuccess || previous.length === 0 ? next : previous;
}

function mergeClosedTrades(journalTrades: ApiRecord[], closeReports: ApiRecord[]): ApiRecord[] {
  const merged: ApiRecord[] = [];
  const seen = new Set<string>();
  for (const trade of [...closeReports, ...journalTrades]) {
    const key = readText(trade, ["mt5_ticket", "ticket", "trade_id"], "") || JSON.stringify(trade);
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(trade);
  }
  return merged.sort((a, b) => {
    const aTime = new Date(readText(a, ["closed_at", "close_time", "generated_at"], "")).getTime();
    const bTime = new Date(readText(b, ["closed_at", "close_time", "generated_at"], "")).getTime();
    return (Number.isFinite(bTime) ? bTime : 0) - (Number.isFinite(aTime) ? aTime : 0);
  });
}

function moneyOrWaiting(value: number): string {
  return Number.isFinite(value) ? money(value) : "Waiting for Data";
}

function clientBotState(mode: string, closed: number, open: number, target: number, hasValidationSession: boolean): { label: string; statusText: string; tone: "healthy" | "warning" | "danger" } {
  if (closed >= target && target > 0) return { label: "Completed", statusText: "Validation Completed", tone: "healthy" };
  if (mode === "RUNNING") return { label: "Running", statusText: open > 0 ? "Waiting for Open Trades to Close" : "Validation in Progress", tone: "healthy" };
  if (["PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED", "WAITING_FOR_MT5_RECONNECT"].includes(mode)) return { label: "Paused", statusText: "Validation Paused", tone: "warning" };
  if (mode === "COMPLETED") return { label: "Completed", statusText: "Validation Completed", tone: "healthy" };
  if (hasValidationSession) return { label: "Stopped", statusText: "Validation Progress Available", tone: "warning" };
  return { label: "Stopped", statusText: "Validation Not Started", tone: "warning" };
}

function autoValidationLoadingMessage(action: "start" | "pause" | "resume" | "stop" | "emergency-stop"): string {
  return action === "start"
    ? "Starting validation..."
    : action === "resume"
      ? "Resuming validation..."
      : action === "pause"
        ? "Pausing validation..."
        : action === "stop"
          ? "Stopping validation..."
          : "Sending emergency stop...";
}

function autoValidationSuccessMessage(action: "start" | "pause" | "resume" | "stop" | "emergency-stop"): string {
  return action === "start"
    ? "Validation started successfully"
    : action === "resume"
      ? "Validation resumed successfully"
      : action === "pause"
        ? "Validation paused successfully"
        : action === "stop"
          ? "Validation stopped successfully"
          : "Emergency stop sent successfully";
}

function autoValidationErrorMessage(action: "start" | "pause" | "resume" | "stop" | "emergency-stop"): string {
  return action === "start"
    ? "Failed to start validation"
    : action === "resume"
      ? "Failed to resume validation"
      : action === "pause"
        ? "Failed to pause validation"
        : action === "stop"
          ? "Failed to stop validation"
          : "Failed to send emergency stop";
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">{eyebrow}</p>
      <h2 className="mt-1 text-2xl font-black">{title}</h2>
    </div>
  );
}

function Metric({ label, value, valueClass = "text-white", compact = false }: { label: string; value: string; valueClass?: string; compact?: boolean }) {
  return (
    <div className={`rounded-xl border border-slate-800 bg-[#0F172A] ${compact ? "p-3" : "p-4"}`}>
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <strong className={`mt-2 block break-words ${compact ? "text-base" : "text-xl"} ${valueClass}`}>{value}</strong>
    </div>
  );
}

type ReasonMessage = { id: string; reason: string; status: "Accepted" | "Rejected" | "Waiting" | "Error"; symbol: string; timestamp: string };

function buildReasonMessages(data: DashboardData): ReasonMessage[] {
  const messages: ReasonMessage[] = [];
  for (const signal of data.clientSignals) {
    const statusText = readText(signal, ["execution_status", "status_level", "risk_status"], "Waiting").toUpperCase();
    const status: ReasonMessage["status"] = statusText.includes("APPROVED") || statusText.includes("READY") ? "Accepted" : statusText.includes("BLOCK") || statusText.includes("REJECT") || statusText.includes("DENIED") ? "Rejected" : "Waiting";
    const symbol = readText(signal, ["symbol"], "EURUSD");
    const reason = readText(signal, ["setup_reason", "reason", "what_needs_to_happen_next"], status === "Accepted" ? "Strategy and risk checks confirmed this setup." : "Waiting for strategy, market, and risk checks to confirm.");
    const timestamp = readText(signal, ["timestamp", "created_at", "updated_at"], "1970-01-01T00:00:00.000Z");
    messages.push({ id: `signal-${symbol}-${timestamp}-${reason}`, reason, status, symbol, timestamp });
    const blockers = cleanBlockers(signal.blocked_reasons ?? signal.missing_requirements);
    blockers.forEach((blocker, index) => {
      messages.push({ id: `blocker-${symbol}-${timestamp}-${index}-${blocker}`, reason: blocker, status: "Rejected", symbol, timestamp });
    });
  }
  const autoStatus = asRecord(data.autoValidation);
  const reports = Array.isArray(autoStatus?.validation_close_reports) ? (autoStatus.validation_close_reports.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  reports.forEach((report, index) => {
    const pnl = readNumber(report, ["net_pnl", "profit_loss", "pnl"], 0);
    messages.push({
      id: `report-${readText(report, ["mt5_ticket", "ticket"], String(index))}`,
      reason: friendlyText(report, ["exit_reason", "reason", "close_reason"], pnl >= 0 ? "Trade closed with accepted validation outcome." : "Trade closed after validation/risk management."),
      status: pnl >= 0 ? "Accepted" : "Rejected",
      symbol: friendlyText(report, ["symbol"], "EURUSD"),
      timestamp: readText(report, ["closed_at", "generated_at", "timestamp"], "1970-01-01T00:00:00.000Z"),
    });
  });
  if (!messages.length) {
    messages.push({ id: "waiting-default", reason: "Waiting for the next strategy decision. Accepted or rejected trade reasons will remain here once generated.", status: "Waiting", symbol: "EURUSD", timestamp: "1970-01-01T00:00:00.000Z" });
  }
  return messages;
}

function readStoredReasons(): ReasonMessage[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(REASON_MESSAGES_KEY) ?? "[]") as ReasonMessage[];
  } catch {
    return [];
  }
}

function ValidationReasonPanel({ messages }: { messages: ReasonMessage[] }) {
  const [storedMessages, setStoredMessages] = useState<ReasonMessage[]>(() => readStoredReasons());
  useEffect(() => {
    const merged = [...messages, ...readStoredReasons()];
    const byId = new Map<string, ReasonMessage>();
    merged.forEach((message) => byId.set(message.id, message));
    const next = Array.from(byId.values()).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).slice(0, 50);
    window.localStorage.setItem(REASON_MESSAGES_KEY, JSON.stringify(next));
    setStoredMessages(next);
  }, [messages]);
  return (
    <div className="premium-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="premium-section-eyebrow">Reason</p>
          <p className="premium-metric-value text-white">Bot Decisions</p>
        </div>
        <p className="premium-metric-label">{storedMessages.length} messages</p>
      </div>
      {storedMessages.length > 0 ? (
        <div className="reason-message-list">
          {storedMessages.slice(0, 8).map((message) => (
            <article className="reason-message" key={message.id}>
              <div>
                <span className={`reason-status ${message.status.toLowerCase()}`}>{message.status}</span>
                <strong>{message.symbol}</strong>
              </div>
              <p>{message.reason}</p>
              <time>{formatTradeTime(message.timestamp)}</time>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState text="Waiting for validation reasons" />
      )}
    </div>
  );
}

function ExecutionModePanel({
  mode,
  nowMs,
  workingAction,
  onApprove,
  onReject,
  onSetMode,
}: {
  mode: ApiRecord | null;
  nowMs: number;
  workingAction: string | null;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onSetMode: (mode: "AUTO" | "APPROVAL") => void;
}) {
  const config = asRecord(mode?.config);
  const executionMode = readText(config, ["execution_mode"], readText(mode, ["execution_mode"], "APPROVAL")) as "AUTO" | "APPROVAL";
  const pending = Array.isArray(mode?.pending_approvals) ? (mode.pending_approvals.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const safety = asRecord(mode?.safety_flags);
  const blockedAutoAttempts = Array.isArray(mode?.blocked_auto_attempts) ? (mode.blocked_auto_attempts.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const lastAuto = asRecord(mode?.last_auto_executed_signal);
  const allowedSymbols = Array.isArray(safety?.allowed_symbols) ? safety.allowed_symbols.join(", ") : "EURUSD, XAUUSD";
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <SectionTitle eyebrow="Execution Mode" title={`Current Mode: ${executionMode}`} />
        <div className="flex flex-wrap gap-2">
          <button className={`rounded-xl px-4 py-2 text-sm font-black ${executionMode === "APPROVAL" ? "bg-emerald-500 text-slate-950" : "border border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800"}`} disabled={workingAction !== null} onClick={() => onSetMode("APPROVAL")} type="button">
            Approval Mode
          </button>
          <button className={`rounded-xl px-4 py-2 text-sm font-black ${executionMode === "AUTO" ? "bg-amber-400 text-slate-950" : "border border-amber-400/30 bg-amber-500/10 text-amber-100 hover:bg-amber-500/20"}`} disabled={workingAction !== null} onClick={() => onSetMode("AUTO")} type="button">
            Auto Mode
          </button>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Demo Only" value={readText(safety, ["demo_only"], "true") === "true" ? "Yes" : "No"} compact />
        <Metric label="Live Trading" value={readText(config, ["live_execution_enabled"], "false") === "true" ? "Enabled" : "Disabled"} valueClass="text-emerald-300" compact />
        <Metric label="Broker Execution" value={readText(config, ["broker_execution_enabled"], "false") === "true" ? "Enabled" : "Disabled"} valueClass="text-emerald-300" compact />
        <Metric label="Max Lot" value={String(readNumber(config, ["max_lot_per_trade"], 0.01))} compact />
        <Metric label="Allowed Symbols" value={allowedSymbols} compact />
      </div>
      {executionMode === "AUTO" ? (
        <div className="mt-4 rounded-xl border border-amber-400/25 bg-amber-500/10 p-4">
          <p className="text-sm font-black uppercase tracking-[0.16em] text-amber-200">Auto Mode Active</p>
          <p className="mt-2 text-sm font-bold text-amber-50">Ready approved signals are revalidated and sent only through the guarded demo sender. Live and broker execution remain disabled.</p>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <Metric label="Last Auto Signal" value={lastAuto ? `${readText(lastAuto, ["symbol"], "Signal")} ${readText(lastAuto, ["signal_hash"], "")}` : "None yet"} compact />
            <Metric label="Blocked Auto Attempts" value={String(blockedAutoAttempts.length)} compact />
          </div>
          {blockedAutoAttempts.length > 0 && (
            <div className="mt-3 grid gap-2">
              {blockedAutoAttempts.slice(0, 3).map((item, index) => (
                <p className="rounded-lg border border-amber-400/20 bg-[#0F172A] px-3 py-2 text-xs font-bold text-amber-100" key={`${readText(item, ["signal_hash"], "blocked")}-${index}`}>
                  {readText(item, ["event"], "BLOCKED")} {readText(item, ["symbol"], "")}: {Array.isArray(asRecord(item.details)?.blockers) ? (asRecord(item.details)?.blockers as unknown[]).join(", ") : "See audit history."}
                </p>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Pending Approvals</p>
          {pending.length === 0 ? (
            <EmptyState text="No signals are pending manual approval." />
          ) : (
            <div className="mt-3 grid gap-3">
              {pending.map((approval) => {
                const signal = asRecord(approval.signal);
                const approvalId = readText(approval, ["approval_id"], "");
                const expiresAt = new Date(readText(approval, ["expires_at"], ""));
                const remaining = Number.isNaN(expiresAt.getTime()) ? 0 : Math.max(0, Math.ceil((expiresAt.getTime() - nowMs) / 1000));
                return (
                  <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4" key={approvalId}>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <p className="text-xs font-black uppercase tracking-[0.16em] text-amber-200">Pending Approval</p>
                        <h3 className="mt-1 text-xl font-black text-white">
                          {readText(approval, ["symbol"], readText(signal, ["symbol"], "Signal"))} {readText(approval, ["action"], readText(signal, ["signal"], ""))}
                        </h3>
                        <p className="mt-1 text-sm font-bold text-slate-400">Expires in {remaining}s</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-slate-950 disabled:bg-slate-700 disabled:text-slate-400" disabled={!approvalId || workingAction !== null || remaining <= 0} onClick={() => onApprove(approvalId)} type="button">
                          Approve
                        </button>
                        <button className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-2 text-sm font-black text-rose-100 disabled:border-slate-700 disabled:text-slate-500" disabled={!approvalId || workingAction !== null} onClick={() => onReject(approvalId)} type="button">
                          Reject
                        </button>
                      </div>
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                      <Metric label="Entry" value={marketNumber(readNumber(approval, ["entry"], Number.NaN), readText(approval, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
                      <Metric label="SL" value={marketNumber(readNumber(approval, ["stop_loss"], Number.NaN), readText(approval, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
                      <Metric label="TP" value={marketNumber(readNumber(approval, ["take_profit"], Number.NaN), readText(approval, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
                      <Metric label="RR" value={`${readNumber(approval, ["risk_reward"], 0).toFixed(2)}:1`} compact />
                      <Metric label="Confidence" value={percent(readNumber(approval, ["confidence"], Number.NaN))} compact />
                      <Metric label="Broker" value={readText(approval, ["broker"], "VANTAGE_DEMO")} compact />
                    </div>
                    <p className="mt-3 text-xs font-bold text-slate-500">Account: {readText(asRecord(approval.account), ["account_login"], "Unavailable")}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function AutoValidationPanel({
  status,
  nowMs,
  pollError,
  workingAction,
  onAction,
}: {
  status: ApiRecord | null;
  nowMs: number;
  pollError: string;
  workingAction: string | null;
  onAction: (action: "start" | "pause" | "resume" | "stop" | "emergency-stop") => void;
}) {
  const session = asRecord(status?.session);
  const config = asRecord(status?.config);
  const watched = asRecord(status?.current_signal_watched);
  const decision = asRecord(status?.last_execution_decision);
  const watchedAudit = asRecord(watched?.approval_audit ?? decision?.approval_audit);
  const mode = readText(session, ["status"], "OFF");
  const recoverableSession = readText(status, ["recoverable_session"], "false") === "true";
  const recoveredSessionId = readText(status, ["recovered_session_id"], "");
  const recoveredClosedTrades = readNumber(status, ["recovered_closed_trades"], 0);
  const recoveredOpenTrades = readNumber(status, ["recovered_open_trades"], 0);
  const blockers = Array.isArray(status?.blocked_reasons) ? status.blocked_reasons.map(String) : [];
  const nextEligible = readText(status, ["next_eligible_time"], "");
  const runnerActive = readText(status, ["runner_active"], "false") === "true";
  const runnerError = readText(status, ["last_runner_error"], "");
  const watchedSymbols = Array.isArray(decision?.watched_symbols) ? decision.watched_symbols.map(String) : Array.isArray(config?.allowed_symbols) ? config.allowed_symbols.map(String) : ["EURUSD", "XAUUSD"];
  const perSymbolResults = asRecord(decision?.per_symbol_results);
  const eurusdCheck = asRecord(perSymbolResults?.EURUSD ?? decision?.EURUSD);
  const xauusdCheck = asRecord(perSymbolResults?.XAUUSD ?? decision?.XAUUSD);
  const mt5Health = asRecord(status?.mt5_health ?? decision?.mt5_health);
  const hashAudit = asRecord(status?.last_hash_change_audit ?? decision?.last_hash_change_audit);
  const senderRejection = asRecord(status?.last_sender_rejection ?? decision?.last_sender_rejection);
  const duplicateCheck = asRecord(status?.last_duplicate_check ?? decision?.last_duplicate_check);
  const openPositionSync = asRecord(status?.open_position_sync);
  const lifecycleSync = asRecord(status?.lifecycle_sync);
  const latestCloseReport = asRecord(status?.latest_validation_close_report ?? lifecycleSync?.latest_validation_close_report);
  const exitManagement = asRecord(status?.exit_management);
  const managedExitPositions = Array.isArray(exitManagement?.managed_positions) ? (exitManagement.managed_positions.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const lastExitAction = asRecord(exitManagement?.last_action);
  const lastFailedExitAction = asRecord(exitManagement?.last_failed_action);
  const currentSessionPositionsBySymbol = asRecord(openPositionSync?.current_session_open_positions_by_symbol);
  const currentSessionPositionsText = currentSessionPositionsBySymbol
    ? Object.entries(currentSessionPositionsBySymbol).map(([symbol, count]) => `${symbol}: ${String(count)}`).join(", ") || "None"
    : "None";
  const executionTimeline = asRecord(decision?.execution_timeline ?? asRecord(status?.post_sender_execution_summary)?.latest_timeline);
  const senderResult = asRecord(decision?.sender_result);
  const hashChangedFields = Array.isArray(hashAudit?.changed_fields) ? (hashAudit.changed_fields.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const hashEvent = readText(hashAudit, ["event"], readText(hashAudit, ["minor_change"], "false") === "true" ? "HASH_CHANGE_MINOR" : "No hash change");
  const confidenceTimeline = Array.isArray(status?.confidence_timeline)
    ? []
    : Array.isArray(asRecord(status?.confidence_timeline)?.XAUUSD)
      ? ((asRecord(status?.confidence_timeline)?.XAUUSD as unknown[]).filter((item) => asRecord(item)) as ApiRecord[])
      : Array.isArray(decision?.xauusd_confidence_timeline)
        ? (decision.xauusd_confidence_timeline.filter((item) => asRecord(item)) as ApiRecord[])
        : [];
  const lastCheckedSymbol = readText(decision, ["last_checked_symbol"], "None");
  const bestCandidateSymbol = readText(decision, ["best_candidate_symbol"], "None");
  const noQualifiedReason = readText(decision, ["no_qualified_reason"], "Waiting for the next validation scan.");
  const lastDisconnectAt = readText(session, ["last_mt5_disconnect_at"], "");
  const reconnectAttempts = readNumber(session, ["mt5_reconnect_attempts"], 0);
  const reconnectTimeout = readNumber(config, ["mt5_disconnect_timeout_seconds"], 600);
  const reconnectElapsed = lastDisconnectAt ? Math.max(0, Math.floor((nowMs - new Date(lastDisconnectAt).getTime()) / 1000)) : 0;
  const reconnectRemaining = lastDisconnectAt ? Math.max(0, reconnectTimeout - reconnectElapsed) : reconnectTimeout;
  const activeStrategyProfile = readText(config, ["strategy_profile"], readText(status, ["strategy_profile"], "AUTO_VALIDATION"));
  const slTpSource = readText(watched, ["sl_tp_source"], readText(watchedAudit, ["sl_tp_source"], "Unknown"));
  const relaxedBlockers = Array.isArray(watchedAudit?.relaxed_blockers)
    ? watchedAudit.relaxed_blockers.map((item) => readText(asRecord(item), ["code"], String(item))).filter(Boolean)
    : Array.isArray(watchedAudit?.advisory_requirements)
      ? watchedAudit.advisory_requirements.map((item) => readText(asRecord(item), ["code"], String(item))).filter(Boolean)
      : [];
  const totalTrades = readNumber(session, ["total_trades"], readNumber(session, ["current_closed_trades"], 0) + readNumber(session, ["current_open_trades"], 0));
  const targetValidationTrades = readNumber(session, ["target_validation_trades"], readNumber(config, ["target_validation_trades", "target_closed_trades"], 30));
  const remainingTrades = readNumber(session, ["remaining_trades_to_target"], Math.max(0, targetValidationTrades - readNumber(session, ["current_closed_trades"], 0)));
  const wins = readNumber(session, ["wins"], 0);
  const losses = readNumber(session, ["losses"], 0);
  const netPnl = readNumber(session, ["net_pnl"], 0);
  const reasonMessages = buildReasonMessages({ ...emptyData, autoValidation: status });
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <SectionTitle eyebrow="AUTO Demo Validation" title={`30-Trade Bot Test: ${mode === "IDLE" ? "OFF" : mode}`} />
        <div className="flex flex-wrap gap-2">
          <button className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-slate-950 disabled:bg-slate-700 disabled:text-slate-400" disabled={workingAction !== null || ["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode)} onClick={() => onAction(recoverableSession ? "resume" : "start")} type="button">
            {recoverableSession ? "Resume Validation" : "Start 30-Trade Validation"}
          </button>
          {recoverableSession ? (
            <button className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm font-bold text-amber-100 disabled:text-slate-500" disabled={workingAction !== null || ["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode)} onClick={() => onAction("start")} type="button">
              Start Fresh
            </button>
          ) : null}
          <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode)} onClick={() => onAction("pause")} type="button">
            Pause
          </button>
          <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 disabled:text-slate-500" disabled={workingAction !== null || !["PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} onClick={() => onAction("resume")} type="button">
            Resume
          </button>
          <button className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm font-bold text-amber-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "PAUSED", "WAITING_FOR_MT5_RECONNECT", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} onClick={() => onAction("stop")} type="button">
            Stop
          </button>
          <button className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-4 py-2 text-sm font-black text-rose-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "PAUSED", "WAITING_FOR_MT5_RECONNECT", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} onClick={() => onAction("emergency-stop")} type="button">
            Emergency Stop
          </button>
        </div>
      </div>

      {recoverableSession ? (
        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3 text-sm font-bold text-amber-100">
          Recovered validation session {recoveredSessionId || "available"}: {recoveredClosedTrades} closed, {recoveredOpenTrades} open. Runner is inactive until you resume.
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <Metric label="Target Closed Trades" value={String(targetValidationTrades)} compact />
        <Metric label="Remaining Closed Trades" value={String(remainingTrades)} compact />
        <Metric label="Closed Trades" value={String(readNumber(session, ["current_closed_trades", "current_session_closed"], 0))} compact />
        <Metric label="Open Trades" value={String(readNumber(session, ["current_open_trades"], 0))} compact />
        <Metric label="Open Trade Limit" value={String(readNumber(config, ["max_open_trades_total"], 0))} compact />
        <Metric label="Per-Symbol Limit" value={String(readNumber(config, ["max_open_trades_per_symbol"], 0))} compact />
        <Metric label="Daily Demo Trades" value={`${readNumber(session, ["daily_demo_trade_count"], 0)} / ${readNumber(config, ["max_daily_demo_trades", "max_daily_trades"], 30)}`} compact />
        <Metric label="Wins / Losses" value={`${readNumber(session, ["wins"], 0)} / ${readNumber(session, ["losses"], 0)}`} compact />
        <Metric label="Win Rate" value={`${readNumber(session, ["win_rate"], 0).toFixed(2)}%`} compact />
        <Metric label="Net P&L" value={money(readNumber(session, ["net_pnl"], 0))} valueClass={pnlClass(readNumber(session, ["net_pnl"], 0))} compact />
        <Metric label="Max Drawdown" value={money(readNumber(session, ["max_drawdown"], 0))} compact />
        <Metric label="Lot" value={String(readNumber(config, ["lot_size"], 0.01))} compact />
        <Metric label="Allowed Symbols" value={Array.isArray(config?.allowed_symbols) ? config.allowed_symbols.join(", ") : "XAUUSD, EURUSD"} compact />
        <Metric label="Watching" value={watchedSymbols.join(" + ")} compact />
        <Metric label="Strategy Profile" value={activeStrategyProfile} valueClass="text-blue-200" compact />
        <Metric label="Session Started By" value={readText(session, ["session_started_by"], "Not started")} compact />
        <Metric label="Recovered Session ID" value={recoveredSessionId || "None"} compact />
        <Metric label="Recovered Closed" value={String(recoveredClosedTrades)} compact />
        <Metric label="Recovered Open" value={String(recoveredOpenTrades)} compact />
        <Metric label="Session Start Time" value={formatTradeTime(readText(session, ["session_start_time", "started_at"], ""))} compact />
        <Metric label="Current Session Opened" value={String(readNumber(session, ["current_session_opened", "opened", "orders_created"], 0))} compact />
        <Metric label="Current Session Closed" value={String(readNumber(session, ["current_session_closed", "current_closed_trades"], 0))} compact />
        <Metric label="Historical/Unowned MT5" value={String(readNumber(openPositionSync, ["historical_unowned_open_positions", "unmatched_open_positions"], 0))} valueClass={readNumber(openPositionSync, ["historical_unowned_open_positions", "unmatched_open_positions"], 0) > 0 ? "text-amber-200" : "text-slate-100"} compact />
        <Metric label="SL/TP Source" value={slTpSource} valueClass={slTpSource === "DEMO_RISK_FALLBACK" ? "text-amber-200" : "text-emerald-300"} compact />
        <Metric label="Advisory Blockers" value={relaxedBlockers.length ? relaxedBlockers.join(", ") : "None"} compact />
        <Metric label="Cooldown" value={`${readNumber(config, ["cooldown_after_trade_minutes"], 15)}m`} compact />
        <Metric label="Next Eligible" value={nextEligible ? formatTradeTime(nextEligible) : "Now"} compact />
        <Metric label="Safety" value="Demo / Vantage Only" valueClass="text-emerald-300" compact />
        <Metric label="Runner" value={runnerActive ? "Active" : "Inactive"} valueClass={runnerActive ? "text-emerald-300" : "text-slate-400"} compact />
        <Metric label="Last Scan Time" value={formatTradeTime(readText(status, ["runner_last_tick_at"], ""))} compact />
        <Metric label="Next Scan Time" value={formatTradeTime(readText(status, ["runner_next_tick_at"], ""))} compact />
        <Metric label="Scan Interval" value={`${readNumber(status, ["runner_interval_seconds"], 3)}s`} compact />
        <Metric label="Run In Progress" value={readText(status, ["run_once_in_progress"], "false") === "true" ? "Yes" : "No"} compact />
        <Metric label="Last Duration" value={`${readNumber(status, ["last_run_once_duration_ms"], 0)}ms`} compact />
        <Metric label="MT5 Health" value={readText(mt5Health, ["status"], "Unknown")} valueClass={readText(mt5Health, ["status"], "") === "MT5_CONNECTED" ? "text-emerald-300" : "text-amber-200"} compact />
        <Metric label="Health Failures" value={String(readNumber(mt5Health, ["consecutive_failed_health_checks"], 0))} compact />
        <Metric label="Last Tick Symbol" value={readText(mt5Health, ["last_successful_tick_symbol"], "None")} compact />
        <Metric label="Last Tick Time" value={formatTradeTime(readText(mt5Health, ["last_tick_time"], ""))} compact />
        <Metric label="Reconnect Timer" value={mode === "WAITING_FOR_MT5_RECONNECT" ? `${reconnectRemaining}s left` : "Inactive"} valueClass={mode === "WAITING_FOR_MT5_RECONNECT" ? "text-amber-200" : "text-slate-400"} compact />
        <Metric label="Last Disconnect" value={formatTradeTime(lastDisconnectAt)} compact />
        <Metric label="Reconnect Attempts" value={String(reconnectAttempts)} compact />
      </div>
      {pollError ? (
        <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm font-bold text-amber-100">
          AUTO status stale: {pollError}
        </div>
      ) : null}
      {readNumber(openPositionSync, ["historical_unowned_open_positions", "unmatched_open_positions"], 0) > 0 ? (
        <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm font-bold text-amber-100">
          Historical MT5 positions detected before this AUTO session. They are not counted toward current validation results.
        </div>
      ) : null}

      <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Execution Funnel</p>
          <h3 className="mt-1 text-xl font-black text-white">AUTO Validation Flow</h3>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Scanned" value={String(readNumber(session, ["signals_scanned"], 0))} compact />
          <Metric label="Ready" value={String(readNumber(session, ["signals_ready_for_preview"], 0))} compact />
          <Metric label="Wrapper Submitted" value={String(readNumber(session, ["wrapper_submitted"], 0))} compact />
          <Metric label="Approval Passed" value={String(readNumber(session, ["approval_workflow_passed"], 0))} compact />
          <Metric label="Guarded Sender Attempted" value={String(readNumber(session, ["guarded_sender_attempted", "signals_sent_to_sender"], 0))} compact />
          <Metric label="Order Send Attempted" value={String(readNumber(session, ["order_send_attempted"], 0))} compact />
          <Metric label="Opened" value={String(readNumber(session, ["opened", "orders_created"], 0))} compact />
          <Metric label="Blocked" value={String(readNumber(session, ["signals_blocked_by_sender"], 0))} compact />
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Validation Performance Dashboard</p>
            <h3 className="mt-1 text-xl font-black text-white">Session Results</h3>
          </div>
          <p className="text-sm font-bold text-slate-500">Keeps the latest closed-trade performance visible during AUTO validation.</p>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Metric label="Total Trades" value={String(totalTrades)} compact />
          <Metric label="Target Closed Trades" value={String(targetValidationTrades)} compact />
          <Metric label="Remaining Closed Trades" value={String(remainingTrades)} compact />
          <Metric label="Open Trades" value={String(readNumber(session, ["current_open_trades"], 0))} compact />
          <Metric label="Closed Trades" value={String(readNumber(session, ["current_closed_trades"], 0))} compact />
          <Metric label="Wins" value={String(wins)} valueClass="text-emerald-300" compact />
          <Metric label="Losses" value={String(losses)} valueClass="text-rose-300" compact />
          <Metric label="Win Rate" value={`${readNumber(session, ["win_rate"], 0).toFixed(2)}%`} compact />
          <Metric label="Net P&L" value={money(netPnl)} valueClass={pnlClass(netPnl)} compact />
          <Metric label="Average RR" value={`${readNumber(session, ["avg_rr", "average_rr"], 0).toFixed(2)}:1`} compact />
          <Metric label="Profit Factor" value={readNumber(session, ["profit_factor"], 0).toFixed(2)} compact />
          <Metric label="Max Drawdown" value={money(readNumber(session, ["max_drawdown"], 0))} compact />
          <Metric label="Best Setup Type" value={readText(session, ["best_setup_type"], "Unavailable")} compact />
          <Metric label="Worst Setup Type" value={readText(session, ["worst_setup_type"], "Unavailable")} compact />
        </div>
        <div className="mt-4">
          <ValidationReasonPanel messages={reasonMessages} />
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Live Validation Report</p>
          <h3 className="mt-1 text-xl font-black text-white">Latest Closed Trade</h3>
        </div>
        {latestCloseReport ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <Metric label="Ticket" value={readText(latestCloseReport, ["ticket"], "Unavailable")} compact />
            <Metric label="Symbol" value={readText(latestCloseReport, ["symbol"], "Unavailable")} compact />
            <Metric label="BUY/SELL" value={readText(latestCloseReport, ["side"], "Unavailable")} compact />
            <Metric label="Entry" value={marketNumber(readNumber(latestCloseReport, ["entry"], Number.NaN), readText(latestCloseReport, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
            <Metric label="Exit" value={marketNumber(readNumber(latestCloseReport, ["exit"], Number.NaN), readText(latestCloseReport, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
            <Metric label="P&L" value={money(readNumber(latestCloseReport, ["pnl"], 0))} valueClass={pnlClass(readNumber(latestCloseReport, ["pnl"], 0))} compact />
            <Metric label="Exit Reason" value={readText(latestCloseReport, ["exit_reason"], "UNKNOWN")} compact />
            <Metric label="Setup Type" value={readText(latestCloseReport, ["setup_type"], "Unknown Setup")} compact />
            <Metric label="Confidence" value={percent(readNumber(latestCloseReport, ["confidence"], Number.NaN))} compact />
            <Metric label="RR" value={readNumber(latestCloseReport, ["rr"], 0) > 0 ? `${readNumber(latestCloseReport, ["rr"], 0).toFixed(2)}:1` : "Unavailable"} compact />
            <Metric label="Session" value={readText(latestCloseReport, ["session"], "Unavailable")} compact />
            <Metric label="Closed At" value={formatTradeTime(readText(latestCloseReport, ["closed_at"], ""))} compact />
          </div>
        ) : (
          <EmptyState text="A live validation report will appear when the next current-session trade closes." />
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Current Signal Watched</p>
          <p className="mt-2 text-lg font-black text-white">{watched ? `${readText(watched, ["symbol"], "Signal")} ${readText(watched, ["signal"], "WAIT")}` : "None"}</p>
          <p className="mt-1 text-sm font-bold text-slate-400">{readText(watched, ["setup_reason", "reason"], "Waiting for qualified signal.")}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Metric label="Last Checked Symbol" value={lastCheckedSymbol} compact />
            <Metric label="Best Candidate Symbol" value={bestCandidateSymbol} compact />
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Last Decision</p>
          <p className="mt-2 text-lg font-black text-white">{readText(decision, ["status"], "No decision yet")}</p>
          {blockers.length > 0 ? <p className="mt-1 text-sm font-bold text-amber-100">{blockers.join(", ")}</p> : <p className="mt-1 text-sm font-bold text-slate-400">No blocked reasons recorded.</p>}
          <p className="mt-2 text-sm font-bold text-slate-400">Why no symbol qualified: {noQualifiedReason}</p>
          <div className="mt-3 grid gap-2">
            <p className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 text-xs font-bold text-slate-300">
              EURUSD: {readText(eurusdCheck, ["status"], "Not checked")} / confidence {readText(eurusdCheck, ["confidence"], "Unavailable")} / {readText(eurusdCheck, ["blocking_reason"], "No result")}
            </p>
            <p className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 text-xs font-bold text-slate-300">
              XAUUSD: {readText(xauusdCheck, ["status"], "Not checked")} / confidence {readText(xauusdCheck, ["confidence"], "Unavailable")} / {readText(xauusdCheck, ["blocking_reason"], "No result")}
            </p>
          </div>
          <p className={`mt-2 text-sm font-bold ${runnerError ? "text-rose-200" : "text-slate-500"}`}>Last Runner Error: {runnerError || "None"}</p>
        </div>
      </div>
      <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Last Sender Rejection</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <Metric label="Code" value={readText(senderRejection, ["rejection_code"], "None")} compact />
          <Metric label="Reason" value={readText(senderRejection, ["rejection_reason"], "None")} compact />
          <Metric label="Failed Guard" value={readText(senderRejection, ["failed_guard"], "None")} compact />
          <Metric label="Last Blocker" value={readText(executionTimeline, ["final_rejection_reason"], readText(senderResult, ["final_blocker"], "None"))} compact />
          <Metric label="Last MT5 Retcode" value={readText(executionTimeline, ["retcode"], readText(senderResult, ["retcode", "final_retcode"], "None"))} compact />
          <Metric label="Order Send Status" value={readText(executionTimeline, ["order_send_status"], readText(senderResult, ["order_send_status"], "None"))} compact />
        </div>
      </div>
      <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Last Duplicate Check</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Metric label="Duplicate Key" value={readText(duplicateCheck, ["duplicate_key"], "None")} compact />
          <Metric label="Duplicate Source" value={readText(duplicateCheck, ["duplicate_source"], "None")} compact />
          <Metric label="Open Positions" value={String(readNumber(duplicateCheck, ["open_positions_count"], 0))} compact />
          <Metric label="Pending Orders" value={String(readNumber(duplicateCheck, ["pending_orders_count"], 0))} compact />
          <Metric label="Matching Journal" value={String(readNumber(duplicateCheck, ["matching_journal_records"], 0))} compact />
          <Metric label="Cooldown Active" value={readText(duplicateCheck, ["cooldown_active"], "false") === "true" ? "Yes" : "No"} compact />
          <Metric label="Duplicate Decision" value={readText(duplicateCheck, ["final_duplicate_decision"], "false") === "true" ? "Blocked" : "Clear"} valueClass={readText(duplicateCheck, ["final_duplicate_decision"], "false") === "true" ? "text-amber-200" : "text-emerald-300"} compact />
        </div>
      </div>
      <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Open Position Sync</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Metric label="MT5 Open Detected" value={String(readNumber(openPositionSync, ["mt5_open_positions_detected"], 0))} compact />
          <Metric label="AUTO-Owned Open" value={String(readNumber(openPositionSync, ["auto_owned_open_positions"], 0))} compact />
          <Metric label="Unmatched Open" value={String(readNumber(openPositionSync, ["unmatched_open_positions"], 0))} compact />
          <Metric label="Historical/Unowned" value={String(readNumber(openPositionSync, ["historical_unowned_open_positions"], 0))} compact />
          <Metric label="MT5 Open Positions" value={String(readNumber(openPositionSync, ["mt5_open_positions"], 0))} compact />
          <Metric label="Historical Positions" value={String(readNumber(openPositionSync, ["historical_positions"], 0))} compact />
          <Metric label="Validation Positions" value={String(readNumber(openPositionSync, ["validation_positions"], 0))} compact />
          <Metric label="Current Session Positions" value={String(readNumber(openPositionSync, ["current_session_positions"], 0))} compact />
          <Metric label="Current Session By Symbol" value={currentSessionPositionsText} compact />
          <Metric label="Limit Count Source" value={readText(openPositionSync, ["limit_count_source"], "current_session_positions_only").replaceAll("_", " ")} compact />
          <Metric label="Open Tickets" value={Array.isArray(openPositionSync?.open_position_tickets) && openPositionSync.open_position_tickets.length ? openPositionSync.open_position_tickets.map(String).join(", ") : "None"} compact />
          <Metric label="Sync Time" value={formatTradeTime(readText(openPositionSync, ["timestamp"], ""))} compact />
        </div>
      </div>
      <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Lifecycle Sync</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Metric label="Lifecycle Status" value={readText(lifecycleSync, ["status"], "NOT_SYNCED")} compact />
          <Metric label="Close Sync Status" value={readText(lifecycleSync, ["close_sync_status"], "NOT_CONFIGURED")} compact />
          <Metric label="Open Trades Checked" value={String(readNumber(lifecycleSync, ["open_trades_checked"], 0))} compact />
          <Metric label="Current Session Closed Updated" value={String(readNumber(lifecycleSync, ["closed_trades_updated"], 0))} compact />
          <Metric label="All Closed Updated" value={String(readNumber(lifecycleSync, ["all_closed_trades_updated"], 0))} compact />
          <Metric label="Lifecycle Sync Time" value={formatTradeTime(readText(lifecycleSync, ["timestamp"], ""))} compact />
        </div>
        <p className={`mt-3 text-sm font-bold ${readText(lifecycleSync, ["status"], "") === "ERROR" ? "text-rose-200" : "text-slate-400"}`}>
          {readText(lifecycleSync, ["message"], "Lifecycle sync has not run.")}
        </p>
      </div>
      <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Exit Management</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Status" value={readText(exitManagement, ["status"], "NOT_RUN")} compact />
          <Metric label="Positions Checked" value={String(readNumber(exitManagement, ["positions_checked"], 0))} compact />
          <Metric label="Actions Taken" value={String(readNumber(exitManagement, ["actions_taken"], 0))} compact />
          <Metric label="Failed Actions" value={String(readNumber(exitManagement, ["failed_actions"], 0))} compact />
          <Metric label="Break Even Moves" value={String(readNumber(exitManagement, ["break_even_moves"], 0))} compact />
          <Metric label="Trailing Updates" value={String(readNumber(exitManagement, ["trailing_stop_moves"], 0))} compact />
          <Metric label="Reversal Exits" value={String(readNumber(exitManagement, ["signal_reversal_exits"], 0))} compact />
          <Metric label="Confidence Exits" value={String(readNumber(exitManagement, ["confidence_drop_exits"], 0))} compact />
          <Metric label="Last Exit Action" value={readText(lastExitAction, ["exit_reason"], readText(lastFailedExitAction, ["exit_reason"], "None"))} compact />
          <Metric label="Last Exit Result" value={readText(asRecord(lastExitAction?.execution_result) ?? asRecord(lastFailedExitAction?.execution_result), ["status"], "None")} compact />
        </div>
        <div className="mt-4 overflow-auto">
          <table className="w-full min-w-[900px] text-left text-xs font-bold text-slate-300">
            <thead className="text-slate-500">
              <tr>{["Ticket", "Symbol", "Side", "Open trade age", "Unrealized P&L", "SL Dist", "TP Dist", "Exit State", "Last Action"].map((item) => <th className="px-3 py-2" key={item}>{item}</th>)}</tr>
            </thead>
            <tbody>
              {managedExitPositions.length ? managedExitPositions.map((item, index) => {
                const execution = asRecord(item.execution_result);
                return (
                  <tr className="border-t border-slate-800" key={`${readText(item, ["ticket"], "ticket")}-${index}`}>
                    <td className="px-3 py-2">{readText(item, ["ticket"], "None")}</td>
                    <td className="px-3 py-2">{readText(item, ["symbol"], "None")}</td>
                    <td className="px-3 py-2">{readText(item, ["side"], "None")}</td>
                    <td className="px-3 py-2">{readNumber(item, ["age_minutes"], 0).toFixed(1)}m</td>
                    <td className={`px-3 py-2 ${pnlClass(readNumber(item, ["unrealized_pnl"], 0))}`}>{money(readNumber(item, ["unrealized_pnl"], 0))}</td>
                    <td className="px-3 py-2">{readText(item, ["distance_to_sl"], "n/a")}</td>
                    <td className="px-3 py-2">{readText(item, ["distance_to_tp"], "n/a")}</td>
                    <td className="px-3 py-2">{readText(item, ["exit_reason"], readText(item, ["action"], "HOLD"))}</td>
                    <td className="px-3 py-2">{readText(execution, ["status"], readText(item, ["action"], "HOLD"))}</td>
                  </tr>
                );
              }) : (
                <tr><td className="px-3 py-4 text-slate-500" colSpan={9}>No current-session open positions have been evaluated for exits yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Signal Hash Audit</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <Metric label="Hash Status" value={hashEvent} valueClass={hashEvent === "HASH_CHANGE_MINOR" ? "text-emerald-300" : hashEvent === "SIGNAL_HASH_CHANGED" ? "text-amber-200" : "text-slate-300"} compact />
            <Metric label="Original Hash" value={readText(hashAudit, ["original_hash"], "None")} compact />
            <Metric label="Current Hash" value={readText(hashAudit, ["current_hash"], "None")} compact />
            <Metric label="Original Time" value={formatTradeTime(readText(hashAudit, ["original_signal_timestamp"], ""))} compact />
            <Metric label="Revalidated Time" value={formatTradeTime(readText(hashAudit, ["revalidation_timestamp"], ""))} compact />
          </div>
          <p className="mt-3 text-sm font-bold text-slate-400">Changed Fields: {hashChangedFields.length > 0 ? hashChangedFields.map((item) => readText(item, ["field"], "field")).join(", ") : "None"}</p>
          <p className="mt-1 text-sm font-bold text-slate-500">{readText(hashAudit, ["root_cause"], "No material hash change recorded.")}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">XAUUSD Confidence Timeline</p>
          {confidenceTimeline.length > 0 ? (
            <div className="mt-3 max-h-56 overflow-auto">
              {confidenceTimeline.slice(-20).map((item, index) => (
                <p className="border-b border-slate-800 py-2 text-xs font-bold text-slate-300" key={`${readText(item, ["timestamp"], "scan")}-${index}`}>
                  {formatTradeTime(readText(item, ["timestamp"], ""))}: confidence {readNumber(item, ["confidence"], 0)} | BOS {readText(item, ["bos"], "n/a")} | sweep {readText(item, ["liquidity_sweep"], "n/a")} | CHOCH {readText(item, ["choch"], "n/a")} | FVG {readText(item, ["fvg"], "n/a")} | OB {readText(item, ["order_block"], "n/a")} | spread {readText(item, ["spread"], "n/a")} | session {readText(item, ["session"], "n/a")} | {readText(item, ["reason_for_confidence_change"], "")}
                </p>
              ))}
            </div>
          ) : (
            <EmptyState text="XAUUSD confidence timeline will appear after validation scans." />
          )}
        </div>
      </div>
    </section>
  );
}

function MarketCard({ title, tick, scope, signal = null }: { title: string; tick: ApiRecord | null; scope: ApiRecord | null; signal?: ApiRecord | null }) {
  const label = title === "XAUUSD" ? xauusdReadinessLabel(tick, signal) : marketLabel(tick);
  const bid = readNumber(tick, ["bid"], Number.NaN);
  const ask = readNumber(tick, ["ask"], Number.NaN);
  const spread = readNumber(tick, ["spread"], Number.NaN);
  const marketStatus = readText(tick, ["market_status", "status"], "").toUpperCase();
  const stale = marketStatus === "STALE_TICK" || readText(tick, ["stale"], "false") === "true";
  const feedUnavailable = !tick || ["SYMBOL_TICK_UNAVAILABLE", "FEED_OFFLINE", "MARKET_CLOSED"].includes(marketStatus);
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex items-start justify-between gap-3">
        <SectionTitle eyebrow="Market Status" title={title} />
        <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${statusTone(label)}`}>{label}</span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3">
        <Metric label="Bid" value={marketNumber(bid, title === "XAUUSD" ? 2 : 5)} compact />
        <Metric label="Ask" value={marketNumber(ask, title === "XAUUSD" ? 2 : 5)} compact />
        <Metric label="Spread" value={Number.isFinite(spread) ? spread.toLocaleString(undefined, { maximumFractionDigits: 6 }) : "Unavailable"} compact />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Metric label="Source" value={readText(scope, ["source"], "MT5_DEMO")} compact />
        <Metric label="Last Update" value={formatTradeTime(readText(tick, ["timestamp"], ""))} compact />
      </div>
      {stale ? <p className="mt-3 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-sm font-bold text-amber-100">Showing last known prices while the latest tick recovers.</p> : null}
      {title === "XAUUSD" ? <p className="mt-3 text-sm font-bold text-slate-400">XAUUSD execution is not enabled today; valid setups are classified for a future guarded demo test.</p> : null}
      {feedUnavailable ? <p className="mt-3 text-sm font-bold text-slate-400">{marketStatus === "MARKET_CLOSED" ? "Market-hours logic confirms the market is closed." : "Market feed unavailable after repeated tick failures."}</p> : null}
    </section>
  );
}

function NiftyMarketCard({ scope }: { scope: ApiRecord | null }) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex items-start justify-between gap-3">
        <SectionTitle eyebrow="Market Status" title="NIFTY50" />
        <span className="rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-xs font-black uppercase text-sky-200">Integration Pending</span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-3">
        <Metric label="Price" value="Unavailable" compact />
        <Metric label="Spread" value="Unavailable" compact />
        <Metric label="Status" value={readText(scope, ["status"], "INTEGRATION_PENDING").replaceAll("_", " ")} compact />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Metric label="Source" value={readText(scope, ["source"], "PENDING_INDIAN_MARKET_INTEGRATION").replaceAll("_", " ")} compact />
        <Metric label="Last Update" value={formatTradeTime(readText(scope, ["timestamp"], ""))} compact />
      </div>
      <p className="mt-3 text-sm font-bold text-slate-400">Indian market data/broker integration pending.</p>
    </section>
  );
}

function PreviewPanel({ preview, signal, canSend, validForSeconds, onConfirm }: { preview: ApiRecord; signal: ApiRecord | null; canSend: boolean; validForSeconds: number; onConfirm: () => void }) {
  const source = asRecord(signal?.candle_source);
  const structure = asRecord(signal?.market_structure_state);
  const components = asRecord(signal?.strategy_components);
  const audit = asRecord(signal?.approval_audit);
  const blockers = blockersFromPreview(preview);
  return (
    <div className="mt-4 rounded-xl border border-blue-400/20 bg-blue-500/10 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-bold text-blue-100">Preview Status: {readText(preview, ["approval_status"], canSend ? "APPROVED" : "NEEDS_ATTENTION").replaceAll("_", " ")}</p>
          <p className="mt-1 text-xs font-bold uppercase tracking-[0.16em] text-blue-200">Read-only preview. No order sent.</p>
        </div>
        <button className="rounded-xl bg-emerald-500 px-4 py-3 text-sm font-black text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400" disabled={!canSend} onClick={onConfirm} type="button">
          Confirm Demo Order
        </button>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Trade Summary</p>
          <div className="mt-3 grid gap-3">
            <Metric label="Symbol" value={readText(preview, ["symbol"], readText(signal, ["symbol"], "Unavailable"))} compact />
            <Metric label="Direction" value={readText(preview, ["side"], readText(signal, ["signal"], "WAIT"))} compact />
            <Metric label="Entry" value={marketNumber(readNumber(preview, ["entry_estimate"], readNumber(signal, ["entry"], Number.NaN)), readText(preview, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
            <Metric label="Stop Loss" value={marketNumber(readNumber(preview, ["stop_loss"], readNumber(signal, ["stop_loss"], Number.NaN)), readText(preview, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
            <Metric label="Take Profit" value={marketNumber(readNumber(preview, ["take_profit"], readNumber(signal, ["take_profit"], Number.NaN)), readText(preview, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
            <Metric label="Risk / Reward" value={`${readNumber(signal, ["risk_reward"], 0).toFixed(2)}:1`} compact />
            <Metric label="Confidence" value={percent(readNumber(signal, ["confidence"], Number.NaN))} compact />
            <Metric label="Trend Bias" value={readText(structure, ["trend_bias"], "Unavailable").replaceAll("_", " ")} compact />
          </div>
        </div>

        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Market Information</p>
          <div className="mt-3 grid gap-3">
            <Metric label="Broker Source" value={readText(source, ["broker_source", "source"], readText(preview, ["broker_source", "source"], "Unavailable"))} compact />
            <Metric label="Account Login" value={readText(source, ["account_login"], readText(preview, ["account_login"], "Unavailable"))} compact />
            <Metric label="Server" value={readText(source, ["server"], readText(preview, ["server"], "Unavailable"))} compact />
            <Metric label="Spread" value={marketNumber(readNumber(preview, ["spread"], Number.NaN), readText(preview, ["symbol"], "") === "XAUUSD" ? 2 : 5)} compact />
            <Metric label="Session" value={readText(components, ["session"], "Unavailable")} compact />
            <Metric label="Last Candle" value={formatTradeTime(lastCandleTimestamp(signal))} compact />
          </div>
        </div>

        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Readiness Information</p>
          <div className="mt-3 grid gap-3">
            <Metric label="Readiness Decision" value={readText(preview, ["readiness_decision"], "BLOCKED").replaceAll("_", " ")} compact />
            <Metric label="Approval Status" value={readText(preview, ["approval_status"], "BLOCKED").replaceAll("_", " ")} compact />
            <Metric label="Signal Validity" value={validForSeconds > 0 ? `Valid for ${validForSeconds}s` : "Expired"} compact />
            <Metric label="Duplicate Protection" value={readText(preview, ["duplicate_protection_status"], "BLOCKED").replaceAll("_", " ")} compact />
            <Metric label="BOS / CHOCH" value={`${readText(audit, ["bos_result"], "Unknown")} / ${readText(audit, ["choch_result"], "Unknown")}`} compact />
            <Metric label="Sweep / FVG / OB" value={`${readText(audit, ["liquidity_sweep_result"], "Unknown")} / ${readText(audit, ["fvg_result"], "Unknown")} / ${readText(audit, ["order_block_result"], "Unknown")}`} compact />
            <Metric label="Final Reason" value={readText(audit, ["final_approval_reason"], readText(signal, ["setup_reason"], "Unavailable"))} compact />
          </div>
          {blockers.length > 0 && (
            <div className="mt-3 rounded-lg border border-amber-400/20 bg-amber-500/10 p-3 text-sm text-amber-100">
              {blockers.map((blocker) => (
                <p key={blocker}>{blocker}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SignalCard({
  symbol,
  signal,
  selected,
  canPreview,
  validForSeconds,
  onSelect,
  onPreview,
}: {
  symbol: ScopedSymbol;
  signal: ApiRecord | null;
  selected: boolean;
  canPreview: boolean;
  validForSeconds: number;
  onSelect: () => void;
  onPreview: (signal: ApiRecord | null) => void;
}) {
  const action = readText(signal, ["signal"], "WAIT").toUpperCase();
  const confidence = readNumber(signal, ["confidence"], Number.NaN);
  const riskReward = readNumber(signal, ["risk_reward"], Number.NaN);
  const actionable = action === "BUY" || action === "SELL";
  const marketStructure = asRecord(signal?.market_structure_state);
  const statusLevel = readText(signal, ["status_level"], readText(signal, ["execution_status"], "WAIT")).toUpperCase();
  const missingRequirements = Array.isArray(signal?.missing_requirements) ? (signal.missing_requirements.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  return (
    <section
      className={`rounded-2xl border p-4 text-left transition ${selected ? "border-blue-400 bg-blue-500/10" : "border-slate-800 bg-[#0F172A] hover:border-slate-600"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{symbol}</p>
          <strong className={`mt-2 block text-2xl ${actionable ? "text-emerald-300" : "text-slate-100"}`}>{action}</strong>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${statusTone(statusLevel)}`}>
          {statusLevel}
        </span>
      </div>
      {readySignal(signal) && validForSeconds > 0 && <p className="mt-3 text-xs font-black uppercase tracking-[0.16em] text-emerald-300">Valid for {validForSeconds}s</p>}
      <p className="mt-3 min-h-10 text-sm font-semibold text-slate-300">{readText(signal, ["setup_reason", "reason"], symbol === "NIFTY50" ? "Indian market integration pending." : "No confirmed setup available.")}</p>
      <div className="mt-3 rounded-xl border border-slate-800 bg-[#0B1220] p-3">
        <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">What needs to happen next?</p>
        <p className="mt-2 text-sm font-bold text-sky-100">{readText(signal, ["what_needs_to_happen_next"], "Waiting for strategy confirmation.")}</p>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Metric label="Confidence" value={Number.isFinite(confidence) ? `${confidence.toFixed(0)}%` : "Unavailable"} compact />
        <Metric label="Entry" value={marketNumber(readNumber(signal, ["entry"], Number.NaN), symbol === "XAUUSD" ? 2 : 5)} compact />
        <Metric label="Stop Loss" value={marketNumber(readNumber(signal, ["stop_loss"], Number.NaN), symbol === "XAUUSD" ? 2 : 5)} compact />
        <Metric label="Take Profit" value={marketNumber(readNumber(signal, ["take_profit"], Number.NaN), symbol === "XAUUSD" ? 2 : 5)} compact />
        <Metric label="Risk / Reward" value={Number.isFinite(riskReward) ? `${riskReward.toFixed(2)}:1` : "Unavailable"} compact />
        <Metric label="Risk Status" value={readText(signal, ["risk_status"], "NO_SIGNAL").replaceAll("_", " ")} compact />
        <Metric label="Trend Bias" value={readText(marketStructure, ["trend_bias"], "Unavailable").replaceAll("_", " ")} compact />
        <Metric label="Structure" value={`${readText(marketStructure, ["higher_timeframe_bias"], "H4?")} / ${readText(marketStructure, ["intermediate_timeframe_bias"], "H1?")} / ${readText(marketStructure, ["lower_timeframe_bias"], "M15?")}`} compact />
      </div>
      <StrategyComponents components={asRecord(signal?.strategy_components)} />
      {missingRequirements.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-500/10 p-3">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-amber-200">Missing Requirements</p>
          <div className="mt-2 grid gap-1 text-xs font-bold text-amber-100">
            {missingRequirements.slice(0, 6).map((item) => (
              <p key={readText(item, ["code"], readText(item, ["label"], "Requirement"))}>{readText(item, ["label"], readText(item, ["code"], "Requirement missing"))}</p>
            ))}
          </div>
        </div>
      )}
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <button className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-bold text-slate-100 hover:bg-slate-800" onClick={onSelect} type="button">
          Select
        </button>
        {readySignal(signal) && validForSeconds > 0 && (
          <button className="rounded-xl bg-blue-500 px-3 py-2 text-sm font-black text-white hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400" disabled={!canPreview} onClick={() => onPreview(signal)} type="button">
            Preview Trade
          </button>
        )}
      </div>
    </section>
  );
}

function StrategyComponents({ components }: { components: ApiRecord | null }) {
  const items = [
    ["Liquidity Sweep", components?.liquidity_sweep],
    ["BOS", components?.bos],
    ["CHOCH", components?.choch],
    ["FVG", components?.fvg],
    ["Order Block", components?.order_block],
    ["Session Valid", components?.session_valid],
    ["Bias", components?.bias],
    ["Session", components?.session],
  ] as const;
  return (
    <div className="mt-4 grid gap-2 sm:grid-cols-2">
      {items.map(([label, value]) => (
        <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-[#0B1220] px-3 py-2 text-xs font-bold" key={label}>
          <span className="text-slate-300">{label}</span>
          <span className={componentTone(value)}>{componentLabel(value)}</span>
        </div>
      ))}
    </div>
  );
}

function componentLabel(value: unknown): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  if (typeof value === "string" && value.trim()) return value.replaceAll("_", " ");
  if (typeof value === "number" && Number.isFinite(value)) return value.toFixed(2);
  return "Unavailable";
}

function componentTone(value: unknown): string {
  if (value === true) return "text-emerald-300";
  if (value === false) return "text-rose-300";
  if (typeof value === "string" && value.trim()) return "text-sky-200";
  if (typeof value === "number" && Number.isFinite(value)) return "text-slate-200";
  return "text-slate-500";
}

function BrokerAccountCard({ brokerId, account, copyPlan }: { brokerId: "STARTRADER" | "FXPRO" | "VANTAGE"; account: ApiRecord | null; copyPlan: ApiRecord | null }) {
  const brokerName = readText(account, ["broker_name"], brokerId === "STARTRADER" ? "StarTrader" : brokerId === "FXPRO" ? "FxPro" : "Vantage");
  const connectionStatus = readText(account, ["connection_status"], "PENDING_CONNECTION").replaceAll("_", " ");
  const executionEnabled = readText(account, ["execution_enabled"], "false") === "true";
  const blockedReasons = Array.isArray(copyPlan?.blocked_reasons) ? (copyPlan.blocked_reasons.map((reason) => String(reason)) as string[]) : [];
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0F172A] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{brokerId}</p>
          <h3 className="mt-1 text-xl font-black text-white">{brokerName}</h3>
        </div>
        <span className="rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-xs font-black uppercase text-sky-200">Pending</span>
      </div>
      <p className="mt-3 text-sm font-bold text-slate-400">{readText(account, ["message"], "Broker account not connected yet.")}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Metric label="Connection Status" value={connectionStatus} compact />
        <Metric label="Account Type" value={readText(account, ["account_type"], "Unavailable")} compact />
        <Metric label="Balance" value={money(readNumber(account, ["balance"], Number.NaN))} valueClass="whitespace-nowrap text-white" compact />
        <Metric label="Equity" value={money(readNumber(account, ["equity"], Number.NaN))} valueClass="whitespace-nowrap text-white" compact />
        <Metric label="Execution Status" value={executionEnabled ? "Enabled" : "Disabled"} valueClass={executionEnabled ? "text-rose-300" : "text-emerald-300"} compact />
        <Metric label="Copy Readiness" value={readText(copyPlan, ["readiness_status"], "BLOCKED").replaceAll("_", " ")} compact />
        <Metric label="Duplicate Protection" value={readText(asRecord(copyPlan?.duplicate_protection), ["reason"], "No duplicate check available.")} compact />
        <Metric label="Execution Decision" value={readText(copyPlan, ["final_execution_decision"], "BLOCKED").replaceAll("_", " ")} compact />
      </div>
      {blockedReasons.length > 0 ? (
        <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm font-bold text-amber-100">
          {blockedReasons.slice(0, 3).map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function VantageXauusdValidationPanel({ status, preview }: { status: ApiRecord | null; preview: ApiRecord | null }) {
  const blockedReasons = Array.isArray(preview?.blocked_reasons) ? (preview.blocked_reasons.map((reason) => String(reason)) as string[]) : [];
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <SectionTitle eyebrow="Vantage XAUUSD Demo Validation" title="Guarded Demo Test Readiness" />
        <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${statusTone(readText(status, ["readiness_result"], "BLOCKED"))}`}>
          {readText(status, ["readiness_result"], "BLOCKED").replaceAll("_", " ")}
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Broker Detected" value={readText(status, ["broker_detected"], "Unavailable").replaceAll("_", " ")} compact />
        <Metric label="Tick Status" value={readText(status, ["tick_available"], "false") === "true" ? "Available" : "Unavailable"} compact />
        <Metric label="Bid / Ask" value={`${marketNumber(readNumber(status, ["bid"], Number.NaN), 2)} / ${marketNumber(readNumber(status, ["ask"], Number.NaN), 2)}`} compact />
        <Metric label="Spread" value={marketNumber(readNumber(status, ["spread"], Number.NaN), 2)} compact />
        <Metric label="Preview Decision" value={readText(preview, ["readiness_decision"], "BLOCKED").replaceAll("_", " ")} compact />
        <Metric label="Would Send" value={readText(preview, ["would_send"], "false") === "true" ? "Yes" : "No"} compact />
        <Metric label="Latest Test Order" value={readText(asRecord(status?.latest_test_order), ["status"], "No order submitted")} compact />
        <Metric label="Safety Flags" value="Live/Broker Off" valueClass="text-emerald-300" compact />
      </div>
      {blockedReasons.length ? (
        <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm font-bold text-amber-100">
          {blockedReasons.slice(0, 4).map((reason) => (
            <p key={reason}>{reason.replaceAll("_", " ")}</p>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm font-bold text-slate-400">Preview is read-only. Test order placement remains behind the Vantage guarded demo endpoint.</p>
      )}
    </section>
  );
}

function CurrentTerminalCard({ account }: { account: ApiRecord | null }) {
  return (
    <section className="mt-4 rounded-2xl border border-slate-800 bg-[#0F172A] p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-300">Current Test Terminal</p>
          <h3 className="mt-1 text-xl font-black text-white">{readText(account, ["server"], "MetaQuotes-Demo")}</h3>
          <p className="mt-1 text-sm font-bold text-slate-400">{readText(account, ["message"], "Current MT5 terminal account; not mapped to StarTrader, FxPro, or Vantage.")}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[34rem]">
          <Metric label="Account" value={readText(account, ["account_login"], "Unavailable")} compact />
          <Metric label="Account Type" value={readText(account, ["account_type"], "Unavailable")} compact />
          <Metric label="Execution" value="Disabled" valueClass="text-emerald-300" compact />
        </div>
      </div>
    </section>
  );
}

function OpenPositionsTable({ positions }: { positions: ApiRecord[] }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[860px] border-separate border-spacing-y-2 text-left text-sm">
        <thead className="text-xs uppercase tracking-[0.16em] text-slate-400">
          <tr>
            {["Ticket", "Symbol", "Direction", "Lot", "Entry", "Current Price", "Floating P&L", "SL", "TP"].map((item, index) => (
              <th className={`px-3 py-2 ${index >= 3 ? "text-right" : ""}`} key={item}>
                {item}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((position, index) => {
            const pnl = readNumber(position, ["floating_pnl", "profit"], 0);
            return (
              <tr className="bg-[#0F172A]" key={`${readText(position, ["ticket"], String(index))}-${index}`}>
                <td className="rounded-l-xl px-3 py-3 font-bold">{readText(position, ["ticket"], "Unavailable")}</td>
                <td className="px-3 py-3">{readText(position, ["symbol"], "Unavailable")}</td>
                <td className="px-3 py-3">{readText(position, ["side", "type"], "Unavailable")}</td>
                <td className="px-3 py-3 text-right">{readText(position, ["lot", "volume"], "Unavailable")}</td>
                <td className="px-3 py-3 text-right">{marketNumber(readNumber(position, ["entry_price", "price_open"], Number.NaN))}</td>
                <td className="px-3 py-3 text-right">{marketNumber(readNumber(position, ["current_price", "price_current"], Number.NaN))}</td>
                <td className={`px-3 py-3 text-right font-bold ${pnlClass(pnl)}`}>{money(pnl)}</td>
                <td className="px-3 py-3 text-right">{marketNumber(readNumber(position, ["stop_loss", "sl"], Number.NaN))}</td>
                <td className="rounded-r-xl px-3 py-3 text-right">{marketNumber(readNumber(position, ["take_profit", "tp"], Number.NaN))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ClosedTradesTable({ trades }: { trades: ApiRecord[] }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full min-w-[860px] border-separate border-spacing-y-2 text-left text-sm">
        <thead className="text-xs uppercase tracking-[0.16em] text-slate-400">
          <tr>{["Symbol", "Side", "Entry", "Close", "P&L", "Result", "Duration", "Closed At"].map((item) => <th className="px-3 py-2" key={item}>{item}</th>)}</tr>
        </thead>
        <tbody>
          {trades.map((trade, index) => {
            const pnl = readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl"], 0);
            return (
              <tr className="bg-[#0F172A]" key={`${readText(trade, ["trade_id", "mt5_ticket"], String(index))}-${index}`}>
                <td className="rounded-l-xl px-3 py-3 font-bold">{readText(trade, ["symbol"], "Unavailable")}</td>
                <td className="px-3 py-3">{readText(trade, ["side"], "Unavailable")}</td>
                <td className="px-3 py-3">{marketNumber(readNumber(trade, ["entry_price"], Number.NaN))}</td>
                <td className="px-3 py-3">{marketNumber(readNumber(trade, ["close_price"], Number.NaN))}</td>
                <td className={`px-3 py-3 font-bold ${pnlClass(pnl)}`}>{money(pnl)}</td>
                <td className="px-3 py-3">{readText(trade, ["result"], "Unavailable")}</td>
                <td className="px-3 py-3">{formatDuration(trade.duration_minutes)}</td>
                <td className="whitespace-pre-line rounded-r-xl px-3 py-3">{formatTradeTime(readText(trade, ["closed_at", "close_time"], ""))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="premium-empty">{text}</div>;
}

function SafetyPill({ text }: { text: string }) {
  return <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1.5 text-xs font-black uppercase tracking-[0.16em] text-emerald-200">{text}</span>;
}
