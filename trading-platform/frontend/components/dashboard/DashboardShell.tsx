"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardAlertsPanel } from "./DashboardAlertsPanel";
import { DashboardSafetyBanner } from "./DashboardSafetyBanner";
import { DashboardStatusGrid } from "./DashboardStatusGrid";
import { fetchDashboardBundle, type DashboardBundle } from "@/lib/dashboard-api";

const emptyBundle: DashboardBundle = {
  status: null,
  overview: null,
  cards: [],
  summary: null,
  alerts: [],
  errors: [],
};

export function DashboardShell() {
  const [bundle, setBundle] = useState<DashboardBundle>(emptyBundle);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    const nextBundle = await fetchDashboardBundle();
    setBundle(nextBundle);
    setLastUpdated(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    setLoading(false);
  }, []);

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void loadDashboard(), 0);
    const interval = window.setInterval(() => void loadDashboard(), 20000);
    return () => {
      window.clearTimeout(initialRefresh);
      window.clearInterval(interval);
    };
  }, [loadDashboard]);

  const cards = useMemo(
    () => (bundle.cards.length ? bundle.cards : bundle.overview?.cards ?? []),
    [bundle.cards, bundle.overview?.cards],
  );

  const alerts = bundle.alerts.length ? bundle.alerts : bundle.overview?.alerts ?? [];
  const backendHealthy = Boolean(bundle.status?.dashboard_ready) && bundle.errors.length === 0;

  return (
    <main className="min-h-screen overflow-hidden bg-[#07111f] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.22),transparent_34rem),radial-gradient(circle_at_80%_10%,rgba(16,185,129,0.16),transparent_28rem),linear-gradient(135deg,#07111f,#0f172a_55%,#111827)]" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 py-8 sm:px-8 lg:px-10">
        <section className="rounded-[2rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl md:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300/80">
                Client VPS Dashboard
              </p>
              <h1 className="mt-3 max-w-4xl text-4xl font-black tracking-[-0.05em] text-white sm:text-6xl">
                AI Multi-Market Trading Bot
              </h1>
              <p className="mt-4 text-lg text-slate-300">VPS Dashboard &amp; Simulation Control Center</p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center lg:flex-col lg:items-end">
              <button
                className="rounded-full bg-sky-300 px-5 py-3 text-sm font-black text-slate-950 shadow-lg shadow-sky-950/30 transition hover:bg-sky-200 disabled:cursor-wait disabled:opacity-70"
                disabled={loading}
                onClick={() => void loadDashboard()}
                type="button"
              >
                {loading ? "Refreshing..." : "Refresh Dashboard"}
              </button>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                {lastUpdated ? `Updated ${lastUpdated}` : "Waiting for first refresh"}
              </p>
            </div>
          </div>
        </section>

        <DashboardSafetyBanner />

        {bundle.errors.length > 0 ? (
          <section className="rounded-3xl border border-rose-300/20 bg-rose-400/10 p-5 text-sm text-rose-100">
            <strong className="block text-base">Partial dashboard data unavailable</strong>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {bundle.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="grid gap-5 lg:grid-cols-[1fr_22rem]">
          <div className="rounded-3xl border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Readiness Summary</p>
            <h2 className="mt-2 text-2xl font-bold text-white">
              {bundle.summary?.headline ?? "Dashboard backend context is loading."}
            </h2>
            <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-300">
              {bundle.summary?.summary ??
                "Fetching current backend readiness, alerts, broker context, webhook intake, and execution queue status."}
            </p>
          </div>

          <div className="rounded-3xl border border-sky-300/15 bg-sky-300/10 p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-xs uppercase tracking-[0.24em] text-sky-200/70">Backend Readiness</p>
            <div className="mt-3 text-4xl font-black text-sky-100">
              {backendHealthy ? "Ready" : loading ? "Loading" : "Review"}
            </div>
            <p className="mt-3 text-sm leading-6 text-sky-50/75">
              {bundle.summary?.safety_status ?? "Simulation-only safety status is being checked."}
            </p>
          </div>
        </section>

        <DashboardStatusGrid cards={cards} loading={loading} />

        <DashboardAlertsPanel alerts={alerts} />
      </div>
    </main>
  );
}
