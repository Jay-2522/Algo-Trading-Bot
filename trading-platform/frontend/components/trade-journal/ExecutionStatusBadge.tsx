import type { ExecutionStatus } from "@/lib/tradeJournalApi";

const toneClass: Record<string, string> = {
  complete: "border-emerald-300/20 bg-emerald-300/10 text-emerald-100",
  pending: "border-amber-300/25 bg-amber-300/10 text-amber-100",
  blocked: "border-rose-300/25 bg-rose-300/10 text-rose-100",
  unavailable: "border-slate-500/25 bg-slate-500/10 text-slate-200",
};

function toneFor(status: string): keyof typeof toneClass {
  const normalized = status.toUpperCase();
  if (["DEMO_FILLED", "COPIED", "APPROVED", "QUEUED", "COMPLETE", "COMPLETED"].includes(normalized)) return "complete";
  if (["WAIT", "PENDING"].includes(normalized)) return "pending";
  if (normalized.includes("BLOCK") || normalized.includes("REJECT") || normalized.includes("FAILED") || normalized.includes("UNAVAILABLE")) return "blocked";
  return "unavailable";
}

export function ExecutionStatusBadge({ status }: { status: ExecutionStatus | string }) {
  const tone = toneFor(status);
  return (
    <span className={`inline-flex max-w-full rounded-full border px-2.5 py-1 text-[0.6rem] font-black uppercase tracking-[0.12em] ${toneClass[tone]}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
