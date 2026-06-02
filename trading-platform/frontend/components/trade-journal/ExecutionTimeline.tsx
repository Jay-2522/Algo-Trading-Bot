import type { ExecutionTimelineStep } from "@/lib/tradeJournalApi";

const stepClass: Record<ExecutionTimelineStep["status"], string> = {
  Complete: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
  Pending: "border-amber-300/25 bg-amber-300/10 text-amber-100",
  Blocked: "border-rose-300/25 bg-rose-300/10 text-rose-100",
  "Not Available": "border-slate-500/25 bg-slate-500/10 text-slate-200",
};

export function ExecutionTimeline({ steps }: { steps: ExecutionTimelineStep[] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <div>
        <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Lifecycle Timeline</p>
        <h3 className="mt-1 text-xl font-black text-white">Signal To Final Status</h3>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-9">
        {steps.map((step, index) => (
          <article className="relative min-h-32 rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={step.label}>
            <div className="flex items-center justify-between gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-300/10 text-xs font-black text-cyan-100">
                {index + 1}
              </span>
              <span className={`rounded-full border px-2 py-1 text-[0.55rem] font-black uppercase tracking-[0.1em] ${stepClass[step.status]}`}>
                {step.status}
              </span>
            </div>
            <strong className="mt-3 block break-words text-sm text-white">{step.label}</strong>
            <p className="mt-2 break-words text-xs leading-5 text-slate-400">{step.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
