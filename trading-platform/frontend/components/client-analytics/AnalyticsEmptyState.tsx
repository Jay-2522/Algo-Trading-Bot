export function AnalyticsEmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-cyan-200/25 bg-cyan-300/[0.055] p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">Analytics Ready</p>
      <h3 className="mt-2 text-lg font-black text-white">No completed demo trades yet</h3>
      <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">
        Analytics are ready. Data will populate after demo signals, risk checks, and execution events are generated.
      </p>
    </div>
  );
}
