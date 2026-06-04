import type { SymbolPerformanceSummary } from "@/lib/clientAnalyticsApi";

function money(value: number): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function SymbolPerformanceGrid({ symbols }: { symbols: SymbolPerformanceSummary[] }) {
  const visibleSymbols = symbols.length ? symbols : [];

  return (
    <section className="grid gap-3 lg:grid-cols-3">
      {visibleSymbols.map((symbol) => {
        const isNifty = symbol.symbol.toUpperCase() === "NIFTY50";
        return (
          <article className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4" key={symbol.symbol}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[0.68rem] font-bold uppercase tracking-[0.18em] text-slate-500">Symbol</p>
                <h3 className="mt-1 text-xl font-black text-white">{symbol.symbol}</h3>
              </div>
              {isNifty ? (
                <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-2.5 py-1 text-[0.58rem] font-black uppercase tracking-[0.12em] text-amber-100">
                  Placeholder / Pending Indian Broker Integration
                </span>
              ) : (
                <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[0.58rem] font-black uppercase tracking-[0.12em] text-cyan-100">
                  Analytics Ready
                </span>
              )}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              {[
                ["Demo Signals", symbol.total_signals],
                ["BUY", symbol.buy_signals],
                ["SELL", symbol.sell_signals],
                ["WAIT", symbol.wait_signals],
                ["Demo Executions", symbol.demo_executions],
                ["Demo Win Rate", `${Number(symbol.win_rate || 0).toFixed(2)}%`],
                ["Demo Net P&L", money(symbol.net_pnl)],
                ["Avg Demo Confidence", Number(symbol.avg_confidence || 0).toFixed(2)],
              ].map(([label, value]) => (
                <div className="rounded-xl border border-white/10 bg-slate-950/35 p-3" key={label}>
                  <p className="break-words text-[0.62rem] uppercase tracking-[0.12em] text-slate-500">{label}</p>
                  <strong className="mt-1 block break-words text-slate-100">{value}</strong>
                </div>
              ))}
            </div>
          </article>
        );
      })}
    </section>
  );
}
