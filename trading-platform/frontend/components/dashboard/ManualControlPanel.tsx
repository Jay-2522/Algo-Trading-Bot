"use client";

import { useMemo, useState } from "react";

import {
  acknowledgeMonitoringAlert,
  cancelSimulationQueueItem,
  emergencyStopPlaceholder,
  pauseSimulationQueue,
  resumeSimulationQueue,
} from "@/lib/dashboard-api";
import { readText } from "@/lib/dashboard-formatters";

import { ConfirmActionModal } from "./ConfirmActionModal";
import { StatusBadge } from "./StatusBadge";

type PendingAction = {
  key: "pause" | "resume" | "cancel" | "acknowledge" | "emergency";
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
};

type ManualControlPanelProps = {
  safetyState: Record<string, unknown> | null;
  queueItems: Array<Record<string, unknown>>;
  alerts: Array<Record<string, unknown>>;
  onActionComplete: () => Promise<void> | void;
};

function getFirstQueueId(items: Array<Record<string, unknown>>): string | null {
  for (const item of items) {
    const status = readText(item, ["status"], "");
    const queueId = readText(item, ["queue_id"], "");
    if (queueId && !status.toUpperCase().includes("CANCEL")) {
      return queueId;
    }
  }
  return null;
}

function getFirstAlertId(alerts: Array<Record<string, unknown>>): string | null {
  for (const alert of alerts) {
    if (alert.acknowledged === true) {
      continue;
    }
    const alertId = readText(alert, ["alert_id"], "");
    if (alertId) {
      return alertId;
    }
  }
  return null;
}

export function ManualControlPanel({ safetyState, queueItems, alerts, onActionComplete }: ManualControlPanelProps) {
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const queuePaused = safetyState?.queue_paused === true;
  const queueId = useMemo(() => getFirstQueueId(queueItems), [queueItems]);
  const alertId = useMemo(() => getFirstAlertId(alerts), [alerts]);

  async function runAction() {
    if (!pendingAction) {
      return;
    }

    setBusy(true);
    setResult(null);
    try {
      const reason = `${pendingAction.title} requested from VPS dashboard manual control panel.`;
      let response: Record<string, unknown>;
      if (pendingAction.key === "pause") {
        response = await pauseSimulationQueue(reason);
      } else if (pendingAction.key === "resume") {
        response = await resumeSimulationQueue(reason);
      } else if (pendingAction.key === "cancel" && queueId) {
        response = await cancelSimulationQueueItem(queueId, reason);
      } else if (pendingAction.key === "acknowledge" && alertId) {
        response = await acknowledgeMonitoringAlert(alertId, reason);
      } else {
        response = await emergencyStopPlaceholder(reason);
      }
      setResult(readText(response, ["message"], "Control action completed safely."));
      setPendingAction(null);
      await onActionComplete();
    } catch (exc) {
      setResult(exc instanceof Error ? exc.message : "Manual control action failed safely.");
    } finally {
      setBusy(false);
    }
  }

  const actions: Array<PendingAction & { disabled?: boolean; badge: string }> = [
    {
      key: "pause",
      title: "Pause Simulation Queue",
      description: "Pause simulated queue processing for operator review. No broker orders exist behind this control.",
      confirmLabel: "Pause Simulation Queue",
      disabled: queuePaused,
      badge: queuePaused ? "Paused" : "Available",
    },
    {
      key: "resume",
      title: "Resume Simulation Queue",
      description: "Resume simulated queue processing after operator review. This does not activate live execution.",
      confirmLabel: "Resume Simulation Queue",
      disabled: !queuePaused,
      badge: queuePaused ? "Available" : "Idle",
    },
    {
      key: "cancel",
      title: "Cancel Latest Queued Simulation Item",
      description: "Cancel the latest queued simulation item. The item is marked cancelled in the safe queue only.",
      confirmLabel: "Cancel Queue Item",
      disabled: !queueId,
      badge: queueId ? "Ready" : "No queue",
      danger: true,
    },
    {
      key: "acknowledge",
      title: "Acknowledge Latest Alert",
      description: "Acknowledge the latest monitoring alert so the audit trail records operator review.",
      confirmLabel: "Acknowledge Alert",
      disabled: !alertId,
      badge: alertId ? "Ready" : "No alerts",
    },
    {
      key: "emergency",
      title: "Emergency Stop Placeholder",
      description: "Record an emergency stop placeholder for future execution phases. This cannot place or cancel real broker orders.",
      confirmLabel: "Record Placeholder",
      badge: "Placeholder",
      danger: true,
    },
  ];

  return (
    <section className="min-w-0 rounded-3xl border border-cyan-300/15 bg-slate-950/60 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="break-words text-[0.68rem] uppercase leading-relaxed tracking-[0.2em] text-cyan-100/70">Manual Controls</p>
          <h2 className="mt-1 break-words text-xl font-black leading-relaxed text-white">Simulation Safety Control Panel</h2>
          <p className="mt-2 max-w-3xl break-words text-sm leading-6 text-slate-400">
            Operator controls are wired to safe backend state only. They can pause, resume, cancel previews, acknowledge alerts, and record a future emergency stop placeholder.
          </p>
        </div>
        <StatusBadge label="Simulation only" tone="good" />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {actions.map((action) => (
          <button
            className={`min-h-32 min-w-0 rounded-2xl border p-4 text-left transition ${
              action.disabled
                ? "cursor-not-allowed border-white/5 bg-white/[0.02] opacity-55"
                : action.danger
                  ? "border-rose-300/20 bg-rose-300/[0.07] hover:bg-rose-300/[0.11]"
                  : "border-white/10 bg-white/[0.04] hover:bg-white/[0.07]"
            }`}
            disabled={action.disabled || busy}
            key={action.key}
            onClick={() => setPendingAction(action)}
            type="button"
          >
            <span className="inline-flex max-w-full rounded-full border border-white/10 bg-slate-950/40 px-2 py-1 text-[0.58rem] font-black uppercase tracking-[0.12em] text-slate-300">
              {action.badge}
            </span>
            <strong className="mt-3 block break-words text-sm leading-relaxed text-white">{action.title}</strong>
            <span className="mt-2 block break-words text-xs leading-5 text-slate-400">{action.description}</span>
          </button>
        ))}
      </div>

      {result ? (
        <div className="mt-4 rounded-2xl border border-sky-300/15 bg-sky-300/10 p-3 text-sm leading-6 text-sky-100">{result}</div>
      ) : null}

      <ConfirmActionModal
        busy={busy}
        confirmLabel={pendingAction?.confirmLabel ?? "Confirm"}
        danger={pendingAction?.danger}
        description={pendingAction?.description ?? ""}
        onCancel={() => setPendingAction(null)}
        onConfirm={() => void runAction()}
        open={Boolean(pendingAction)}
        title={pendingAction?.title ?? "Confirm Action"}
      />
    </section>
  );
}
