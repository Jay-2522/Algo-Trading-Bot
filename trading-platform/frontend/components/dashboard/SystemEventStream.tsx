import {
  formatRelativeTime,
  normalizeAuditEvent,
  normalizeDecisionEvent,
  normalizeSecurityEvent,
  normalizeStatus,
  type ActivityEvent,
} from "@/lib/dashboard-formatters";
import { StatusBadge } from "./StatusBadge";

function alertToEvent(alert: Record<string, unknown>, index: number): ActivityEvent {
  const title = typeof alert.title === "string" ? alert.title : "Monitoring alert";
  return {
    id: typeof alert.alert_id === "string" ? alert.alert_id : `alert-${index}`,
    category: "Monitoring",
    title,
    detail: typeof alert.message === "string" ? alert.message : "Monitoring event",
    status: normalizeStatus(alert.severity),
    timestamp: typeof alert.timestamp === "string" ? alert.timestamp : null,
  };
}

export function SystemEventStream({
  alerts,
  lifecycleAuditEvents,
  orchestrationDecisions,
  securityEvents,
}: {
  alerts: Array<Record<string, unknown>>;
  lifecycleAuditEvents: Array<Record<string, unknown>>;
  orchestrationDecisions: Array<Record<string, unknown>>;
  securityEvents: Array<Record<string, unknown>>;
}) {
  const events = [
    ...alerts.map(alertToEvent),
    ...lifecycleAuditEvents.map(normalizeAuditEvent),
    ...orchestrationDecisions.map(normalizeDecisionEvent),
    ...securityEvents.map(normalizeSecurityEvent),
  ].slice(0, 10);

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">System Stream</p>
          <h2 className="mt-1 text-xl font-bold text-white">System Event Stream</h2>
        </div>
        <StatusBadge label={`${events.length} events`} tone={events.length ? "info" : "muted"} />
      </div>

      {events.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-700 bg-white/[0.03] p-5">
          <strong className="text-sm text-slate-100">No active system events</strong>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Monitoring alerts, broker state changes, webhook security events, and orchestration events will stream here.
          </p>
        </div>
      ) : (
        <div className="mt-5 grid gap-3">
          {events.map((event, index) => (
            <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-4" key={`${event.id}-${index}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <strong className="break-words text-sm text-white">{event.title}</strong>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{event.category}</p>
                </div>
                <StatusBadge label={event.status} tone={event.status === "rejected" ? "danger" : "info"} />
              </div>
              <p className="mt-2 break-words text-sm leading-relaxed text-slate-400">{event.detail}</p>
              <p className="mt-2 text-xs text-slate-500">{formatRelativeTime(event.timestamp)}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
