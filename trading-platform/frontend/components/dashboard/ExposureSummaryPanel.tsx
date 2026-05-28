import type { PortfolioExposureSummaryData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

export function ExposureSummaryPanel({ exposure }: { exposure: PortfolioExposureSummaryData | null }) {
  const rows = Object.entries(exposure?.exposure_by_symbol ?? {});

  return (
    <section className="min-w-0 rounded-3xl border border-cyan-300/15 bg-cyan-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-cyan-100/70">Exposure Summary</p>
          <h3 className="mt-1 break-words text-xl font-black text-white">Symbol-Level Readiness</h3>
        </div>
        <StatusBadge label="Simulation" tone="good" />
      </div>

      <div className="mt-4 space-y-3">
        {rows.length ? (
          rows.map(([symbol, details]) => {
            const status = String(details.status ?? "UNKNOWN");
            const isBlocked = status.includes("BLOCK");
            const accounts = Array.isArray(details.supporting_accounts) ? details.supporting_accounts.map(String) : [];
            return (
              <div className="min-w-0 rounded-2xl border border-white/10 bg-slate-950/35 p-4" key={symbol}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <strong className="break-words text-sm text-white">{symbol}</strong>
                  <StatusBadge label={isBlocked ? "Conditional" : "Ready"} tone={isBlocked ? "warning" : "good"} />
                </div>
                <p className="mt-2 break-words text-xs leading-6 text-slate-400">
                  {String(details.reason ?? "Simulated exposure checks available.")}
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-[0.65rem] text-slate-300">
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-1">
                    Max lot {String(details.max_total_lot ?? 0)}
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-1">
                    Max risk {String(details.max_risk ?? 0)}%
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-1">
                    {accounts.length ? `${accounts.length} accounts` : "No active accounts"}
                  </span>
                </div>
              </div>
            );
          })
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
            Exposure summary is loading.
          </div>
        )}
      </div>
    </section>
  );
}
