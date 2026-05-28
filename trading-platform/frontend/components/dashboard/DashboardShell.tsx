"use client";

import { useMemo } from "react";

import { AccountStatusPanel } from "./AccountStatusPanel";
import { AutoRefreshControl } from "./AutoRefreshControl";
import { BrokerStatusPanel } from "./BrokerStatusPanel";
import { ControlAuditPanel } from "./ControlAuditPanel";
import { DashboardAlertsPanel } from "./DashboardAlertsPanel";
import { DashboardHeader } from "./DashboardHeader";
import { DashboardSafetyBanner } from "./DashboardSafetyBanner";
import { DashboardStatusGrid } from "./DashboardStatusGrid";
import { ExecutionSafetyPanel } from "./ExecutionSafetyPanel";
import { LiveActivityFeed } from "./LiveActivityFeed";
import { LiveAccountRoutingPanel } from "./LiveAccountRoutingPanel";
import { LiveBrokerPanel } from "./LiveBrokerPanel";
import { LiveExecutionQueuePanel } from "./LiveExecutionQueuePanel";
import { LiveMonitoringPanel } from "./LiveMonitoringPanel";
import { LiveWebhookPanel } from "./LiveWebhookPanel";
import { ManualControlPanel } from "./ManualControlPanel";
import { RecentSignalsPanel } from "./RecentSignalsPanel";
import { SafetyLockPanel } from "./SafetyLockPanel";
import { SystemEventStream } from "./SystemEventStream";
import { TradeLifecycleTimeline } from "./TradeLifecycleTimeline";
import { useDashboardData } from "@/hooks/useDashboardData";

export function DashboardShell() {
  const { bundle, loading, isPaused, lastUpdated, lastError, refresh, togglePause } = useDashboardData(10000);

  const cards = useMemo(
    () => (bundle.cards.length ? bundle.cards : bundle.overview?.cards ?? []),
    [bundle.cards, bundle.overview?.cards],
  );

  const alerts = bundle.alerts.length ? bundle.alerts : bundle.overview?.alerts ?? [];
  const backendHealthy = Boolean(bundle.status?.dashboard_ready) && bundle.errors.length === 0;

  return (
    <main className="min-h-screen overflow-hidden bg-[#07111f] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.2),transparent_32rem),radial-gradient(circle_at_80%_8%,rgba(20,184,166,0.14),transparent_28rem),linear-gradient(135deg,#06101d,#0f172a_54%,#0b1120)]" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-6 sm:px-6 lg:px-8">
        <DashboardHeader
          controls={
            <AutoRefreshControl
              isPaused={isPaused}
              lastUpdated={lastUpdated}
              loading={loading}
              onManualRefresh={() => void refresh()}
              onTogglePause={togglePause}
            />
          }
        />

        <DashboardSafetyBanner />

        {lastError || bundle.errors.length > 0 ? (
          <section className="rounded-3xl border border-rose-300/20 bg-rose-400/10 p-5 text-sm text-rose-100">
            <strong className="block text-base">Partial dashboard data unavailable</strong>
            {lastError ? <p className="mt-2">{lastError}</p> : null}
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {bundle.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-[1fr_20rem]">
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

          <div className="rounded-3xl border border-cyan-300/15 bg-cyan-300/10 p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-xs uppercase tracking-[0.24em] text-sky-200/70">Backend Readiness</p>
            <div className="mt-3 text-3xl font-black text-sky-100">
              {backendHealthy ? "Ready" : loading ? "Loading" : "Review"}
            </div>
            <p className="mt-3 text-sm leading-6 text-sky-50/75">
              {bundle.summary?.safety_status ?? "Simulation-only safety status is being checked."}
            </p>
          </div>
        </section>

        <DashboardStatusGrid cards={cards} loading={loading} />

        <section className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
          <ManualControlPanel
            alerts={alerts}
            onActionComplete={() => refresh()}
            queueItems={bundle.queueItems}
            safetyState={bundle.safetyState}
          />
          <SafetyLockPanel safetyState={bundle.safetyState} />
        </section>

        <ControlAuditPanel events={bundle.controlAuditEvents} />

        <section className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          <LiveBrokerPanel brokerStatus={bundle.brokerStatus} observationStatus={bundle.brokerObservationStatus} />
          <LiveAccountRoutingPanel accountStatus={bundle.accountStatus} allocationStatus={bundle.allocationStatus} />
          <LiveExecutionQueuePanel executionStatus={bundle.executionStatus} lifecycleStatus={bundle.lifecycleStatus} />
          <LiveWebhookPanel webhookStatus={bundle.webhookStatus} orchestrationStatus={bundle.webhookOrchestrationStatus} />
          <LiveMonitoringPanel alerts={alerts} phase3Status={bundle.phase3Status} />
        </section>

        <TradeLifecycleTimeline
          lifecycleAuditEvents={bundle.lifecycleAuditEvents}
          orchestrationDecisions={bundle.orchestrationDecisions}
          queueItems={bundle.queueItems}
          webhookEvents={bundle.webhookEvents}
        />

        <section className="grid gap-4 xl:grid-cols-[1.35fr_0.95fr]">
          <LiveActivityFeed
            lifecycleAuditEvents={bundle.lifecycleAuditEvents}
            orchestrationDecisions={bundle.orchestrationDecisions}
            queueItems={bundle.queueItems}
            securityEvents={bundle.webhookSecurityEvents}
            webhookEvents={bundle.webhookEvents}
          />
          <RecentSignalsPanel webhookEvents={bundle.webhookEvents} />
        </section>

        <SystemEventStream
          alerts={alerts}
          lifecycleAuditEvents={bundle.lifecycleAuditEvents}
          orchestrationDecisions={bundle.orchestrationDecisions}
          securityEvents={bundle.webhookSecurityEvents}
        />

        <section className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
          <div className="min-w-0">
            <BrokerStatusPanel status={bundle.brokerStatus} />
          </div>
          <div className="min-w-0">
            <AccountStatusPanel status={bundle.accountStatus} />
          </div>
          <div className="min-w-0 lg:col-span-2 2xl:col-span-1">
            <ExecutionSafetyPanel status={bundle.executionStatus} />
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1fr_22rem]">
          <DashboardAlertsPanel alerts={alerts} />
          <div className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Phase 3 Readiness</p>
            <h2 className="mt-1 text-xl font-bold text-white">{String(bundle.phase3Status?.overall_status ?? "Loading")}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Full signal-to-simulation pipeline, safety audit, broker readiness, routing, allocation, queue, and monitoring context.
            </p>
            <div className="mt-4 rounded-2xl border border-emerald-300/15 bg-emerald-300/10 p-3 text-xs text-emerald-100">
              Live execution remains disabled.
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
