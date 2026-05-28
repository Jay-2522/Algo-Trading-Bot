import { normalizeStatus, type NormalizedStatus } from "@/lib/dashboard-formatters";

const stages = [
  "Signal Received",
  "Validation",
  "Risk Check",
  "Allocation",
  "Queue Preparation",
  "Simulated Fill",
  "Lifecycle Complete",
];

const stageClass: Record<NormalizedStatus, string> = {
  completed: "border-emerald-300/40 bg-emerald-300/15 text-emerald-100 shadow-[0_0_28px_rgba(16,185,129,0.22)]",
  pending: "border-sky-300/25 bg-sky-300/10 text-sky-100",
  rejected: "border-rose-300/35 bg-rose-300/10 text-rose-100",
  warning: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  info: "border-slate-600/50 bg-slate-800/35 text-slate-300",
};

function inferProgress({
  webhookEvents,
  orchestrationDecisions,
  queueItems,
  lifecycleAuditEvents,
}: {
  webhookEvents: Array<Record<string, unknown>>;
  orchestrationDecisions: Array<Record<string, unknown>>;
  queueItems: Array<Record<string, unknown>>;
  lifecycleAuditEvents: Array<Record<string, unknown>>;
}): NormalizedStatus[] {
  const hasSignal = webhookEvents.length > 0;
  const hasDecision = orchestrationDecisions.length > 0;
  const hasQueue = queueItems.length > 0;
  const hasLifecycle = lifecycleAuditEvents.length > 0;
  const rejected = [...orchestrationDecisions, ...queueItems, ...lifecycleAuditEvents].some((event) =>
    normalizeStatus(event.final_decision ?? event.status ?? event.event_type) === "rejected",
  );

  if (rejected) {
    return ["completed", "completed", "rejected", "pending", "pending", "pending", "pending"];
  }

  return [
    hasSignal ? "completed" : "pending",
    hasSignal ? "completed" : "pending",
    hasDecision ? "completed" : "pending",
    hasDecision ? "completed" : "pending",
    hasQueue ? "completed" : "pending",
    hasLifecycle ? "completed" : "pending",
    hasLifecycle ? "completed" : "pending",
  ];
}

export function TradeLifecycleTimeline(props: {
  webhookEvents: Array<Record<string, unknown>>;
  orchestrationDecisions: Array<Record<string, unknown>>;
  queueItems: Array<Record<string, unknown>>;
  lifecycleAuditEvents: Array<Record<string, unknown>>;
}) {
  const progress = inferProgress(props);

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div>
        <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Simulated Flow</p>
        <h2 className="mt-1 break-words text-xl font-bold text-white">Trade Lifecycle Timeline</h2>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-7">
        {stages.map((stage, index) => {
          const status = progress[index];
          return (
            <div className="relative min-w-0" key={stage}>
              {index < stages.length - 1 ? (
                <div className="absolute left-6 top-6 hidden h-px w-[calc(100%+1rem)] bg-gradient-to-r from-cyan-300/35 to-transparent lg:block" />
              ) : null}
              <div className={`relative min-h-28 rounded-2xl border p-4 ${stageClass[status]}`}>
                <div className="mb-3 flex h-5 w-5 items-center justify-center rounded-full border border-current text-[0.65rem] font-black">
                  {index + 1}
                </div>
                <strong className="block break-words text-sm leading-relaxed">{stage}</strong>
                <span className="mt-2 block text-xs capitalize opacity-75">{status}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
