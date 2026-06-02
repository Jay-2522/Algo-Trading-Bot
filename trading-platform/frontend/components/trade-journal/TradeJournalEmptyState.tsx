export function TradeJournalEmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-cyan-200/25 bg-cyan-300/[0.055] p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">Execution Journal Ready</p>
      <h3 className="mt-2 text-lg font-black text-white">No demo execution history yet</h3>
      <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
        No demo execution history yet. Once strategy signals pass risk checks and demo execution is approved, the journal will show the full lifecycle here.
      </p>
    </div>
  );
}
