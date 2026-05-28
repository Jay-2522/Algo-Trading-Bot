import { StatusBadge } from "./StatusBadge";

export function AutoRefreshControl({
  loading,
  isPaused,
  lastUpdated,
  onManualRefresh,
  onTogglePause,
}: {
  loading: boolean;
  isPaused: boolean;
  lastUpdated: string | null;
  onManualRefresh: () => void;
  onTogglePause: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center lg:flex-col lg:items-end">
      <div className="flex flex-wrap gap-2">
        <button
          className="rounded-full border border-cyan-200/30 bg-cyan-200 px-5 py-2.5 text-sm font-black text-slate-950 shadow-lg shadow-cyan-950/20 transition hover:bg-cyan-100 disabled:cursor-wait disabled:opacity-70"
          disabled={loading}
          onClick={onManualRefresh}
          type="button"
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
        <button
          className="rounded-full border border-white/10 bg-slate-900/70 px-4 py-2.5 text-sm font-bold text-slate-100 transition hover:bg-slate-800"
          onClick={onTogglePause}
          type="button"
        >
          {isPaused ? "Resume Auto" : "Pause Auto"}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge label={isPaused ? "Paused" : "10s polling"} tone={isPaused ? "warning" : "good"} />
        <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">
          {lastUpdated ? `Updated ${lastUpdated}` : "Awaiting refresh"}
        </p>
      </div>
    </div>
  );
}
