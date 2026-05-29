import type { OperationalHealthSummaryData, OperationalModuleStatusData, WarningSummaryData } from "@/lib/dashboard-api";

import { ModuleStatusGrid } from "./ModuleStatusGrid";
import { OperationalInsightsPanel } from "./OperationalInsightsPanel";
import { SystemHealthScore } from "./SystemHealthScore";
import { WarningCenter } from "./WarningCenter";

export function OperationalHealthPanel({
  summary,
  modules,
  warnings,
}: {
  summary: OperationalHealthSummaryData | null;
  modules: OperationalModuleStatusData[];
  warnings: WarningSummaryData[];
}) {
  return (
    <section className="space-y-4">
      <section className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
        <p className="text-[0.68rem] uppercase tracking-[0.24em] text-cyan-100/70">Operational Intelligence Center</p>
        <h2 className="mt-2 break-words text-3xl font-black leading-tight text-white">Monitoring & Observability</h2>
        <p className="mt-3 max-w-4xl break-words text-sm leading-7 text-slate-300">
          Real-time operational posture across health, warnings, broker readiness, webhook activity, queue state, portfolio analytics, and safety controls.
        </p>
      </section>
      <section className="grid gap-4 xl:grid-cols-[0.85fr_1.25fr]">
        <SystemHealthScore summary={summary} />
        <OperationalInsightsPanel summary={summary} />
      </section>
      <ModuleStatusGrid modules={modules} />
      <WarningCenter warnings={warnings} />
    </section>
  );
}
