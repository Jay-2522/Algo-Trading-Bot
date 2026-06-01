from pathlib import Path

from backend.deployment.runtime_audit_store import RuntimeAuditStore
from backend.deployment.runtime_models import VPSRuntimeStatus
from backend.deployment.service_health_checker import ServiceHealthChecker


class RuntimeManager:
    """Read-only VPS runtime manager. Scripts perform manual starts/restarts."""

    def __init__(
        self,
        project_root: Path | None = None,
        health_checker: ServiceHealthChecker | None = None,
        audit_store: RuntimeAuditStore | None = None,
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.health_checker = health_checker or ServiceHealthChecker()
        self.audit_store = audit_store or RuntimeAuditStore()

    def get_runtime_status(self) -> VPSRuntimeStatus:
        backend = self.get_backend_status()
        frontend = self.get_frontend_status()
        service_management_ready = self.get_service_management_status()["service_management_ready"]
        healthcheck_ready = (self.project_root / "scripts" / "vps_healthcheck.ps1").exists()
        runtime_ready = backend.running
        warnings = [*backend.warnings, *frontend.warnings]
        if not healthcheck_ready:
            warnings.append("VPS healthcheck script is not present.")
        if not service_management_ready:
            warnings.append("Runtime service management scripts or docs are not ready.")
        if backend.running and service_management_ready and healthcheck_ready:
            status = "READY_FOR_VPS_RUNTIME"
        elif backend.running:
            status = "READY_FOR_LOCAL_RUNTIME"
        elif service_management_ready and healthcheck_ready:
            status = "WARNING"
        else:
            status = "BLOCKED"

        result = VPSRuntimeStatus(
            status=status,
            backend_service=backend,
            frontend_service=frontend,
            mt5_terminal_required=True,
            runtime_ready=runtime_ready,
            service_management_ready=service_management_ready,
            healthcheck_ready=healthcheck_ready,
            warnings=warnings,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        self.audit_store.store_event(
            {
                "event_type": "RUNTIME_STATUS_CHECK",
                "message": "Read-only runtime status checked.",
                "metadata": {"status": result.status, "backend_running": backend.running, "frontend_running": frontend.running},
            }
        )
        return result

    def get_backend_status(self):
        return self.health_checker.check_backend()

    def get_frontend_status(self):
        return self.health_checker.check_frontend()

    def get_mt5_runtime_notes(self) -> dict:
        return {
            "mt5_terminal_required": True,
            "manual_install_required": True,
            "demo_account_required": True,
            "autotrading_demo_only_note": "AutoTrading is required only for guarded MT5 demo execution tests.",
            "live_trading_disabled": True,
            "broker_execution_enabled": False,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "warnings": ["Install and login to MT5 manually on the VPS. Use demo accounts only."],
        }

    def get_service_management_status(self) -> dict:
        scripts = [
            "runtime_status.ps1",
            "restart_backend.ps1",
            "restart_frontend.ps1",
            "restart_all.ps1",
            "vps_healthcheck.ps1",
        ]
        docs = [
            "vps-runtime-guide.md",
            "windows-vps-service-guide.md",
            "linux-vps-service-guide.md",
        ]
        scripts_ready = all((self.project_root / "scripts" / script).exists() for script in scripts)
        docs_ready = all((self.project_root / "docs" / doc).exists() for doc in docs)
        return {
            "service_management_ready": scripts_ready and docs_ready,
            "runtime_scripts_ready": scripts_ready,
            "runtime_docs_ready": docs_ready,
            "api_process_control_enabled": False,
            "manual_scripts_only": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def list_audit_events(self, limit: int = 100) -> list[dict]:
        return self.audit_store.list_events(limit)
