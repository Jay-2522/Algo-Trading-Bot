const defaultPipeline = [
  "TradingView Signal",
  "AI Orchestration",
  "Risk Check",
  "Account Routing",
  "Allocation",
  "Execution Queue",
  "Simulation Lifecycle",
];

export function PipelineReadinessPanel({ stages }: { stages: string[] }) {
  const visibleStages = stages.length ? stages : defaultPipeline;

  return (
    <section className="min-w-0 rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <p className="text-[0.68rem] uppercase tracking-[0.22em] text-cyan-100/70">Pipeline Readiness</p>
      <h3 className="mt-1 text-xl font-black text-white">Signal-to-Simulation Flow</h3>
      <div className="mt-5 grid gap-3 md:grid-cols-7">
        {visibleStages.map((stage, index) => (
          <div className="relative min-w-0" key={stage}>
            {index < visibleStages.length - 1 ? (
              <div className="pointer-events-none absolute left-1/2 top-5 hidden h-px w-full bg-gradient-to-r from-cyan-300/45 to-transparent md:block" />
            ) : null}
            <div className="relative z-10 flex min-h-28 min-w-0 flex-col items-center rounded-2xl border border-cyan-200/15 bg-slate-950/45 p-3 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-full border border-cyan-300/30 bg-cyan-300/15 text-sm font-black text-cyan-100 shadow-lg shadow-cyan-500/10">
                {index + 1}
              </span>
              <span className="mt-3 break-words text-xs font-bold leading-5 text-slate-200">{stage}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
