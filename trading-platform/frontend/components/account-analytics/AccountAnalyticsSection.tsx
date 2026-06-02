"use client";

import { useCallback, useEffect, useState } from "react";

import {
  emptyAccounts,
  emptySyncStatus,
  fetchAccountAnalyticsAccounts,
  fetchAccountSyncStatus,
  type AccountAnalyticsSummary,
  type AccountSyncStatus,
} from "@/lib/accountAnalyticsApi";

import { AccountAnalyticsEmptyState } from "./AccountAnalyticsEmptyState";
import { AccountOverviewCards } from "./AccountOverviewCards";
import { AccountPerformanceGrid } from "./AccountPerformanceGrid";
import { CopierSyncPanel } from "./CopierSyncPanel";

function SafetyBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-cyan-100">
      {label}
    </span>
  );
}

export function AccountAnalyticsSection() {
  const [accounts, setAccounts] = useState<AccountAnalyticsSummary[]>(emptyAccounts);
  const [sync, setSync] = useState<AccountSyncStatus>(emptySyncStatus);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [accountData, syncData] = await Promise.all([fetchAccountAnalyticsAccounts(), fetchAccountSyncStatus()]);
    setAccounts(accountData.length ? accountData : emptyAccounts);
    setSync(syncData);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const empty = accounts.every((account) => account.total_executions === 0 && account.total_copied_trades === 0);

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.76),rgba(8,47,73,0.4),rgba(20,184,166,0.08))] p-5 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.24em] text-cyan-100/70">Account Intelligence</p>
          <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white sm:text-3xl">
            Account Analytics & Copier Intelligence
          </h2>
          <p className="mt-2 max-w-5xl break-words text-sm leading-7 text-slate-300">
            Monitor master account activity, copier synchronization, account performance, and execution consistency.
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
        <AccountOverviewCards accounts={accounts} sync={sync} />
        <AccountPerformanceGrid accounts={accounts} />
        <CopierSyncPanel accounts={accounts} sync={sync} />
        {empty ? <AccountAnalyticsEmptyState /> : null}
      </div>
    </section>
  );
}
