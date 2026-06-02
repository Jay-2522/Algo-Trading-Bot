import type { InstrumentReadiness } from "@/lib/executiveDashboardApi";

export function InstrumentReadinessPanel({ instruments }: { instruments: InstrumentReadiness[] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/45 p-5">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-cyan-100/70">Instrument Readiness</p>
      <h3 className="mt-2 text-xl font-black text-white">Coverage Matrix</h3>
      <div className="mt-4 grid gap-3">
        {instruments.map((instrument) => (
          <article className="rounded-2xl border border-white/10 bg-white/[0.035] p-4" key={instrument.symbol}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <strong className="text-lg text-white">{instrument.symbol}</strong>
              <span className={instrument.ready ? "rounded-full bg-emerald-300/10 px-3 py-1 text-xs font-black text-emerald-100" : "rounded-full bg-amber-300/10 px-3 py-1 text-xs font-black text-amber-100"}>
                {instrument.status.replaceAll("_", " ")}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-400">{instrument.reason}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
