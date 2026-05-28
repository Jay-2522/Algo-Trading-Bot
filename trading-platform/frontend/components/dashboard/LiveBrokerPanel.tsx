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
    <section className="min-h-64 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/50 p-5 shadow-xl shadow-black/15 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-slate-500">Live Broker Panel</p>
          <h2 className="mt-1 break-words text-lg font-bold leading-relaxed text-white">Broker Compatibility</h2>
        </div>
        <StatusBadge label={observation} tone={observation === "operational" ? "good" : "info"} />
      </div>
      <div className="mt-4 grid gap-2">
        {(brokers.length ? brokers : ["STARTRADER", "FXPRO", "VANTAGE"]).map((broker) => (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2.5" key={broker}>
            <span className="min-w-0 max-w-full truncate text-sm font-semibold text-slate-200" title={broker}>{broker}</span>
            <span className="shrink-0 text-xs leading-relaxed text-emerald-200">execution disabled</span>
          </div>
        ))}
      </div>
    </section>
  );
}
