"use client";

import { useCallback, useEffect, useState } from "react";

import { emptyExecutionHistory, fetchExecutionHistory, type ExecutionHistory, type TradeJournalEntry } from "@/lib/tradeJournalApi";

import { ExecutionTimeline } from "./ExecutionTimeline";
import { TradeDetailDrawer } from "./TradeDetailDrawer";
import { TradeHistoryTable } from "./TradeHistoryTable";
import { TradeJournalEmptyState } from "./TradeJournalEmptyState";

function SafetyBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-cyan-100">
      {label}
    </span>
  );
}

export function TradeJournalSection() {
  const [history, setHistory] = useState<ExecutionHistory>(emptyExecutionHistory);
  const [selectedTrade, setSelectedTrade] = useState<TradeJournalEntry | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setHistory(await fetchExecutionHistory());
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const entries = history.entries;
  const blocked = entries.filter((entry) => entry.status === "BLOCKED" || entry.status === "FAILED_SAFE" || entry.status === "DEMO_REJECTED").length;
  const filled = entries.filter((entry) => entry.status === "DEMO_FILLED" || entry.status === "COPIED").length;

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.78),rgba(8,47,73,0.38),rgba(15,23,42,0.72))] p-5 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.24em] text-cyan-100/70">Execution History</p>
          <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white sm:text-3xl">Trade Journal & Execution History</h2>
          <p className="mt-2 max-w-5xl break-words text-sm leading-7 text-slate-300">
            A transparent record of strategy signals, risk decisions, demo execution attempts, copier results, and confirmation status.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SafetyBadge label="DEMO ONLY" />
          <SafetyBadge label="LIVE DISABLED" />
          <SafetyBadge label="AUDIT READY" />
          <SafetyBadge label={loading ? "LOADING" : "READY"} />
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Journal Entries", entries.length],
          ["Demo Filled / Copied", filled],
          ["Blocked / Rejected", blocked],
          ["Confirmations", history.raw.confirmations.length],
        ].map(([label, value]) => (
          <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-4" key={label}>
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <strong className="mt-2 block text-2xl font-black text-white">{value}</strong>
          </div>
        ))}
      </div>

      <div className="mt-5 space-y-4">
        <TradeHistoryTable entries={entries} onSelectTrade={setSelectedTrade} />
        <ExecutionTimeline steps={history.timeline} />
        {!entries.length ? <TradeJournalEmptyState /> : null}
      </div>

      <TradeDetailDrawer trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </section>
  );
}
