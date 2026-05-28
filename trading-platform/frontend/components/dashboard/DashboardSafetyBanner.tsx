const safetyItems = [
  { label: "Simulation Only", value: "Active" },
  { label: "Live Execution", value: "Disabled" },
  { label: "Broker Orders", value: "Not Placed" },
];

export function DashboardSafetyBanner() {
  return (
    <section className="grid gap-3 rounded-3xl border border-emerald-300/20 bg-emerald-400/10 p-4 shadow-2xl shadow-emerald-950/20 backdrop-blur-xl md:grid-cols-3">
      {safetyItems.map((item) => (
        <div
          className="rounded-2xl border border-emerald-300/15 bg-slate-950/35 px-5 py-4"
          key={item.label}
        >
          <p className="text-xs uppercase tracking-[0.22em] text-emerald-100/70">{item.label}</p>
          <strong className="mt-2 block text-lg text-emerald-100">{item.value}</strong>
        </div>
      ))}
    </section>
  );
}
