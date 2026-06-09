"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { fetchClientTradeHistory, type ApiRecord } from "@/lib/clientOperatingDashboardApi";
import { readNumber, readText } from "@/lib/dashboard-formatters";

const PAGE_SIZE = 10;

function money(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Unavailable";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function marketNumber(value: number | null | undefined, digits = 5): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "Unavailable";
  return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
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

function closeTimestamp(trade: ApiRecord): number {
  const value = readText(trade, ["closed_at", "close_time"], "");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

export function TradeHistoryPage() {
  const [trades, setTrades] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [symbolFilter, setSymbolFilter] = useState<"ALL" | "EURUSD" | "XAUUSD" | "NIFTY50">("ALL");
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchClientTradeHistory(500);
        if (!active) return;
        setTrades(result.filter((trade) => readText(trade, ["status"], "").toUpperCase() === "CLOSED"));
      } catch (loadError) {
        if (!active) return;
        setError(loadError instanceof Error ? loadError.message : "Trade history unavailable.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  const filteredTrades = useMemo(() => {
    const normalizedQuery = query.trim().toUpperCase();
    const scoped = symbolFilter === "ALL" ? trades : trades.filter((trade) => readText(trade, ["symbol"], "").toUpperCase() === symbolFilter);
    const matching = normalizedQuery ? scoped.filter((trade) => readText(trade, ["symbol"], "").toUpperCase().includes(normalizedQuery)) : scoped;
    return [...matching].sort((left, right) => {
      const difference = closeTimestamp(right) - closeTimestamp(left);
      return sortOrder === "newest" ? difference : -difference;
    });
  }, [query, sortOrder, symbolFilter, trades]);

  const totalPages = Math.max(1, Math.ceil(filteredTrades.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageTrades = filteredTrades.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [query, sortOrder, symbolFilter]);

  return (
    <main className="min-h-screen bg-[#050816] text-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5 shadow-2xl shadow-black/30">
          <Link className="text-sm font-bold text-blue-200 hover:text-blue-100" href="/dashboard">
            Back to Dashboard
          </Link>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.24em] text-blue-300">Trade History</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Completed Demo Trades</h1>
              <p className="mt-2 text-sm text-slate-400">All completed trades recorded in the persistent journal.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Search by symbol
                <input className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" placeholder="EURUSD" value={query} onChange={(event) => setQuery(event.target.value)} />
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Filter
                <select className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" value={symbolFilter} onChange={(event) => setSymbolFilter(event.target.value as "ALL" | "EURUSD" | "XAUUSD" | "NIFTY50")}>
                  <option value="ALL">All scoped symbols</option>
                  <option value="EURUSD">EURUSD</option>
                  <option value="XAUUSD">XAUUSD</option>
                  <option value="NIFTY50">NIFTY50</option>
                </select>
              </label>
              <label className="grid gap-2 text-sm font-bold text-slate-300">
                Sort by date
                <select className="rounded-xl border border-slate-700 bg-[#0F172A] px-3 py-3 text-white" value={sortOrder} onChange={(event) => setSortOrder(event.target.value as "newest" | "oldest")}>
                  <option value="newest">Newest first</option>
                  <option value="oldest">Oldest first</option>
                </select>
              </label>
            </div>
          </div>
        </header>

        <section className="rounded-2xl border border-slate-800 bg-[#0B1220] p-5">
          {loading ? <EmptyState text="Loading completed trades." /> : null}
          {error ? <EmptyState text="Market feed unavailable." /> : null}
          {!loading && !error && pageTrades.length === 0 ? <EmptyState text="Completed trades will appear here." /> : null}
          {!loading && !error && pageTrades.length > 0 ? <HistoryTable trades={pageTrades} /> : null}
          {!loading && !error && filteredTrades.length > 0 ? (
            <div className="mt-4 flex flex-col gap-3 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
              <span>
                Page {safePage} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 font-bold text-slate-100 disabled:cursor-not-allowed disabled:opacity-50" disabled={safePage === 1} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">
                  Previous
                </button>
                <button className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 font-bold text-slate-100 disabled:cursor-not-allowed disabled:opacity-50" disabled={safePage === totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} type="button">
                  Next
                </button>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}

function HistoryTable({ trades }: { trades: ApiRecord[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[920px] border-separate border-spacing-y-2 text-left text-sm">
        <thead className="text-xs uppercase tracking-[0.16em] text-slate-400">
          <tr>
            {["Date", "Symbol", "Direction", "Lot", "Entry", "Exit", "P&L", "Result", "Duration"].map((item, index) => (
              <th className={`px-3 py-2 ${index >= 3 && index !== 7 ? "text-right" : ""}`} key={item}>
                {item}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, index) => {
            const pnl = readNumber(trade, ["net_pnl", "profit_loss", "realized_pnl"], 0);
            return (
              <tr className="bg-[#0F172A]" key={`${readText(trade, ["trade_id", "mt5_ticket"], String(index))}-${index}`}>
                <td className="whitespace-pre-line rounded-l-xl px-3 py-3 font-bold">{formatTradeTime(readText(trade, ["closed_at", "close_time"], ""))}</td>
                <td className="px-3 py-3">{readText(trade, ["symbol"], "Unavailable")}</td>
                <td className="px-3 py-3">{readText(trade, ["side"], "Unavailable")}</td>
                <td className="px-3 py-3 text-right">{readText(trade, ["lot"], "Unavailable")}</td>
                <td className="px-3 py-3 text-right">{marketNumber(readNumber(trade, ["entry_price"], Number.NaN))}</td>
                <td className="px-3 py-3 text-right">{marketNumber(readNumber(trade, ["close_price"], Number.NaN))}</td>
                <td className={`px-3 py-3 text-right font-bold ${pnlClass(pnl)}`}>{money(pnl)}</td>
                <td className="px-3 py-3">{readText(trade, ["result"], "Unavailable")}</td>
                <td className="rounded-r-xl px-3 py-3 text-right">{formatDuration(trade.duration_minutes)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed border-slate-700 bg-[#0F172A] p-5 text-sm font-bold text-slate-400">{text}</div>;
}
