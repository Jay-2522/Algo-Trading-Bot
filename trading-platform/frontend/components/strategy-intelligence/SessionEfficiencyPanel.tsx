export function SessionEfficiencyPanel({ sessions }: { sessions: Array<Record<string, unknown>> }) {
  const visible = sessions.length ? sessions : ["ASIAN", "LONDON", "NEW_YORK", "OVERLAP"].map((session) => ({
    session,
    signals: 0,
    risk_pass_rate: 0,
    execution_rate: 0,
    efficiency_score: 0,
  }));

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Session Efficiency</p>
      <h3 className="mt-1 text-xl font-black text-white">Session Effectiveness</h3>
      <div className="mt-4 space-y-2">
        {visible.map((item) => (
          <div className="grid gap-2 rounded-xl border border-white/10 bg-white/[0.035] p-3 text-sm md:grid-cols-4" key={String(item.session)}>
            <strong className="text-white">{String(item.session).replaceAll("_", " ")}</strong>
            <span className="text-slate-300">Signals {Number(item.signals || 0)}</span>
            <span className="text-slate-300">Risk {Number(item.risk_pass_rate || 0).toFixed(2)}%</span>
            <span className="text-slate-300">Score {Number(item.efficiency_score || 0).toFixed(2)}%</span>
          </div>
        ))}
      </div>
    </section>
  );
}
