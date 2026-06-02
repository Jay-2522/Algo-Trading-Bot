import type { TradeJournalEntry } from "@/lib/tradeJournalApi";

import { ExecutionStatusBadge } from "./ExecutionStatusBadge";

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3">
      <p className="text-[0.62rem] uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <strong className="mt-1 block break-words text-sm text-slate-100">{value || "Not available"}</strong>
    </div>
  );
}

export function TradeDetailDrawer({ trade, onClose }: { trade: TradeJournalEntry | null; onClose: () => void }) {
  if (!trade) return null;
  const identifiers: Array<[string, string | number | null | undefined]> = [
    ["signal_id", trade.signal_id],
    ["decision_id", trade.decision_id],
    ["queue_preview_id", trade.queue_preview_id],
    ["approval_id", trade.approval_id],
    ["candidate_id", trade.candidate_id],
    ["final_execution_id", trade.final_execution_id],
    ["copy_batch_id", trade.copy_batch_id],
    ["confirmation_id", trade.confirmation_id],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/55 p-4 backdrop-blur-sm md:items-center">
      <section className="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl border border-cyan-300/20 bg-slate-950 p-5 shadow-2xl shadow-black/40">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">Read-Only Trade Detail</p>
            <h3 className="mt-2 text-2xl font-black text-white">{trade.symbol} {trade.action}</h3>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ExecutionStatusBadge status={trade.status} />
            <button
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-slate-200 hover:border-cyan-300/25"
              onClick={onClose}
              type="button"
            >
              Close
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {identifiers.map(([label, value]) => (
            <Field key={label} label={label} value={value} />
          ))}
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-500">Rejection Reasons</p>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              {trade.rejection_reasons?.length ? trade.rejection_reasons.join(", ") : "Not available"}
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-500">Warnings</p>
            <p className="mt-2 text-sm leading-6 text-slate-300">{trade.warnings?.length ? trade.warnings.join(", ") : "Not available"}</p>
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/35 p-4">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-slate-500">Safety Flags</p>
          <div className="mt-3 grid gap-2 text-xs text-slate-300 sm:grid-cols-2 xl:grid-cols-4">
            <div>simulation_only = {String(trade.simulation_only ?? true)}</div>
            <div>demo_execution = {String(trade.demo_execution ?? true)}</div>
            <div>live_execution_enabled = {String(trade.live_execution_enabled ?? false)}</div>
            <div>broker_execution_enabled = {String(trade.broker_execution_enabled ?? false)}</div>
          </div>
        </div>
      </section>
    </div>
  );
}
