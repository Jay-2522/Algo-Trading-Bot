export function ReportEmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-cyan-200/25 bg-cyan-300/[0.055] p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">Reports Ready</p>
      <h3 className="mt-2 text-lg font-black text-white">No reportable demo trades yet</h3>
      <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
        Reports will populate from real demo signals, risk checks, execution history, and copier events. No fake trades or P&L are generated.
      </p>
    </div>
  );
}
