from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.mt5_demo.demo_order_authorization_service import DemoOrderAuthorizationService
from backend.mt5_demo.demo_order_dry_run_service import DemoOrderDryRunService
from backend.mt5_demo.demo_order_preflight_models import DemoOrderPreflightResult
from backend.mt5_demo.mt5_execution_gate_validation_service import MT5ExecutionGateValidationService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService
from backend.mt5_demo.mt5_risk_qualification_service import MT5RiskQualificationService


class DemoOrderPreflightService:
    """Final readiness validation before any future DEMO-only order sender is considered."""

    allowed_symbols = {"EURUSD", "XAUUSD"}
    allowed_actions = {"BUY", "SELL"}
    max_lot = 0.01

    def __init__(
        self,
        authorization_service: DemoOrderAuthorizationService,
        dry_run_service: DemoOrderDryRunService,
        risk_qualification_service: MT5RiskQualificationService,
        execution_gate_service: MT5ExecutionGateValidationService,
        market_data_service: MT5MarketDataService,
    ) -> None:
        self.authorization_service = authorization_service
        self.dry_run_service = dry_run_service
        self.risk_qualification_service = risk_qualification_service
        self.execution_gate_service = execution_gate_service
        self.market_data_service = market_data_service
        self._history: list[dict[str, Any]] = []

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "PREFLIGHT_READY",
            "allowed_symbols": sorted(self.allowed_symbols),
            "allowed_actions": sorted(self.allowed_actions),
            "max_demo_lot": self.max_lot,
            "history_count": len(self._history),
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def run_preflight(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        latest_dry_run = self.dry_run_service.get_latest()
        source = payload if payload else latest_dry_run
        symbol = str(source.get("symbol") or "").strip().upper()
        action = str(source.get("action") or "").strip().upper()
        lot = self._float_or_none(source.get("lot"))
        entry_price = self._float_or_none(source.get("entry_price"))
        stop_loss = self._float_or_none(source.get("stop_loss"))
        take_profit = self._float_or_none(source.get("take_profit"))
        dry_run_id = source.get("dry_run_id")

        authorization = self.authorization_service.get_status()
        risk = self.risk_qualification_service.get_status()
        gate = self.execution_gate_service.get_status()
        spread = self.market_data_service.get_symbol_spread(symbol) if symbol in self.allowed_symbols else {}

        checks = {
            "symbol_check": symbol in self.allowed_symbols,
            "action_check": action in self.allowed_actions,
            "lot_check": lot is not None and 0 < lot <= self.max_lot,
            "stop_loss_check": stop_loss is not None,
            "take_profit_check": take_profit is not None,
            "risk_check": risk.get("status") == "RISK_QUALIFICATION_READY",
            "authorization_check": self._authorization_ready(authorization),
            "execution_gate_check": gate.get("status") == "EXECUTION_GATE_VALIDATION_READY" and gate.get("execution_allowed") is False,
            "market_data_check": spread.get("status") == "OK",
            "spread_check": spread.get("spread") is not None,
        }
        rejection_reasons = self._rejection_reasons(checks, dry_run_id, latest_dry_run)
        warnings = list(spread.get("warnings", []))
        if spread.get("message"):
            warnings.append(str(spread["message"]))
        validation_passed = not rejection_reasons
        result = DemoOrderPreflightResult(
            preflight_id=f"demo-preflight-{uuid4()}",
            dry_run_id=str(dry_run_id) if dry_run_id else None,
            validation_passed=validation_passed,
            warnings=warnings,
            rejection_reasons=rejection_reasons,
            would_be_allowed_in_demo=validation_passed,
            execution_allowed=False,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            timestamp=self._timestamp(),
            **checks,
        ).to_dict()
        self._history.append(result)
        return result

    def get_latest(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_RUN",
            "validation_passed": False,
            "rejection_reasons": ["No demo order preflight has been run yet."],
            "would_be_allowed_in_demo": False,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def list_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def _rejection_reasons(self, checks: dict[str, bool], dry_run_id: Any, latest_dry_run: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        names = {
            "symbol_check": "Invalid symbol.",
            "action_check": "Invalid action.",
            "lot_check": "Lot must be greater than 0 and no more than 0.01.",
            "stop_loss_check": "stop_loss is required.",
            "take_profit_check": "take_profit is required.",
            "risk_check": "Risk qualification is unavailable.",
            "authorization_check": "Demo authorization is not granted.",
            "execution_gate_check": "Execution gate is unavailable.",
            "market_data_check": "MT5 demo market data is unavailable.",
            "spread_check": "Spread is unavailable.",
        }
        for key, message in names.items():
            if checks[key] is False:
                reasons.append(message)
        if not dry_run_id:
            reasons.append("dry_run_id is required.")
        elif latest_dry_run.get("dry_run_id") != dry_run_id:
            reasons.append("dry_run_id does not match the latest dry-run.")
        if latest_dry_run.get("validation_passed") is not True:
            reasons.append("Latest dry-run has not passed validation.")
        return reasons

    def _authorization_ready(self, authorization: dict[str, Any]) -> bool:
        return (
            authorization.get("status") == "READY_FOR_DEMO_ORDER_TESTING"
            and authorization.get("demo_order_testing_enabled") is True
            and authorization.get("live_execution_enabled") is False
            and authorization.get("broker_execution_enabled") is False
            and authorization.get("execution_allowed") is False
        )

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
