import type { TradeJournalEntry } from "@/lib/tradeJournalApi";

import { ExecutionStatusBadge } from "./ExecutionStatusBadge";
import { TradeJournalEmptyState } from "./TradeJournalEmptyState";

function money(value: number | null): string {
  return value === null ? "Not available" : `$${Number(value || 0).toFixed(2)}`;
}

function timeLabel(value: string | null): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

export function TradeHistoryTable({
  entries,
  onSelectTrade,
}: {
  entries: TradeJournalEntry[];
  onSelectTrade: (trade: TradeJournalEntry) => void;
}) {
  if (!entries.length) {
    return <TradeJournalEmptyState />;
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/40">
      <div className="grid gap-2 border-b border-white/10 bg-white/[0.04] p-3 text-[0.65rem] font-black uppercase tracking-[0.12em] text-slate-500 md:grid-cols-[1.1fr_0.7fr_0.65fr_0.8fr_1fr_1fr_0.75fr_1.1fr_0.6fr]">
        <span>Time</span>
        <span>Symbol</span>
        <span>Action</span>
        <span>Confidence</span>
        <span>Status</span>
        <span>Demo Result</span>
        <span>P&L</span>
        <span>Risk Notes</span>
        <span>Details</span>
      </div>
      {entries.map((entry) => (
        <div
          className="grid gap-2 border-b border-white/10 p-3 text-sm last:border-b-0 md:grid-cols-[1.1fr_0.7fr_0.65fr_0.8fr_1fr_1fr_0.75fr_1.1fr_0.6fr]"
          key={entry.trade_id}
        >
          <span className="break-words text-slate-300">{timeLabel(entry.time)}</span>
          <strong className="break-words text-white">{entry.symbol}</strong>
          <span className="break-words text-cyan-100">{entry.action}</span>
          <span className="break-words text-slate-300">{Number(entry.confidence || 0).toFixed(2)}</span>
          <ExecutionStatusBadge status={entry.status} />
          <span className="break-words text-slate-300">{entry.demo_result || "Not available"}</span>
          <span className="break-words text-slate-300">{money(entry.pnl)}</span>
          <span className="break-words text-slate-400">{entry.risk_notes.length ? entry.risk_notes.join(", ") : "Not available"}</span>
          <button
            className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.1em] text-cyan-100 hover:bg-cyan-300/[0.16]"
            onClick={() => onSelectTrade(entry)}
            type="button"
          >
            View
          </button>
        </div>
      ))}
    </section>
  );
}
