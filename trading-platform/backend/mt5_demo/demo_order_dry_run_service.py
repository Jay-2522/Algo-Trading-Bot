from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.mt5_demo.demo_order_authorization_service import DemoOrderAuthorizationService
from backend.mt5_demo.demo_order_dry_run_models import DemoOrderDryRunResult
from backend.mt5_demo.mt5_execution_gate_validation_service import MT5ExecutionGateValidationService


class DemoOrderDryRunService:
    """Builds DEMO order previews without submitting anything to a broker."""

    allowed_symbols = {"EURUSD", "XAUUSD"}
    allowed_actions = {"BUY", "SELL"}
    max_lot = 0.01

    def __init__(
        self,
        authorization_service: DemoOrderAuthorizationService,
        execution_gate_service: MT5ExecutionGateValidationService,
    ) -> None:
        self.authorization_service = authorization_service
        self.execution_gate_service = execution_gate_service
        self._history: list[dict[str, Any]] = []

    def get_status(self) -> dict[str, Any]:
        authorization = self.authorization_service.get_status()
        gate = self.execution_gate_service.get_status()
        return {
            "status": "DRY_RUN_READY" if self._authorization_ready(authorization) and self._gate_ready(gate) else "DRY_RUN_LOCKED",
            "allowed_symbols": sorted(self.allowed_symbols),
            "allowed_actions": sorted(self.allowed_actions),
            "max_demo_lot": self.max_lot,
            "authorization_status": authorization.get("status"),
            "execution_gate_status": gate.get("status"),
            "history_count": len(self._history),
            "would_send_to_mt5": False,
            "mt5_order_sent": False,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def create_dry_run(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        symbol = str(payload.get("symbol") or "").strip().upper()
        action = str(payload.get("action") or "").strip().upper()
        lot = self._float_or_none(payload.get("lot"))
        entry_price = self._float_or_none(payload.get("entry_price"))
        stop_loss = self._float_or_none(payload.get("stop_loss"))
        take_profit = self._float_or_none(payload.get("take_profit"))
        rejection_reasons = self._validate(payload, symbol, action, lot, stop_loss, take_profit)
        validation_passed = not rejection_reasons
        result = DemoOrderDryRunResult(
            dry_run_id=f"demo-dry-run-{uuid4()}",
            symbol=symbol,
            action=action,
            lot=lot or 0.0,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            validation_passed=validation_passed,
            rejection_reasons=rejection_reasons,
            order_payload_preview=self._preview(symbol, action, lot, entry_price, stop_loss, take_profit) if validation_passed else {},
            would_send_to_mt5=False,
            mt5_order_sent=False,
            execution_allowed=False,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            timestamp=self._timestamp(),
        ).to_dict()
        self._history.append(result)
        return result

    def get_latest(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_RUN",
            "validation_passed": False,
            "rejection_reasons": ["No demo order dry-run has been created yet."],
            "would_send_to_mt5": False,
            "mt5_order_sent": False,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def list_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def _validate(
        self,
        payload: dict[str, Any],
        symbol: str,
        action: str,
        lot: float | None,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> list[str]:
        reasons: list[str] = []
        authorization = self.authorization_service.get_status()
        gate = self.execution_gate_service.get_status()

        if symbol not in self.allowed_symbols:
            reasons.append("Unsupported symbol. Allowed symbols are EURUSD and XAUUSD.")
        if action not in self.allowed_actions:
            reasons.append("Unsupported action. Allowed actions are BUY and SELL.")
        if lot is None or lot <= 0:
            reasons.append("Lot must be greater than 0.")
        elif lot > self.max_lot:
            reasons.append("Lot exceeds the 0.01 max demo lot.")
        if stop_loss is None:
            reasons.append("stop_loss is required.")
        if take_profit is None:
            reasons.append("take_profit is required.")
        if payload.get("manual_confirmation") is not True:
            reasons.append("manual_confirmation must be true.")
        if not payload.get("risk_decision_id"):
            reasons.append("risk_decision_id is required for dry-run risk traceability.")
        if not payload.get("gate_decision_id"):
            reasons.append("gate_decision_id is required for execution gate traceability.")
        if not self._authorization_ready(authorization):
            reasons.append("Demo authorization is locked.")
        if not self._gate_ready(gate):
            reasons.append("Execution gate is not ready.")
        if payload.get("live_execution_enabled") is True:
            reasons.append("live_execution_enabled cannot be true.")
        if payload.get("broker_execution_enabled") is True:
            reasons.append("broker_execution_enabled cannot be true.")
        return reasons

    def _preview(
        self,
        symbol: str,
        action: str,
        lot: float | None,
        entry_price: float | None,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "type": action,
            "volume": lot,
            "price": entry_price,
            "sl": stop_loss,
            "tp": take_profit,
        }

    def _authorization_ready(self, authorization: dict[str, Any]) -> bool:
        return (
            authorization.get("status") == "READY_FOR_DEMO_ORDER_TESTING"
            and authorization.get("demo_order_testing_enabled") is True
            and authorization.get("live_execution_enabled") is False
            and authorization.get("broker_execution_enabled") is False
            and authorization.get("execution_allowed") is False
        )

    def _gate_ready(self, gate: dict[str, Any]) -> bool:
        return gate.get("status") == "EXECUTION_GATE_VALIDATION_READY" and gate.get("execution_allowed") is False

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
