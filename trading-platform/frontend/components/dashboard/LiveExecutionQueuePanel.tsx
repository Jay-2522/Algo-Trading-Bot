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
    <section className="rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Live Execution Queue</p>
          <h2 className="mt-1 text-lg font-bold text-white">Queue & Lifecycle</h2>
        </div>
        <StatusBadge label="Disabled" tone="good" />
      </div>
      <div className="mt-4 grid grid-cols-4 gap-2 text-center">
        {[
          ["Total", total],
          ["Queued", queued],
          ["Fills", fills],
          ["Rejects", rejections],
        ].map(([label, value]) => (
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3" key={label}>
            <strong className="block text-xl text-white">{value}</strong>
            <span className="text-[0.68rem] text-slate-500">{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
