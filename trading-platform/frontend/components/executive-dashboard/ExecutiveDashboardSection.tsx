"use client";

import { useCallback, useEffect, useState } from "react";

import {
  emptyExecutiveSummary,
  emptyInstruments,
  emptyReadinessItems,
  emptySystemHealth,
  fetchExecutiveInstruments,
  fetchExecutiveReadiness,
  fetchExecutiveSummary,
  fetchExecutiveSystemHealth,
  type ExecutiveSummary,
  type InstrumentReadiness,
  type ReadinessItem,
  type SystemHealth,
} from "@/lib/executiveDashboardApi";

import { ExecutiveSummaryPanel } from "./ExecutiveSummaryPanel";
import { InstrumentReadinessPanel } from "./InstrumentReadinessPanel";
import { ProductionReadinessPanel } from "./ProductionReadinessPanel";
import { SystemHealthPanel } from "./SystemHealthPanel";
import { SystemReadinessCards } from "./SystemReadinessCards";

function SafetyBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-cyan-100">
      {label}
    </span>
  );
}

export function ExecutiveDashboardSection() {
  const [summary, setSummary] = useState<ExecutiveSummary>(emptyExecutiveSummary);
  const [readiness, setReadiness] = useState<ReadinessItem[]>(emptyReadinessItems);
  const [instruments, setInstruments] = useState<InstrumentReadiness[]>(emptyInstruments);
  const [health, setHealth] = useState<SystemHealth>(emptySystemHealth);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [summaryData, readinessData, instrumentData, healthData] = await Promise.all([
      fetchExecutiveSummary(),
      fetchExecutiveReadiness(),
      fetchExecutiveInstruments(),
      fetchExecutiveSystemHealth(),
    ]);
    setSummary(summaryData);
    setReadiness(readinessData);
    setInstruments(instrumentData);
    setHealth(healthData);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(8,47,73,0.46),rgba(15,23,42,0.78),rgba(20,184,166,0.08))] p-5 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.24em] text-cyan-100/70">Executive Command Center</p>
          <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white sm:text-3xl">Executive Command Center</h2>
          <p className="mt-2 max-w-5xl break-words text-sm leading-7 text-slate-300">
            A complete operational view of analytics, execution, reporting, account synchronization, deployment readiness, and instrument coverage.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SafetyBadge label="SIMULATION ONLY" />
          <SafetyBadge label="DEMO MODE" />
          <SafetyBadge label="LIVE DISABLED" />
          <SafetyBadge label={loading ? "LOADING" : "READY"} />
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <ExecutiveSummaryPanel summary={summary} />
        <SystemReadinessCards items={readiness} />
        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <InstrumentReadinessPanel instruments={instruments} />
          <SystemHealthPanel health={health} />
        </div>
        <ProductionReadinessPanel summary={summary} />
      </div>
    </section>
  );
}
