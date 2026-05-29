# Dashboard Data Source Audit

This audit records the backend source of truth for dashboard status and score fields.

| Displayed metric | Source endpoint | Source service | Value source |
| --- | --- | --- | --- |
| System Status | `/dashboard/status` | `DashboardStateProvider` | Derived from Phase 3 readiness, monitoring status, active alerts, and safety flags. |
| Backend Readiness | `/dashboard/status` | `DashboardStateProvider` | `READY` only when shared dashboard state is client-demo ready. |
| Platform Health | `/dashboard/status` | `DashboardStateProvider` | Shared health score used by platform, operational, and execution health views. |
| Operational Health | `/operational-intelligence/health-summary` | `OperationalIntelligenceService` | Consumes the shared platform health score and adds module/warning counts. |
| Execution Health | `/execution-dashboard/overview` | `ExecutionDashboardService` | Consumes the shared platform health score and adds execution subsystem statuses. |
| Client Readiness | `/client-acceptance/readiness` | `DeliveryReadinessService` | Delivery checklist score derived from shared demo-ready state plus production deployment gate. |
| Phase 3 Readiness | `/phase3/status` | `Phase3ReadinessService` | Route audit, pipeline validation, and safety audit. `FAILED` appears only on actual validation failure. |
| Dashboard Warnings | `/operational-intelligence/warnings` | `WarningEngine` | Generated from module `WARNING`/`FAILED` states; safety and pending integration notes are informational. |

No dashboard health score is hardcoded. Demo-safe production gaps such as VPS deployment and Indian broker integration remain readiness gates, not platform-health failures.

