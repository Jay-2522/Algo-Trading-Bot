export function DashboardHeader({
  loading,
  lastUpdated,
  onRefresh,
}: {
  loading: boolean;
  lastUpdated: string | null;
  onRefresh: () => void;
}) {
  return (
    <header className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(135deg,rgba(15,23,42,0.92),rgba(8,47,73,0.58),rgba(15,23,42,0.82))] p-5 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-6 lg:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.32em] text-cyan-200/75">Client VPS Dashboard</p>
          <h1 className="mt-3 max-w-4xl text-3xl font-black tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl">
            AI Multi-Market Trading Bot
          </h1>
          <p className="mt-3 text-sm text-slate-300 sm:text-base">VPS Dashboard &amp; Simulation Control Center</p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center lg:flex-col lg:items-end">
          <button
            className="rounded-full border border-cyan-200/30 bg-cyan-200 px-5 py-2.5 text-sm font-black text-slate-950 shadow-lg shadow-cyan-950/20 transition hover:bg-cyan-100 disabled:cursor-wait disabled:opacity-70"
            disabled={loading}
            onClick={onRefresh}
            type="button"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">
            {lastUpdated ? `Updated ${lastUpdated}` : "Awaiting refresh"}
          </p>
        </div>
      </div>
    </header>
  );
}
