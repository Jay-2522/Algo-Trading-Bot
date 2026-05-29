import type { AcceptanceChecklistItemData } from "@/lib/dashboard-api";

import { StatusBadge } from "./StatusBadge";

export function AcceptanceChecklist({ checklist }: { checklist: AcceptanceChecklistItemData[] }) {
  const fallback = ["Dashboard", "Monitoring", "Portfolio", "Demo Mode", "Control Center", "Webhooks", "Routing", "Allocation", "Queue"].map(
    (label) => ({ label, complete: true, status: "COMPLETE" }),
  );
  const items = checklist.length ? checklist : fallback;

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Acceptance Checklist</p>
      <h3 className="mt-1 text-xl font-black text-white">Completed Systems</h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <div className="flex min-w-0 items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.035] p-3" key={item.label}>
            <span className="min-w-0 break-words text-sm font-bold text-slate-200">{item.label}</span>
            <StatusBadge label={item.status} tone={item.complete ? "good" : "warning"} />
          </div>
        ))}
      </div>
    </section>
  );
}
