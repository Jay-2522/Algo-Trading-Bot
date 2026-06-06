"use client";

import { useEffect, useState } from "react";

import { emptyPlatformFoundationBundle, fetchPlatformFoundationBundle, type PlatformFoundationBundle } from "@/lib/platformFoundationApi";
import { readNumber, readText } from "@/lib/dashboard-formatters";
import { StatusBadge } from "./StatusBadge";

function metric(value: unknown): string {
  const number = Number(value ?? 0);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0";
}

export function PlatformFoundationPanel() {
  const [bundle, setBundle] = useState<PlatformFoundationBundle>(emptyPlatformFoundationBundle);

  useEffect(() => {
    let active = true;
    fetchPlatformFoundationBundle().then((data) => {
      if (active) setBundle(data);
    });
    return () => {
      active = false;
    };
  }, []);

  const cards = [
    {
      title: "Trade Journal Persistence",
      status: "Ready",
      value: `${metric(readNumber(bundle.journalSummary, ["total_trades"], 0))} records`,
      detail: readText(bundle.journalSummary, ["message"], "No completed demo trades yet."),
      tone: "info" as const,
    },
    {
      title: "Strategy Analytics",
      status: "Derived",
      value: `${metric(readNumber(bundle.strategyOverview, ["closed_demo_trades"], 0))} closed`,
      detail: readText(bundle.strategyOverview, ["message"], "No completed demo trades yet."),
      tone: "info" as const,
    },
    {
      title: "Reports V2",
      status: "Waiting",
      value: "Empty",
      detail: readText(bundle.reportsStatus, ["message"], "Reports will populate after demo trades are recorded."),
      tone: "muted" as const,
    },
    {
      title: "Trade Copier Readiness",
      status: "Disabled",
      value: readText(bundle.copierReadiness, ["status"], "FUTURE_EXECUTION_REQUIRED").replaceAll("_", " "),
      detail: readText(bundle.copierReadiness, ["message"], "Trade copier is architecture-ready but execution-disabled."),
      tone: "warning" as const,
    },
  ];

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Platform Foundations</p>
          <h2 className="mt-1 text-xl font-bold text-white">Phase 18 Prep Surface</h2>
        </div>
        <StatusBadge label="Execution Disabled" tone="warning" />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <article className="min-h-36 rounded-2xl border border-white/10 bg-white/[0.035] p-4" key={card.title}>
            <div className="flex min-w-0 items-start justify-between gap-2">
              <strong className="break-words text-sm text-white">{card.title}</strong>
              <StatusBadge label={card.status} tone={card.tone} />
            </div>
            <p className="mt-3 break-words text-xl font-black leading-tight text-slate-100">{card.value}</p>
            <p className="mt-2 break-words text-xs leading-5 text-slate-400">{card.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
