import { StatusBadge } from "./StatusBadge";

const brokers = ["STARTRADER", "FxPro", "Vantage"];

function getSupportedBrokers(status: Record<string, unknown> | null): string[] {
  const value = status?.supported_brokers;
  return Array.isArray(value) ? value.map(String) : [];
}

export function BrokerStatusPanel({ status }: { status: Record<string, unknown> | null }) {
  const supported = getSupportedBrokers(status).map((broker) => broker.toUpperCase());

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Broker Layer</p>
          <h2 className="mt-1 text-xl font-bold text-white">Broker Status</h2>
        </div>
        <StatusBadge label={status ? "Metadata Online" : "Loading"} tone={status ? "good" : "muted"} />
      </div>

      <div className="mt-5 grid gap-3">
        {brokers.map((broker) => {
          const available = supported.includes(broker.toUpperCase());
          return (
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" key={broker}>
              <div className="flex items-center justify-between gap-3">
                <strong className="text-sm text-slate-100">{broker}</strong>
                <StatusBadge label={available ? "Available" : "Pending"} tone={available ? "good" : "warning"} />
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-[0.72rem] text-slate-400">
                <span>Metadata ready</span>
                <span>Read-only check</span>
                <span className="text-emerald-200">Execution disabled</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
