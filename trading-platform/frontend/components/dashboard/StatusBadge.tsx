type StatusTone = "good" | "info" | "warning" | "danger" | "muted";

const toneClass: Record<StatusTone, string> = {
  good: "border-emerald-300/20 bg-emerald-300/10 text-emerald-100",
  info: "border-sky-300/20 bg-sky-300/10 text-sky-100",
  warning: "border-amber-300/25 bg-amber-300/10 text-amber-100",
  danger: "border-rose-300/25 bg-rose-300/10 text-rose-100",
  muted: "border-slate-500/25 bg-slate-500/10 text-slate-200",
};

export function StatusBadge({ label, tone = "info" }: { label: string; tone?: StatusTone }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[0.65rem] font-black uppercase tracking-[0.18em] ${toneClass[tone]}`}>
      {label}
    </span>
  );
}
