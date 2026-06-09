"use client";

import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AutoRefreshControl } from "./AutoRefreshControl";
import { StatusBadge } from "./StatusBadge";
import type { DashboardStatus, Mt5MarketOverviewData, Mt5SymbolOverviewData, PortfolioAccountSummaryData, PortfolioExposureSummaryData, PortfolioOverviewData } from "@/lib/dashboard-api";
import { formatRelativeTime, readNumber, readText } from "@/lib/dashboard-formatters";

type TraderBundle = {
  status: DashboardStatus | null;
  portfolioOverview: PortfolioOverviewData | null;
  portfolioAccounts: PortfolioAccountSummaryData[];
  portfolioExposure: PortfolioExposureSummaryData | null;
  portfolioPnlSummary: Record<string, unknown> | null;
  recentTrades: Array<Record<string, unknown>>;
  tradePerformance: Record<string, unknown> | null;
  tradeRiskAnalytics: Record<string, unknown> | null;
  mt5MarketOverview: Mt5MarketOverviewData | null;
  demoPositionMonitor: Record<string, unknown> | null;
  persistentTrades: Array<Record<string, unknown>>;
  outcomeSummary: Record<string, unknown> | null;
  signals: Array<Record<string, unknown>>;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

const emptyTraderBundle: TraderBundle = {
  status: null,
  portfolioOverview: null,
  portfolioAccounts: [],
  portfolioExposure: null,
  portfolioPnlSummary: null,
  recentTrades: [],
  tradePerformance: null,
  tradeRiskAnalytics: null,
  mt5MarketOverview: null,
  demoPositionMonitor: null,
  persistentTrades: [],
  outcomeSummary: null,
  signals: [],
};

function buildApiUrl(endpoint: string): string {
  const url = new URL(endpoint, API_BASE_URL);
  url.searchParams.set("_ts", String(Date.now()));
  return url.toString();
}

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(buildApiUrl(endpoint), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${endpoint} returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function useTraderDashboardData(refreshIntervalMs = 10000) {
  const [bundle, setBundle] = useState<TraderBundle>(emptyTraderBundle);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const requestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setLoading(true);

    const requests = {
      status: fetchJson<DashboardStatus>("/dashboard/status"),
      portfolioOverview: fetchJson<PortfolioOverviewData>("/portfolio/overview"),
      portfolioAccounts: fetchJson<PortfolioAccountSummaryData[]>("/portfolio/accounts"),
      portfolioExposure: fetchJson<PortfolioExposureSummaryData>("/portfolio/exposure"),
      portfolioPnlSummary: fetchJson<Record<string, unknown>>("/portfolio/pnl-summary"),
      recentTrades: fetchJson<Array<Record<string, unknown>>>("/trade-journal/recent?limit=8"),
      tradePerformance: fetchJson<Record<string, unknown>>("/trade-journal/overall-performance"),
      tradeRiskAnalytics: fetchJson<Record<string, unknown>>("/trade-journal/risk-analytics"),
      mt5MarketOverview: fetchJson<Mt5MarketOverviewData>("/mt5-demo/overview"),
      demoPositionMonitor: fetchJson<Record<string, unknown>>("/mt5-demo/position-monitor/open"),
      persistentTrades: fetchJson<Array<Record<string, unknown>>>("/trade-journal/persistence/recent?limit=5"),
      outcomeSummary: fetchJson<Record<string, unknown>>("/analytics/outcomes/summary"),
      signals: fetchJson<Array<Record<string, unknown>>>("/webhooks/events?limit=4"),
    };

    const entries = await Promise.allSettled(Object.entries(requests).map(async ([key, promise]) => [key, await promise] as const));
    setBundle((previous) => {
      const next = { ...previous };
      for (const entry of entries) {
        if (entry.status !== "fulfilled") continue;
        const [key, value] = entry.value;
        if (Array.isArray(value) && value.length === 0) {
          next[key as keyof TraderBundle] = value as never;
        } else {
          next[key as keyof TraderBundle] = value as never;
        }
      }
      return next;
    });
    setLastUpdated(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    setLoading(false);
    requestInFlight.current = false;
  }, []);

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(initialRefresh);
  }, [refresh]);

  useEffect(() => {
    if (isPaused) return;
    const interval = window.setInterval(() => void refresh(), refreshIntervalMs);
    return () => window.clearInterval(interval);
  }, [isPaused, refresh, refreshIntervalMs]);

  return {
    bundle,
    loading,
    isPaused,
    lastUpdated,
    refresh,
    togglePause: () => setIsPaused((current) => !current),
  };
}

function money(value: number | undefined, maximumFractionDigits = 0): string {
  return `$${Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits })}`;
}

function signedMoney(value: number | undefined): string {
  const amount = Number(value ?? 0);
  const prefix = amount > 0 ? "+" : "";
  return `${prefix}${money(amount, 2)}`;
}

function todayPnl(trades: Array<Record<string, unknown>>, fallback: number): number {
  const today = new Date().toDateString();
  const total = trades.reduce((sum, trade) => {
    const timestamp = readText(trade, ["timestamp"], "");
    if (!timestamp || new Date(timestamp).toDateString() !== today) {
      return sum;
    }
    return sum + readNumber(trade, ["pnl"], 0);
  }, 0);
  return trades.length ? total : fallback;
}

function marketValue(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "Unavailable";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function freshnessTone(value: string | undefined): "good" | "info" | "warning" | "danger" | "muted" {
  if (value === "READY") return "good";
  if (value === "STALE") return "warning";
  if (value === "OFFLINE") return "danger";
  return "muted";
}

function symbolOverview(overview: Mt5MarketOverviewData | null, symbol: string): Mt5SymbolOverviewData | null {
  return overview?.symbols?.[symbol] ?? null;
}

function isLegacyFakeTrade(trade: Record<string, unknown>): boolean {
  const strategyName = readText(trade, ["strategy_name"], "").toUpperCase();
  const notes = readText(trade, ["notes"], "").toUpperCase();
  return strategyName.includes("DAY14_TEST_STRATEGY") || notes.includes("SWAGGER-CREATED ANALYTICS-ONLY VERIFICATION ENTRY");
}

function statusTone(value: string | boolean | null | undefined): "good" | "info" | "warning" | "danger" | "muted" {
  const text = String(value ?? "").toUpperCase();
  if (text.includes("READY") || text.includes("HEALTHY") || text.includes("CONNECTED") || value === true) return "good";
  if (text.includes("PENDING") || text.includes("REVIEW") || text.includes("CONDITIONAL")) return "warning";
  if (text.includes("DISABLED") || text.includes("BLOCK") || text.includes("LOSS")) return "warning";
  if (text.includes("FAIL") || text.includes("ERROR")) return "danger";
  return "info";
}

export function DashboardShell({
  executiveDashboardSection,
  analyticsSection,
  accountAnalyticsSection,
  platformFoundationSection,
  strategyIntelligenceSection,
  tradeJournalSection,
  reportsSection,
}: {
  executiveDashboardSection?: React.ReactNode;
  analyticsSection?: React.ReactNode;
  accountAnalyticsSection?: React.ReactNode;
  platformFoundationSection?: React.ReactNode;
  strategyIntelligenceSection?: React.ReactNode;
  tradeJournalSection?: React.ReactNode;
  reportsSection?: React.ReactNode;
}) {
  const { bundle, loading, isPaused, lastUpdated, refresh, togglePause } = useTraderDashboardData(10000);
  const exposure = bundle.portfolioExposure ?? bundle.portfolioOverview?.exposure_summary ?? null;
  const pnl = bundle.portfolioPnlSummary ?? bundle.portfolioOverview?.pnl_summary ?? null;
  const accounts = bundle.portfolioAccounts.length ? bundle.portfolioAccounts : bundle.portfolioOverview?.accounts ?? [];
  const recentTrades = bundle.recentTrades
    .filter((trade) => readText(trade, ["outcome"], "OPEN").toUpperCase() !== "OPEN")
    .filter((trade) => !isLegacyFakeTrade(trade))
    .slice(0, 5);
  const hasCompletedDemoTrades = recentTrades.length > 0;
  const signals = bundle.signals.slice(0, 4);

  const balance = exposure?.total_simulated_balance ?? accounts.reduce((sum, account) => sum + account.balance, 0);
  const equity = exposure?.total_simulated_equity ?? accounts.reduce((sum, account) => sum + account.equity, 0);
  const dailyPnl = hasCompletedDemoTrades ? todayPnl(recentTrades, readNumber(pnl, ["net_pnl"], 0)) : 0;
  const connectionStatus = bundle.status?.dashboard_ready ? "Connected" : loading ? "Connecting" : "Review";
  const botStatus = bundle.status?.system_status ?? "Checking";
  const risk = bundle.tradeRiskAnalytics;
  const eurusdMarket = symbolOverview(bundle.mt5MarketOverview, "EURUSD");
  const xauusdMarket = symbolOverview(bundle.mt5MarketOverview, "XAUUSD");
  const demoPositions = Array.isArray(bundle.demoPositionMonitor?.positions) ? (bundle.demoPositionMonitor.positions as Array<Record<string, unknown>>) : [];
  const openDemoPosition = demoPositions[0] ?? null;
  const closedDemoTrade = bundle.persistentTrades.find((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED") ?? null;
  const outcomeSummary = bundle.outcomeSummary;
  const closedOutcomeCount = readNumber(outcomeSummary, ["total_closed_trades"], 0);
  const marketCards = [
    {
      label: "EURUSD Demo Bid",
      value: marketValue(eurusdMarket?.bid),
      detail: `Spread ${marketValue(eurusdMarket?.spread)} / freshness ${eurusdMarket?.freshness ?? "OFFLINE"}`,
      tone: freshnessTone(eurusdMarket?.freshness),
    },
    {
      label: "XAUUSD Demo Bid",
      value: marketValue(xauusdMarket?.bid, 2),
      detail: xauusdMarket?.bid
        ? `Spread ${marketValue(xauusdMarket.spread, 2)} / freshness ${xauusdMarket.freshness}`
        : `Availability ${xauusdMarket?.availability_status ?? "UNAVAILABLE"} / ${xauusdMarket?.tick_status ?? "NO_TICK"}`,
      tone: freshnessTone(xauusdMarket?.freshness),
    },
    {
      label: "Market Freshness",
      value: bundle.mt5MarketOverview?.status ?? "OFFLINE",
      detail: `MT5 demo source / last update ${formatRelativeTime(bundle.mt5MarketOverview?.last_update ?? "")}`,
      tone: freshnessTone(bundle.mt5MarketOverview?.status),
    },
  ];

  const topCards = useMemo(
    () => [
      { label: "Simulated Balance", value: money(balance), detail: "Derived from /portfolio/exposure simulated account summaries", tone: "info" as const },
      { label: "Simulated Equity", value: money(equity), detail: "Derived from /portfolio/exposure simulated account summaries", tone: "good" as const },
      { label: "Demo P&L", value: signedMoney(dailyPnl), detail: "Derived from completed demo journal records only", tone: dailyPnl >= 0 ? ("good" as const) : ("danger" as const) },
      { label: "Open Demo Positions", value: String(demoPositions.length), detail: "Read-only MT5 DEMO position monitor", tone: demoPositions.length ? ("info" as const) : ("muted" as const) },
      { label: "AI Signals", value: String(signals.length), detail: "Demo analysis events from /webhooks/events", tone: "info" as const },
    ],
    [balance, dailyPnl, equity, signals.length],
  );

  return (
    <main className="min-h-screen overflow-hidden bg-[#07111f] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.2),transparent_32rem),radial-gradient(circle_at_80%_8%,rgba(20,184,166,0.14),transparent_28rem),linear-gradient(135deg,#06101d,#0f172a_54%,#0b1120)]" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
        <header className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(8,47,73,0.58),rgba(15,23,42,0.82))] p-5 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[0.68rem] font-bold uppercase tracking-[0.32em] text-cyan-200/75">Trader Dashboard</p>
              <h1 className="mt-2 max-w-4xl text-3xl font-black tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl">
                Portfolio & AI Trading
              </h1>
              <p className="mt-2 text-sm text-slate-300 sm:text-base">Simulated balances, demo trade records, analysis signals, derived risk, and connection status.</p>
            </div>
            <AutoRefreshControl
              isPaused={isPaused}
              lastUpdated={lastUpdated}
              loading={loading}
              onManualRefresh={() => void refresh()}
              onTogglePause={togglePause}
            />
          </div>
        </header>

        <section className="grid gap-3 rounded-3xl border border-emerald-300/20 bg-[linear-gradient(135deg,rgba(16,185,129,0.14),rgba(15,23,42,0.62))] p-3 shadow-2xl shadow-emerald-950/10 backdrop-blur-xl md:grid-cols-3">
          {[
            ["Bot Status", botStatus.replaceAll("_", " ")],
            ["Live Trading", bundle.status?.live_execution_enabled ? "Enabled" : "Disabled"],
            ["Connection", connectionStatus],
          ].map(([label, value]) => (
            <div className="rounded-2xl border border-emerald-300/15 bg-slate-950/35 px-4 py-3" key={label}>
              <p className="text-xs uppercase tracking-[0.22em] text-emerald-100/70">{label}</p>
              <strong className="mt-2 block text-lg text-emerald-100">{value}</strong>
            </div>
          ))}
        </section>

        <section className="grid gap-3 md:grid-cols-3">
          {marketCards.map((card) => (
            <article className="min-h-28 rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.06] p-4 shadow-2xl shadow-black/20 backdrop-blur-xl" key={card.label}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="break-words text-[0.68rem] uppercase tracking-[0.18em] text-cyan-100/70">{card.label}</p>
                <StatusBadge label={card.tone === "good" ? "Fresh" : card.tone === "warning" ? "Stale" : card.tone === "danger" ? "Offline" : "Review"} tone={card.tone} />
              </div>
              <strong className="mt-3 block break-words text-2xl font-black leading-tight text-white">{card.value}</strong>
              <p className="mt-2 break-words text-xs leading-5 text-cyan-50/70">{card.detail}</p>
            </article>
          ))}
        </section>

        <section className="grid gap-3 md:grid-cols-5">
          {topCards.map((card) => (
            <article className="min-h-32 rounded-3xl border border-white/10 bg-slate-950/60 p-4 shadow-2xl shadow-black/20 backdrop-blur-xl" key={card.label}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="break-words text-[0.68rem] uppercase tracking-[0.18em] text-slate-500">{card.label}</p>
                <StatusBadge label={card.tone === "good" ? "Demo" : card.tone === "danger" ? "Review" : card.tone === "muted" ? "Hidden" : "Info"} tone={card.tone} />
              </div>
              <strong className="mt-3 block break-words text-2xl font-black leading-tight text-white">{card.value}</strong>
              <p className="mt-2 break-words text-xs leading-5 text-slate-400">{card.detail}</p>
            </article>
          ))}
        </section>

        {executiveDashboardSection}
        {platformFoundationSection}
        {analyticsSection}
        <section className="rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[0.68rem] uppercase tracking-[0.22em] text-emerald-100/70">DEMO Performance</p>
              <h2 className="mt-1 text-xl font-bold text-white">Trade Outcome Intelligence</h2>
            </div>
            <StatusBadge label={closedOutcomeCount ? "Closed Trades" : "Empty"} tone={closedOutcomeCount ? "good" : "muted"} />
          </div>
          {closedOutcomeCount ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                ["Total Closed Trades", readText(outcomeSummary, ["total_closed_trades"], "0")],
                ["Win Rate", `${readText(outcomeSummary, ["win_rate"], "0")}%`],
                ["Net PnL", signedMoney(readNumber(outcomeSummary, ["net_pnl"], 0))],
                ["Avg RR", readText(outcomeSummary, ["avg_rr"], "0")],
                ["Best Trade", signedMoney(readNumber(outcomeSummary?.best_trade as Record<string, unknown>, ["realized_pnl"], 0))],
                ["Worst Trade", signedMoney(readNumber(outcomeSummary?.worst_trade as Record<string, unknown>, ["realized_pnl"], 0))],
                ["Best Symbol", readText(outcomeSummary, ["best_symbol"], "n/a")],
                ["Worst Symbol", readText(outcomeSummary, ["worst_symbol"], "n/a")],
              ].map(([label, value]) => (
                <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3" key={label}>
                  <p className="text-[0.65rem] uppercase tracking-[0.14em] text-slate-500">{label}</p>
                  <strong className="mt-1 block break-words text-lg text-white">{value}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-emerald-200/20 bg-slate-950/35 p-4 text-sm leading-6 text-emerald-50/80">
              <strong className="block text-white">No closed demo trades yet.</strong>
              DEMO performance attribution will populate after MT5 demo trades close and are synchronized.
            </div>
          )}
        </section>
        {strategyIntelligenceSection}
        {accountAnalyticsSection}
        {tradeJournalSection}
        {reportsSection}

        <section className="grid gap-4 xl:grid-cols-[1.25fr_0.85fr]">
          <section className="min-w-0 rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">DEMO MT5 Monitor</p>
                <h2 className="mt-1 text-xl font-bold text-white">Open Demo MT5 Position</h2>
              </div>
              <StatusBadge label={openDemoPosition ? "DEMO OPEN" : closedDemoTrade ? "DEMO CLOSED" : "DEMO EMPTY"} tone={openDemoPosition ? "info" : closedDemoTrade ? "good" : "muted"} />
            </div>

            {openDemoPosition ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  ["Ticket", readText(openDemoPosition, ["ticket"], "")],
                  ["Symbol", readText(openDemoPosition, ["symbol"], "")],
                  ["Side", readText(openDemoPosition, ["side"], "")],
                  ["Lot", readText(openDemoPosition, ["lot"], "")],
                  ["Entry", marketValue(readNumber(openDemoPosition, ["entry_price"], 0))],
                  ["Current Price", marketValue(readNumber(openDemoPosition, ["current_price"], 0))],
                  ["SL", marketValue(readNumber(openDemoPosition, ["stop_loss"], 0))],
                  ["TP", marketValue(readNumber(openDemoPosition, ["take_profit"], 0))],
                  ["Floating P&L", signedMoney(readNumber(openDemoPosition, ["floating_pnl"], 0))],
                  ["Lifecycle Status", readText(openDemoPosition, ["lifecycle_status"], "OPEN")],
                  ["Journal Status", readText(openDemoPosition, ["journal_status"], "UNKNOWN")],
                ].map(([label, value]) => (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={label}>
                    <p className="text-[0.65rem] uppercase tracking-[0.14em] text-slate-500">{label}</p>
                    <strong className="mt-1 block break-words text-sm text-white">{value}</strong>
                  </div>
                ))}
                <p className="sm:col-span-2 text-xs leading-5 text-slate-400">
                  DEMO account only. Source: /mt5-demo/position-monitor/open and persistent trade journal.
                </p>
              </div>
            ) : closedDemoTrade ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {[
                  ["Ticket", readText(closedDemoTrade, ["mt5_ticket"], "")],
                  ["Symbol", readText(closedDemoTrade, ["symbol"], "")],
                  ["Side", readText(closedDemoTrade, ["side"], "")],
                  ["Lot", readText(closedDemoTrade, ["lot"], "")],
                  ["Realized P&L", signedMoney(readNumber(closedDemoTrade, ["net_pnl", "profit_loss"], 0))],
                  ["Result", readText(closedDemoTrade, ["result"], "CLOSED")],
                  ["Close Time", readText(closedDemoTrade, ["closed_at"], "")],
                  ["Exit Reason", readText(closedDemoTrade, ["exit_reason"], "UNKNOWN")],
                ].map(([label, value]) => (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={label}>
                    <p className="text-[0.65rem] uppercase tracking-[0.14em] text-slate-500">{label}</p>
                    <strong className="mt-1 block break-words text-sm text-white">{value}</strong>
                  </div>
                ))}
                <p className="sm:col-span-2 text-xs leading-5 text-slate-400">
                  DEMO account only. Closed trade details are from persistent journal records synchronized from MT5 history.
                </p>
              </div>
            ) : (
              <div className="mt-4 rounded-2xl border border-dashed border-slate-700 bg-white/[0.03] p-5">
                <strong className="text-sm text-slate-100">No open MT5 demo positions.</strong>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">This card uses read-only MT5 DEMO position data and journal matching. No live broker execution is enabled.</p>
              </div>
            )}
          </section>

          <section className="min-w-0 rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[0.68rem] uppercase tracking-[0.22em] text-cyan-100/70">AI Signals</p>
                <h2 className="mt-1 text-xl font-bold text-white">What The AI Is Watching</h2>
              </div>
              <StatusBadge label={signals.length ? "Active" : "Waiting"} tone={signals.length ? "info" : "muted"} />
            </div>
            <div className="mt-4 grid gap-3">
              {signals.length ? (
                signals.map((signal, index) => (
                  <article className="rounded-2xl border border-white/10 bg-slate-950/35 p-4" key={`${readText(signal, ["event_id"], String(index))}-${index}`}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <strong className="break-words text-sm text-white">{readText(signal, ["symbol"], "Market")}</strong>
                      <StatusBadge label={readText(signal, ["action"], "Alert")} tone="info" />
                    </div>
                    <p className="mt-2 break-words text-xs leading-5 text-slate-400">
                      {readText(signal, ["strategy"], "AI setup")} / {readText(signal, ["timeframe"], "M15")} / confidence {readText(signal, ["confidence"], "n/a")}
                    </p>
                    <p className="mt-2 text-xs text-slate-500">{formatRelativeTime(readText(signal, ["timestamp"], ""))}</p>
                  </article>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-700 bg-white/[0.03] p-4 text-sm text-slate-400">
                  No new AI trade idea yet.
                </div>
              )}
            </div>
          </section>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Demo Trades</p>
            <h2 className="mt-1 text-xl font-bold text-white">Trade History</h2>
            <div className="mt-4 space-y-3">
              {hasCompletedDemoTrades ? recentTrades.map((trade, index) => (
                <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={`${readText(trade, ["journal_id"], String(index))}-${index}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <strong className="text-sm text-white">{readText(trade, ["symbol"], "Trade")} {readText(trade, ["side"], "")}</strong>
                    <StatusBadge label={readText(trade, ["outcome"], "Open")} tone={statusTone(readText(trade, ["outcome"], ""))} />
                  </div>
                  <p className="mt-2 text-xs text-slate-400">{signedMoney(readNumber(trade, ["pnl"], 0))} / RR {readText(trade, ["rr"], "0")} / {formatRelativeTime(readText(trade, ["timestamp"], ""))}</p>
                </div>
              )) : (
                <div className="rounded-2xl border border-dashed border-slate-700 bg-white/[0.03] p-4 text-sm leading-6 text-slate-400">
                  <strong className="block text-slate-200">No completed demo trades yet.</strong>
                  Performance will populate after real demo execution records are available.
                </div>
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-[0.68rem] uppercase tracking-[0.22em] text-emerald-100/70">Performance</p>
            <h2 className="mt-1 text-xl font-bold text-white">Demo Performance</h2>
            {hasCompletedDemoTrades ? (
              <div className="mt-4 grid grid-cols-2 gap-3">
                {[
                  ["Trades", readText(bundle.tradePerformance, ["total_trades"], "0")],
                  ["Win Rate", `${readText(bundle.tradePerformance, ["win_rate"], "0")}%`],
                  ["Net P&L", signedMoney(readNumber(bundle.tradePerformance, ["net_profit"], dailyPnl))],
                  ["Best Trade", signedMoney(readNumber(bundle.tradePerformance, ["best_trade"], 0))],
                ].map(([label, value]) => (
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3" key={label}>
                    <p className="text-[0.65rem] uppercase tracking-[0.14em] text-slate-500">{label}</p>
                    <strong className="mt-1 block break-words text-lg text-white">{value}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-2xl border border-dashed border-emerald-200/20 bg-slate-950/35 p-4 text-sm leading-6 text-emerald-50/80">
                <strong className="block text-white">No completed demo trades yet.</strong>
                Performance will populate after real demo execution records are available.
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Risk & Safety</p>
            <h2 className="mt-1 text-xl font-bold text-white">Protection Status</h2>
            <div className="mt-4 grid gap-3">
              {[
                ["Risk Level", readText(risk, ["active_risk_level"], "LOW"), statusTone(readText(risk, ["active_risk_level"], "LOW"))],
                ["Demo Drawdown", `${readText(risk, ["daily_drawdown_percent"], "0")}%`, "good"],
                ["Demo Exposure", `${readText(risk, ["current_exposure_percent"], "0")}%`, "good"],
                ["Live Trading", bundle.status?.live_execution_enabled ? "Enabled" : "Disabled", "warning"],
              ].map(([label, value, tone]) => (
                <div className="flex min-w-0 items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={label}>
                  <span className="break-words text-sm font-bold text-slate-200">{label}</span>
                  <StatusBadge label={String(value)} tone={tone as "good" | "info" | "warning" | "danger" | "muted"} />
                </div>
              ))}
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
