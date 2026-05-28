const safetyItems = [
  { label: "Simulation Only", value: "Active" },
  { label: "Live Execution", value: "Disabled" },
  { label: "Broker Orders", value: "Not Placed" },
];

export function DashboardSafetyBanner() {
  return (
    <section className="grid gap-3 rounded-3xl border border-emerald-300/20 bg-[linear-gradient(135deg,rgba(16,185,129,0.14),rgba(15,23,42,0.62))] p-3 shadow-2xl shadow-emerald-950/10 backdrop-blur-xl md:grid-cols-3">
      {safetyItems.map((item) => (
        <div
          className="rounded-2xl border border-emerald-300/15 bg-slate-950/35 px-4 py-3"
          key={item.label}
        >
          <p className="text-xs uppercase tracking-[0.22em] text-emerald-100/70">{item.label}</p>
          <strong className="mt-2 block text-lg text-emerald-100">{item.value}</strong>
        </div>
      ))}
    </section>
  );
}
