import type { WarningSummaryData } from "@/lib/dashboard-api";
import { formatRelativeTime } from "@/lib/dashboard-formatters";

import { StatusBadge } from "./StatusBadge";

function tone(severity: string): "good" | "info" | "warning" | "danger" {
  const normalized = severity.toUpperCase();
  if (normalized.includes("CRITICAL") || normalized.includes("ERROR")) return "danger";
  if (normalized.includes("WARN")) return "warning";
  if (normalized.includes("INFO")) return "info";
  return "good";
}

export function WarningCenter({ warnings }: { warnings: WarningSummaryData[] }) {
  return (
    <section className="min-w-0 rounded-3xl border border-amber-300/15 bg-amber-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-amber-100/70">Warning Center</p>
          <h3 className="mt-1 break-words text-xl font-black text-white">Operational Warnings</h3>
        </div>
        <StatusBadge label={`${warnings.length} items`} tone={warnings.length ? "warning" : "good"} />
      </div>
      <div className="mt-4 space-y-3">
        {warnings.length ? (
          warnings.slice(0, 6).map((warning) => (
            <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3" key={warning.warning_id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <strong className="break-words text-sm text-white">{warning.category}</strong>
                <StatusBadge label={warning.severity} tone={tone(warning.severity)} />
              </div>
              <p className="mt-2 break-words text-xs leading-6 text-amber-50/75">{warning.message}</p>
              <p className="mt-2 text-[0.65rem] uppercase tracking-[0.12em] text-amber-100/45">{formatRelativeTime(warning.timestamp)}</p>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
            No operational warnings are active.
          </div>
        )}
      </div>
    </section>
  );
}
