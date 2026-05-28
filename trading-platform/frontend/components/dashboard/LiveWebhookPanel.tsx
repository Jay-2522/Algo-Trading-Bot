import { StatusBadge } from "./StatusBadge";

function numberValue(source: Record<string, unknown> | null, key: string): number {
  const value = source?.[key];
  return typeof value === "number" ? value : 0;
}

export function LiveWebhookPanel({
  webhookStatus,
  orchestrationStatus,
}: {
  webhookStatus: Record<string, unknown> | null;
  orchestrationStatus: Record<string, unknown> | null;
}) {
  const events = numberValue(webhookStatus, "events_stored");
  const decisions = numberValue(orchestrationStatus, "decisions_stored");

  return (
    <section className="min-h-64 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Live Webhook Panel</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">TradingView Intake</h2>
        </div>
        <StatusBadge label={String(webhookStatus?.status ?? "loading")} tone="info" />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="break-words text-xs leading-relaxed text-slate-500">Events stored</p>
          <strong className="mt-1 block break-words text-2xl leading-tight text-white">{events}</strong>
        </div>
        <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="break-words text-xs leading-relaxed text-slate-500">Orchestration decisions</p>
          <strong className="mt-1 block break-words text-2xl leading-tight text-white">{decisions}</strong>
        </div>
      </div>
    </section>
  );
}
