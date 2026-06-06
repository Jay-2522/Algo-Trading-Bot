from datetime import datetime, timezone
from typing import Any

from backend.client_analytics.client_analytics_service import ClientAnalyticsService
from backend.client_analytics.executive_dashboard_service import ExecutiveDashboardService
from backend.client_analytics.strategy_analytics_service import StrategyAnalyticsService
from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator
from backend.strategy_engine.strategy_service import StrategyService
from backend.strategy_execution_bridge.strategy_execution_bridge_service import StrategyExecutionBridgeService


class XAUUSDDemoValidationStore:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def store(self, result: dict[str, Any]) -> dict[str, Any]:
        self._history.append(result)
        return result

    def latest(self) -> dict[str, Any] | None:
        return self._history[-1] if self._history else None

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history[-limit:]


validation_store = XAUUSDDemoValidationStore()


class XAUUSDDemoValidationService:
    """Validate XAUUSD demo signal flow without order placement."""

    def __init__(
        self,
        strategy_service: StrategyService | None = None,
        bridge_service: StrategyExecutionBridgeService | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
        analytics_service: ClientAnalyticsService | None = None,
        strategy_analytics_service: StrategyAnalyticsService | None = None,
        executive_service: ExecutiveDashboardService | None = None,
        store: XAUUSDDemoValidationStore | None = None,
    ) -> None:
        self.strategy_service = strategy_service or StrategyService()
        self.bridge_service = bridge_service or StrategyExecutionBridgeService(strategy_service=self.strategy_service)
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator()
        self.analytics_service = analytics_service or ClientAnalyticsService()
        self.strategy_analytics_service = strategy_analytics_service or StrategyAnalyticsService()
        self.executive_service = executive_service or ExecutiveDashboardService()
        self.store = store or validation_store

    def status(self) -> dict[str, Any]:
        latest = self.store.latest()
        return {
            "symbol": "XAUUSD",
            "environment": "DEMO",
            "status": latest["status"] if latest else "NOT_RUN",
            "latest_validation_id": latest.get("validation_id") if latest else None,
            "history_count": len(self.store.history(1000)),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def run_validation(self) -> dict[str, Any]:
        warnings: list[str] = []
        failures: list[str] = []
        strategy_status = self.strategy_service.get_status()
        signal = self.strategy_service.analyze_xauusd()
        signal_payload = signal.model_dump(mode="json")

        component_checks = self._strategy_component_checks(warnings)
        risk_decision = self.risk_evaluator.evaluate_single_account_request(
            {
                "request_id": f"phase14-xauusd-validation-{signal.signal_id}",
                "signal_id": signal.signal_id,
                "symbol": "XAUUSD",
                "canonical_symbol": "XAUUSD",
                "action": signal.action,
                "lot": 0.01,
                "requested_lot": 0.01,
                "confirm_demo_execution": False,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }
        )
        bridge_decision = self.bridge_service.evaluate_and_preview_signal(signal)
        bridge_payload = bridge_decision.model_dump(mode="json")
        analytics_check = self._analytics_check()

        if signal.execution_allowed is not False:
            failures.append("XAUUSD signal execution_allowed became true.")
        if bridge_decision.live_execution_enabled or bridge_decision.broker_execution_enabled:
            failures.append("Execution bridge exposed live or broker execution.")
        if bridge_decision.queue_preview_created:
            failures.append("Execution bridge created a queue preview for XAUUSD validation.")
        if bridge_decision.eligible:
            failures.append("Execution bridge marked XAUUSD signal eligible.")
        if not analytics_check["xauusd_in_symbols"]:
            failures.append("XAUUSD missing from client analytics symbols.")
        if not analytics_check["xauusd_in_strategy_performance"]:
            failures.append("XAUUSD missing from strategy performance analytics.")
        if not analytics_check["xauusd_in_executive_instruments"]:
            failures.append("XAUUSD missing from executive instrument readiness.")

        if self._limited_backend_context(component_checks):
            warnings.append("No live/demo XAUUSD candle stream available; strategy output is limited to current backend context.")

        status = "FAIL" if failures else "WARNING" if warnings else "PASS"
        result = {
            "validation_id": f"xauusd-demo-validation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "symbol": "XAUUSD",
            "environment": "DEMO",
            "signal_generated": bool(signal.signal_id),
            "strategy_status": strategy_status.get("status", "UNKNOWN"),
            "risk_checked": True,
            "risk_approved": bool(risk_decision.approved),
            "bridge_checked": True,
            "execution_allowed": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "status": status,
            "warnings": warnings,
            "failures": failures,
            "signal": {
                "signal_id": signal.signal_id,
                "action": signal.action,
                "confidence": signal.confidence,
                "trade_quality": signal.trade_quality,
                "execution_allowed": signal.execution_allowed,
                "client_summary": signal.client_summary,
                "technical_summary": signal.technical_summary,
            },
            "strategy_components": component_checks,
            "risk_decision": risk_decision.model_dump(mode="json"),
            "bridge_decision": bridge_payload,
            "analytics_check": analytics_check,
            "simulation_only": True,
            "timestamp": self._timestamp(),
        }
        return self.store.store(result)

    def latest(self) -> dict[str, Any]:
        latest = self.store.latest()
        if latest is None:
            return {
                "symbol": "XAUUSD",
                "environment": "DEMO",
                "status": "NOT_RUN",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "warnings": ["No XAUUSD demo validation run has been recorded yet."],
                "timestamp": self._timestamp(),
            }
        return latest

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.history(limit)

    def close(self) -> None:
        self.strategy_service.close()
        self.bridge_service.close()

    def _strategy_component_checks(self, warnings: list[str]) -> dict[str, Any]:
        components: dict[str, Any] = {}
        try:
            liquidity = self.strategy_service.analyze_xauusd_liquidity()
            components["liquidity"] = {
                "available": True,
                "sweep_detected": getattr(liquidity, "sweep_detected", False),
                "direction": getattr(liquidity, "sweep_direction", "NONE"),
                "warnings": getattr(liquidity, "warnings", []),
            }
        except Exception as exc:
            warnings.append(f"Liquidity context unavailable: {exc}")
            components["liquidity"] = {"available": False}

        try:
            structure = self.strategy_service.analyze_xauusd_structure()
            components["structure"] = {
                "available": True,
                "bos_detected": getattr(structure, "bos_detected", False),
                "choch_detected": getattr(structure, "choch_detected", False),
                "structure_bias": getattr(structure, "structure_bias", "NEUTRAL"),
                "warnings": getattr(structure, "warnings", []),
            }
        except Exception as exc:
            warnings.append(f"Structure context unavailable: {exc}")
            components["structure"] = {"available": False}

        for name, builder in [
            ("fvg", self.strategy_service.analyze_xauusd_fvg),
            ("order_block", self.strategy_service.analyze_xauusd_order_block),
            ("regime", self.strategy_service.analyze_xauusd_regime),
            ("confidence", self.strategy_service.analyze_xauusd_confluence),
        ]:
            try:
                components[name] = {"available": True, "data": builder()}
            except Exception as exc:
                warnings.append(f"{name} context unavailable: {exc}")
                components[name] = {"available": False}
        return components

    def _analytics_check(self) -> dict[str, Any]:
        symbols = self.analytics_service.get_all_symbol_performance()
        strategy_performance = self.strategy_analytics_service.get_symbol_performance("XAUUSD")
        executive = self.executive_service.get_instrument_readiness()
        executive_symbols = {
            item.get("symbol")
            for item in executive.get("instruments", [])
            if isinstance(item, dict)
        }
        return {
            "xauusd_in_symbols": "XAUUSD" in {item.symbol for item in symbols},
            "xauusd_in_strategy_performance": strategy_performance.symbol == "XAUUSD",
            "xauusd_in_executive_instruments": "XAUUSD" in executive_symbols,
            "strategy_performance": strategy_performance.model_dump(mode="json"),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _limited_backend_context(self, components: dict[str, Any]) -> bool:
        confidence = components.get("confidence", {}).get("data", {})
        missing = confidence.get("missing_confirmations", []) if isinstance(confidence, dict) else []
        return bool(missing) or confidence.get("confidence", 0) == 0 if isinstance(confidence, dict) else True

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
