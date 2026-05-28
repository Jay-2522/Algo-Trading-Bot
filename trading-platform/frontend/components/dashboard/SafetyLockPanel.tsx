import { StatusBadge } from "./StatusBadge";

function readBool(source: Record<string, unknown> | null | undefined, key: string): boolean {
  return source?.[key] === true;
}

export function SafetyLockPanel({ safetyState }: { safetyState: Record<string, unknown> | null }) {
  const queuePaused = readBool(safetyState, "queue_paused");
  const emergencyStop = readBool(safetyState, "emergency_stop_active");
  const liveExecution = readBool(safetyState, "live_execution_enabled");
  const brokerExecution = readBool(safetyState, "broker_execution_enabled");
  const locks = Array.isArray(safetyState?.active_locks) ? safetyState.active_locks.map(String) : [];

  return (
    <section className="min-w-0 rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-emerald-100/70">Safety Locks</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">Manual Safety State</h2>
        </div>
        <StatusBadge label={liveExecution || brokerExecution ? "Review" : "Locked"} tone={liveExecution || brokerExecution ? "danger" : "good"} />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {[
          ["Queue", queuePaused ? "Paused" : "Ready for simulation"],
          ["Emergency Stop", emergencyStop ? "Placeholder active" : "Placeholder idle"],
          ["Live Execution", liveExecution ? "Enabled" : "Disabled"],
          ["Broker Execution", brokerExecution ? "Enabled" : "Disabled"],
        ].map(([label, value]) => (
          <div className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/35 p-3" key={label}>
            <p className="break-words text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <strong className="mt-1 block break-words text-sm leading-relaxed text-white">{value}</strong>
          </div>
        ))}
      </div>

      <div className="mt-4 min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
        <p className="text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">Active Locks</p>
        <p className="mt-2 break-words text-sm leading-6 text-slate-300">{locks.length ? locks.join(", ") : "No active operator locks."}</p>
      </div>
    </section>
  );
}
