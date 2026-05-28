import type { ClientDemoOverviewData, ExecutiveKpiData } from "@/lib/dashboard-api";

import { ClientKpiGrid } from "./ClientKpiGrid";
import { ExecutiveOverviewPanel } from "./ExecutiveOverviewPanel";
import { PipelineReadinessPanel } from "./PipelineReadinessPanel";

export function ClientDemoModePanel({
  overview,
  kpis,
}: {
  overview: ClientDemoOverviewData | null;
  kpis: ExecutiveKpiData[];
}) {
  const visibleKpis = kpis.length ? kpis : overview?.kpis ?? [];
  return (
    <section className="space-y-4">
      <ExecutiveOverviewPanel overview={overview} />
      <ClientKpiGrid kpis={visibleKpis} />
      <PipelineReadinessPanel stages={overview?.pipeline_summary ?? []} />
    </section>
  );
}
