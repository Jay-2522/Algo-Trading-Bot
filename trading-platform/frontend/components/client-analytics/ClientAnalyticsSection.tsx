"use client";

import { useCallback, useEffect, useState } from "react";

import { AnalyticsEmptyState } from "./AnalyticsEmptyState";
import { AnalyticsOverviewCards } from "./AnalyticsOverviewCards";
import { RiskAnalyticsPanel } from "./RiskAnalyticsPanel";
import { SessionPerformancePanel } from "./SessionPerformancePanel";
import { SymbolPerformanceGrid } from "./SymbolPerformanceGrid";
import {
  emptyAnalyticsOverview,
  emptyRiskAnalytics,
  emptySessions,
  emptySymbols,
  fetchClientAnalyticsOverview,
  fetchClientAnalyticsRisk,
  fetchClientAnalyticsSessions,
  fetchClientAnalyticsSnapshot,
  fetchClientAnalyticsSymbols,
  type ClientAnalyticsOverview,
  type RiskAnalyticsSummary,
  type SessionPerformanceSummary,
  type SymbolPerformanceSummary,
} from "@/lib/clientAnalyticsApi";

function SafetyBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-cyan-100">
      {label}
    </span>
  );
}

export function ClientAnalyticsSection() {
  const [overview, setOverview] = useState<ClientAnalyticsOverview>(emptyAnalyticsOverview);
  const [symbols, setSymbols] = useState<SymbolPerformanceSummary[]>(emptySymbols);
  const [sessions, setSessions] = useState<SessionPerformanceSummary[]>(emptySessions);
  const [risk, setRisk] = useState<RiskAnalyticsSummary>(emptyRiskAnalytics);
  const [loading, setLoading] = useState(true);
  const emptyData = overview.total_signals === 0 && overview.total_demo_executions === 0;

  const refresh = useCallback(async () => {
    setLoading(true);
    const [overviewData, symbolData, sessionData, riskData] = await Promise.all([
      fetchClientAnalyticsOverview(),
      fetchClientAnalyticsSymbols(),
      fetchClientAnalyticsSessions(),
      fetchClientAnalyticsRisk(),
    ]);
    void fetchClientAnalyticsSnapshot();
    setOverview(overviewData);
    setSymbols(symbolData.length ? symbolData : emptySymbols);
    setSessions(sessionData.length ? sessionData : emptySessions);
    setRisk(riskData);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(8,47,73,0.42),rgba(15,23,42,0.74),rgba(20,184,166,0.08))] p-5 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.24em] text-cyan-100/70">Client Analytics</p>
          <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white sm:text-3xl">
            Client Analytics & Performance Intelligence
          </h2>
          <p className="mt-2 max-w-5xl break-words text-sm leading-7 text-slate-300">
            Transparent analytics for strategy signals, demo execution, risk blocks, symbol performance, and session behavior.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SafetyBadge label="SIMULATION ONLY" />
          <SafetyBadge label="DEMO MODE" />
          <SafetyBadge label="LIVE DISABLED" />
          <SafetyBadge label={loading ? "LOADING" : "READY"} />
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-3">
        <div className="grid gap-2 text-xs text-slate-300 sm:grid-cols-2 xl:grid-cols-4">
          <div>simulation_only = {String(overview.simulation_only)}</div>
          <div>demo_execution = {String(overview.demo_execution)}</div>
          <div>live_execution_enabled = {String(overview.live_execution_enabled)}</div>
          <div>broker_execution_enabled = {String(overview.broker_execution_enabled)}</div>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <AnalyticsOverviewCards overview={overview} />
        <SymbolPerformanceGrid symbols={symbols} />
        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <SessionPerformancePanel sessions={sessions} />
          <RiskAnalyticsPanel risk={risk} />
        </div>
        {emptyData ? <AnalyticsEmptyState /> : null}
      </div>
    </section>
  );
}
