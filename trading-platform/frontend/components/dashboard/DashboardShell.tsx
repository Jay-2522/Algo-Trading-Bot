"use client";

import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import {
  fetchClientOperatingDashboard,
  fetchClientMarketPrices,
  fetchClientSignals,
  approveExecutionModeSignal,
  emergencyStopAutoValidation,
  previewClientDemoTrade,
  pauseAutoValidation,
  rejectExecutionModeSignal,
  resumeAutoValidation,
  sendGuardedClientDemoTrade,
  setExecutionMode,
  startAutoValidation,
  stopAutoValidation,
  syncClientLifecycle,
  syncClientPositionsToJournal,
  type ApiRecord,
  type ClientOrderPayload,
} from "@/lib/clientOperatingDashboardApi";
import { readNumber, readText } from "@/lib/dashboard-formatters";

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

const READY_SIGNAL_HOLD_SECONDS = 30;

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

function isMarketOpen(tick: ApiRecord | null): boolean {
  return readText(tick, ["status"], "").toUpperCase() === "OK" && readText(tick, ["freshness"], "").toUpperCase() === "READY";
}

function marketLabel(tick: ApiRecord | null): string {
  const status = readText(tick, ["status"], "").toUpperCase();
  if (status === "SYMBOL_NOT_AVAILABLE" || status === "SYMBOL_UNAVAILABLE") return "Symbol Not Available";
  return isMarketOpen(tick) ? "Market Ready" : "Market Closed / Feed Offline";
}

function xauusdReadinessLabel(tick: ApiRecord | null, signal: ApiRecord | null): string {
  const status = readText(tick, ["status"], "").toUpperCase();
  if (status === "SYMBOL_NOT_AVAILABLE" || status === "SYMBOL_UNAVAILABLE") return "Symbol Not Available";
  if (!isMarketOpen(tick)) return "Market Closed / Feed Offline";
  const action = readText(signal, ["signal"], "WAIT").toUpperCase();
  if (action === "BUY" || action === "SELL") return "Ready for Future Demo Test";
  return "Waiting for Strategy Setup";
}

function statusTone(status: string): string {
  const text = status.toUpperCase();
  if (text.includes("OPEN") || text.includes("CONNECTED") || text.includes("READY") || text.includes("DEMO")) return "text-emerald-300 border-emerald-400/30 bg-emerald-400/10";
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

function rrFrom(entry: number, action: "BUY" | "SELL", stopLoss: number, takeProfit: number): number | null {
  if (entry <= 0 || stopLoss <= 0 || takeProfit <= 0) return null;
  const risk = action === "BUY" ? entry - stopLoss : stopLoss - entry;
  const reward = action === "BUY" ? takeProfit - entry : entry - takeProfit;
  if (risk <= 0 || reward <= 0) return null;
  return Number((reward / risk).toFixed(2));
}

function cleanBlockers(blockers: unknown): string[] {
  if (!Array.isArray(blockers)) return [];
  return blockers.map((item) => String(item).replaceAll("_", " ").toLowerCase()).slice(0, 6);
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
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<ScopedSymbol>("EURUSD");
  const [preview, setPreview] = useState<ApiRecord | null>(null);
  const [previewSignal, setPreviewSignal] = useState<ApiRecord | null>(null);
  const [sendResult, setSendResult] = useState<ApiRecord | null>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [workingAction, setWorkingAction] = useState<string | null>(null);
  const [heldReadySignals, setHeldReadySignals] = useState<HeldSignals>({});
  const [nowMs, setNowMs] = useState(Date.now());
  const requestInFlight = useRef(false);
  const priceRequestInFlight = useRef(false);
  const signalRequestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setLoading(true);
    try {
      const result = await fetchClientOperatingDashboard();
      const payload = result.data;
      setData((current) => ({
        account: "account" in payload ? asRecord(payload.account) : current.account,
        eurusdTick: "eurusdTick" in payload ? asRecord(payload.eurusdTick) : current.eurusdTick,
        xauusdTick: "xauusdTick" in payload ? asRecord(payload.xauusdTick) : current.xauusdTick,
        marketScope: "marketScope" in payload && Array.isArray(payload.marketScope) ? (payload.marketScope.filter((item) => asRecord(item)) as ApiRecord[]) : current.marketScope,
        clientSignals: "clientSignals" in payload ? recordsFrom(payload.clientSignals, "signals") : current.clientSignals,
        brokerAccounts: "brokerAccounts" in payload ? recordsFrom(payload.brokerAccounts, "accounts") : current.brokerAccounts,
        brokerCopyPlans: "brokerCopyReadiness" in payload ? recordsFrom(payload.brokerCopyReadiness, "plans") : current.brokerCopyPlans,
        currentTerminalAccount: "brokerAccounts" in payload ? asRecord(asRecord(payload.brokerAccounts)?.current_terminal_account) : current.currentTerminalAccount,
        vantageXauusdStatus: "vantageXauusdStatus" in payload ? asRecord(payload.vantageXauusdStatus) : current.vantageXauusdStatus,
        vantageXauusdPreview: "vantageXauusdPreview" in payload ? asRecord(payload.vantageXauusdPreview) : current.vantageXauusdPreview,
        openPositions: "openPositions" in payload ? recordsFrom(payload.openPositions, "positions") : current.openPositions,
        recentTrades: "recentTrades" in payload && Array.isArray(payload.recentTrades) ? (payload.recentTrades.filter((item) => asRecord(item)) as ApiRecord[]) : current.recentTrades,
        journalSummary: "journalSummary" in payload ? asRecord(payload.journalSummary) : current.journalSummary,
        outcomeSummary: "outcomeSummary" in payload ? asRecord(payload.outcomeSummary) : current.outcomeSummary,
        guardedStatus: "guardedStatus" in payload ? asRecord(payload.guardedStatus) : current.guardedStatus,
        executionMode: "executionMode" in payload ? asRecord(payload.executionMode) : current.executionMode,
        autoValidation: "autoValidation" in payload ? asRecord(payload.autoValidation) : current.autoValidation,
      }));
      setErrors(result.errors);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
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
        setData((current) => ({
          ...current,
          eurusdTick: asRecord(prices.eurusdTick),
          xauusdTick: asRecord(prices.xauusdTick),
        }));
      }
      setErrors(prices.errors);
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
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
        setData((current) => ({
          ...current,
          clientSignals: recordsFrom(signals.signals, "signals"),
        }));
      }
      setErrors(signals.errors);
    } catch (error) {
      setErrors([error instanceof Error ? error.message : "Backend unavailable"]);
    } finally {
      signalRequestInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    void refresh();
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

  async function handleSync(action: "positions" | "lifecycle") {
    setWorkingAction(action);
    setTradeError(null);
    try {
      if (action === "positions") {
        await syncClientPositionsToJournal();
      } else {
        await syncClientLifecycle();
      }
      await refresh();
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : "Sync failed.");
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
    setWorkingAction(`auto-validation-${action}`);
    setTradeError(null);
    try {
      const result =
        action === "start"
          ? await startAutoValidation()
          : action === "pause"
            ? await pauseAutoValidation()
            : action === "resume"
              ? await resumeAutoValidation()
              : action === "emergency-stop"
                ? await emergencyStopAutoValidation()
                : await stopAutoValidation();
      setData((current) => ({ ...current, autoValidation: result }));
    } catch (error) {
      setTradeError(error instanceof Error ? error.message : "AUTO validation action failed.");
    } finally {
      setWorkingAction(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#050816] text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5 shadow-2xl shadow-black/30">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.24em] text-blue-300">Client-Scoped AI Trading</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl">AI Trading Dashboard</h1>
              <p className="mt-2 text-sm text-slate-400">EURUSD, XAUUSD, and NIFTY50 signal monitoring with guarded execution.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 hover:bg-slate-800" onClick={() => void refresh()} type="button">
                {loading ? "Refreshing..." : "Refresh"}
              </button>
              <button className="rounded-xl border border-blue-400/30 bg-blue-500/10 px-4 py-2 text-sm font-bold text-blue-100 hover:bg-blue-500/20" onClick={() => void handleSync("positions")} type="button">
                Refresh Positions
              </button>
              <button className="rounded-xl border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm font-bold text-cyan-100 hover:bg-cyan-500/20" onClick={() => void handleSync("lifecycle")} type="button">
                Sync Lifecycle
              </button>
            </div>
          </div>
          <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_1fr_0.8fr_1fr]">
            <section>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Account Status</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <Metric label="Account" value={readText(data.account, ["login"], "Unavailable")} />
                <Metric label="Server" value={readText(data.account, ["server"], "Unavailable")} />
                <Metric label="Balance" value={money(numeric(data.account, ["balance"]))} valueClass="whitespace-nowrap text-white" />
                <Metric label="Equity" value={money(numeric(data.account, ["equity"]))} valueClass="whitespace-nowrap text-white" />
              </div>
            </section>
            <section>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Account Health</p>
              <div className="mt-3 grid gap-3">
                <Metric label="Margin Level" value={percent(numeric(data.account, ["margin_level"]))} compact />
                <Metric label="Free Margin" value={money(numeric(data.account, ["free_margin"]))} valueClass="whitespace-nowrap text-white" compact />
                <Metric label="Used Margin" value={money(numeric(data.account, ["used_margin"]))} valueClass="whitespace-nowrap text-white" compact />
              </div>
            </section>
            <section>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Floating P&L</p>
              <div className="mt-3 grid gap-3">
                <Metric label="Open Positions" value={String(data.openPositions.length)} compact />
                <Metric label="Floating P&L" value={money(openFloatingPnl)} valueClass={pnlClass(openFloatingPnl)} />
                <Metric label="Today's P&L" value={money(todayPnl(closedTrades))} valueClass={pnlClass(todayPnl(closedTrades))} compact />
              </div>
            </section>
            <section>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Last Trade</p>
              <div className="mt-3 grid gap-3">
                {lastTrade ? (
                  <>
                    <Metric label="Setup" value={`${readText(lastTrade, ["symbol"], "Trade")} ${readText(lastTrade, ["side"], "")}`} compact />
                    <Metric label="Result" value={readText(lastTrade, ["result"], "Unavailable")} compact />
                    <Metric label="P&L" value={money(readNumber(lastTrade, ["net_pnl", "profit_loss", "realized_pnl"], 0))} valueClass={pnlClass(readNumber(lastTrade, ["net_pnl", "profit_loss", "realized_pnl"], 0))} compact />
                  </>
                ) : (
                  <Metric label="Status" value="No completed trades yet" compact />
                )}
              </div>
            </section>
          </div>
          <p className="mt-3 text-xs text-slate-500">{lastUpdated ? `Prices refresh every 1s. AI signals refresh every 5s. Last full update ${lastUpdated}.` : "Preparing dashboard data."}</p>
        </header>

        <ExecutionModePanel
          mode={data.executionMode}
          nowMs={nowMs}
          workingAction={workingAction}
          onApprove={(approvalId) => void handleApprovalDecision("approve", approvalId)}
          onReject={(approvalId) => void handleApprovalDecision("reject", approvalId)}
          onSetMode={(mode) => void handleExecutionModeChange(mode)}
        />

        <AutoValidationPanel
          status={data.autoValidation}
          workingAction={workingAction}
          onAction={(action) => void handleAutoValidationAction(action)}
        />

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <SectionTitle eyebrow="Market Overview" title="Scoped Instruments" />
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <MarketCard title="EURUSD" tick={data.eurusdTick} scope={data.marketScope.find((item) => readText(item, ["symbol"], "") === "EURUSD") ?? null} />
            <MarketCard title="XAUUSD" tick={data.xauusdTick} scope={data.marketScope.find((item) => readText(item, ["symbol"], "") === "XAUUSD") ?? null} signal={displayedSignals.find((item) => readText(item, ["symbol"], "") === "XAUUSD") ?? null} />
            <NiftyMarketCard scope={data.marketScope.find((item) => readText(item, ["symbol"], "") === "NIFTY50") ?? null} />
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <SectionTitle eyebrow="AI Signal Center" title="Current Client Signals" />
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            {(["EURUSD", "XAUUSD", "NIFTY50"] as const).map((symbol) => (
              <SignalCard
                key={symbol}
                canPreview={canPreviewSignal(displayedSignals.find((item) => readText(item, ["symbol"], "") === symbol) ?? null)}
                onPreview={(signal) => void handlePreview(signal)}
                selected={selectedSymbol === symbol}
                signal={displayedSignals.find((item) => readText(item, ["symbol"], "") === symbol) ?? null}
                symbol={symbol}
                validForSeconds={signalHoldRemaining(displayedSignals.find((item) => readText(item, ["symbol"], "") === symbol) ?? null, nowMs)}
                onSelect={() => setSelectedSymbol(symbol)}
              />
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <SectionTitle eyebrow="Broker Accounts" title="StarTrader, FxPro, and Vantage" />
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            {(["STARTRADER", "FXPRO", "VANTAGE"] as const).map((brokerId) => (
              <BrokerAccountCard
                account={data.brokerAccounts.find((account) => readText(account, ["broker_id"], "") === brokerId) ?? null}
                brokerId={brokerId}
                copyPlan={data.brokerCopyPlans.find((plan) => readText(plan, ["broker_id"], "") === brokerId) ?? null}
                key={brokerId}
              />
            ))}
          </div>
          <CurrentTerminalCard account={data.currentTerminalAccount} />
        </section>

        <VantageXauusdValidationPanel status={data.vantageXauusdStatus} preview={data.vantageXauusdPreview} />

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Signal Execution Panel</p>
                <h2 className="mt-1 text-2xl font-black">Review the selected AI signal and approve demo execution.</h2>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${statusTone(readText(selectedSignal, ["execution_status"], "WAITING"))}`}>{readText(selectedSignal, ["execution_status"], "WAITING")}</span>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <Metric label="Selected Symbol" value={selectedSymbol} />
              <Metric label="AI Direction" value={signalAction} />
              <Metric label="Entry" value={marketNumber(signalEntry, selectedSymbol === "XAUUSD" ? 2 : 5)} />
              <Metric label="Stop Loss" value={marketNumber(stopLoss, selectedSymbol === "XAUUSD" ? 2 : 5)} />
              <Metric label="Take Profit" value={marketNumber(takeProfit, selectedSymbol === "XAUUSD" ? 2 : 5)} />
              <Metric label="Lot" value="0.01" />
              <Metric label="Risk / Reward" value={Number.isFinite(rr) ? `${rr.toFixed(2)}:1` : "Unavailable"} />
              <Metric label="Risk Status" value={readText(selectedSignal, ["risk_status"], "NO_SIGNAL").replaceAll("_", " ")} />
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <button className="rounded-xl bg-blue-500 px-4 py-3 text-sm font-black text-white hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400" disabled={!canPreview} onClick={() => void handlePreview()} type="button">
                {workingAction === "preview" ? "Previewing..." : "Preview Signal Trade"}
              </button>
              <button className="rounded-xl bg-emerald-500 px-4 py-3 text-sm font-black text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400" disabled={!canSend} onClick={() => setConfirmOpen(true)} type="button">
                Confirm & Send Demo Order
              </button>
            </div>

            <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Trade Status</p>
              <div className="mt-3 grid gap-2 text-sm text-slate-300">
                {tradeStatus.map((status) => (
                  <div className="flex items-center justify-between gap-3" key={status.text}>
                    <span className="font-bold text-slate-200">{status.text}</span>
                    <span className={status.ok ? "font-bold text-emerald-300" : "font-bold text-rose-300"}>{status.ok ? "Ready" : "Blocked"}</span>
                  </div>
                ))}
              </div>
            </div>

            {preview && <PreviewPanel preview={preview} signal={previewSignal ?? selectedSignal} canSend={canSend} validForSeconds={signalHoldRemaining(previewSignal ?? selectedSignal, nowMs)} onConfirm={() => setConfirmOpen(true)} />}

            {(tradeError || sendResult) && (
              <div className={`mt-4 rounded-xl border p-4 text-sm ${tradeError ? "border-rose-400/25 bg-rose-500/10 text-rose-100" : "border-emerald-400/25 bg-emerald-500/10 text-emerald-100"}`}>
                {tradeError || `Demo order status: ${readText(sendResult, ["status"], "Submitted")}`}
              </div>
            )}
            {signalAction === "WAIT" ? <EmptyState text="Waiting for a valid strategy setup." /> : null}
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
            <SectionTitle eyebrow="Open Trades" title="Active Demo Positions" />
            {data.openPositions.length ? <OpenPositionsTable positions={data.openPositions} /> : <EmptyState text="Waiting for the next AI-approved trade." />}
          </section>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <SectionTitle eyebrow="Closed Demo Trades" title="Completed Trade Journal" />
            <Link className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 hover:bg-slate-800" href="/dashboard/history">
              View Full Trade History
            </Link>
          </div>
          {closedTrades.length ? <ClosedTradesTable trades={closedTrades} /> : <EmptyState text="Completed trades will appear here." />}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <SectionTitle eyebrow="Performance Summary" title="Demo Analytics" />
          {closedCount ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <Metric label="Total Trades" value={String(totalTrades)} />
              <Metric label="Closed Trades" value={String(closedCount)} />
              <Metric label="Win Rate" value={`${winRate.toFixed(2)}%`} />
              <Metric label="Net P&L" value={money(netPnl)} valueClass={pnlClass(netPnl)} />
              <Metric label="Average RR" value={avgRr ? avgRr.toFixed(2) : "Unavailable"} />
              {closedCount >= 5 ? <Metric label="Best / Worst" value={`${money(readNumber(bestTrade, ["realized_pnl", "net_pnl"], Number.NaN))} / ${money(readNumber(worstTrade, ["realized_pnl", "net_pnl"], Number.NaN))}`} /> : null}
            </div>
          ) : (
            <EmptyState text="Need more closed trades." />
          )}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-4">
          <div className="flex flex-wrap items-center gap-3">
            <SafetyPill text="DEMO MODE" />
            <SafetyPill text="LIVE TRADING DISABLED" />
            <SafetyPill text="GUARDED EXECUTION ENABLED" />
          </div>
          {errors.length > 0 && (
            <div className="mt-3 rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm text-amber-100">
              <strong className="block text-amber-50">Backend unavailable</strong>
              Some dashboard data is unavailable. Last successful values remain visible where available.
            </div>
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
  workingAction,
  onAction,
}: {
  status: ApiRecord | null;
  workingAction: string | null;
  onAction: (action: "start" | "pause" | "resume" | "stop" | "emergency-stop") => void;
}) {
  const session = asRecord(status?.session);
  const config = asRecord(status?.config);
  const watched = asRecord(status?.current_signal_watched);
  const decision = asRecord(status?.last_execution_decision);
  const mode = readText(session, ["status"], "OFF");
  const blockers = Array.isArray(status?.blocked_reasons) ? status.blocked_reasons.map(String) : [];
  const nextEligible = readText(status, ["next_eligible_time"], "");
  return (
    <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <SectionTitle eyebrow="AUTO Demo Validation" title={`30-Trade Bot Test: ${mode === "IDLE" ? "OFF" : mode}`} />
        <div className="flex flex-wrap gap-2">
          <button className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-black text-slate-950 disabled:bg-slate-700 disabled:text-slate-400" disabled={workingAction !== null || mode === "RUNNING"} onClick={() => onAction("start")} type="button">
            Start 30-Trade Validation
          </button>
          <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 disabled:text-slate-500" disabled={workingAction !== null || mode !== "RUNNING"} onClick={() => onAction("pause")} type="button">
            Pause
          </button>
          <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 disabled:text-slate-500" disabled={workingAction !== null || mode !== "PAUSED"} onClick={() => onAction("resume")} type="button">
            Resume
          </button>
          <button className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm font-bold text-amber-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "PAUSED"].includes(mode)} onClick={() => onAction("stop")} type="button">
            Stop
          </button>
          <button className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-4 py-2 text-sm font-black text-rose-100 disabled:text-slate-500" disabled={workingAction !== null || !["RUNNING", "PAUSED"].includes(mode)} onClick={() => onAction("emergency-stop")} type="button">
            Emergency Stop
          </button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <Metric label="Target Trades" value={String(readNumber(session, ["target_closed_trades"], readNumber(config, ["target_closed_trades"], 30)))} compact />
        <Metric label="Completed" value={String(readNumber(session, ["current_closed_trades"], 0))} compact />
        <Metric label="Open Trades" value={String(readNumber(session, ["current_open_trades"], 0))} compact />
        <Metric label="Wins / Losses" value={`${readNumber(session, ["wins"], 0)} / ${readNumber(session, ["losses"], 0)}`} compact />
        <Metric label="Win Rate" value={`${readNumber(session, ["win_rate"], 0).toFixed(2)}%`} compact />
        <Metric label="Net P&L" value={money(readNumber(session, ["net_pnl"], 0))} valueClass={pnlClass(readNumber(session, ["net_pnl"], 0))} compact />
        <Metric label="Max Drawdown" value={money(readNumber(session, ["max_drawdown"], 0))} compact />
        <Metric label="Lot" value={String(readNumber(config, ["lot_size"], 0.01))} compact />
        <Metric label="Allowed Symbols" value={Array.isArray(config?.allowed_symbols) ? config.allowed_symbols.join(", ") : "XAUUSD, EURUSD"} compact />
        <Metric label="Cooldown" value={`${readNumber(config, ["cooldown_after_trade_minutes"], 15)}m`} compact />
        <Metric label="Next Eligible" value={nextEligible ? formatTradeTime(nextEligible) : "Now"} compact />
        <Metric label="Safety" value="Demo / Vantage Only" valueClass="text-emerald-300" compact />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Current Signal Watched</p>
          <p className="mt-2 text-lg font-black text-white">{watched ? `${readText(watched, ["symbol"], "Signal")} ${readText(watched, ["signal"], "WAIT")}` : "None"}</p>
          <p className="mt-1 text-sm font-bold text-slate-400">{readText(watched, ["setup_reason", "reason"], "Waiting for qualified signal.")}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-[#0F172A] p-4">
          <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-400">Last Execution Decision</p>
          <p className="mt-2 text-lg font-black text-white">{readText(decision, ["status"], "No decision yet")}</p>
          {blockers.length > 0 ? <p className="mt-1 text-sm font-bold text-amber-100">{blockers.join(", ")}</p> : <p className="mt-1 text-sm font-bold text-slate-400">No blocked reasons recorded.</p>}
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
  const feedUnavailable = !tick || readText(tick, ["status"], "").toUpperCase() !== "OK";
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
      {title === "XAUUSD" ? <p className="mt-3 text-sm font-bold text-slate-400">XAUUSD execution is not enabled today; valid setups are classified for a future guarded demo test.</p> : null}
      {feedUnavailable ? <p className="mt-3 text-sm font-bold text-slate-400">Market feed unavailable.</p> : null}
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
  return <div className="mt-4 rounded-xl border border-dashed border-slate-700 bg-[#0F172A] p-5 text-sm font-bold text-slate-400">{text}</div>;
}

function SafetyPill({ text }: { text: string }) {
  return <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1.5 text-xs font-black uppercase tracking-[0.16em] text-emerald-200">{text}</span>;
}
