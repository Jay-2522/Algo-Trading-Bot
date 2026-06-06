from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.mt5_demo.demo_execution_simulator_models import DemoExecutionSimulationResult
from backend.mt5_demo.demo_order_preflight_service import DemoOrderPreflightService


class DemoExecutionSimulatorService:
    """Virtual DEMO execution simulator. It never interacts with MT5 order APIs."""

    contract_sizes = {
        "EURUSD": 100000,
        "XAUUSD": 100,
    }
    leverage_estimate = 50

    def __init__(self, preflight_service: DemoOrderPreflightService) -> None:
        self.preflight_service = preflight_service
        self._history: list[dict[str, Any]] = []

    def get_status(self) -> dict[str, Any]:
        latest_preflight = self.preflight_service.get_latest()
        return {
            "status": "SIMULATOR_READY",
            "latest_preflight_passed": latest_preflight.get("validation_passed") is True,
            "history_count": len(self._history),
            "estimation_mode": "ESTIMATED_VALUES_ONLY",
            "execution_allowed": False,
            "would_send_to_mt5": False,
            "mt5_order_sent": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def simulate_execution(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        latest_preflight = self.preflight_service.get_latest()
        source = payload if payload else latest_preflight
        symbol = str(source.get("symbol") or "").strip().upper()
        action = str(source.get("action") or "").strip().upper()
        lot = self._float_or_none(source.get("lot"))
        entry_price = self._float_or_none(source.get("entry_price"))
        stop_loss = self._float_or_none(source.get("stop_loss"))
        take_profit = self._float_or_none(source.get("take_profit"))
        preflight_id = source.get("preflight_id") or latest_preflight.get("preflight_id")
        warnings = ["ESTIMATED_VALUES_ONLY", "NO_ORDER_SENT"]
        rejection_reasons = self._rejection_reasons(
            latest_preflight,
            preflight_id,
            symbol,
            action,
            lot,
            entry_price,
            stop_loss,
            take_profit,
        )
        simulation_passed = not rejection_reasons
        risk_amount = self._risk_amount(symbol, lot, entry_price, stop_loss) if simulation_passed else None
        reward_amount = self._reward_amount(symbol, lot, entry_price, take_profit) if simulation_passed else None
        result = DemoExecutionSimulationResult(
            simulation_id=f"demo-simulation-{uuid4()}",
            preflight_id=str(preflight_id) if preflight_id else None,
            symbol=symbol,
            action=action,
            lot=lot or 0.0,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            simulated_risk_amount=risk_amount,
            simulated_reward_amount=reward_amount,
            risk_reward_ratio=self._ratio(reward_amount, risk_amount),
            estimated_margin=self._estimated_margin(symbol, lot, entry_price) if simulation_passed else None,
            simulated_order_payload=self._payload(symbol, action, lot, entry_price, stop_loss, take_profit) if simulation_passed else {},
            simulation_passed=simulation_passed,
            execution_allowed=False,
            would_send_to_mt5=False,
            mt5_order_sent=False,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            warnings=warnings + rejection_reasons,
            timestamp=self._timestamp(),
        ).to_dict()
        self._history.append(result)
        return result

    def get_latest(self) -> dict[str, Any]:
        if self._history:
            return self._history[-1]
        return {
            "status": "NOT_RUN",
            "simulation_passed": False,
            "warnings": ["No demo execution simulation has been run yet."],
            "execution_allowed": False,
            "would_send_to_mt5": False,
            "mt5_order_sent": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
        }

    def list_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def _rejection_reasons(
        self,
        latest_preflight: dict[str, Any],
        preflight_id: Any,
        symbol: str,
        action: str,
        lot: float | None,
        entry_price: float | None,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> list[str]:
        reasons: list[str] = []
        if latest_preflight.get("validation_passed") is not True:
            reasons.append("Latest preflight has not passed validation.")
        if not preflight_id:
            reasons.append("preflight_id is required.")
        elif latest_preflight.get("preflight_id") != preflight_id:
            reasons.append("preflight_id does not match the latest preflight.")
        if symbol not in self.contract_sizes:
            reasons.append("Unsupported symbol for simulation.")
        if action not in {"BUY", "SELL"}:
            reasons.append("Unsupported action for simulation.")
        if lot is None or lot <= 0 or lot > 0.01:
            reasons.append("Lot must be greater than 0 and no more than 0.01.")
        if entry_price is None or entry_price <= 0:
            reasons.append("entry_price must be greater than 0.")
        if stop_loss is None or stop_loss <= 0:
            reasons.append("stop_loss must be greater than 0.")
        if take_profit is None or take_profit <= 0:
            reasons.append("take_profit must be greater than 0.")
        return reasons

    def _risk_amount(self, symbol: str, lot: float | None, entry_price: float | None, stop_loss: float | None) -> float:
        return self._price_distance_amount(symbol, lot, entry_price, stop_loss)

    def _reward_amount(self, symbol: str, lot: float | None, entry_price: float | None, take_profit: float | None) -> float:
        return self._price_distance_amount(symbol, lot, entry_price, take_profit)

    def _price_distance_amount(self, symbol: str, lot: float | None, first: float | None, second: float | None) -> float:
        contract_size = self.contract_sizes.get(symbol, 1)
        amount = abs(float(first or 0) - float(second or 0)) * float(lot or 0) * contract_size
        return round(amount, 2)

    def _ratio(self, reward_amount: float | None, risk_amount: float | None) -> float | None:
        if risk_amount is None or risk_amount <= 0 or reward_amount is None:
            return None
        return round(reward_amount / risk_amount, 2)

    def _estimated_margin(self, symbol: str, lot: float | None, entry_price: float | None) -> float:
        contract_size = self.contract_sizes.get(symbol, 1)
        margin = float(entry_price or 0) * float(lot or 0) * contract_size / self.leverage_estimate
        return round(margin, 2)

    def _payload(
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
            "comment": "SIMULATED_ONLY_NO_ORDER_SENT",
        }

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
