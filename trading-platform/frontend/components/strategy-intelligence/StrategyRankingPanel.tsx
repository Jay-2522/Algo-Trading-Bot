export function StrategyRankingPanel({ rankings }: { rankings: Array<Record<string, unknown>> }) {
  const visible = rankings.length ? rankings : ["XAUUSD", "EURUSD", "NIFTY50"].map((symbol, index) => ({
    rank: index + 1,
    symbol,
    strategy_score: 0,
    placeholder: symbol === "NIFTY50",
  }));

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Rankings</p>
      <h3 className="mt-1 text-xl font-black text-white">Comparative Ranking</h3>
      <div className="mt-4 space-y-2">
        {visible.map((item) => (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.035] p-3" key={String(item.symbol)}>
            <div>
              <strong className="text-white">#{Number(item.rank || 0)} {String(item.symbol)}</strong>
              <p className="mt-1 text-xs text-slate-400">{item.placeholder ? "PENDING IMPLEMENTATION" : "Ranked by strategy score"}</p>
            </div>
            <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[0.6rem] font-black uppercase tracking-[0.12em] text-cyan-100">
              {Number(item.strategy_score || 0).toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
