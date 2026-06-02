"use client";

import { useCallback, useEffect, useState } from "react";

import { emptyClientReport, fetchDailyReport, fetchRiskReport, fetchSymbolReport, fetchWeeklyReport, type ClientReport } from "@/lib/clientReportsApi";

import { ReportEmptyState } from "./ReportEmptyState";
import { ReportExportPanel } from "./ReportExportPanel";
import { ReportPreview } from "./ReportPreview";
import { ReportSummaryCards } from "./ReportSummaryCards";

function SafetyBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[0.62rem] font-black uppercase tracking-[0.14em] text-cyan-100">
      {label}
    </span>
  );
}

export function ClientReportsSection() {
  const [report, setReport] = useState<ClientReport>(emptyClientReport);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [daily] = await Promise.all([
      fetchDailyReport(),
      fetchWeeklyReport(),
      fetchSymbolReport("XAUUSD"),
      fetchRiskReport(),
    ]);
    setReport(daily);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const empty = Boolean(report.summary.empty_report);

  return (
    <section className="rounded-3xl border border-cyan-300/15 bg-[linear-gradient(135deg,rgba(8,47,73,0.4),rgba(15,23,42,0.78),rgba(16,185,129,0.08))] p-5 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.24em] text-cyan-100/70">Client Reports</p>
          <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white sm:text-3xl">Client Reports & Exports</h2>
          <p className="mt-2 max-w-5xl break-words text-sm leading-7 text-slate-300">
            Download transparent demo performance, risk, execution, and strategy reports.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SafetyBadge label="DEMO REPORT" />
          <SafetyBadge label="SIMULATION ONLY" />
          <SafetyBadge label="LIVE DISABLED" />
          <SafetyBadge label={loading ? "LOADING" : "READY"} />
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <ReportSummaryCards report={report} />
        <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
          <ReportExportPanel />
          <ReportPreview report={report} />
        </div>
        {empty ? <ReportEmptyState /> : null}
      </div>
    </section>
  );
}
