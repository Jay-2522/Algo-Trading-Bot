import type { ReadinessItem } from "@/lib/executiveDashboardApi";

function tone(status: string): string {
  const value = status.toUpperCase();
  if (value.includes("READY")) return "border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-100";
  if (value.includes("PENDING")) return "border-amber-300/20 bg-amber-300/[0.08] text-amber-100";
  return "border-cyan-300/20 bg-cyan-300/[0.08] text-cyan-100";
}

export function SystemReadinessCards({ items }: { items: ReadinessItem[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-9">
      {items.map((item) => (
        <article className={`min-h-32 rounded-2xl border p-4 ${tone(item.status)}`} key={item.name}>
          <p className="text-[0.62rem] font-black uppercase tracking-[0.16em] opacity-70">{item.name}</p>
          <strong className="mt-3 block break-words text-lg">{item.status.replaceAll("_", " ")}</strong>
          <p className="mt-2 text-sm font-black text-white">{Math.round(item.score)}%</p>
          <p className="mt-1 text-[0.6rem] uppercase tracking-[0.1em] opacity-70">Readiness score</p>
        </article>
      ))}
    </div>
  );
}
