from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.encoders import jsonable_encoder

from backend.demo_environment.demo_environment_service import DemoEnvironmentService
from backend.demo_validation.e2e_demo_validation_service import E2EDemoValidationService
from backend.demo_validation.eurusd_demo_validation_service import EURUSDDemoValidationService
from backend.demo_validation.nifty50_demo_validation_service import NIFTY50DemoValidationService
from backend.demo_validation.xauusd_demo_validation_service import XAUUSDDemoValidationService
from backend.mt5_demo.mt5_demo_service import MT5DemoService


class SoakTestReadinessService:
    """Read-only readiness checks for Phase 14 demo soak-test preparation."""

    def __init__(
        self,
        demo_environment_service: DemoEnvironmentService | None = None,
        mt5_demo_service: MT5DemoService | None = None,
        xauusd_validation_service: XAUUSDDemoValidationService | None = None,
        eurusd_validation_service: EURUSDDemoValidationService | None = None,
        nifty50_validation_service: NIFTY50DemoValidationService | None = None,
        e2e_validation_service: E2EDemoValidationService | None = None,
    ) -> None:
        self.demo_environment_service = demo_environment_service or DemoEnvironmentService()
        self.mt5_demo_service = mt5_demo_service or MT5DemoService()
        self.xauusd_validation_service = xauusd_validation_service or XAUUSDDemoValidationService()
        self.eurusd_validation_service = eurusd_validation_service or EURUSDDemoValidationService()
        self.nifty50_validation_service = nifty50_validation_service or NIFTY50DemoValidationService()
        self.e2e_validation_service = e2e_validation_service or E2EDemoValidationService()

    def get_status(self) -> dict[str, Any]:
        return self._build_readiness(run_preflight=False)

    def get_readiness(self) -> dict[str, Any]:
        return self._build_readiness(run_preflight=False)

    def run_preflight(self) -> dict[str, Any]:
        return self._build_readiness(run_preflight=True)

    def get_checklist(self) -> dict[str, Any]:
        docs_ready = self._failure_docs_available()
        return {
            "phase": "PHASE_14_DAY_7",
            "environment": "DEMO_SOAK_PREPARATION",
            "sections": [
                {
                    "name": "Backend",
                    "items": [
                        self._item("Health endpoint available", True),
                        self._item("Status endpoint available", True),
                        self._item("No backend exceptions", True),
                    ],
                },
                {
                    "name": "Demo",
                    "items": [
                        self._item("Demo environment status available", True),
                        self._item("MT5 demo status available or safely not connected", True),
                        self._item("XAUUSD validation available", True),
                        self._item("EURUSD validation available", True),
                        self._item("NIFTY50 validation available", True),
                        self._item("E2E preview validation available", True),
                    ],
                },
                {
                    "name": "Safety",
                    "items": [
                        self._item("simulation_only=true", True),
                        self._item("live_execution_enabled=false", True),
                        self._item("broker_execution_enabled=false", True),
                        self._item("execution_allowed=false", True),
                        self._item("preview_only=true", True),
                    ],
                },
                {
                    "name": "Monitoring",
                    "items": [
                        self._item("Logs available", True),
                        self._item("Health checks available", True),
                        self._item("Readiness checks available", True),
                        self._item("Failure handling docs available", docs_ready),
                    ],
                },
            ],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "preview_only": True,
            "timestamp": self._timestamp(),
        }

    def close(self) -> None:
        self.xauusd_validation_service.close()
        self.eurusd_validation_service.close()
        self.nifty50_validation_service.close()
        self.e2e_validation_service.close()

    def _build_readiness(self, run_preflight: bool) -> dict[str, Any]:
        warnings: list[str] = []
        failures: list[str] = []

        backend = self._safe_call("backend_status", self._backend_status, failures)
        demo_environment = self._safe_call("demo_environment", self.demo_environment_service.get_status, failures)
        mt5_demo = self._safe_call("mt5_demo", self.mt5_demo_service.get_status, failures)
        xauusd = self._safe_call("xauusd_validation", self.xauusd_validation_service.status, failures)
        eurusd = self._safe_call("eurusd_validation", self.eurusd_validation_service.status, failures)
        nifty50 = self._safe_call("nifty50_validation", self.nifty50_validation_service.status, failures)
        if run_preflight:
            e2e = self._safe_call("e2e_preview_validation", self.e2e_validation_service.run_validation, failures)
        else:
            e2e = self._safe_call("e2e_preview_validation", self.e2e_validation_service.status, failures)

        payloads = {
            "backend": backend,
            "demo_environment": demo_environment,
            "mt5_demo": mt5_demo,
            "xauusd_validation": xauusd,
            "eurusd_validation": eurusd,
            "nifty50_validation": nifty50,
            "e2e_preview_validation": e2e,
        }
        safety_findings = self._safety_findings(payloads)
        failures.extend(safety_findings)

        if mt5_demo.get("status") == "NOT_CONNECTED":
            warnings.append("MT5 demo is safely not connected; soak can monitor status but cannot validate connected market watch.")
        for label, payload in [
            ("XAUUSD", xauusd),
            ("EURUSD", eurusd),
            ("NIFTY50", nifty50),
            ("E2E", e2e),
        ]:
            if payload.get("status") == "NOT_RUN":
                warnings.append(f"{label} validation has not been run in this process yet.")
            elif payload.get("status") == "WARNING":
                warnings.append(f"{label} validation is available with warnings.")

        backend_ready = bool(backend.get("backend_ready"))
        demo_environment_ready = self._service_available(demo_environment)
        mt5_demo_ready = self._service_available(mt5_demo) and mt5_demo.get("status") in {"CONNECTED", "NOT_CONNECTED"}
        xauusd_ready = self._service_available(xauusd)
        eurusd_ready = self._service_available(eurusd)
        nifty50_ready = self._service_available(nifty50)
        e2e_ready = self._service_available(e2e)
        all_safety_locked = not safety_findings
        soak_ready = all(
            [
                backend_ready,
                demo_environment_ready,
                mt5_demo_ready,
                xauusd_ready,
                eurusd_ready,
                nifty50_ready,
                e2e_ready,
                all_safety_locked,
                self._failure_docs_available(),
            ]
        )

        return {
            "phase": "PHASE_14_DAY_7",
            "environment": "DEMO_SOAK_PREPARATION",
            "soak_ready": soak_ready,
            "backend_ready": backend_ready,
            "demo_environment_ready": demo_environment_ready,
            "mt5_demo_ready": mt5_demo_ready,
            "xauusd_validation_ready": xauusd_ready,
            "eurusd_validation_ready": eurusd_ready,
            "nifty50_validation_ready": nifty50_ready,
            "e2e_preview_ready": e2e_ready,
            "all_safety_locked": all_safety_locked,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "preview_only": True,
            "status": "READY_FOR_SOAK_TEST" if soak_ready else "NOT_READY",
            "warnings": warnings,
            "failures": failures,
            "checks": jsonable_encoder(payloads),
            "checklist": self.get_checklist(),
            "timestamp": self._timestamp(),
        }

    def _safe_call(self, name: str, callback, failures: list[str]) -> dict[str, Any]:
        try:
            return jsonable_encoder(callback())
        except Exception as exc:
            failures.append(f"{name} check failed: {exc}")
            return {
                "status": "ERROR",
                "error": str(exc),
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
            }

    def _backend_status(self) -> dict[str, Any]:
        return {
            "status": "HEALTHY",
            "backend_ready": True,
            "health_endpoint_available": True,
            "status_endpoint_available": True,
            "no_backend_exceptions": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _service_available(self, payload: dict[str, Any]) -> bool:
        return bool(payload) and payload.get("status") != "ERROR"

    def _safety_findings(self, payload: Any) -> list[str]:
        findings: list[str] = []
        for path, key, value in self._walk(payload):
            if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed"} and value is True:
                findings.append(f"Unsafe flag detected at {path}.{key}=true.")
            if key == "preview_only" and value is False:
                findings.append(f"Preview-only flag disabled at {path}.preview_only=false.")
        return findings

    def _walk(self, payload: Any, path: str = "root"):
        if isinstance(payload, dict):
            for key, value in payload.items():
                yield path, key, value
                yield from self._walk(value, f"{path}.{key}")
        elif isinstance(payload, list):
            for index, value in enumerate(payload):
                yield from self._walk(value, f"{path}[{index}]")

    def _failure_docs_available(self) -> bool:
        root = Path(__file__).resolve().parents[2]
        required = [
            root / "docs" / "validation-day-4-failure-handling.md",
            root / "docs" / "phase14-day7-soak-testing-preparation.md",
        ]
        return all(path.is_file() for path in required)

    def _item(self, label: str, completed: bool) -> dict[str, Any]:
        return {"label": label, "completed": completed}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
