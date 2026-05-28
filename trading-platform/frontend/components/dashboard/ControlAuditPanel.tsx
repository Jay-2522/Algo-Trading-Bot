import { formatRelativeTime, readText } from "@/lib/dashboard-formatters";

export function ControlAuditPanel({ events }: { events: Array<Record<string, unknown>> }) {
  const visibleEvents = events.slice(0, 5);

  return (
    <section className="min-w-0 rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Control Audit</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">Operator Actions</h2>
        </div>
        <span className="rounded-full border border-sky-300/20 bg-sky-300/10 px-2.5 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-sky-100">
          {events.length} events
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {visibleEvents.length ? (
          visibleEvents.map((event, index) => (
            <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3" key={readText(event, ["event_id"], `control-event-${index}`)}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <strong className="min-w-0 break-words text-sm leading-relaxed text-white">{readText(event, ["action_type"], "Control event")}</strong>
                <span className="shrink-0 text-[0.68rem] text-slate-500">{formatRelativeTime(readText(event, ["timestamp"], ""))}</span>
              </div>
              <p className="mt-1 break-words text-xs leading-6 text-slate-400">{readText(event, ["reason"], "Simulation-only control audit event.")}</p>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-4 text-sm leading-6 text-slate-400">
            No manual control actions recorded yet. Operator controls will appear here once used.
          </div>
        )}
      </div>
    </section>
  );
}
