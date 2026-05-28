import {
  formatRelativeTime,
  normalizeAuditEvent,
  normalizeDecisionEvent,
  normalizeQueueEvent,
  normalizeSecurityEvent,
  normalizeStatus,
  normalizeWebhookEvent,
  type ActivityEvent,
  type NormalizedStatus,
} from "@/lib/dashboard-formatters";
import { StatusBadge } from "./StatusBadge";

const dotClass: Record<NormalizedStatus, string> = {
  completed: "bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.7)]",
  pending: "bg-sky-300 shadow-[0_0_18px_rgba(125,211,252,0.55)]",
  rejected: "bg-rose-300 shadow-[0_0_18px_rgba(253,164,175,0.6)]",
  warning: "bg-amber-300 shadow-[0_0_18px_rgba(252,211,77,0.55)]",
  info: "bg-slate-400",
};

const tone: Record<NormalizedStatus, "good" | "info" | "warning" | "danger" | "muted"> = {
  completed: "good",
  pending: "info",
  rejected: "danger",
  warning: "warning",
  info: "muted",
};

function sortEvents(events: ActivityEvent[]): ActivityEvent[] {
  return [...events].sort((a, b) => new Date(b.timestamp ?? 0).getTime() - new Date(a.timestamp ?? 0).getTime());
}

export function LiveActivityFeed({
  webhookEvents,
  orchestrationDecisions,
  queueItems,
  lifecycleAuditEvents,
  securityEvents,
}: {
  webhookEvents: Array<Record<string, unknown>>;
  orchestrationDecisions: Array<Record<string, unknown>>;
  queueItems: Array<Record<string, unknown>>;
  lifecycleAuditEvents: Array<Record<string, unknown>>;
  securityEvents: Array<Record<string, unknown>>;
}) {
  const events = sortEvents([
    ...webhookEvents.map(normalizeWebhookEvent),
    ...orchestrationDecisions.map(normalizeDecisionEvent),
    ...queueItems.map(normalizeQueueEvent),
    ...lifecycleAuditEvents.map(normalizeAuditEvent),
    ...securityEvents.map(normalizeSecurityEvent),
  ]).slice(0, 12);

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-slate-500">Operations Stream</p>
          <h2 className="mt-1 break-words text-xl font-bold text-white">Live Activity Feed</h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-100">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(110,231,183,0.8)]" />
          Polling every 10s
        </div>
      </div>

      {events.length === 0 ? (
        <div className="mt-5 rounded-2xl border border-dashed border-slate-700 bg-white/[0.03] p-5">
          <strong className="text-sm text-slate-100">No simulated activity yet</strong>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">
            Webhook events, orchestration decisions, allocation previews, queue lifecycle events, and security events will appear here once generated.
          </p>
        </div>
      ) : (
        <div className="mt-5 grid gap-3">
          {events.map((event, index) => {
            const status = normalizeStatus(event.status);
            return (
              <article
                className="group flex gap-3 rounded-2xl border border-white/10 bg-white/[0.035] p-4 transition hover:border-cyan-200/25 hover:bg-white/[0.055]"
                key={`${event.id}-${index}`}
              >
                <div className="pt-1">
                  <span className={`block h-3 w-3 rounded-full ${dotClass[status]}`} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="break-words text-sm font-bold leading-relaxed text-white">{event.title}</p>
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{event.category}</p>
                    </div>
                    <StatusBadge label={event.status} tone={tone[status]} />
                  </div>
                  <p className="mt-2 break-words text-sm leading-relaxed text-slate-400">{event.detail}</p>
                  <p className="mt-2 text-xs text-slate-500">{formatRelativeTime(event.timestamp)}</p>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
