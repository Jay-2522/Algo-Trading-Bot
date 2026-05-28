export function DashboardAlertsPanel({ alerts }: { alerts: Array<Record<string, unknown>> }) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <h2>Monitoring Alerts</h2>
        <span className="muted">{alerts.length} active / recent</span>
      </div>
      {alerts.length === 0 ? (
        <div className="emptyPanel">No monitoring alerts are currently reported.</div>
      ) : (
        <div className="alertList">
          {alerts.slice(0, 6).map((alert, index) => (
            <div className="alertItem" key={String(alert.alert_id ?? index)}>
              <strong>{String(alert.title ?? alert.severity ?? "Alert")}</strong>
              <span>{String(alert.message ?? "Monitoring event detected.")}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
