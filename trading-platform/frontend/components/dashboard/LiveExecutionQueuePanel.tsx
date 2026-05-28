import { StatusBadge } from "./StatusBadge";

function readNumber(source: Record<string, unknown> | null, key: string): number {
  const value = source?.[key];
  return typeof value === "number" ? value : 0;
}

export function LiveExecutionQueuePanel({
  executionStatus,
  lifecycleStatus,
}: {
  executionStatus: Record<string, unknown> | null;
  lifecycleStatus: Record<string, unknown> | null;
}) {
  const queued = readNumber(executionStatus, "queued");
  const total = readNumber(executionStatus, "total_items");
  const fills = readNumber(lifecycleStatus, "simulated_fills");
  const rejections = readNumber(lifecycleStatus, "simulated_rejections");

  return (
    <section className="min-h-64 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Live Execution Queue</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">Queue & Lifecycle</h2>
        </div>
        <StatusBadge label="Disabled" tone="good" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 text-center sm:grid-cols-4 lg:grid-cols-2 2xl:grid-cols-4">
        {[
          ["Total", total],
          ["Queued", queued],
          ["Fills", fills],
          ["Rejects", rejections],
        ].map(([label, value]) => (
          <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3" key={label}>
            <strong className="block break-words text-xl leading-tight text-white">{value}</strong>
            <span className="break-words text-[0.68rem] leading-relaxed text-slate-500">{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
