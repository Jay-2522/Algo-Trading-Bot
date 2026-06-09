"use client";

import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import {
  fetchClientOperatingDashboard,
  previewClientDemoTrade,
  sendGuardedClientDemoTrade,
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
  openPositions: ApiRecord[];
  recentTrades: ApiRecord[];
  journalSummary: ApiRecord | null;
  outcomeSummary: ApiRecord | null;
  guardedStatus: ApiRecord | null;
};

type TradeForm = {
  symbol: "EURUSD";
  action: "BUY" | "SELL";
  stopLoss: string;
  takeProfit: string;
};

const emptyData: DashboardData = {
  account: null,
  eurusdTick: null,
  xauusdTick: null,
  openPositions: [],
  recentTrades: [],
  journalSummary: null,
  outcomeSummary: null,
  guardedStatus: null,
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
  return isMarketOpen(tick) ? "Market Open" : "Market Closed / Feed Offline";
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

function currentEntryPrice(tick: ApiRecord | null, action: "BUY" | "SELL"): number {
  return action === "BUY" ? readNumber(tick, ["ask"], 0) : readNumber(tick, ["bid"], 0);
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

function tradeStatusMessage(marketOpen: boolean, openTradeExists: boolean, stopLoss: string, takeProfit: string, formValid: boolean): { ok: boolean; text: string } {
  if (!marketOpen) return { ok: false, text: "Market Closed" };
  if (!stopLoss) return { ok: false, text: "Stop Loss Required" };
  if (!takeProfit) return { ok: false, text: "Take Profit Required" };
  if (openTradeExists) return { ok: false, text: "Existing Demo Position Active" };
  if (!formValid) return { ok: false, text: "Check SL / TP Placement" };
  return { ok: true, text: "Trade Ready" };
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
  const [form, setForm] = useState<TradeForm>({ symbol: "EURUSD", action: "BUY", stopLoss: "", takeProfit: "" });
  const [preview, setPreview] = useState<ApiRecord | null>(null);
  const [sendResult, setSendResult] = useState<ApiRecord | null>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [workingAction, setWorkingAction] = useState<string | null>(null);
  const requestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setLoading(true);
    try {
      const result = await fetchClientOperatingDashboard();
      const payload = result.data;
      setData({
        account: asRecord(payload.account),
        eurusdTick: asRecord(payload.eurusdTick),
        xauusdTick: asRecord(payload.xauusdTick),
        openPositions: recordsFrom(payload.openPositions, "positions"),
        recentTrades: Array.isArray(payload.recentTrades) ? (payload.recentTrades.filter((item) => asRecord(item)) as ApiRecord[]) : [],
        journalSummary: asRecord(payload.journalSummary),
        outcomeSummary: asRecord(payload.outcomeSummary),
        guardedStatus: asRecord(payload.guardedStatus),
      });
      setErrors(result.errors);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    } finally {
      setLoading(false);
      requestInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const interval = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const closedTrades = useMemo(() => data.recentTrades.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED"), [data.recentTrades]);
  const marketOpen = isMarketOpen(data.eurusdTick);
  const openTradeExists = data.openPositions.length > 0 || readNumber(data.journalSummary, ["open_demo_trades"], 0) > 0;
  const approvalReady = preview?.approved_for_future_demo_order === true;
  const stopLoss = Number(form.stopLoss);
  const takeProfit = Number(form.takeProfit);
  const entryPrice = currentEntryPrice(data.eurusdTick, form.action);
  const rr = rrFrom(entryPrice, form.action, stopLoss, takeProfit);
  const formValid = form.symbol === "EURUSD" && Number.isFinite(stopLoss) && stopLoss > 0 && Number.isFinite(takeProfit) && takeProfit > 0 && rr !== null;
  const canPreview = marketOpen && !openTradeExists && formValid && !workingAction;
  const canSend = canPreview && approvalReady;
  const totalTrades = readNumber(data.journalSummary, ["total_trades"], 0);
  const closedCount = readNumber(data.journalSummary, ["closed_demo_trades"], 0);
  const winRate = readNumber(data.journalSummary, ["win_rate"], 0);
  const netPnl = readNumber(data.journalSummary, ["net_pnl"], 0);
  const avgRr = readNumber(data.journalSummary, ["avg_rr"], readNumber(data.outcomeSummary, ["avg_rr"], 0));
  const bestTrade = asRecord(data.outcomeSummary?.best_trade);
  const worstTrade = asRecord(data.outcomeSummary?.worst_trade);
  const openFloatingPnl = floatingPnl(data.openPositions);
  const lastTrade = closedTrades[0] ?? null;
  const tradeStatus = tradeStatusMessage(marketOpen, openTradeExists, form.stopLoss, form.takeProfit, formValid);

  const orderPayload = (): ClientOrderPayload => ({
    symbol: "EURUSD",
    action: form.action,
    lot: 0.01,
    entry_price: entryPrice,
    stop_loss: stopLoss,
    take_profit: takeProfit,
  });

  async function handlePreview() {
    setTradeError(null);
    setSendResult(null);
    if (!canPreview) {
      setTradeError("Preview is blocked until the market is open, SL/TP are valid, and no demo position is open.");
      return;
    }
    setWorkingAction("preview");
    try {
      const result = await previewClientDemoTrade(orderPayload());
      setPreview(result);
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
      const result = await sendGuardedClientDemoTrade(orderPayload());
      setSendResult(result);
      setConfirmOpen(false);
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

  return (
    <main className="min-h-screen bg-[#050816] text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5 shadow-2xl shadow-black/30">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.24em] text-blue-300">MT5 Demo Operating Dashboard</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Client Trading Monitor</h1>
              <p className="mt-2 text-sm text-slate-400">Monitor demo account status, market feed, trades, and guarded demo execution.</p>
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
                <Metric label="Balance" value={money(numeric(data.account, ["balance"]))} />
                <Metric label="Equity" value={money(numeric(data.account, ["equity"]))} />
              </div>
            </section>
            <section>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Account Health</p>
              <div className="mt-3 grid gap-3">
                <Metric label="Margin Level" value={percent(numeric(data.account, ["margin_level"]))} compact />
                <Metric label="Free Margin" value={money(numeric(data.account, ["free_margin"]))} compact />
                <Metric label="Used Margin" value={money(numeric(data.account, ["used_margin"]))} compact />
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
          <section className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Forex Sessions</p>
              <div className="grid gap-2 sm:grid-cols-4 lg:min-w-[36rem]">
                {(["Sydney", "Tokyo", "London", "New York"] as const).map((session) => {
                  const open = sessionOpen(session);
                  return (
                    <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-[#0B1220] px-3 py-2" key={session}>
                      <span className="text-sm font-bold text-slate-200">{session}</span>
                      <span className={open ? "text-xs font-black text-emerald-300" : "text-xs font-black text-slate-500"}>{open ? "OPEN" : "CLOSED"}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
          <p className="mt-3 text-xs text-slate-500">{lastUpdated ? `Auto-refresh every 5 seconds. Last updated ${lastUpdated}.` : "Preparing dashboard data."}</p>
        </header>

        <section className="grid gap-4 lg:grid-cols-2">
          <MarketCard title="EURUSD" tick={data.eurusdTick} />
          <MarketCard title="XAUUSD" tick={data.xauusdTick} />
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-300">Quick Trade Panel</p>
                <h2 className="mt-1 text-2xl font-black">Guarded Demo Order</h2>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-black uppercase ${statusTone(marketLabel(data.eurusdTick))}`}>{marketLabel(data.eurusdTick)}</span>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Symbol
                <select className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" value={form.symbol} disabled>
                  <option>EURUSD</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Direction
                <select className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" value={form.action} onChange={(event) => setForm((current) => ({ ...current, action: event.target.value as "BUY" | "SELL" }))}>
                  <option>BUY</option>
                  <option>SELL</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Lot
                <input className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" value="0.01" disabled />
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Entry
                <input className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-slate-300" value={marketNumber(entryPrice)} disabled />
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Stop Loss
                <input className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" inputMode="decimal" placeholder="Required" value={form.stopLoss} onChange={(event) => setForm((current) => ({ ...current, stopLoss: event.target.value }))} />
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Take Profit
                <input className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" inputMode="decimal" placeholder="Required" value={form.takeProfit} onChange={(event) => setForm((current) => ({ ...current, takeProfit: event.target.value }))} />
              </label>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <button className="rounded-xl bg-blue-500 px-4 py-3 text-sm font-black text-white hover:bg-blue-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400" disabled={!canPreview} onClick={() => void handlePreview()} type="button">
                {workingAction === "preview" ? "Previewing..." : "Preview Trade"}
              </button>
              <button className="rounded-xl bg-emerald-500 px-4 py-3 text-sm font-black text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400" disabled={!canSend} onClick={() => setConfirmOpen(true)} type="button">
                Place Demo Trade
              </button>
            </div>

            <div className="mt-4 rounded-xl border border-slate-800 bg-[#0F172A] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Trade Status</p>
              <div className="mt-3 grid gap-2 text-sm text-slate-300">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-bold text-slate-200">{marketOpen ? "Market Open" : "Market Closed"}</span>
                  <span className={marketOpen ? "font-bold text-emerald-300" : "font-bold text-rose-300"}>{marketOpen ? "Ready" : "Blocked"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-bold text-slate-200">{tradeStatus.text}</span>
                  <span className={tradeStatus.ok ? "font-bold text-emerald-300" : "font-bold text-rose-300"}>{tradeStatus.ok ? "Ready" : "Blocked"}</span>
                </div>
              </div>
            </div>

            {preview && (
              <div className="mt-4 rounded-xl border border-blue-400/20 bg-blue-500/10 p-4">
                <p className="text-sm font-bold text-blue-100">Preview Status: {approvalReady ? "Approved" : "Needs Attention"}</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <Metric label="Risk / Reward" value={rr ? `${rr}:1` : "Unavailable"} compact />
                  <Metric label="Estimated Margin" value="Unavailable" compact />
                  <Metric label="Lot" value="0.01" compact />
                </div>
                {cleanBlockers(preview.blockers).length > 0 && (
                  <div className="mt-3 rounded-lg border border-amber-400/20 bg-amber-500/10 p-3 text-sm text-amber-100">
                    {cleanBlockers(preview.blockers).map((blocker) => (
                      <p key={blocker}>{blocker}</p>
                    ))}
                  </div>
                )}
              </div>
            )}

            {(tradeError || sendResult) && (
              <div className={`mt-4 rounded-xl border p-4 text-sm ${tradeError ? "border-rose-400/25 bg-rose-500/10 text-rose-100" : "border-emerald-400/25 bg-emerald-500/10 text-emerald-100"}`}>
                {tradeError || `Demo order status: ${readText(sendResult, ["status"], "Submitted")}`}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
            <SectionTitle eyebrow="Open Demo Positions" title="Active MT5 Demo Exposure" />
            {data.openPositions.length ? <OpenPositionsTable positions={data.openPositions} /> : <EmptyState text="Waiting for the next trade opportunity." />}
          </section>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <SectionTitle eyebrow="Closed Demo Trades" title="Completed Trade Journal" />
            <Link className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold text-slate-100 hover:bg-slate-800" href="/dashboard/history">
              View Trade History
            </Link>
          </div>
          {closedTrades.length ? <ClosedTradesTable trades={closedTrades} /> : <EmptyState text="Completed trades will appear here." />}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          <SectionTitle eyebrow="Performance Summary" title="Demo Analytics" />
          {closedCount ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
              <Metric label="Total Trades" value={String(totalTrades)} />
              <Metric label="Closed Trades" value={String(closedCount)} />
              <Metric label="Win Rate" value={`${winRate.toFixed(2)}%`} />
              <Metric label="Net P&L" value={money(netPnl)} valueClass={pnlClass(netPnl)} />
              <Metric label="Average RR" value={avgRr ? avgRr.toFixed(2) : "Unavailable"} />
              <Metric label="Best / Worst" value={`${money(readNumber(bestTrade, ["realized_pnl", "net_pnl"], Number.NaN))} / ${money(readNumber(worstTrade, ["realized_pnl", "net_pnl"], Number.NaN))}`} />
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
              Some dashboard data is unavailable. Values marked unavailable are not estimated.
            </div>
          )}
        </section>
      </div>

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-[#0B1220] p-6 shadow-2xl shadow-black">
            <h2 className="text-2xl font-black">Confirm DEMO Trade</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Metric label="Symbol" value={form.symbol} compact />
              <Metric label="Direction" value={form.action} compact />
              <Metric label="Lot" value="0.01" compact />
              <Metric label="Entry" value={marketNumber(entryPrice)} compact />
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

function MarketCard({ title, tick }: { title: string; tick: ApiRecord | null }) {
  const label = marketLabel(tick);
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
      {feedUnavailable ? <p className="mt-3 text-sm font-bold text-slate-400">Market feed unavailable.</p> : null}
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
