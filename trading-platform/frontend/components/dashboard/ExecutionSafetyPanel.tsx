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
    <section className="rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-emerald-100/70">Execution Safety</p>
          <h2 className="mt-1 text-xl font-bold text-white">Simulation Guardrails</h2>
        </div>
        <StatusBadge label={`${totalItems} queued`} tone="good" />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {safetyRows.map(([title, detail]) => (
          <div className="rounded-2xl border border-emerald-100/10 bg-slate-950/30 p-4" key={title}>
            <strong className="text-sm text-emerald-100">{title}</strong>
            <p className="mt-2 text-xs leading-5 text-emerald-50/65">{detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
