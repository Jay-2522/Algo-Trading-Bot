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
  fetchReasonMessages,
  approveExecutionModeSignal,
  fetchAutoValidationRuntimeSnapshot,
  previewClientDemoTrade,
  pauseAutoValidation,
  rejectExecutionModeSignal,
  resetAutoValidationClosedTrades,
  resumeAutoValidation,
  runAutoValidationExitManagement,
  sendGuardedClientDemoTrade,
  sendPortalChatMessage,
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
  niftyTick: ApiRecord | null;
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
type AutoValidationAction = "start" | "pause" | "resume" | "stop" | "reset-closed-trades";

const READY_SIGNAL_HOLD_SECONDS = 30;
const TARGET_TRADES = 30;
const RISK_NOTICE_VISIBLE_MS = 8000;
const ARCHIVED_ROUND_2_SESSION_IDS = new Set(["auto-validation-6dbfe380-22b1-44ea-9fc2-f4b7c25c3de9"]);
const ARCHIVED_ROUND_2_NET_PNL = -4.74;
const DASHBOARD_CACHE_KEY = "client-dashboard-last-successful-snapshot-v2";
const BALANCE_HISTORY_KEY = "algopilot_balance_history";
const INITIAL_ACCOUNT_BALANCE = 100000;
const CHAT_STORAGE_KEY = "algopilot_portal_chat_messages";
const ForexSessionsMap = dynamic(() => import("./ForexSessionsMap").then((mod) => mod.ForexSessionsMap), {
  loading: () => <div className="forex-leaflet-map-loading" />,
  ssr: false,
});
const ROUND_2_NOTE = "Round 2: EURUSD-only validation. No manual intervention. Client dashboard shows Round 2 only.";
const ROUND_3_NOTE = "Round 3: edge-score validation. Requires H4/M15 history, RR >= 2.0, risk approval, clean spread, higher-timeframe bias, and enough SMC confluence. London/NY is advisory only.";
const ROUND_3_START_PAYLOAD: ApiRecord = {
  session_started_by: "user_click",
  strategy_profile: "DEMO_COLLECTION",
  allowed_symbols: ["EURUSD", "XAUUSD"],
  target_validation_trades: TARGET_TRADES,
  target_closed_trades: TARGET_TRADES,
  round_label: "ROUND_3",
  session_note: ROUND_3_NOTE,
  client_dashboard_scope: "CURRENT_SESSION_ONLY",
};
const FOREX_DISPLAY_TIME_ZONE = "Asia/Kolkata";
const VALIDATION_SYMBOLS = new Set(["EURUSD", "XAUUSD", "NIFTY50"]);
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
  niftyTick: null,
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

function sameJsonValue(left: unknown, right: unknown): boolean {
  return JSON.stringify(left ?? null) === JSON.stringify(right ?? null);
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
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "Unavailable";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function marketPriceText(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "-";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function signed(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
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

function actualClosedTradeCount(trades: ApiRecord[]): number {
  return trades.length;
}

function tradeWinCount(trades: ApiRecord[]): number {
  return trades.filter((trade) => tradeResultLabel(trade) === "WIN").length;
}

function tradeLossCount(trades: ApiRecord[]): number {
  return trades.filter((trade) => tradeResultLabel(trade) === "LOSS").length;
}

function closedTradeProgressText(actualClosedTrades: number, targetTrades: number): string {
  if (targetTrades > 0 && actualClosedTrades > targetTrades) return `${actualClosedTrades} trades completed (target was ${targetTrades})`;
  return `${actualClosedTrades} of ${targetTrades} closed trades completed.`;
}

function validationSession(data: DashboardData): ApiRecord | null {
  return asRecord(asRecord(data.autoValidation)?.session);
}

function validationSessionId(data: DashboardData): string {
  return readText(validationSession(data), ["session_id", "id", "validation_session_id"], "");
}

function validationRoundLabel(data: DashboardData): string {
  return readText(validationSession(data), ["round_label"], "").toUpperCase();
}

function isRound3ValidationSession(data: DashboardData): boolean {
  return /^ROUND_\d+$/i.test(validationRoundLabel(data));
}

function validationRoundTitle(data: DashboardData): string {
  const label = validationRoundLabel(data);
  const match = label.match(/^ROUND_(\d+)$/i);
  return match ? `Round ${match[1]} Results` : "Round Results";
}

function tradeSessionId(trade: ApiRecord): string {
  return readText(trade, ["validation_session_id", "session_id"], "");
}

function activeStatsExcluded(trade: ApiRecord): boolean {
  return trade.active_stats_excluded === true || readText(trade, ["active_stats_excluded"], "").toLowerCase() === "true";
}

function closedTradesOnly(trades: ApiRecord[]): ApiRecord[] {
  return trades.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED" && !activeStatsExcluded(trade));
}

function round3ClosedTrades(data: DashboardData, trades: ApiRecord[]): ApiRecord[] {
  const sessionId = validationSessionId(data);
  if (!sessionId || !isRound3ValidationSession(data)) return [];
  return closedTradesOnly(trades).filter((trade) => tradeSessionId(trade) === sessionId);
}

function round2ClosedTrades(data: DashboardData, trades: ApiRecord[]): ApiRecord[] {
  const round3SessionId = isRound3ValidationSession(data) ? validationSessionId(data) : "";
  const archived = closedTradesOnly(trades).filter((trade) => ARCHIVED_ROUND_2_SESSION_IDS.has(tradeSessionId(trade)));
  if (archived.length > 0) return archived;
  return closedTradesOnly(trades).filter((trade) => {
    if (round3SessionId && tradeSessionId(trade) === round3SessionId) return false;
    const symbol = readText(trade, ["symbol"], "").toUpperCase();
    return !symbol || symbol === "EURUSD";
  });
}

function round2NetPnl(trades: ApiRecord[]): number {
  const archivedRound2 = trades.length === 32 && trades.every((trade) => ARCHIVED_ROUND_2_SESSION_IDS.has(tradeSessionId(trade)));
  return archivedRound2 ? ARCHIVED_ROUND_2_NET_PNL : trades.reduce((sum, trade) => sum + tradePnl(trade), 0);
}

function round3OpenPositions(data: DashboardData, positions: ApiRecord[]): ApiRecord[] {
  const sessionId = validationSessionId(data);
  if (!sessionId || !isRound3ValidationSession(data)) return [];
  const scopedPositions = positions.filter((position) => readText(position, ["validation_session_id", "session_id"], "") === sessionId);
  if (scopedPositions.length > 0) return scopedPositions;
  return validationOpenPositions(data.openPositions).filter((position) => readText(position, ["validation_session_id", "session_id"], "") === sessionId);
}

function round3DashboardData(data: DashboardData): DashboardData {
  if (isRound3ValidationSession(data)) return data;
  const autoStatus = asRecord(data.autoValidation);
  const config = asRecord(autoStatus?.config);
  const resetSession: ApiRecord = {
    ...(validationSession(data) ?? {}),
    session_id: "",
    status: "READY_ROUND_3",
    round_label: "ROUND_3",
    session_note: ROUND_3_NOTE,
    target_closed_trades: TARGET_TRADES,
    target_validation_trades: TARGET_TRADES,
    current_closed_trades: 0,
    current_session_closed: 0,
    current_open_trades: 0,
    current_session_open_trades: 0,
    wins: 0,
    losses: 0,
    net_pnl: 0,
    max_drawdown: 0,
    profit_factor: 0,
    current_strategy_level: 0,
    last_trade_activity_time: "",
    adaptive_level_activation_time: "",
    adaptive_strategy_levels: {
      "0": { level: 0, name: "Original Round 3", status: "Active", open: 0, closed: 0, reached: true },
      "1": { level: 1, name: "Slightly Relaxed", status: "Not Reached", open: 0, closed: 0, reached: false },
      "2": { level: 2, name: "Momentum Assisted", status: "Not Reached", open: 0, closed: 0, reached: false },
      "3": { level: 3, name: "Fast Opportunity", status: "Not Reached", open: 0, closed: 0, reached: false },
    },
  };
  return {
    ...data,
    autoValidation: {
      ...(autoStatus ?? {}),
      blocked_reasons: [],
      current_signal_watched: null,
      last_execution_decision: null,
      latest_validation_close_report: null,
      validation_close_reports: [],
      config: {
        ...(config ?? {}),
        allowed_symbols: ["EURUSD", "XAUUSD"],
        min_rr: 2.0,
        strategy_profile: "DEMO_COLLECTION",
        target_closed_trades: TARGET_TRADES,
        target_validation_trades: TARGET_TRADES,
      },
      session: resetSession,
    },
  };
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

function relativeSyncAge(value: unknown): string {
  if (!value) return "Waiting for first sync";
  const timestamp = new Date(String(value)).getTime();
  if (!Number.isFinite(timestamp)) return "Waiting for first sync";
  const seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (seconds < 60) return `Last sync ${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Last sync ${minutes}m ago`;
  return `Last sync ${Math.floor(minutes / 60)}h ago`;
}

function recordAgeMs(value: unknown): number {
  const timestamp = new Date(String(value || "")).getTime();
  return Number.isFinite(timestamp) ? Date.now() - timestamp : Number.POSITIVE_INFINITY;
}

function isRiskNoticeStatus(status: string): boolean {
  return status === "RISK_HALTED" || status === "RISK_CLEARED";
}

function isVisibleRiskNotice(status: string, timestamp: unknown, active = false): boolean {
  if (!isRiskNoticeStatus(status)) return true;
  if (active && status === "RISK_HALTED") return true;
  return recordAgeMs(timestamp) <= RISK_NOTICE_VISIBLE_MS;
}

function formatSyncClock(value: unknown): string {
  if (!value) return "";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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

function validationOpenPositions(positions: ApiRecord[]): ApiRecord[] {
  return positions.filter((position) => VALIDATION_SYMBOLS.has(readText(position, ["symbol"], "").toUpperCase()));
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
  const [reasonRefreshToken, setReasonRefreshToken] = useState(0);
  const requestInFlight = useRef(false);
  const priceRequestInFlight = useRef(false);
  const signalRequestInFlight = useRef(false);
  const runtimeSnapshotRequestInFlight = useRef(false);

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
          niftyTick: "niftyTick" in payload ? recordOrPrevious(payload.niftyTick, current.niftyTick) : current.niftyTick,
          marketScope: "marketScope" in payload ? arrayRecordsOrPrevious(payload.marketScope, current.marketScope, fullSuccess) : current.marketScope,
          clientSignals: "clientSignals" in payload ? recordsOrPrevious(payload.clientSignals, "signals", current.clientSignals, fullSuccess) : current.clientSignals,
          brokerAccounts: "brokerAccounts" in payload ? recordsOrPrevious(payload.brokerAccounts, "accounts", current.brokerAccounts, fullSuccess) : current.brokerAccounts,
          brokerCopyPlans: "brokerCopyReadiness" in payload ? recordsOrPrevious(payload.brokerCopyReadiness, "plans", current.brokerCopyPlans, fullSuccess) : current.brokerCopyPlans,
          currentTerminalAccount: brokerAccounts ? recordOrPrevious(brokerAccounts.current_terminal_account, current.currentTerminalAccount) : current.currentTerminalAccount,
          vantageXauusdStatus: "vantageXauusdStatus" in payload ? recordOrPrevious(payload.vantageXauusdStatus, current.vantageXauusdStatus) : current.vantageXauusdStatus,
          vantageXauusdPreview: "vantageXauusdPreview" in payload ? recordOrPrevious(payload.vantageXauusdPreview, current.vantageXauusdPreview) : current.vantageXauusdPreview,
          openPositions: "openPositions" in payload ? recordsFrom(payload.openPositions, "positions") : current.openPositions,
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
      if (prices.eurusdTick || prices.xauusdTick || prices.niftyTick || prices.marketScope) {
        setData((current) => {
          const eurusdTick = recordOrPrevious(prices.eurusdTick, current.eurusdTick);
          const xauusdTick = recordOrPrevious(prices.xauusdTick, current.xauusdTick);
          const niftyTick = recordOrPrevious(prices.niftyTick, current.niftyTick);
          const marketScope = Array.isArray(prices.marketScope) ? arrayRecordsOrPrevious(prices.marketScope, current.marketScope, false) : current.marketScope;
          if (
            sameJsonValue(eurusdTick, current.eurusdTick) &&
            sameJsonValue(xauusdTick, current.xauusdTick) &&
            sameJsonValue(niftyTick, current.niftyTick) &&
            sameJsonValue(marketScope, current.marketScope)
          ) {
            return current;
          }
          const next = {
            ...current,
            eurusdTick,
            xauusdTick,
            niftyTick,
            marketScope,
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

  const refreshRuntimeSnapshot = useCallback(async () => {
    if (runtimeSnapshotRequestInFlight.current) return;
    runtimeSnapshotRequestInFlight.current = true;
    try {
      const result = await fetchAutoValidationRuntimeSnapshot();
      if (result.ok && result.snapshot) {
        setData((current) => {
          const positions = result.snapshot?.mt5_last_sync && Array.isArray(result.snapshot?.mt5_open_positions)
            ? (result.snapshot.mt5_open_positions.filter((item) => typeof item === "object" && item !== null) as ApiRecord[])
            : current.openPositions;
          const next = { ...current, autoValidation: result.snapshot, openPositions: positions };
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
      runtimeSnapshotRequestInFlight.current = false;
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
    const interval = window.setInterval(() => void refreshPrices(), 5000);
    return () => window.clearInterval(interval);
  }, [refreshPrices]);

  useEffect(() => {
    const interval = window.setInterval(() => void refreshSignals(), 5000);
    return () => window.clearInterval(interval);
  }, [refreshSignals]);

  useEffect(() => {
    void refreshRuntimeSnapshot();
    const interval = window.setInterval(() => void refreshRuntimeSnapshot(), 2000);
    return () => window.clearInterval(interval);
  }, [refreshRuntimeSnapshot]);

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
  const closedTrades = useMemo(() => closedTradesOnly(data.recentTrades), [data.recentTrades]);
  const activeSessionId = currentValidationSessionId(data.autoValidation);
  const clientClosedTrades = useMemo(() => sessionScopedRecords(closedTrades, activeSessionId), [closedTrades, activeSessionId]);
  const clientOpenPositions = useMemo(() => validationOpenPositions(data.openPositions), [data.openPositions]);
  const marketOpen = isMarketOpen(data.eurusdTick);
  const openTradeExists = clientOpenPositions.length > 0 || readNumber(data.journalSummary, ["open_demo_trades"], 0) > 0;
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
  const openFloatingPnl = floatingPnl(clientOpenPositions);
  const lastTrade = closedTrades[0] ?? null;
  const tradeStatus = tradeStatusMessages(selectedMarketOpen, openTradeExists, selectedSignal, formValid);
  const eurusdLive = useLivePrice("EURUSD", data.eurusdTick);
  const xauusdLive = useLivePrice("XAUUSD", data.xauusdTick);
  const niftyLive = useLivePrice("NIFTY50", data.niftyTick ?? findNiftyMarketRecord(data));

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

  async function handleAutoValidationAction(action: AutoValidationAction) {
    if (workingAction !== null) return;
    if (action === "reset-closed-trades") {
      const confirmed = window.confirm("Reset active closed trade records for the current Round 3 session only? This clears current-round outcomes and analytics, but does not affect archived rounds or Round 2 history.");
      if (!confirmed) return;
    }
    setWorkingAction(`auto-validation-${action}`);
    setTradeError(null);
    showToast("loading", autoValidationLoadingMessage(action));
    try {
      const currentAutoValidation = data.autoValidation;
      const recoverable = readText(currentAutoValidation, ["recoverable_session"], "false") === "true";
      const currentSession = asRecord(currentAutoValidation?.session);
      const currentMode = readText(currentSession, ["status"], "");
      const currentSessionId = readText(currentSession, ["session_id", "id", "validation_session_id"], "");
      const currentClosed = readNumber(currentSession, ["current_closed_trades", "current_session_closed"], 0);
      const currentOpen = readNumber(currentSession, ["current_open_trades", "current_session_open"], 0);
      const recoveredClosed = readNumber(currentAutoValidation, ["recovered_closed_trades"], 0);
      const recoveredOpen = readNumber(currentAutoValidation, ["recovered_open_trades"], 0);
      const startPayload: ApiRecord = action === "start" ? { ...ROUND_3_START_PAYLOAD } : {};
      const currentSessionStarted = Boolean(currentSessionId) && !["READY_ROUND_3", "COMPLETED", "STOPPED"].includes(currentMode);
      if (action === "start" && (recoverable || currentSessionStarted || currentOpen > 0 || !["", "IDLE", "OFF", "READY", "READY_ROUND_3", "COMPLETED", "STOPPED"].includes(currentMode))) {
        setToast(null);
        const closed = currentClosed || recoveredClosed;
        const open = currentOpen || recoveredOpen;
        const message = closed > 0 || open > 0 ? `Round 3 already has ${closed} closed and ${open} open trades. Use Resume Validation to continue it.` : "Round 3 validation is already started. Use Resume Validation to continue it.";
        setTradeError(message);
        showToast("error", message);
        return;
      }
      const result =
        action === "start"
          ? await startAutoValidation(startPayload)
          : action === "pause"
            ? await pauseAutoValidation()
            : action === "resume"
              ? await resumeAutoValidation()
              : action === "reset-closed-trades"
                ? await resetAutoValidationClosedTrades()
                : await stopAutoValidation();
      setData((current) => {
        const currentAuto = asRecord(current.autoValidation) ?? {};
        const currentSession = asRecord(currentAuto.session) ?? {};
        const quickControlResponse = action === "pause" || action === "resume";
        const sessionStatus = readText(result, ["session_status"], readText(result, ["validation_status"], ""));
        const nextSession = quickControlResponse
          ? {
              ...currentSession,
              status: sessionStatus === "VALIDATION_IN_PROGRESS" ? "RUNNING" : sessionStatus || readText(currentSession, ["status"], ""),
              session_id: readText(result, ["active_session_id"], readText(currentSession, ["session_id"], "")),
              current_open_trades: readNumber(result, ["open_trades"], readNumber(currentSession, ["current_open_trades"], 0)),
              current_session_open_trades: readNumber(result, ["open_trades"], readNumber(currentSession, ["current_session_open_trades"], 0)),
              current_closed_trades: readNumber(result, ["closed_trades"], readNumber(currentSession, ["current_closed_trades"], 0)),
              current_session_closed: readNumber(result, ["closed_trades"], readNumber(currentSession, ["current_session_closed"], 0)),
            }
          : asRecord(result.session) ?? currentSession;
        const nextAuto = quickControlResponse
          ? { ...currentAuto, ...result, mode: nextSession.status, session: nextSession }
          : result;
        const next = { ...current, autoValidation: nextAuto };
        writeCachedDashboardData(next);
        return next;
      });
      setLastSuccessfulSync(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      if (action === "start" && readText(result, ["status"], "") === "SESSION_ALREADY_STARTED") {
        const message = readText(result, ["message"], "Round 3 validation is already started. Use Resume Validation to continue it.");
        setTradeError(message);
        showToast("error", message);
      } else if (action === "resume" && (readText(result, ["status"], "") === "RESUME_BLOCKED" || result.can_resume === false)) {
        const check = asRecord(result.resume_check);
        const reason = readText(result, ["message"], "") || `Resume failed: ${readText(check, ["block_reason"], "backend did not provide a reason")}`;
        setTradeError(reason);
        showToast("error", reason);
      } else {
        showToast("success", readText(result, ["message"], autoValidationSuccessMessage(action)));
      }
      if (action === "reset-closed-trades") {
        await refresh();
      }
    } catch (error) {
      const message = (action === "resume" || action === "pause") && error instanceof Error ? `${action === "resume" ? "Resume" : "Pause"} failed: backend route error: ${error.message}` : autoValidationErrorMessage(action);
      setTradeError(message);
      showToast("error", message);
    } finally {
      setWorkingAction(null);
    }
  }

  async function handleClientRefresh() {
    const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setCalculatorResetToken((token) => token + 1);
    setReasonRefreshToken((token) => token + 1);
    setLastSuccessfulSync(timestamp);
    setToast(null);
    void Promise.allSettled([refreshPrices(), refreshSignals(), refreshRuntimeSnapshot()]).then((results) => {
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
              niftyLive={niftyLive}
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
              closedTrades={closedTrades}
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
              reasonRefreshToken={reasonRefreshToken}
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
  niftyLive,
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
  niftyLive: LivePriceState;
  onAutoValidationAction: (action: AutoValidationAction) => void;
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
  const target = readNumber(session, ["target_closed_trades", "target_validation_trades"], readNumber(config, ["target_closed_trades", "target_validation_trades"], TARGET_TRADES));
  const closed = actualClosedTradeCount(closedTrades);
  const open = scopedOpenPositions.length;
  const mode = readText(session, ["status"], "");
  const botState = clientBotState(mode, closed, open, target, Boolean(readText(session, ["session_id", "id", "validation_session_id"], "") || mode || closed || open));
  const mt5HealthStatus = readText(mt5Health, ["status"], "").toUpperCase();
  const mt5HealthFailures = readNumber(mt5Health, ["consecutive_failed_health_checks"], 0);
  const mt5Connected = mt5HealthStatus === "MT5_CONNECTED" || mt5HealthFailures < 3;
  const validationSymbol = Array.isArray(config?.allowed_symbols) ? String(config.allowed_symbols[0] ?? "EURUSD") : "EURUSD";
  const quickStartDisabled = workingAction !== null || ["RUNNING", "WAITING_FOR_MT5_RECONNECT"].includes(mode);
  const primaryLive = validationSymbol === "XAUUSD" ? xauusdLive : eurusdLive;
  const accountBalance = numeric(data.account, ["balance"]);

  return (
    <div className="portal-dashboard">
      <section className="portal-stat-grid">
        <PortalStatCard label="EURUSD" value={marketPriceText(eurusdLive.currentPrice)} delta={`${signed(eurusdLive.delta)} (${signed(eurusdLive.deltaPercent)}%)`} live={eurusdLive} />
        <PortalStatCard label="XAUUSD" value={marketPriceText(xauusdLive.currentPrice, 2)} delta={`${signed(xauusdLive.delta, 2)} (${signed(xauusdLive.deltaPercent)}%)`} live={xauusdLive} />
        <PortalStatCard delta={niftyLive.endpointConnected ? `${signed(niftyLive.delta, 2)} (${signed(niftyLive.deltaPercent, 2)}%)` : "Waiting for market feed"} label="NIFTY50" live={niftyLive} value={marketPriceText(niftyLive.currentPrice, 2)} />
        <PortalStatCard label="Floating P&L" value={money(openFloatingPnl)} delta="Open demo positions" />
        <PortalStatCard label="Today's P&L" value={money(todayPnl)} delta="Closed trade journal" />
      </section>

      <section className="portal-main-grid">
        <div className="portal-chart-card">
          <AccountBalanceChart balance={accountBalance} marketOpen={primaryLive.marketOpen} />
          {scopedOpenPositions.length ? <ClientOpenPositionsTable positions={scopedOpenPositions} managedPositions={[]} /> : <EmptyState text="No Active Positions" />}
        </div>

        <PositionCalculatorPanel accountBalance={accountBalance} resetToken={calculatorResetToken} />
      </section>

      <section className="portal-bottom-grid">
        <TradeHistoryPanel trades={data.recentTrades} />
        <MarketHoursCard />
      </section>
    </div>
  );
}

function findNiftyMarketRecord(data: DashboardData): ApiRecord | null {
  return data.marketScope.find((item) => {
    const text = JSON.stringify(item).toUpperCase();
    return text.includes("NIFTY");
  }) ?? null;
}

function niftySnapshot(data: DashboardData): { connected: boolean; currentPrice: number; delta: number; deltaPercent: number; history: LivePricePoint[] } {
  const record = data.niftyTick ?? findNiftyMarketRecord(data);
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
  badge,
  badgeStyle = "default",
  delta,
  label,
  live,
  note,
  value,
}: {
  badge?: string;
  badgeStyle?: "default" | "neutral";
  delta: string | null;
  label: string;
  live?: LivePriceState;
  note?: string;
  value: string;
}) {
  const direction = live?.marketOpen ? live.direction : "flat";
  const badgeText = badge ?? (live ? (live.endpointConnected ? (live.marketOpen ? "MT5 Live" : live.statusMessage || "Market Closed") : "Waiting") : "Live");
  return (
    <div className="portal-stat-card">
      <div className="portal-stat-header">
        <p className="premium-metric-label">{label}</p>
        <span className={`premium-badge ${badgeStyle === "neutral" ? "neutral" : ""}`}>{badgeText}</span>
      </div>
      <p className={`portal-stat-value price-flash-${direction}`}>{value}</p>
      {delta ? <p className={`portal-stat-delta ${direction}`}>{delta}</p> : null}
      {note ? <p className="portal-stat-note">{note}</p> : null}
    </div>
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
              <span className={session.isOpen ? "open" : ""}>{session.countdown}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="timezone-note">Times shown in Asia/Kolkata</p>
      {londonOpen && newYorkOpen ? <div className="overlap-banner">London + New York overlap - High liquidity window</div> : null}
    </section>
  );
}

function TraderProfileView({ closedTrades, data, onRefresh }: { closedTrades: ApiRecord[]; data: DashboardData; onRefresh: () => void }) {
  const [editing, setEditing] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);
  const broker = asRecord(data.brokerAccounts[0]) ?? {};
  const config = asRecord(data.autoValidation?.config);
  const mode = asRecord(data.executionMode);
  const round2Trades = round2ClosedTrades(data, closedTrades);
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
      <RoundResultsCard data={data} detailsTitle="Round 2 Trade Details" filename="round-2-results.csv" title="Round 2 Results" trades={round2Trades} />
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

type ChatRequestError = Error & { rateLimited?: boolean; retryAfterSeconds?: number };

const RAW_GROQ_ERROR_PATTERN = /(groq|rate.?limit|tokens per minute|retry-after|x-ratelimit|api key|organization|returned 4\d\d|returned 5\d\d|model.*llama|raw provider)/i;

function isRawGroqErrorMessage(message: ChatMessage): boolean {
  return message.role === "assistant" && RAW_GROQ_ERROR_PATTERN.test(message.text);
}

function sanitizeChatMessages(value: unknown): ChatMessage[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (!item || typeof item !== "object") return null;
      const record = item as Record<string, unknown>;
      const id = typeof record.id === "string" ? record.id : `stored-${index}`;
      const role = record.role === "user" || record.role === "assistant" ? record.role : null;
      const text = typeof record.text === "string" ? record.text.trim() : "";
      return role && text ? ({ id, role, text } as ChatMessage) : null;
    })
    .filter((message): message is ChatMessage => message !== null)
    .filter((message) => !isRawGroqErrorMessage(message));
}

function PortalChatView({ data }: { data: DashboardData }) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      return sanitizeChatMessages(JSON.parse(window.sessionStorage.getItem(CHAT_STORAGE_KEY) ?? "[]"));
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [cooldownNow, setCooldownNow] = useState(0);
  const [reasonMessages, setReasonMessages] = useState<ReasonMessage[]>([]);
  const cooldownSeconds = Math.max(0, Math.ceil((cooldownUntil - cooldownNow) / 1000));
  const coolingDown = cooldownSeconds > 0;
  useEffect(() => {
    const cleanMessages = messages.filter((message) => !isRawGroqErrorMessage(message));
    if (cleanMessages.length !== messages.length) {
      setMessages(cleanMessages);
      return;
    }
    window.sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(cleanMessages));
  }, [messages]);
  useEffect(() => {
    if (!coolingDown) return undefined;
    setCooldownNow(Date.now());
    const interval = window.setInterval(() => setCooldownNow(Date.now()), 250);
    return () => window.clearInterval(interval);
  }, [coolingDown, cooldownUntil]);
  useEffect(() => {
    let cancelled = false;
    const loadReasons = async () => {
      const records = await fetchReasonMessages();
      if (!cancelled) setReasonMessages(normalizeReasonMessages(records).slice(0, 50));
    };
    void loadReasons();
    const interval = window.setInterval(loadReasons, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);
  const send = async () => {
    const question = input.trim();
    if (!question || typing || coolingDown) return;
    const userMessage = { id: `${Date.now()}-user`, role: "user" as const, text: question };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setTyping(true);
    const diagnosticAnswer = answerValidatorDiagnosticQuestion(question, reasonMessages);
    if (diagnosticAnswer) {
      setMessages((current) => [...current, { id: `${Date.now()}-assistant`, role: "assistant", text: diagnosticAnswer }]);
      setTyping(false);
      return;
    }
    try {
      const response = await sendPortalChatMessage({
        context: buildChatContext(data, reasonMessages),
        messages: messages.slice(-3).map((message) => ({ role: message.role, text: message.text })),
        question,
      });
      setMessages((current) => [...current, { id: `${Date.now()}-assistant`, role: "assistant", text: response.reply }]);
    } catch (error) {
      const chatError = error as ChatRequestError;
      if (chatError.rateLimited) {
        const seconds = Math.max(10, Math.ceil(chatError.retryAfterSeconds ?? 10));
        setCooldownUntil(Date.now() + seconds * 1000);
        setCooldownNow(Date.now());
        setMessages((current) => [
          ...current,
          {
            id: `${Date.now()}-assistant-cooldown`,
            role: "assistant",
            text: `Assistant is cooling down. Try again in ${seconds} seconds.`,
          },
        ]);
        return;
      }
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-assistant-error`,
          role: "assistant",
          text: "The assistant is temporarily busy. Please try again in a few seconds.",
        },
      ]);
    } finally {
      setTyping(false);
    }
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
      {coolingDown ? <p className="chat-cooldown">Assistant is cooling down. Try again in {cooldownSeconds} seconds.</p> : null}
      <div className="chat-input-row">
        <input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void send(); }} placeholder="Ask about your trading system..." />
        <button className="portal-primary-button !m-0 !w-auto !px-5" disabled={!input.trim() || typing || coolingDown} onClick={() => void send()} type="button">Send</button>
      </div>
    </section>
  );
}

function buildChatContext(data: DashboardData, reasons: ReasonMessage[] = []): string {
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const mt5Health = asRecord(autoStatus?.mt5_health);
  const latestSignal = data.clientSignals[0] ?? null;
  const closedTradeCount = actualClosedTradeCount(data.recentTrades.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED"));
  const eurusdStatus = data.eurusdTick ? { price: numeric(data.eurusdTick, ["last", "price", "current_price", "ltp", "bid", "ask"], Number.NaN), status: readText(data.eurusdTick, ["market_status", "status", "freshness"], "available") } : null;
  const xauusdStatus = data.xauusdTick ? { price: numeric(data.xauusdTick, ["last", "price", "current_price", "ltp", "bid", "ask"], Number.NaN), status: readText(data.xauusdTick, ["market_status", "status", "freshness"], "available") } : null;
  const context = {
    account: {
      balance: numeric(data.account, ["balance"]),
      equity: numeric(data.account, ["equity"]),
    },
    markets: { EURUSD: eurusdStatus, XAUUSD: xauusdStatus },
    mt5: friendlyText(mt5Health, ["status"], "not available"),
    validation: {
      status: friendlyText(session, ["status"], "not started"),
      closedTrades: closedTradeCount,
      openTrades: validationOpenPositions(data.openPositions).length,
      latestSignal: latestSignal
        ? {
            symbol: readText(latestSignal, ["symbol"], ""),
            status: readText(latestSignal, ["execution_status", "status_level", "signal"], ""),
            reason: readText(latestSignal, ["setup_reason", "reason", "what_needs_to_happen_next"], ""),
          }
        : null,
    },
    brokers: data.brokerAccounts.slice(0, 3).map((account) => ({ broker: readText(account, ["broker", "broker_name", "name"], "Unavailable"), status: readText(account, ["status", "connection_status"], "Unavailable") })),
    trades: {
      count: data.recentTrades.length,
      summary: data.journalSummary,
    },
    latestReason: reasons.slice(0, 1).map((reason) => ({ symbol: reason.symbol, status: reason.status, reason: reason.reason, timestamp: reason.timestamp }))[0] ?? null,
    validatorDiagnostics: buildChatValidatorDiagnostics(reasons),
  };
  return JSON.stringify(context);
}

function questionSymbol(question: string): string | null {
  const upper = question.toUpperCase();
  if (upper.includes("EURUSD")) return "EURUSD";
  if (upper.includes("XAUUSD")) return "XAUUSD";
  if (upper.includes("NIFTY50") || upper.includes("NIFTY 50")) return "NIFTY50";
  return null;
}

function hasValidatorDiagnostics(message: ReasonMessage): boolean {
  return Boolean(
    message.timeframe ||
      message.candles_loaded != null ||
      message.candles_required != null ||
      message.data_source ||
      message.validation_status ||
      message.rejection_reason,
  );
}

function findValidatorDiagnostic(question: string, reasons: ReasonMessage[]): ReasonMessage | null {
  const symbol = questionSymbol(question);
  const candidates = symbol ? reasons.filter((reason) => reason.symbol.toUpperCase() === symbol) : reasons;
  return candidates.find(hasValidatorDiagnostics) ?? null;
}

function answerValidatorDiagnosticQuestion(question: string, reasons: ReasonMessage[]): string | null {
  const normalized = question.toLowerCase();
  const asksCandles = normalized.includes("candles") || normalized.includes("candle");
  const asksRejected = normalized.includes("why") && normalized.includes("reject");
  const asksTimeframe = normalized.includes("timeframe") && (normalized.includes("failed") || normalized.includes("fail") || normalized.includes("which"));
  if (!asksCandles && !asksRejected && !asksTimeframe) return null;
  const diagnostic = findValidatorDiagnostic(question, reasons);
  if (!diagnostic) return "Validator diagnostics are not available for this decision.";
  if (asksCandles) {
    if (diagnostic.candles_loaded === null && diagnostic.candles_required === null) return "Validator diagnostics are not available for this decision.";
    const loaded = diagnostic.candles_loaded !== null && diagnostic.candles_loaded !== undefined ? `${diagnostic.candles_loaded}` : "not available";
    const required = diagnostic.candles_required !== null && diagnostic.candles_required !== undefined ? `${diagnostic.candles_required}` : "not available";
    return `${diagnostic.symbol} loaded ${loaded} candles. Required candles: ${required}.`;
  }
  if (asksTimeframe) {
    if (!diagnostic.timeframe) return "Validator diagnostics are not available for this decision.";
    return `${diagnostic.symbol} validation timeframe: ${diagnostic.timeframe}.`;
  }
  if (asksRejected) {
    const reason = diagnostic.rejection_reason || (diagnostic.status === "Rejected" ? diagnostic.reason : "");
    if (!reason) return "Validator diagnostics are not available for this decision.";
    return `${diagnostic.symbol} was rejected because ${reason.replace(/\.$/, "")}.`;
  }
  return null;
}

function buildChatValidatorDiagnostics(reasons: ReasonMessage[]): ApiRecord[] {
  const seen = new Set<string>();
  return reasons
    .filter(hasValidatorDiagnostics)
    .filter((reason) => {
      const key = reason.symbol.toUpperCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 3)
    .map((reason) => ({
      symbol: reason.symbol,
      timeframe: reason.timeframe || null,
      candles_loaded: reason.candles_loaded ?? null,
      candles_required: reason.candles_required ?? null,
      data_source: reason.data_source || null,
      validation_status: reason.validation_status || reason.status,
      rejection_reason: reason.rejection_reason || null,
    }));
}

function buildBotAnswer(question: string, data: DashboardData): string {
  const q = question.toLowerCase();
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const mt5Health = asRecord(autoStatus?.mt5_health);
  const closedTradeCount = actualClosedTradeCount(data.recentTrades.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED"));
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
    return `Validation status is ${friendlyText(session, ["status"], "not started")}. Closed trades: ${closedTradeCount}. Open trades: ${validationOpenPositions(data.openPositions).length}.`;
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
  onAutoValidationAction: (action: AutoValidationAction) => void;
  onRefresh: () => void;
  onSync: (action: "positions" | "lifecycle" | "exit-management") => void;
  openFloatingPnl: number;
  reasonRefreshToken: number;
  scopedOpenPositions: ApiRecord[];
  todayPnl: number;
  workingAction: string | null;
}) {
  const round3Data = round3DashboardData(props.data);
  const round3Trades = round3ClosedTrades(round3Data, props.closedTrades);
  const round3Positions = round3OpenPositions(round3Data, props.scopedOpenPositions);
  return (
    <div className="portal-test-shell">
      <TestEnvironmentTitleCard />
      <RoundResultsCard data={round3Data} detailsTitle={`${validationRoundTitle(round3Data).replace(" Results", "")} Trade Details`} emptyAsZero filename={`${validationRoundTitle(round3Data).toLowerCase().replace(/\s+/g, "-")}.csv`} title={validationRoundTitle(round3Data)} trades={round3Trades} />
      <ClientDashboardView {...props} data={round3Data} closedTrades={round3Trades} loading={false} scopedOpenPositions={round3Positions} showHero={false} />
      <TradeIntelligenceSection closedTrades={round3Trades} reasonContexts={buildReasonContexts(round3Data)} />
      <AdaptiveStrategyEvolutionCard data={round3Data} />
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

function tradeDirection(trade: ApiRecord): string {
  return readText(trade, ["side", "type", "direction"], "BUY").toUpperCase() === "SELL" ? "SELL" : "BUY";
}

function round2TradeCsvRow(trade: ApiRecord, index: number): string[] {
  return [
    friendlyText(trade, ["mt5_ticket", "ticket", "trade_id", "id"], String(index + 1)),
    friendlyText(trade, ["symbol"], "EURUSD"),
    tradeDirection(trade),
    tradeResultLabel(trade),
    money(tradePnl(trade)),
    marketPriceText(readNumber(trade, ["entry_price", "entryPrice", "openPrice", "entry"], Number.NaN), friendlyText(trade, ["symbol"], "EURUSD") === "XAUUSD" ? 2 : 5),
    marketPriceText(readNumber(trade, ["close_price", "exitPrice", "closePrice", "exit"], Number.NaN), friendlyText(trade, ["symbol"], "EURUSD") === "XAUUSD" ? 2 : 5),
    exitReasonForTrade(trade),
    formatTradeTime(readText(trade, ["openTime", "open_time", "opened_at", "entry_time"], "")),
    formatTradeTime(readText(trade, ["closed_at", "closeTime", "close_time", "exit_time"], "")),
  ];
}

function downloadCsv(filename: string, rows: string[][]): void {
  const csv = rows.map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function tradeHistoryTimestamp(trade: ApiRecord): string {
  return readText(trade, ["updated_at", "closed_at", "close_time", "opened_at", "open_time", "created_at"], "");
}

function tradeRoundLabel(trade: ApiRecord): string {
  const explicit = readText(trade, ["round_label", "round", "validation_round"], "");
  if (explicit) return explicit.replace(/^ROUND_(\d+)$/i, "Round $1");
  const sessionId = tradeSessionId(trade);
  if (ARCHIVED_ROUND_2_SESSION_IDS.has(sessionId)) return "Round 2";
  const profile = readText(trade, ["strategy_profile"], "").toUpperCase();
  if (profile.includes("DEMO_COLLECTION")) return "Round 3";
  return sessionId ? "Validation" : "Manual";
}

function TradeHistoryPanel({ trades: allTrades }: { trades: ApiRecord[] }) {
  const [filter, setFilter] = useState<"All" | "EURUSD" | "XAUUSD" | "Wins" | "Losses">("All");
  const trades = [...allTrades].sort((a, b) => tradeHistoryTimestamp(b).localeCompare(tradeHistoryTimestamp(a)));
  const filtered = trades.filter((trade) => {
    if (filter === "All") return true;
    if (filter === "EURUSD") return readText(trade, ["symbol"], "EURUSD").toUpperCase() === "EURUSD";
    if (filter === "XAUUSD") return readText(trade, ["symbol"], "EURUSD").toUpperCase() === "XAUUSD";
    if (filter === "Wins") return readText(trade, ["result"], "").toUpperCase() === "WIN";
    return readText(trade, ["result"], "").toUpperCase() === "LOSS";
  });
  const wins = trades.filter((trade) => readText(trade, ["result"], "").toUpperCase() === "WIN").length;
  const losses = trades.filter((trade) => readText(trade, ["result"], "").toUpperCase() === "LOSS").length;
  const netPnl = trades.reduce((sum, trade) => sum + readNumber(trade, ["net_pnl", "total_pnl", "profit_loss", "pnl"], 0), 0);
  const exportCSV = () => {
    const header = ["Ticket", "Round", "Session ID", "Symbol", "Direction", "Entry Price", "Current/Close Price", "SL", "TP", "Status", "Result", "P&L", "Opened Time", "Closed Time"];
    const rows = trades.map((trade) => [
      readText(trade, ["mt5_ticket", "ticket"], ""),
      tradeRoundLabel(trade),
      tradeSessionId(trade),
      readText(trade, ["symbol"], "EURUSD"),
      readText(trade, ["side", "type"], ""),
      String(readNumber(trade, ["entry_price", "entryPrice"], 0)),
      String(readNumber(trade, ["current_price", "currentPrice", "close_price", "exitPrice"], 0)),
      String(readNumber(trade, ["stop_loss", "stopLoss"], 0)),
      String(readNumber(trade, ["take_profit", "takeProfit"], 0)),
      readText(trade, ["status"], ""),
      readText(trade, ["result"], ""),
      String(readNumber(trade, ["net_pnl", "total_pnl", "profit_loss", "pnl"], 0)),
      readText(trade, ["opened_at", "open_time", "created_at"], ""),
      readText(trade, ["closed_at", "closeTime", "close_time"], ""),
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
              <tr>{["Ticket", "Round", "Session ID", "Symbol", "Direction", "Entry Price", "Current/Close Price", "SL", "TP", "Status", "Result", "P&L", "Opened Time", "Closed Time"].map((item) => <th key={item}>{item}</th>)}</tr>
            </thead>
            <tbody>
              {filtered.map((trade, index) => {
                const type = readText(trade, ["side", "type"], "BUY");
                const result = readText(trade, ["result"], "").toUpperCase();
                const pnl = readNumber(trade, ["net_pnl", "total_pnl", "profit_loss", "pnl"], 0);
                const symbol = readText(trade, ["symbol"], "EURUSD");
                const digits = symbol === "XAUUSD" ? 2 : 5;
                const status = readText(trade, ["status"], "OPEN").toUpperCase();
                const currentOrClosePrice = readNumber(trade, ["current_price", "currentPrice", "close_price", "exitPrice"], Number.NaN);
                return (
                  <tr key={readText(trade, ["trade_id", "id", "mt5_ticket"], String(index))}>
                    <td>{readText(trade, ["mt5_ticket", "ticket"], "-")}</td>
                    <td>{tradeRoundLabel(trade)}</td>
                    <td className="trade-history-session">{tradeSessionId(trade) || "-"}</td>
                    <td>{symbol}</td>
                    <td><span className={`trade-type-pill ${type === "SELL" ? "sell" : "buy"}`}>{type}</span></td>
                    <td>{marketPriceText(readNumber(trade, ["entry_price", "entryPrice"], Number.NaN), digits)}</td>
                    <td>{marketPriceText(currentOrClosePrice, digits)}</td>
                    <td>{marketPriceText(readNumber(trade, ["stop_loss", "stopLoss"], Number.NaN), digits)}</td>
                    <td>{marketPriceText(readNumber(trade, ["take_profit", "takeProfit"], Number.NaN), digits)}</td>
                    <td>{status}</td>
                    <td><span className={`result-pill ${result === "LOSS" ? "loss" : result === "WIN" ? "win" : ""}`}>{result || "-"}</span></td>
                    <td className={pnlClass(pnl)}>{money(pnl)}</td>
                    <td>{formatTradeTime(readText(trade, ["opened_at", "open_time", "created_at"], ""))}</td>
                    <td>{formatTradeTime(readText(trade, ["closed_at", "closeTime", "close_time"], ""))}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="trade-history-empty">
          <strong>No trades recorded yet.</strong>
          <span>Trades will appear here automatically as validation opens, updates, and closes positions.</span>
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

function RoundResultsCard({
  data,
  detailsTitle,
  emptyAsZero = false,
  filename,
  title,
  trades,
}: {
  data: DashboardData;
  detailsTitle: string;
  emptyAsZero?: boolean;
  filename: string;
  title: string;
  trades: ApiRecord[];
}) {
  const [expanded, setExpanded] = useState(false);
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const config = asRecord(autoStatus?.config);
  const target = title.includes("Round 2") ? TARGET_TRADES : readNumber(session, ["target_closed_trades", "target_validation_trades"], readNumber(config, ["target_closed_trades", "target_validation_trades"], TARGET_TRADES));
  const resultTrades = closedTradesOnly(trades);
  const actualClosedTrades = actualClosedTradeCount(resultTrades);
  const actualWins = tradeWinCount(resultTrades);
  const actualWinRate = actualClosedTrades ? (actualWins / actualClosedTrades) * 100 : 0;
  const netPnl = title.includes("Round 2") ? round2NetPnl(resultTrades) : resultTrades.reduce((sum, trade) => sum + tradePnl(trade), 0);
  const hasTrades = actualClosedTrades > 0;
  const downloadReport = () => {
    const header = ["Ticket", "Symbol", "Direction", "Result", "P&L", "Entry Price", "Exit Price", "Exit Reason", "Open Time", "Close Time"];
    const rows = resultTrades.map((trade, index) => round2TradeCsvRow(trade, index));
    downloadCsv(filename, [header, ...rows]);
  };
  return (
    <section className="round1-card">
      <div className="premium-test-header">
        <div>
          <p className="premium-section-eyebrow">EURUSD Test Results</p>
          <h2 className="premium-section-title">{title}</h2>
          {!hasTrades ? <p className="test-results-empty">{title} trades will appear here from the trade journal.</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="portal-panel-tab round2-results-action" disabled={!hasTrades} onClick={() => setExpanded((value) => !value)} type="button">{hasTrades ? (expanded ? "Hide Trades" : "View Trades") : "No trades yet"}</button>
          <button className="portal-panel-tab round2-results-action" disabled={!hasTrades} onClick={downloadReport} type="button">Download Report</button>
        </div>
      </div>
      <div className="premium-stat-grid">
        <ClientMetric label="Target" value={String(target)} compact />
        <ClientMetric label="Closed" value={hasTrades || emptyAsZero ? String(actualClosedTrades) : "-"} compact />
        <ClientMetric label="Win Rate" value={hasTrades ? `${actualWinRate.toFixed(2)}%` : emptyAsZero ? "0%" : "-"} compact />
        <ClientMetric label="Net P&L" value={hasTrades || emptyAsZero ? money(netPnl) : "-"} compact />
      </div>
      {expanded ? <EurusdTradeHistory trades={resultTrades} title={detailsTitle} onClose={() => setExpanded(false)} /> : null}
    </section>
  );
}

function EurusdTradeHistory({ trades, title, onClose }: { trades: ApiRecord[]; title: string; onClose: () => void }) {
  return (
    <div className="test-trade-history">
      <div className="test-trade-history-header">
        <h3>{title}</h3>
        <button onClick={onClose} type="button">Close x</button>
      </div>
      {trades.length ? (
        <div className="test-trade-table-wrap">
          <table className="test-trade-table">
            <thead>
              <tr>{["Ticket", "Symbol", "Direction", "Result", "P&L", "Entry Price", "Exit Price", "Exit Reason", "Open Time", "Close Time"].map((item) => <th key={item}>{item}</th>)}</tr>
            </thead>
            <tbody>
              {trades.map((trade, index) => {
                const pnl = tradePnl(trade);
                const symbol = friendlyText(trade, ["symbol"], "EURUSD");
                const digits = symbol === "XAUUSD" ? 2 : 5;
                return (
                  <tr key={readText(trade, ["trade_id", "id", "mt5_ticket", "ticket"], String(index))}>
                    <td>{friendlyText(trade, ["mt5_ticket", "ticket", "trade_id", "id"], "No ticket")}</td>
                    <td>{symbol}</td>
                    <td><span className={`trade-type-pill ${tradeDirection(trade) === "SELL" ? "sell" : "buy"}`}>{tradeDirection(trade)}</span></td>
                    <td><span className={`result-pill ${tradeResultLabel(trade) === "LOSS" ? "loss" : "win"}`}>{tradeResultLabel(trade)}</span></td>
                    <td className={pnlClass(pnl)}>{money(pnl)}</td>
                    <td>{marketPriceText(readNumber(trade, ["entry_price", "entryPrice", "openPrice", "entry"], Number.NaN), digits)}</td>
                    <td>{marketPriceText(readNumber(trade, ["close_price", "exitPrice", "closePrice", "exit"], Number.NaN), digits)}</td>
                    <td>{exitReasonForTrade(trade)}</td>
                    <td>{formatTradeTime(readText(trade, ["openTime", "open_time", "opened_at", "entry_time"], ""))}</td>
                    <td>{formatTradeTime(readText(trade, ["closed_at", "closeTime", "close_time", "exit_time"], ""))}</td>
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
            <p className="premium-test-note">Round 3 controls and verification data will appear when the latest dashboard snapshot is ready.</p>
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
  reasonRefreshToken = 0,
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
  onAutoValidationAction: (action: AutoValidationAction) => void;
  onRefresh: () => void;
  onSync: (action: "positions" | "lifecycle" | "exit-management") => void;
  openFloatingPnl: number;
  reasonRefreshToken?: number;
  scopedOpenPositions: ApiRecord[];
  showHero?: boolean;
  todayPnl: number;
  workingAction: string | null;
}) {
  const autoStatus = asRecord(data.autoValidation);
  const session = asRecord(autoStatus?.session);
  const config = asRecord(autoStatus?.config);
  const mt5Health = asRecord(autoStatus?.mt5_health);
  const riskHalt = asRecord(autoStatus?.risk_halt) ?? asRecord(session?.risk_halt_diagnostics);
  const exitManagement = asRecord(autoStatus?.exit_management);
  const target = readNumber(session, ["target_closed_trades", "target_validation_trades"], readNumber(config, ["target_closed_trades", "target_validation_trades"], TARGET_TRADES));
  const actualClosedTrades = actualClosedTradeCount(closedTrades);
  const closed = actualClosedTrades;
  const open = scopedOpenPositions.length;
  const remaining = Math.max(0, target - actualClosedTrades);
  const progress = target > 0 ? Math.min(100, Math.round((closed / target) * 100)) : 0;
  const wins = tradeWinCount(closedTrades);
  const losses = tradeLossCount(closedTrades);
  const winRate = actualClosedTrades ? (wins / actualClosedTrades) * 100 : 0;
  const mode = readText(session, ["status"], "");
  const sessionNote = readText(session, ["session_note"], "");
  const allowedSymbols = Array.isArray(config?.allowed_symbols) ? config.allowed_symbols.map(String).join(", ") : "EURUSD";
  const sessionId = readText(session, ["session_id", "id", "validation_session_id"], "");
  const riskHaltMessage = readText(riskHalt, ["message"], "");
  const riskHaltStatus = readText(riskHalt, ["status"], "").toUpperCase();
  const riskHaltTimestamp = readText(riskHalt, ["timestamp"], "");
  const riskHaltActive = riskHaltStatus === "RISK_HALTED" || mode === "HALTED_RISK";
  const showRiskHaltNotice = Boolean(riskHaltMessage && isVisibleRiskNotice(riskHaltStatus, riskHaltTimestamp, riskHaltActive));
  const controlsDisabled = workingAction !== null;
  const recoverableSession = readText(autoStatus, ["recoverable_session"], "false") === "true";
  const hasValidationSession = Boolean(sessionId || mode || closed > 0 || open > 0);
  const currentSessionStarted = Boolean(sessionId) && !["READY_ROUND_3", "COMPLETED", "STOPPED"].includes(mode);
  const startDisabled = controlsDisabled || currentSessionStarted || recoverableSession || open > 0 || !["", "IDLE", "OFF", "READY", "READY_ROUND_3", "COMPLETED", "STOPPED"].includes(mode);
  const botState = clientBotState(mode, actualClosedTrades, open, target, hasValidationSession);
  const mt5HealthStatus = readText(mt5Health, ["status"], "").toUpperCase();
  const mt5HealthFailures = readNumber(mt5Health, ["consecutive_failed_health_checks"], 0);
  const mt5Connected = mt5HealthStatus === "MT5_CONNECTED" || mt5HealthFailures < 3;
  const mt5ActuallyDisconnected = ["MT5_DISCONNECTED", "DISCONNECTED", "CONNECTION_FAILED", "WAITING_FOR_MT5_RECONNECT"].includes(mt5HealthStatus) && mt5HealthFailures >= 3;
  const mt5LastSyncValue =
    readText(mt5Health, ["last_tick_time"], "") ||
    readText(mt5Health, ["timestamp"], "") ||
    readText(autoStatus, ["lifecycle_sync", "timestamp"], "") ||
    readText(session, ["mt5_disconnect_recovered_at", "risk_halt_cleared_at"], "");
  const mt5LastSyncClock = formatSyncClock(mt5LastSyncValue);
  const closeReports = Array.isArray(autoStatus?.validation_close_reports) ? (autoStatus.validation_close_reports.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const recentClosed = mergeClosedTrades(closedTrades, closeReports).slice(0, 5);
  const reasonContexts = useMemo(() => buildReasonContexts(data), [data]);

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
        <StatusStripItem label="MT5 Status" value={mt5Connected ? `Connected • Last sync ${mt5LastSyncClock || "recorded"}` : mt5ActuallyDisconnected ? "Disconnected" : "Checking"} tone={mt5Connected ? "healthy" : mt5ActuallyDisconnected ? "danger" : "warning"} />
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
            <p className="premium-test-note">{closedTradeProgressText(actualClosedTrades, target)}</p>
            <p className="premium-test-note">{sessionNote || ROUND_3_NOTE}</p>
          </div>
          <strong className="premium-test-progress">{progress}%</strong>
        </div>
        <div className="premium-progress-track">
          <div className="premium-progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="premium-sub-grid">
          <div className="premium-sub-card">
            <p className="premium-section-eyebrow">Round 3 validation</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <ClientMetric label="Target Closed Trades" value={String(target)} compact />
              <ClientMetric label="Closed Trades" value={String(actualClosedTrades)} compact />
              <ClientMetric label="Remaining Trades" value={String(remaining)} compact />
              <ClientMetric label="Open Trades" value={String(open)} compact />
              <ClientMetric label="Validation Symbols" value={allowedSymbols} compact />
            </div>
          </div>
          <div className="premium-sub-card">
            <ClientSectionTitle eyebrow="Controls" title="Validation actions" />
            {showRiskHaltNotice ? (
              <p className={`premium-risk-halt-message ${riskHaltActive ? "active" : "cleared"}`}>
                {riskHaltActive ? `Risk halted: ${riskHaltMessage.replace(/^Risk halted:\s*/i, "")}` : riskHaltMessage}
              </p>
            ) : null}
            <div className="premium-control-grid mt-5">
              <ClientButton disabled={startDisabled} loading={workingAction === "auto-validation-start"} onClick={() => onAutoValidationAction("start")}>Start Validation</ClientButton>
              <ClientButton disabled={controlsDisabled || !["PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} loading={workingAction === "auto-validation-resume"} onClick={() => onAutoValidationAction("resume")}>Resume Validation</ClientButton>
              <ClientButton disabled={controlsDisabled || !["RUNNING", "VALIDATION_IN_PROGRESS", "WAITING_FOR_OPEN_TRADES_TO_CLOSE", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC", "PAUSED_REQUIRES_USER_RESUME"].includes(mode)} loading={workingAction === "auto-validation-pause"} onClick={() => onAutoValidationAction("pause")}>Pause</ClientButton>
              <ClientButton disabled={controlsDisabled || !["RUNNING", "VALIDATION_IN_PROGRESS", "PAUSED", "WAITING_FOR_OPEN_TRADES_TO_CLOSE", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} loading={workingAction === "auto-validation-stop"} onClick={() => onAutoValidationAction("stop")}>Stop</ClientButton>
              <ClientButton disabled={controlsDisabled} loading={workingAction === "dashboard-refresh"} onClick={onRefresh}>Refresh</ClientButton>
              <ClientButton disabled={controlsDisabled} loading={workingAction === "auto-validation-reset-closed-trades"} onClick={() => onAutoValidationAction("reset-closed-trades")}>Reset Closed Trades</ClientButton>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
        <div className="premium-panel">
          <p className="premium-section-eyebrow">Performance summary</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <ClientMetric label="Wins" value={String(wins)} valueClass="text-emerald-200" compact />
            <ClientMetric label="Losses" value={String(losses)} valueClass="text-rose-200" compact />
            <ClientMetric label="Win Rate" value={`${winRate.toFixed(2)}%`} compact />
            <ClientMetric label="Net P&L" value={money(readNumber(session, ["net_pnl"], 0))} valueClass={pnlClass(readNumber(session, ["net_pnl"], 0))} compact />
            <ClientMetric label="Profit Factor" value={readNumber(session, ["profit_factor"], 0).toFixed(2)} compact />
            <ClientMetric label="Max Drawdown" value={money(readNumber(session, ["max_drawdown"], 0))} compact />
          </div>
        </div>
        <ValidationReasonPanel contexts={reasonContexts} refreshToken={reasonRefreshToken} />
      </section>

      <LiveScanStatusCard data={data} />

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
          <tr>{["Ticket", "Symbol", "Direction", "Entry Price", "Current Price", "P&L", "Stop Loss", "Take Profit", "Trade Age", "Exit Status"].map((item) => <th className="px-4 py-2" key={item}>{item}</th>)}</tr>
        </thead>
        <tbody>
          {positions.map((position, index) => {
            const ticket = readText(position, ["ticket"], "");
            const managed = managedPositions.find((item) => readText(item, ["ticket"], "") === ticket) ?? null;
            const pnl = readNumber(position, ["floating_pnl", "profit"], 0);
            return (
              <tr key={`${ticket || index}-${index}`}>
                <td>{ticket || "Unavailable"}</td>
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
          <tr>{["Ticket", "Symbol", "Direction", "Result", "P&L", "Exit Reason", "Closed Time"].map((item) => <th className="px-4 py-2" key={item}>{item}</th>)}</tr>
        </thead>
        <tbody>
          {trades.map((trade, index) => {
            const pnl = readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl", "pnl"], 0);
            const ticket = readText(trade, ["mt5_ticket", "ticket", "trade_id"], "");
            const result = friendlyText(trade, ["result"], pnl >= 0 ? "WIN" : "LOSS");
            return (
              <tr key={`${readText(trade, ["trade_id", "mt5_ticket", "ticket"], String(index))}-${index}`}>
                <td>{ticket || "Unavailable"}</td>
                <td>{friendlyText(trade, ["symbol"], "Waiting")}</td>
                <td>{friendlyText(trade, ["side", "direction", "action"], "Waiting")}</td>
                <td>{result}</td>
                <td className={pnlClass(pnl)}>{money(pnl)}</td>
                <td>{friendlyText(trade, ["exit_reason"], "Closed")}</td>
                <td>{formatTradeTime(readText(trade, ["closed_at", "close_time", "generated_at"], ""))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TradeIntelligenceSection({ closedTrades, reasonContexts }: { closedTrades: ApiRecord[]; reasonContexts: ReasonContext[] }) {
  const trades = closedTrades.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED");
  const hasRound3Statistics = trades.length > 0;
  const reasonMessages = hasRound3Statistics ? normalizeReasonMessages(reasonContexts).filter(isRound3EdgeScoreReasonMessage) : [];
  const autopsyRows = trades.slice(0, 8);
  const lossPatterns = aggregatePatterns(trades.filter((trade) => tradePnl(trade) < 0).flatMap(lossFeatureLabelsForTrade));
  const rejectionBreakdown = aggregatePatterns(reasonMessages.filter((message) => message.status === "Rejected").map(rejectionReasonLabel));
  const featureImpactRows = buildFeatureImpactRows(trades);
  const conclusionRows = buildStrategyConclusionRows(trades, lossPatterns, rejectionBreakdown, featureImpactRows);
  const winningDnaRows = buildWinningDnaSummaryRows(trades);

  return (
    <section>
      <div className="grid gap-6">
        <div className="premium-sub-card p-5 lg:p-6">
          <ClientSectionTitle eyebrow="Research Dashboard" title="TRADE INTELLIGENCE" />
          {!hasRound3Statistics ? (
            <EmptyState text="No Round 3 statistics available yet." />
          ) : autopsyRows.length ? (
            <div className="premium-table-wrap mt-4">
              <table className="premium-table text-xs">
                <thead>
                  <tr>{["Ticket", "Symbol", "Result", "Entry Quality", "Missing Confirmation", "Why SL Was Hit", "Suggested Fix"].map((item) => <th className="px-3 py-2" key={item}>{item}</th>)}</tr>
                </thead>
                <tbody>
                  {autopsyRows.map((trade, index) => (
                    <tr key={`${readText(trade, ["mt5_ticket", "ticket", "trade_id"], String(index))}-${index}`}>
                      <td className="px-3 py-2">{friendlyText(trade, ["mt5_ticket", "ticket", "trade_id"], "No ticket")}</td>
                      <td className="px-3 py-2">{friendlyText(trade, ["symbol"], "Symbol pending")}</td>
                      <td className={`px-3 py-2 ${tradePnl(trade) >= 0 ? "text-emerald-200" : "text-rose-200"}`}>{tradeResultLabel(trade)}</td>
                      <td className="px-3 py-2" title={entrySetupForTrade(trade)}>{tradeAutopsyText(trade, "entry_quality", "Pending")}</td>
                      <td className="px-3 py-2" title={autopsyConfirmationTooltip(trade)}>{tradeAutopsyText(trade, "missing_confirmation", "None")}</td>
                      <td className="px-3 py-2 text-slate-100" title={rootCauseForTrade(trade)}>{tradeAutopsyText(trade, "why_sl_was_hit", compactRootCauseForTrade(trade))}</td>
                      <td className="px-3 py-2 text-blue-100">{tradeAutopsyText(trade, "suggested_rule_fix", "Monitor repeat pattern.")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState text="—" />
          )}

          {hasRound3Statistics ? <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <div>
              <p className="text-[0.68rem] font-bold uppercase tracking-[0.14em] text-blue-300">Loss Pattern Analysis</p>
              <PatternBars patterns={lossPatterns} emptyText="—" />
            </div>
            <div>
              <p className="text-[0.68rem] font-bold uppercase tracking-[0.14em] text-blue-300">Validation Rejection Breakdown</p>
              <PatternBars patterns={rejectionBreakdown} emptyText="—" />
            </div>
          </div> : null}

          {hasRound3Statistics ? <FeatureImpactTable rows={featureImpactRows} /> : null}
        </div>

        <div className="premium-sub-card p-5 lg:p-6">
          <ClientSectionTitle eyebrow="Research Dashboard" title="STRATEGY CONCLUSIONS" />
          {hasRound3Statistics ? <StrategyConclusionTable rows={conclusionRows} winningDnaRows={winningDnaRows} /> : (
            <div className="mt-4">
              <EmptyState text="No Round 3 statistics available yet." />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function AdaptiveStrategyEvolutionCard({ data }: { data: DashboardData }) {
  const session = validationSession(data);
  const symbolState = asRecord(session?.symbol_adaptive_state) ?? {};
  const legacyCurrentLevel = readNumber(session, ["current_strategy_level"], 0);
  const legacyLevelsRecord = asRecord(session?.adaptive_strategy_levels) ?? {};
  const definitions = [
    { level: 0, name: "Original Round 3" },
    { level: 1, name: "Slightly Relaxed" },
    { level: 2, name: "Momentum Assisted" },
    { level: 3, name: "Fast Opportunity" },
  ];
  const symbols = Object.keys(symbolState).length ? Object.keys(symbolState).sort() : ["EURUSD"];
  const rowsForSymbol = (symbol: string) => {
    const state = asRecord(symbolState[symbol]);
    const currentLevel = readNumber(state, ["current_level"], legacyCurrentLevel);
    const levelsRecord = asRecord(state?.levels) ?? legacyLevelsRecord;
    return definitions.map((definition) => {
      const record = asRecord(levelsRecord[String(definition.level)]);
      const open = readNumber(record, ["open"], 0);
      const closed = readNumber(record, ["closed"], 0);
      const reached = Boolean(record?.reached) || definition.level <= currentLevel;
      const worked = open + closed > 0;
      const status =
        definition.level === currentLevel
          ? "Active"
          : worked
            ? "Worked"
            : reached
              ? "Not Worked"
              : "Not Reached";
      return { ...definition, open, closed, status, currentLevel };
    });
  };
  return (
    <section className="premium-sub-card p-5 lg:p-6">
      <ClientSectionTitle eyebrow="Round 3" title="Adaptive Strategy Evolution" />
      <div className="mt-4 grid gap-5 xl:grid-cols-2">
        {symbols.map((symbol) => (
          <div key={symbol}>
            <p className="mb-2 text-[0.68rem] font-bold uppercase tracking-[0.14em] text-blue-300">{symbol}</p>
            <p className="mb-3 text-xs font-semibold text-slate-400">
              {readText(asRecord(symbolState[symbol]), ["current_level_reason", "adaptive_level_reason"], "Original Round 3 baseline.")}
            </p>
            <div className="premium-table-wrap">
              <table className="premium-table text-xs">
                <thead>
                  <tr>{["Level", "Status", "Open", "Closed"].map((item) => <th className="px-3 py-2" key={item}>{item}</th>)}</tr>
                </thead>
                <tbody>
                  {rowsForSymbol(symbol).map((row) => (
                    <tr className={row.level === row.currentLevel ? "bg-blue-400/[0.08]" : ""} key={`${symbol}-${row.level}`}>
                      <td className="px-3 py-2 font-bold text-white">Level {row.level} - {row.name}</td>
                      <td className={`px-3 py-2 font-bold ${adaptiveLevelStatusClass(row.status)}`}>{row.status}</td>
                      <td className="px-3 py-2">{row.open}</td>
                      <td className="px-3 py-2">{row.closed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function latestScanDiagnostics(data: DashboardData): ApiRecord[] {
  const autoStatus = asRecord(data.autoValidation);
  const root = asRecord(autoStatus?.latest_scan_diagnostics) ?? asRecord(asRecord(autoStatus?.session)?.latest_scan_diagnostics) ?? {};
  return ["EURUSD", "XAUUSD"].map((symbol) => ({ symbol, ...(asRecord(root[symbol]) ?? {}) }));
}

function scanMissingList(scan: ApiRecord): string[] {
  const raw = Array.isArray(scan.missing_confirmations) ? scan.missing_confirmations : [];
  return raw.map((item) => String(item)).filter(Boolean).slice(0, 4);
}

type ScanChecklistItem = { label: string; passed: boolean };

function scanBoolean(scan: ApiRecord, keys: string[]): boolean {
  return keys.some((key) => {
    const value = scan[key];
    if (value === true) return true;
    const textValue = String(value ?? "").trim().toUpperCase();
    return ["TRUE", "YES", "OK", "READY", "CLEAN", "PASSED", "ALIGNED", "PRESENT"].includes(textValue);
  });
}

function scanChecklist(scan: ApiRecord): ScanChecklistItem[] {
  const rawChecklist = Array.isArray(scan.checklist_items) ? scan.checklist_items : [];
  if (rawChecklist.length) {
    return rawChecklist
      .map((item) => {
        const record = asRecord(item);
        return {
          label: readText(record, ["label"], ""),
          passed: record?.passed === true,
        };
      })
      .filter((item) => item.label);
  }
  const htfText = readText(scan, ["htf_alignment", "htf_bias"], "").toUpperCase();
  const htfPassed = scanBoolean(scan, ["htf_alignment", "trend_alignment"]) || (Boolean(htfText) && !["NOT_ALIGNED", "UNCLEAR", "WAIT", "NONE", "FALSE"].includes(htfText));
  const momentumPassed = scanBoolean(scan, ["momentum", "pullback_retest"]);
  const structurePassed = scanBoolean(scan, ["bos", "liquidity_sweep", "fvg", "fvg_retest", "structure_confirmation"]);
  return [
    { label: "HTF alignment", passed: htfPassed },
    { label: "Momentum / Pullback", passed: momentumPassed },
    { label: "Structure confirmation", passed: structurePassed },
    { label: "RR >= 2", passed: scanBoolean(scan, ["rr_ok"]) },
    { label: "Spread clean", passed: scanBoolean(scan, ["spread_ok"]) },
  ];
}

function scanChecklistPassed(scan: ApiRecord): number {
  const checklist = scanChecklist(scan);
  return readNumber(scan, ["checklist_passed"], checklist.filter((item) => item.passed).length);
}

function scanChecklistTotal(scan: ApiRecord): number {
  const checklist = scanChecklist(scan);
  return readNumber(scan, ["checklist_total"], checklist.length || 5);
}

function scanNeeds(scan: ApiRecord): string[] {
  return scanChecklist(scan)
    .filter((item) => !item.passed)
    .map((item) => item.label);
}

function closestScan(scanRows: ApiRecord[]): ApiRecord | null {
  const available = scanRows.filter((scan) => readText(scan, ["timestamp"], "") && !scanIsStale(scan));
  if (!available.length) return null;
  return [...available].sort((left, right) => {
    const scoreDelta = scanChecklistPassed(right) - scanChecklistPassed(left);
    if (scoreDelta !== 0) return scoreDelta;
    return readNumber(left, ["missing_count"], 99) - readNumber(right, ["missing_count"], 99);
  })[0];
}

function scanTimestamp(scan: ApiRecord): string {
  return readText(scan, ["last_scan_timestamp", "timestamp"], "");
}

function scanIsStale(scan: ApiRecord): boolean {
  const timestamp = scanTimestamp(scan);
  if (!timestamp) return true;
  const parsed = new Date(timestamp).getTime();
  return !Number.isFinite(parsed) || Date.now() - parsed > 60000;
}

function scanTimeLabel(scan: ApiRecord): string {
  const timestamp = scanTimestamp(scan);
  if (!timestamp) return "—";
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function LiveScanStatusCard({ data }: { data: DashboardData }) {
  const scans = latestScanDiagnostics(data);
  const runtimeHealth = asRecord(asRecord(data.autoValidation)?.runtime_health) ?? {};
  const closest = closestScan(scans);
  const hasAnyScan = scans.some((scan) => Boolean(readText(scan, ["timestamp"], "")));
  const allScansStale = hasAnyScan && scans.every((scan) => !readText(scan, ["timestamp"], "") || scanIsStale(scan));
  const runtimeScanAge = readNumber(runtimeHealth, ["last_scan_age_seconds"], 0);
  const runtimeScanStale = runtimeScanAge > 60;
  const mt5SyncLive = runtimeHealth.mt5_sync_loop_alive === true;
  const scanStale = allScansStale || runtimeScanStale;
  const closestNeeds = closest ? scanNeeds(closest).slice(0, 2) : [];
  return (
    <section className="premium-panel">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="premium-section-eyebrow">Round 3</p>
          <p className="premium-metric-value text-white">LIVE SCAN STATUS</p>
        </div>
        {scanStale ? (
          <div className="rounded-lg border border-amber-400/20 bg-amber-400/[0.06] px-3 py-2 text-xs font-bold leading-5 text-amber-100">
            {mt5SyncLive ? "Scan stale, MT5 sync live" : "Scan stale — waiting for fresh scan"}
          </div>
        ) : closest ? (
          <>
            <div className="rounded-lg border border-blue-400/15 bg-blue-400/[0.06] px-3 py-2 text-xs font-bold leading-5 text-blue-100">
              <span className="whitespace-nowrap">Closest: {readText(closest, ["symbol"], "-")} — {readNumber(closest, ["score"], 0)}/{readNumber(closest, ["required_score"], 5)}</span>
              <span className="ml-2 text-slate-300">Needs: {closestNeeds.length ? closestNeeds.join(" + ") : "ready"}</span>
            </div>
          </>
        ) : null}
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        {scans.map((scan) => {
          const symbol = readText(scan, ["symbol"], "—");
          const hasScan = Boolean(readText(scan, ["timestamp"], ""));
          const missing = scanMissingList(scan);
          const stale = hasScan && scanIsStale(scan);
          const checklist = scanChecklist(scan);
          return (
            <div className="rounded-xl border border-slate-800/80 bg-[#08111F] p-4" key={symbol}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-black text-white">{symbol}</p>
                  <p className="mt-1 text-xs font-bold text-slate-400">
                    {hasScan ? `Level ${readNumber(scan, ["adaptive_level"], 0)} • ${readText(scan, ["decision"], "PENDING")}` : "No scan yet"}
                  </p>
                </div>
                <p className={`font-mono text-lg font-black ${stale ? "text-amber-200" : "text-blue-100"}`}>{hasScan ? (stale ? "STALE DATA" : `${readNumber(scan, ["score"], 0)}/${readNumber(scan, ["required_score"], 5)}`) : "—"}</p>
              </div>
              {hasScan ? (
                <>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="scan-status-pill">Last scan: {scanTimeLabel(scan)}</span>
                    <span className="scan-status-pill">Duration: {Math.max(1, readNumber(scan, ["total_scan_ms"], 1))}ms</span>
                    <span className={`scan-status-pill ${stale ? "warning" : "good"}`}>Status: {stale ? "Stale data" : "Fresh"}</span>
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {checklist.map((item) => (
                      <div className={`scan-check-row ${item.passed ? "passed" : "missing"}`} key={`${symbol}-${item.label}`}>
                        <span>{item.passed ? "✓" : "✕"}</span>
                        <strong>{item.label}</strong>
                      </div>
                    ))}
                  </div>
                  <div className="hidden">
                    <ClientMetric label="Last scan" value={scanTimeLabel(scan)} compact />
                    <ClientMetric label="Duration" value={`${Math.max(1, readNumber(scan, ["total_scan_ms"], 1))}ms`} compact />
                    <ClientMetric label="History" value={readText(scan, ["history_ready"], "") === "true" || scan.history_ready === true ? "Ready" : "Waiting"} compact />
                    <ClientMetric label="Spread" value={scan.spread_ok === true ? "Clean" : "Blocked"} compact />
                    <ClientMetric label="RR" value={scan.rr_ok === true ? "OK" : "Blocked"} compact />
                    <ClientMetric label="Status" value={stale ? "Stale" : "Fresh"} compact />
                  </div>
                  <div className="hidden">
                    <p className="text-[0.68rem] font-black uppercase tracking-[0.14em] text-slate-500">Missing</p>
                    <p className="mt-1 text-sm font-bold text-slate-200">{missing.length ? missing.join(", ") : "—"}</p>
                    <p className="mt-1 text-xs font-bold text-slate-500">{readText(scan, ["estimated_readiness"], readText(scan, ["reject_reason"], ""))}</p>
                  </div>
                </>
              ) : (
                <EmptyState text="Run a per-symbol read-only scan to populate diagnostics." />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function adaptiveLevelStatusClass(status: string): string {
  if (status === "Active") return "text-blue-200";
  if (status === "Worked") return "text-emerald-200";
  if (status === "Not Worked") return "text-amber-200";
  return "text-slate-500";
}

function PatternBars({ emptyText, patterns }: { emptyText: string; patterns: IntelligencePattern[] }) {
  return (
    <>
      {patterns.length ? (
        <div className="mt-3 grid gap-3">
          {patterns.map((pattern) => (
            <div key={pattern.label}>
              <div className="flex items-center justify-between gap-3 text-xs font-bold">
                <span className="text-slate-100">{pattern.label}</span>
                <span className={patternValueClass(pattern.percentage)}>{pattern.count} / {pattern.percentage.toFixed(0)}%</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full border border-blue-900/40 bg-[#020815]">
                <div className={`h-full rounded-full ${patternBarClass(pattern.percentage)}`} style={{ width: `${Math.max(4, pattern.percentage)}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text={emptyText} />
      )}
    </>
  );
}

function patternBarClass(percentage: number): string {
  if (percentage > 50) return "bg-gradient-to-r from-rose-700 to-rose-400";
  if (percentage >= 25) return "bg-gradient-to-r from-amber-600 to-orange-300";
  return "bg-gradient-to-r from-[#173A8A] to-[#255EDC]";
}

function patternValueClass(percentage: number): string {
  const color = percentage > 50 ? "text-rose-200" : percentage >= 25 ? "text-amber-200" : "text-blue-200";
  return `font-mono ${color}`;
}

function TradeSetupTags({ trade }: { trade: ApiRecord }) {
  return (
    <div className="flex max-w-[360px] flex-wrap gap-1.5">
      {setupTagsForTrade(trade).map((tag) => (
        <span className={`rounded border px-2 py-0.5 text-[0.62rem] font-black uppercase tracking-[0.08em] ${tradeTagClass(tag)}`} key={tag}>
          {tag}
        </span>
      ))}
    </div>
  );
}

function tradeTagClass(tag: string): string {
  const text = tag.toUpperCase().replace(/\s+/g, "_");
  if (text === "DEMO_COLLECTION") return "border-blue-400/25 bg-blue-400/10 text-blue-100";
  if (text.startsWith("RR_")) return "border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-200";
  if (text.includes("MISSING") || text === "OUTSIDE_SESSION") return "border-rose-400/30 bg-rose-400/10 text-rose-200";
  if (text.includes("PRESENT") || text === "TREND_ALIGNED" || text === "LONDON/NY") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
  return "border-slate-500/30 bg-slate-500/10 text-slate-200";
}

function FeatureImpactTable({ rows }: { rows: FeatureImpactRow[] }) {
  const unavailable = "—";
  return (
      <div className="premium-table-wrap mt-5">
        <table className="premium-table text-xs">
          <thead>
            <tr>
              <th>Feature</th>
              <th>State</th>
              <th>Trades</th>
              <th>Wins</th>
              <th>Losses</th>
              <th>Win Rate</th>
              <th>Net P&L</th>
              <th>Insight</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.feature}-${row.state}`}>
                <td className="px-3 py-2 font-bold text-white">{row.feature}</td>
                <td className="px-3 py-2 text-blue-100">{row.state}</td>
                <td className="px-3 py-2">{row.hasData ? row.trades : unavailable}</td>
                <td className="px-3 py-2">{row.hasData ? row.wins : unavailable}</td>
                <td className="px-3 py-2">{row.hasData ? row.losses : unavailable}</td>
                <td className="px-3 py-2">{row.hasData ? `${row.winRate.toFixed(1)}%` : unavailable}</td>
                <td className={`px-3 py-2 font-bold ${row.hasData ? pnlClass(row.netPnl) : "text-slate-400"}`}>{row.hasData ? money(row.netPnl) : unavailable}</td>
                <td className="px-3 py-2 text-slate-200">{row.insight}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
  );
}

function StrategyConclusionTable({ rows, winningDnaRows }: { rows: StrategyConclusionRow[]; winningDnaRows: WinningDnaSummaryRow[] }) {
  const diagnosticRows = rows.filter((row) => row.type !== "AI");
  const aiRows = rows.filter((row) => row.type === "AI");
  return (
    <>
      <StrategyRowsTable rows={diagnosticRows} />
      <WinningDnaSummaryTable rows={winningDnaRows} />
      <StrategyRowsTable rows={aiRows} />
    </>
  );
}

function StrategyRowsTable({ rows }: { rows: StrategyConclusionRow[] }) {
  if (!rows.length) return <EmptyState text="—" />;
  return (
    <div className="premium-table-wrap mt-4">
      <table className="premium-table text-xs">
        <thead>
          <tr>{["Type", "Feature Combination", "Trades", "Wins", "Losses", "Win Rate", "Net P&L", "Observation"].map((item) => <th className="px-3 py-2" key={item}>{item}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr className={conclusionRowClass(row.type)} key={`${row.type}-${row.label}`}>
              <td className="px-3 py-2"><ConclusionBadge type={row.type} /></td>
              <td className="px-3 py-2 font-bold text-white">{row.label}</td>
              <td className={`px-3 py-2 ${row.trades === "—" ? "text-slate-500" : ""}`}>{row.trades}</td>
              <td className={`px-3 py-2 ${row.wins === "—" ? "text-slate-500" : ""}`}>{row.wins}</td>
              <td className={`px-3 py-2 ${row.losses === "—" ? "text-slate-500" : ""}`}>{row.losses}</td>
              <td className={`px-3 py-2 ${row.winRate === "—" ? "text-slate-500" : ""}`}>{row.winRate}</td>
              <td className={`px-3 py-2 font-bold ${row.netPnlTone !== null ? pnlClass(row.netPnlTone) : "text-slate-400"}`}>{row.netPnl}</td>
              <td className="px-3 py-2 text-slate-200">{row.observation}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WinningDnaSummaryTable({ rows }: { rows: WinningDnaSummaryRow[] }) {
  return (
    <>
      <p className="mt-5 text-[0.68rem] font-bold uppercase tracking-[0.14em] text-emerald-200">Winning DNA</p>
      <div className="premium-table-wrap mt-2">
        <table className="premium-table text-xs">
          <thead>
            <tr>{["Feature Combination", "Trades", "Wins", "Win Rate", "Average RR", "Observation"].map((item) => <th className="px-3 py-2" key={item}>{item}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className="bg-emerald-400/[0.035]" key={row.label}>
                <td className="px-3 py-2 font-bold text-white">{row.label}</td>
                <td className={`px-3 py-2 ${isDash(row.trades) ? "text-slate-500" : ""}`}>{row.trades}</td>
                <td className={`px-3 py-2 ${isDash(row.wins) ? "text-slate-500" : ""}`}>{row.wins}</td>
                <td className={`px-3 py-2 ${isDash(row.winRate) ? "text-slate-500" : ""}`}>{row.winRate}</td>
                <td className={`px-3 py-2 ${isDash(row.averageRr) ? "text-slate-500" : "font-bold text-fuchsia-200"}`}>{row.averageRr}</td>
                <td className="px-3 py-2 text-slate-200">{row.observation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function isDash(value: string): boolean {
  return value === "—" || value === "â€”";
}

function conclusionRowClass(type: StrategyConclusionRow["type"]): string {
  if (type === "WINNING") return "bg-emerald-400/[0.035]";
  if (type === "LOSS") return "bg-rose-400/[0.04]";
  if (type === "REJECTION") return "bg-amber-400/[0.04]";
  return "bg-blue-400/[0.035]";
}

function ConclusionBadge({ type }: { type: StrategyConclusionRow["type"] }) {
  const className =
    type === "WINNING"
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
      : type === "LOSS"
        ? "border-rose-400/30 bg-rose-400/10 text-rose-200"
        : type === "REJECTION"
          ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
          : "border-blue-400/30 bg-blue-400/10 text-blue-200";
  return <span className={`inline-flex rounded border px-2 py-1 text-[0.62rem] font-black uppercase tracking-[0.12em] ${className}`}>{type}</span>;
}

function cleanAnalysisText(value: string): string {
  const cleaned = value.replace(/_/g, " ").replace(/\s+/g, " ").replace(/\.\.+/g, ".").trim();
  if (!cleaned || /^(unknown|null|undefined|unspecified reason)$/i.test(cleaned) || /\[object Object\]/i.test(cleaned)) return "";
  return cleaned.replace(/\b([A-Za-z][A-Za-z0-9-]*)\s+\1\b/gi, "$1");
}

function nestedRecord(record: ApiRecord | null, key: string): ApiRecord | null {
  return asRecord(record?.[key]);
}

function tradeMetadata(trade: ApiRecord): { approval: ApiRecord | null; components: ApiRecord | null; exitManagement: ApiRecord | null; market: ApiRecord | null } {
  const metadata = nestedRecord(trade, "strategy_metadata");
  return {
    approval: nestedRecord(metadata, "approval_audit"),
    components: nestedRecord(metadata, "strategy_components"),
    exitManagement: nestedRecord(trade, "exit_management"),
    market: nestedRecord(metadata, "market_structure_state"),
  };
}

function tradePnl(trade: ApiRecord): number {
  return readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl", "pnl"], 0);
}

function tradeResultLabel(trade: ApiRecord): string {
  const result = cleanAnalysisText(readText(trade, ["result"], ""));
  if (result) return result.toUpperCase();
  return tradePnl(trade) >= 0 ? "WIN" : "LOSS";
}

function tradeAutopsy(trade: ApiRecord): ApiRecord {
  return asRecord(trade.autopsy) ?? {};
}

function tradeAutopsyText(trade: ApiRecord, key: string, fallback = ""): string {
  return cleanAnalysisText(readText(tradeAutopsy(trade), [key], "")) || fallback;
}

function autopsyConfirmations(trade: ApiRecord, key: "confirmations_present" | "confirmations_missing"): string[] {
  const value = tradeAutopsy(trade)[key];
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function autopsyConfirmationTooltip(trade: ApiRecord): string {
  const present = autopsyConfirmations(trade, "confirmations_present");
  const missing = autopsyConfirmations(trade, "confirmations_missing");
  return `Present: ${present.length ? present.join(", ") : "None"} | Missing: ${missing.length ? missing.join(", ") : "None"}`;
}

function entrySetupForTrade(trade: ApiRecord): string {
  const { approval } = tradeMetadata(trade);
  return cleanAnalysisText(readText(approval, ["final_approval_reason"], "") || readText(trade, ["setup_reason", "notes"], "")) || "Entry setup recorded without additional notes.";
}

function setupTagsForTrade(trade: ApiRecord): string[] {
  const { approval, components } = tradeMetadata(trade);
  const tags: string[] = [];
  const rawSetup = entrySetupForTrade(trade);
  const profile = cleanAnalysisText(readText(approval, ["strategy_profile", "profile"], "") || readText(trade, ["strategy_profile", "profile"], ""));
  if (profile) tags.push(profile.toUpperCase().replace(/\s+/g, "_"));
  else if (rawSetup.toUpperCase().includes("DEMO COLLECTION")) tags.push("DEMO_COLLECTION");
  const bos = passFailState(trade, "bos_result", "bos");
  const sweep = passFailState(trade, "liquidity_sweep_result", "liquidity_sweep");
  const fvg = passFailState(trade, "fvg_result", "fvg");
  const trend = trendStateForTrade(trade);
  const session = sessionStateForTrade(trade);
  if (bos !== "unknown") tags.push(`BOS ${bos === "present" ? "PRESENT" : "MISSING"}`);
  if (sweep !== "unknown") tags.push(`LIQUIDITY SWEEP ${sweep === "present" ? "PRESENT" : "MISSING"}`);
  if (fvg !== "unknown") tags.push(`FVG ${fvg === "present" ? "PRESENT" : "MISSING"}`);
  if (trend !== "unknown") tags.push(trend === "aligned" ? "TREND ALIGNED" : "TREND NOT ALIGNED");
  if (session !== "unknown") tags.push(session === "london_ny" ? "LONDON/NY" : "OUTSIDE_SESSION");
  const rr = readNumber(approval, ["risk_reward", "risk_reward_ratio", "rr"], readNumber(components, ["risk_reward", "risk_reward_ratio", "rr"], Number.NaN));
  if (Number.isFinite(rr)) tags.push(`RR ${rr.toFixed(1)}`);
  return tags.length ? tags.slice(0, 7) : ["Diagnostics Pending"];
}

function exitReasonForTrade(trade: ApiRecord): string {
  const { exitManagement } = tradeMetadata(trade);
  return cleanAnalysisText(readText(exitManagement, ["last_exit_reason", "last_exit_action"], "") || readText(trade, ["exit_reason", "close_reason"], "")) || "Closed by lifecycle sync";
}

function compactRootCauseForTrade(trade: ApiRecord): string {
  const exitReason = exitReasonForTrade(trade).toLowerCase();
  const bos = passFailState(trade, "bos_result", "bos");
  const sweep = passFailState(trade, "liquidity_sweep_result", "liquidity_sweep");
  const fvg = passFailState(trade, "fvg_result", "fvg");
  const session = sessionStateForTrade(trade);
  if (tradePnl(trade) >= 0) {
    if (exitReason.includes("tp") || exitReason.includes("take profit")) return bos === "present" ? "TP after BOS confirmation" : "TP after confirmation";
    return "Won despite advisory warnings";
  }
  if (exitReason.includes("stop") || exitReason.includes("sl")) return bos === "missing" ? "Stop loss after BOS missing" : "Stop loss after BOS confirmation";
  if (session === "outside") return "Session weakness";
  if (exitReason.includes("stale") || exitReason.includes("time")) return "Time exit before continuation";
  if (sweep === "missing") return "Weak liquidity confirmation";
  if (bos === "missing") return "Stop loss after BOS missing";
  if (fvg === "missing") return "Weak confirmation";
  return "Weak liquidity confirmation";
}

function requirementLabels(record: ApiRecord | null): string[] {
  const items = Array.isArray(record?.missing_requirements) ? record?.missing_requirements : Array.isArray(record?.relaxed_blockers) ? record?.relaxed_blockers : [];
  return items
    .map((item) => {
      const object = asRecord(item);
      return cleanAnalysisText(readText(object, ["label", "code"], ""));
    })
    .filter(Boolean);
}

function rootCauseForTrade(trade: ApiRecord): string {
  const { approval, components } = tradeMetadata(trade);
  const exitReason = exitReasonForTrade(trade);
  const requirements = requirementLabels(approval);
  const session = cleanAnalysisText(readText(components, ["session"], ""));
  if (tradePnl(trade) < 0) {
    if (requirements.length) return `${exitReason}; watch ${requirements.slice(0, 2).join(" and ")}.`;
    if (session) return `${exitReason}; session condition was ${session}.`;
    return `${exitReason}; review entry quality and exit timing.`;
  }
  return requirements.length ? `Won while advisory checks remained: ${requirements.slice(0, 2).join(" and ")}.` : `${exitReason}; setup completed with positive P&L.`;
}

function lossReasonForTrade(trade: ApiRecord): string {
  const { approval } = tradeMetadata(trade);
  return requirementLabels(approval)[0] || exitReasonForTrade(trade);
}

function lossFeatureLabelsForTrade(trade: ApiRecord): string[] {
  const labels: string[] = [];
  const autopsyMissing = autopsyConfirmations(trade, "confirmations_missing");
  if (autopsyMissing.length) {
    autopsyMissing.forEach((item) => labels.push(item));
    return labels;
  }
  if (passFailState(trade, "bos_result", "bos") === "missing") labels.push("BOS missing");
  if (passFailState(trade, "liquidity_sweep_result", "liquidity_sweep") === "missing") labels.push("Liquidity sweep missing");
  if (passFailState(trade, "fvg_result", "fvg") === "missing") labels.push("FVG missing");
  if (trendStateForTrade(trade) === "not_aligned") labels.push("Trend not aligned");
  if (sessionStateForTrade(trade) === "outside") labels.push("No session bonus");
  return labels.length ? labels : [lossReasonForTrade(trade)];
}

function rejectionReasonLabel(message: ReasonMessage): string {
  const text = cleanAnalysisText(message.rejection_reason || message.reason);
  if (isLegacyStrategyDiagnostic(text)) return "";
  return text || "Validation checks did not pass";
}

function isRound3EdgeScoreReasonMessage(message: ReasonMessage): boolean {
  const combined = [
    message.reason,
    message.rejection_reason,
    message.decision_reason,
    message.validation_status,
    String(message.confirmation_score ?? ""),
    String(message.confirmation_required ?? ""),
  ].join(" ");
  if (isLegacyStrategyDiagnostic(combined)) return false;
  return /score|confirmation|RR|risk|spread|history|edge|ROUND_3|BOS|FVG|liquidity|trend/i.test(combined);
}

function isLegacyStrategyDiagnostic(value: string): boolean {
  const text = value.toLowerCase();
  const mentionsLegacyConfidenceGate = text.includes("confidence") && (text.includes("75") || text.includes("threshold") || text.includes("needs"));
  const mentionsHardSessionGate = text.includes("outside") && (text.includes("london") || text.includes("new york") || text.includes("ny"));
  const mentionsOrderBlockGate = text.includes("order block") && text.includes("not confirmed");
  return mentionsLegacyConfidenceGate || mentionsHardSessionGate || mentionsOrderBlockGate;
}

function aggregatePatterns(labels: string[]): IntelligencePattern[] {
  const counts = new Map<string, number>();
  labels.map(cleanAnalysisText).filter(Boolean).forEach((label) => counts.set(label, (counts.get(label) ?? 0) + 1));
  const total = [...counts.values()].reduce((sum, count) => sum + count, 0);
  if (!total) return [];
  return [...counts.entries()]
    .map(([label, count]) => ({ count, label, percentage: (count / total) * 100 }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
    .slice(0, 5);
}

function passFailState(trade: ApiRecord, approvalKey: string, componentKey: string): "present" | "missing" | "unknown" {
  const { approval, components } = tradeMetadata(trade);
  const result = cleanAnalysisText(readText(approval, [approvalKey], "")).toLowerCase();
  if (["pass", "passed", "present", "confirmed", "true"].includes(result)) return "present";
  if (["fail", "failed", "missing", "false"].includes(result)) return "missing";
  const component = components?.[componentKey];
  if (typeof component === "boolean") return component ? "present" : "missing";
  const componentText = cleanAnalysisText(readText(components, [componentKey], "")).toLowerCase();
  if (["present", "confirmed", "pass", "true"].includes(componentText)) return "present";
  if (["missing", "fail", "false"].includes(componentText)) return "missing";
  const setupText = cleanAnalysisText(readText(trade, ["setup_type", "entry_setup", "entry_reason"], "")).toLowerCase();
  if (setupText) {
    if (componentKey === "bos") return setupText.includes("bos") || setupText.includes("structure") ? "present" : "missing";
    if (componentKey === "fvg") return setupText.includes("fvg") || setupText.includes("imbalance") ? "present" : "missing";
    if (componentKey === "liquidity_sweep") return setupText.includes("liquidity") || setupText.includes("sweep") ? "present" : "missing";
  }
  return "unknown";
}

function trendStateForTrade(trade: ApiRecord): "aligned" | "not_aligned" | "unknown" {
  const { components, market } = tradeMetadata(trade);
  const side = cleanAnalysisText(readText(trade, ["side", "direction", "order_type"], "")).toUpperCase();
  const componentBias = cleanAnalysisText(readText(components, ["bias", "trend_alignment"], "")).toUpperCase();
  const marketBias = cleanAnalysisText(readText(market, ["trend_bias", "higher_timeframe_bias"], "")).toUpperCase();
  const bias = componentBias || marketBias;
  if (!bias) return "unknown";
  if (["ALIGNED", "TRUE", "PASS", "PASSED"].includes(bias)) return "aligned";
  if (["NOT ALIGNED", "MISALIGNED", "FALSE", "FAIL", "FAILED"].includes(bias)) return "not_aligned";
  if (!side) return "unknown";
  return bias.includes(side) ? "aligned" : "not_aligned";
}

function sessionStateForTrade(trade: ApiRecord): "london_ny" | "outside" | "unknown" {
  const session = cleanAnalysisText(readText(tradeMetadata(trade).components, ["session"], "")).toLowerCase();
  if (!session) return "unknown";
  if (session.includes("outside")) return "outside";
  if (session.includes("london") || session.includes("new york") || session.includes("ny")) return "london_ny";
  return "unknown";
}

function featureImpactRow(
  trades: ApiRecord[],
  feature: string,
  state: string,
  predicate: (trade: ApiRecord) => boolean,
): FeatureImpactRow {
  const matchingTrades = trades.filter(predicate);
  const wins = matchingTrades.filter((trade) => tradePnl(trade) >= 0).length;
  const losses = matchingTrades.length - wins;
  const netPnl = matchingTrades.reduce((sum, trade) => sum + tradePnl(trade), 0);
  const winRate = matchingTrades.length ? (wins / matchingTrades.length) * 100 : 0;
  const hasData = matchingTrades.length > 0;
  const lossRate = matchingTrades.length ? (losses / matchingTrades.length) * 100 : 0;
  const insight = hasData ? `${losses} of ${matchingTrades.length} lost (${lossRate.toFixed(0)}%).` : "—";
  return { feature, hasData, insight, losses, netPnl, state, trades: matchingTrades.length, winRate, wins };
}

function buildFeatureImpactRows(trades: ApiRecord[]): FeatureImpactRow[] {
  return [
    featureImpactRow(trades, "BOS", "Present", (trade) => passFailState(trade, "bos_result", "bos") === "present"),
    featureImpactRow(trades, "BOS", "Missing", (trade) => passFailState(trade, "bos_result", "bos") === "missing"),
    featureImpactRow(trades, "Liquidity Sweep", "Present", (trade) => passFailState(trade, "liquidity_sweep_result", "liquidity_sweep") === "present"),
    featureImpactRow(trades, "Liquidity Sweep", "Missing", (trade) => passFailState(trade, "liquidity_sweep_result", "liquidity_sweep") === "missing"),
    featureImpactRow(trades, "FVG", "Present", (trade) => passFailState(trade, "fvg_result", "fvg") === "present"),
    featureImpactRow(trades, "FVG", "Missing", (trade) => passFailState(trade, "fvg_result", "fvg") === "missing"),
    featureImpactRow(trades, "Trend Alignment", "Aligned", (trade) => trendStateForTrade(trade) === "aligned"),
    featureImpactRow(trades, "Trend Alignment", "Not Aligned", (trade) => trendStateForTrade(trade) === "not_aligned"),
    featureImpactRow(trades, "Session Bonus", "Active", (trade) => sessionStateForTrade(trade) === "london_ny"),
    featureImpactRow(trades, "Session Bonus", "Inactive", (trade) => sessionStateForTrade(trade) === "outside"),
  ];
}

function strategyDnaRow(trades: ApiRecord[], label: string, predicate: (trade: ApiRecord) => boolean): StrategyDnaRow | null {
  const matchingTrades = trades.filter(predicate);
  if (!matchingTrades.length) return null;
  const wins = matchingTrades.filter((trade) => tradePnl(trade) >= 0).length;
  const losses = matchingTrades.length - wins;
  const netPnl = matchingTrades.reduce((sum, trade) => sum + tradePnl(trade), 0);
  const winRate = (wins / matchingTrades.length) * 100;
  return {
    insight: `${label} won ${wins} of ${matchingTrades.length} (${winRate.toFixed(0)}%).`,
    label,
    losses,
    netPnl,
    trades: matchingTrades.length,
    winRate,
    wins,
  };
}

function riskRewardForTrade(trade: ApiRecord): number {
  const { approval, components } = tradeMetadata(trade);
  return readNumber(approval, ["risk_reward", "risk_reward_ratio", "rr"], readNumber(components, ["risk_reward", "risk_reward_ratio", "rr"], Number.NaN));
}

function winningDnaSummaryRow(trades: ApiRecord[], label: string, predicate: (trade: ApiRecord) => boolean): WinningDnaSummaryRow {
  const matchingTrades = trades.filter(predicate);
  if (!matchingTrades.length) return { averageRr: "—", label, observation: "—", trades: "—", winRate: "—", wins: "—" };
  const wins = matchingTrades.filter((trade) => tradePnl(trade) >= 0).length;
  const winRate = (wins / matchingTrades.length) * 100;
  const rrValues = matchingTrades.map(riskRewardForTrade).filter((value) => Number.isFinite(value));
  const averageRr = rrValues.length ? rrValues.reduce((sum, value) => sum + value, 0) / rrValues.length : Number.NaN;
  return {
    averageRr: Number.isFinite(averageRr) ? averageRr.toFixed(1) : "—",
    label,
    observation: `${wins} of ${matchingTrades.length} won (${winRate.toFixed(1)}%).`,
    trades: String(matchingTrades.length),
    winRate: `${winRate.toFixed(1)}%`,
    wins: String(wins),
  };
}

function buildWinningDnaSummaryRows(trades: ApiRecord[]): WinningDnaSummaryRow[] {
  return [
    winningDnaSummaryRow(
      trades,
      "FVG + Trend Alignment",
      (trade) => passFailState(trade, "fvg_result", "fvg") === "present" && trendStateForTrade(trade) === "aligned",
    ),
    winningDnaSummaryRow(
      trades,
      "Trend + Session Bonus",
      (trade) => trendStateForTrade(trade) === "aligned" && sessionStateForTrade(trade) === "london_ny",
    ),
    winningDnaSummaryRow(
      trades,
      "BOS + FVG + Session Bonus",
      (trade) => passFailState(trade, "bos_result", "bos") === "present" && passFailState(trade, "fvg_result", "fvg") === "present" && sessionStateForTrade(trade) === "london_ny",
    ),
  ];
}

function conclusionFromDna(type: "WINNING" | "LOSS", label: string, row: StrategyDnaRow | null): StrategyConclusionRow {
  if (!row) return missingConclusionRow(type, label);
  return {
    label,
    losses: String(row.losses),
    netPnl: money(row.netPnl),
    netPnlTone: row.netPnl,
    observation: row.insight,
    trades: String(row.trades),
    type,
    winRate: `${row.winRate.toFixed(1)}%`,
    wins: String(row.wins),
  };
}

function missingConclusionRow(type: StrategyConclusionRow["type"], label: string): StrategyConclusionRow {
  return {
    label,
    losses: "—",
    netPnl: "—",
    netPnlTone: null,
    observation: "—",
    trades: "—",
    type,
    winRate: "—",
    wins: "—",
  };
}

function findPattern(patterns: IntelligencePattern[], label: string, aliases: string[] = []): IntelligencePattern | null {
  const terms = [label, ...aliases].map((item) => cleanAnalysisText(item).toLowerCase()).filter(Boolean);
  return patterns.find((pattern) => {
    const text = cleanAnalysisText(pattern.label).toLowerCase();
    return terms.some((term) => text.includes(term) || term.includes(text));
  }) ?? null;
}

function rejectionConclusionRow(label: string, pattern: IntelligencePattern | null): StrategyConclusionRow {
  if (!pattern) return missingConclusionRow("REJECTION", label);
  return {
    label,
    losses: "—",
    netPnl: "—",
    netPnlTone: null,
    observation: `${pattern.percentage.toFixed(1)}% of rejections. Fix this blocker first.`,
    trades: String(pattern.count),
    type: "REJECTION",
    winRate: "—",
    wins: "—",
  };
}

function aiConclusionRow(label: string, observation: string, source?: FeatureImpactRow | IntelligencePattern): StrategyConclusionRow {
  const featureSource = source && "feature" in source ? source : null;
  return {
    label,
    losses: featureSource ? String(featureSource.losses) : "—",
    netPnl: featureSource ? money(featureSource.netPnl) : "—",
    netPnlTone: featureSource ? featureSource.netPnl : null,
    observation: observation || "â€”",
    trades: featureSource ? String(featureSource.trades) : "—",
    type: "AI",
    winRate: featureSource ? `${featureSource.winRate.toFixed(1)}%` : "—",
    wins: featureSource ? String(featureSource.wins) : "—",
  };
}

function strongestSetupObservation(trades: ApiRecord[], fallback?: FeatureImpactRow): string {
  const candidates = buildWinningDnaSummaryRows(trades).filter((row) => !isDash(row.trades));
  const best = candidates.sort((left, right) => Number.parseFloat(right.winRate) - Number.parseFloat(left.winRate))[0];
  if (best) return `Prioritize ${best.label}.`;
  if (fallback?.feature === "FVG" && fallback.state === "Present") return "Prioritize FVG + trend alignment.";
  if (fallback?.feature === "Session Bonus" && fallback.state === "Active") return "Prioritize trend with session bonus.";
  return fallback ? `Prioritize ${fallback.feature} ${fallback.state}.` : "—";
}

function weakestSetupObservation(row?: FeatureImpactRow): string {
  if (!row) return "—";
  if (row.feature === "BOS" && row.state === "Present") return "Trades with BOS present alone are underperforming.";
  if (row.feature === "BOS" && row.state === "Missing") return "Missing BOS confirmation is underperforming.";
  if (row.feature === "FVG" && row.state === "Missing") return "Missing FVG confirmation is underperforming.";
  if (row.feature === "Liquidity Sweep" && row.state === "Missing") return "Missing liquidity sweep is underperforming.";
  if (row.feature === "Session Bonus" && row.state.includes("Inactive")) return "Weak-score off-session trades are underperforming.";
  return `${row.feature} ${row.state} is underperforming.`;
}

function lossContributorObservation(pattern?: IntelligencePattern): string {
  if (!pattern) return "—";
  const text = pattern.label.toLowerCase();
  if (text.includes("bos")) return "Missing BOS confirmation drives most losses.";
  if (text.includes("liquidity") || text.includes("sweep")) return "Weak liquidity confirmation drives losses.";
  if (text.includes("fvg")) return "Missing FVG confirmation drives losses.";
  if (text.includes("session")) return "Weak score without session bonus drives losses.";
  if (text.includes("time") || text.includes("stale")) return "Stale exits are costing continuation.";
  return `${pattern.label} drives most losses.`;
}

function validationBlockerObservation(pattern?: IntelligencePattern): string {
  if (!pattern) return "—";
  const text = pattern.label.toLowerCase();
  if (text.includes("h4")) return "Insufficient H4 candle history causes most rejections.";
  if (text.includes("m15")) return "Insufficient M15 candle history causes most rejections.";
  if (text.includes("h1")) return "Insufficient H1 candle history causes most rejections.";
  if (text.includes("risk")) return "Risk validation causes most rejections.";
  if (text.includes("stop") || text.includes("sl")) return "Stop-loss validation causes most rejections.";
  return `${pattern.label} causes most rejections.`;
}

function recommendedImprovementObservation(topLoss?: IntelligencePattern, topRejection?: IntelligencePattern): string {
  const lossText = topLoss?.label.toLowerCase() ?? "";
  if (lossText.includes("bos") || lossText.includes("fvg")) return `${topLoss?.label} is the largest observed loss pattern.`;
  if (lossText.includes("liquidity") || lossText.includes("sweep")) return `${topLoss?.label} is the largest observed loss pattern.`;
  if (lossText.includes("session")) return `${topLoss?.label} is the largest observed loss pattern.`;
  if (topRejection) return `${topRejection.label} is the largest observed rejection pattern.`;
  return "Collect more current-round outcomes before changing filters.";
}

function featureObservation(row?: FeatureImpactRow): string {
  if (!row || !row.hasData) return "—";
  const lossRate = row.trades ? (row.losses / row.trades) * 100 : 0;
  return `${row.feature} ${row.state.toLowerCase()} lost ${row.losses} of ${row.trades} (${lossRate.toFixed(0)}%).`;
}

function patternObservation(pattern: IntelligencePattern | undefined, denominator: number, fallback: string): string {
  if (!pattern || denominator <= 0) return "—";
  return `${pattern.label} caused ${pattern.count} of ${denominator} ${fallback} (${pattern.percentage.toFixed(0)}%).`;
}

function symbolPerformanceObservation(trades: ApiRecord[]): string {
  const groups = ["EURUSD", "XAUUSD"].map((symbol) => {
    const scoped = trades.filter((trade) => readText(trade, ["symbol"], "").toUpperCase() === symbol);
    const wins = scoped.filter((trade) => tradePnl(trade) > 0).length;
    const pnl = scoped.reduce((sum, trade) => sum + tradePnl(trade), 0);
    const winRate = scoped.length ? (wins / scoped.length) * 100 : 0;
    return { symbol, trades: scoped.length, winRate, pnl };
  });
  const active = groups.filter((item) => item.trades > 0);
  if (!active.length) return "No symbol performance yet.";
  const best = active.sort((left, right) => right.pnl - left.pnl || right.winRate - left.winRate || right.trades - left.trades)[0];
  return `${best.symbol} performs better so far: ${best.trades} trades, ${best.winRate.toFixed(0)}% win rate, ${money(best.pnl)} net.`;
}

function buildStrategyConclusionRows(trades: ApiRecord[], _losses: IntelligencePattern[], rejections: IntelligencePattern[], _featureRows: FeatureImpactRow[]): StrategyConclusionRow[] {
  const lossCount = trades.filter((trade) => tradePnl(trade) < 0).length;
  const topRejection = rejections[0];
  const bestFeature = _featureRows
    .filter((row) => row.hasData)
    .sort((left, right) => right.winRate - left.winRate || right.netPnl - left.netPnl || right.trades - left.trades)[0];
  const weakestFeature = _featureRows
    .filter((row) => row.hasData)
    .sort((left, right) => (right.losses / Math.max(right.trades, 1)) - (left.losses / Math.max(left.trades, 1)) || left.netPnl - right.netPnl)[0];
  const topLoss = _losses[0];
  const baseRows = [
    conclusionFromDna(
      "WINNING",
      "BOS + FVG + Session Bonus",
      strategyDnaRow(
        trades,
        "BOS + FVG + Session Bonus",
        (trade) => passFailState(trade, "bos_result", "bos") === "present" && passFailState(trade, "fvg_result", "fvg") === "present" && sessionStateForTrade(trade) === "london_ny",
      ),
    ),
    conclusionFromDna(
      "WINNING",
      "Trend + Session Bonus",
      strategyDnaRow(
        trades,
        "Trend + Session Bonus",
        (trade) => trendStateForTrade(trade) === "aligned" && sessionStateForTrade(trade) === "london_ny",
      ),
    ),
    conclusionFromDna(
      "WINNING",
      "FVG + Trend Alignment",
      strategyDnaRow(
        trades,
        "FVG + Trend Alignment",
        (trade) => passFailState(trade, "fvg_result", "fvg") === "present" && trendStateForTrade(trade) === "aligned",
      ),
    ),
    conclusionFromDna(
      "WINNING",
      "Liquidity Sweep + BOS",
      strategyDnaRow(
        trades,
        "Liquidity Sweep + BOS",
        (trade) => passFailState(trade, "bos_result", "bos") === "present" && passFailState(trade, "liquidity_sweep_result", "liquidity_sweep") === "present",
      ),
    ),
    conclusionFromDna(
      "LOSS",
      "BOS Missing",
      strategyDnaRow(trades, "BOS Missing", (trade) => passFailState(trade, "bos_result", "bos") === "missing"),
    ),
    conclusionFromDna(
      "LOSS",
      "Liquidity Sweep Missing",
      strategyDnaRow(trades, "Liquidity Sweep Missing", (trade) => passFailState(trade, "liquidity_sweep_result", "liquidity_sweep") === "missing"),
    ),
    conclusionFromDna(
      "LOSS",
      "FVG Missing",
      strategyDnaRow(trades, "FVG Missing", (trade) => passFailState(trade, "fvg_result", "fvg") === "missing"),
    ),
    conclusionFromDna(
      "LOSS",
      "No Session Bonus",
      strategyDnaRow(trades, "No Session Bonus", (trade) => sessionStateForTrade(trade) === "outside"),
    ),
    conclusionFromDna(
      "LOSS",
      "Time Stale Exit",
      strategyDnaRow(trades, "Time Stale Exit", (trade) => exitReasonForTrade(trade).toLowerCase().includes("stale") || exitReasonForTrade(trade).toLowerCase().includes("time")),
    ),
    rejectionConclusionRow("H4 history insufficient", findPattern(rejections, "H4 history insufficient", ["H4 history", "H4 insufficient"])),
    rejectionConclusionRow("M15 history insufficient", findPattern(rejections, "M15 history insufficient", ["M15 history", "M15 insufficient"])),
    rejectionConclusionRow("H1 history insufficient", findPattern(rejections, "H1 history insufficient", ["H1 history", "H1 insufficient"])),
    rejectionConclusionRow("Stop Loss rejection", findPattern(rejections, "Stop Loss rejection", ["stop loss", "sl validation"])),
    rejectionConclusionRow("Risk rejection", findPattern(rejections, "Risk rejection", ["risk validation", "risk rejection"])),
  ];
  return [
    ...baseRows,
    aiConclusionRow("Best observed condition", featureObservation(bestFeature), bestFeature),
    aiConclusionRow("Weakest observed condition", featureObservation(weakestFeature), weakestFeature),
    aiConclusionRow("Largest loss pattern", patternObservation(topLoss, lossCount, "losses")),
    aiConclusionRow("Main validation blocker", patternObservation(topRejection, rejections.reduce((sum, item) => sum + item.count, 0), "rejections")),
    aiConclusionRow("Best symbol", symbolPerformanceObservation(trades)),
    aiConclusionRow("Current sample", `${trades.length} closed trades analyzed in active round.`),
  ];
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
  if (mode === "READY_ROUND_3") return { label: "Ready", statusText: "Ready for Round 3 Validation", tone: "healthy" };
  if (closed >= target && target > 0) return { label: "Completed", statusText: "Validation Completed", tone: "healthy" };
  if (mode === "WAITING_FOR_MT5_HISTORY_SYNC") return { label: "Waiting", statusText: "Waiting for MT5 history sync", tone: "warning" };
  if (mode === "RUNNING") return { label: "Running", statusText: open > 0 ? "Waiting for Open Trades to Close" : "Validation in Progress", tone: "healthy" };
  if (mode === "HALTED_RISK") return { label: "Risk Halted", statusText: "Risk Halted", tone: "danger" };
  if (["PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED", "WAITING_FOR_MT5_RECONNECT"].includes(mode)) return { label: "Paused", statusText: "Validation Paused", tone: "warning" };
  if (mode === "COMPLETED") return { label: "Completed", statusText: "Validation Completed", tone: "healthy" };
  if (hasValidationSession) return { label: "Stopped", statusText: "Validation Progress Available", tone: "warning" };
  return { label: "Stopped", statusText: "Validation Not Started", tone: "warning" };
}

function autoValidationLoadingMessage(action: AutoValidationAction): string {
  return action === "start"
    ? "Starting validation..."
    : action === "resume"
      ? "Resuming validation..."
      : action === "pause"
        ? "Pausing validation..."
        : action === "stop"
          ? "Stopping validation..."
          : "Resetting closed trade records...";
}

function autoValidationSuccessMessage(action: AutoValidationAction): string {
  return action === "start"
    ? "Validation started successfully"
    : action === "resume"
      ? "Validation resumed successfully"
      : action === "pause"
      ? "Validation paused successfully"
      : action === "stop"
        ? "Validation stopped successfully"
        : "Closed trade records reset";
}

function autoValidationErrorMessage(action: AutoValidationAction): string {
  return action === "start"
    ? "Failed to start validation"
    : action === "resume"
      ? "Failed to resume validation"
      : action === "pause"
      ? "Failed to pause validation"
      : action === "stop"
        ? "Failed to stop validation"
        : "Failed to reset closed trades";
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

type ReasonStatus = "Accepted" | "Rejected" | "Waiting" | "SCAN_RESULT" | "OPEN_CONFIRMED" | "POSITION_MONITOR" | "CLOSED" | "CLOSED_WIN" | "CLOSED_LOSS" | "RISK_HALTED" | "RISK_CLEARED" | "Error";
type ReasonMessage = {
  candles_loaded?: number | null;
  candles_required?: number | null;
  data_source?: string;
  id: string;
  event_id?: string;
  reason: string;
  rejection_reason?: string;
  status: ReasonStatus;
  symbol: string;
  timestamp: string;
  timeframe?: string;
  validation_status?: string;
  history_ready?: boolean | null;
  groqGenerated?: boolean;
  source?: "groq" | "rule" | "execution";
  ticket?: string;
  decision_reason?: string;
  confirmation_missing?: string[];
  confirmation_passed?: string[];
  confirmation_score?: number | null;
  confirmation_required?: number | null;
  confirmation_total?: number | null;
  bos?: boolean | null;
  fvg?: boolean | null;
  fvg_retest?: boolean | null;
  htf_bias?: string;
  liquidity_sweep?: boolean | null;
  momentum?: boolean | null;
  pullback_retest?: boolean | null;
};
type ReasonContext = ApiRecord & { status: ReasonStatus; symbol: string; timestamp: string };

type IntelligencePattern = {
  count: number;
  label: string;
  percentage: number;
};

type FeatureImpactRow = {
  feature: string;
  hasData: boolean;
  insight: string;
  losses: number;
  netPnl: number;
  state: string;
  trades: number;
  winRate: number;
  wins: number;
};

type StrategyDnaRow = {
  insight: string;
  label: string;
  losses: number;
  netPnl: number;
  trades: number;
  winRate: number;
  wins: number;
};

type StrategyConclusionRow = {
  label: string;
  losses: string;
  netPnl: string;
  netPnlTone: number | null;
  observation: string;
  trades: string;
  type: "WINNING" | "LOSS" | "REJECTION" | "AI";
  winRate: string;
  wins: string;
};

type WinningDnaSummaryRow = {
  averageRr: string;
  label: string;
  observation: string;
  trades: string;
  winRate: string;
  wins: string;
};

function firstReasonText(record: ApiRecord, keys: string[]): string {
  for (const key of keys) {
    const value = readText(record, [key], "");
    if (value) return value;
  }
  return "";
}

function firstReasonNumber(record: ApiRecord, keys: string[]): number | null {
  for (const key of keys) {
    const value = numeric(record, [key], Number.NaN);
    if (Number.isFinite(value)) return value;
  }
  return null;
}

function validatorDiagnosticsFromRecord(record: ApiRecord, fallbackStatus: ReasonStatus, fallbackReason: string): ApiRecord {
  return {
    candles_loaded: firstReasonNumber(record, ["candles_loaded", "candlesLoaded", "loaded_candles", "loadedCandles", "bars_loaded", "barsLoaded", "history_bars", "candle_count"]),
    candles_required: firstReasonNumber(record, ["candles_required", "candlesRequired", "required_candles", "requiredCandles", "minimum_candles", "minimumCandles", "min_bars", "minBars"]),
    data_source: firstReasonText(record, ["data_source", "dataSource", "source", "feed_source", "feedSource"]),
    rejection_reason: firstReasonText(record, ["rejection_reason", "rejectionReason", "final_rejection_reason", "finalRejectionReason"]) || fallbackReason,
    decision_reason: firstReasonText(record, ["decision_reason", "decisionReason"]),
    timeframe: firstReasonText(record, ["timeframe", "tf", "validation_timeframe", "validationTimeframe", "failed_timeframe", "failedTimeframe"]).toUpperCase(),
    validation_status: firstReasonText(record, ["validation_status", "validationStatus", "execution_status", "executionStatus", "status_level", "risk_status"]) || fallbackStatus,
    final_decision_reason: firstReasonText(record, ["final_decision_reason", "finalDecisionReason"]),
    passed_rules: Array.isArray(record.passed_rules) ? record.passed_rules : [],
    failed_rules: Array.isArray(record.failed_rules) ? record.failed_rules : [],
    advisory_warnings: Array.isArray(record.advisory_warnings) ? record.advisory_warnings : [],
    RR: firstReasonNumber(record, ["RR", "risk_reward", "riskReward", "rr"]),
    required_rr: firstReasonNumber(record, ["required_rr", "requiredRR", "minimum_rr", "minimumRR"]),
    confirmation_score: firstReasonNumber(record, ["confirmation_score", "confirmationScore"]),
    confirmation_required: firstReasonNumber(record, ["confirmation_required", "confirmationRequired"]),
    confirmation_total: firstReasonNumber(record, ["confirmation_total", "confirmationTotal"]),
    confirmation_passed: Array.isArray(record.confirmation_passed) ? record.confirmation_passed : [],
    confirmation_missing: Array.isArray(record.confirmation_missing) ? record.confirmation_missing : [],
    bos_status: firstReasonText(record, ["bos_status", "bosStatus"]),
    fvg_status: firstReasonText(record, ["fvg_status", "fvgStatus"]),
    h4_history_status: firstReasonText(record, ["h4_history_status", "h4HistoryStatus"]),
    m15_history_status: firstReasonText(record, ["m15_history_status", "m15HistoryStatus"]),
    history_ready: record.history_ready === true ? true : record.history_ready === false ? false : null,
  };
}

function reasonArrayText(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item ?? "").trim()).filter(Boolean) : [];
}

function hasDecisionTicket(record: ApiRecord): boolean {
  const ticket = readText(record, ["ticket", "mt5_ticket", "mt5Ticket", "order_ticket", "orderTicket"], "");
  return Boolean(ticket && ticket !== "0");
}

function hasActualOrderExecution(record: ApiRecord): boolean {
  if (!hasDecisionTicket(record)) return false;
  const source = readText(record, ["source"], "").toLowerCase();
  const status = readText(record, ["status", "execution_status", "executionStatus", "validation_status", "validationStatus"], "").toUpperCase();
  return record.order_opened === true || record.mt5_order_sent === true || source === "execution" || status.includes("ORDER_SENT") || status.includes("DEMO_ORDER_SENT");
}

function hasHardDecisionFailure(record: ApiRecord): boolean {
  const combined = [
    readText(record, ["reason", "setupReason", "whatNeedsToHappenNext", "rejection_reason", "final_decision_reason"], ""),
    readText(record, ["status", "execution_status", "executionStatus", "validation_status", "validationStatus", "risk_status", "riskStatus"], ""),
    ...reasonArrayText(record.blockers),
    ...reasonArrayText(record.failed_rules),
  ].join(" ").toUpperCase();
  return /RR[^A-Z0-9]*(?:BELOW|LOW|<)|RISK_REWARD[^A-Z0-9]*(?:BELOW|LOW)|SPREAD[^A-Z0-9]*(?:TOO_HIGH|TOO HIGH|HIGH|UNAVAILABLE)|RISK[^A-Z0-9]*(?:REJECT|DENIED|FAILED)|SL_TP|HISTORY[^A-Z0-9]*(?:INSUFFICIENT|UNAVAILABLE|MISSING)|INSUFFICIENT[^A-Z0-9]*(?:H4|M15|HISTORY)|DIRECTION[^A-Z0-9]*(?:MISMATCH|OPPOSITE|UNCLEAR)|GUARDED_SENDER_REJECTED|LIVE_ACCOUNT|DEMO_ACCOUNT|MT5_DISCONNECTED|HIGH_IMPACT_NEWS_BLACKOUT/.test(combined);
}

function hasWaitingDecisionState(record: ApiRecord): boolean {
  const combined = [
    readText(record, ["reason", "setupReason", "whatNeedsToHappenNext", "rejection_reason", "final_decision_reason"], ""),
    readText(record, ["status", "execution_status", "executionStatus", "validation_status", "validationStatus", "risk_status", "riskStatus"], ""),
    ...reasonArrayText(record.blockers),
    ...reasonArrayText(record.failed_rules),
  ].join(" ").toUpperCase();
  return /CONFIRMATION_SCORE|CONFIDENCE|MISSING[^A-Z0-9]*(?:BOS|FVG|LIQUIDITY|TREND)|(?:BOS|FVG|LIQUIDITY|TREND)[^A-Z0-9]*(?:MISSING|WAITING|PENDING)|NO_READY_APPROVED_SIGNAL|SESSION[^A-Z0-9]*(?:OPENING|PENDING)/.test(combined);
}

function decisionStatusFromRecord(record: ApiRecord): ReasonStatus {
  const statusText = readText(record, ["status", "execution_status", "executionStatus", "status_level", "risk_status", "validation_status"], "").toUpperCase();
  const reportType = readText(record, ["report_type", "event_type", "event"], "").toUpperCase();
  const combinedText = [readText(record, ["reason"], ""), readText(record, ["final_decision_reason"], ""), readText(record, ["decision_reason"], "")].join(" ");
  if (statusText.includes("RISK_HALTED") || reportType.includes("RISK_HALTED")) return "RISK_HALTED";
  if (statusText.includes("RISK_CLEARED") || reportType.includes("RISK_CLEARED")) return "RISK_CLEARED";
  if (statusText.includes("SCAN_RESULT") || reportType.includes("SCAN_RESULT")) return "SCAN_RESULT";
  if (statusText.includes("POSITION_MONITOR") || reportType.includes("POSITION_MONITOR")) return "POSITION_MONITOR";
  if (/CLOSED_LOSS|Result:\s*LOSS|closed\./i.test(combinedText)) return "CLOSED_LOSS";
  if (/CLOSED_WIN|Result:\s*WIN/i.test(combinedText)) return "CLOSED_WIN";
  if (statusText.includes("OPEN_CONFIRMED") || reportType.includes("OPEN_CONFIRMED")) return "OPEN_CONFIRMED";
  if (statusText.includes("CLOSED_WIN") || reportType.includes("CLOSED_WIN")) return "CLOSED_WIN";
  if (statusText.includes("CLOSED_LOSS") || reportType.includes("CLOSED_LOSS")) return "CLOSED_LOSS";
  if (statusText.includes("CLOSED") || reportType.includes("VALIDATION_TRADE_CLOSED") || reportType.includes("ORDER_CLOSED_CONFIRMED")) return "CLOSED";
  if (hasActualOrderExecution(record)) return "Accepted";
  if (statusText.includes("ERROR") || statusText.includes("FAIL") || statusText.includes("DISCONNECT")) return "Error";
  if (hasHardDecisionFailure(record)) return "Rejected";
  if (hasWaitingDecisionState(record)) return "Waiting";
  if (statusText.includes("BLOCK") || statusText.includes("REJECT") || statusText.includes("DENIED")) return "Rejected";
  return "Waiting";
}

function decisionLabel(value: string): string {
  const normalized = value.replace(/_/g, " ").toLowerCase();
  if (normalized.includes("bos")) return "BOS";
  if (normalized.includes("fvg")) return "FVG";
  if (normalized.includes("liquidity")) return "Liquidity sweep";
  if (normalized.includes("trend")) return "Trend alignment";
  if (normalized.includes("h4")) return "H4 history";
  if (normalized.includes("m15")) return "M15 history";
  if (normalized.includes("session")) return "London/NY session bonus";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function uniqueDecisionLabels(values: string[]): string[] {
  const seen = new Set<string>();
  return values.map(decisionLabel).filter((value) => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function decisionBool(record: ApiRecord, keys: string[]): boolean | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "boolean") return value;
    const textValue = String(value ?? "").trim().toUpperCase();
    if (["TRUE", "YES", "PRESENT", "AVAILABLE", "ALIGNED", "PASSED"].includes(textValue)) return true;
    if (["FALSE", "NO", "MISSING", "INSUFFICIENT", "NOT_ALIGNED", "FAILED"].includes(textValue)) return false;
  }
  return null;
}

function confirmationLabels(record: ApiRecord, kind: "present" | "missing"): string[] {
  const explicit = Array.isArray(record[kind === "present" ? "confirmation_passed" : "confirmation_missing"]) ? (record[kind === "present" ? "confirmation_passed" : "confirmation_missing"] as unknown[]).map(String) : [];
  if (explicit.length) return uniqueDecisionLabels(explicit);
  const states = [
    ["BOS", decisionBool(record, ["bosConfirmed", "bos_status"])],
    ["FVG", decisionBool(record, ["fvgConfirmed", "fvg_status"])],
    ["Liquidity sweep", decisionBool(record, ["liquiditySweep", "liquidity_sweep_status"])],
    ["Trend alignment", decisionBool(record, ["trendAlignment", "trend_alignment_status"])],
  ] as const;
  return states.filter(([, state]) => state === (kind === "present")).map(([label]) => label);
}

function canonicalRound3DecisionReason(record: ApiRecord, status: ReasonStatus): string | null {
  const symbol = readText(record, ["symbol"], "EURUSD").toUpperCase();
  const score = firstReasonNumber(record, ["confirmation_score", "confirmationScore"]);
  const required = firstReasonNumber(record, ["confirmation_required", "confirmationRequired"]) ?? 2;
  const total = firstReasonNumber(record, ["confirmation_total", "confirmationTotal"]) ?? 4;
  const rr = firstReasonNumber(record, ["RR", "risk_reward", "riskReward", "rr"]);
  const requiredRr = firstReasonNumber(record, ["required_rr", "requiredRR", "minimum_rr", "minimumRR"]) ?? 2;
  const ticket = readText(record, ["ticket", "mt5_ticket", "mt5Ticket"], "");
  const failedRules = Array.isArray(record.failed_rules) ? record.failed_rules.map(String) : [];
  const blockers = cleanBlockers(record.blocked_reasons ?? record.blockers ?? record.failed_rules ?? record.missing_requirements);
  const allBlockers = [...failedRules, ...blockers];
  const h4 = decisionBool(record, ["h4HistoryValid", "h4_history_status"]);
  const m15 = decisionBool(record, ["m15HistoryValid", "m15_history_status"]);
  const session = decisionBool(record, ["sessionValid"]) ?? (failedRules.some((item) => /SESSION_LONDON_NY/i.test(item)) ? true : null);
  if (status === "Rejected" && rr !== null && rr < requiredRr) return `RR ${rr} below required ${requiredRr}`;
  if (status === "Rejected" && allBlockers.some((item) => /SPREAD/i.test(item))) return "Spread too high";
  const present = uniqueDecisionLabels([h4 === true ? "H4 history" : "", m15 === true ? "M15 history" : "", session === true ? "London/NY session bonus" : "", ...confirmationLabels(record, "present")].filter(Boolean));
  const missing = score !== null && score >= required ? [] : uniqueDecisionLabels([h4 === false ? "H4 history" : "", m15 === false ? "M15 history" : "", ...confirmationLabels(record, "missing")].filter(Boolean));
  if (status === "Accepted") {
    const lines = [`${symbol} trade opened successfully.`, `Score ${score ?? present.length}/${total}`];
    for (const item of present.filter((label) => !/history|session/i.test(label))) lines.push(`${item} ✓`);
    if (rr !== null) lines.push(`RR ${rr}`);
    if (ticket) lines.push(`Ticket ${ticket}`);
    return lines.join("\n");
  }
  if (score !== null || present.length || missing.length) {
    const lines = [`Score ${score ?? present.length}/${required}`];
    if (present.length) {
      lines.push("Present:");
      present.forEach((item) => lines.push(`- ${item} ✓`));
    }
    if (missing.length) {
      lines.push("Missing:");
      missing.forEach((item) => lines.push(`- ${item} ✗`));
    }
    return lines.join("\n");
  }
  return null;
}

function decisionReasonFromRecord(record: ApiRecord, status: ReasonStatus, fallback: string): string {
  const rawReason = readText(record, ["setup_reason", "reason", "what_needs_to_happen_next"], fallback);
  if (status === "OPEN_CONFIRMED") return rawReason || "OPEN_CONFIRMED";
  const decisionReason = readText(record, ["decision_reason", "decisionReason"], "");
  const finalReason = readText(record, ["final_decision_reason", "finalDecisionReason"], "");
  const canonical = canonicalRound3DecisionReason(record, status);
  if (canonical) return canonical;
  if (decisionReason && !isLegacyStrategyDiagnostic(decisionReason) && !/required round 3|rule failed/i.test(decisionReason)) return decisionReason;
  if (status !== "Accepted" && /^accepted:/i.test(finalReason)) {
    return `${readText(record, ["symbol"], "EURUSD").toUpperCase()} waiting: setup passed; waiting for MT5 order execution.`;
  }
  const score = firstReasonNumber(record, ["confirmation_score", "confirmationScore"]);
  const required = firstReasonNumber(record, ["confirmation_required", "confirmationRequired"]) ?? 2;
  const total = firstReasonNumber(record, ["confirmation_total", "confirmationTotal"]) ?? 4;
  const rr = firstReasonNumber(record, ["RR", "risk_reward", "riskReward", "rr"]);
  const requiredRr = firstReasonNumber(record, ["required_rr", "requiredRR", "minimum_rr", "minimumRR"]) ?? 2;
  const missing = Array.isArray(record.confirmation_missing) ? record.confirmation_missing.map(String).filter(Boolean) : [];
  const failedRules = Array.isArray(record.failed_rules) ? record.failed_rules.map(String) : [];
  const blockers = cleanBlockers(record.blocked_reasons ?? record.blockers ?? record.failed_rules ?? record.missing_requirements);
  const allBlockers = [...failedRules, ...blockers];
  if (status === "Accepted" && hasDecisionTicket(record)) {
    return `${readText(record, ["symbol"], "EURUSD").toUpperCase()} trade opened successfully. Ticket: ${readText(record, ["ticket", "mt5_ticket", "mt5Ticket"], "")}. Score ${score ?? 0}/${total}. RR ${rr ?? requiredRr}. Risk approved.`;
  }
  if (allBlockers.some((item) => /SPREAD/i.test(item))) return "Rejected: spread too high.";
  if (allBlockers.some((item) => /RR|RISK_REWARD/i.test(item)) && rr !== null) return `Rejected: RR ${rr} below required ${requiredRr}.`;
  if (allBlockers.some((item) => /CONFIRMATION_SCORE/i.test(item)) || (score !== null && score < required)) {
    const missingText = missing.length ? ` Missing ${missing.join(", ")}.` : "";
    return `${status === "Rejected" ? "Rejected" : "Waiting"}: Score ${score ?? 0}/${required}.${missingText}`;
  }
  if (status === "Waiting" && /^accepted\b/i.test(rawReason)) return fallback;
  if (status === "Waiting" && /halted/i.test(rawReason) && /BOS|FVG|liquidity|trend|confirmation|confidence/i.test(rawReason)) {
    return rawReason.replace(/\bTrade was halted due to\b/i, `${readText(record, ["symbol"], "EURUSD").toUpperCase()} waiting:`).replace(/\bTrade halted due to\b/i, `${readText(record, ["symbol"], "EURUSD").toUpperCase()} waiting:`);
  }
  return rawReason;
}

function buildReasonContexts(data: DashboardData): ReasonContext[] {
  const messages: ReasonContext[] = [];
  const niftyConnected = Boolean(data.niftyTick && numeric(data.niftyTick, ["last", "price", "current_price", "ltp", "bid", "ask"], Number.NaN));
  const autoStatus = asRecord(data.autoValidation);
  const runtimeHealth = asRecord(autoStatus?.runtime_health) ?? {};
  const snapshotDecisions = Array.isArray(autoStatus?.bot_decisions_latest_3) ? autoStatus.bot_decisions_latest_3 : [];
  for (const value of snapshotDecisions) {
    const item = asRecord(value);
    if (!item) continue;
    messages.push({
      ...item,
      id: readText(item, ["event_id", "id"], ""),
      event_id: readText(item, ["event_id", "id"], ""),
      symbol: readText(item, ["symbol"], "SYSTEM").toUpperCase(),
      status: decisionStatusFromRecord(item),
      timestamp: readText(item, ["timestamp"], new Date(0).toISOString()),
      reason: readText(item, ["reason", "final_decision_reason"], "Validation update received."),
    });
  }
  const scanAgeSeconds = readNumber(runtimeHealth, ["last_scan_age_seconds"], 0);
  if (scanAgeSeconds > 60) {
    messages.unshift({
      id: `scan-stale-${readText(runtimeHealth, ["active_session_id"], "active")}`,
      event_id: `scan-stale-${readText(runtimeHealth, ["active_session_id"], "active")}`,
      symbol: "SYSTEM",
      status: "Waiting",
      timestamp: readText(runtimeHealth, ["timestamp"], new Date().toISOString()),
      reason: runtimeHealth.mt5_sync_loop_alive === true ? "Scan is stale; waiting for fresh diagnostics. MT5 sync is still live." : "Scan is stale; waiting for fresh diagnostics.",
    });
  }
  const historyWarmup = asRecord(autoStatus?.history_warmup ?? asRecord(autoStatus?.last_execution_decision)?.history_warmup);
  const currentHistoryReady = historyWarmup?.history_ready === true || autoStatus?.history_ready === true;
  for (const signal of data.clientSignals) {
    const status = decisionStatusFromRecord(signal);
    const symbol = readText(signal, ["symbol"], "EURUSD").toUpperCase();
    if (symbol === "NIFTY50" && !niftyConnected) continue;
    const reason = decisionReasonFromRecord(signal, status, "Waiting for strategy, market, and risk checks to confirm.");
    if (currentHistoryReady && /insufficient historical data|history.*insufficient|insufficient real candles/i.test(reason)) continue;
    const timestamp = readText(signal, ["timestamp", "created_at", "updated_at"], "1970-01-01T00:00:00.000Z");
    const signalCandleSource = asRecord(signal.candle_source) ?? {};
    const signalTimeframes = asRecord(signalCandleSource.timeframes) ?? {};
    const signalH4Count = firstReasonNumber(signalCandleSource, ["signal_h4_count", "signalH4Count"]) ?? firstReasonNumber(asRecord(signalTimeframes.H4) ?? {}, ["returned_count", "returnedCount"]) ?? 0;
    const signalM15Count = firstReasonNumber(signalCandleSource, ["signal_m15_count", "signalM15Count"]) ?? firstReasonNumber(asRecord(signalTimeframes.M15) ?? {}, ["returned_count", "returnedCount"]) ?? 0;
    messages.push({
      symbol,
      status,
      timestamp,
      reason,
      confidence: numeric(signal, ["confidence", "signal_confidence", "confidence_score"], Number.NaN),
      riskReward: numeric(signal, ["risk_reward", "risk_reward_ratio", "rr"], Number.NaN),
      requiredRR: numeric(signal, ["required_rr", "minimum_rr"], 2.0),
      trendAlignment: signal.trend_alignment ?? signal.trendAlignment ?? signal.trend_confirmed,
      liquiditySweep: signal.liquidity_sweep ?? signal.liquiditySweep,
      bosConfirmed: signal.bos_confirmed ?? signal.bosConfirmed ?? asRecord(signal.strategy_components)?.bos,
      fvgConfirmed: signal.fvg_confirmed ?? signal.fvgConfirmed ?? asRecord(signal.strategy_components)?.fvg,
      sessionValid: signal.session_valid ?? signal.sessionValid ?? asRecord(signal.strategy_components)?.session_valid,
      confirmation_score: numeric(signal, ["confirmation_score", "confirmationScore"], Number.NaN),
      confirmation_required: numeric(signal, ["confirmation_required", "confirmationRequired"], 2),
      confirmation_total: numeric(signal, ["confirmation_total", "confirmationTotal"], 4),
      confirmation_passed: Array.isArray(signal.confirmation_passed) ? signal.confirmation_passed : [],
      confirmation_missing: Array.isArray(signal.confirmation_missing) ? signal.confirmation_missing : [],
      h4HistoryValid: currentHistoryReady || signalH4Count >= 300 || readText(signal, ["h4_history_status"], "").toUpperCase() === "AVAILABLE",
      m15HistoryValid: currentHistoryReady || signalM15Count >= 300 || readText(signal, ["m15_history_status"], "").toUpperCase() === "AVAILABLE",
      orderBlockConfirmed: signal.order_block_confirmed ?? signal.orderBlockConfirmed,
      signalHash: readText(signal, ["signal_hash", "hash"], ""),
      blockers: cleanBlockers(signal.blocked_reasons ?? signal.failed_rules ?? signal.missing_requirements),
      setupReason: reason,
      niftyConnected,
      ...validatorDiagnosticsFromRecord(signal, status, reason),
    });
    const blockers = cleanBlockers(signal.blocked_reasons ?? signal.failed_rules ?? signal.missing_requirements);
    if (blockers.length && status === "Rejected") messages[messages.length - 1].blockers = blockers;
  }
  const historyDiagnostics = Array.isArray(historyWarmup?.diagnostics) ? (historyWarmup.diagnostics.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  const pendingHistory = historyDiagnostics.find((item) => item.history_ready !== true);
  if (pendingHistory) {
    const symbol = readText(pendingHistory, ["symbol"], "EURUSD").toUpperCase();
    const requestedSymbol = readText(pendingHistory, ["requested_symbol", "requestedSymbol"], symbol).toUpperCase();
    const resolvedSymbol = readText(pendingHistory, ["resolved_symbol", "resolvedSymbol"], requestedSymbol);
    const timeframe = readText(pendingHistory, ["timeframe"], "H4").toUpperCase();
    const loaded = firstReasonNumber(pendingHistory, ["candles_loaded", "candlesLoaded", "returned_count", "returnedCount"]) ?? 0;
    const required = firstReasonNumber(pendingHistory, ["candles_required", "candlesRequired", "requested_count", "requestedCount"]) ?? 300;
    messages.unshift({
      symbol,
      status: "Waiting",
      timestamp: readText(historyWarmup, ["timestamp"], new Date(0).toISOString()),
      reason: `Waiting for MT5 ${timeframe} history sync: ${requestedSymbol} resolved as ${resolvedSymbol}, loaded ${loaded} / required ${required} candles.`,
      timeframe,
      requested_symbol: requestedSymbol,
      resolved_symbol: resolvedSymbol,
      candles_loaded: loaded,
      candles_required: required,
      data_source: firstReasonText(pendingHistory, ["data_source", "dataSource", "source"]) || "MT5_DEMO",
      mt5_last_error: firstReasonText(pendingHistory, ["mt5_last_error", "mt5LastError"]),
      process_id: firstReasonText(pendingHistory, ["process_id", "processId"]),
      connection_id: firstReasonText(pendingHistory, ["connection_id", "connectionId"]),
      validation_status: "WAITING_FOR_MT5_HISTORY_SYNC",
      history_ready: false,
      niftyConnected,
    });
  }
  const reports = Array.isArray(autoStatus?.validation_close_reports) ? (autoStatus.validation_close_reports.filter((item) => asRecord(item)) as ApiRecord[]) : [];
  reports.forEach((report, index) => {
    const pnl = readNumber(report, ["net_pnl", "profit_loss", "pnl"], 0);
    const symbol = friendlyText(report, ["symbol"], "EURUSD").toUpperCase();
    if (symbol === "NIFTY50" && !niftyConnected) return;
    const ticket = readText(report, ["mt5_ticket", "ticket"], "");
    const side = friendlyText(report, ["side", "direction"], "TRADE").toUpperCase();
    const result = friendlyText(report, ["result"], pnl >= 0 ? "WIN" : "LOSS").toUpperCase();
    const exitReason = friendlyText(report, ["exit_reason", "reason", "close_reason"], "MT5 history confirmed close");
    const closedAt = readText(report, ["closed_at", "generated_at", "timestamp"], "1970-01-01T00:00:00.000Z");
    const closeReason = `${symbol} ${side} closed. Ticket: ${ticket || "Unavailable"}. Result: ${result}. P&L: ${money(pnl)}. Exit: ${exitReason}. Closed: ${formatTradeTime(closedAt)}.`;
    const status: ReasonStatus = ticket ? "CLOSED" : "Waiting";
    messages.push({
      id: `reason-${symbol}-closed-${ticket || readText(report, ["trade_id"], String(index))}`,
      ticket: ticket || String(index),
      reason: closeReason,
      status,
      symbol,
      timestamp: closedAt,
      pnl,
      niftyConnected,
      ...validatorDiagnosticsFromRecord(report, status, exitReason),
    });
  });
  return messages;
}

function normalizeReasonMessages(records: ApiRecord[]): ReasonMessage[] {
  const normalized = records
    .map((record): ReasonMessage => {
      const sourceText = readText(record, ["source"], "");
      const source: ReasonMessage["source"] = sourceText === "groq" ? "groq" : sourceText === "execution" ? "execution" : "rule";
      const status = decisionStatusFromRecord({ ...record, source });
      const reason = decisionReasonFromRecord(record, status, readText(record, ["reason"], ""));
      const symbol = readText(record, ["symbol"], "EURUSD").toUpperCase();
      const timestamp = readText(record, ["timestamp"], "1970-01-01T00:00:00.000Z");
      const ticket = readText(record, ["ticket", "mt5_ticket", "mt5Ticket"], "");
      const rawId = readText(record, ["id"], "");
      const eventId = readText(record, ["event_id", "eventId"], rawId);
      const id = rawId || (ticket ? `reason-${symbol}-${status}-ticket-${ticket}` : `reason-${symbol}-${status}-${timestamp}-${reason.slice(0, 48)}`);
      return {
        id,
        event_id: eventId || id,
        candles_loaded: (() => {
          const value = numeric(record, ["candles_loaded"], Number.NaN);
          return Number.isFinite(value) ? value : null;
        })(),
        candles_required: (() => {
          const value = numeric(record, ["candles_required"], Number.NaN);
          return Number.isFinite(value) ? value : null;
        })(),
        data_source: readText(record, ["data_source"], ""),
        reason,
        rejection_reason: readText(record, ["rejection_reason"], ""),
        decision_reason: readText(record, ["decision_reason"], ""),
        status,
        symbol,
        timestamp,
        ticket,
        confirmation_score: firstReasonNumber(record, ["confirmation_score", "confirmationScore"]),
        confirmation_required: firstReasonNumber(record, ["confirmation_required", "confirmationRequired"]),
        confirmation_total: firstReasonNumber(record, ["confirmation_total", "confirmationTotal"]),
        confirmation_passed: Array.isArray(record.confirmation_passed) ? record.confirmation_passed.map(String) : [],
        confirmation_missing: Array.isArray(record.confirmation_missing) ? record.confirmation_missing.map(String) : [],
        bos: record.bos === true ? true : record.bos === false ? false : null,
        fvg: record.fvg === true ? true : record.fvg === false ? false : null,
        fvg_retest: record.fvg_retest === true ? true : record.fvg_retest === false ? false : null,
        htf_bias: readText(record, ["htf_bias", "htf_alignment"], ""),
        liquidity_sweep: record.liquidity_sweep === true ? true : record.liquidity_sweep === false ? false : null,
        momentum: record.momentum === true ? true : record.momentum === false ? false : null,
        pullback_retest: record.pullback_retest === true ? true : record.pullback_retest === false ? false : null,
        timeframe: readText(record, ["timeframe"], ""),
        validation_status: readText(record, ["validation_status"], ""),
        history_ready: record.history_ready === true ? true : record.history_ready === false ? false : null,
        groqGenerated: record.groqGenerated === true,
        source,
      };
    })
    .filter((message) => message.id && message.reason);
  const seen = new Set<string>();
  return normalized
    .filter((message) => {
      const key = message.event_id || message.id || `${message.symbol}|${message.status}|${message.reason}|${message.timestamp}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .sort((left, right) => {
      const timestampDelta = new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime();
      if (Number.isFinite(timestampDelta) && timestampDelta !== 0) return timestampDelta;
      return (right.event_id || right.id).localeCompare(left.event_id || left.id);
    });
}

function reasonMessagePriority(message: ReasonMessage): number {
  const status = message.status.toUpperCase();
  if (["SCAN_RESULT", "Accepted", "OPEN_CONFIRMED", "POSITION_MONITOR", "CLOSED_WIN", "CLOSED_LOSS", "CLOSED"].map((item) => item.toUpperCase()).includes(status)) return 0;
  if (isRiskNoticeStatus(status)) return 2;
  return 1;
}

function filterVisibleBotMessages(messages: ReasonMessage[]): ReasonMessage[] {
  return messages
    .filter((message) => isVisibleRiskNotice(message.status.toUpperCase(), message.timestamp, message.status === "RISK_HALTED"))
    .sort((left, right) => {
      const priorityDelta = reasonMessagePriority(left) - reasonMessagePriority(right);
      if (priorityDelta !== 0) return priorityDelta;
      const timestampDelta = new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime();
      if (Number.isFinite(timestampDelta) && timestampDelta !== 0) return timestampDelta;
      return (right.event_id || right.id).localeCompare(left.event_id || left.id);
    });
}

function scanBlockerLabel(value: string): string {
  const normalized = value.replace(/[_-]/g, " ").trim().toLowerCase();
  if (!normalized) return "";
  if (normalized.includes("htf") || normalized.includes("h1/h4") || normalized.includes("h4/h1") || normalized.includes("higher timeframe")) return "HTF alignment";
  if (normalized.includes("momentum") || normalized.includes("pullback") || normalized.includes("retest")) return "momentum/pullback";
  if (normalized.includes("structure") || normalized.includes("bos") || normalized.includes("liquidity") || normalized.includes("fvg")) return "structure confirmation";
  if (normalized.includes("spread")) return "clean spread";
  if (normalized.includes("rr") || normalized.includes("risk reward")) return "RR >= 2.0";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function joinHumanList(values: string[]): string {
  const clean = values.filter(Boolean);
  if (clean.length <= 1) return clean[0] ?? "";
  if (clean.length === 2) return `${clean[0]} and ${clean[1]}`;
  return `${clean.slice(0, -1).join(", ")}, and ${clean[clean.length - 1]}`;
}

function uniqueScanLabels(values: string[]): string[] {
  const seen = new Set<string>();
  const ordered = values.filter((value) => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const rank: Record<string, number> = {
    "HTF alignment": 0,
    "momentum/pullback": 1,
    "structure confirmation": 2,
  };
  return ordered.sort((left, right) => (rank[left] ?? 99) - (rank[right] ?? 99));
}

function latestScanSummary(message: ReasonMessage): string {
  const score = Number.isFinite(message.confirmation_score ?? Number.NaN) ? Number(message.confirmation_score) : null;
  const required = Number.isFinite(message.confirmation_required ?? Number.NaN) ? Number(message.confirmation_required) : null;
  const missingLabels = uniqueScanLabels((message.confirmation_missing ?? []).map(scanBlockerLabel));
  const groupedMissing = uniqueScanLabels(missingLabels.map(scanBlockerLabel)).filter((label) => !/clean spread|rr/i.test(label));
  const reasonLabels = groupedMissing.length ? groupedMissing : uniqueScanLabels((message.reason.match(/missing ([^.]+)/i)?.[1] ?? "").split(/,| and /).map(scanBlockerLabel));
  const blockedBy = reasonLabels.length ? `blocked by missing ${joinHumanList(reasonLabels)}` : "waiting for balanced gate alignment";
  const scoreText = score !== null && required !== null ? `score ${score}/${required}` : "score pending";
  return `Scan update: ${scoreText}. ${blockedBy}.`;
}

function isTradeLifecycleMessage(message: ReasonMessage): boolean {
  return ["Accepted", "OPEN_CONFIRMED", "CLOSED", "CLOSED_WIN", "CLOSED_LOSS"].includes(message.status);
}

function botStatusLabel(status: ReasonStatus): string {
  if (status === "SCAN_RESULT") return "SCAN";
  if (status === "OPEN_CONFIRMED" || status === "Accepted") return "OPEN";
  if (status === "CLOSED_WIN") return "WIN";
  if (status === "CLOSED_LOSS") return "LOSS";
  if (status === "CLOSED") return "CLOSED";
  if (status === "POSITION_MONITOR") return "MONITOR";
  if (status === "RISK_HALTED") return "RISK";
  if (status === "RISK_CLEARED") return "NOTICE";
  return status;
}

function cleanBotReasonText(value: string): string {
  return value
    .replace(/\b(SCAN_RESULT|CLOSED_LOSS|CLOSED_WIN|OPEN_CONFIRMED|POSITION_MONITOR)\b:?/gi, "")
    .replace(/\bconfirmation_required\s*=\s*\d+\b/gi, "")
    .replace(/\brequired round 3 entry rule failed\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

function botDecisionText(message: ReasonMessage): string {
  const symbol = message.symbol || "Signal";
  const score = Number.isFinite(message.confirmation_score ?? Number.NaN) ? Number(message.confirmation_score) : null;
  const required = Number.isFinite(message.confirmation_required ?? Number.NaN) ? Number(message.confirmation_required) : 5;
  const raw = cleanBotReasonText(message.reason || "");
  if (message.groqGenerated && raw && !/^\s*(score|symbol|ticket|status)\b/i.test(raw)) return raw;
  if (message.status === "SCAN_RESULT") {
    const derivedMissing = [
      message.htf_bias && ["NOT_ALIGNED", "UNCLEAR", "WAIT", "NONE", "FALSE"].includes(message.htf_bias.toUpperCase()) ? "HTF alignment" : "",
      message.momentum !== true && message.pullback_retest !== true ? "momentum/pullback" : "",
      message.bos !== true && message.liquidity_sweep !== true && message.fvg !== true && message.fvg_retest !== true ? "structure confirmation" : "",
    ].filter(Boolean);
    const missing = uniqueScanLabels([...(message.confirmation_missing ?? []).map(scanBlockerLabel), ...derivedMissing]);
    if (missing.length) {
      return `${symbol} is not ready yet. History and spread are fine, but ${joinHumanList(missing.map((item) => item.toLowerCase()))} ${missing.length === 1 ? "is" : "are"} still missing.`;
    }
    return `${symbol} scan is close. Score ${score ?? 0}/${required}; waiting for the balanced entry gates to fully align.`;
  }
  if (message.status === "CLOSED_LOSS") {
    const legacy = /legacy/i.test(raw) ? " This trade is marked as a legacy-path loss." : "";
    const reason = raw || `${symbol} closed at stop loss because the entry did not hold after execution.`;
    return reason.includes(symbol) ? `${reason}${legacy}` : `${symbol} ${reason.charAt(0).toLowerCase()}${reason.slice(1)}${legacy}`;
  }
  if (message.status === "CLOSED_WIN") {
    return raw && raw.includes(symbol) ? raw : `${symbol} closed in profit. ${raw || "The setup reached its target."}`;
  }
  if (message.status === "OPEN_CONFIRMED" || message.status === "Accepted") {
    const ticket = message.ticket ? ` Ticket ${message.ticket}.` : "";
    if (raw && !/^symbol:/i.test(raw)) return raw.includes(symbol) ? raw : `${symbol} ${raw.charAt(0).toLowerCase()}${raw.slice(1)}`;
    return `${symbol} trade opened successfully.${ticket}`;
  }
  return raw && raw.includes(symbol) ? raw : `${symbol}: ${raw || "Waiting for the next validation update."}`;
}

function latestScanCycleMs(messages: ReasonMessage[]): number {
  const values = messages
    .filter((message) => message.status === "SCAN_RESULT")
    .map((message) => new Date(message.timestamp).getTime())
    .filter(Number.isFinite);
  return values.length ? Math.max(...values) : 0;
}

function currentBotMessages(messages: ReasonMessage[]): ReasonMessage[] {
  const latestScanMs = latestScanCycleMs(messages);
  return messages
    .filter((message) => {
      if (isTradeLifecycleMessage(message)) return true;
      if (message.status === "SCAN_RESULT") {
        const messageMs = new Date(message.timestamp).getTime();
        return !latestScanMs || (Number.isFinite(messageMs) && latestScanMs - messageMs <= 10000);
      }
      if (isRiskNoticeStatus(message.status.toUpperCase())) return true;
      const messageMs = new Date(message.timestamp).getTime();
      return !latestScanMs || (Number.isFinite(messageMs) && messageMs >= latestScanMs);
    })
    .slice(0, 3);
}

function reasonMessagesSignature(messages: ReasonMessage[]): string {
  return messages
    .map((message) => [message.event_id || message.id, message.symbol, message.status, message.timestamp, message.reason, message.ticket || "", message.validation_status || ""].join("\u001f"))
    .join("\u001e");
}

function setReasonMessagesIfChanged(setter: React.Dispatch<React.SetStateAction<ReasonMessage[]>>, next: ReasonMessage[]): void {
  setter((current) => (reasonMessagesSignature(current) === reasonMessagesSignature(next) ? current : next));
}

function ValidationReasonPanel({ contexts, refreshToken = 0 }: { contexts: ReasonContext[]; refreshToken?: number }) {
  void refreshToken;
  const storedMessages = useMemo(() => normalizeReasonMessages(contexts), [contexts]);
  const currentHistoryWaiting = contexts.some((context) => context.history_ready === false || readText(context, ["validation_status"], "").toUpperCase() === "WAITING_FOR_MT5_HISTORY_SYNC");
  const visibleMessages = filterVisibleBotMessages(
    currentHistoryWaiting
      ? storedMessages
      : storedMessages.filter((message) => !/history sync|insufficient historical data|history.*insufficient|insufficient real candles/i.test(message.reason) && message.validation_status !== "WAITING_FOR_MT5_HISTORY_SYNC"),
  );
  const botMessages = currentBotMessages(visibleMessages);
  return (
    <div className="premium-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="premium-section-eyebrow">Reason</p>
          <p className="premium-metric-value text-white">Bot Decisions</p>
        </div>
        <p className="premium-metric-label">Latest 3 messages</p>
      </div>
      {botMessages.length > 0 ? (
        <div className="reason-message-list">
          {botMessages.map((message) => (
            <article className="reason-message" key={message.event_id || message.id}>
              <div>
                <span className={`reason-status ${message.status.toLowerCase()}`}>{botStatusLabel(message.status)}</span>
                <strong>{message.symbol}</strong>
              </div>
              <p>{botDecisionText(message)}</p>
              <time>{formatTradeTime(message.timestamp)}</time>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState text="Waiting for validation decisions" />
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
  onAction: (action: "start" | "pause" | "resume" | "stop") => void;
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
  const targetValidationTrades = readNumber(session, ["target_validation_trades"], readNumber(config, ["target_validation_trades", "target_closed_trades"], TARGET_TRADES));
  const wins = readNumber(session, ["wins"], 0);
  const losses = readNumber(session, ["losses"], 0);
  const actualClosedTrades = wins + losses || readNumber(session, ["current_closed_trades", "current_session_closed"], 0);
  const totalTrades = actualClosedTrades + readNumber(session, ["current_open_trades"], 0);
  const remainingTrades = Math.max(0, targetValidationTrades - actualClosedTrades);
  const winRate = actualClosedTrades ? (wins / actualClosedTrades) * 100 : 0;
  const netPnl = readNumber(session, ["net_pnl"], 0);
  const reasonMessages = buildReasonContexts({ ...emptyData, autoValidation: status });
  const currentOpenTrades = readNumber(session, ["current_open_trades"], 0);
  const currentSessionId = readText(session, ["session_id", "id", "validation_session_id"], "");
  const currentSessionStarted = Boolean(currentSessionId) && !["READY_ROUND_3", "COMPLETED", "STOPPED"].includes(mode);
  const startDisabled = workingAction !== null || currentSessionStarted || recoverableSession || currentOpenTrades > 0 || !["", "IDLE", "OFF", "READY", "READY_ROUND_3", "COMPLETED", "STOPPED"].includes(mode);
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <SectionTitle eyebrow="AUTO Demo Validation" title={`${TARGET_TRADES}-Trade Bot Test: ${mode === "IDLE" ? "OFF" : mode}`} />
        <div className="flex flex-wrap gap-2">
          <button className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-slate-950 disabled:bg-slate-700 disabled:text-slate-400" disabled={startDisabled} onClick={() => onAction("start")} type="button">
            Start {TARGET_TRADES}-Trade Validation
          </button>
          <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "VALIDATION_IN_PROGRESS", "WAITING_FOR_OPEN_TRADES_TO_CLOSE", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC", "PAUSED_REQUIRES_USER_RESUME"].includes(mode)} onClick={() => onAction("pause")} type="button">
            Pause
          </button>
          <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 disabled:text-slate-500" disabled={workingAction !== null || !["PAUSED", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} onClick={() => onAction("resume")} type="button">
            Resume
          </button>
          <button className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm font-bold text-amber-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "VALIDATION_IN_PROGRESS", "PAUSED", "WAITING_FOR_OPEN_TRADES_TO_CLOSE", "WAITING_FOR_MT5_RECONNECT", "WAITING_FOR_MT5_HISTORY_SYNC", "PAUSED_REQUIRES_USER_RESUME", "RECOVERED_STOPPED"].includes(mode)} onClick={() => onAction("stop")} type="button">
            Stop
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
        <Metric label="Closed Trades" value={String(actualClosedTrades)} compact />
        <Metric label="Open Trades" value={String(readNumber(session, ["current_open_trades"], 0))} compact />
        <Metric label="Open Trade Limit" value={String(readNumber(config, ["max_open_trades_total"], 0))} compact />
        <Metric label="Per-Symbol Limit" value={String(readNumber(config, ["max_open_trades_per_symbol"], 0))} compact />
        <Metric label="Daily Demo Trades" value={`${readNumber(session, ["daily_demo_trade_count"], 0)} / ${readNumber(config, ["max_daily_demo_trades", "max_daily_trades"], 30)}`} compact />
        <Metric label="Wins / Losses" value={`${wins} / ${losses}`} compact />
        <Metric label="Win Rate" value={`${winRate.toFixed(2)}%`} compact />
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
        <Metric label="Current Session Closed" value={String(actualClosedTrades)} compact />
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
          <Metric label="Closed Trades" value={String(actualClosedTrades)} compact />
          <Metric label="Wins" value={String(wins)} valueClass="text-emerald-300" compact />
          <Metric label="Losses" value={String(losses)} valueClass="text-rose-300" compact />
          <Metric label="Win Rate" value={`${winRate.toFixed(2)}%`} compact />
          <Metric label="Net P&L" value={money(netPnl)} valueClass={pnlClass(netPnl)} compact />
          <Metric label="Average RR" value={`${readNumber(session, ["avg_rr", "average_rr"], 0).toFixed(2)}:1`} compact />
          <Metric label="Profit Factor" value={readNumber(session, ["profit_factor"], 0).toFixed(2)} compact />
          <Metric label="Max Drawdown" value={money(readNumber(session, ["max_drawdown"], 0))} compact />
          <Metric label="Best Setup Type" value={readText(session, ["best_setup_type"], "Unavailable")} compact />
          <Metric label="Worst Setup Type" value={readText(session, ["worst_setup_type"], "Unavailable")} compact />
        </div>
        <div className="mt-4">
          <ValidationReasonPanel contexts={reasonMessages} />
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
