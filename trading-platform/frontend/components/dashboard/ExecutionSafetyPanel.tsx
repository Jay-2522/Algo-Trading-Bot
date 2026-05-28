import { StatusBadge } from "./StatusBadge";

const safetyRows = [
  ["Queue preparation only", "Orders are staged as non-executing intents."],
  ["Simulated lifecycle only", "Acceptance, fill, rejection, and cancellation are emulated."],
  ["Manual override later", "Operator controls are planned for a later phase."],
  ["No live orders enabled", "Broker execution remains disabled at every layer."],
];

export function ExecutionSafetyPanel({ status }: { status: Record<string, unknown> | null }) {
  const totalItems = typeof status?.total_items === "number" ? status.total_items : 0;

  return (
    <section className="overflow-hidden rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-emerald-100/70">Execution Safety</p>
          <h2 className="mt-1 break-words text-xl font-bold leading-relaxed text-white">Simulation Guardrails</h2>
        </div>
        <StatusBadge label={`${totalItems} queued`} tone="good" />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {safetyRows.map(([title, detail]) => (
          <div className="min-w-0 rounded-2xl border border-emerald-100/10 bg-slate-950/30 p-4" key={title}>
            <strong className="break-words text-sm leading-relaxed text-emerald-100">{title}</strong>
            <p className="mt-2 break-words text-xs leading-relaxed text-emerald-50/65">{detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
