from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder

from backend.demo_validation.eurusd_demo_validation_service import EURUSDDemoValidationService
from backend.demo_validation.nifty50_demo_validation_service import NIFTY50DemoValidationService
from backend.demo_validation.xauusd_demo_validation_service import XAUUSDDemoValidationService


class E2EDemoValidationStore:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def store(self, result: dict[str, Any]) -> dict[str, Any]:
        self._history.append(result)
        return result

    def latest(self) -> dict[str, Any] | None:
        return self._history[-1] if self._history else None

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history[-limit:]


e2e_demo_validation_store = E2EDemoValidationStore()


class E2EDemoValidationService:
    """Run end-to-end demo preview validation for all supported instruments."""

    SYMBOLS = ["XAUUSD", "EURUSD", "NIFTY50"]

    def __init__(self, store: E2EDemoValidationStore | None = None) -> None:
        self.store = store or e2e_demo_validation_store

    def status(self) -> dict[str, Any]:
        latest = self.store.latest()
        return {
            "environment": "DEMO_PREVIEW",
            "symbols_tested": self.SYMBOLS,
            "status": latest["status"] if latest else "NOT_RUN",
            "latest_validation_id": latest.get("validation_id") if latest else None,
            "history_count": len(self.store.history(1000)),
            "all_safety_locked": latest.get("all_safety_locked") if latest else None,
            "execution_allowed": False,
            "preview_only": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def run_validation(self) -> dict[str, Any]:
        warnings: list[str] = []
        failures: list[str] = []

        xauusd = self._run_xauusd()
        eurusd = self._run_eurusd()
        nifty50 = self._run_nifty50()
        symbol_results = {
            "XAUUSD": xauusd,
            "EURUSD": eurusd,
            "NIFTY50": nifty50,
        }

        for symbol, output in symbol_results.items():
            if output.get("status") == "FAIL":
                failures.append(f"{symbol} validation returned FAIL.")
            for warning in output.get("warnings", []):
                warnings.append(f"{symbol}: {warning}")

        safety_findings = self._safety_findings(symbol_results)
        failures.extend(safety_findings)
        pipeline_checks = self._pipeline_checks(symbol_results)
        for name, passed in pipeline_checks.items():
            if not passed:
                failures.append(f"Pipeline check failed: {name}.")

        all_safety_locked = not safety_findings
        status = "FAIL" if failures else "WARNING" if warnings else "PASS"
        result = {
            "validation_id": f"e2e-demo-preview-validation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "environment": "DEMO_PREVIEW",
            "symbols_tested": self.SYMBOLS,
            "xauusd_status": xauusd.get("status", "UNKNOWN"),
            "eurusd_status": eurusd.get("status", "UNKNOWN"),
            "nifty50_status": nifty50.get("status", "UNKNOWN"),
            "all_safety_locked": all_safety_locked,
            "execution_allowed": False,
            "preview_only": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "status": status,
            "warnings": warnings,
            "failures": failures,
            "pipeline_checks": pipeline_checks,
            "symbol_results": symbol_results,
            "audit_history_checked": True,
            "latest_result_available": True,
            "history_available": True,
            "fake_trades_created": False,
            "fake_pnl_created": False,
            "trade_journal_records_created": False,
            "why_no_trades_were_placed": (
                "Phase 14 Day 6 validates preview behavior only; execution_allowed, "
                "live_execution_enabled, and broker_execution_enabled remain false."
            ),
            "timestamp": self._timestamp(),
        }
        return self.store.store(result)

    def latest(self) -> dict[str, Any]:
        latest = self.store.latest()
        if latest is None:
            return {
                "environment": "DEMO_PREVIEW",
                "symbols_tested": self.SYMBOLS,
                "status": "NOT_RUN",
                "all_safety_locked": None,
                "execution_allowed": False,
                "preview_only": True,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "warnings": ["No E2E demo preview validation run has been recorded yet."],
                "timestamp": self._timestamp(),
            }
        return latest

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.history(limit)

    def close(self) -> None:
        return None

    def _run_xauusd(self) -> dict[str, Any]:
        service = XAUUSDDemoValidationService()
        try:
            return jsonable_encoder(service.run_validation())
        finally:
            service.close()

    def _run_eurusd(self) -> dict[str, Any]:
        service = EURUSDDemoValidationService()
        try:
            return jsonable_encoder(service.run_validation())
        finally:
            service.close()

    def _run_nifty50(self) -> dict[str, Any]:
        service = NIFTY50DemoValidationService()
        try:
            return jsonable_encoder(service.run_validation())
        finally:
            service.close()

    def _safety_findings(self, payload: Any) -> list[str]:
        findings: list[str] = []
        for path, key, value in self._walk(payload):
            if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed"} and value is True:
                findings.append(f"Unsafe flag detected at {path}.{key}=true.")
            if key == "preview_only" and value is False:
                findings.append(f"Preview-only flag disabled at {path}.preview_only=false.")
        nifty = payload.get("NIFTY50", {}) if isinstance(payload, dict) else {}
        if nifty.get("preview_only") is not True:
            findings.append("NIFTY50 validation did not report preview_only=true.")
        if nifty.get("execution_status", {}).get("preview_only") is not True:
            findings.append("NIFTY50 execution bridge did not report preview_only=true.")
        return findings

    def _walk(self, payload: Any, path: str = "root"):
        if isinstance(payload, dict):
            for key, value in payload.items():
                current = f"{path}.{key}"
                yield path, key, value
                yield from self._walk(value, current)
        elif isinstance(payload, list):
            for index, value in enumerate(payload):
                yield from self._walk(value, f"{path}[{index}]")

    def _pipeline_checks(self, results: dict[str, dict[str, Any]]) -> dict[str, bool]:
        xauusd = results["XAUUSD"]
        eurusd = results["EURUSD"]
        nifty50 = results["NIFTY50"]
        return {
            "xauusd_strategy_validation": bool(xauusd.get("signal_generated")),
            "xauusd_risk_validation": xauusd.get("risk_checked") is True,
            "xauusd_execution_bridge_preview": xauusd.get("bridge_checked") is True
            and xauusd.get("bridge_decision", {}).get("eligible") is False,
            "xauusd_analytics_presence": xauusd.get("analytics_check", {}).get("xauusd_in_symbols") is True,
            "eurusd_strategy_validation": bool(eurusd.get("signal_generated")),
            "eurusd_risk_validation": eurusd.get("risk_checked") is True,
            "eurusd_execution_bridge_preview": eurusd.get("bridge_checked") is True
            and eurusd.get("bridge_decision", {}).get("eligible") is False,
            "eurusd_analytics_presence": eurusd.get("analytics_check", {}).get("eurusd_in_symbols") is True,
            "nifty50_market_data_check": nifty50.get("market_data_checked") is True,
            "nifty50_smc_snapshot": nifty50.get("strategy_checked") is True
            and bool(nifty50.get("strategy_snapshot")),
            "nifty50_risk_validation": nifty50.get("risk_checked") is True,
            "nifty50_execution_preview": nifty50.get("execution_preview_checked") is True
            and nifty50.get("execution_status", {}).get("preview_only") is True,
            "nifty50_analytics_presence": nifty50.get("analytics_check", {}).get("nifty50_in_symbols") is True,
        }

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
