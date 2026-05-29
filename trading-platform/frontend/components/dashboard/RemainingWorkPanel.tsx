export function RemainingWorkPanel({ items }: { items: string[] }) {
  const fallback = [
    "MT5 Demo Execution Bridge",
    "Multi-Account Trade Copier",
    "Execution Confirmation Tracking",
    "VPS Deployment",
    "Indian Broker Integration",
  ];
  const visibleItems = items.length ? items : fallback;

  return (
    <section className="rounded-3xl border border-amber-300/15 bg-amber-300/[0.06] p-5 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <p className="text-[0.68rem] uppercase tracking-[0.22em] text-amber-100/70">Remaining Work</p>
      <h3 className="mt-1 text-xl font-black text-white">Next Delivery Items</h3>
      <ul className="mt-4 space-y-3">
        {visibleItems.map((item) => (
          <li className="flex min-w-0 gap-3 text-sm leading-6 text-amber-50/80" key={item}>
            <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-amber-300" />
            <span className="break-words">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
