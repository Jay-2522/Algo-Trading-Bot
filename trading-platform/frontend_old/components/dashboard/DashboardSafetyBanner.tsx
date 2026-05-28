export function DashboardSafetyBanner() {
  return (
    <section className="safetyBanner" aria-label="Dashboard safety status">
      <div>
        <span className="safetyLabel">Simulation Only</span>
        <strong>Active</strong>
      </div>
      <div>
        <span className="safetyLabel">Live Execution</span>
        <strong>Disabled</strong>
      </div>
      <div>
        <span className="safetyLabel">Broker Orders</span>
        <strong>Not Placed</strong>
      </div>
    </section>
  );
}
