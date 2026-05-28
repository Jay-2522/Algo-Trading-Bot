"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardAlertsPanel } from "./DashboardAlertsPanel";
import { DashboardSafetyBanner } from "./DashboardSafetyBanner";
import { DashboardStatusGrid } from "./DashboardStatusGrid";
import { fetchDashboardBundle, type DashboardBundle } from "../../lib/dashboard-api";

const emptyBundle: DashboardBundle = {
  status: null,
  overview: null,
  cards: [],
  summary: null,
  alerts: [],
};

export function DashboardShell() {
  const [bundle, setBundle] = useState<DashboardBundle>(emptyBundle);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextBundle = await fetchDashboardBundle();
      setBundle(nextBundle);
      setUpdatedAt(new Date().toLocaleTimeString());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Dashboard backend is unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
    const interval = window.setInterval(() => void loadDashboard(), 20000);
    return () => window.clearInterval(interval);
  }, [loadDashboard]);

  const cards = useMemo(
    () => (bundle.cards.length ? bundle.cards : bundle.overview?.cards ?? []),
    [bundle.cards, bundle.overview?.cards],
  );

  const alerts = bundle.alerts.length ? bundle.alerts : bundle.overview?.alerts ?? [];

  return (
    <main className="dashboardRoot">
      <section className="hero">
        <div>
          <p className="eyebrow">Client VPS Dashboard</p>
          <h1>AI Multi-Market Trading Bot</h1>
          <p className="subtitle">VPS Dashboard &amp; Simulation Control Center</p>
        </div>
        <div className="heroActions">
          <button className="refreshButton" type="button" onClick={() => void loadDashboard()}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
          <span className="lastUpdated">{updatedAt ? `Updated ${updatedAt}` : "Waiting for first refresh"}</span>
        </div>
      </section>

      <DashboardSafetyBanner />

      {error ? <div className="errorPanel">Backend dashboard data is unavailable: {error}</div> : null}

      <section className="summaryPanel">
        <div>
          <p className="eyebrow">Readiness Summary</p>
          <h2>{bundle.summary?.headline ?? "Dashboard backend context is loading."}</h2>
          <p>{bundle.summary?.summary ?? "Fetching current backend readiness, alerts, and safety status."}</p>
        </div>
        <div className="summaryStatus">
          <span>Phase 3</span>
          <strong>{bundle.summary?.phase3_status ?? bundle.status?.status ?? "Loading"}</strong>
        </div>
      </section>

      <DashboardStatusGrid cards={cards} />

      <DashboardAlertsPanel alerts={alerts} />

      <style jsx global>{`
        body {
          margin: 0;
          background: #07111f;
          color: #e5edf7;
          font-family:
            Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .dashboardRoot {
          min-height: 100vh;
          padding: 40px;
          background:
            radial-gradient(circle at top left, rgba(35, 120, 210, 0.22), transparent 32rem),
            linear-gradient(135deg, #07111f 0%, #0d1728 55%, #111827 100%);
        }

        .hero,
        .summaryPanel,
        .safetyBanner,
        .panel,
        .dashboardCard {
          border: 1px solid rgba(148, 163, 184, 0.22);
          background: rgba(15, 23, 42, 0.72);
          box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
          backdrop-filter: blur(16px);
          border-radius: 24px;
        }

        .hero {
          display: flex;
          justify-content: space-between;
          gap: 24px;
          padding: 32px;
          margin-bottom: 18px;
        }

        .eyebrow,
        .safetyLabel,
        .muted,
        .lastUpdated {
          color: #93a4b8;
          font-size: 0.82rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        h1,
        h2,
        p {
          margin: 0;
        }

        h1 {
          margin-top: 8px;
          font-size: clamp(2.2rem, 5vw, 4rem);
          letter-spacing: -0.05em;
        }

        h2 {
          font-size: 1.35rem;
          margin-bottom: 10px;
        }

        .subtitle {
          margin-top: 10px;
          color: #b8c4d4;
          font-size: 1.05rem;
        }

        .heroActions {
          display: flex;
          align-items: flex-end;
          flex-direction: column;
          gap: 10px;
        }

        .refreshButton {
          border: 0;
          border-radius: 999px;
          background: #38bdf8;
          color: #06111f;
          cursor: pointer;
          font-weight: 800;
          padding: 12px 20px;
        }

        .safetyBanner {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
          margin-bottom: 18px;
          padding: 18px;
        }

        .safetyBanner div {
          border-radius: 18px;
          background: rgba(21, 128, 61, 0.18);
          border: 1px solid rgba(74, 222, 128, 0.22);
          padding: 16px;
        }

        .safetyBanner strong {
          display: block;
          margin-top: 6px;
          color: #86efac;
          font-size: 1.1rem;
        }

        .summaryPanel {
          display: flex;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 18px;
          padding: 24px;
        }

        .summaryPanel p {
          color: #b8c4d4;
          line-height: 1.6;
        }

        .summaryStatus {
          min-width: 160px;
          border-radius: 18px;
          padding: 16px;
          background: rgba(56, 189, 248, 0.12);
          text-align: right;
        }

        .summaryStatus span {
          display: block;
          color: #93a4b8;
        }

        .summaryStatus strong {
          display: block;
          margin-top: 6px;
          color: #7dd3fc;
          font-size: 1.35rem;
        }

        .cardGrid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 18px;
          margin-bottom: 18px;
        }

        .dashboardCard {
          padding: 20px;
        }

        .cardTopline,
        .panelHeader {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .cardTitle {
          color: #cbd5e1;
          font-weight: 700;
        }

        .cardValue {
          margin: 22px 0 8px;
          color: #f8fafc;
          font-size: 1.8rem;
          font-weight: 800;
          overflow-wrap: anywhere;
        }

        .cardSubtitle {
          color: #9caabd;
          line-height: 1.4;
        }

        .statusBadge {
          border-radius: 999px;
          font-size: 0.72rem;
          font-weight: 800;
          padding: 6px 9px;
          text-transform: uppercase;
        }

        .badgeInfo {
          background: rgba(34, 197, 94, 0.16);
          color: #86efac;
        }

        .badgeWarning {
          background: rgba(245, 158, 11, 0.16);
          color: #fcd34d;
        }

        .badgeDanger {
          background: rgba(239, 68, 68, 0.16);
          color: #fca5a5;
        }

        .panel {
          padding: 24px;
        }

        .alertList {
          display: grid;
          gap: 10px;
          margin-top: 16px;
        }

        .alertItem,
        .emptyPanel,
        .errorPanel {
          border-radius: 16px;
          padding: 14px 16px;
          background: rgba(15, 23, 42, 0.9);
          color: #b8c4d4;
        }

        .alertItem {
          display: flex;
          justify-content: space-between;
          gap: 18px;
        }

        .errorPanel {
          border: 1px solid rgba(248, 113, 113, 0.3);
          margin-bottom: 18px;
          color: #fecaca;
        }

        @media (max-width: 1100px) {
          .cardGrid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 720px) {
          .dashboardRoot {
            padding: 20px;
          }

          .hero,
          .summaryPanel {
            flex-direction: column;
          }

          .safetyBanner,
          .cardGrid {
            grid-template-columns: 1fr;
          }

          .heroActions,
          .summaryStatus {
            align-items: flex-start;
            text-align: left;
          }
        }
      `}</style>
    </main>
  );
}
