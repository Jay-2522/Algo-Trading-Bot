import { formatRelativeTime, readText } from "@/lib/dashboard-formatters";
import { StatusBadge } from "./StatusBadge";

export function RecentSignalsPanel({ webhookEvents }: { webhookEvents: Array<Record<string, unknown>> }) {
  const signals = webhookEvents.slice(0, 6);

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Signal Desk</p>
          <h2 className="mt-1 text-xl font-bold text-white">Recent Signals</h2>
        </div>
        <StatusBadge label={`${signals.length} visible`} tone="info" />
      </div>

      {signals.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-700 bg-white/[0.03] p-5">
          <strong className="text-sm text-slate-100">No TradingView signals received</strong>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Recent symbol, action, timeframe, confidence, and strategy data will populate here after webhook ingestion.
          </p>
        </div>
      ) : (
        <div className="mt-5 overflow-hidden rounded-2xl border border-white/10">
          {signals.map((signal, index) => (
            <div className="grid gap-2 border-b border-white/10 bg-white/[0.025] p-3 text-sm last:border-b-0 md:grid-cols-6" key={`${readText(signal, ["event_id"], String(index))}-${index}`}>
              <span className="break-words font-bold text-white">{readText(signal, ["symbol"], "N/A")}</span>
              <span className="break-words text-cyan-100">{readText(signal, ["action"], "ALERT")}</span>
              <span className="break-words text-slate-300">{readText(signal, ["timeframe"], "M15")}</span>
              <span className="break-words text-slate-300">{readText(signal, ["confidence"], "n/a")}</span>
              <span className="break-words text-slate-400">{readText(signal, ["strategy"], "TradingView")}</span>
              <span className="break-words text-slate-500">{formatRelativeTime(readText(signal, ["timestamp"], ""))}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
