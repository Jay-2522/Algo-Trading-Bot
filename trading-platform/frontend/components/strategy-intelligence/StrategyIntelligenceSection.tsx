"use client";

import { useCallback, useEffect, useState } from "react";

import {
  emptyOverview,
  emptyStrategies,
  fetchStrategyOverview,
  fetchStrategyPerformance,
  fetchStrategyRankings,
  fetchStrategySessionEfficiency,
  type StrategyOverview,
  type StrategyPerformanceSummary,
} from "@/lib/strategyAnalyticsApi";

import { SessionEfficiencyPanel } from "./SessionEfficiencyPanel";
import { StrategyComparisonGrid } from "./StrategyComparisonGrid";
import { StrategyIntelligenceEmptyState } from "./StrategyIntelligenceEmptyState";
import { StrategyOverviewCards } from "./StrategyOverviewCards";
import { StrategyRankingPanel } from "./StrategyRankingPanel";

function SafetyBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-cyan-100">
      {label}
    </span>
  );
}

export function StrategyIntelligenceSection() {
  const [overview, setOverview] = useState<StrategyOverview>(emptyOverview);
  const [strategies, setStrategies] = useState<StrategyPerformanceSummary[]>(emptyStrategies);
  const [rankings, setRankings] = useState<Array<Record<string, unknown>>>([]);
  const [sessions, setSessions] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [overviewData, performanceData, rankingData, sessionData] = await Promise.all([
      fetchStrategyOverview(),
      fetchStrategyPerformance(),
      fetchStrategyRankings(),
      fetchStrategySessionEfficiency(),
    ]);
    setOverview(overviewData);
    setStrategies(performanceData.length ? performanceData : emptyStrategies);
    setRankings(rankingData);
    setSessions(sessionData);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const empty = strategies.every((strategy) => strategy.total_signals === 0 && strategy.strategy_score === 0);

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(8,47,73,0.42),rgba(15,23,42,0.76),rgba(14,165,233,0.08))] p-5 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.24em] text-cyan-100/70">Strategy Intelligence</p>
          <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white sm:text-3xl">Strategy Performance Intelligence</h2>
          <p className="mt-2 max-w-5xl break-words text-sm leading-7 text-slate-300">
            Compare signal quality, execution quality, risk efficiency, and session effectiveness across supported instruments.
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
        <StrategyOverviewCards overview={overview} />
        <StrategyComparisonGrid strategies={strategies} />
        <div className="grid gap-4 xl:grid-cols-[1fr_0.8fr]">
          <SessionEfficiencyPanel sessions={sessions} />
          <StrategyRankingPanel rankings={rankings} />
        </div>
        {empty ? <StrategyIntelligenceEmptyState /> : null}
      </div>
    </section>
  );
}
