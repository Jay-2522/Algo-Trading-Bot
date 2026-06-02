import type { SessionPerformanceSummary } from "@/lib/clientAnalyticsApi";

function labelFor(session: string): string {
  return session.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function money(value: number): string {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function SessionPerformancePanel({ sessions }: { sessions: SessionPerformanceSummary[] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Session Analytics</p>
          <h3 className="mt-1 text-xl font-black text-white">Session Performance</h3>
        </div>
        <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[0.6rem] font-black uppercase tracking-[0.12em] text-cyan-100">
          Demo Data Only
        </span>
      </div>

      <div className="mt-4 overflow-hidden rounded-xl border border-white/10">
        {sessions.map((session) => (
          <div className="grid gap-2 border-b border-white/10 bg-white/[0.025] p-3 text-sm last:border-b-0 md:grid-cols-6" key={session.session}>
            <strong className="break-words text-white">{labelFor(session.session)}</strong>
            <span className="break-words text-slate-300">Signals {session.total_signals}</span>
            <span className="break-words text-slate-300">Demo {session.demo_executions}</span>
            <span className="break-words text-slate-300">Win {Number(session.win_rate || 0).toFixed(2)}%</span>
            <span className="break-words text-slate-300">P&L {money(session.net_pnl)}</span>
            <span className="break-words text-slate-300">Conf {Number(session.avg_confidence || 0).toFixed(2)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
