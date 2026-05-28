import { StatusBadge } from "./StatusBadge";

const brokers = ["STARTRADER", "FxPro", "Vantage"];

function getSupportedBrokers(status: Record<string, unknown> | null): string[] {
  const value = status?.supported_brokers;
  return Array.isArray(value) ? value.map(String) : [];
}

export function BrokerStatusPanel({ status }: { status: Record<string, unknown> | null }) {
  const supported = getSupportedBrokers(status).map((broker) => broker.toUpperCase());

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Broker Layer</p>
          <h2 className="mt-1 break-words text-xl font-bold leading-relaxed text-white">Broker Status</h2>
        </div>
        <StatusBadge label={status ? "Metadata Online" : "Loading"} tone={status ? "good" : "muted"} />
      </div>

      <div className="mt-5 grid gap-3">
        {brokers.map((broker) => {
          const available = supported.includes(broker.toUpperCase());
          return (
            <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-4" key={broker}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="min-w-0 max-w-full truncate text-sm text-slate-100" title={broker}>{broker}</strong>
                <StatusBadge label={available ? "Available" : "Pending"} tone={available ? "good" : "warning"} />
              </div>
              <div className="mt-3 grid gap-2 text-[0.72rem] leading-relaxed text-slate-400 sm:grid-cols-3">
                <span className="break-words">Metadata ready</span>
                <span className="break-words">Read-only check</span>
                <span className="break-words text-emerald-200">Execution disabled</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
