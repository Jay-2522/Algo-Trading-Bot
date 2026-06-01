from typing import Any


class RecoveryRunbookService:
    """Read-only operational recovery guidance."""

    def get_mt5_recovery_steps(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "steps": [
                    "Capture current platform logs before changing MT5 state.",
                    "Restart MT5 manually on the VPS.",
                    "Confirm login is a demo account only.",
                    "Verify broker server and symbol visibility.",
                    "Enable AutoTrading only for guarded demo execution tests.",
                    "Check /monitoring/mt5 and /deployment/readiness.",
                ]
            }
        )

    def get_backend_recovery_steps(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "steps": [
                    "Run scripts/runtime_status.ps1.",
                    "Review logs/platform.log.",
                    "Start backend with scripts/restart_backend.ps1 if not running.",
                    "Verify /health, /deployment/status, and /monitoring/health.",
                ]
            }
        )

    def get_frontend_recovery_steps(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "steps": [
                    "Run npm run build inside frontend.",
                    "Start frontend with scripts/restart_frontend.ps1 if not running.",
                    "Open /dashboard and verify API connectivity.",
                ]
            }
        )

    def get_full_recovery_plan(self) -> dict[str, Any]:
        return self._safe_payload(
            {
                "backend": self.get_backend_recovery_steps()["steps"],
                "frontend": self.get_frontend_recovery_steps()["steps"],
                "mt5": self.get_mt5_recovery_steps()["steps"],
                "final_validation": [
                    "Run python tests/regression_routes_verification.py.",
                    "Run latest Phase 10 verification script.",
                    "Run npm run build in frontend.",
                    "Confirm live and broker execution flags remain false.",
                ],
            }
        )

    def _safe_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload.update(
            {
                "simulation_only": True,
                "demo_execution": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }
        )
        return payload
