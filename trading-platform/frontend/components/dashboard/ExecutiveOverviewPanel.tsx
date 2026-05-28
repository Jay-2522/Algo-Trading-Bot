import type { ClientDemoOverviewData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

function ListGroup({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="min-w-0 rounded-3xl border border-white/10 bg-slate-950/35 p-4">
      <p className="text-[0.68rem] uppercase tracking-[0.18em] text-slate-500">{title}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? (
          items.map((item) => (
            <span className="max-w-full rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-bold text-slate-200" key={item}>
              {item}
            </span>
          ))
        ) : (
          <span className="text-sm text-slate-500">Loading...</span>
        )}
      </div>
    </div>
  );
}

export function ExecutiveOverviewPanel({ overview }: { overview: ClientDemoOverviewData | null }) {
  return (
    <section className="min-w-0 overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950/60 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-cyan-100/70">Client Demo Mode</p>
          <h2 className="mt-2 break-words text-3xl font-black leading-tight text-white">Executive Overview</h2>
          <p className="mt-3 max-w-4xl break-words text-sm leading-7 text-slate-300">
            A presentation-ready view of the platform MVP: supported markets, supported brokers, TradingView signal flow,
            simulation queue readiness, and safety boundaries.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge label={overview?.system_status ?? "Loading"} tone="good" />
          <StatusBadge label={overview?.live_execution_enabled ? "Live Enabled" : "Live Disabled"} tone="good" />
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ListGroup title="Supported Markets" items={overview?.supported_markets ?? []} />
        <ListGroup title="Supported Brokers" items={overview?.supported_brokers ?? []} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="min-w-0 rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.07] p-4">
          <p className="text-[0.68rem] uppercase tracking-[0.18em] text-emerald-100/70">Safety Summary</p>
          <ul className="mt-3 space-y-2">
            {(overview?.safety_summary ?? ["Simulation-only mode active.", "Live execution disabled."]).map((item) => (
              <li className="flex min-w-0 gap-2 text-sm leading-6 text-emerald-50/80" key={item}>
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-300" />
                <span className="break-words">{item}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="min-w-0 rounded-3xl border border-sky-300/15 bg-sky-300/[0.07] p-4">
          <p className="text-[0.68rem] uppercase tracking-[0.18em] text-sky-100/70">Next Production Steps</p>
          <ul className="mt-3 space-y-2">
            {(overview?.next_steps ?? ["Demo execution bridge", "VPS deployment", "Production hardening"]).map((item) => (
              <li className="flex min-w-0 gap-2 text-sm leading-6 text-sky-50/80" key={item}>
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-300" />
                <span className="break-words">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
