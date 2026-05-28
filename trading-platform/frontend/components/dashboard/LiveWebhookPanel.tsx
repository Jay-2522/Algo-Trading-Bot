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
    <section className="rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Live Webhook Panel</p>
          <h2 className="mt-1 text-lg font-bold text-white">TradingView Intake</h2>
        </div>
        <StatusBadge label={String(webhookStatus?.status ?? "loading")} tone="info" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-xs text-slate-500">Events stored</p>
          <strong className="mt-1 block text-2xl text-white">{events}</strong>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-xs text-slate-500">Orchestration decisions</p>
          <strong className="mt-1 block text-2xl text-white">{decisions}</strong>
        </div>
      </div>
    </section>
  );
}
