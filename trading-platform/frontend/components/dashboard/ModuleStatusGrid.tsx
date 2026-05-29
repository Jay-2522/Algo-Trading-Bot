import type { OperationalModuleStatusData } from "@/lib/dashboard-api";
import { formatRelativeTime } from "@/lib/dashboard-formatters";

import { StatusBadge } from "./StatusBadge";

function tone(status: string): "good" | "warning" | "danger" | "muted" {
  const normalized = status.toUpperCase();
  if (normalized.includes("FAIL")) return "danger";
  if (normalized.includes("WARN")) return "warning";
  if (normalized.includes("DISABLE")) return "muted";
  return "good";
}

export function ModuleStatusGrid({ modules }: { modules: OperationalModuleStatusData[] }) {
  const fallback = [
    "Brokers",
    "Webhooks",
    "Dashboard",
    "Monitoring",
    "Control Center",
    "Portfolio",
    "Queue Engine",
    "Orchestration",
  ].map((moduleName) => ({
    module_name: moduleName,
    status: "LOADING",
    last_check: "",
    message: "Module status is loading.",
  }));
  const visibleModules = modules.length ? modules : fallback;

  return (
    <section className="min-w-0 rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Module Grid</p>
      <h3 className="mt-1 break-words text-xl font-black text-white">Monitored Subsystems</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {visibleModules.map((module) => (
          <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.035] p-4" key={module.module_name}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <strong className="min-w-0 flex-1 break-words text-sm text-white">{module.module_name}</strong>
              <StatusBadge label={module.status} tone={tone(module.status)} />
            </div>
            <p className="mt-2 line-clamp-2 break-words text-xs leading-5 text-slate-400">{module.message}</p>
            <p className="mt-3 text-[0.65rem] uppercase tracking-[0.12em] text-slate-600">{formatRelativeTime(module.last_check)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
