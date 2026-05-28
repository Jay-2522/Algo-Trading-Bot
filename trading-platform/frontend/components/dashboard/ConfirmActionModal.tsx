"use client";

type ConfirmActionModalProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmActionModal({
  open,
  title,
  description,
  confirmLabel,
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmActionModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg overflow-hidden rounded-3xl border border-white/10 bg-slate-950 p-6 shadow-2xl shadow-black/50">
        <p className="text-[0.68rem] uppercase tracking-[0.22em] text-slate-500">Confirm Simulation Control</p>
        <h2 className="mt-2 break-words text-2xl font-black leading-tight text-white">{title}</h2>
        <p className="mt-3 break-words text-sm leading-7 text-slate-300">{description}</p>
        <div className="mt-4 rounded-2xl border border-emerald-300/15 bg-emerald-300/10 p-3 text-xs leading-6 text-emerald-100">
          This action affects simulation and dashboard state only. Live broker execution remains disabled.
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            className="rounded-2xl border border-white/10 px-4 py-2 text-sm font-bold text-slate-200 transition hover:bg-white/10 disabled:opacity-60"
            disabled={busy}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
          <button
            className={`rounded-2xl border px-4 py-2 text-sm font-black text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${
              danger
                ? "border-rose-300/30 bg-rose-500/20 hover:bg-rose-500/30"
                : "border-cyan-300/30 bg-cyan-400/20 hover:bg-cyan-400/30"
            }`}
            disabled={busy}
            onClick={onConfirm}
            type="button"
          >
            {busy ? "Working..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
