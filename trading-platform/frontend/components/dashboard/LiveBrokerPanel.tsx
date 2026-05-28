import { StatusBadge } from "./StatusBadge";

function readStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

export function LiveBrokerPanel({
  brokerStatus,
  observationStatus,
}: {
  brokerStatus: Record<string, unknown> | null;
  observationStatus: Record<string, unknown> | null;
}) {
  const brokers = readStringArray(brokerStatus?.supported_brokers);
  const observation = String(observationStatus?.status ?? "loading");

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Live Broker Panel</p>
          <h2 className="mt-1 text-lg font-bold text-white">Broker Compatibility</h2>
        </div>
        <StatusBadge label={observation} tone={observation === "operational" ? "good" : "info"} />
      </div>
      <div className="mt-4 grid gap-2">
        {(brokers.length ? brokers : ["STARTRADER", "FXPRO", "VANTAGE"]).map((broker) => (
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2" key={broker}>
            <span className="text-sm font-semibold text-slate-200">{broker}</span>
            <span className="text-xs text-emerald-200">execution disabled</span>
          </div>
        ))}
      </div>
    </section>
  );
}
